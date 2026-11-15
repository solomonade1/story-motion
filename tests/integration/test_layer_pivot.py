"""Layer pivot points (QG ANIM-02): rotation turns about the chosen pivot, and the default stays the old behaviour."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from helpers import frame_png, make_project
from storymotion_media.contracts import parse_manifest
from storymotion_media.errors import ManifestValidationError
from storymotion_media.render import RenderOptions, render
from storymotion_media.toolchain import Toolchain

pytestmark = pytest.mark.ffmpeg
W, H = 640, 360  # draft size


def yellow_centroid(img: Image.Image) -> tuple[float, float]:
    pts = [
        (x, y)
        for x in range(0, img.size[0], 2)
        for y in range(0, img.size[1], 2)
        if (p := img.getpixel((x, y)))[0] > 200 and p[1] > 200 and p[2] < 90
    ]
    assert pts, "no yellow layer visible"
    return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)


def centroid_for(tc: Toolchain, tmp: Path, name: str, rotate: float, pivot: tuple[float, float] | None) -> tuple[float, float]:
    layer: dict[str, Any] = {
        "assetId": "dot",
        "start": {"x": 0.5, "y": 0.4, "widthFrac": 0.2, "rotateDeg": rotate},
        "end": {"x": 0.5, "y": 0.4, "widthFrac": 0.2, "rotateDeg": rotate},
    }
    if pivot:
        layer |= {"pivotX": pivot[0], "pivotY": pivot[1]}
    shots = [{"id": "s1", "sceneId": "sc", "startMs": 0, "durationMs": 3000, "mode": "LAYERED", "sourceAssetIds": ["c"], "layers": [layer]}]
    root = tmp / name
    m = make_project(root, shots=shots, seconds=3.0)
    out = tmp / f"{name}.mp4"
    render(m, root, out, RenderOptions(draft=True), tc)
    return yellow_centroid(frame_png(tc, out, 30, tmp / f"{name}.png"))


def test_pivot_turns_the_layer_about_the_chosen_point(tc: Toolchain, tmp_path: Path) -> None:
    layer_w = 0.2 * W  # 128 px; the layer is square
    px, py = 0.5 * W, 0.4 * H
    # centre pivot (the default): rotating does not move the layer
    cx, cy = centroid_for(tc, tmp_path, "centre", 90, None)
    assert (cx, cy) == pytest.approx((px, py), abs=3)
    # pivot at the layer's LEFT edge: at 0 deg the layer sits to the right of the pivot...
    cx, cy = centroid_for(tc, tmp_path, "left0", 0, (0.0, 0.5))
    assert (cx, cy) == pytest.approx((px + layer_w / 2, py), abs=3)
    # ...and a 90 deg clockwise turn about the pivot swings it BELOW the pivot
    cx, cy = centroid_for(tc, tmp_path, "left90", 90, (0.0, 0.5))
    assert (cx, cy) == pytest.approx((px, py + layer_w / 2), abs=3)
    # 180 deg: it ends up to the left
    cx, cy = centroid_for(tc, tmp_path, "left180", 180, (0.0, 0.5))
    assert (cx, cy) == pytest.approx((px - layer_w / 2, py), abs=3)
    # a top-edge pivot at 90 deg swings it to the left of the pivot
    cx, cy = centroid_for(tc, tmp_path, "top90", 90, (0.5, 0.0))
    assert (cx, cy) == pytest.approx((px - layer_w / 2, py), abs=3)


def test_pivot_values_outside_the_picture_are_refused(tmp_path: Path) -> None:
    base = make_project(tmp_path / "p", seconds=3.0).model_dump(mode="json")
    layered = next(s for s in base["shots"] if s["mode"] == "LAYERED")
    layered["layers"][0]["pivotX"] = 1.5
    import json

    with pytest.raises(ManifestValidationError) as ei:
        parse_manifest(json.dumps(base))
    assert any(i.path.endswith("pivotX") for i in ei.value.issues)
