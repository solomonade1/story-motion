"""Media intake, previews, duplicates, relinking, cancellation, jobs (FR-MEDIA-001..004,006; FR-PROJ-003; QG DATA-03..06)."""

from __future__ import annotations

import hashlib
import threading
import time
from pathlib import Path

import pytest
from PIL import Image

from helpers import make_image, make_wav
from storymotion_media.studio import assets as assets_mod
from storymotion_media.studio.assets import AssetService
from storymotion_media.studio.errors import AssetNotFound, InvalidInput, StudioError
from storymotion_media.studio.jobs import JobManager
from storymotion_media.studio.store import Project, Workspace
from storymotion_media.toolchain import Toolchain, ffprobe_json, run

pytestmark = pytest.mark.ffmpeg


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def ffmpeg_make(tc: Toolchain, out: Path, lavfi: str, *args: str) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    p = run([tc.ffmpeg, "-v", "error", "-y", "-f", "lavfi", "-i", lavfi, *args, out], timeout=120)
    assert p.returncode == 0, p.stderr
    return out


@pytest.fixture
def proj(tmp_path: Path) -> Project:
    ws = Workspace(tmp_path / "ws")
    return ws.project(ws.create("Test").projectId)


@pytest.fixture
def svc(proj: Project, tc: Toolchain) -> AssetService:
    return AssetService(proj, tc)


@pytest.fixture
def media(tmp_path: Path, tc: Toolchain) -> dict[str, Path]:
    d = tmp_path / "src"
    make_image(d / "pic.png", (150, 40, 40), size=(1600, 900))
    make_image(d / "photo.jpg", (40, 60, 160), size=(1280, 720))
    Image.open(d / "pic.png").save(d / "pic.webp")
    make_wav(d / "voice.wav", 2.0)
    ffmpeg_make(tc, d / "voice.mp3", "sine=frequency=440:duration=2", "-c:a", "libmp3lame")
    ffmpeg_make(tc, d / "voice.aac", "sine=frequency=330:duration=2", "-c:a", "aac", "-f", "adts")
    ffmpeg_make(
        tc, d / "clip.mp4", "testsrc=size=1280x720:rate=24:duration=2", "-c:v", "libx264", "-pix_fmt", "yuv420p"
    )
    ffmpeg_make(tc, d / "clip.mov", "testsrc=size=640x360:rate=30:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p")
    return {p.name: p for p in d.iterdir()}


def test_every_supported_format_imports_with_metadata_and_previews(
    svc: AssetService, media: dict[str, Path], tc: Toolchain
) -> None:
    res = svc.import_files([str(p) for p in media.values()])
    assert res.errors == []
    by_name = {a["orig_name"]: a for a in res.imported}
    assert set(by_name) == set(media)
    # pic.webp is a re-encode of pic.png (different bytes), so all 8 are distinct assets
    assert len(res.imported) == 8 and res.duplicates == []
    img = by_name["pic.png"]
    assert (img["width"], img["height"], img["category"], img["kind"]) == (1600, 900, "environment", "image")
    assert by_name["photo.jpg"]["width"] == 1280 and by_name["pic.webp"]["kind"] == "image"
    assert by_name["voice.wav"]["sample_rate"] == 22050 and abs(by_name["voice.wav"]["duration_ms"] - 2000) < 60
    assert by_name["voice.mp3"]["category"] == "audio" and 1800 < by_name["voice.mp3"]["duration_ms"] < 2300
    assert by_name["voice.aac"]["kind"] == "audio" and by_name["voice.aac"]["sample_rate"] == 44100
    clip = by_name["clip.mp4"]
    assert (clip["width"], clip["height"], clip["category"]) == (1280, 720, "rendered_video") and abs(
        clip["fps"] - 24
    ) < 0.01
    assert by_name["clip.mov"]["width"] == 640 and abs(by_name["clip.mov"]["fps"] - 30) < 0.01
    for a in res.imported:  # DATA-06: usable thumbnail and proxy for every valid import
        assert a["thumbUrl"] and a["proxyUrl"] and a["status"] == "ok", a["orig_name"]
        thumb = svc.served_file(a["id"], "thumbs")
        proxy = svc.served_file(a["id"], "proxies")
        assert thumb.stat().st_size > 0 and proxy.stat().st_size > 0
        if a["kind"] != "audio":
            assert max(Image.open(thumb).size) <= 320
        assert ffprobe_json(tc, proxy)["streams"], a["orig_name"]
    pv = svc.served_file(clip["id"], "proxies")
    vs = next(s for s in ffprobe_json(tc, pv)["streams"] if s["codec_type"] == "video")
    assert vs["height"] == 360 and vs["codec_name"] == "h264"  # compressed preview proxy
    for p in media.values():  # sources are never modified
        assert p.exists()


