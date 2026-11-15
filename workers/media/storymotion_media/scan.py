"""Scan a project drop-folder and register its media (hash, type guess, probed metadata).

Folder convention (see docs/BLENDER_HANDOFF.md):
  images/  full-frame pictures            -> type "environment"
  layers/  transparent cut-outs (PNG)     -> type "prop"       (change to "character" where it is one)
  audio/   narration / music / sfx        -> type "audio"
  clips/   videos rendered elsewhere      -> type "rendered_video"

Nothing is modified or uploaded. Provenance is left as TODO and ``licenseVerified=false`` on purpose:
the creator must state where each file came from before it can be used publicly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Any

from .contracts import AUDIO_EXT, IMAGE_EXT, VIDEO_EXT, Asset, Provenance
from .errors import MediaError, ToolchainError
from .ingest import probe_asset, resolve_in_root, sha256_file
from .toolchain import Toolchain, ffprobe_json

FOLDERS = {
    "images": ("environment", IMAGE_EXT),
    "layers": ("prop", IMAGE_EXT),
    "audio": ("audio", AUDIO_EXT),
    "clips": ("rendered_video", VIDEO_EXT),
}
ALPHA_FORMATS = ("rgba", "bgra", "argb", "abgr", "ya8", "pal8", "gbrap")


@dataclass
class ScanResult:
    assets: list[dict[str, Any]] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def slugify(stem: str, taken: set[str]) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")[:56] or "asset"
    if not base[0].isalnum():
        base = "a-" + base
    cand, n = base, 2
    while cand in taken:
        cand, n = f"{base}-{n}", n + 1
    taken.add(cand)
    return cand


def scan_project(tc: Toolchain, root: Any) -> ScanResult:
    res = ScanResult()
    taken: set[str] = set()
    for folder, (typ, exts) in FOLDERS.items():
        d = root / folder
        if not d.is_dir():
            continue
        for f in sorted(p for p in d.rglob("*") if p.is_file()):
            rel = PurePosixPath(*f.relative_to(root).parts).as_posix()
            if folder in ("images", "layers") and f.suffix.lower() in VIDEO_EXT:
                res.warnings.append(
                    f"{rel}: is a video in '{folder}/'; ignored here. Copy it to clips/ to use it as a clip."
                )
                continue
            if f.suffix.lower() not in exts:
                res.problems.append(f"{rel}: unsupported file type '{f.suffix}' for folder '{folder}/'")
                continue
            try:
                resolved = resolve_in_root(root, rel)
                aid = slugify(f.stem, taken)
                asset = Asset(
                    id=aid,
                    type=typ,
                    path=rel,
                    sha256=sha256_file(resolved),
                    provenance=Provenance(
                        kind="creator_supplied",
                        source="TODO: where did this file come from?",
                        license="TODO: licence / permission",
                        licenseVerified=False,
                    ),
                )
                info = probe_asset(tc, asset, root)
            except (MediaError, ValueError) as exc:
                res.problems.append(f"{rel}: {exc}")
                continue
            entry = asset.model_dump(mode="json")
            entry["_probe"] = info.as_dict()
            res.assets.append(entry)
            if folder == "layers":
                try:
                    pix = next(
                        (
                            s.get("pix_fmt", "")
                            for s in ffprobe_json(tc, resolved)["streams"]
                            if s["codec_type"] == "video"
                        ),
                        "",
                    )
                except ToolchainError:
                    pix = ""
                if pix not in ALPHA_FORMATS:
                    res.warnings.append(
                        f"{rel}: in layers/ but has no transparency (pixel format '{pix}'). "
                        "Export a PNG with an alpha channel, or it will cover the background."
                    )
            if folder == "images" and info.width and info.height:
                if info.width * 9 != info.height * 16:
                    res.warnings.append(f"{rel}: {info.width}x{info.height} is not 16:9; it will be cropped to fill")
                if info.width < 1920:
                    res.warnings.append(f"{rel}: {info.width}x{info.height} is below 1920x1080; it will be upscaled")
            if folder == "clips" and info.width and info.height and (info.width, info.height) != (1920, 1080):
                res.warnings.append(f"{rel}: clip is {info.width}x{info.height}, not 1920x1080 (scaled/cropped)")
            if folder == "clips" and info.fps and abs(info.fps - 24) > 0.01 and abs(info.fps - 30) > 0.01:
                res.warnings.append(f"{rel}: clip runs at {info.fps:.2f} fps (converted to the project fps)")
    narr = [a for a in res.assets if a["type"] == "audio"]
    if not narr:
        res.problems.append("no audio found: put the narration in audio/")
    return res
