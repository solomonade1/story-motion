"""Build narration.wav from <project>/script.txt (one paragraph per line) with a LOCAL voice engine.

  python scripts/make_narration.py projects/<name> --engine piper --model tools/piper-voices/en_US-joe-medium.onnx
  python scripts/make_narration.py projects/<name> --engine sapi  [--voice "Microsoft David Desktop"]

Writes <project>/audio/narration.wav and <project>/narration.timing.json (per-line speech start/end, ms).
Offline; text is sent via stdin / a JSON file, never on a command line. Output is loudness-normalised
(single-pass EBU R128, -16 LUFS) unless --no-loudnorm.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workers" / "media"))

from storymotion_media.toolchain import get_toolchain, run  # noqa: E402

LEAD_MS, GAP_MS, TAIL_MS = 500, 500, 1200
SR = 22050


def synth_sapi(lines: list[str], tmp: Path, voice: str, rate: int) -> list[Path]:
    (tmp / "texts.json").write_text(json.dumps(lines), encoding="utf-8")
    subprocess.run(  # noqa: S603
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/tts_sapi.ps1"),
            "-TextsJson",
            str(tmp / "texts.json"),
            "-OutDir",
            str(tmp),
            "-Voice",
            voice,
            "-Rate",
            str(rate),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return [tmp / f"line-{i:02d}.wav" for i in range(len(lines))]


def synth_piper(lines: list[str], tmp: Path, model: Path, length_scale: float) -> list[Path]:
    outs = []
    for i, text in enumerate(lines):
        out = tmp / f"line-{i:02d}.wav"
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "piper", "-m", str(model), "-f", str(out), "--length-scale", str(length_scale)],
            input=text,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        outs.append(out)
    return outs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--engine", choices=["sapi", "piper"], default="sapi")
    ap.add_argument("--voice", default="Microsoft David Desktop")
    ap.add_argument("--rate", type=int, default=0)
    ap.add_argument("--model", type=Path, help="Piper .onnx model")
    ap.add_argument("--length-scale", type=float, default=1.0, help="Piper: >1 = slower")
    ap.add_argument("--no-loudnorm", action="store_true")
    ap.add_argument("--lines", type=int, default=0, help="only the first N lines (audition samples)")
    ap.add_argument("--out", type=Path, help="write the wav here instead of <project>/audio/narration.wav")
    a = ap.parse_args()
    proj = Path(a.project).resolve()
    lines = [ln.strip() for ln in (proj / "script.txt").read_text(encoding="utf-8").splitlines() if ln.strip()]
    if a.lines:
        lines = lines[: a.lines]
    silence = lambda ms: b"\x00\x00" * (SR * ms // 1000)  # noqa: E731
    pcm, timing, cursor = b"", [], 0
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        if a.engine == "piper":
            if not a.model:
                ap.error("--model is required for --engine piper")
            wavs = synth_piper(lines, tmp, a.model.resolve(), a.length_scale)
        else:
            wavs = synth_sapi(lines, tmp, a.voice, a.rate)
        for i, (text, w) in enumerate(zip(lines, wavs, strict=True)):
            with wave.open(str(w), "rb") as wf:
                assert (wf.getnchannels(), wf.getsampwidth(), wf.getframerate()) == (1, 2, SR), "unexpected format"
                data = wf.readframes(wf.getnframes())
            lead = LEAD_MS if i == 0 else 0
            trail = TAIL_MS if i == len(lines) - 1 else GAP_MS
            speech_ms = len(data) // 2 * 1000 // SR
            timing.append(
                {"line": i + 1, "text": text, "speechStartMs": cursor + lead, "speechEndMs": cursor + lead + speech_ms}
            )
            chunk = silence(lead) + data + silence(trail)
            cursor += len(chunk) // 2 * 1000 // SR
            pcm += chunk
        raw = tmp / "raw.wav"
        with wave.open(str(raw), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(pcm)
        dest = a.out or (proj / "audio" / "narration.wav")
        dest.parent.mkdir(parents=True, exist_ok=True)
        if a.no_loudnorm:
            dest.write_bytes(raw.read_bytes())
        else:
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
                    "loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar",
                    str(SR),
                    "-ac",
                    "1",
                    "-sample_fmt",
                    "s16",
                    dest,
                ],
                timeout=300,
            )
            if p.returncode != 0:
                raise SystemExit(f"loudnorm failed: {p.stderr[-300:]}")
    if not a.out:
        label = a.model.stem if a.engine == "piper" and a.model else a.voice
        (proj / "narration.timing.json").write_text(
            json.dumps({"engine": a.engine, "voice": label, "totalMs": cursor, "lines": timing}, indent=2),
            encoding="utf-8",
        )
    for t_ in timing:
        print(f"{t_['line']}: {t_['speechStartMs']:6d}-{t_['speechEndMs']:6d} ms  {t_['text'][:60]}")
    print(f"total {cursor} ms -> {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
