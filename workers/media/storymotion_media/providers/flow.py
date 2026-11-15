"""Safe client-side flow around any provider: bounded retries, reconciliation, verified download.

Policy (FR-AI-005, QG COST-05/06, F-04, F-14):
- A *transport retry* is only allowed for errors that prove the job was NOT accepted (429/outage),
  is bounded, and re-uses the same approval. It never creates a new billable attempt.
- A submit timeout means "maybe accepted": look the job up by approval id; if that is impossible
  raise AmbiguousSubmission and make NO further submission.
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from pathlib import Path

from ..toolchain import Toolchain, ffprobe_json
from .base import (
    AmbiguousSubmission,
    AnimationRequest,
    Approval,
    IntegrityError,
    LocalArtifact,
    ProviderUnavailable,
    RateLimited,
    RemoteJobRef,
    SubmitTimeout,
    UnsupportedOperation,
    VideoGenerationProvider,
)

MAX_TRANSPORT_RETRIES = 2


def submit_once(
    provider: VideoGenerationProvider,
    request: AnimationRequest,
    approval: Approval,
    *,
    sleep: Callable[[float], None] = time.sleep,
) -> RemoteJobRef:
    attempt = 0
    while True:
        try:
            return provider.submit(request, approval)
        except (RateLimited, ProviderUnavailable):
            attempt += 1
            if attempt > MAX_TRANSPORT_RETRIES:
                raise
            sleep(min(2.0 * 2 ** (attempt - 1), 30.0))  # backoff; same approval, same job
        except SubmitTimeout as exc:
            try:
                ref = provider.lookup_by_approval(approval.approval_id)
            except UnsupportedOperation:
                ref = None
            if ref is None:
                raise AmbiguousSubmission(
                    "submit timed out and the job could not be confirmed; automatic resubmission "
                    "is blocked until the provider side is reconciled by the user"
                ) from exc
            return ref


def poll_until_done(
    provider: VideoGenerationProvider,
    ref: RemoteJobRef,
    *,
    max_polls: int = 20,
    sleep: Callable[[float], None] = time.sleep,
) -> str | None:
    """Return the provider-claimed sha256 once completed; raise on failure or poll exhaustion."""
    for _ in range(max_polls):
        st = provider.get_status(ref)
        if st.state == "completed":
            return st.result_sha256
        if st.state == "failed":
            raise IntegrityError(f"generation failed: {st.error}")
        sleep(0.0)
    raise IntegrityError("generation did not finish within the poll budget; job left for reconciliation")


def download_verified(
    provider: VideoGenerationProvider,
    tc: Toolchain,
    ref: RemoteJobRef,
    request: AnimationRequest,
    dest_dir: Path,
) -> LocalArtifact:
    art = provider.download(ref, dest_dir)
    actual = hashlib.sha256(art.path.read_bytes()).hexdigest()
    if art.claimed_sha256 and actual != art.claimed_sha256:
        art.path.unlink(missing_ok=True)
        raise IntegrityError("downloaded file hash differs from the provider's checksum; clip rejected")
    try:
        data = ffprobe_json(tc, art.path)
    except Exception as exc:
        art.path.unlink(missing_ok=True)
        raise IntegrityError(f"downloaded clip is not decodable: {exc}") from exc
    vid = next((s for s in data["streams"] if s["codec_type"] == "video"), None)
    if vid is None or (int(vid["width"]), int(vid["height"])) != (request.width, request.height):
        art.path.unlink(missing_ok=True)
        raise IntegrityError("clip resolution differs from the request; clip rejected")
    dur_ms = float(data["format"]["duration"]) * 1000
    if abs(dur_ms - request.duration_ms) > 250:
        art.path.unlink(missing_ok=True)
        raise IntegrityError(f"clip is {dur_ms:.0f} ms but {request.duration_ms} ms was requested")
    return LocalArtifact(art.path, actual, art.is_mock, {**art.meta, "sha256": actual, "durationMs": round(dur_ms)})
