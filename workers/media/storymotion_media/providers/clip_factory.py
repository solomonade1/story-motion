"""Local synthesis of a MOCK 'generated action clip' for the fake provider.

This only exists so the pipeline can demonstrate how an approved cloud-generated clip is
incorporated without a live paid call. The motion (a silhouette arcing over a rail) is a crude
procedural stand-in; it is NOT evidence of any model's action quality.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from ..errors import RenderError
from ..toolchain import Toolchain, run
from .base import AnimationRequest

FPS = 24


def _badge(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (300, 26), (120, 0, 0, 190))
    ImageDraw.Draw(img).text(
        (8, 5), "MOCK PROVIDER OUTPUT - not AI", fill=(255, 255, 255, 255), font=ImageFont.load_default(size=13)
    )
    img.save(path)


class FfmpegMockClipFactory:
    def __init__(self, toolchain: Toolchain) -> None:
        self._tc = toolchain

    def __call__(self, request: AnimationRequest, out: Path) -> None:
        w, h, d = request.width, request.height, request.duration_ms / 1000
        n = request.duration_ms * FPS // 1000
        bg = request.sources[0].path
        with tempfile.TemporaryDirectory() as t:
            badge = Path(t) / "badge.png"
            _badge(badge)
            argv: list[str | Path] = [self._tc.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
            for p in (bg, *(s.path for s in request.sources[1:2]), badge):
                argv += ["-protocol_whitelist", "file", "-loop", "1", "-framerate", str(FPS), "-i", p]
            cover = f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,crop={w}:{h},setsar=1"
            if len(request.sources) >= 2:
                pp = f"min(t/{d:.4f},1)"
                graph = (
                    f"[0:v]{cover}[bg];"
                    f"[1:v]format=rgba,scale=-2:{int(h * 0.38)},"
                    f"rotate=a='2*PI*1.5*{pp}':ow='hypot(iw,ih)':oh='ow':c=black@0[s];"
                    f"[bg][s]overlay=x='main_w*(0.46+0.22*{pp})-overlay_w/2':"
                    f"y='main_h*(0.40-0.18*sin(PI*{pp})+0.62*{pp}*{pp})-overlay_h/2':eval=frame[a];"
                    f"[a][2:v]overlay=x=10:y=main_h-36,format=yuv420p[v]"
                )
            else:
                graph = f"[0:v]{cover}[a];[a][1:v]overlay=x=10:y=main_h-36,format=yuv420p[v]"
            argv += [
                "-filter_complex",
                graph,
                "-map",
                "[v]",
                "-frames:v",
                str(n),
                "-r",
                str(FPS),
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "18",
                "-pix_fmt",
                "yuv420p",
                "-fflags",
                "+bitexact",
                "-flags:v",
                "+bitexact",
                "-map_metadata",
                "-1",
                "-an",
                out,
            ]
            proc = run(argv, timeout=600)
        if proc.returncode != 0:
            raise RenderError(f"mock clip synthesis failed: {proc.stderr.strip()[-400:]}")
