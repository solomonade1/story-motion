"""Transitions, clip trim/speed, audio beds and fades carried from the storyboard into the render."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from test_rendered_and_scan import make_clip
from test_studio_api import Client, server, wait_job  # noqa: F401  (fixture re-export)

from helpers import make_wav
from storymotion_media.studio.api import ApiServer
from storymotion_media.studio.render_service import RenderService
from storymotion_media.toolchain import Toolchain, run

pytestmark = pytest.mark.ffmpeg


def clip_shot(i: str, start: int, dur: int, clip: str, **kw: Any) -> dict[str, Any]:
    return {"id": i, "startMs": start, "durationMs": dur, "mode": "RENDERED", "clipAssetId": clip, **kw}


def setup(c: Client, root: Path, tc: Toolchain) -> dict[str, str]:
    src = root / "src"
    make_clip(tc, src / "clip.mp4", red_s=2.0, blue_s=2.0)  # 4 s
    make_wav(src / "voice.wav", 6.0)
    make_wav(src / "bed.wav", 8.0)
    pid = c.call("POST", "/api/projects", {"name": "Hezekiah"})[1]["projectId"]
    job = c.call(
        "POST", f"/api/projects/{pid}/assets/import",
        {"paths": [str(src / "clip.mp4"), str(src / "voice.wav"), str(src / "bed.wav")], "mode": "copy"},
    )[1]
    assert wait_job(c, pid, job["id"])["state"] == "completed"
    by = {a["orig_name"]: a["id"] for a in c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]}
    return {"pid": pid, "clip": by["clip.mp4"], "voice": by["voice.wav"], "bed": by["bed.wav"]}


def put(c: Client, ids: dict[str, str], shots: list[dict[str, Any]], **top: Any) -> dict[str, Any]:
    sb = {"narrationAssetId": ids["voice"], "scenes": [{"id": "s1", "title": "S", "shots": shots}], **top}
    st, view, _ = c.call("PUT", f"/api/projects/{ids['pid']}/storyboard", {"storyboard": sb})
    assert st == 200, view
    return view  # type: ignore[no-any-return]


def codes(view: dict[str, Any]) -> list[str]:
    return [d["code"] for d in view["diagnostics"]]


def test_transition_trim_speed_bed_and_fades_reach_the_manifest_and_the_render(
    server: tuple[ApiServer, Client, Path], tc: Toolchain  # noqa: F811
) -> None:
    srv, c, root = server
    ids = setup(c, root, tc)
    bed = {"assetId": ids["bed"], "role": "ambience", "gainDb": -18.0, "fadeInMs": 500, "fadeOutMs": 800, "duckDb": 12.0}
    view = put(
        c, ids,
        [
            clip_shot("a", 0, 2500, ids["clip"]),
            clip_shot("b", 2500, 3500, ids["clip"], transition={"type": "crossfade", "durationMs": 500}, trimStartMs=1000, fitSpeed=True),
        ],
        fadeInMs=300, fadeOutMs=600, audioTracks=[bed],
    )
    assert [d for d in view["diagnostics"] if d["severity"] != "info"] == []

    p = srv.ws.project(ids["pid"])
    manifest, _ = RenderService(p, srv.assets(ids["pid"]), tc).prepare()
    b = manifest.shots[1]
    assert (b.transition.type, b.transition.durationMs) == ("crossfade", 500)
    assert manifest.shots[0].transition.type == "cut"
    assert b.rendered is not None and b.rendered.trimStartMs == 1000
    assert b.rendered.speed == pytest.approx(0.857, abs=0.001)  # (4000-1000) ms of clip over a 3500 ms shot
    assert (manifest.video.fadeInMs, manifest.video.fadeOutMs) == (300, 600)
    assert manifest.audioTracks[0].duckDb == 12.0 and manifest.audioTracks[0].fadeOutMs == 800

    job = c.call("POST", f"/api/projects/{ids['pid']}/storyboard/render", {"draft": True})[1]
    done = wait_job(c, ids["pid"], job["id"])
    assert done["state"] == "completed", done
    mp4 = p.dir / "renders" / done["result"]["file"]
    probe = run([tc.ffprobe, "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", mp4], timeout=60)
    assert {s["codec_type"] for s in json.loads(probe.stdout)["streams"]} == {"video", "audio"}


def test_fit_speed_slows_a_short_clip_but_never_below_the_floor_or_above_normal(
    server: tuple[ApiServer, Client, Path], tc: Toolchain  # noqa: F811
) -> None:
    srv, c, root = server
    ids = setup(c, root, tc)
    p = srv.ws.project(ids["pid"])

    def speed_for(duration: int, trim: int = 0) -> float:
        put(c, ids, [clip_shot("a", 0, duration, ids["clip"], fitSpeed=True, trimStartMs=trim), clip_shot("b", duration, 6000 - duration, ids["clip"])])
        m, _ = RenderService(p, srv.assets(ids["pid"]), tc).prepare()
        assert m.shots[0].rendered is not None
        return m.shots[0].rendered.speed

    assert speed_for(5000) == pytest.approx(0.8, abs=0.01)  # 4 s clip stretched over 5 s
    assert speed_for(3000) == 1.0  # clip is long enough: never speeds up
    assert speed_for(5900) == pytest.approx(0.678, abs=0.001)  # 4000/5900, above the floor
    assert speed_for(4000, trim=2000) == 0.6  # 2000/4000 = 0.5 would be below the floor: clamped, last frame held


def test_bad_transitions_and_beds_are_refused_with_reasons(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    ids = setup(c, root, tc)
    url = f"/api/projects/{ids['pid']}/storyboard/render"
    fade = {"type": "crossfade", "durationMs": 500}

    view = put(c, ids, [clip_shot("a", 0, 3000, ids["clip"], transition=fade), clip_shot("b", 3000, 3000, ids["clip"])])
    assert "first-transition" in codes(view)
    assert c.call("POST", url, {"draft": True})[0] == 409

    view = put(c, ids, [clip_shot("a", 0, 5800, ids["clip"]), clip_shot("b", 5800, 300, ids["clip"], transition=fade)])
    assert "transition-too-long" in codes(view)
    assert "longer than a neighbouring shot (300 ms)" in c.call("POST", url, {"draft": True})[1]["error"]["message"]

    ok = [clip_shot("a", 0, 3000, ids["clip"]), clip_shot("b", 3000, 3000, ids["clip"], trimStartMs=9000)]
    assert "trim-past-clip" in codes(put(c, ids, ok))

    ok[1]["trimStartMs"] = 0
    assert "bed-is-narration" in codes(put(c, ids, ok, audioTracks=[{"assetId": ids["voice"]}]))
    assert "bed-after-narration" in codes(put(c, ids, ok, audioTracks=[{"assetId": ids["bed"], "startMs": 6500}]))
    assert c.call("POST", url, {"draft": True})[0] == 409
    assert codes(put(c, ids, ok, audioTracks=[{"assetId": ids["clip"]}])) == ["bed-not-audio"]


def test_invalid_transition_and_bed_values_are_refused_as_structure_errors(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    ids = setup(c, root, tc)
    base = f"/api/projects/{ids['pid']}/storyboard"

    def try_put(shot_patch: dict[str, Any], **top: Any) -> dict[str, Any]:
        sb = {"scenes": [{"id": "s1", "shots": [clip_shot("a", 0, 1000, ids["clip"], **shot_patch)]}], **top}
        st, err, _ = c.call("PUT", base, {"storyboard": sb})
        assert st == 422, err
        return err["error"]["issues"]  # type: ignore[no-any-return]

    assert "cut" in try_put({"transition": {"type": "cut", "durationMs": 200}})[0]["message"]
    assert "at least 100" in try_put({"transition": {"type": "crossfade", "durationMs": 20}})[0]["message"]
    assert try_put({"speed": 3.0})[0]["path"].endswith("speed")
    assert try_put({}, audioTracks=[{"assetId": ids["bed"], "gainDb": 40}])[0]["path"] == "audioTracks[0].gainDb"
    assert try_put({}, fadeInMs=-5)[0]["path"] == "fadeInMs"
    assert try_put({"transition": {"type": "wipe", "durationMs": 300}})[0]["path"].endswith("transition.type")


def test_a_storyboard_saved_before_this_version_still_opens(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    ids = setup(c, root, tc)
    old = {"storyboardVersion": "1.0.0", "narrationAssetId": ids["voice"], "characters": [],
           "scenes": [{"id": "s1", "title": "Old", "text": "", "characterIds": [], "shots": [
               {"id": "a", "startMs": 0, "durationMs": 6000, "mode": "RENDERED", "clipAssetId": ids["clip"]}]}]}
    st, view, _ = c.call("PUT", f"/api/projects/{ids['pid']}/storyboard", {"storyboard": old})
    assert st == 200
    shot = view["storyboard"]["scenes"][0]["shots"][0]
    assert shot["transition"] == {"type": "cut", "durationMs": 0} and shot["speed"] == 1.0 and view["storyboard"]["audioTracks"] == []
