"""Minimal local preview path (FR-TIME-005, QG TIME-07): draft proxy render + static HTML page.

The page is a single local file that references the draft MP4 by relative path. It loads no
remote resources and states plainly that the preview is a low-resolution proxy.
"""

from __future__ import annotations

import html
from pathlib import Path

from .contracts import Manifest
from .render import RenderOptions, RenderReport, render
from .toolchain import Toolchain

_PAGE = """<!doctype html><meta charset="utf-8"><title>StoryMotion preview - {title}</title>
<style>body{{font:15px system-ui;margin:24px;max-width:960px}}
.warn{{background:#fff3cd;border:1px solid #e0c36a;padding:8px 12px;border-radius:6px}}
video{{width:100%;background:#000;margin:12px 0}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:4px 8px;text-align:left}}
button{{cursor:pointer}}</style>
<h1>{title}</h1>
<p class="warn"><b>Draft preview - proxy fidelity.</b> {w}x{h}, heavy compression. The final export is
1920x1080. Placeholder art / synthetic narration unless stated otherwise in the project provenance.</p>
<video id="v" src="{video}" controls></video>
<table><tr><th>Shot</th><th>Start</th><th>Mode</th><th>Action</th><th></th></tr>
{rows}</table>
<script>function seek(t){{var v=document.getElementById('v');v.currentTime=t;v.play();}}</script>
"""


def build_preview(
    manifest: Manifest, root: Path, out_dir: Path, tc: Toolchain, *, overwrite: bool = False
) -> tuple[Path, RenderReport]:
    out_dir.mkdir(parents=True, exist_ok=True)
    video = out_dir / "preview_draft.mp4"
    report = render(manifest, root, video, RenderOptions(draft=True, overwrite=overwrite), tc)
    modes = {s["id"]: s["renderedMode"] for s in report.shots}
    rows = []
    for s in manifest.shots:
        label = modes[s.id] + ("" if modes[s.id] == s.mode else f" (fallback from {s.mode})")
        rows.append(
            f"<tr><td>{html.escape(s.id)}</td><td>{s.startMs / 1000:.2f}s</td><td>{html.escape(label)}</td>"
            f"<td>{html.escape(s.action)}</td>"
            f'<td><button onclick="seek({s.startMs / 1000:.3f})">play from here</button></td></tr>'
        )
    page = _PAGE.format(
        title=html.escape(manifest.title),
        video=html.escape(video.name),
        w=report.width,
        h=report.height,
        rows="\n".join(rows),
    )
    index = out_dir / "preview.html"
    index.write_text(page, encoding="utf-8")
    return index, report
