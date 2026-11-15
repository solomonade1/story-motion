"""Locate and run FFmpeg/ffprobe safely.

Rules (Charter B3, QG TRUST-02): subprocesses always receive an argument *list* (never a shell
string), stdin is closed, every call has a timeout, and no background processes are left behind.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import ToolchainError

ENV_DIR = "STORYMOTION_FFMPEG_DIR"
_EXE = ".exe" if os.name == "nt" else ""


@dataclass(frozen=True)
class Toolchain:
    ffmpeg: Path
    ffprobe: Path
    version: str

    @property
    def description(self) -> str:
        return f"{self.version} ({self.ffmpeg})"


def _candidate_dirs() -> list[Path]:
    dirs: list[Path] = []
    env = os.environ.get(ENV_DIR)
    if env:
        dirs.append(Path(env))
    repo_root = Path(__file__).resolve().parents[3]
    dirs.append(repo_root / "tools" / "ffmpeg" / "bin")
    return dirs


def locate_tool(name: str) -> Path | None:
    for d in _candidate_dirs():
        cand = d / f"{name}{_EXE}"
        if cand.is_file():
            return cand
    found = shutil.which(name)
    return Path(found) if found else None


def run(argv: list[str | Path], *, timeout: float, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a tool without a shell. ``argv`` is a list; elements are never re-parsed."""
    str_argv = [str(a) for a in argv]
    try:
        return subprocess.run(  # noqa: S603 - argv list, shell=False, validated inputs
            str_argv,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=cwd,
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ToolchainError(
            f"Timed out after {timeout:.0f}s running {Path(str_argv[0]).name}. "
            "The process was terminated; no partial output was published."
        ) from exc
    except OSError as exc:
        raise ToolchainError(f"Could not start {str_argv[0]}: {exc}") from exc


def get_toolchain() -> Toolchain:
    """Return a verified toolchain or raise an actionable error (QG F-17)."""
    ffmpeg = locate_tool("ffmpeg")
    ffprobe = locate_tool("ffprobe")
    fix = f"Install FFmpeg (see README 'Setup') or set {ENV_DIR} to the folder that contains ffmpeg and ffprobe."
    if ffmpeg is None or ffprobe is None:
        missing = [n for n, p in (("ffmpeg", ffmpeg), ("ffprobe", ffprobe)) if p is None]
        raise ToolchainError(f"Required tool(s) not found: {', '.join(missing)}. {fix}")
    proc = run([ffmpeg, "-hide_banner", "-version"], timeout=30)
    if proc.returncode != 0 or not proc.stdout.startswith("ffmpeg version"):
        raise ToolchainError(f"{ffmpeg} did not run correctly (exit {proc.returncode}). {fix}")
    version = proc.stdout.splitlines()[0]
    tc = Toolchain(ffmpeg=ffmpeg, ffprobe=ffprobe, version=version)
    _require_features(tc)
    return tc


def _require_features(tc: Toolchain) -> None:
    needed_filters = ("zoompan", "xfade", "overlay", "rotate", "concat", "tpad", "blackdetect")
    proc = run([tc.ffmpeg, "-hide_banner", "-filters"], timeout=30)
    missing = [f for f in needed_filters if f" {f} " not in proc.stdout]
    enc = run([tc.ffmpeg, "-hide_banner", "-encoders"], timeout=30)
    for e in ("libx264", "aac"):
        if f" {e} " not in enc.stdout:
            missing.append(f"encoder:{e}")
    if missing:
        raise ToolchainError(
            f"This FFmpeg build lacks required features: {', '.join(missing)}. "
            "Use a full/essentials Windows build (README 'Setup')."
        )


def ffprobe_json(tc: Toolchain, path: Path, *, count_frames: bool = False) -> dict[str, Any]:
    argv: list[str | Path] = [
        tc.ffprobe,
        "-v",
        "error",
        "-protocol_whitelist",
        "file",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
    ]
    if count_frames:
        argv.insert(-2, "-count_frames")
    argv.append(path)
    proc = run(argv, timeout=120)
    if proc.returncode != 0:
        raise ToolchainError(f"ffprobe could not read {path.name}: {proc.stderr.strip()[:400]}")
    try:
        data: dict[str, Any] = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise ToolchainError(f"ffprobe returned unreadable output for {path.name}") from exc
    return data
