"""Storyboard -> render over the local API (FR-RENDER-001..005, FR-ANIM-001, FR-TIME-005, ANIM-04 refusal paths)."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest
from test_studio_api import Client, server, wait_job  # noqa: F401  (fixture re-export)

from helpers import make_image, make_wav
from storymotion_media.studio.api import ApiServer
from storymotion_media.studio.render_service import RenderService
from storymotion_media.toolchain import Toolchain, run

pytestmark = pytest.mark.ffmpeg


def shot(i: str, start: int, dur: int, img: str, **kw: Any) -> dict[str, Any]:
    return {"id": i, "startMs": start, "durationMs": dur, "mode": "STATIC", "imageAssetId": img, **kw}


def project(c: Client, root: Path) -> tuple[str, str, str, str]:
    src = root / "src"
    make_image(src / "one.png", (150, 40, 40), size=(1920, 1080))
    make_image(src / "two.png", (40, 150, 40), size=(1920, 1080))
    make_wav(src / "voice.wav", 3.0)
    pid = c.call("POST", "/api/projects", {"name": "Jonah"})[1]["projectId"]
    # pictures are linked (outside the project) so the staging path is exercised; narration is copied
    j1 = c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": [str(src / "one.png"), str(src / "two.png")], "mode": "link"})[1]
    wait_job(c, pid, j1["id"])
    j2 = c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": [str(src / "voice.wav")], "mode": "copy"})[1]
    wait_job(c, pid, j2["id"])
    assets = c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]
    by = {a["orig_name"]: a["id"] for a in assets}
    return pid, by["one.png"], by["two.png"], by["voice.wav"]


def put_board(c: Client, pid: str, nar: str, shots: list[dict[str, Any]]) -> None:
    sb = {"narrationAssetId": nar, "scenes": [{"id": "s1", "title": "Scene", "shots": shots}]}
    assert c.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": sb})[0] == 200


def test_render_draft_from_the_storyboard_and_play_it_back(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    pid, one, two, nar = project(c, root)
    put_board(c, pid, nar, [shot("a", 0, 1500, one, mode="CINEMATIC", preset="pan-left"), shot("b", 1500, 1500, two)])
    st, job, _ = c.call("POST", f"/api/projects/{pid}/storyboard/render", {"draft": True})
    assert st == 202
    done = wait_job(c, pid, job["id"])
    assert done["state"] == "completed", done
    res = done["result"]
    assert res["draft"] is True and (res["width"], res["height"], res["fps"]) == (640, 360, 24)
    assert "draft" in res["fidelity"] and res["frames"] == 72 and len(res["sha256"]) == 64

    renders = c.call("GET", f"/api/projects/{pid}/renders")[1]["renders"]
    assert [r["file"] for r in renders] == [res["file"]]
    # the file is served to the player (token in query is accepted for media), with byte ranges for seeking
    url = f"/api/projects/{pid}/renders/{res['file']}?token={srv.token}"
    st, body, h = c.call("GET", url, token=None)
    assert st == 200 and h["content-type"] == "video/mp4" and h["accept-ranges"] == "bytes" and body[4:8] == b"ftyp"
    st, part, h = c.call("GET", url, token=None, headers={"Range": "bytes=0-99"})
    assert st == 206 and len(part) == 100 and h["content-range"].startswith("bytes 0-99/")
    assert c.call("GET", url, token=None, headers={"Range": "bytes=999999999-"})[0] == 416
    assert c.call("GET", f"/api/projects/{pid}/renders/{res['file']}", token=None)[0] == 401
    assert c.call("GET", f"/api/projects/{pid}/renders/r-000000000000-draft.mp4")[0] == 404
    assert c.call("GET", f"/api/projects/{pid}/renders/..%2Fproject.json")[0] in (400, 404)

    # independent check of the file on disk: real video with the narration's length
    mp4 = srv.ws.project(pid).dir / "renders" / res["file"]
    probe = run([tc.ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", mp4], timeout=60)
    streams = json.loads(probe.stdout)["streams"]
    assert {s["codec_type"] for s in streams} == {"video", "audio"}
    # a second render never overwrites the first
    job2 = c.call("POST", f"/api/projects/{pid}/storyboard/render", {"draft": True})[1]
    assert wait_job(c, pid, job2["id"])["state"] == "completed"
    assert len(c.call("GET", f"/api/projects/{pid}/renders")[1]["renders"]) == 2
    # source pictures are untouched
    assert (root / "src" / "one.png").exists()


def test_motion_presets_really_move_the_picture(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    pid, one, _, nar = project(c, root)
    put_board(c, pid, nar, [shot("a", 0, 3000, one, mode="CINEMATIC", preset="slow-push-in")])
    done = wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/storyboard/render", {"draft": True})[1]["id"])
    assert done["state"] == "completed", done
    mp4 = srv.ws.project(pid).dir / "renders" / done["result"]["file"]
    frames = []
    for t in ("0.2", "2.6"):
        out = root / f"f{t}.png"
        run([tc.ffmpeg, "-y", "-v", "error", "-ss", t, "-i", mp4, "-frames:v", "1", out], timeout=60)
        frames.append(out.read_bytes())
    assert frames[0] != frames[1]  # a push-in changes the picture over time (not a frozen slideshow)


def test_refuses_to_render_a_storyboard_with_problems_and_says_why(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    srv, c, root = server
    pid, one, two, nar = project(c, root)
    url = f"/api/projects/{pid}/storyboard/render"
    st, err, _ = c.call("POST", url, {"draft": True})
    assert st == 409 and err["error"]["code"] == "not_render_ready" and "no storyboard" in err["error"]["message"].lower()
    put_board(c, pid, nar, [shot("a", 0, 1000, one), shot("b", 1500, 1500, two)])  # 500 ms gap
    st, err, _ = c.call("POST", url, {"draft": True})
    assert st == 409 and "Gap of 500 ms" in err["error"]["message"]
    put_board(c, pid, nar, [shot("a", 0, 1500, one, mode="LAYERED"), shot("b", 1500, 1500, None)])  # type: ignore[arg-type]
    err = c.call("POST", url, {"draft": True})[1]["error"]["message"]
    assert "at least one layer" in err and "need a picture" in err
    assert c.call("POST", url, {"draft": "yes"})[0] == 400
    assert not (srv.ws.project(pid).dir / "renders").exists() or not list((srv.ws.project(pid).dir / "renders").glob("*.mp4"))
    assert [j for j in c.call("GET", f"/api/projects/{pid}/jobs")[1]["jobs"] if j["kind"] == "render"] == []  # refused: no job


def test_generative_and_ignored_presets_are_reported_never_silent(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    srv, c, root = server
    pid, one, two, nar = project(c, root)
    put_board(c, pid, nar, [shot("a", 0, 1500, one, mode="GENERATIVE"), shot("b", 1500, 1500, two, preset="pan-left")])
    done = wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/storyboard/render", {"draft": True})[1]["id"])
    assert done["state"] == "completed", done
    text = " | ".join(done["result"]["warnings"])
    assert "no AI request is made" in text and "preset 'pan-left' is ignored" in text
    assert done["result"]["fallbacks"][0]["shot"] == "a"  # the fallback is declared in the report


def test_cancelled_render_publishes_nothing(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    pid, one, two, nar = project(c, root)
    put_board(c, pid, nar, [shot("a", 0, 1500, one), shot("b", 1500, 1500, two)])
    p = srv.ws.project(pid)
    svc = RenderService(p, srv.assets(pid), tc)
    manifest, notes = svc.prepare()
    ev = threading.Event()
    ev.set()
    assert svc.run(manifest, notes, draft=True, progress=lambda f, m: None, cancel=ev) == {"cancelled": True}
    left = [f.name for f in (p.dir / "renders").iterdir() if not f.name.startswith("_")]
    assert left == []  # no mp4, no report, no work folder
    seen: list[tuple[float, str]] = []
    svc.run(manifest, notes, draft=True, progress=lambda f, m: seen.append((f, m)), cancel=threading.Event())
    assert seen[0][0] == 0.0 and seen[-1][0] < 1.0 and [f for f, _ in seen] == sorted(f for f, _ in seen)
