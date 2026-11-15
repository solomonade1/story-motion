"""Export package for editors and AI models: files, timeline correctness against the real clips, and the round trip back."""

from __future__ import annotations

import json
import re
import threading
from pathlib import Path
from typing import Any

import pytest
from PIL import Image
from test_rendered_and_scan import make_clip
from test_studio_api import Client, server, wait_job  # noqa: F401  (fixture re-export)

from helpers import make_image, make_wav
from storymotion_media.export_pack import tc
from storymotion_media.studio.api import ApiServer
from storymotion_media.studio.render_service import RenderService
from storymotion_media.toolchain import Toolchain, run

pytestmark = pytest.mark.ffmpeg
FPS = 24


def frames_of(tool: Toolchain, f: Path) -> int:
    p = run([tool.ffprobe, "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", f], timeout=120)
    return int(p.stdout.strip().rstrip(","))


def audio_info(tool: Toolchain, f: Path) -> dict[str, Any]:
    p = run([tool.ffprobe, "-v", "error", "-select_streams", "a:0", "-show_entries", "stream=sample_rate,channels,codec_name:format=duration", "-of", "json", f], timeout=60)
    d = json.loads(p.stdout)
    return {"rate": int(d["streams"][0]["sample_rate"]), "ch": d["streams"][0]["channels"], "codec": d["streams"][0]["codec_name"], "dur": float(d["format"]["duration"])}


def setup(c: Client, root: Path, tool: Toolchain) -> dict[str, Any]:
    src = root / "src"
    make_image(src / "one.png", (200, 40, 40), size=(1920, 1080))
    make_image(src / "two.png", (40, 200, 40), size=(1920, 1080))
    make_clip(tool, src / "clip.mp4", red_s=2.0, blue_s=2.0)
    make_wav(src / "voice.wav", 6.0)
    make_wav(src / "bed.wav", 3.0)  # shorter than the video: must loop
    pid = c.call("POST", "/api/projects", {"name": "Export test"})[1]["projectId"]
    paths = [str(src / n) for n in ("one.png", "two.png", "clip.mp4", "voice.wav", "bed.wav")]
    assert wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": paths})[1]["id"])["state"] == "completed"
    by = {a["orig_name"]: a["id"] for a in c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]}
    sb = {
        "narrationAssetId": by["voice.wav"], "fadeInMs": 300, "fadeOutMs": 500,
        "audioTracks": [{"assetId": by["bed.wav"], "role": "ambience", "gainDb": -12.0, "startMs": 500, "fadeInMs": 400, "fadeOutMs": 600, "loop": True, "duckDb": 9.0}],
        "characters": [{"id": "jonah", "name": "Jonah"}],
        "scenes": [
            {"id": "s1", "title": "Call", "text": "God spoke to Jonah.", "characterIds": ["jonah"], "shots": [
                {"id": "a", "startMs": 0, "durationMs": 2000, "mode": "CINEMATIC", "imageAssetId": by["one.png"], "preset": "pan-left", "action": "Jonah listens", "mustShow": ["Jonah"], "avoid": ["fish"], "characterIds": ["jonah"]},
                {"id": "b", "startMs": 2000, "durationMs": 2000, "mode": "STATIC", "imageAssetId": by["two.png"], "transition": {"type": "crossfade", "durationMs": 500}, "action": "He turns away"},
            ]},
            {"id": "s2", "title": "Storm", "text": "A great wind rose.", "shots": [
                {"id": "c", "startMs": 4000, "durationMs": 2000, "mode": "RENDERED", "clipAssetId": by["clip.mp4"], "transition": {"type": "fadeblack", "durationMs": 400}, "action": "The sea rages"},
            ]},
        ],
    }
    st, view, _ = c.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": sb})
    assert st == 200 and not [d for d in view["diagnostics"] if d["severity"] != "info"], view
    return {"pid": pid, "by": by, "sb": view["storyboard"]}


def run_export(c: Client, pid: str, mode: str) -> dict[str, Any]:
    st, job, _ = c.call("POST", f"/api/projects/{pid}/storyboard/export", {"mode": mode})
    assert st == 202, job
    done = wait_job(c, pid, job["id"])
    assert done["state"] == "completed", done
    return done["result"]  # type: ignore[no-any-return]


