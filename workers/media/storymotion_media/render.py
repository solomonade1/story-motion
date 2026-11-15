"""Deterministic local render: manifest -> per-shot segments -> composed MP4 (PRD 10.4).

Design notes
- Narration is the clock. Shot boundaries are integer ms in the manifest; they are quantised to
  frame indices once (``frame_edges``) and every later step works in whole frames.
- A shot's segment is ``body + tail`` frames. ``tail`` is extra footage consumed by an outgoing
  crossfade, so the *onset* of every transition lands exactly on the next shot's start frame.
- Only numbers (never user strings) are interpolated into filtergraphs. File names are passed as
  ``-i`` arguments, each behind ``-protocol_whitelist file`` so a hostile file cannot make FFmpeg
  read the network (QG TRUST-02).
- GENERATIVE shots NEVER call a provider here. They render an already-downloaded, approved clip
  or fall back to the declared local mode, and the fallback is reported (QG ANIM-03).
"""

from __future__ import annotations

import os
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import PROCESSOR_VERSION
from .contracts import AudioTrack, Camera, Easing, Layer, Manifest, Shot
from .errors import RenderCancelled, RenderError
from .ingest import AssetInfo, resolve_in_root, sha256_file, verify_manifest_assets
from .toolchain import Toolchain, get_toolchain, run
from .verify_output import verify_output

WORK_MARKER = ".storymotion-work"
DRAFT_SIZE = (640, 360)


@dataclass(frozen=True)
class RenderOptions:
    draft: bool = False
    overwrite: bool = False
    keep_work: bool = False
    step_timeout_s: float = 900.0
    progress: Callable[[float, str], None] | None = None  # (fraction 0..1, message); called between steps
    cancel: threading.Event | None = None  # checked between steps; a running FFmpeg step is not interrupted


@dataclass
class ShotPlan:
    shot: Shot
    index: int
    start_frame: int
    body_frames: int
    tail_frames: int
    effective_mode: str
    fallback_reason: str | None = None

    @property
    def total_frames(self) -> int:
        return self.body_frames + self.tail_frames


