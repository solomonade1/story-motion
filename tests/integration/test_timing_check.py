"""Cut-timing measurement (QG TIME-04) on real renders, plus the pure comparison logic."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from test_studio_api import Client, server, wait_job  # noqa: F401  (fixture re-export)

from helpers import make_image, make_wav
from storymotion_media.cli import main
from storymotion_media.studio.api import ApiServer
from storymotion_media.timing_check import check_render, compare, draft_vs_final
from storymotion_media.toolchain import Toolchain


def test_compare_pairs_nearest_cuts_and_applies_the_time04_limits() -> None:
    ok = compare([48, 96, 144], [(48, 0.9), (97, 0.9), (143, 0.9)])
    assert ok["medianAbsDeviationFrames"] == 1 and ok["maxAbsDeviationFrames"] == 1 and ok["withinTime04"] is True
    late = compare([48, 96, 144], [(51, 0.9), (99, 0.9), (147, 0.9)])  # every cut 3 frames late
    assert late["withinTime04"] is False and late["maxAbsDeviationFrames"] == 3
    missing = compare([48, 96], [(48, 0.9)])
    assert missing["unmatchedExpected"] == [96] and missing["withinTime04"] is False  # a missing cut is never "fine"
    extra = compare([48], [(48, 0.9), (70, 0.4), (80, 0.07)])
    assert extra["extraDetected"] == [70] and extra["withinTime04"] is True  # weak motion (0.07) is not reported
    assert compare([], [(10, 0.9)])["withinTime04"] is False  # nothing expected: nothing proven
    # a faint cut between similar pictures wins over a stronger unrelated flicker only if it is the strongest nearby change
    faint = compare([100], [(100, 0.12), (102, 0.06)])
    assert faint["pairs"][0]["detected"] == 100 and faint["weakestCutScore"] == 0.12


def test_draft_vs_final_compares_the_same_cut_in_both_renders() -> None:
    d = {"pairs": [{"expected": 48, "detected": 48, "deviation": 0}, {"expected": 96, "detected": 97, "deviation": 1}]}
    f = {"pairs": [{"expected": 48, "detected": 48, "deviation": 0}, {"expected": 96, "detected": 96, "deviation": 0}]}
    assert draft_vs_final(d, f) == {"compared": 2, "medianAbsDeviationFrames": 0.5, "maxAbsDeviationFrames": 1}


@pytest.mark.ffmpeg
def test_hard_cuts_land_on_the_planned_frames_in_draft_and_final(
    server: tuple[ApiServer, Client, Path], tc: Toolchain, capsys: pytest.CaptureFixture[str]  # noqa: F811
) -> None:
    srv, c, root = server
    src = root / "src"
    hues = [(200, 30, 30), (30, 200, 30), (30, 30, 200), (200, 200, 30), (30, 200, 200)]
    for i, h in enumerate(hues):
        make_image(src / f"p{i}.png", h, size=(1920, 1080))
    make_wav(src / "voice.wav", 10.0)
    pid = c.call("POST", "/api/projects", {"name": "Timing"})[1]["projectId"]
    paths = [str(src / f"p{i}.png") for i in range(5)] + [str(src / "voice.wav")]
    assert wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/assets/import", {"paths": paths})[1]["id"])["state"] == "completed"
    by = {a["orig_name"]: a["id"] for a in c.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]}
    starts = [0, 1900, 4100, 6350, 8200]  # deliberately not on frame boundaries (24 fps = 41.67 ms)
    shots: list[dict[str, Any]] = []
    for i, s in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else 10000
        mode = "CINEMATIC" if i % 2 else "STATIC"
        shots.append({"id": f"s{i}", "startMs": s, "durationMs": end - s, "mode": mode, "imageAssetId": by[f"p{i}.png"], "preset": "slow-push-in"})
    sb = {"narrationAssetId": by["voice.wav"], "scenes": [{"id": "s", "title": "S", "shots": shots}]}
    assert c.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": sb})[0] == 200

    results = {}
    for draft in (True, False):
        done = wait_job(c, pid, c.call("POST", f"/api/projects/{pid}/storyboard/render", {"draft": draft})[1]["id"])
        assert done["state"] == "completed", done
        mp4 = srv.ws.project(pid).dir / "renders" / done["result"]["file"]
        results[draft] = check_render(tc, mp4, mp4.with_suffix(".json"))
    for r in results.values():
        assert r["hardCutsExpected"] == 4 and r["measured"] == 4 and r["unmatchedExpected"] == []
        assert r["withinTime04"] is True, r
        assert r["maxAbsDeviationFrames"] <= 1  # the renderer places cuts on the rounded frame: at most rounding noise
    assert draft_vs_final(results[True], results[False])["maxAbsDeviationFrames"] <= 1

    # the command-line tool reports the same thing and exits 0 when within the limits
    mp4 = next((srv.ws.project(pid).dir / "renders").glob("*-final.mp4"))
    assert main(["timing-check", str(mp4)]) == 0
    assert '"withinTime04": true' in capsys.readouterr().out
