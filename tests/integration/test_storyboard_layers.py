"""LAYERED shots in the storyboard: model, diagnostics, save/reopen, and a real render (FR-ANIM-002, QG ANIM-02)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from test_studio_api import Client, server, wait_job  # noqa: F401  (fixture re-export)

from helpers import frame_png, make_image, make_layer, make_wav
from storymotion_media.errors import ManifestValidationError
from storymotion_media.studio.api import ApiServer
from storymotion_media.studio.render_service import RenderService
from storymotion_media.studio.storyboard import diagnose, parse_storyboard
from storymotion_media.toolchain import Toolchain

NAR, BG, LAY = "a-0000000000aa", "a-0000000000b1", "a-0000000000b2"
LIB = {NAR: {"kind": "audio", "status": "ok"}, BG: {"kind": "image", "status": "ok"}, LAY: {"kind": "image", "status": "ok"}}


def pose(x: float, y: float, w: float = 0.2, rot: float = 0.0) -> dict[str, Any]:
    return {"x": x, "y": y, "widthFrac": w, "rotateDeg": rot}


def layer(**kw: Any) -> dict[str, Any]:
    return {"assetId": LAY, "start": pose(0.2, 0.5), "end": pose(0.8, 0.5), **kw}


def board(*layers: dict[str, Any], mode: str = "LAYERED") -> Any:
    shot = {"id": "a", "startMs": 0, "durationMs": 3000, "mode": mode, "imageAssetId": BG, "layers": list(layers)}
    return parse_storyboard({"narrationAssetId": NAR, "scenes": [{"id": "s", "shots": [shot]}]})


def codes(sb: Any) -> list[str]:
    return [d["code"] for d in diagnose(sb, narration_ms=3000, assets=LIB)]


# ---------------------------------------------------------------- model + diagnostics (no FFmpeg)
@pytest.mark.parametrize(
    ("patch", "path_end"),
    [
        ({"start": pose(2.0, 0.5)}, "start.x"),
        ({"start": pose(0.5, 0.5, 0.0)}, "start.widthFrac"),
        ({"end": pose(0.5, 0.5, 0.2, 400)}, "end.rotateDeg"),
        ({"pivotX": 1.2}, "pivotX"),
        ({"pivotY": -0.1}, "pivotY"),
        ({"swayDeg": 90}, "swayDeg"),
        ({"easing": "bounce"}, "easing"),
        ({"assetId": "../x"}, "assetId"),
    ],
)
def test_bad_layer_values_are_refused_with_the_field_path(patch: dict[str, Any], path_end: str) -> None:
    with pytest.raises(ManifestValidationError) as ei:
        board(layer(**patch))
    assert any(i.path.startswith("scenes[0].shots[0].layers[0]") and i.path.endswith(path_end) for i in ei.value.issues)


def test_layered_diagnostics() -> None:
    assert codes(board(layer())) == []
    assert codes(board()) == ["no-layers"]  # blocks rendering (see test below)
    assert codes(board(layer(assetId="a-0000000000ff"))) == ["layer-missing"]
    assert codes(board(layer(assetId=NAR))) == ["layer-not-image"]
    lib = {**LIB, LAY: {"kind": "image", "status": "missing"}}
    assert [d["code"] for d in diagnose(board(layer()), narration_ms=3000, assets=lib)] == ["layer-unavailable"]
    assert codes(board(layer(), mode="STATIC")) == ["layers-ignored"]


def test_layers_round_trip_with_every_field() -> None:
    sb = board(layer(pivotX=0.1, pivotY=0.9, swayDeg=6, swayPeriodMs=2500, easing="linear"))
    again = parse_storyboard(sb.model_dump())
    ly = again.scenes[0].shots[0].layers[0]
    assert (ly.pivotX, ly.pivotY, ly.swayDeg, ly.swayPeriodMs, ly.easing) == (0.1, 0.9, 6, 2500, "linear") and again == sb


# ---------------------------------------------------------------- over the API, with a real render
@pytest.mark.ffmpeg
def test_layered_shot_saves_reopens_renders_and_the_layer_moves_about_its_pivot(
    server: tuple[ApiServer, Client, Path], tc: Toolchain  # noqa: F811
) -> None:
    srv, c, root = server
    src = root / "src"
    make_image(src / "bg.png", (40, 140, 60), size=(1920, 1080))
    make_layer(src / "dot.png")  # yellow disc on transparency
    make_wav(src / "voice.wav", 3.0)
    pid = c.call("POST", "/api/projects", {"name": "Layers"})[1]["projectId"]
    paths = [str(src / "bg.png"), str(src / "dot.png"), str(src / "voice.wav")]
    assert wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": paths})[1]["id"])["state"] == "completed"
    by = {a["orig_name"]: a["id"] for a in c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]}
    base = f"/api/projects/{pid}/storyboard"

    def put(layers: list[dict[str, Any]], **shot_extra: Any) -> dict[str, Any]:
        shot = {"id": "a", "startMs": 0, "durationMs": 3000, "mode": "LAYERED", "imageAssetId": by["bg.png"], "layers": layers, **shot_extra}
        st, view, _ = c.call("PUT", base, {"storyboard": {"narrationAssetId": by["voice.wav"], "scenes": [{"id": "s", "shots": [shot]}]}})
        assert st == 200, view
        return view  # type: ignore[no-any-return]

    # a LAYERED shot with no layer is refused with the reason
    put([])
    st, err, _ = c.call("POST", base + "/render", {"draft": True})
    assert st == 409 and "at least one layer" in err["error"]["message"]

    ly = {"assetId": by["dot.png"], "start": pose(0.5, 0.4, 0.2, 0), "end": pose(0.5, 0.4, 0.2, 90), "pivotX": 0.0, "pivotY": 0.5, "easing": "linear"}
    view = put([ly])
    assert [d for d in view["diagnostics"] if d["severity"] != "info"] == []
    assert c.call("GET", base)[1]["storyboard"] == view["storyboard"]  # save/reopen reproduces every layer field

    m, _notes = RenderService(srv.ws.project(pid), srv.assets(pid), tc).prepare()
    lm = m.shots[0].layers[0]
    assert (lm.pivotX, lm.pivotY, lm.easing, lm.end.rotateDeg) == (0.0, 0.5, "linear", 90) and m.shots[0].camera is None

    done = wait_job(c, pid, c.call("POST", base + "/render", {"draft": True})[1]["id"])
    assert done["state"] == "completed", done
    mp4 = srv.ws.project(pid).dir / "renders" / done["result"]["file"]

    def centroid(frame: int) -> tuple[float, float]:
        img: Image.Image = frame_png(tc, mp4, frame, root / f"f{frame}.png")
        pts = [(x, y) for x in range(0, img.size[0], 2) for y in range(0, img.size[1], 2)
               if (p := img.getpixel((x, y)))[0] > 200 and p[1] > 200 and p[2] < 90]
        assert pts
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    (x0, y0), (x1, y1) = centroid(2), centroid(68)  # start (0 deg) and near the end (about 90 deg clockwise)
    assert x0 > 640 * 0.5 + 40 and abs(y0 - 0.4 * 360) < 6  # at the start the disc sits to the right of its pivot
    assert y1 > y0 + 30 and x1 < x0 - 30  # it has swung down and in about the pivot: not just spun in place


@pytest.mark.ffmpeg
def test_layer_preview_keeps_transparency_and_is_removed_with_the_asset(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    import io

    srv, c, root = server
    src = root / "src"
    make_layer(src / "dot.png")  # yellow disc, transparent corners
    make_wav(src / "voice.wav", 1.0)
    pid = c.call("POST", "/api/projects", {"name": "Alpha"})[1]["projectId"]
    paths = [str(src / "dot.png"), str(src / "voice.wav")]
    assert wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": paths})[1]["id"])["state"] == "completed"
    by = {a["orig_name"]: a["id"] for a in c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]}
    url = f"/api/projects/{pid}/assets/{by['dot.png']}/alpha?token={srv.token}"
    st, body, h = c.call("GET", url, token=None)
    assert st == 200 and h["content-type"] == "image/png"
    img = Image.open(io.BytesIO(body))
    assert img.mode == "RGBA" and img.getpixel((2, 2))[3] == 0 and img.getpixel((img.size[0] // 2, img.size[1] // 2))[3] == 255
    assert c.call("GET", f"/api/projects/{pid}/assets/{by['dot.png']}/alpha", token=None)[0] == 401  # token still required
    assert c.call("GET", f"/api/projects/{pid}/assets/{by['voice.wav']}/alpha?token={srv.token}", token=None)[0] == 404
    cached = srv.ws.project(pid).dir / "previews" / f"{by['dot.png']}.png"
    assert cached.is_file()
    assert c.call("DELETE", f"/api/projects/{pid}/assets/{by['dot.png']}")[0] == 200
    assert not cached.exists()
