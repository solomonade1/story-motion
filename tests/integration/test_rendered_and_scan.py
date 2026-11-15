"""RENDERED (creator/Blender clip) shots and the drop-folder scanner. Real FFmpeg."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from PIL import Image

from helpers import frame_png, make_image, make_layer, make_project, make_wav, mean_rgb
from storymotion_media.contracts import parse_manifest
from storymotion_media.errors import ManifestValidationError
from storymotion_media.ingest import sha256_file
from storymotion_media.render import RenderOptions, render
from storymotion_media.scan import scan_project
from storymotion_media.toolchain import Toolchain, run

pytestmark = pytest.mark.ffmpeg


def make_clip(tc: Toolchain, out: Path, *, red_s: float, blue_s: float, size: str = "1280x720", fps: int = 24) -> None:
    """A clip that is red for red_s seconds and then blue for blue_s seconds."""
    out.parent.mkdir(parents=True, exist_ok=True)
    g = (
        f"color=c=red:s={size}:r={fps}:d={red_s}[a];color=c=0x4090ff:s={size}:r={fps}:d={blue_s}[b];"
        "[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]"
    )
    p = run([tc.ffmpeg, "-v", "error", "-y", "-filter_complex", g, "-map", "[v]", "-c:v", "libx264", out], timeout=120)
    assert p.returncode == 0, p.stderr


def project_with_clip(tc: Toolchain, root: Path, rendered: dict[str, object], seconds: float = 3.0):  # noqa: ANN201
    make_clip(tc, root / "clips/c.mp4", red_s=1.0, blue_s=3.0)
    base = make_project(
        root,
        seconds=seconds,
        shots=[
            {
                "id": "r1",
                "sceneId": "sc",
                "startMs": 0,
                "durationMs": int(seconds * 1000),
                "mode": "RENDERED",
                "rendered": rendered,
            },
        ],
        extra_assets=[
            {
                "id": "clip",
                "type": "rendered_video",
                "path": "clips/c.mp4",
                "sha256": sha256_file(root / "clips/c.mp4"),
                "provenance": {"kind": "creator_supplied", "source": "test", "license": "CC0", "licenseVerified": True},
            }
        ],
    )
    return base


def test_rendered_clip_plays_as_is_and_trim_selects_content(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = project_with_clip(tc, root, {"assetId": "clip", "trimStartMs": 0})
    out = tmp_path / "a.mp4"
    rep = render(m, root, out, RenderOptions(draft=True), tc)
    assert rep.shots[0]["declaredMode"] == "RENDERED" == rep.shots[0]["renderedMode"] and not rep.fallbacks
    first = mean_rgb(frame_png(tc, out, 5, tmp_path / "f5.png"))
    later = mean_rgb(frame_png(tc, out, 40, tmp_path / "f40.png"))  # 1.67 s -> blue part
    assert first[0] > first[2] + 100 and later[2] > later[0] + 100

    m2 = project_with_clip(tc, tmp_path / "q", {"assetId": "clip", "trimStartMs": 1000})
    out2 = tmp_path / "b.mp4"
    render(m2, tmp_path / "q", out2, RenderOptions(draft=True), tc)
    start = mean_rgb(frame_png(tc, out2, 2, tmp_path / "g2.png"))
    assert start[2] > start[0] + 100  # trimmed past the red second: starts on blue


def test_short_clip_holds_last_frame_and_warns(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = project_with_clip(tc, root, {"assetId": "clip", "trimStartMs": 3500}, seconds=3.0)  # 0.5 s usable of 3 s
    rep = render(m, root, tmp_path / "s.mp4", RenderOptions(draft=True), tc)
    assert any("last frame is held" in w for w in rep.warnings)


def test_rendered_contract_rules() -> None:
    def doc(shot: dict[str, object], clip_type: str = "rendered_video") -> str:
        d = json.loads(make_minimal_doc(clip_type))
        d["shots"] = [shot]
        return json.dumps(d)

    base = {"id": "r1", "sceneId": "sc", "startMs": 0, "durationMs": 2000, "mode": "RENDERED"}
    parse_manifest(doc({**base, "rendered": {"assetId": "clip"}}))  # valid, no sourceAssetIds needed
    for bad, text in [
        ({**base}, "require 'rendered'"),
        ({**base, "rendered": {"assetId": "clip"}, "fallbackMode": "STATIC"}, "must not use"),
        ({**base, "rendered": {"assetId": "ghost"}}, "unknown asset"),
        ({**base, "rendered": {"assetId": "img"}}, "rendered_video"),
        (
            {**base, "mode": "STATIC", "sourceAssetIds": ["img"], "rendered": {"assetId": "clip"}},
            "only valid on RENDERED",
        ),
        ({**base, "mode": "STATIC"}, "needs at least one image"),
    ]:
        with pytest.raises(ManifestValidationError) as ei:
            parse_manifest(doc(bad))  # type: ignore[arg-type]
        assert text in str(ei.value), str(ei.value)


def make_minimal_doc(clip_type: str) -> str:
    prov = {"kind": "creator_supplied", "source": "t", "license": "x", "licenseVerified": True}
    h = "a" * 64
    return json.dumps(
        {
            "schemaVersion": "1.1.0",
            "projectId": "m",
            "title": "t",
            "video": {"width": 1920, "height": 1080, "fps": 24},
            "narration": {"assetId": "n", "durationMs": 2000},
            "assets": [
                {"id": "n", "type": "audio", "path": "audio/n.wav", "sha256": h, "provenance": prov},
                {"id": "img", "type": "environment", "path": "images/i.png", "sha256": h, "provenance": prov},
                {"id": "clip", "type": clip_type, "path": "clips/c.mp4", "sha256": h, "provenance": prov},
            ],
            "scenes": [{"id": "sc", "title": "t", "narration": {"startMs": 0, "endMs": 2000}, "shotIds": ["r1"]}],
            "shots": [],
        }
    )


def test_scan_registers_assets_and_flags_realistic_mistakes(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "proj"
    make_image(root / "images/Harbour Dawn (v2).png", (10, 20, 30), size=(1280, 720))  # small, odd name
    make_image(root / "images/Harbour Dawn (v2).jpg", (10, 20, 30), size=(1920, 1080))  # slug collision
    make_layer(root / "layers/jonah.png")
    Image.new("RGB", (100, 100), (255, 0, 0)).save(root / "layers/no_alpha.png")  # opaque "layer"
    make_wav(root / "audio/narration.wav", 2.0)
    make_clip(tc, root / "clips/throw.mp4", red_s=1, blue_s=1)
    (root / "images/notes.txt").write_text("hi")
    (root / "images/broken.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"junk" * 20)
    res = scan_project(tc, root)
    ids = {a["id"]: a for a in res.assets}
    assert "harbour-dawn-v2" in ids and "harbour-dawn-v2-2" in ids  # unique, valid ids
    assert ids["throw"]["type"] == "rendered_video" and ids["jonah"]["type"] == "prop"
    assert all(a["provenance"]["licenseVerified"] is False for a in res.assets)
    assert len(ids["throw"]["sha256"]) == 64
    assert any("notes.txt" in p and "unsupported" in p for p in res.problems)
    assert any("broken.png" in p and "corrupt" in p for p in res.problems)
    assert any("no_alpha.png" in w and "no transparency" in w for w in res.warnings)
    assert any("not 1920x1080" in w for w in res.warnings) and any("below 1920x1080" in w for w in res.warnings)
    assert not (root / "images/notes.txt").stat().st_size == 0  # source untouched
    shutil.rmtree(root)


def test_scan_requires_audio(tc: Toolchain, tmp_path: Path) -> None:
    make_image(tmp_path / "p/images/a.png", (1, 2, 3))
    assert any("no audio found" in p for p in scan_project(tc, tmp_path / "p").problems)


def test_speed_slows_the_clip_down(tc: Toolchain, tmp_path: Path) -> None:
    """At speed 0.5 the 1 s red part lasts 2 s: red at 1.5 s (frame 36), blue after 2 s."""
    root = tmp_path / "p"
    m = project_with_clip(tc, root, {"assetId": "clip", "speed": 0.5}, seconds=3.0)
    out = tmp_path / "slow.mp4"
    render(m, root, out, RenderOptions(draft=True), tc)
    at_1_5 = mean_rgb(frame_png(tc, out, 36, tmp_path / "a.png"))
    at_2_5 = mean_rgb(frame_png(tc, out, 60, tmp_path / "b.png"))
    assert at_1_5[0] > at_1_5[2] + 100 and at_2_5[2] > at_2_5[0] + 100


def test_plan_builder_derives_durations_and_hashes(tc: Toolchain, tmp_path: Path) -> None:
    from storymotion_media.plan import build_manifest

    root = tmp_path / "p"
    make_wav(root / "audio/narration.wav", 6.0)
    make_clip(tc, root / "clips/a.mp4", red_s=3, blue_s=3)
    make_clip(tc, root / "clips/b.mp4", red_s=3, blue_s=3)
    plan = {
        "projectId": "mini",
        "title": "mini",
        "narration": "audio/narration.wav",
        "scenes": [
            {"id": "s-1", "title": "one", "shots": [{"id": "a", "startMs": 0, "clip": "clips/a.mp4"}]},
            {
                "id": "s-2",
                "title": "two",
                "shots": [
                    {
                        "id": "b",
                        "startMs": 2500,
                        "clip": "clips/b.mp4",
                        "transition": {"type": "fadeblack", "durationMs": 400},
                    }
                ],
            },
        ],
    }
    m = build_manifest(tc, root, plan)
    assert [(s.id, s.startMs, s.durationMs) for s in m.shots] == [("a", 0, 2500), ("b", 2500, 3500)]
    assert m.scenes[1].narration.startMs == 2500 and abs(m.narration.durationMs - 6000) <= 5
    assert all(len(a.sha256) == 64 for a in m.assets)
    plan["scenes"][0]["shots"][0]["clip"] = "clips/missing.mp4"
    with pytest.raises(ManifestValidationError, match="not found by the scan"):
        build_manifest(tc, root, plan)


def test_plan_line_cues_and_fit_speed(tc: Toolchain, tmp_path: Path) -> None:
    from storymotion_media.plan import build_manifest

    root = tmp_path / "p"
    make_wav(root / "audio/narration.wav", 8.0)
    make_clip(tc, root / "clips/a.mp4", red_s=2, blue_s=2)  # 4 s clip
    (root / "narration.timing.json").write_text(
        json.dumps(
            {
                "lines": [
                    {"line": 1, "speechStartMs": 500, "speechEndMs": 1000},
                    {"line": 2, "speechStartMs": 2000, "speechEndMs": 3000},
                ]
            }
        ),
        encoding="utf-8",
    )
    plan = {
        "projectId": "mini",
        "title": "mini",
        "narration": "audio/narration.wav",
        "scenes": [
            {"id": "s-1", "title": "one", "shots": [{"id": "a", "line": 1, "clip": "clips/a.mp4"}]},
            {"id": "s-2", "title": "two", "shots": [{"id": "b", "line": 2, "clip": "clips/a.mp4", "speed": "fit"}]},
        ],
    }
    m = build_manifest(tc, root, plan)
    assert [s.startMs for s in m.shots] == [0, 2000]  # line 1 -> 0, line 2 -> its speech start
    b = m.shots[1]
    assert b.rendered is not None and b.rendered.speed == pytest.approx(4000 / 6000, abs=0.01)  # 4 s clip fills 6 s
    plan["scenes"][1]["shots"][0]["line"] = 9
    with pytest.raises(ManifestValidationError, match="not in narration.timing.json"):
        build_manifest(tc, root, plan)


def test_plan_continue_resumes_the_clip_where_the_last_shot_stopped(tc: Toolchain, tmp_path: Path) -> None:
    from storymotion_media.plan import build_manifest

    root = tmp_path / "p"
    make_wav(root / "audio/narration.wav", 6.0)
    make_clip(tc, root / "clips/a.mp4", red_s=3, blue_s=3)
    plan = {
        "projectId": "mini",
        "title": "mini",
        "narration": "audio/narration.wav",
        "scenes": [
            {
                "id": "s-1",
                "title": "one",
                "shots": [
                    {"id": "a", "startMs": 0, "clip": "clips/a.mp4"},
                    {"id": "b", "startMs": 2500, "clip": "clips/a.mp4", "continue": True},
                ],
            }
        ],
    }
    m = build_manifest(tc, root, plan)
    assert m.shots[1].rendered is not None and m.shots[1].rendered.trimStartMs == 2500  # no jump back


def test_plan_transitions_finish_when_the_next_line_begins(tc: Toolchain, tmp_path: Path) -> None:
    from storymotion_media.plan import build_manifest

    root = tmp_path / "p"
    make_wav(root / "audio/narration.wav", 8.0)
    make_clip(tc, root / "clips/a.mp4", red_s=3, blue_s=3)
    (root / "narration.timing.json").write_text(
        json.dumps(
            {
                "lines": [
                    {"line": 1, "speechStartMs": 500, "speechEndMs": 2000},
                    {"line": 2, "speechStartMs": 2500, "speechEndMs": 5000},
                ]
            }
        ),
        encoding="utf-8",
    )
    plan = {
        "projectId": "mini",
        "title": "mini",
        "narration": "audio/narration.wav",
        "scenes": [
            {
                "id": "s-1",
                "title": "one",
                "shots": [
                    {"id": "a", "line": 1, "clip": "clips/a.mp4"},
                    {
                        "id": "b",
                        "line": 2,
                        "clip": "clips/a.mp4",
                        "transition": {"type": "crossfade", "durationMs": 500},
                    },
                ],
            }
        ],
    }
    m = build_manifest(tc, root, plan)
    b = m.shots[1]
    assert b.startMs + b.transition.durationMs == 2500  # fade runs 2000-2500 (the pause), done as line 2 starts
