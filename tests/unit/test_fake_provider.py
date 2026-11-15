"""Fake provider + client flow. Every result here is MOCK evidence: app logic only (not live billing).

Covers FR-AI-001..005, FR-BUD-002/005/007, QG COST-01/02/05/06/09, F-02..F-04, F-07.
"""

from __future__ import annotations

import socket
from pathlib import Path

import pytest

from storymotion_media.providers.base import (
    AmbiguousSubmission,
    AnimationRequest,
    ApprovalInvalid,
    PricingUnavailable,
    ProviderUnavailable,
    RateLimited,
    RequestValidationError,
    SourceImage,
    UnsupportedOperation,
    create_approval,
)
from storymotion_media.providers.fake import FakeVideoProvider, Scenario
from storymotion_media.providers.flow import (
    MAX_TRANSPORT_RETRIES,
    poll_until_done,
    submit_once,
)


class Clock:
    def __init__(self) -> None:
        self.t = 1000.0

    def __call__(self) -> float:
        return self.t


def stub_factory(req: AnimationRequest, out: Path) -> None:
    out.write_bytes(b"MOCKCLIP" + req.request_hash().encode())


def req(**kw: object) -> AnimationRequest:
    base: dict[str, object] = dict(
        shot_id="s1",
        sources=(SourceImage(Path("a.png"), "a" * 64),),
        prompt="Sailors throw Jonah",
        duration_ms=5000,
        width=1280,
        height=720,
    )
    base.update(kw)
    return AnimationRequest(**base)  # type: ignore[arg-type]


def provider(tmp_path: Path, **kw: object) -> FakeVideoProvider:
    kw.setdefault("clock", Clock())
    return FakeVideoProvider(clip_factory=stub_factory, work_dir=tmp_path / "prov", **kw)  # type: ignore[arg-type]


def approved(p: FakeVideoProvider, r: AnimationRequest, aid: str = "ap-1"):  # noqa: ANN201
    return create_approval(p.quote(r), user_confirmed=True, approval_id=aid)


def no_sleep(_: float) -> None:
    pass


def test_no_network_is_ever_used(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*a: object, **k: object) -> None:
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    p = provider(tmp_path)
    r = req()
    ref = submit_once(p, r, approved(p, r), sleep=no_sleep)
    assert poll_until_done(p, ref, sleep=no_sleep)
    assert p.download(ref, tmp_path / "dl").path.exists()


@pytest.mark.parametrize(
    ("kw", "field"),
    [
        ({"duration_ms": 7777}, "duration_ms"),
        ({"width": 640, "height": 360}, "resolution"),
        ({"prompt": "  "}, "prompt"),
        ({"prompt": "x" * 2001}, "prompt"),
        ({"sources": ()}, "sources"),
        ({"sources": (SourceImage(Path("a.bmp"), "b" * 64),)}, "sources[0]"),
        ({"sources": tuple(SourceImage(Path(f"{i}.png"), "c" * 64) for i in range(3))}, "sources"),
    ],
)
def test_unsupported_requests_rejected_before_quote(tmp_path: Path, kw: dict[str, object], field: str) -> None:
    p = provider(tmp_path)
    with pytest.raises(RequestValidationError) as ei:
        p.quote(req(**kw))
    assert any(i.path == field for i in ei.value.issues)
    assert not p.charges


def test_quote_uses_min_billable_and_exact_integer_money(tmp_path: Path) -> None:
    p = provider(tmp_path, min_billable_ms=4000, price_micro_usd_per_second=33_333)
    short = p.quote(req(duration_ms=3000))
    assert short.billable_ms == 4000 and short.amount_micro_usd == 133_332  # integer micro-USD
    assert p.quote(req(duration_ms=5000)).amount_micro_usd == 166_665
    assert short.is_mock and short.amount_usd == "0.133332"


@pytest.mark.parametrize("kw", [{"price_micro_usd_per_second": None}, {"pricing_config_version": None}])
def test_unknown_price_fails_closed(tmp_path: Path, kw: dict[str, object]) -> None:  # COST-02 / F-03
    p = provider(tmp_path, **kw)
    with pytest.raises(PricingUnavailable):
        p.quote(req())
    assert p.submit_calls == 0 and not p.charges


