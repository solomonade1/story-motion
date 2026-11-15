"""Synthesise an ORIGINAL ambient bed (pad + drone + wind + sparse plucks) timed to the narration.

  python scripts/make_ambience.py projects/<name> [--seed 7] [--out audio/ambience.wav]

Everything is generated from scratch by this script, so there is no third-party licence. It is a
*placeholder-grade* bed: swap in a real licensed track by changing one line of plan.json.
The mood follows narration lines (needs narration.timing.json): sombre -> warm lift at the prayer ->
tension at the warning -> low, ominous close. Requires numpy (pip install -e ".[audio]").
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workers" / "media"))
from storymotion_media.toolchain import get_toolchain, run  # noqa: E402

SR = 44100
N = lambda name: {  # noqa: E731
    "D2": 73.42,
    "A2": 110.0,
    "Bb2": 116.54,
    "F2": 87.31,
    "G2": 98.0,
    "C3": 130.81,
    "D3": 146.83,
    "Eb3": 155.56,
    "F3": 174.61,
    "Ab3": 207.65,
    "A3": 220.0,
    "Bb3": 233.08,
    "C4": 261.63,
    "D4": 293.66,
    "E4": 329.63,
    "F4": 349.23,
    "G4": 392.0,
    "A4": 440.0,
    "Bb4": 466.16,
    "D5": 587.33,
}[name]

# chord sections: (first narration line, [notes], pad gain)
SECTIONS = [
    (1, ["D3", "F3", "A3", "E4"], 1.0),  # sickroom: D minor add9
    (3, ["Bb2", "D3", "F3", "A3"], 1.15),  # prayer: Bbmaj7, warmer
    (5, ["F2", "C3", "F3", "A3", "C4"], 1.1),  # "Scripture does not": F major, resolving
    (6, ["G2", "Bb2", "D3", "Ab3"], 1.1),  # Babylon: G minor with a flat-nine tension
    (7, ["D2", "Eb3", "A3", "C4"], 1.0),  # the next king: dissonant low D
    (8, ["D2", "A2", "D3"], 0.9),  # close: bare fifths
]
# plucked notes: (line, offset seconds from that line's start, note, gain)
PLUCKS = [
    (1, 0.9, "A4", 0.5),
    (2, 0.4, "F4", 0.45),
    (2, 2.6, "E4", 0.4),
    (3, 0.5, "D5", 0.5),
    (3, 2.4, "A4", 0.45),
    (3, 4.4, "F4", 0.45),
    (4, 1.0, "A4", 0.4),
    (5, 0.2, "D4", 0.5),
    (6, 1.2, "Ab3", 0.4),
    (6, 3.4, "G4", 0.35),
    (7, 0.8, "Eb3", 0.5),
    (7, 3.0, "D4", 0.4),
    (8, 0.3, "A3", 0.5),
]


def smooth_gate(t: np.ndarray, start: float, end: float, fade: float) -> np.ndarray:
    up = np.clip((t - start) / fade, 0, 1)
    down = np.clip((end - t) / fade, 0, 1)
    return np.minimum(up, down) ** 2 * (3 - 2 * np.minimum(up, down))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", type=Path)
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    timing = json.loads((proj / "narration.timing.json").read_text(encoding="utf-8"))
    starts = {ln["line"]: ln["speechStartMs"] / 1000 for ln in timing["lines"]}
    total = timing["totalMs"] / 1000 + 1.5
    t = np.arange(int(total * SR)) / SR
    rng = np.random.default_rng(a.seed)
    out = np.zeros((2, t.size))

    # drone: very low D, slow breathing
    breath = 0.75 + 0.25 * np.sin(2 * np.pi * 0.06 * t + 0.5)
    for ch, det in ((0, 0.0), (1, 0.07)):
        out[ch] += (
            0.30 * breath * (np.sin(2 * np.pi * (N("D2") + det) * t) + 0.5 * np.sin(2 * np.pi * (N("A2") + det) * t))
        )

    # chord pads with soft section crossfades
    ends = [starts[SECTIONS[i + 1][0]] if i + 1 < len(SECTIONS) else total for i in range(len(SECTIONS))]
    for (line, notes, gain), end in zip(SECTIONS, ends, strict=True):
        start = 0.0 if line == 1 else starts[line] - 1.0
        gate = smooth_gate(t, start - 1.2, end + 1.2, 2.4) * gain
        for k, nm in enumerate(notes):
            f = N(nm)
            for ch in (0, 1):
                for det in (-0.18, 0.0, 0.21):
                    ph = rng.uniform(0, 2 * np.pi)
                    lfo = 0.8 + 0.2 * np.sin(2 * np.pi * (0.05 + 0.013 * k) * t + ph)
                    out[ch] += (
                        0.045
                        * gate
                        * lfo
                        * (
                            np.sin(2 * np.pi * (f + det + 0.05 * ch) * t + ph)
                            + 0.28 * np.sin(2 * np.pi * 2 * (f + det) * t + ph)
                        )
                    )

    # plucks (soft attack, long decay)
    for line, off, nm, g in PLUCKS:
        t0 = starts[line] + off
        if t0 >= total - 0.5:
            continue
        tt = t - t0
        env = np.where(tt >= 0, np.minimum(tt / 0.012, 1) * np.exp(-np.maximum(tt, 0) / 1.5), 0)
        f = N(nm)
        tone = (
            np.sin(2 * np.pi * f * tt) + 0.35 * np.sin(2 * np.pi * 2 * f * tt) + 0.12 * np.sin(2 * np.pi * 3 * f * tt)
        )
        pan = rng.uniform(0.35, 0.65)
        out[0] += 0.10 * g * env * tone * (1 - pan)
        out[1] += 0.10 * g * env * tone * pan

    # wind: low-passed noise with slow swells (stronger at the Babylon / next-king parts)
    for ch in (0, 1):
        noise = rng.standard_normal(t.size)
        k = 0.0035
        y = np.empty_like(noise)
        acc = 0.0
        for i in range(noise.size):  # one-pole low-pass
            acc += k * (noise[i] - acc)
            y[i] = acc
        swell = 0.5 + 0.5 * np.sin(2 * np.pi * 0.09 * t + ch)
        weight = 0.6 + 0.8 * smooth_gate(t, starts[6] - 1, total, 3.0)
        out[ch] += 6.0 * y * swell * weight * 0.5

    # global fades, peak normalise
    out *= (smooth_gate(t, 0.0, total, 1.8) * np.minimum(1, (total - t) / 3.0).clip(0, 1))[None, :]
    out *= 0.6 / np.abs(out).max()
    pcm = (out.T * 32767).astype("<i2")

    dest = a.out or (proj / "audio" / "ambience.wav")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        raw = Path(td) / "raw.wav"
        with wave.open(str(raw), "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(pcm.tobytes())
        tc = get_toolchain()
        p = run(
            [
                tc.ffmpeg,
                "-v",
                "error",
                "-y",
                "-i",
                raw,
                "-af",
                "aecho=0.8:0.7:70|140|260:0.35|0.25|0.15,lowpass=f=7000,loudnorm=I=-24:TP=-3:LRA=7",
                "-ar",
                "48000",
                dest,
            ],
            timeout=300,
        )
        if p.returncode != 0:
            raise SystemExit(p.stderr[-400:])
    print(f"wrote {dest} ({total:.1f} s, original synthesis, seed {a.seed})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
