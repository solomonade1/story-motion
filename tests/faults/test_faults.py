"""Negative / fault-injection checks mapped to QG section 7 (F-xx) and TRUST-02.

Each test names the F-ID it exercises. Provider-side items are MOCK-only.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from helpers import make_project
from storymotion_media import toolchain
from storymotion_media.contracts import parse_manifest
from storymotion_media.errors import ManifestValidationError, MediaError, ToolchainError
from storymotion_media.ingest import resolve_in_root, verify_manifest_assets
from storymotion_media.providers.base import AnimationRequest, IntegrityError, SourceImage, create_approval
from storymotion_media.providers.clip_factory import FfmpegMockClipFactory
from storymotion_media.providers.fake import FakeVideoProvider, Scenario
from storymotion_media.providers.flow import download_verified, poll_until_done, submit_once


def test_F12_malformed_json_and_negative_time_are_blocked_with_locations() -> None:
    with pytest.raises(ManifestValidationError) as ei:
        parse_manifest('{"schemaVersion": "1.0.0",')
    assert "line" in str(ei.value)
    with pytest.raises(ManifestValidationError) as ei2:
        parse_manifest('{"schemaVersion":"1.0.0","projectId":"x","title":"t","shots":[{"startMs":-5}]}')
    assert any("shots[0].startMs" in str(i) for i in ei2.value.issues)


def test_F13_hostile_paths_and_arguments_are_inert(tmp_path: Path) -> None:
    marker = tmp_path / "PWNED"
    out = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import sys;print(sys.argv[1])", f"a; touch {marker} & $(x) | `y`"],
        capture_output=True,
        text=True,
        check=True,
        shell=False,
    )
    assert "touch" in out.stdout and not marker.exists()
    p = toolchain.run([sys.executable, "-c", "import sys;print(sys.argv[1])", "x;y&z|w"], timeout=30)
    assert p.stdout.strip() == "x;y&z|w"  # our runner passes arguments verbatim, no shell
    with pytest.raises(MediaError, match="outside the project root"):
        resolve_in_root(tmp_path, "../outside.png")


def test_F13_shell_metacharacters_in_filename_render_fine(tc: toolchain.Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = make_project(root, seconds=3.0)
    evil = "img/a; touch PWNED & $(whoami).png"
    (root / evil).write_bytes((root / "img/a.png").read_bytes())
    doc = m.model_dump(mode="json")
    next(a for a in doc["assets"] if a["id"] == "a")["path"] = evil
    infos = verify_manifest_assets(tc, parse_manifest(__import__("json").dumps(doc)), root)
    assert infos["a"].width == 2560 and not (root / "PWNED").exists() and not Path("PWNED").exists()


def test_F11_modified_or_missing_source_is_flagged_not_silently_used(tc: toolchain.Toolchain, tmp_path: Path) -> None:
    """DATA-03 / F-11: every problem is listed with its asset; nothing is rendered."""
    root = tmp_path / "p"
    m = make_project(root, seconds=3.0)
    (root / "img/b.png").write_bytes(b"changed")
    (root / "img/c.png").unlink()
    with pytest.raises(ManifestValidationError) as ei:
        verify_manifest_assets(tc, m, root)
    msg = str(ei.value)
    assert "changed on disk" in msg and "is missing" in msg and "assets[2]" in msg and "assets[3]" in msg


def test_DATA04_corrupt_image_fails_with_actionable_error(tc: toolchain.Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = make_project(root, seconds=3.0)
    bad = root / "img/a.png"
    bad.write_bytes(b"\x89PNG\r\n\x1a\n" + b"garbage" * 10)
    import hashlib

    doc = m.model_dump(mode="json")
    next(a for a in doc["assets"] if a["id"] == "a")["sha256"] = hashlib.sha256(bad.read_bytes()).hexdigest()
    with pytest.raises(ManifestValidationError, match="corrupt or unsupported"):
        verify_manifest_assets(tc, parse_manifest(__import__("json").dumps(doc)), root)


def test_narration_length_mismatch_is_reported(tc: toolchain.Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = make_project(root, seconds=3.0)
    doc = m.model_dump(mode="json")
    doc["narration"]["durationMs"] = 3200
    doc["shots"][-1]["durationMs"] += 200
    doc["scenes"][0]["narration"]["endMs"] += 200
    with pytest.raises(ManifestValidationError, match="the audio file is"):
        verify_manifest_assets(tc, parse_manifest(__import__("json").dumps(doc)), root)


def test_F17_missing_ffmpeg_gives_corrective_action(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(toolchain, "_candidate_dirs", lambda: [tmp_path])
    monkeypatch.setattr(toolchain.shutil, "which", lambda _n: None)
    with pytest.raises(ToolchainError) as ei:
        toolchain.get_toolchain()
    assert "not found" in str(ei.value) and toolchain.ENV_DIR in str(ei.value)


def _req(root: Path, tc: toolchain.Toolchain) -> AnimationRequest:
    m = make_project(root, seconds=3.0)
    return AnimationRequest(
        "g1",
        tuple(SourceImage(root / m.asset(i).path, m.asset(i).sha256) for i in ("a", "dot")),
        "Sailors throw Jonah",
        3000,
        1280,
        720,
    )


def test_F14_hash_mismatch_download_is_rejected_and_removed(tc: toolchain.Toolchain, tmp_path: Path) -> None:
    req = _req(tmp_path / "p", tc)
    prov = FakeVideoProvider(FfmpegMockClipFactory(tc), tmp_path / "prov", scenario=Scenario(corrupt_download=True))
    ref = submit_once(prov, req, create_approval(prov.quote(req), user_confirmed=True, approval_id="ap"))
    poll_until_done(prov, ref, sleep=lambda _s: None)
    with pytest.raises(IntegrityError, match="hash differs"):
        download_verified(prov, tc, ref, req, tmp_path / "dl")
    assert not list((tmp_path / "dl").glob("*.mp4"))
    assert len(prov.charges) == 1  # accounting preserved even though the clip was rejected


def test_F07_wrong_resolution_or_duration_clip_is_rejected(tc: toolchain.Toolchain, tmp_path: Path) -> None:
    req = _req(tmp_path / "p", tc)
    real = FfmpegMockClipFactory(tc)

    def wrong_size(r: AnimationRequest, out: Path) -> None:
        real(AnimationRequest(r.shot_id, r.sources, r.prompt, r.duration_ms, 1920, 1080), out)

    prov = FakeVideoProvider(wrong_size, tmp_path / "prov")
    ref = submit_once(prov, req, create_approval(prov.quote(req), user_confirmed=True, approval_id="ap"))
    poll_until_done(prov, ref, sleep=lambda _s: None)
    with pytest.raises(IntegrityError, match="resolution"):
        download_verified(prov, tc, ref, req, tmp_path / "dl")

    def wrong_len(r: AnimationRequest, out: Path) -> None:
        real(AnimationRequest(r.shot_id, r.sources, r.prompt, 5000, r.width, r.height), out)

    prov2 = FakeVideoProvider(wrong_len, tmp_path / "prov2")
    ref2 = submit_once(prov2, req, create_approval(prov2.quote(req), user_confirmed=True, approval_id="ap2"))
    poll_until_done(prov2, ref2, sleep=lambda _s: None)
    with pytest.raises(IntegrityError, match="requested"):
        download_verified(prov2, tc, ref2, req, tmp_path / "dl2")