def test_exact_duplicate_is_recognised_and_not_copied_twice(
    svc: AssetService, media: dict[str, Path], tmp_path: Path, proj: Project
) -> None:
    first = svc.import_files([str(media["pic.png"])])
    twin = tmp_path / "elsewhere" / "renamed copy.png"
    twin.parent.mkdir()
    twin.write_bytes(media["pic.png"].read_bytes())
    again = svc.import_files([str(twin)])
    assert again.imported == [] and len(again.duplicates) == 1
    assert (
        again.duplicates[0]["existingId"] == first.imported[0]["id"] and "identical" in again.duplicates[0]["message"]
    )
    assert len(svc.list_assets()) == 1 and len(list((proj.dir / "assets").iterdir())) == 1


def test_link_mode_does_not_copy_and_never_touches_the_original(
    svc: AssetService, media: dict[str, Path], proj: Project
) -> None:
    before = (sha(media["clip.mp4"]), media["clip.mp4"].stat().st_mtime_ns)
    res = svc.import_files([str(media["clip.mp4"])], mode="link")
    a = res.imported[0]
    assert a["mode"] == "link" and a["rel_path"] is None and a["abs_path"] == str(media["clip.mp4"].resolve())
    assert not list((proj.dir / "assets").iterdir()) and a["thumbUrl"] and a["proxyUrl"]
    assert (sha(media["clip.mp4"]), media["clip.mp4"].stat().st_mtime_ns) == before


