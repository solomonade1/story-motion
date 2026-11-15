"""Provider-neutral cloud video-generation boundary (PRD 11.3, FR-AI-001..005).

Nothing here is specific to any vendor; no provider fields leak into the manifest (the manifest
only stores ``providerProfileId`` and an already-downloaded clip asset). Money is integer
micro-USD so there is no binary-float accounting (Charter C2).

Phase 0 scope: contract + fake provider only. The reservation ledger, spend caps, secrets storage
and live adapter are Phase 4; the pieces below that touch money are intentionally minimal.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Protocol

from ..errors import FieldIssue, StoryMotionError

MICRO = 1_000_000  # micro-USD per USD


# ------------------------------------------------------------------ errors
class ProviderError(StoryMotionError):
    """Base class for provider failures."""


class RequestValidationError(ProviderError):
    def __init__(self, issues: list[FieldIssue]) -> None:
        self.issues = issues
        super().__init__("Request rejected before any submission:\n" + "\n".join(f"  - {i}" for i in issues))


class PricingUnavailable(ProviderError):
    """Unknown/stale pricing: fail closed, never submit (FR-BUD-007)."""


class ApprovalInvalid(ProviderError):
    """Missing, mismatched, reused-for-another-request or stale approval/quote (FR-BUD-005)."""


class SubmitTimeout(ProviderError):
    """Transport timeout; the provider MAY have accepted the job. Reconcile, never blind-retry."""


class RateLimited(ProviderError):
    """HTTP 429-style: definitely not accepted."""


class ProviderUnavailable(ProviderError):
    """Outage: definitely not accepted."""


class AmbiguousSubmission(ProviderError):
    """Acceptance state unknown. Further paid submissions must stay blocked (COST-06)."""


class IntegrityError(ProviderError):
    """Downloaded artifact failed hash or media validation (QG F-07/F-14)."""


class UnsupportedOperation(ProviderError):
    pass


# ------------------------------------------------------------------ data
@dataclass(frozen=True)
class ProviderCapabilities:
    provider_id: str
    model_label: str
    image_formats: tuple[str, ...]
    max_source_images: int
    durations_ms: tuple[int, ...]  # allowed request durations
    resolutions: tuple[tuple[int, int], ...]
    supports_negative_prompt: bool
    supports_cancel: bool
    supports_idempotent_lookup: bool
    price_micro_usd_per_second: int | None  # None = unknown -> quotes fail closed
    min_billable_ms: int
    pricing_config_version: str | None
    pricing_verified: bool  # True only after checking the provider's own published pricing
    warnings: tuple[str, ...] = ()  # FR-AI-007: constraints that may not be enforceable


@dataclass(frozen=True)
class SourceImage:
    path: Path
    sha256: str


@dataclass(frozen=True)
class AnimationRequest:
    shot_id: str
    sources: tuple[SourceImage, ...]
    prompt: str
    duration_ms: int
    width: int
    height: int
    negative_prompt: str = ""
    seed: int | None = None

    def request_hash(self) -> str:
        canon = {
            "shot": self.shot_id,
            "src": [s.sha256 for s in self.sources],
            "p": self.prompt,
            "n": self.negative_prompt,
            "d": self.duration_ms,
            "w": self.width,
            "h": self.height,
            "seed": self.seed,
        }
        return hashlib.sha256(json.dumps(canon, sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class CostQuote:
    quote_id: str
    request_hash: str
    amount_micro_usd: int
    currency: str
    pricing_config_version: str
    expires_at: float
    billable_ms: int
    is_mock: bool

    @property
    def amount_usd(self) -> str:
        return f"{self.amount_micro_usd // MICRO}.{self.amount_micro_usd % MICRO:06d}"


@dataclass(frozen=True)
class Approval:
    """Created ONLY after explicit user confirmation (PRD 11.3 ``approvalId``)."""

    approval_id: str
    quote_id: str
    request_hash: str
    max_micro_usd: int


def create_approval(quote: CostQuote, *, user_confirmed: bool, approval_id: str) -> Approval:
    if not user_confirmed:
        raise ApprovalInvalid("explicit user confirmation is required before any billable request")
    if not approval_id:
        raise ApprovalInvalid("approval_id must be non-empty")
    return Approval(approval_id, quote.quote_id, quote.request_hash, quote.amount_micro_usd)


@dataclass(frozen=True)
class RemoteJobRef:
    provider_id: str
    job_id: str
    request_hash: str


@dataclass(frozen=True)
class GenerationStatus:
    state: Literal["queued", "generating", "completed", "failed"]
    progress: float = 0.0
    error: str | None = None
    result_sha256: str | None = None  # provider-claimed checksum of the result


@dataclass(frozen=True)
class LocalArtifact:
    path: Path
    claimed_sha256: str | None
    is_mock: bool
    meta: dict[str, object] = field(default_factory=dict)


class VideoGenerationProvider(Protocol):
    id: str

    def get_capabilities(self) -> ProviderCapabilities: ...
    def quote(self, request: AnimationRequest) -> CostQuote: ...
    def submit(self, request: AnimationRequest, approval: Approval) -> RemoteJobRef: ...
    def lookup_by_approval(self, approval_id: str) -> RemoteJobRef | None: ...
    def get_status(self, ref: RemoteJobRef) -> GenerationStatus: ...
    def download(self, ref: RemoteJobRef, dest_dir: Path) -> LocalArtifact: ...
    def cancel(self, ref: RemoteJobRef) -> None: ...
