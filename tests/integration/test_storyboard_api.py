"""Storyboard over the local API: import, edit, save/reopen, live narration clock (TIME-01/02, FR-SCRIPT-001..004)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_studio_api import Client, server, wait_job  # noqa: F401  (fixture re-export)

from helpers import make_image, make_wav
from storymotion_media.studio.api import ApiServer

pytestmark = pytest.mark.ffmpeg


def setup_project(c: Client, root: Path) -> tuple[str, str, str]:
    src = root / "src"
    make_image(src / "pic.png", (150, 40, 40), size=(1280, 720))
    make_wav(src / "voice.wav", 2.0)
    pid = c.call("POST", "/api/projects", {"name": "Jonah"})[1]["projectId"]
    job = c.call(
        "POST", f"/api/projects/{pid}/assets/import", {"paths": [str(src / "pic.png"), str(src / "voice.wav")]}
    )[1]
    assert wait_job(c, pid, job["id"])["state"] == "completed"
    assets = c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]
    img = next(a["id"] for a in assets if a["kind"] == "image")
    aud = next(a["id"] for a in assets if a["kind"] == "audio")
    return pid, img, aud


def test_empty_storyboard_then_import_script_edit_save_and_reopen(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    _, c, root = server
    pid, img, aud = setup_project(c, root)
    base = f"/api/projects/{pid}/storyboard"

    st, view, _ = c.call("GET", base)
    assert st == 200 and view["storyboard"]["scenes"] == [] and view["narrationMs"] is None

    st, view, _ = c.call("POST", base + "/import-script", {"text": "# The call\nGo to Nineveh.\n\n# The storm\nWind.", "filename": "j.md"})
    assert st == 200 and [s["title"] for s in view["storyboard"]["scenes"]] == ["The call", "The storm"]

    sbd = view["storyboard"]
    sbd["narrationAssetId"] = aud
    sbd["characters"] = [{"id": "jonah", "name": "Jonah"}]
    sbd["scenes"][0]["shots"] = [
        {"id": "s1a", "startMs": 0, "durationMs": 1000, "mode": "CINEMATIC", "imageAssetId": img, "characterIds": ["jonah"],
         "action": "Jonah listens", "mustShow": ["Jonah"], "avoid": [], "preset": "slow-push-in"},
    ]
    sbd["scenes"][1]["shots"] = [{"id": "s2a", "startMs": 1500, "durationMs": 500, "mode": "STATIC", "imageAssetId": img}]
    st, saved, _ = c.call("PUT", base, {"storyboard": sbd, "baseRevision": view["revision"]})
    assert st == 200
    assert saved["narrationMs"] is not None and abs(saved["narrationMs"] - 2000) < 60  # the clock is the audio file
    assert [d["code"] for d in saved["diagnostics"]] == ["gap"]
    assert "Gap of 500 ms" in saved["diagnostics"][0]["message"]  # flagged, but the work is saved

    # close/reopen: the same storyboard comes back from disk
    again = c.call("GET", base)[1]
    assert again["storyboard"] == saved["storyboard"] and again["revision"] == saved["revision"]
    # and it lives in the project document, next to (not instead of) the script
    doc = c.call("GET", f"/api/projects/{pid}")[1]["document"]
    assert doc["ext"]["storyboard"]["scenes"][0]["shots"][0]["preset"] == "slow-push-in"


def test_invalid_input_is_refused_with_field_locations_and_nothing_is_saved(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    _, c, root = server
    pid, img, _ = setup_project(c, root)
    base = f"/api/projects/{pid}/storyboard"
    before = c.call("GET", base)[1]["revision"]
    bad = {"scenes": [{"id": "s1", "shots": [{"id": "x", "startMs": 0, "durationMs": -5, "imageAssetId": img}]}]}
    st, err, _ = c.call("PUT", base, {"storyboard": bad})
    assert st == 422 and err["error"]["code"] == "invalid_plan"
    assert err["error"]["issues"][0]["path"] == "scenes[0].shots[0].durationMs"
    st, err, _ = c.call("POST", base + "/import-plan", {"text": '{"scenes": [,]}'})
    assert st == 422 and err["error"]["issues"][0]["path"].startswith("line 1")
    assert c.call("GET", base)[1]["revision"] == before


def test_import_will_not_silently_replace_existing_shots(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    _, c, root = server
    pid, img, _ = setup_project(c, root)
    base = f"/api/projects/{pid}/storyboard"
    plan: dict[str, Any] = {"scenes": [{"id": "s1", "title": "A", "shots": [{"id": "a", "startMs": 0, "durationMs": 1000, "imageAssetId": img}]}]}
    assert c.call("PUT", base, {"storyboard": plan})[0] == 200
    st, err, _ = c.call("POST", base + "/import-script", {"text": "New text."})
    assert st == 400 and "replace" in err["error"]["message"]
    assert c.call("GET", base)[1]["storyboard"]["scenes"][0]["shots"][0]["id"] == "a"  # untouched
    assert c.call("POST", base + "/import-script", {"text": "New text.", "replace": True})[0] == 200
    st, err, _ = c.call("POST", base + "/import-plan", {"text": '{"scenes": []}'})
    assert st == 400  # a storyboard exists, so an explicit confirmation is required
    assert c.call("POST", base + "/import-plan", {"text": '{"scenes": []}', "replace": True})[0] == 200


def test_stale_revision_and_missing_asset_are_reported(server: tuple[ApiServer, Client, Path]) -> None:  # noqa: F811
    _, c, root = server
    pid, img, _ = setup_project(c, root)
    base = f"/api/projects/{pid}/storyboard"
    v = c.call("GET", base)[1]
    assert c.call("PUT", base, {"storyboard": v["storyboard"], "baseRevision": v["revision"]})[0] == 200
    st, err, _ = c.call("PUT", base, {"storyboard": v["storyboard"], "baseRevision": v["revision"]})
    assert st == 409 and err["error"]["code"] == "stale_revision"
    # a picture removed from the library afterwards is flagged on the shot, not a crash
    plan = {"scenes": [{"id": "s1", "shots": [{"id": "a", "startMs": 0, "durationMs": 1000, "imageAssetId": img}]}]}
    assert c.call("PUT", base, {"storyboard": plan})[0] == 200
    assert c.call("DELETE", f"/api/projects/{pid}/assets/{img}")[0] == 200
    codes = [d["code"] for d in c.call("GET", base)[1]["diagnostics"]]
    assert "image-missing" in codes
    assert c.call("GET", base, token=None)[0] == 401