@dataclass
class RenderReport:
    manifest_project: str
    processor_version: str
    toolchain: str
    draft: bool
    width: int
    height: int
    fps: int
    shots: list[dict[str, Any]] = field(default_factory=list)
    fallbacks: list[dict[str, str]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    commands: list[list[str]] = field(default_factory=list)
    timings_s: dict[str, float] = field(default_factory=dict)
    output: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    assets: list[dict[str, Any]] = field(default_factory=list)
    max_cut_quantisation_error_ms: float = 0.0


# ---------------------------------------------------------------- timing


def ms_to_frame(ms: int, fps: int) -> int:
    return (ms * fps + 500) // 1000  # integer round-half-up; no float drift


def frame_edges(shots: list[Shot], fps: int) -> list[int]:
    edges = [ms_to_frame(s.startMs, fps) for s in shots]
    edges.append(ms_to_frame(shots[-1].endMs, fps))
    return edges


def plan_shots(manifest: Manifest, fps: int) -> list[ShotPlan]:
    shots = manifest.shots
    edges = frame_edges(shots, fps)
    plans: list[ShotPlan] = []
    for i, s in enumerate(shots):
        body = edges[i + 1] - edges[i]
        if body < 1:
            raise RenderError(f"shot '{s.id}' is shorter than one frame at {fps} fps")
        tail = 0
        if i + 1 < len(shots) and shots[i + 1].transition.type != "cut":
            tail = max(1, ms_to_frame(shots[i + 1].transition.durationMs, fps))
        mode = s.mode
        reason = None
        if s.mode == "RENDERED":
            pass  # creator-supplied clip; rendered as-is, no fallback, no provider
        elif s.mode == "GENERATIVE":
            gen = s.generation
            assert gen is not None and s.fallbackMode is not None  # guaranteed by contract
            if gen.clipAssetId and s.approval == "approved":
                mode = "GENERATIVE"
            else:
                mode = s.fallbackMode
                if not gen.clipAssetId:
                    reason = "no generated clip attached"
                else:
                    reason = f"clip not approved (approval={s.approval})"
        plans.append(ShotPlan(s, i, edges[i], body, tail, mode, reason))
    return plans


# ---------------------------------------------------------------- expressions


def _ease(kind: Easing, p: str) -> str:
    if kind == "linear":
        return p
    if kind == "easeIn":
        return f"({p})*({p})"
    if kind == "easeOut":
        return f"({p})*(2-({p}))"
    return f"({p})*({p})*(3-2*({p}))"


def _lerp(a: float, b: float, e: str) -> str:
    return f"({a:.6f}+({b - a:.6f})*({e}))"


def _bg_chain(w: int, h: int, fps: int, camera: Camera | None, body: int) -> str:
    cover = "force_original_aspect_ratio=increase:flags=lanczos"
    if camera is None:
        return f"scale={w}:{h}:{cover},crop={w}:{h},setsar=1"
    denom = max(body - 1, 1)
    e = _ease(camera.easing, f"min(on/{denom},1)")
    z = _lerp(camera.start.scale, camera.end.scale, e)
    cx = _lerp(camera.start.x, camera.end.x, e)
    cy = _lerp(camera.start.y, camera.end.y, e)
    x = f"clip({cx}*iw-iw/({z})/2,0,iw-iw/({z}))"
    y = f"clip({cy}*ih-ih/({z})/2,0,ih-ih/({z}))"
    return (
        f"scale={2 * w}:{2 * h}:{cover},crop={2 * w}:{2 * h},setsar=1,"
        f"zoompan=z='{z}':x='{x}':y='{y}':d=1:s={w}x{h}:fps={fps}"
    )


def _layer_chain(idx: int, lay: Layer, w: int, body_s: float, aspect: float = 1.0) -> tuple[str, str, str]:
    """Return (filter chain for the layer input, overlay x expr, overlay y expr).

    ``x``/``y`` place the layer's pivot in the frame; rotation turns the layer about that pivot. With the default
    centre pivot this is the original behaviour, expression for expression (renders stay bit-identical)."""
    e = _ease(lay.easing, f"min(t/{body_s:.6f},1)")
    wf = _lerp(lay.start.widthFrac, lay.end.widthFrac, e)
    rot0, rot1 = lay.start.rotateDeg, lay.end.rotateDeg
    rot = _lerp(rot0, rot1, e)
    if lay.swayDeg:
        rot += f"+{lay.swayDeg:.6f}*sin(2*PI*t*1000/{lay.swayPeriodMs})"
    chain = (
        f"[{idx}:v]format=rgba,scale=w='max(2,{w}*{wf})':h=-1:eval=frame,"
        # c=black@0 (explicit transparent), NOT c=none: 'none' leaves unwritten pixels and made
        # renders non-reproducible run to run (see ADR-0003, test_layered_camera_*).
        f"rotate=a='({rot})*PI/180':ow='hypot(iw,ih)':oh='ow':c=black@0"
    )
    px = _lerp(lay.start.x, lay.end.x, e)
    py = _lerp(lay.start.y, lay.end.y, e)
    if abs(lay.pivotX - 0.5) < 1e-9 and abs(lay.pivotY - 0.5) < 1e-9:
        return chain, f"main_w*{px}-overlay_w/2", f"main_h*{py}-overlay_h/2"
    # Off-centre pivot: the layer's centre sits at (pivot - centre offset) turned by the current angle.
    # Rotation here is clockwise on a y-down frame, like the ``rotate`` filter above.
    a = f"(({rot})*PI/180)"
    wl = f"(main_w*{wf})"  # current layer width in output pixels
    dx = f"(({0.5 - lay.pivotX:.6f})*{wl})"
    dy = f"(({0.5 - lay.pivotY:.6f})*{wl}*{aspect:.6f})"
    cx = f"(main_w*{px}+{dx}*cos{a}-{dy}*sin{a})"
    cy = f"(main_h*{py}+{dx}*sin{a}+{dy}*cos{a})"
    return chain, f"{cx}-overlay_w/2", f"{cy}-overlay_h/2"


def _flash_expr(shot: Shot, fps: int) -> str | None:
    terms = []
    for eff in shot.effects:
        for at in eff.atMs:
            terms.append(f"{eff.intensity:.4f}*max(0,1-abs(t-{at / 1000:.4f})/0.15)")
    return "+".join(terms) if terms else None


# ---------------------------------------------------------------- segment encode


def _clip_ref(shot: Shot) -> tuple[str, int, float]:
    """(asset id, trim start ms, speed) of the clip a GENERATIVE/RENDERED shot plays."""
    if shot.mode == "RENDERED":
        assert shot.rendered is not None
        return shot.rendered.assetId, shot.rendered.trimStartMs, shot.rendered.speed
    assert shot.generation is not None and shot.generation.clipAssetId is not None
    return shot.generation.clipAssetId, 0, 1.0


def _in_args(path: Path, *, still_fps: int | None, trim_start_ms: int = 0) -> list[str]:
    args = ["-protocol_whitelist", "file"]
    if trim_start_ms:
        args += ["-ss", f"{trim_start_ms / 1000:.3f}"]
    if still_fps is not None:
        args += ["-loop", "1", "-framerate", str(still_fps)]
    return [*args, "-i", str(path)]


# Normalise full-range (JPEG) sources to limited-range BT.709 so output is plain yuv420p.
_TV = "scale=out_range=tv:out_color_matrix=bt709:flags=bicubic"

_ENC_SEG = [
    "-c:v",
    "libx264",
    "-preset",
    "fast",
    "-crf",
    "14",
    "-pix_fmt",
    "yuv420p",
    "-colorspace",
    "bt709",
    "-color_primaries",
    "bt709",
    "-color_trc",
    "bt709",
    "-color_range",
    "tv",
    "-fflags",
    "+bitexact",
    "-flags:v",
    "+bitexact",
    "-map_metadata",
    "-1",
    "-an",
]


def build_segment_argv(
    tc: Toolchain,
    plan: ShotPlan,
    manifest: Manifest,
    infos: dict[str, AssetInfo],
    w: int,
    h: int,
    fps: int,
    out: Path,
) -> list[str | Path]:
    shot, n = plan.shot, plan.total_frames
    body_s = plan.body_frames / fps
    argv: list[str | Path] = [
        tc.ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-y",
    ]

    if plan.effective_mode in ("GENERATIVE", "RENDERED"):
        clip_id, trim_ms, speed = _clip_ref(shot)
        clip = infos[clip_id]
        argv += _in_args(clip.path, still_fps=None, trim_start_ms=trim_ms)
        # slow-down: stretch timestamps, then blend-interpolate back to the project fps (no stutter)
        retime = (
            f"setpts=(PTS-STARTPTS)/{speed:.6f},minterpolate=fps={fps}:mi_mode=blend,"
            if abs(speed - 1.0) > 1e-6
            else ""
        )
        graph = (
            f"[0:v]{retime}fps={fps},scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={w}:{h},setsar=1,tpad=stop_mode=clone:stop_duration={n / fps + 1:.3f},"
            f"trim=end_frame={n},setpts=PTS-STARTPTS,{_TV},format=yuv420p[v]"
        )
    else:
        bg = infos[shot.sourceAssetIds[0]]
        argv += _in_args(bg.path, still_fps=fps)
        use_camera = plan.effective_mode in ("CINEMATIC", "LAYERED") and shot.camera is not None
        parts = [f"[0:v]{_bg_chain(w, h, fps, shot.camera if use_camera else None, plan.body_frames)}[c0]"]
        cur = "c0"
        if plan.effective_mode == "LAYERED":
            # Pin the background to RGBA before overlaying. Without this, zoompan+overlay shots
            # were non-reproducible run to run (pixel-format negotiation); with it, 0 of 230
            # frames differed across runs (tests: test_layered_camera_segment_is_deterministic).
            parts[0] = parts[0].replace("[c0]", ",format=rgba[c0]")
            for i, lay in enumerate(shot.layers, start=1):
                argv += _in_args(infos[lay.assetId].path, still_fps=fps)
                li = infos[lay.assetId]
                aspect = (li.height / li.width) if li.width and li.height else 1.0
                chain, ox, oy = _layer_chain(i, lay, w, body_s, aspect)
                parts.append(f"{chain}[l{i}]")
                parts.append(f"[{cur}][l{i}]overlay=x='{ox}':y='{oy}':eval=frame:format=auto[c{i}]")
                cur = f"c{i}"
        tail = f"{_TV},format=yuv420p"
        flash = _flash_expr(shot, fps)
        if flash:
            tail += f",eq=brightness='{flash}':eval=frame"
        parts.append(f"[{cur}]{tail}[v]")
        graph = ";".join(parts)

    argv += ["-filter_complex", graph, "-map", "[v]", "-frames:v", str(n), "-r", str(fps), *_ENC_SEG, out]
    return argv


# ---------------------------------------------------------------- final composition


def build_final_argv(
    tc: Toolchain,
    manifest: Manifest,
    plans: list[ShotPlan],
    seg_paths: list[Path],
    narration: Path,
    w: int,
    h: int,
    fps: int,
    out: Path,
    draft: bool,
    badge: Path | None,
    tracks: list[tuple[AudioTrack, Path]] | None = None,
) -> tuple[list[str | Path], int]:
    tracks = tracks or []
    argv: list[str | Path] = [tc.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
    for p in seg_paths:
        argv += _in_args(p, still_fps=None)
    argv += _in_args(narration, still_fps=None)
    nar_idx = len(seg_paths)
    for trk, path in tracks:
        if trk.loop:
            argv += ["-stream_loop", "-1"]
        argv += _in_args(path, still_fps=None)

    parts = [f"[{i}:v]fps={fps},settb=1/{fps},setpts=PTS[s{i}]" for i in range(len(seg_paths))]
    cur = "s0"
    for k in range(1, len(plans)):
        tr = plans[k].shot.transition
        out_lbl = f"m{k}"
        if tr.type == "cut":
            parts.append(f"[{cur}][s{k}]concat=n=2:v=1:a=0[{out_lbl}x];[{out_lbl}x]settb=1/{fps}[{out_lbl}]")
        else:
            kind = "fade" if tr.type == "crossfade" else "fadeblack"
            dur = max(1, ms_to_frame(tr.durationMs, fps)) / fps
            off = plans[k].start_frame / fps
            parts.append(
                f"[{cur}][s{k}]xfade=transition={kind}:duration={dur:.6f}:offset={off:.6f}[{out_lbl}x];"
                f"[{out_lbl}x]settb=1/{fps}[{out_lbl}]"
            )
        cur = out_lbl
    total_frames = plans[-1].start_frame + plans[-1].body_frames
    total_s = total_frames / fps
    post = ["format=yuv420p"]
    fi, fo = manifest.video.fadeInMs / 1000, manifest.video.fadeOutMs / 1000
    if fi:
        post.append(f"fade=t=in:st=0:d={fi:.3f}")
    if fo:
        post.append(f"fade=t=out:st={total_s - fo:.6f}:d={fo:.3f}")
    parts.append(f"[{cur}]{','.join(post)}[vbase]")
    vlabel = "vbase"
    if draft and badge is not None:
        argv += _in_args(badge, still_fps=fps)
        parts.append(f"[vbase][{nar_idx + 1 + len(tracks)}:v]overlay=x=8:y=8:shortest=1[vout]")
        vlabel = "vout"
    crf, preset, abr = ("30", "veryfast", "96k") if draft else ("18", "medium", "192k")
    if tracks:
        parts += _audio_mix_graph(manifest, tracks, nar_idx, total_s)
        audio_args: list[str] = ["-map", "[aout]"]
    else:
        audio_args = ["-map", f"{nar_idx}:a", "-af", "aresample=48000,aformat=channel_layouts=stereo"]
    argv += [
        "-filter_complex",
        ";".join(parts),
        "-map",
        f"[{vlabel}]",
        *audio_args,
        "-frames:v",
        str(total_frames),
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        crf,
        "-pix_fmt",
        "yuv420p",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-color_range",
        "tv",
        "-c:a",
        "aac",
        "-b:a",
        abr,
        "-ar",
        "48000",
        "-ac",
        "2",
        "-fflags",
        "+bitexact",
        "-flags:v",
        "+bitexact",
        "-flags:a",
        "+bitexact",
        "-map_metadata",
        "-1",
        "-movflags",
        "+faststart",
        out,
    ]
    return argv, total_frames


def _audio_mix_graph(
    manifest: Manifest, tracks: list[tuple[AudioTrack, Path]], nar_idx: int, total_s: float
) -> list[str]:
    """Narration + bed track(s). Beds are levelled, faded, trimmed to the video and ducked while the
    narrator speaks (sidechain compression driven by the narration). A limiter prevents clipping."""
    n_ducked = sum(1 for t, _ in tracks if t.duckDb > 0)
    # first split output = the voice for the final mix; the others drive the ducking of each bed
    split_labels = "[nmix]" + "".join(f"[nsc{j}]" for j in range(n_ducked))
    parts = [f"[{nar_idx}:a]aresample=48000,aformat=channel_layouts=stereo,asplit={1 + n_ducked}{split_labels}"]
    bed_labels = []
    duck_i = 0
    for j, (t, _p) in enumerate(tracks):
        idx = nar_idx + 1 + j
        start_s = t.startMs / 1000
        length = max(0.1, total_s - start_s)
        chain = (
            f"[{idx}:a]aresample=48000,aformat=channel_layouts=stereo,atrim=end={length:.3f},asetpts=PTS-STARTPTS,"
            f"volume={t.gainDb:.2f}dB"
        )
        if t.fadeInMs:
            chain += f",afade=t=in:st=0:d={t.fadeInMs / 1000:.3f}"
        if t.fadeOutMs:
            chain += f",afade=t=out:st={max(0.0, length - t.fadeOutMs / 1000):.3f}:d={t.fadeOutMs / 1000:.3f}"
        if t.startMs:
            chain += f",adelay={t.startMs}|{t.startMs}"
        label = f"bed{j}"
        parts.append(f"{chain}[{label}]")
        if t.duckDb > 0:
            ratio = round(1 / (1 - min(t.duckDb, 20.0) / 25.0), 2)
            parts.append(
                f"[{label}][nsc{duck_i}]sidechaincompress=threshold=0.02:ratio={ratio}:attack=30:release=600:makeup=1"
                f"[{label}d]"
            )
            label += "d"
            duck_i += 1
        bed_labels.append(f"[{label}]")
    bus = "".join(bed_labels)
    if len(bed_labels) > 1:
        parts.append(f"{bus}amix=inputs={len(bed_labels)}:normalize=0[bus]")
        bus = "[bus]"
    parts.append(f"[nmix]{bus}amix=inputs=2:normalize=0:duration=first,alimiter=limit=0.89:level=0[aout]")
    return parts


def _make_badge(path: Path) -> None:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGBA", (330, 28), (0, 0, 0, 170))
    d = ImageDraw.Draw(img)
    d.text(
        (8, 6),
        "DRAFT PREVIEW - proxy fidelity, not final",
        fill=(255, 220, 80, 255),
        font=ImageFont.load_default(size=13),
    )
    img.save(path)


# ---------------------------------------------------------------- orchestration


def _sanitise(argv: list[str | Path], subs: dict[str, str]) -> list[str]:
    out = []
    for a in argv:
        s = str(a)
        for k, v in subs.items():
            s = s.replace(k, v)
        out.append(s)
    return out


def _run_step(
    tc: Toolchain, argv: list[str | Path], what: str, timeout: float, report: RenderReport, subs: dict[str, str]
) -> float:
    report.commands.append(_sanitise(argv, subs))
    t0 = time.perf_counter()
    proc = run(argv, timeout=timeout)
    dt = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RenderError(
            f"FFmpeg failed while {what} (exit {proc.returncode}). "
            f"Nothing was published. Details: {proc.stderr.strip()[-600:]}"
        )
    return dt


def render(
    manifest: Manifest,
    root: Path,
    out_path: Path,
    options: RenderOptions | None = None,
    tc: Toolchain | None = None,
) -> RenderReport:
    """Render ``manifest`` (assets under ``root``) to ``out_path`` and verify the result."""
    opts = options or RenderOptions()
    tc = tc or get_toolchain()
    root = root.resolve()
    out_path = out_path.resolve()
    if out_path.exists() and not opts.overwrite:
        raise RenderError(f"{out_path.name} already exists; pass overwrite to replace it")
    out_path.parent.mkdir(parents=True, exist_ok=True)

    fps = manifest.video.fps
    w, h = DRAFT_SIZE if opts.draft else (manifest.video.width, manifest.video.height)
    report = RenderReport(
        manifest_project=manifest.projectId,
        processor_version=PROCESSOR_VERSION,
        toolchain=tc.version,
        draft=opts.draft,
        width=w,
        height=h,
        fps=fps,
    )
    t_all = time.perf_counter()

    infos = verify_manifest_assets(tc, manifest, root)
    report.assets = [i.as_dict() for i in infos.values()]
    bg_ids = {sh.sourceAssetIds[0] for sh in manifest.shots if sh.sourceAssetIds}
    for info in infos.values():
        if (
            info.asset_id in bg_ids
            and info.kind == "image"
            and info.width
            and info.height
            and (info.width < manifest.video.width or info.height < manifest.video.height)
        ):
            report.warnings.append(
                f"asset '{info.asset_id}' is {info.width}x{info.height}, smaller than the "
                f"{manifest.video.width}x{manifest.video.height} output; it will be upscaled"
            )
    plans = plan_shots(manifest, fps)
    for p in plans:
        if p.fallback_reason:
            msg = {"shot": p.shot.id, "usedMode": p.effective_mode, "reason": p.fallback_reason}
            report.fallbacks.append(msg)
            report.warnings.append(
                f"shot '{p.shot.id}' is GENERATIVE but renders as {p.effective_mode}: "
                f"{p.fallback_reason}. No provider request was made."
            )
        if p.effective_mode in ("GENERATIVE", "RENDERED"):
            clip_id, trim_ms, speed = _clip_ref(p.shot)
            clip = infos[clip_id]
            if clip.duration_ms is not None:
                avail = round((clip.duration_ms - trim_ms) / speed)
                need = p.body_frames * 1000 // fps
                if avail < need - 40:
                    report.warnings.append(
                        f"clip for shot '{p.shot.id}' has {avail} ms usable but the shot needs "
                        f"{need} ms; its last frame is held"
                    )
                elif avail > need + 250:
                    report.warnings.append(
                        f"clip for shot '{p.shot.id}' has {avail - need} ms more than the shot uses; the end is cut"
                    )
    report.max_cut_quantisation_error_ms = max(abs(p.start_frame * 1000 / fps - p.shot.startMs) for p in plans)

    work = out_path.parent / f".work-{out_path.stem}"
    if work.exists():
        if not (work / WORK_MARKER).exists():
            raise RenderError(f"{work} exists but is not a StoryMotion work folder; not touching it")
        shutil.rmtree(work)
    work.mkdir()
    (work / WORK_MARKER).write_text("temporary render files; safe to delete\n", encoding="utf-8")
    subs = {str(root): "<ROOT>", str(work): "<WORK>", str(tc.ffmpeg.parent): "<FFMPEG>"}
    partial = work / "final.partial.mp4"

    try:
        seg_paths: list[Path] = []
        n_steps = len(plans) + 2

        def tick(done: int, msg: str) -> None:
            if opts.cancel is not None and opts.cancel.is_set():
                raise RenderCancelled("The render was cancelled. Nothing was published.")
            if opts.progress is not None:
                opts.progress(min(0.98, done / n_steps), msg)

        for p in plans:
            tick(p.index, f"Encoding shot {p.index + 1} of {len(plans)}")
            seg = work / f"seg-{p.index:02d}-{p.shot.id}.mp4"
            argv = build_segment_argv(tc, p, manifest, infos, w, h, fps, seg)
            dt = _run_step(tc, argv, f"encoding shot '{p.shot.id}'", opts.step_timeout_s, report, subs)
            seg_paths.append(seg)
            report.shots.append(
                {
                    "id": p.shot.id,
                    "declaredMode": p.shot.mode,
                    "renderedMode": p.effective_mode,
                    "startMs": p.shot.startMs,
                    "durationMs": p.shot.durationMs,
                    "startFrame": p.start_frame,
                    "bodyFrames": p.body_frames,
                    "tailFrames": p.tail_frames,
                    "encodeSeconds": round(dt, 3),
                    "transitionIn": p.shot.transition.type,
                }
            )
        badge = None
        if opts.draft:
            badge = work / "draft-badge.png"
            _make_badge(badge)
        nar_path = infos[manifest.narration.assetId].path
        final_argv, total_frames = build_final_argv(
            tc,
            manifest,
            plans,
            seg_paths,
            nar_path,
            w,
            h,
            fps,
            partial,
            opts.draft,
            badge,
            [(t, infos[t.assetId].path) for t in manifest.audioTracks],
        )
        tick(len(plans), "Joining the shots and mixing the audio")
        dt = _run_step(tc, final_argv, "composing the final video", opts.step_timeout_s, report, subs)
        report.timings_s["compose"] = round(dt, 3)
        report.timings_s["segments"] = round(sum(s["encodeSeconds"] for s in report.shots), 3)

        tick(len(plans) + 1, "Checking the finished video")
        t0 = time.perf_counter()
        report.verification = verify_output(
            tc,
            partial,
            expected_w=w,
            expected_h=h,
            expected_fps=fps,
            expected_frames=total_frames,
            narration_ms=manifest.narration.durationMs,
            allowed_black=_allowed_black_windows(manifest, plans, total_frames / fps),
        )
        report.timings_s["verify"] = round(time.perf_counter() - t0, 3)
        os.replace(partial, out_path)  # publish only after validation passed
    finally:
        if not opts.keep_work:
            shutil.rmtree(work, ignore_errors=True)

    report.timings_s["total"] = round(time.perf_counter() - t_all, 3)
    report.output = {
        "file": out_path.name,
        "sha256": sha256_file(out_path),
        "sizeBytes": out_path.stat().st_size,
        "frames": total_frames,
        "draft": opts.draft,
    }
    return report


def _allowed_black_windows(manifest: Manifest, plans: list[ShotPlan], total_s: float) -> list[tuple[float, float]]:
    """Black is only acceptable inside declared fades (QG OPS-03: no *unplanned* black)."""
    fps = manifest.video.fps
    wins: list[tuple[float, float]] = []
    if manifest.video.fadeInMs:
        wins.append((0.0, manifest.video.fadeInMs / 1000 + 0.2))
    if manifest.video.fadeOutMs:
        wins.append((total_s - manifest.video.fadeOutMs / 1000 - 0.2, total_s + 0.1))
    for p in plans[1:]:
        tr = p.shot.transition
        if tr.type == "fadeblack":
            start = p.start_frame / fps
            wins.append((start, start + max(1, ms_to_frame(tr.durationMs, fps)) / fps))
    return wins


def resolve_asset_path(root: Path, rel: str) -> Path:
    """Public helper for tools that need a contained path."""
    return resolve_in_root(root, rel)
