"""Deterministic FAKE hosted-video provider (FX-06). It never touches the network.

Every number here (price, durations, limits) is a MOCK value invented for tests. A pass against
this class proves app logic only - NOT live pricing, quality or billing semantics (Charter B3/E5).
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..errors import FieldIssue
from .base import (
    MICRO,
    AnimationRequest,
    Approval,
    ApprovalInvalid,
    CostQuote,
    GenerationStatus,
    LocalArtifact,
    PricingUnavailable,
    ProviderCapabilities,
    ProviderUnavailable,
    RateLimited,
    RemoteJobRef,
    RequestValidationError,
    SubmitTimeout,
    UnsupportedOperation,
)

ClipFactory = Callable[[AnimationRequest, Path], None]


@dataclass
class Scenario:
    submit: Literal["ok", "lost_response", "rate_limited_once", "outage"] = "ok"
    job: Literal["success", "fail"] = "success"
    corrupt_download: bool = False
    polls_to_complete: int = 2


@dataclass
class _Job:
    job_id: str
    request: AnimationRequest
    approval_id: str
    quote_amount: int
    polls: int = 0
    cancelled: bool = False
    result_path: Path | None = None
    result_sha: str | None = None


@dataclass(frozen=True)
class ChargeEvent:
    job_id: str
    amount_micro_usd: int
    note: str = "MOCK provider-side charge"


@dataclass
class FakeVideoProvider:
    clip_factory: ClipFactory
    work_dir: Path
    scenario: Scenario = field(default_factory=Scenario)
    clock: Callable[[], float] = time.monotonic
    pricing_config_version: str | None = "mock-pricing-v0"
    price_micro_usd_per_second: int | None = 50_000  # $0.05/s - NOT a real price
    min_billable_ms: int = 3000
    quote_ttl_s: float = 300.0
    supports_cancel: bool = True
    supports_idempotent_lookup: bool = True
    id: str = "mock-video"

    def __post_init__(self) -> None:
        self._quotes: dict[str, CostQuote] = {}
        self._jobs: dict[str, _Job] = {}
        self._by_approval: dict[str, str] = {}
        self._rate_limit_spent = False
        self.charges: list[ChargeEvent] = []
        self.submit_calls = 0
        self.work_dir.mkdir(parents=True, exist_ok=True)

    # -- capabilities
    def get_capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_id=self.id,
            model_label="fake-i2v-v0 (MOCK, not a real model)",
            image_formats=(".png", ".jpg", ".jpeg", ".webp"),
            max_source_images=2,
            durations_ms=(3000, 4000, 5000, 6000, 8000, 10000),
            resolutions=((1280, 720), (1920, 1080)),
            supports_negative_prompt=True,
            supports_cancel=self.supports_cancel,
            supports_idempotent_lookup=self.supports_idempotent_lookup,
            price_micro_usd_per_second=self.price_micro_usd_per_second,
            min_billable_ms=self.min_billable_ms,
            pricing_config_version=self.pricing_config_version,
            pricing_verified=False,
            warnings=("Mock provider: identity/physics constraints are not enforced (FR-AI-007).",),
        )

    def _validate(self, req: AnimationRequest) -> None:
        caps, issues = self.get_capabilities(), []
        if not req.prompt.strip():
            issues.append(FieldIssue("prompt", "must not be empty"))
        if len(req.prompt) > 2000:
            issues.append(FieldIssue("prompt", "longer than 2000 characters"))
        if req.negative_prompt and not caps.supports_negative_prompt:
            issues.append(FieldIssue("negative_prompt", "not supported by this provider"))
        if not 1 <= len(req.sources) <= caps.max_source_images:
            issues.append(FieldIssue("sources", f"need 1..{caps.max_source_images} images"))
        for i, s in enumerate(req.sources):
            if s.path.suffix.lower() not in caps.image_formats:
                issues.append(FieldIssue(f"sources[{i}]", f"unsupported format {s.path.suffix}"))
        if req.duration_ms not in caps.durations_ms:
            issues.append(FieldIssue("duration_ms", f"{req.duration_ms} not in {caps.durations_ms}"))
        if (req.width, req.height) not in caps.resolutions:
            issues.append(FieldIssue("resolution", f"{req.width}x{req.height} not in {caps.resolutions}"))
        if issues:
            raise RequestValidationError(issues)

    # -- quote
    def quote(self, request: AnimationRequest) -> CostQuote:
        self._validate(request)
        if self.price_micro_usd_per_second is None or self.pricing_config_version is None:
            raise PricingUnavailable("price unknown or ambiguous; refusing to quote (fail closed)")
        billable = max(request.duration_ms, self.min_billable_ms)
        amount = self.price_micro_usd_per_second * billable // 1000
        qid = "q-" + hashlib.sha256(f"{request.request_hash()}|{len(self._quotes)}".encode()).hexdigest()[:12]
        q = CostQuote(
            quote_id=qid,
            request_hash=request.request_hash(),
            amount_micro_usd=amount,
            currency="USD",
            pricing_config_version=self.pricing_config_version,
            expires_at=self.clock() + self.quote_ttl_s,
            billable_ms=billable,
            is_mock=True,
        )
        self._quotes[qid] = q
        return q

    # -- submit (idempotent per approval id)
    def submit(self, request: AnimationRequest, approval: Approval) -> RemoteJobRef:
        self.submit_calls += 1
        q = self._quotes.get(approval.quote_id)
        if not approval.approval_id or q is None:
            raise ApprovalInvalid("approval does not reference a known quote")
        if q.request_hash != request.request_hash() or approval.request_hash != q.request_hash:
            raise ApprovalInvalid("approval/quote were issued for a different request")
        if self.clock() > q.expires_at:
            raise ApprovalInvalid("quote expired; request and approve a fresh quote")
        if approval.max_micro_usd < q.amount_micro_usd:
            raise ApprovalInvalid("approved maximum is below the quoted amount")
        self._validate(request)

        existing = self._by_approval.get(approval.approval_id)
        if existing:  # same approval => same attempt; never a second charge
            return RemoteJobRef(self.id, existing, q.request_hash)
        if self.scenario.submit == "outage":
            raise ProviderUnavailable("provider outage (mock)")
        if self.scenario.submit == "rate_limited_once" and not self._rate_limit_spent:
            self._rate_limit_spent = True
            raise RateLimited("429 Too Many Requests (mock)")

        job_id = "job-" + hashlib.sha256(approval.approval_id.encode()).hexdigest()[:10]
        self._jobs[job_id] = _Job(job_id, request, approval.approval_id, q.amount_micro_usd)
        self._by_approval[approval.approval_id] = job_id
        self.charges.append(ChargeEvent(job_id, q.amount_micro_usd))
        if self.scenario.submit == "lost_response":
            raise SubmitTimeout("timed out waiting for the submit response (mock: job WAS accepted)")
        return RemoteJobRef(self.id, job_id, q.request_hash)

    def lookup_by_approval(self, approval_id: str) -> RemoteJobRef | None:
        if not self.supports_idempotent_lookup:
            raise UnsupportedOperation("provider has no idempotent lookup")
        job_id = self._by_approval.get(approval_id)
        if job_id is None:
            return None
        return RemoteJobRef(self.id, job_id, self._jobs[job_id].request.request_hash())

    # -- status / download
    def get_status(self, ref: RemoteJobRef) -> GenerationStatus:
        job = self._jobs[ref.job_id]
        if job.cancelled:
            return GenerationStatus("failed", 0.0, "cancelled")
        job.polls += 1
        if job.polls < self.scenario.polls_to_complete:
            frac = job.polls / self.scenario.polls_to_complete
            return GenerationStatus("queued" if job.polls == 1 else "generating", frac)
        if self.scenario.job == "fail":
            return GenerationStatus("failed", 1.0, "mock generation failure")
        if job.result_path is None:
            out = self.work_dir / f"{job.job_id}.mp4"
            self.clip_factory(job.request, out)
            job.result_path = out
            job.result_sha = hashlib.sha256(out.read_bytes()).hexdigest()
        return GenerationStatus("completed", 1.0, None, job.result_sha)

    def download(self, ref: RemoteJobRef, dest_dir: Path) -> LocalArtifact:
        job = self._jobs[ref.job_id]
        if job.result_path is None:
            raise UnsupportedOperation("job has no result yet; poll status first")
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / f"{job.job_id}.mp4"
        data = job.result_path.read_bytes()
        if self.scenario.corrupt_download:
            data = data[: len(data) // 2]  # truncated transfer
        dest.write_bytes(data)
        return LocalArtifact(dest, job.result_sha, True, {"jobId": job.job_id, "mock": True})

    def cancel(self, ref: RemoteJobRef) -> None:
        if not self.supports_cancel:
            raise UnsupportedOperation("this provider does not support cancellation; the charge stands")
        self._jobs[ref.job_id].cancelled = True

    # -- test/oracle helpers
    @property
    def total_charged_micro_usd(self) -> int:
        return sum(c.amount_micro_usd for c in self.charges)

    @staticmethod
    def usd(micro: int) -> str:
        return f"${micro // MICRO}.{micro % MICRO:06d}"