def test_tc_and_edl_are_frame_exact() -> None:
    assert tc(0, 24) == "00:00:00:00" and tc(23, 24) == "00:00:00:23" and tc(24, 24) == "00:00:01:00" and tc(3600 * 24, 24) == "01:00:00:00"
    assert tc(86400 + 12, 30 * 1) == "00:48:00:12"


@pytest.fixture
def exported(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> tuple[Path, dict[str, Any], dict[str, Any], Client, ApiServer]:  # noqa: F811
    srv, c, root = server
    ids = setup(c, root, tc)
    res = run_export(c, ids["pid"], "full")
    return srv.ws.project(ids["pid"]).dir / "exports" / res["folder"], res, ids, c, srv


def test_full_package_contents(exported: Any, tc: Toolchain) -> None:
    folder, res, ids, _c, _srv = exported
    assert res["mode"] == "full" and res["shots"] == 3 and res["folder"].endswith("-full")
    names = {p["path"] for p in res["listing"]}
    for must in ("README.md", "timeline/timeline.otio", "timeline/timeline.edl", "audio/narration.wav", "audio/bed1_ambience.wav", "audio/final_mix.wav",
                 "ai/handoff.json", "ai/README_FOR_MODELS.md", "ai/storyboard.schema.json", "ai/script.txt", "ai/contact_sheet_1.jpg",
                 "shots/001_a.mp4", "shots/002_b.mp4", "shots/003_c.mp4", "ai/keyframes/002_b_mid.jpg"):
        assert must in names, must
    assert not list(folder.parent.glob(".work-*"))  # no temp folder left behind
    # clips: video only, project size, body frames + the handle a following transition needs
    expect = {"001_a.mp4": 48 + 12, "002_b.mp4": 48 + 10, "003_c.mp4": 48}  # shot b is followed by a 400 ms (10 frame) dip
    for name, n in expect.items():
        assert frames_of(tc, folder / "shots" / name) == n, name
    probe = run([tc.ffprobe, "-v", "error", "-show_entries", "stream=codec_type,width,height", "-of", "json", folder / "shots" / "001_a.mp4"], timeout=60)
    streams = json.loads(probe.stdout)["streams"]
    assert [(s["codec_type"], s["width"], s["height"]) for s in streams] == [("video", 1920, 1080)]
    # audio
    nar = audio_info(tc, folder / "audio" / "narration.wav")
    assert (nar["rate"], nar["ch"], nar["codec"]) == (48000, 2, "pcm_s16le") and abs(nar["dur"] - 6.0) < 0.1
    for f in ("bed1_ambience.wav", "final_mix.wav"):
        a = audio_info(tc, folder / "audio" / f)
        assert abs(a["dur"] - 6.0) < 0.15 and a["rate"] == 48000, f  # the 3 s bed was looped to the whole video


def test_edl_matches_the_storyboard_in_timecode(exported: Any) -> None:
    folder, *_ = exported
    text = (folder / "timeline" / "timeline.edl").read_text()
    assert text.startswith("TITLE: Export test") and "FCM: NON-DROP FRAME" in text
    events = [ln for ln in text.splitlines() if re.match(r"^\d{3}  AX", ln)]
    # shot a: cut at record 01:00:00:00 for 2 s
    assert events[0].endswith("00:00:00:00 00:00:02:00 01:00:00:00 01:00:02:00") and " C " in events[0]
    # shot b: zero-length hold of a, then a 12-frame dissolve into b at 01:00:02:00
    assert events[1].split()[-4:] == ["00:00:02:00", "00:00:02:00", "01:00:02:00", "01:00:02:00"]
    assert " D    012 " in events[2] and events[2].endswith("00:00:00:00 00:00:02:00 01:00:02:00 01:00:04:00")
    # shot c: a 10-frame dip, written as a dissolve and labelled as such
    assert " D    010 " in events[4] and events[4].endswith("00:00:00:00 00:00:02:00 01:00:04:00 01:00:06:00")
    assert "dip to black (written as a dissolve), 400 ms" in text and "FROM CLIP NAME: 003_c.mp4" in text
    assert "FROM CLIP NAME: 001_a.mp4" in text and "FROM CLIP NAME: 002_b.mp4" in text


def test_otio_structure_is_correct_and_agrees_with_the_files(exported: Any, tc: Toolchain) -> None:
    folder, _res, _ids, *_ = exported
    otio = json.loads((folder / "timeline" / "timeline.otio").read_text())
    assert otio["OTIO_SCHEMA"] == "Timeline.1" and otio["global_start_time"]["value"] == 3600 * FPS
    tracks = otio["tracks"]["children"]
    assert [(t["kind"], t["name"]) for t in tracks] == [("Video", "Video"), ("Audio", "Narration"), ("Audio", "Bed 1 (ambience)")]
    video = tracks[0]["children"]
    assert [c["OTIO_SCHEMA"] for c in video] == ["Clip.2", "Transition.1", "Clip.2", "Transition.1", "Clip.2"]
    clips = [c for c in video if c["OTIO_SCHEMA"] == "Clip.2"]
    assert sum(c["source_range"]["duration"]["value"] for c in clips) == 144 == otio["tracks"]["source_range"]["duration"]["value"]  # 6 s at 24 fps
    for t in (c for c in video if c["OTIO_SCHEMA"] == "Transition.1"):
        assert t["in_offset"]["value"] == 0 and t["out_offset"]["value"] in (12, 10) and t["transition_type"] == "SMPTE_Dissolve"
    for c in clips:  # every referenced file exists, and its declared available range equals the REAL frame count (body + handle)
        f = folder / c["media_reference"]["target_url"]
        assert f.is_file()
        assert c["media_reference"]["available_range"]["duration"]["value"] == frames_of(tc, f)
        assert c["source_range"]["duration"]["value"] <= c["media_reference"]["available_range"]["duration"]["value"]
    for t in tracks[1:]:
        assert (folder / t["children"][0]["media_reference"]["target_url"]).is_file()
    assert tracks[2]["children"][0]["metadata"]["storymotion"]["duckDb"] == 9.0 and "not applied" not in json.dumps(tracks[2])


def test_ai_brief_is_complete_and_round_trips_back_into_the_project(exported: Any) -> None:
    folder, _res, ids, c, _srv = exported
    ai = folder / "ai"
    h = json.loads((ai / "handoff.json").read_text())
    assert h["handoffVersion"] == "storymotion.handoff/1" and h["video"] == {"width": 1920, "height": 1080, "fps": 24, "fadeInMs": 300, "fadeOutMs": 500}
    assert [s["id"] for s in h["shots"]] == ["a", "b", "c"] and [(s["startMs"], s["startFrame"], s["frames"]) for s in h["shots"]] == [(0, 0, 48), (2000, 48, 48), (4000, 96, 48)]
    a = h["shots"][0]
    assert a["intent"] == {"action": "Jonah listens", "mustShow": ["Jonah"], "avoid": ["fish"]} and a["preset"] == "pan-left" and a["camera"]["start"]["x"] > a["camera"]["end"]["x"]
    assert h["shots"][1]["transitionIn"] == {"type": "crossfade", "durationMs": 500}
    assert [sc["script"] for sc in h["scenes"]] == ["God spoke to Jonah.", "A great wind rose."]
    ids_in_pkg = {x["id"] for x in h["assets"]}
    assert ids_in_pkg == set(ids["by"].values())  # the project's own ids, so answers import back
    assert all(x["provenance"]["licenseVerified"] is False for x in h["assets"]) and "GENERATIVE" in json.dumps(h["constraints"]["modes"])
    assert h["currentStoryboard"]["scenes"][0]["shots"][0]["id"] == "a" and h["diagnostics"] == []
    # no machine paths, no secrets
    blob = (ai / "handoff.json").read_text() + (folder / "timeline" / "timeline.otio").read_text() + (folder / "timeline" / "timeline.edl").read_text()
    assert "C:\\\\" not in blob and "C:/" not in blob and "token" not in blob.lower()
    # keyframes are real pictures
    for tag in ("start", "mid", "end"):
        with Image.open(ai / "keyframes" / f"002_b_{tag}.jpg") as im:
            assert im.size[0] == 640
    schema = json.loads((ai / "storyboard.schema.json").read_text())
    assert "scenes" in schema["properties"] and "audioTracks" in schema["properties"]
    assert "Import scene plan" in (ai / "README_FOR_MODELS.md").read_text() and "never invent" in (ai / "README_FOR_MODELS.md").read_text().lower()
    # the round trip: a model returns the (edited) storyboard; the app validates it and takes it in
    revised = h["currentStoryboard"]
    revised["scenes"][1]["shots"][0]["transition"] = {"type": "crossfade", "durationMs": 300}
    base = f"/api/projects/{ids['pid']}/storyboard"
    st, view, _ = c.call("POST", base + "/import-plan", {"text": json.dumps(revised), "replace": True})
    assert st == 200 and view["storyboard"]["scenes"][1]["shots"][0]["transition"]["durationMs"] == 300
    assert [d for d in view["diagnostics"] if d["severity"] != "info"] == []


def test_brief_mode_is_light_and_has_no_media(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    ids = setup(c, root, tc)
    res = run_export(c, ids["pid"], "brief")
    folder = srv.ws.project(ids["pid"]).dir / "exports" / res["folder"]
    names = {p["path"] for p in res["listing"]}
    assert res["mode"] == "brief" and "ai/handoff.json" in names and "ai/keyframes/001_a_mid.jpg" in names
    assert not (folder / "shots").exists() and not (folder / "audio").exists() and not (folder / "timeline").exists() and not (folder / ".seg").exists()
    h = json.loads((folder / "ai" / "handoff.json").read_text())
    assert h["project"]["exportMode"] == "brief" and h["narration"]["file"] is None
    assert res["totalBytes"] < 2_000_000  # stills and text only
    with Image.open(folder / "ai" / "keyframes" / "001_a_mid.jpg") as im:
        assert im.size[0] == 640


def test_refusals_listing_open_and_cancel(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    srv, c, root = server
    ids = setup(c, root, tc)
    pid = ids["pid"]
    base = f"/api/projects/{pid}/storyboard/export"
    assert c.call("POST", base, {"mode": "everything"})[0] == 400
    sb = ids["sb"]
    sb["scenes"][0]["shots"][1]["startMs"] = 2600  # a gap: not ready, same rule as rendering
    assert c.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": sb})[0] == 200
    st, err, _ = c.call("POST", base, {"mode": "brief"})
    assert st == 409 and "Gap of 600 ms" in err["error"]["message"]
    assert [j for j in c.call("GET", f"/api/projects/{pid}/jobs")[1]["jobs"] if j["kind"] == "export"] == []
    sb["scenes"][0]["shots"][1]["startMs"] = 2000
    c.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": sb})
    res = run_export(c, pid, "brief")
    listing = c.call("GET", f"/api/projects/{pid}/exports")[1]["exports"]
    assert [e["folder"] for e in listing] == [res["folder"]] and listing[0]["mode"] == "brief"
    st, opened, _ = c.call("POST", f"/api/projects/{pid}/exports/{res['folder']}/open", {})
    assert st == 200 and opened["opened"] is False and res["folder"] in opened["path"]  # no app window: reports the location
    assert c.call("POST", f"/api/projects/{pid}/exports/x-000000000000-full/open", {})[0] == 404
    assert c.call("POST", f"/api/projects/{pid}/exports/..%2Fproject.json/open", {})[0] in (400, 404)
    assert c.call("POST", f"/api/projects/{pid}/exports/{res['folder']}/open", {}, token=None)[0] == 401
    # cancelled before the first step: nothing published, no temp folder
    p = srv.ws.project(pid)
    svc = RenderService(p, srv.assets(pid), tc)
    manifest, _n = svc.prepare()
    ev = threading.Event()
    ev.set()
    assert svc.export(manifest, "full", progress=lambda f, m: None, cancel=ev) == {"cancelled": True}
    left = sorted(x.name for x in (p.dir / "exports").iterdir())
    assert left == [res["folder"]]


def test_independent_assets_are_exact_self_describing_and_verifiable(server: tuple[ApiServer, Client, Path], tc: Toolchain) -> None:  # noqa: F811
    import hashlib

    srv, c, root = server
    ids = setup(c, root, tc)
    res = run_export(c, ids["pid"], "assets")
    folder = srv.ws.project(ids["pid"]).dir / "exports" / res["folder"]
    assert res["mode"] == "assets" and res["folder"].endswith("-assets") and res["shots"] == 3
    assert not (folder / "timeline").exists() and not (folder / "ai").exists()  # no editor files, no model files: just assets
    assert not list(folder.parent.glob(".work-*"))

    # 1. clips are EXACTLY the shot length: no transition handle, even for shot b which is followed by a dip
    for sid in ("a", "b", "c"):
        assert frames_of(tc, folder / "shots" / f"{sid}.mp4") == 48, sid
        side = json.loads((folder / "shots" / f"{sid}.json").read_text())
        assert side["video"]["frames"] == 48 and side["video"]["audio"] is False and side["video"]["durationMs"] == 2000
        assert (folder / side["poster"]).is_file() and (folder / side["file"]).is_file()
    total = sum(json.loads((folder / "shots" / f"{s}.json").read_text())["video"]["frames"] for s in ("a", "b", "c"))
    assert total == 144  # the whole 6 s episode, with nothing duplicated
    # 2. each sidecar describes the shot on its own
    b = json.loads((folder / "shots" / "b.json").read_text())
    assert b["transitionIn"] == {"type": "crossfade", "durationMs": 500} and b["story"] == {"sceneId": "s1", "order": 2, "startMs": 2000, "endMs": 4000, "durationMs": 2000, "startFrame": 48}
    a = json.loads((folder / "shots" / "a.json").read_text())
    assert a["intent"] == {"action": "Jonah listens", "mustShow": ["Jonah"], "avoid": ["fish"]} and a["preset"] == "pan-left" and a["mode"] == "CINEMATIC"
    assert a["sources"][0]["file"].startswith("sources/") and (folder / a["sources"][0]["file"]).is_file()
    # 3. sources are the originals, byte for byte
    one = next((folder / "sources").glob("*-one.png"))
    assert one.read_bytes() == (root / "src" / "one.png").read_bytes()
    index = json.loads((folder / "index.json").read_text())
    assert {s["assetId"] for s in index["sources"]} == set(ids["by"].values()) and all(s["provenance"]["licenseVerified"] is False for s in index["sources"])
    # 4. audio sidecars say what is and is not applied
    bed = json.loads((folder / "audio" / "bed1_ambience.json").read_text())
    assert bed["applied"]["gainDb"] == -12.0 and bed["notApplied"] == {"duckDb": 9.0} and bed["role"] == "ambience"
    assert json.loads((folder / "audio" / "final_mix.json").read_text())["role"] == "final-mix"
    # 5a. plain LF line endings, so the standard `sha256sum -c` works anywhere (regression: Windows CRLF made it fail)
    for name in ("SHA256SUMS.txt", "index.json", "README.md", "shots/a.json", "audio/narration.json"):
        assert b"\r" not in (folder / name).read_bytes(), name
    # 5. SHA256SUMS.txt is complete and correct, checked here independently of the app
    sums = dict(reversed(ln.split("  ", 1)) for ln in (folder / "SHA256SUMS.txt").read_text().splitlines())
    on_disk = {p.relative_to(folder).as_posix() for p in folder.rglob("*") if p.is_file()} - {"SHA256SUMS.txt"}
    assert set(sums) == on_disk
    for rel, digest in sums.items():
        assert hashlib.sha256((folder / rel).read_bytes()).hexdigest() == digest, rel
    for row in index["shots"] + index["audio"]:
        assert sums[row["file"]] == hashlib.sha256((folder / row["file"]).read_bytes()).hexdigest()
    (folder / "shots" / "a.json").write_text("tampered")  # a changed file no longer matches
    assert hashlib.sha256((folder / "shots" / "a.json").read_bytes()).hexdigest() != sums["shots/a.json"]
    # 6. portable: no machine paths or secrets anywhere in the text files
    blob = "".join(p.read_text(encoding="utf-8") for p in folder.rglob("*.json") if p.name != "a.json") + (folder / "README.md").read_text()
    assert "C:\\\\" not in blob and "C:/" not in blob and "token" not in blob.lower()
    listing = c.call("GET", f"/api/projects/{ids['pid']}/exports")[1]["exports"]
    assert [e["mode"] for e in listing] == ["assets"]


@pytest.mark.parametrize("mode", ["brief", "assets"])
def test_publishing_rides_out_transient_folder_locks(server: tuple[ApiServer, Client, Path], tc: Toolchain, monkeypatch: pytest.MonkeyPatch, mode: str) -> None:  # noqa: F811
    """Regression: the final folder rename failed once with 'Access is denied' (virus scanner holding a new file)."""
    srv, c, root = server
    ids = setup(c, root, tc)
    real_rename = Path.rename
    denied = {"n": 0}

    def flaky(self: Path, target: Any) -> Any:
        if self.name.startswith(".work-x-") and denied["n"] < 3:
            denied["n"] += 1
            raise PermissionError(5, "Access is denied")
        return real_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky)
    res = run_export(c, ids["pid"], mode)
    assert denied["n"] == 3 and res["folder"].endswith(mode)  # failed three times, then published
    assert not list((srv.ws.project(ids["pid"]).dir / "exports").glob(".work-*"))
