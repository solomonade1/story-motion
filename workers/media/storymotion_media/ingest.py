"""Asset verification against a manifest: containment, hash, decodability, metadata.

Covers the Phase 0 slice of FR-MEDIA-002 / FR-PROJ-003 (missing media flagged, never a crash).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .contracts import Asset, Manifest
from .errors import FieldIssue, ManifestValidationError, MediaError, ToolchainError
from .toolchain import Toolchain, ffprobe_json, run

AUDIO_DURATION_TOLERANCE_MS = 50


@dataclass(frozen=True)
class AssetInfo:
    asset_id: str
    path: Path
    sha256: str
    size_bytes: int
    kind: str
    width: int | None = None
    height: int | None = None
    duration_ms: int | None = None
    sample_rate: int | None = None
    channels: int | None = None
    fps: float | None = None
    warnings: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.asset_id,
            "path": str(self.path.name),
            "sha256": self.sha256,
            "sizeBytes": self.size_bytes,
            "kind": self.kind,
            "width": self.width,
            "height": self.height,
            "durationMs": self.duration_ms,
            "sampleRate": self.sample_rate,
            "channels": self.channels,
            "fps": self.fps,
            "warnings": list(self.warnings),
        }


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_in_root(root: Path, rel: str) -> Path:
    """Resolve ``rel`` under ``root``; reject anything that escapes it (symlinks included)."""
    root_resolved = root.resolve()
    target = (root_resolved / rel).resolve()
    if not target.is_relative_to(root_resolved):
        raise MediaError(f"'{rel}' resolves outside the project root; refusing to read it")
    return target


def _frac(rate: str | None) -> float | None:
    if not rate or "/" not in rate:
        return None
    n, d = rate.split("/", 1)
    return float(n) / float(d) if float(d) else None


def decode_check(tc: Toolchain, path: Path, kind: str) -> str | None:
    """ffprobe only reads headers; a truncated/garbage file can still 'probe' fine (found by
    test_DATA04). Really decode: first frame for image/video, the whole stream for audio."""
    argv: list[str | Path] = [
        tc.ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-v",
        "error",
        "-xerror",
        "-protocol_whitelist",
        "file",
        "-i",
        path,
    ]
    argv += ["-frames:v", "1"] if kind in ("image", "video") else ["-vn"]
    proc = run([*argv, "-f", "null", "-"], timeout=300)
    if proc.returncode != 0 or proc.stderr.strip():
        return proc.stderr.strip().splitlines()[0][:200] if proc.stderr.strip() else f"exit {proc.returncode}"
    return None


def probe_asset(tc: Toolchain, asset: Asset, root: Path) -> AssetInfo:
    path = resolve_in_root(root, asset.path)
    if not path.is_file():
        raise MediaError(f"asset '{asset.id}' is missing: {asset.path} (relink or restore the file)")
    actual = sha256_file(path)
    if actual != asset.sha256:
        raise MediaError(
            f"asset '{asset.id}' ({asset.path}) changed on disk: sha256 {actual[:12]}… does not "
            f"match manifest {asset.sha256[:12]}… (stale approved renders must not be reused)"
        )
    try:
        data = ffprobe_json(tc, path)
    except ToolchainError as exc:
        raise MediaError(f"asset '{asset.id}' is corrupt or unsupported: {exc}") from exc
    streams = data.get("streams", [])
    vid = next((s for s in streams if s.get("codec_type") == "video"), None)
    aud = next((s for s in streams if s.get("codec_type") == "audio"), None)
    dur = data.get("format", {}).get("duration")
    duration_ms = round(float(dur) * 1000) if dur not in (None, "N/A") else None
    kind = asset.media_kind
    if vid is not None and (int(vid.get("width", 0)) <= 0 or int(vid.get("height", 0)) <= 0):
        raise MediaError(f"asset '{asset.id}' is corrupt or unsupported: zero-sized picture")
    problem = decode_check(tc, path, kind)
    if problem:
        raise MediaError(f"asset '{asset.id}' is corrupt or unsupported: cannot decode ({problem})")
    if kind in ("image", "video") and vid is None:
        raise MediaError(f"asset '{asset.id}' has no decodable video/image stream")
    if kind == "audio" and aud is None:
        raise MediaError(f"asset '{asset.id}' has no decodable audio stream")
    return AssetInfo(
        asset_id=asset.id,
        path=path,
        sha256=actual,
        size_bytes=path.stat().st_size,
        kind=kind,
        width=int(vid["width"]) if vid else None,
        height=int(vid["height"]) if vid else None,
        duration_ms=duration_ms if kind != "image" else None,
        sample_rate=int(aud["sample_rate"]) if aud else None,
        channels=int(aud["channels"]) if aud else None,
        fps=_frac(vid.get("avg_frame_rate")) if (vid and kind == "video") else None,
    )


def verify_manifest_assets(tc: Toolchain, manifest: Manifest, root: Path) -> dict[str, AssetInfo]:
    """Verify every asset; collect *all* problems instead of stopping at the first."""
    infos: dict[str, AssetInfo] = {}
    issues: list[FieldIssue] = []
    for i, asset in enumerate(manifest.assets):
        try:
            infos[asset.id] = probe_asset(tc, asset, root)
        except MediaError as exc:
            issues.append(FieldIssue(f"assets[{i}] ({asset.id})", str(exc)))
    nar = infos.get(manifest.narration.assetId)
    if nar and nar.duration_ms is not None:
        delta = abs(nar.duration_ms - manifest.narration.durationMs)
        if delta > AUDIO_DURATION_TOLERANCE_MS:
            issues.append(
                FieldIssue(
                    "narration.durationMs",
                    f"declared {manifest.narration.durationMs} ms but the audio file is "
                    f"{nar.duration_ms} ms (tolerance {AUDIO_DURATION_TOLERANCE_MS} ms)",
                )
            )
    if issues:
        raise ManifestValidationError(issues)
    return infos
