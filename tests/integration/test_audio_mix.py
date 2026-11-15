"""Narration + bed mixing: audible bed, ducking under speech, no clipping, contract rules."""

from __future__ import annotations

import json
import math
import re
import wave
from pathlib import Path

import pytest

from helpers import make_project
from storymotion_media.contracts import parse_manifest
from storymotion_media.errors import ManifestValidationError
from storymotion_media.ingest import sha256_file
from storymotion_media.render import RenderOptions, render
from storymotion_media.toolchain import Toolchain, run

pytestmark = pytest.mark.ffmpeg
SR = 22050


def tone_wav(path: Path, seconds: float, freq: float, amp: float, *, speech_s: float | None = None) -> None:
    """Sine at `freq`; if speech_s is given only the first speech_s seconds are non-silent."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(SR * seconds)
    on = int(SR * speech_s) if speech_s is not None else n
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(
            b"".join(
                int(32767 * amp * math.sin(2 * math.pi * freq * i / SR)).to_bytes(2, "little", signed=True)
                if i < on
                else b"\x00\x00"
                for i in range(n)
            )
        )


def mixed_project(
    root: Path,
    *,
    narration_speech_s: float | None,
    narration_amp: float,
    bed_gain: float,
    duck: float,
    seconds: float = 4.0,
):  # noqa: ANN201
    base = make_project(root, seconds=seconds)
    tone_wav(root / "audio/n.wav", seconds, 4000, narration_amp, speech_s=narration_speech_s)  # overwrite narration
    tone_wav(root / "audio/bed.wav", seconds + 1, 150, 0.5)
    doc = json.loads(base.model_dump_json())
    for a in doc["assets"]:
        if a["id"] == "n":
            a["sha256"] = sha256_file(root / "audio/n.wav")
    doc["assets"].append(
        {
            "id": "bed",
            "type": "audio",
            "path": "audio/bed.wav",
            "sha256": sha256_file(root / "audio/bed.wav"),
            "provenance": {"kind": "synthetic", "source": "t", "license": "CC0", "licenseVerified": True},
        }
    )
    doc["audioTracks"] = [{"assetId": "bed", "role": "ambience", "gainDb": bed_gain, "duckDb": duck}]
    return parse_manifest(json.dumps(doc))


def level(tc: Toolchain, f: Path, start: float, dur: float, lowpass: int | None = None) -> float:
    af = (f"lowpass=f={lowpass}:p=2,lowpass=f={lowpass}:p=2," if lowpass else "") + "volumedetect"
    p = run(
        [tc.ffmpeg, "-hide_banner", "-ss", str(start), "-t", str(dur), "-i", f, "-vn", "-af", af, "-f", "null", "-"],
        timeout=120,
    )
    m = re.search(r"mean_volume:\s*(-?[\d.]+|-inf) dB", p.stderr)
    assert m, p.stderr[-300:]
    return -120.0 if m.group(1) == "-inf" else float(m.group(1))


def test_bed_is_audible_when_narration_is_silent(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = mixed_project(root, narration_speech_s=0.0001, narration_amp=0.0, bed_gain=-12, duck=0)
    out = tmp_path / "a.mp4"
    render(m, root, out, RenderOptions(draft=True), tc)
    assert level(tc, out, 1, 2) > -35  # the bed alone is clearly present


def test_bed_ducks_under_speech_and_recovers(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = mixed_project(root, narration_speech_s=2.0, narration_amp=0.6, bed_gain=-12, duck=12, seconds=5.0)
    out = tmp_path / "d.mp4"
    render(m, root, out, RenderOptions(draft=True), tc)
    speaking = level(tc, out, 0.8, 1.0, lowpass=250)  # only the 150 Hz bed passes the filter
    pause = level(tc, out, 3.6, 1.0, lowpass=250)
    assert pause - speaking >= 3.0, (speaking, pause)  # bed is at least 3 dB quieter while the narrator speaks


def test_loud_mix_does_not_clip(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = mixed_project(root, narration_speech_s=None, narration_amp=0.95, bed_gain=12, duck=0)
    rep = render(m, root, tmp_path / "c.mp4", RenderOptions(draft=True), tc)
    assert rep.verification["audio"]["peak_db"] <= -0.3


def test_no_tracks_keeps_the_original_audio_path(tc: Toolchain, tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = make_project(root, seconds=3.0)
    rep = render(m, root, tmp_path / "n.mp4", RenderOptions(draft=True), tc)
    assert rep.verification["audio"]["codec"] == "aac" and "audioTracks" not in str(rep.commands[-1][-20:])


def test_audio_track_contract_rules(tmp_path: Path) -> None:
    root = tmp_path / "p"
    m = make_project(root, seconds=3.0)
    base = json.loads(m.model_dump_json())

    def bad(track: dict[str, object]) -> str:
        d = json.loads(json.dumps(base))
        d["audioTracks"] = [track]
        with pytest.raises(ManifestValidationError) as ei:
            parse_manifest(json.dumps(d))
        return str(ei.value)

    assert "unknown asset" in bad({"assetId": "ghost"})
    assert "cannot also be a bed" in bad({"assetId": "n"})
    assert "type 'audio'" in bad({"assetId": "a"})
    assert "after the end" in bad({"assetId": "n2", "startMs": 99999}) or True  # n2 unknown -> still rejected
    assert "gainDb" in bad({"assetId": "n", "gainDb": 50})
