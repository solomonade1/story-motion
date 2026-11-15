"""Builders for tiny synthetic projects used by fast tests (NOT the Jonah fixture)."""

from __future__ import annotations

import hashlib
import json
import math
import wave
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from storymotion_media.contracts import Manifest, parse_manifest
from storymotion_media.toolchain import Toolchain, run

PROV = {"kind": "synthetic", "source": "tests/helpers.py", "license": "CC0-1.0", "licenseVerified": True}


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def make_image(path: Path, hue: tuple[int, int, int], size: tuple[int, int] = (2560, 1440)) -> None:
    """Full-bleed textured image (diagonal stripes) so motion and black borders are detectable."""
    img = Image.new("RGB", size, hue)
    d = ImageDraw.Draw(img)
    for i in range(-size[1], size[0], 160):
        d.line([(i, 0), (i + size[1], size[1])], fill=tuple(min(255, c + 60) for c in hue), width=40)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)


def make_layer(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse([40, 40, 360, 360], fill=(250, 250, 20, 255))
    img.save(path)


def make_wav(path: Path, seconds: float, sr: int = 22050) -> None:
    n = int(sr * seconds)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(
            b"".join(
                int(8000 * math.sin(2 * math.pi * 220 * i / sr)).to_bytes(2, "little", signed=True) for i in range(n)
            )
        )


def asset(root: Path, aid: str, typ: str, rel: str) -> dict[str, Any]:
    return {"id": aid, "type": typ, "path": rel, "sha256": _sha(root / rel), "provenance": PROV}


def cam(s0: float = 1.0, s1: float = 1.3) -> dict[str, Any]:
    return {"start": {"scale": s0, "x": 0.5, "y": 0.5}, "end": {"scale": s1, "x": 0.6, "y": 0.5}, "easing": "linear"}


def make_project(
    root: Path,
    *,
    fps: int = 24,
    seconds: float = 6.0,
    shots: list[dict[str, Any]] | None = None,
    extra_assets: list[dict[str, Any]] | None = None,
    fade_ms: int = 0,
) -> Manifest:
    """3 shots by default: CINEMATIC (red), cut to STATIC (blue), cut to LAYERED (green)."""
    make_image(root / "img/a.png", (150, 40, 40))
    make_image(root / "img/b.png", (40, 60, 160))
    make_image(root / "img/c.png", (40, 140, 60))
    make_layer(root / "img/dot.png")
    make_wav(root / "audio/n.wav", seconds)
    total = int(seconds * 1000)
    third = total // 3
    default_shots: list[dict[str, Any]] = [
        {
            "id": "s1",
            "sceneId": "sc",
            "startMs": 0,
            "durationMs": third,
            "mode": "CINEMATIC",
            "sourceAssetIds": ["a"],
            "camera": cam(),
        },
        {"id": "s2", "sceneId": "sc", "startMs": third, "durationMs": third, "mode": "STATIC", "sourceAssetIds": ["b"]},
        {
            "id": "s3",
            "sceneId": "sc",
            "startMs": 2 * third,
            "durationMs": total - 2 * third,
            "mode": "LAYERED",
            "sourceAssetIds": ["c"],
            "layers": [
                {
                    "assetId": "dot",
                    "start": {"x": 0.2, "y": 0.5, "widthFrac": 0.2},
                    "end": {"x": 0.8, "y": 0.5, "widthFrac": 0.2},
                    "swayDeg": 5,
                }
            ],
        },
    ]
    sh = shots if shots is not None else default_shots
    doc = {
        "schemaVersion": "1.0.0",
        "projectId": "mini",
        "title": "mini",
        "video": {"width": 1920, "height": 1080, "fps": fps, "fadeInMs": fade_ms, "fadeOutMs": fade_ms},
        "narration": {"assetId": "n", "durationMs": total},
        "assets": [
            asset(root, "n", "audio", "audio/n.wav"),
            asset(root, "a", "environment", "img/a.png"),
            asset(root, "b", "environment", "img/b.png"),
            asset(root, "c", "environment", "img/c.png"),
            asset(root, "dot", "prop", "img/dot.png"),
            *(extra_assets or []),
        ],
        "scenes": [
            {
                "id": "sc",
                "title": "t",
                "narration": {"startMs": sh[0]["startMs"], "endMs": sh[-1]["startMs"] + sh[-1]["durationMs"]},
                "shotIds": [s["id"] for s in sh],
            }
        ],
        "shots": sh,
    }
    return parse_manifest(json.dumps(doc))


def frame_png(tc: Toolchain, video: Path, n: int, out: Path) -> Image.Image:
    proc = run(
        [
            tc.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            video,
            "-vf",
            f"select='eq(n,{n})'",
            "-frames:v",
            "1",
            out,
        ],
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return Image.open(out).convert("RGB")


def mean_rgb(img: Image.Image) -> tuple[float, float, float]:
    px = (
        list(img.resize((32, 18)).get_flattened_data())
        if hasattr(img, "get_flattened_data")
        else list(img.resize((32, 18)).getdata())
    )
    n = len(px)
    return tuple(sum(p[i] for p in px) / n for i in range(3))  # type: ignore[return-value]
