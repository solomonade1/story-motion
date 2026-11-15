"""Real FFmpeg renders of tiny synthetic projects. Evidence for OPS-01/02/03, ANIM-01/03, FR-RENDER-*."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import ImageChops, ImageStat

from helpers import cam, frame_png, make_project, mean_rgb
from storymotion_media.contracts import parse_manifest
from storymotion_media.errors import RenderError, ToolchainError
from storymotion_media.generation_demo import attach_generated_clip
from storymotion_media.ingest import sha256_file
from storymotion_media.preview import build_preview
from storymotion_media.providers.base import AnimationRequest as Req
from storymotion_media.providers.base import SourceImage, create_approval
from storymotion_media.providers.clip_factory import FfmpegMockClipFactory
from storymotion_media.providers.fake import FakeVideoProvider
from storymotion_media.providers.flow import download_verified, poll_until_done, submit_once
from storymotion_media.render import RenderOptions, render
from storymotion_media.toolchain import Toolchain, ffprobe_json

pytestmark = pytest.mark.ffmpeg


def _mean_diff(a, b) -> float:  # noqa: ANN001
    return sum(ImageStat.Stat(ImageChops.difference(a, b)).mean) / 3


def test_full_resolution_export_probes_as_spec(tc: Toolchain, tmp_path: Path) -> None:
    """OPS-01/02/03, FR-RENDER-002/005, FR-AUDIO-003."""
    m = make_project(tmp_path / "p", seconds=6.0, fade_ms=500)
    out = tmp_path / "o" / "mini.mp4"
    rep = render(m, tmp_path / "p", out, RenderOptions(), tc)
    data = ffprobe_json(tc, out, count_frames=True)
    v = next(s for s in data["streams"] if s["codec_type"] == "video")
    a = next(s for s in data["streams"] if s["codec_type"] == "audio")
    assert (v["codec_name"], v["width"], v["height"], v["pix_fmt"]) == ("h264", 1920, 1080, "yuv420p")
    assert v["avg_frame_rate"] == "24/1" and int(v["nb_read_frames"]) == 144
    assert (a["codec_name"], int(a["sample_rate"]), a["channels"]) == ("aac", 48000, 2)
    assert abs(float(data["format"]["duration"]) * 1000 - 6000) <= 250
    assert rep.verification["problems"] == [] and rep.verification["unplannedBlack"] == []
    assert rep.output["sha256"] == sha256_file(out)
    assert not list(out.parent.glob(".work-*"))  # temp files cleaned up


def test_cut_lands_exactly_on_the_expected_frame(tc: Toolchain, tmp_path: Path) -> None:
    """TIME-04 (local, render-only): the cut onset is on the quantised narration boundary."""
    m = make_project(tmp_path / "p", seconds=6.0)  # shot 2 starts at 2000 ms -> frame 48
    out = tmp_path / "cut.mp4"
    render(m, tmp_path / "p", out, RenderOptions(draft=True), tc)
    before = mean_rgb(frame_png(tc, out, 47, tmp_path / "f47.png"))
    after = mean_rgb(frame_png(tc, out, 48, tmp_path / "f48.png"))
    assert before[0] > before[2] + 40  # still the red shot
    assert after[2] > after[0] + 40  # first frame of the blue shot


def test_cinematic_moves_static_holds_and_no_black_borders(tc: Toolchain, tmp_path: Path) -> None:
    """ANIM-01 (mini sample): visible directional motion, nothing black at the edges."""
    m = make_project(tmp_path / "p", seconds=6.0)
    out = tmp_path / "m.mp4"
    render(m, tmp_path / "p", out, RenderOptions(), tc)
    f0 = frame_png(tc, out, 2, tmp_path / "c0.png")
    f1 = frame_png(tc, out, 44, tmp_path / "c1.png")  # near the end of the 48-frame cinematic shot
    assert _mean_diff(f0, f1) > 5  # camera moved (measured ~28 on this fixture)
    s0 = frame_png(tc, out, 52, tmp_path / "s0.png")
    s1 = frame_png(tc, out, 90, tmp_path / "s1.png")
    # lossy encode => not bit-identical; measured static noise is ~0.0002 vs ~28 for real motion
    assert _mean_diff(s0, s1) < 0.5  # static shot truly holds
    for f in (f0, f1):
        w, h = f.size
        for xy in ((2, 2), (w - 3, 2), (2, h - 3), (w - 3, h - 3)):
            assert sum(f.getpixel(xy)) > 120  # not a black border


def test_layered_layer_moves_between_start_and_end(tc: Toolchain, tmp_path: Path) -> None:
    m = make_project(tmp_path / "p", seconds=6.0)
    out = tmp_path / "l.mp4"
    render(m, tmp_path / "p", out, RenderOptions(draft=True), tc)

    def yellow_x(img) -> float:  # noqa: ANN001
        w, h = img.size
        xs = [
            x
            for x in range(0, w, 4)
            for y in range(0, h, 4)
            if (p := img.getpixel((x, y)))[0] > 200 and p[1] > 200 and p[2] < 90
        ]
        return sum(xs) / len(xs)

    early = yellow_x(frame_png(tc, out, 100, tmp_path / "e.png"))
    late = yellow_x(frame_png(tc, out, 140, tmp_path / "l.png"))
    assert late > early + 20  # moved left -> right (0.2 -> 0.8 of frame width)


def test_generative_without_clip_falls_back_visibly_and_makes_no_provider_call(tc: Toolchain, tmp_path: Path) -> None:
    """ANIM-03: never silently change a paid mode; report the fallback."""
    shots = [
        {
            "id": "g1",
            "sceneId": "sc",
            "startMs": 0,
            "durationMs": 3000,
            "mode": "GENERATIVE",
            "fallbackMode": "CINEMATIC",
            "sourceAssetIds": ["a"],
            "camera": cam(),
            "generation": {"providerProfileId": "mock-video"},
        },
        {"id": "g2", "sceneId": "sc", "startMs": 3000, "durationMs": 3000, "mode": "STATIC", "sourceAssetIds": ["b"]},
    ]
    root = tmp_path / "p"
    m = make_project(root, shots=shots)
    rep = render(m, root, tmp_path / "g.mp4", RenderOptions(draft=True), tc)
    assert rep.fallbacks == [{"shot": "g1", "usedMode": "CINEMATIC", "reason": "no generated clip attached"}]
    assert any("No provider request was made" in w for w in rep.warnings)
    assert rep.shots[0]["declaredMode"] == "GENERATIVE" and rep.shots[0]["renderedMode"] == "CINEMATIC"


def test_mock_provider_clip_is_incorporated_only_when_approved(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    shots = [
        {
            "id": "g1",
            "sceneId": "sc",
            "startMs": 0,
            "durationMs": 3000,
            "mode": "GENERATIVE",
            "fallbackMode": "CINEMATIC",
            "sourceAssetIds": ["a", "dot"],
            "camera": cam(),
            "generation": {"providerProfileId": "mock-video"},
        },
        {"id": "g2", "sceneId": "sc", "startMs": 3000, "durationMs": 3000, "mode": "STATIC", "sourceAssetIds": ["b"]},
    ]
    m = make_project(root, shots=shots)
    # Flow: quote -> approval -> submit -> poll -> verified download (all MOCK, no network)
    req = Req(
        "g1",
        tuple(SourceImage(root / m.asset(i).path, m.asset(i).sha256) for i in ("a", "dot")),
        "Sailors throw Jonah",
        3000,
        1280,
        720,
    )
    prov = FakeVideoProvider(FfmpegMockClipFactory(tc), tmp_path / "prov")
    ref = submit_once(prov, req, create_approval(prov.quote(req), user_confirmed=True, approval_id="ap"))
    poll_until_done(prov, ref, sleep=lambda _s: None)
    art = download_verified(prov, tc, ref, req, tmp_path / "dl")
    rel = "gen/g1.mp4"
    (root / "gen").mkdir()
    (root / rel).write_bytes(art.path.read_bytes())

    pending = attach_generated_clip(m, "g1", rel, sha256_file(root / rel), approved=False)
    rep = render(pending, root, tmp_path / "pending.mp4", RenderOptions(draft=True), tc)
    assert rep.shots[0]["renderedMode"] == "CINEMATIC" and "not approved" in rep.fallbacks[0]["reason"]

    ok = attach_generated_clip(m, "g1", rel, sha256_file(root / rel), approved=True)
    rep = render(ok, root, tmp_path / "ok.mp4", RenderOptions(draft=True), tc)
    assert rep.shots[0]["renderedMode"] == "GENERATIVE" and not rep.fallbacks
    assert len(prov.charges) == 1 and prov.total_charged_micro_usd == 150_000


def test_render_is_bit_reproducible_on_this_machine(tc: Toolchain, tmp_path: Path) -> None:
    m = make_project(tmp_path / "p", seconds=4.0)
    a = render(m, tmp_path / "p", tmp_path / "a.mp4", RenderOptions(draft=True), tc)
    b = render(m, tmp_path / "p", tmp_path / "b.mp4", RenderOptions(draft=True), tc)
    assert a.output["sha256"] == b.output["sha256"]


def test_crossfade_and_fadeblack_keep_exact_total_frames(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    shots = [
        {
            "id": "s1",
            "sceneId": "sc",
            "startMs": 0,
            "durationMs": 2000,
            "mode": "CINEMATIC",
            "sourceAssetIds": ["a"],
            "camera": cam(),
        },
        {
            "id": "s2",
            "sceneId": "sc",
            "startMs": 2000,
            "durationMs": 2000,
            "mode": "STATIC",
            "sourceAssetIds": ["b"],
            "transition": {"type": "crossfade", "durationMs": 500},
        },
        {
            "id": "s3",
            "sceneId": "sc",
            "startMs": 4000,
            "durationMs": 2000,
            "mode": "STATIC",
            "sourceAssetIds": ["c"],
            "transition": {"type": "fadeblack", "durationMs": 600},
        },
    ]
    m = make_project(root, shots=shots)
    rep = render(m, root, tmp_path / "x.mp4", RenderOptions(draft=True), tc)
    assert rep.verification["video"]["frames"] == 144
    mid = mean_rgb(frame_png(tc, tmp_path / "x.mp4", 48 + 6, tmp_path / "mid.png"))
    assert mid[0] > 40 and mid[2] > 60  # mid-crossfade shows both red and blue contributions


def test_preview_page_states_proxy_fidelity(tc: Toolchain, tmp_path: Path) -> None:
    """FR-TIME-005 / TIME-07: preview is labelled as a proxy and works from local files only."""
    m = make_project(tmp_path / "p")
    page, rep = build_preview(m, tmp_path / "p", tmp_path / "prev", tc)
    html = page.read_text(encoding="utf-8")
    assert "proxy fidelity" in html and "preview_draft.mp4" in html and html.count("play from here") == 3
    assert "http://" not in html and "https://" not in html  # no remote resources
    assert (rep.width, rep.height) == (640, 360)


def test_manifest_roundtrip_json_is_stable() -> None:
    m = parse_manifest(
        json.dumps(json.loads((Path(__file__).parents[1] / "fixtures/jonah/manifest.json").read_text(encoding="utf-8")))
    )
    assert parse_manifest(m.model_dump_json()) == m


def test_existing_output_is_not_overwritten_by_default(tc: Toolchain, tmp_path: Path) -> None:
    m = make_project(tmp_path / "p", seconds=3.0)
    out = tmp_path / "keep.mp4"
    out.write_bytes(b"PRECIOUS")
    with pytest.raises(RenderError, match="already exists"):
        render(m, tmp_path / "p", out, RenderOptions(draft=True), tc)
    assert out.read_bytes() == b"PRECIOUS"


def test_step_timeout_kills_ffmpeg_and_publishes_nothing(tc: Toolchain, tmp_path: Path) -> None:
    """F-09 spirit / OPS-04: a killed render leaves no published output and no temp folder."""
    m = make_project(tmp_path / "p", seconds=3.0)
    out = tmp_path / "t.mp4"
    with pytest.raises(ToolchainError, match="Timed out"):
        render(m, tmp_path / "p", out, RenderOptions(draft=True, step_timeout_s=0.01), tc)
    assert not out.exists() and not list(tmp_path.glob(".work-*"))


def test_layered_camera_rotation_render_is_reproducible(tc: Toolchain, tmp_path: Path) -> None:
    """End-to-end reproducibility smoke test for camera + rotating layer. NOTE: this tiny clip is
    NOT sensitive to the c=none defect (mutation-checked); the Jonah-shot test below is."""
    root = tmp_path / "p"
    shots = [
        {
            "id": "s1",
            "sceneId": "sc",
            "startMs": 0,
            "durationMs": 3000,
            "mode": "LAYERED",
            "sourceAssetIds": ["a"],
            "camera": cam(1.0, 1.15),
            "layers": [
                {
                    "assetId": "dot",
                    "start": {"x": 0.3, "y": 0.5, "widthFrac": 0.34, "rotateDeg": -4},
                    "end": {"x": 0.7, "y": 0.5, "widthFrac": 0.36, "rotateDeg": 4},
                    "swayDeg": 9,
                    "swayPeriodMs": 2100,
                }
            ],
        }
    ]
    m = make_project(root, shots=shots, seconds=3.0)
    a = render(m, root, tmp_path / "a.mp4", RenderOptions(), tc)
    b = render(m, root, tmp_path / "b.mp4", RenderOptions(), tc)
    assert a.output["sha256"] == b.output["sha256"]


def test_jonah_layered_shots_are_pixel_reproducible_before_encoding(tc: Toolchain) -> None:
    """Regression for the rotate c=none defect. On the real Jonah shots 03/12 (zoompan camera +
    rotating layer) 23-204 of ~200 frames differed run to run before the fix (mutation-checked:
    this test fails with c=none). Compares per-frame hashes of the filter output over 3 runs."""
    from storymotion_media.contracts import load_manifest
    from storymotion_media.ingest import verify_manifest_assets
    from storymotion_media.render import build_segment_argv, plan_shots
    from storymotion_media.toolchain import run

    root = Path(__file__).parents[1] / "fixtures" / "jonah"
    m = load_manifest(root / "manifest.json")
    infos = verify_manifest_assets(tc, m, root)
    plan = next(p for p in plan_shots(m, 24) if p.shot.id == "shot-03")
    runs = []
    for _ in range(3):
        argv = [str(x) for x in build_segment_argv(tc, plan, m, infos, 1920, 1080, 24, Path("unused.mp4"))]
        argv = [*argv[: argv.index("-c:v")], "-f", "framemd5", "-"]  # hash raw filter output
        proc = run(argv, timeout=600)
        assert proc.returncode == 0, proc.stderr[-300:]
        runs.append([ln.split(",")[-1] for ln in proc.stdout.splitlines() if not ln.startswith("#")])
    assert len(runs[0]) == plan.total_frames
    assert runs[0] == runs[1] == runs[2]
