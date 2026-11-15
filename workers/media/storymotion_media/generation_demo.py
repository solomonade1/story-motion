"""End-to-end MOCK generation flow for one GENERATIVE shot, then clip incorporation.

quote -> (simulated) explicit approval -> submit -> poll -> verified download -> attach as an
immutable ``generated_video`` asset -> shot becomes renderable. No network; no real money.
"""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from .contracts import Asset, Generation, Manifest, Provenance
from .errors import StoryMotionError
from .ingest import resolve_in_root, sha256_file
from .providers.base import AnimationRequest, SourceImage, create_approval
from .providers.clip_factory import FfmpegMockClipFactory
from .providers.fake import FakeVideoProvider, Scenario
from .providers.flow import download_verified, poll_until_done, submit_once
from .toolchain import Toolchain


def request_for_shot(manifest: Manifest, shot_id: str, root: Path, w: int = 1280, h: int = 720) -> AnimationRequest:
    shot = next((s for s in manifest.shots if s.id == shot_id), None)
    if shot is None or shot.mode != "GENERATIVE":
        raise StoryMotionError(f"'{shot_id}' is not a GENERATIVE shot")
    srcs = []
    for aid in shot.sourceAssetIds[:2]:
        a = manifest.asset(aid)
        srcs.append(SourceImage(resolve_in_root(root, a.path), a.sha256))
    prompt = shot.action
    if shot.mustShow:
        prompt += ". Must show: " + "; ".join(shot.mustShow)
    return AnimationRequest(
        shot_id=shot.id,
        sources=tuple(srcs),
        prompt=prompt,
        duration_ms=shot.durationMs,
        width=w,
        height=h,
        negative_prompt="; ".join(shot.avoid),
        seed=42,
    )


def attach_generated_clip(manifest: Manifest, shot_id: str, rel_path: str, sha256: str, *, approved: bool) -> Manifest:
    asset = Asset(
        id=f"{shot_id}-mock-clip",
        type="generated_video",
        path=rel_path,
        sha256=sha256,
        provenance=Provenance(
            kind="mock_provider_output",
            source="storymotion_media FakeVideoProvider (local, no network)",
            license="n/a - procedural mock output",
            licenseVerified=False,
            notes="MOCK clip. Proves integration only; not AI output and not evidence of quality.",
        ),
    )
    shots = []
    for s in manifest.shots:
        if s.id == shot_id:
            assert s.generation is not None
            s = s.model_copy(
                update={
                    "generation": Generation(providerProfileId=s.generation.providerProfileId, clipAssetId=asset.id),
                    "approval": "approved" if approved else "pending",
                }
            )
        shots.append(s)
    return manifest.model_copy(update={"assets": [*manifest.assets, asset], "shots": shots})


def run_mock_generation(
    tc: Toolchain,
    manifest: Manifest,
    root: Path,
    shot_id: str,
    *,
    simulate_user_approval: bool,
    scenario: Scenario | None = None,
) -> tuple[Manifest, dict[str, Any]]:
    """Run the fake provider flow. ``root`` must be a writable project workspace copy."""
    req = request_for_shot(manifest, shot_id, root)
    provider = FakeVideoProvider(
        clip_factory=FfmpegMockClipFactory(tc),
        work_dir=root / ".provider-mock",
        scenario=scenario or Scenario(),
    )
    log: dict[str, Any] = {
        "provider": provider.id,
        "MOCK": True,
        "shot": shot_id,
        "approvalSimulatedByHarness": simulate_user_approval,
        "capabilities": {
            "model": provider.get_capabilities().model_label,
            "pricingVerified": provider.get_capabilities().pricing_verified,
        },
    }
    quote = provider.quote(req)
    log["quote"] = {
        "usd(MOCK, not a real price)": quote.amount_usd,
        "billableMs": quote.billable_ms,
        "pricingConfig": quote.pricing_config_version,
    }
    approval = create_approval(quote, user_confirmed=simulate_user_approval, approval_id=f"demo-{shot_id}-1")
    ref = submit_once(provider, req, approval, sleep=lambda _s: None)
    claimed = poll_until_done(provider, ref, sleep=lambda _s: None)
    art = download_verified(provider, tc, ref, req, root / ".provider-mock" / "downloads")
    log["job"] = {
        "id": ref.job_id,
        "claimedSha256": claimed,
        "verifiedSha256": art.meta["sha256"],
        "durationMs": art.meta["durationMs"],
    }
    log["mockChargesMicroUsd"] = provider.total_charged_micro_usd
    log["submitCalls"] = provider.submit_calls

    rel = f"assets/generated/{shot_id}-mock.mp4"
    dest = resolve_in_root(root, rel)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(art.path, dest)
    new_manifest = attach_generated_clip(manifest, shot_id, rel, sha256_file(dest), approved=simulate_user_approval)
    return new_manifest, log