def test_bad_files_get_actionable_errors_and_do_not_stop_the_batch(
    svc: AssetService, media: dict[str, Path], tmp_path: Path
) -> None:
    d = tmp_path / "bad"
    d.mkdir()
    (d / "broken.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"junk" * 30)
    good = bytearray(media["pic.png"].read_bytes())
    mid = len(good) // 2
    good[mid : mid + 400] = bytes([0xDE, 0xAD, 0xBE, 0xEF]) * 100  # header probes fine; pixel data cannot decode
    (d / "corrupt_mid.png").write_bytes(bytes(good))
    mp3 = bytearray(media["voice.mp3"].read_bytes())
    mp3[len(mp3) // 2 : len(mp3) // 2 + 300] = bytes([0xDE, 0xAD, 0xBE, 0xEF]) * 75  # probes fine, cannot decode
    (d / "corrupt_mid.mp3").write_bytes(bytes(mp3))
    (d / "empty.png").write_bytes(b"")
    (d / "notes.txt").write_text("hello")
    (d / "folder").mkdir()
    (d / "truncated.mp4").write_bytes(media["clip.mp4"].read_bytes()[:3000])
    batch = [
        str(d / "broken.png"),
        str(d / "corrupt_mid.png"),
        str(d / "corrupt_mid.mp3"),
        str(d / "empty.png"),
        str(d / "notes.txt"),
        str(d / "folder"),
        str(d / "truncated.mp4"),
        str(d / "gone.png"),
        "relative/path.png",
        str(media["photo.jpg"]),
    ]
    res = svc.import_files(batch)
    codes = {Path(e["path"]).name: e["code"] for e in res.errors}
    assert codes == {
        "broken.png": "corrupt_media",
        "corrupt_mid.png": "corrupt_media",
        "corrupt_mid.mp3": "corrupt_media",
        "empty.png": "empty_file",
        "notes.txt": "unsupported_type",
        "folder": "not_a_file",
        "truncated.mp4": "corrupt_media",
        "gone.png": "not_found",
        "path.png": "invalid_path",
    }
    msgs = {Path(e["path"]).name: e["message"] for e in res.errors}
    assert (
        "damaged or incomplete" in msgs["broken.png"]
        and "Supported:" in msgs["notes.txt"]
        and "full path" in msgs["path.png"]
    )
    assert [a["orig_name"] for a in res.imported] == ["photo.jpg"]  # the good file still imported
    assert len(svc.list_assets()) == 1


def test_video_damaged_mid_file_is_imported_with_a_visible_warning(
    svc: AssetService, tc: Toolchain, tmp_path: Path
) -> None:
    clip = ffmpeg_make(
        tc, tmp_path / "long.mp4", "testsrc=size=640x360:rate=24:duration=6", "-c:v", "libx264", "-pix_fmt", "yuv420p"
    )
    b = bytearray(clip.read_bytes())
    b[len(b) // 2 : len(b) // 2 + 800] = bytes([0xDE, 0xAD, 0xBE, 0xEF]) * 200
    bad = tmp_path / "damaged.mp4"
    bad.write_bytes(bytes(b))
    res = svc.import_files([str(bad)])
    assert res.errors == [] and len(res.imported) == 1
    assert "damaged sections" in (res.imported[0]["status_detail"] or "")


def test_hostile_file_name_is_inert(svc: AssetService, tmp_path: Path, media: dict[str, Path], proj: Project) -> None:
    evil = tmp_path / "src" / "a; touch PWNED & $(whoami) `x`.png"
    Image.open(media["pic.png"]).resize((800, 450)).save(evil)  # make it distinct
    res = svc.import_files([str(evil)])
    a = res.imported[0]
    assert (
        a["rel_path"].startswith("assets/a-")
        and ";" not in a["rel_path"]
        and "$" not in a["rel_path"]
        and " " not in a["rel_path"]
    )
    assert not (proj.dir / "PWNED").exists() and not Path("PWNED").exists()
    assert a["orig_name"] == evil.name  # kept as display text only


def test_move_then_relink_by_path_and_by_folder(svc: AssetService, media: dict[str, Path], tmp_path: Path) -> None:
    """DATA-03: a moved source is flagged; unaffected assets are preserved; repair succeeds."""
    svc.import_files([str(media["clip.mp4"]), str(media["photo.jpg"]), str(media["voice.wav"])], mode="link")
    moved = tmp_path / "moved" / "deep" / "dir"
    moved.mkdir(parents=True)
    media["clip.mp4"].rename(moved / "clip.mp4")
    media["voice.wav"].rename(moved / "voice-renamed.wav")
    counts = svc.check_all()["counts"]
    assert counts == {"ok": 1, "missing": 2, "changed": 0}
    by = {a["orig_name"]: a for a in svc.list_assets()}
    assert (
        by["photo.jpg"]["status"] == "ok"
        and by["clip.mp4"]["status"] == "missing"
        and "Relink" in by["clip.mp4"]["status_detail"]
    )
    # wrong content is refused
    imposter = tmp_path / "imposter.mp4"
    imposter.write_bytes(b"not the same")
    with pytest.raises(InvalidInput, match="not identical"):
        svc.relink(by["clip.mp4"]["id"], str(imposter))
    # relink by path
    fixed = svc.relink(by["clip.mp4"]["id"], str(moved / "clip.mp4"))
    assert fixed["status"] == "ok" and fixed["abs_path"] == str((moved / "clip.mp4").resolve())
    # relink by folder search finds the renamed file by content
    out = svc.relink_folder(str(tmp_path / "moved"))
    assert out["relinked"] == [by["voice.wav"]["id"]] and out["stillMissing"] == []
    assert svc.check_all()["counts"] == {"ok": 3, "missing": 0, "changed": 0}


def test_modified_source_is_flagged_not_silently_trusted(svc: AssetService, media: dict[str, Path]) -> None:
    """F-11: an externally modified file is 'changed', never reported ok."""
    svc.import_files([str(media["voice.wav"])], mode="link")
    media["voice.wav"].write_bytes(media["voice.wav"].read_bytes() + b"\x00" * 64)
    assert svc.check_all()["counts"]["changed"] == 1
    a = svc.list_assets()[0]
    assert a["status"] == "changed" and "changed" in a["status_detail"]


def test_deleted_project_copy_is_restored_by_relinking(
    svc: AssetService, media: dict[str, Path], proj: Project
) -> None:
    a = svc.import_files([str(media["photo.jpg"])]).imported[0]
    (proj.dir / a["rel_path"]).unlink()
    assert svc.check_all()["counts"]["missing"] == 1
    svc.relink(a["id"], str(media["photo.jpg"]))
    assert (proj.dir / a["rel_path"]).exists() and svc.check_all()["counts"] == {"ok": 1, "missing": 0, "changed": 0}


def test_cancel_before_and_during_import_leaves_no_partial_files(
    svc: AssetService, media: dict[str, Path], proj: Project
) -> None:
    ev = threading.Event()
    ev.set()
    res = svc.import_files([str(media["pic.png"])], cancel=ev)
    assert res.cancelled and res.imported == [] and svc.list_assets() == []
    ev2 = threading.Event()
    calls = {"n": 0}

    def progress(_f: float, msg: str) -> None:
        if "Importing" in msg:
            calls["n"] += 1
            if calls["n"] == 2:  # cancel as the second file starts
                ev2.set()

    res = svc.import_files(
        [str(media["pic.png"]), str(media["photo.jpg"]), str(media["voice.wav"])], progress=progress, cancel=ev2
    )
    assert res.cancelled and [a["orig_name"] for a in res.imported] == ["pic.png"]
    assert len(svc.list_assets()) == 1
    assert not list(proj.dir.rglob("*.part"))
    ids = {a["id"] for a in svc.list_assets()}
    for sub in ("assets", "thumbs", "proxies"):  # nothing orphaned from the cancelled files
        for f in (proj.dir / sub).iterdir():
            assert any(i in f.name for i in ids), f.name


def test_cancel_inside_a_file_removes_its_partial_copy(
    svc: AssetService, media: dict[str, Path], proj: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    ev = threading.Event()
    real = svc._copy_verified

    def copy_then_cancel(*a: object, **k: object) -> None:
        real(*a, **k)
        ev.set()  # the user presses Cancel right after the copy landed, before the import finished

    monkeypatch.setattr(svc, "_copy_verified", copy_then_cancel)
    res = svc.import_files([str(media["pic.png"])], cancel=ev)
    assert res.cancelled and res.imported == [] and svc.list_assets() == []
    for sub in ("assets", "thumbs", "proxies"):
        assert list((proj.dir / sub).iterdir()) == [], sub


def test_disk_full_or_read_only_is_reported_and_leaves_nothing_behind(
    svc: AssetService, media: dict[str, Path], proj: Project, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Simulated ENOSPC/EROFS (a real full disk is not created in tests): clear message, no row, no files, source intact."""

    def boom(*_a: object, **_k: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(assets_mod.shutil, "copyfile", boom)
    res = svc.import_files([str(media["pic.png"])])
    assert res.imported == [] and res.errors[0]["code"] == "copy_failed"
    assert (
        "disk may be full or read-only" in res.errors[0]["message"]
        and "original file is untouched" in res.errors[0]["message"]
    )
    assert svc.list_assets() == [] and not list((proj.dir / "assets").iterdir()) and media["pic.png"].exists()


def test_category_validation_and_removal_rules(svc: AssetService, media: dict[str, Path], proj: Project) -> None:
    copy = svc.import_files([str(media["pic.png"])]).imported[0]
    link = svc.import_files([str(media["photo.jpg"])], mode="link").imported[0]
    assert svc.set_category(copy["id"], "character")["category"] == "character"
    with pytest.raises(InvalidInput):
        svc.set_category(copy["id"], "weapon")
    with pytest.raises(InvalidInput):
        svc.import_files([str(media["voice.wav"])], mode="teleport")
    with pytest.raises(InvalidInput):
        svc.import_files([])
    svc.remove(copy["id"])
    assert not (proj.dir / copy["rel_path"]).exists() and not (proj.dir / copy["thumb_rel"]).exists()
    svc.remove(link["id"])
    assert media["photo.jpg"].exists()  # a linked original is never deleted
    with pytest.raises(AssetNotFound):
        svc.get(copy["id"])


def test_preview_files_are_served_only_via_database_lookup(svc: AssetService, media: dict[str, Path]) -> None:
    a = svc.import_files([str(media["pic.png"])]).imported[0]
    assert svc.served_file(a["id"], "thumbs").is_file()
    for bad in ("../../etc/passwd", "a-000000000000", "a-../x", ""):
        with pytest.raises((InvalidInput, AssetNotFound)):
            svc.served_file(bad, "thumbs")


# ------------------------------------------------------------------ jobs
def wait_job(jm: JobManager, proj: Project, jid: str) -> dict:
    return jm.wait(proj, jid, timeout=60)


def test_import_job_reports_progress_and_completes(svc: AssetService, proj: Project, media: dict[str, Path]) -> None:
    jm = JobManager()
    try:
        files = [str(media[n]) for n in ("pic.png", "photo.jpg", "voice.wav")]
        job = jm.start(
            proj, "import", {"count": 3}, lambda rep, ev: svc.import_files(files, progress=rep, cancel=ev).as_dict()
        )
        assert job["state"] in ("queued", "running", "completed")
        done = wait_job(jm, proj, job["id"])
        assert done["state"] == "completed" and done["progress"] == 1.0 and len(done["result"]["imported"]) == 3
        assert jm.list_jobs(proj)[0]["id"] == job["id"]
    finally:
        jm.shutdown()


def test_running_job_can_be_cancelled(svc: AssetService, proj: Project) -> None:
    jm = JobManager()
    started = threading.Event()

    def slow(rep, ev):  # noqa: ANN001, ANN202
        started.set()
        for i in range(200):
            if ev.is_set():
                return {"cancelled": True, "done": i}
            rep(i / 200, f"step {i}")
            time.sleep(0.02)
        return {"done": 200}

    try:
        job = jm.start(proj, "slow", {}, slow)
        assert started.wait(10)
        jm.cancel(proj, job["id"])
        done = wait_job(jm, proj, job["id"])
        assert done["state"] == "cancelled" and done["result"]["done"] < 200
    finally:
        jm.shutdown()


def test_failing_job_records_a_readable_error_and_state_machine_is_enforced(proj: Project) -> None:
    jm = JobManager()
    try:

        def explode(_rep, _ev):  # noqa: ANN001, ANN202
            raise ValueError("kaboom")

        job = jm.start(proj, "boom", {}, explode)
        done = wait_job(jm, proj, job["id"])
        assert done["state"] == "failed" and "kaboom" in done["error"] and "Nothing was half-saved" in done["error"]
        with pytest.raises(StudioError, match="cannot go from"):
            jm._transition(proj, job["id"], "running")  # failed -> running is illegal
        with pytest.raises(InvalidInput):
            jm.get(proj, "../../x")
    finally:
        jm.shutdown()


def test_jobs_running_when_the_process_died_become_interrupted(proj: Project) -> None:
    with proj.db() as con:
        con.execute(
            "INSERT INTO jobs(id,kind,state,progress,created_at,updated_at) VALUES('j-aaaaaaaaaaaa','import','running',0.4,'n','n')"
        )
        con.execute(
            "INSERT INTO jobs(id,kind,state,progress,created_at,updated_at) VALUES('j-bbbbbbbbbbbb','import','completed',1,'n','n')"
        )
    jm = JobManager()
    try:
        assert jm.reconcile(proj) == 1
        assert (
            jm.get(proj, "j-aaaaaaaaaaaa")["state"] == "interrupted"
            and "safe" in jm.get(proj, "j-aaaaaaaaaaaa")["error"]
        )
        assert jm.get(proj, "j-bbbbbbbbbbbb")["state"] == "completed" and jm.reconcile(proj) == 0
    finally:
        jm.shutdown()


def test_twenty_plus_assets_and_a_narration_import_and_survive_reopening(tmp_path: Path, tc: Toolchain) -> None:
    """Phase 1 acceptance: 20+ assets + a narration file import, and everything is intact after close/reopen."""
    fixtures = Path(__file__).parents[1] / "fixtures" / "jonah" / "assets"
    files = [
        *sorted((fixtures / "images").glob("*.jpg")),
        *sorted((fixtures / "layers").glob("*.png")),
        fixtures / "audio" / "narration.wav",
    ]
    extra = tmp_path / "extra"
    for i in range(9):  # more unique pictures in mixed formats
        png = extra / f"gen-{i}.png"
        make_image(png, (20 + i * 20, 60, 200 - i * 15), size=(1280, 720))
        if i % 3 == 0:
            Image.open(png).save(extra / f"gen-{i}.webp")
            files.append(extra / f"gen-{i}.webp")
        else:
            files.append(png)
    assert len(files) >= 24
    ws = Workspace(tmp_path / "ws")
    pid = ws.create("Twenty plus").projectId
    svc = AssetService(ws.project(pid), tc)
    started = time.monotonic()
    res = svc.import_files([str(f) for f in files])
    elapsed = time.monotonic() - started
    assert res.errors == [] and res.duplicates == [] and len(res.imported) == len(files)
    assert {a["kind"] for a in res.imported} == {"image", "audio"} and sum(
        a["kind"] == "audio" for a in res.imported
    ) == 1
    narr = next(a for a in res.imported if a["orig_name"] == "narration.wav")
    assert narr["sample_rate"] == 22050 and abs(narr["duration_ms"] - 85606) < 100  # the real Jonah narration
    assert all(a["thumbUrl"] and a["proxyUrl"] and a["status"] == "ok" for a in res.imported)
    assert elapsed < 120, (
        f"import took {elapsed:.0f}s"
    )  # generous machine-independent bound; the real figure is printed in the log
    print(f"IMPORT_TIMING files={len(files)} seconds={elapsed:.1f}")
    reopened = AssetService(Workspace(tmp_path / "ws").project(pid), tc)  # close/reopen
    again = reopened.list_assets()
    assert {a["id"] for a in again} == {a["id"] for a in res.imported}  # nothing lost or invented
    assert [a["id"] for a in again] == [
        a["id"] for a in svc.list_assets()
    ]  # and the library order is stable across reopen
    assert reopened.check_all(verify_hash=True)["counts"] == {"ok": len(files), "missing": 0, "changed": 0}
