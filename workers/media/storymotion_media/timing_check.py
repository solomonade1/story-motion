"""Measure where hard cuts really land in a rendered video against where the storyboard put them (QG TIME-04).

The render report lists every shot's intended ``startFrame`` and its transition. For shots entered by a *cut* we find
the actual cut in the video by frame-to-frame scene change and report the deviation in output frames:
  TIME-04 threshold: median deviation <= 1 frame, max <= 2 frames [QA proposal].
Crossfades and dips are gradual, so they have no single frame to measure and are excluded (and counted).
This is a measurement of the file, not a claim about what a viewer perceives.
"""

from __future__ import annotations

import json
import re
import statistics
from pathlib import Path
from typing import Any

from .errors import MediaError
from .toolchain import Toolchain, run

MEDIAN_LIMIT_FRAMES = 1
MAX_LIMIT_FRAMES = 2


Detection = tuple[int, float]  # (frame number, scene-change score 0..1)
CANDIDATE_FLOOR = 0.05  # anything weaker is camera motion or noise
EXTRA_REPORT_FLOOR = 0.15  # an unexpected change at least this strong is reported as an extra cut


def detect_cut_frames(tc: Toolchain, video: Path, fps: int, *, threshold: float = CANDIDATE_FLOOR) -> list[Detection]:
    """Frames (0-based) where the picture changes, with how strongly. Weak changes are candidates only."""
    argv: list[str | Path] = [
        tc.ffmpeg, "-hide_banner", "-nostats", "-nostdin", "-i", video, "-an",
        "-vf", f"scale=320:-2,select='gt(scene,{threshold})',metadata=print:key=lavfi.scene_score,showinfo", "-f", "null", "-",
    ]
    proc = run(argv, timeout=900)
    if proc.returncode != 0:
        raise MediaError(f"Could not analyse {video.name}: {proc.stderr.strip()[-300:]}")
    times = [float(m) for m in re.findall(r"showinfo[^\n]*?pts_time:\s*([0-9.]+)", proc.stderr)]
    scores = [float(m) for m in re.findall(r"lavfi\.scene_score=([0-9.]+)", proc.stderr)]
    return sorted((round(t * fps), sc) for t, sc in zip(times, scores, strict=False))


def compare(expected: list[int], detected: list[Detection], *, window: int = 6) -> dict[str, Any]:
    """Pair each planned cut with the strongest picture change within ``window`` frames (nearest on a tie)."""
    pairs: list[dict[str, Any]] = []
    unmatched: list[int] = []
    free = list(detected)
    for e in expected:
        near = [d for d in free if abs(d[0] - e) <= window]
        if not near:
            unmatched.append(e)
            continue
        best = max(near, key=lambda d: (round(d[1], 3), -abs(d[0] - e)))
        free.remove(best)
        pairs.append({"expected": e, "detected": best[0], "deviation": best[0] - e, "score": round(best[1], 3)})
    devs = [abs(p["deviation"]) for p in pairs]
    extras = [f for f, sc in free if sc >= EXTRA_REPORT_FLOOR]
    ok = bool(expected) and not unmatched and statistics.median(devs) <= MEDIAN_LIMIT_FRAMES and max(devs) <= MAX_LIMIT_FRAMES
    return {
        "measured": len(pairs),
        "unmatchedExpected": unmatched,
        "extraDetected": extras,
        "weakestCutScore": min((p["score"] for p in pairs), default=None),
        "medianAbsDeviationFrames": statistics.median(devs) if devs else None,
        "maxAbsDeviationFrames": max(devs) if devs else None,
        "pairs": pairs,
        "withinTime04": ok,
    }


def check_render(tc: Toolchain, video: Path, report_path: Path) -> dict[str, Any]:
    """Compare a render against its own report. Returns a result dict (never claims more than was measured)."""
    report = json.loads(report_path.read_text(encoding="utf-8"))
    fps = int(report["fps"])
    shots = report["shots"]
    expected = [s["startFrame"] for i, s in enumerate(shots) if i > 0 and s["transitionIn"] == "cut"]
    gradual = sum(1 for i, s in enumerate(shots) if i > 0 and s["transitionIn"] != "cut")
    detected = detect_cut_frames(tc, video, fps)
    result = compare(expected, detected)
    result |= {
        "file": video.name, "fps": fps, "hardCutsExpected": len(expected), "gradualTransitionsNotMeasured": gradual,
        "thresholds": {"medianFrames": MEDIAN_LIMIT_FRAMES, "maxFrames": MAX_LIMIT_FRAMES},
    }
    if not expected:
        result["note"] = "No hard cuts in this render, so there is nothing to measure."
    return result


def draft_vs_final(draft: dict[str, Any], final: dict[str, Any]) -> dict[str, Any]:
    """Preview (draft) against export (final): the same cut should land on the same frame."""
    f = {p["expected"]: p["detected"] for p in final["pairs"]}
    diffs = [abs(p["detected"] - f[p["expected"]]) for p in draft["pairs"] if p["expected"] in f]
    return {
        "compared": len(diffs),
        "medianAbsDeviationFrames": statistics.median(diffs) if diffs else None,
        "maxAbsDeviationFrames": max(diffs) if diffs else None,
    }