def test_no_approval_without_explicit_confirmation(tmp_path: Path) -> None:
    p = provider(tmp_path)
    q = p.quote(req())
    with pytest.raises(ApprovalInvalid):
        create_approval(q, user_confirmed=False, approval_id="x")


def test_submit_rejects_wrong_request_expired_quote_and_low_max(tmp_path: Path) -> None:
    clock = Clock()
    p = provider(tmp_path, clock=clock)
    r = req()
    ap = approved(p, r)
    with pytest.raises(ApprovalInvalid, match="different request"):
        p.submit(req(prompt="something else"), ap)
    low = type(ap)(ap.approval_id, ap.quote_id, ap.request_hash, ap.max_micro_usd - 1)
    with pytest.raises(ApprovalInvalid, match="below the quoted"):
        p.submit(r, low)
    clock.t += 301  # past TTL
    with pytest.raises(ApprovalInvalid, match="expired"):
        p.submit(r, ap)
    assert not p.charges


def test_same_approval_is_idempotent_new_approval_is_new_attempt(tmp_path: Path) -> None:  # COST-05
    p = provider(tmp_path)
    r = req()
    a1 = approved(p, r, "ap-1")
    j1, j1b = p.submit(r, a1), p.submit(r, a1)
    assert j1 == j1b and len(p.charges) == 1
    a2 = approved(p, r, "ap-2")  # a creative retry needs its own explicit approval
    assert p.submit(r, a2).job_id != j1.job_id and len(p.charges) == 2


def test_lost_response_is_reconciled_without_second_charge(tmp_path: Path) -> None:  # COST-06 / F-04
    p = provider(tmp_path, scenario=Scenario(submit="lost_response"))
    r = req()
    ref = submit_once(p, r, approved(p, r), sleep=no_sleep)
    assert ref.job_id and len(p.charges) == 1 and p.submit_calls == 1


def test_lost_response_without_lookup_blocks_resubmission(tmp_path: Path) -> None:
    p = provider(tmp_path, scenario=Scenario(submit="lost_response"), supports_idempotent_lookup=False)
    r = req()
    with pytest.raises(AmbiguousSubmission):
        submit_once(p, r, approved(p, r), sleep=no_sleep)
    assert p.submit_calls == 1  # exactly one attempt; no blind retry
    with pytest.raises(UnsupportedOperation):
        p.lookup_by_approval("ap-1")


def test_rate_limit_retries_are_bounded_and_do_not_double_charge(tmp_path: Path) -> None:
    p = provider(tmp_path, scenario=Scenario(submit="rate_limited_once"))
    r = req()
    sleeps: list[float] = []
    submit_once(p, r, approved(p, r), sleep=sleeps.append)
    assert p.submit_calls == 2 and len(p.charges) == 1 and sleeps == [2.0]


def test_outage_gives_up_after_bounded_retries_with_zero_charges(tmp_path: Path) -> None:  # F-02-like
    p = provider(tmp_path, scenario=Scenario(submit="outage"))
    r = req()
    with pytest.raises((ProviderUnavailable, RateLimited)):
        submit_once(p, r, approved(p, r), sleep=no_sleep)
    assert p.submit_calls == MAX_TRANSPORT_RETRIES + 1 and not p.charges


def test_failed_job_surfaces_error_and_keeps_the_charge_record(tmp_path: Path) -> None:
    p = provider(tmp_path, scenario=Scenario(job="fail"))
    r = req()
    ref = submit_once(p, r, approved(p, r), sleep=no_sleep)
    with pytest.raises(Exception, match="generation failed"):
        poll_until_done(p, ref, sleep=no_sleep)
    assert len(p.charges) == 1  # potential charge preserved (F-06 spirit)


def test_cancel_unsupported_is_explicit(tmp_path: Path) -> None:
    p = provider(tmp_path, supports_cancel=False)
    r = req()
    ref = submit_once(p, r, approved(p, r), sleep=no_sleep)
    with pytest.raises(UnsupportedOperation, match="charge stands"):
        p.cancel(ref)
    assert len(p.charges) == 1


def test_capabilities_are_labelled_unverified_mock(tmp_path: Path) -> None:
    caps = provider(tmp_path).get_capabilities()
    assert caps.pricing_verified is False and "MOCK" in caps.model_label and caps.warnings
