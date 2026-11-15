"""Post-render validation (FR-RENDER-005, QG OPS-01..03): probe, decode, black-frame scan."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .errors import OutputValidationError
from .toolchain import Toolchain, ffprobe_json, run

DURATION_TOLERANCE_MS = 250  # QG OPS-02 [QA proposal]


def _detect_black(tc: Toolchain, path: Path) -> list[tuple[float, float]]:
    proc = run(
        [
            tc.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-protocol_whitelist",
            "file",
            "-i",
            path,
            "-vf",
            "blackdetect=d=0.3:pix_th=0.08",
            "-an",
            "-f",
            "null",
            "-",
        ],
        timeout=600,
    )
    segs = []
    for m in re.finditer(r"black_start:([\d.]+)\s+black_end:([\d.]+)", proc.stderr):
        segs.append((float(m.group(1)), float(m.group(2))))
    return segs


def verify_output(
    tc: Toolchain,
    path: Path,
    *,
    expected_w: int,
    expected_h: int,
    expected_fps: int,
    expected_frames: int,
    narration_ms: int,
    allowed_black: list[tuple[float, float]],
) -> dict[str, Any]:
    problems: list[str] = []
    if not path.is_file() or path.stat().st_size == 0:
        raise OutputValidationError(["output file is missing or empty"])
    data = ffprobe_json(tc, path, count_frames=True)
    streams = data["streams"]
    vids = [s for s in streams if s["codec_type"] == "video"]
    auds = [s for s in streams if s["codec_type"] == "audio"]
    fmt = data["format"]
    info: dict[str, Any] = {"format": fmt.get("format_name"), "streams": len(streams)}

    if len(vids) != 1:
        problems.append(f"expected 1 video stream, found {len(vids)}")
    if len(auds) != 1:
        problems.append(f"expected 1 audio stream, found {len(auds)}")
    if vids:
        v = vids[0]
        num, den = v["avg_frame_rate"].split("/")
        fps = float(num) / float(den)
        nb = int(v.get("nb_read_frames", -1))
        info["video"] = {
            "codec": v["codec_name"],
            "profile": v.get("profile"),
            "width": v["width"],
            "height": v["height"],
            "fps": round(fps, 3),
            "pix_fmt": v["pix_fmt"],
            "frames": nb,
            "duration_s": float(v.get("duration", 0)),
            "start_time": float(v.get("start_time", 0)),
        }
        if v["codec_name"] != "h264":
            problems.append(f"video codec is {v['codec_name']}, expected h264")
        if (v["width"], v["height"]) != (expected_w, expected_h):
            problems.append(f"video is {v['width']}x{v['height']}, expected {expected_w}x{expected_h}")
        if abs(fps - expected_fps) > 0.01:
            problems.append(f"video fps is {fps:.3f}, expected {expected_fps}")
        if nb != expected_frames:
            problems.append(f"decoded {nb} frames, expected {expected_frames}")
    if auds:
        a = auds[0]
        info["audio"] = {
            "codec": a["codec_name"],
            "sample_rate": int(a["sample_rate"]),
            "channels": a["channels"],
            "duration_s": float(a.get("duration", 0)),
            "start_time": float(a.get("start_time", 0)),
        }
        if a["codec_name"] != "aac":
            problems.append(f"audio codec is {a['codec_name']}, expected aac")
        if int(a["sample_rate"]) != 48000 or a["channels"] != 2:
            problems.append("audio must be 48 kHz stereo (FR-AUDIO-003)")
        delta_ms = abs(float(a.get("duration", 0)) * 1000 - narration_ms)
        info["audioVsNarrationDeltaMs"] = round(delta_ms, 1)
        if delta_ms > DURATION_TOLERANCE_MS:
            problems.append(f"audio is {delta_ms:.0f} ms off the narration length (>{DURATION_TOLERANCE_MS})")
    if vids and auds:
        dv, da = float(vids[0].get("duration", 0)), float(auds[0].get("duration", 0))
        info["videoVsAudioDeltaMs"] = round(abs(dv - da) * 1000, 1)
        if abs(dv - da) * 1000 > DURATION_TOLERANCE_MS:
            problems.append(f"video/audio durations differ by {abs(dv - da) * 1000:.0f} ms")
        sdelta = abs(float(vids[0].get("start_time", 0)) - float(auds[0].get("start_time", 0)))
        info["startOffsetMs"] = round(sdelta * 1000, 1)

    if auds:  # digital clipping check on the delivered audio (QG TIME-06)
        vd = run(
            [
                tc.ffmpeg,
                "-hide_banner",
                "-nostdin",
                "-protocol_whitelist",
                "file",
                "-i",
                path,
                "-vn",
                "-af",
                "volumedetect",
                "-f",
                "null",
                "-",
            ],
            timeout=300,
        )
        mx = re.search(r"max_volume:\s*(-?[\d.]+) dB", vd.stderr)
        mean = re.search(r"mean_volume:\s*(-?[\d.]+) dB", vd.stderr)
        if mx:
            info.setdefault("audio", {})["peak_db"] = float(mx.group(1))
            if mean:
                info["audio"]["mean_db"] = float(mean.group(1))
            if float(mx.group(1)) > -0.3:
                problems.append(f"audio peak is {mx.group(1)} dB: digital clipping risk")

    # Full decode must succeed with no errors (truncation/corruption check).
    dec = run(
        [
            tc.ffmpeg,
            "-hide_banner",
            "-nostdin",
            "-v",
            "error",
            "-xerror",
            "-protocol_whitelist",
            "file",
            "-i",
            path,
            "-f",
            "null",
            "-",
        ],
        timeout=600,
    )
    info["decodeErrors"] = dec.stderr.strip()[:400]
    if dec.returncode != 0 or dec.stderr.strip():
        problems.append(f"full decode reported errors: {dec.stderr.strip()[:200]}")

    black = _detect_black(tc, path)
    unplanned = [(s, e) for s, e in black if not any(s >= lo - 0.05 and e <= hi + 0.05 for lo, hi in allowed_black)]
    info["blackSegments"] = black
    info["unplannedBlack"] = unplanned
    if unplanned:
        problems.append(f"unplanned black segments: {unplanned}")

    info["problems"] = problems
    if problems:
        raise OutputValidationError(problems)
    return info
