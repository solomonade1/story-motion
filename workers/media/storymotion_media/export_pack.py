"""Export package: take the storyboard to another editor, or hand it to a video/vision model (and take its answer back).

Folder layout (``full`` mode; ``brief`` writes only ``ai/``):

  README.md                      what is here and how to open it
  shots/001_<shot>.mp4           one video-only clip per shot at the project size; each carries a few extra frames at the end
                                 (the "handle") that a following dissolve/dip needs
  audio/narration.wav            48 kHz stereo
  audio/bed<N>_<role>.wav        each music/ambience bed as used (level, start, fades, loop applied; NOT ducked)
  audio/final_mix.wav            the complete mix exactly as in the final render (ducked, limited)
  timeline/timeline.otio         OpenTimelineIO (JSON): video track with transitions, narration and bed audio tracks
  timeline/timeline.edl          CMX3600 edit list (video only; dips are written as dissolves)
  ai/handoff.json                machine-readable description of every scene, shot, asset, time, setting and diagnostic
  ai/README_FOR_MODELS.md        instructions for an LLM / video model, including how to return improvements
  ai/storyboard.schema.json      JSON Schema of the storyboard a model may return (import it with "Import scene plan")
  ai/script.txt                  the script passage of each scene
  ai/keyframes/NNN_<shot>_{start,mid,end}.jpg and ai/contact_sheet_N.jpg   still frames for vision models

Rules: nothing is uploaded anywhere (this only writes a local folder); source files are never modified; asset ids in the
package are the project's own, so a storyboard returned by a model imports straight back; every time is an integer
millisecond on the narration clock, with the matching frame number at the project fps.
Timeline files are generated to the formats' published structure; they have NOT been opened in Premiere, Resolve or any
other editor by the developer. Treat the first import as a test.
"""

from __future__ import annotations

import json
import shutil
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from . import PROCESSOR_VERSION
from .contracts import Manifest
from .errors import RenderCancelled, RenderError
from .ingest import AssetInfo, sha256_file, verify_manifest_assets
from .render import (
    DRAFT_SIZE,
    ShotPlan,
    _in_args,
    build_segment_argv,
    ms_to_frame,
    plan_shots,
)
from .studio.atomic import rename_with_retry
from .toolchain import Toolchain, run

HANDOFF_VERSION = "storymotion.handoff/1"
START_TC_HOURS = 1  # EDL/OTIO record timecode starts at 01:00:00:00, the editors' convention
Mode = Literal["full", "brief", "assets"]


@dataclass(frozen=True)
class ExportOptions:
    mode: Mode = "full"
    progress: Callable[[float, str], None] | None = None
    cancel: threading.Event | None = None
    step_timeout_s: float = 900.0


def _ff(tc: Toolchain, args: list[str | Path], what: str, timeout: float) -> None:
    proc = run([tc.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y", *args], timeout=timeout)
    if proc.returncode != 0:
        raise RenderError(f"FFmpeg failed while {what} (exit {proc.returncode}). Nothing was published. {proc.stderr.strip()[-400:]}")


# ------------------------------------------------------------------------------------------------ timecode
def tc(frames: int, fps: int) -> str:
    """Non-drop timecode HH:MM:SS:FF (24 and 30 fps are whole-number rates, so no drop frame)."""
    f = max(0, frames)
    h, rem = divmod(f, 3600 * fps)
    m, rem = divmod(rem, 60 * fps)
    s, ff = divmod(rem, fps)
    return f"{h:02d}:{m:02d}:{s:02d}:{ff:02d}"


def _clip_name(plan: ShotPlan) -> str:
    return f"{plan.index + 1:03d}_{plan.shot.id}.mp4"


def _transition_frames(plans: list[ShotPlan], k: int, fps: int) -> int:
    """Length in frames of the transition INTO shot k (0 for a cut)."""
    tr = plans[k].shot.transition
    return 0 if tr.type == "cut" else max(1, ms_to_frame(tr.durationMs, fps))


# ------------------------------------------------------------------------------------------------ timeline files
def build_edl(title: str, plans: list[ShotPlan], fps: int) -> str:
    """CMX3600. One event per shot; a transition becomes the usual pair of lines (zero-length outgoing hold + dissolve into the shot).
    Reel is always AX (auxiliary); the clip file name is in the ``FROM CLIP NAME`` comment."""
    base = START_TC_HOURS * 3600 * fps
    lines = [f"TITLE: {title[:60]}", "FCM: NON-DROP FRAME", ""]
    n = 0
    for k, p in enumerate(plans):
        rec_in = base + p.start_frame
        rec_out = rec_in + p.body_frames
        dur = _transition_frames(plans, k, fps) if k > 0 else 0
        name = _clip_name(p)
        n += 1
        if dur:
            prev = plans[k - 1]
            lines.append(f"{n:03d}  AX       V     C        {tc(prev.body_frames, fps)} {tc(prev.body_frames, fps)} {tc(rec_in, fps)} {tc(rec_in, fps)}")
            lines.append(f"* FROM CLIP NAME: {_clip_name(prev)}")
            kind = "dip to black (written as a dissolve)" if p.shot.transition.type == "fadeblack" else "crossfade"
            lines.append(f"{n:03d}  AX       V     D    {dur:03d} {tc(0, fps)} {tc(p.body_frames, fps)} {tc(rec_in, fps)} {tc(rec_out, fps)}")
            lines.append(f"* FROM CLIP NAME: {name}")
            lines.append(f"* TRANSITION: {kind}, {p.shot.transition.durationMs} ms, starts at the cut")
        else:
            lines.append(f"{n:03d}  AX       V     C        {tc(0, fps)} {tc(p.body_frames, fps)} {tc(rec_in, fps)} {tc(rec_out, fps)}")
            lines.append(f"* FROM CLIP NAME: {name}")
        if p.shot.action:
            lines.append(f"* COMMENT: {p.shot.action[:100]}")
        lines.append("")
    return "\n".join(lines) + "\n"


def _rt(frames: int, fps: int) -> dict[str, Any]:
    return {"OTIO_SCHEMA": "RationalTime.1", "rate": float(fps), "value": float(frames)}


def _tr(start: int, dur: int, fps: int) -> dict[str, Any]:
    return {"OTIO_SCHEMA": "TimeRange.1", "duration": _rt(dur, fps), "start_time": _rt(start, fps)}


def _ref(url: str, dur_frames: int, fps: int) -> dict[str, Any]:
    return {
        "OTIO_SCHEMA": "ExternalReference.1", "metadata": {}, "name": Path(url).name, "available_range": _tr(0, dur_frames, fps),
        "available_image_bounds": None, "target_url": url,
    }


def build_otio(title: str, plans: list[ShotPlan], fps: int, narration_frames: int, beds: list[dict[str, Any]], nar_file: str) -> dict[str, Any]:
    """OpenTimelineIO JSON. Clips are the shot files (source_range = the shot's own frames; the file also holds a handle after
    them for the following transition). A transition belongs between two clips with in_offset 0 and out_offset = its length."""
    video: list[dict[str, Any]] = []
    for k, p in enumerate(plans):
        dur = _transition_frames(plans, k, fps) if k > 0 else 0
        if dur:
            video.append(
                {
                    "OTIO_SCHEMA": "Transition.1", "metadata": {"storymotion": {"type": p.shot.transition.type, "durationMs": p.shot.transition.durationMs}},
                    "name": "Crossfade" if p.shot.transition.type == "crossfade" else "Dip to black",
                    "transition_type": "SMPTE_Dissolve", "in_offset": _rt(0, fps), "out_offset": _rt(dur, fps),
                }
            )
        video.append(
            {
                "OTIO_SCHEMA": "Clip.2", "name": f"{p.shot.id}", "source_range": _tr(0, p.body_frames, fps),
                "media_reference": _ref(f"shots/{_clip_name(p)}", p.body_frames + p.tail_frames, fps), "active_media_reference_key": "DEFAULT_MEDIA",
                "metadata": {"storymotion": {"shotId": p.shot.id, "sceneId": p.shot.sceneId, "mode": p.shot.mode, "startMs": p.shot.startMs, "durationMs": p.shot.durationMs, "action": p.shot.action}},
            }
        )
    audio_tracks: list[dict[str, Any]] = [
        {
            "OTIO_SCHEMA": "Track.1", "name": "Narration", "kind": "Audio", "metadata": {}, "source_range": None,
            "children": [{
                "OTIO_SCHEMA": "Clip.2", "name": "Narration", "source_range": _tr(0, narration_frames, fps),
                "media_reference": _ref(nar_file, narration_frames, fps), "active_media_reference_key": "DEFAULT_MEDIA", "metadata": {},
            }],
        }
    ]
    for b in beds:
        audio_tracks.append(
            {
                "OTIO_SCHEMA": "Track.1", "name": b["name"], "kind": "Audio", "metadata": {}, "source_range": None,
                "children": [{
                    "OTIO_SCHEMA": "Clip.2", "name": b["name"], "source_range": _tr(0, narration_frames, fps),
                    "media_reference": _ref(b["file"], narration_frames, fps), "active_media_reference_key": "DEFAULT_MEDIA",
                    "metadata": {"storymotion": {k: v for k, v in b.items() if k not in ("file", "name")}},
                }],
            }
        )
    total = plans[-1].start_frame + plans[-1].body_frames
    return {
        "OTIO_SCHEMA": "Timeline.1", "name": title, "metadata": {"storymotion": {"processorVersion": PROCESSOR_VERSION, "fps": fps}},
        "global_start_time": _rt(START_TC_HOURS * 3600 * fps, fps),
        "tracks": {
            "OTIO_SCHEMA": "Stack.1", "name": "tracks", "metadata": {}, "source_range": _tr(0, total, fps),
            "children": [
                {"OTIO_SCHEMA": "Track.1", "name": "Video", "kind": "Video", "metadata": {}, "source_range": None, "children": video},
                *audio_tracks,
            ],
        },
    }


# ------------------------------------------------------------------------------------------------ AI hand-off
def constraints() -> dict[str, Any]:
    """What a model may change, taken from the same limits the app enforces (so its suggestions import cleanly)."""
    from .studio.presets import PRESET_CAMERAS

    return {
        "timing": "Integer milliseconds on the narration clock. Shots play in scene order then shot order, start at 0, are contiguous (each startMs equals the previous end), and the last ends within 250 ms of the narration length.",
        "modes": {"STATIC": "picture held still", "CINEMATIC": "picture with a camera move from a preset", "LAYERED": "background picture plus moving transparent layers",
                  "RENDERED": "a creator-supplied video clip (trim and slow-down allowed)", "GENERATIVE": "NOT available: renders with a local fallback; do not propose it"},
        "presets": sorted(PRESET_CAMERAS) + ["hold"],
        "transitions": {"types": ["cut", "crossfade", "fadeblack"], "durationMs": "100-5000 for crossfade/fadeblack; 0 for cut; not allowed on the first shot; must not exceed either neighbouring shot's length; starts when the shot starts"},
        "clip": {"speed": "0.5-1.5 (below 1 slows the clip)", "fitSpeed": "slow the clip just enough to fill the shot (not below 0.6x)", "trimStartMs": ">= 0 and inside the clip"},
        "layers": {"count": "up to 8 per shot", "pose": "x,y of the layer's pivot in the frame (-0.5..1.5), widthFrac (0..2], rotateDeg (-360..360)", "easing": ["linear", "easeIn", "easeOut", "easeInOut"], "pivot": "pivotX/pivotY 0..1 inside the layer picture", "swayDeg": "0-45"},
        "audioTracks": {"count": "up to 8", "gainDb": "-60..12", "duckDb": "0-30 (lowers the bed under narration)", "startMs": ">= 0 and before the narration ends", "fadeInMs/fadeOutMs": ">= 0", "loop": "repeat if shorter than the video"},
        "videoFades": {"fadeInMs": "0-10000", "fadeOutMs": "0-10000"},
        "doNotInvent": "Only use asset ids listed in handoff.json. Do not add pictures, clips or audio that are not listed. Do not claim licences.",
    }


def build_handoff(manifest: Manifest, plans: list[ShotPlan], storyboard: dict[str, Any], diagnostics: list[dict[str, Any]], project_name: str, infos: dict[str, AssetInfo], mode: Mode, files: dict[str, str]) -> dict[str, Any]:
    fps = manifest.video.fps
    nar = infos[manifest.narration.assetId]
    scene_text = {sc["id"]: sc.get("text", "") for sc in storyboard.get("scenes", [])}
    scene_title = {sc["id"]: sc.get("title", "") for sc in storyboard.get("scenes", [])}
    shots = []
    for p in plans:
        s = p.shot
        shots.append(
            {
                "id": s.id, "sceneId": s.sceneId, "order": p.index + 1, "startMs": s.startMs, "durationMs": s.durationMs, "endMs": s.endMs,
                "startFrame": p.start_frame, "frames": p.body_frames, "mode": s.mode, "renderedAs": p.effective_mode,
                "intent": {"action": s.action, "mustShow": s.mustShow, "avoid": s.avoid},
                "sourceAssetIds": s.sourceAssetIds, "clipAssetId": s.rendered.assetId if s.rendered else None,
                "camera": s.camera.model_dump() if s.camera else None, "layers": [ly.model_dump() for ly in s.layers],
                "clip": {"trimStartMs": s.rendered.trimStartMs, "speed": s.rendered.speed} if s.rendered else None,
                "transitionIn": s.transition.model_dump(), "preset": next((sh.get("preset") for sc in storyboard.get("scenes", []) for sh in sc.get("shots", []) if sh["id"] == s.id), None),
                "files": {k: v for k, v in files.items() if k.startswith(f"{p.index + 1:03d}_")},
            }
        )
    assets = []
    for a in manifest.assets:
        i = infos[a.id]
        assets.append({"id": a.id, "type": a.type, "kind": a.media_kind, "originalName": a.provenance.source.replace("Studio import: ", ""), "sha256": a.sha256,
                       "width": i.width, "height": i.height, "durationMs": i.duration_ms, "provenance": a.provenance.model_dump()})
    return {
        "handoffVersion": HANDOFF_VERSION,
        "about": "A description of one StoryMotion Studio video: what is on screen when, with what intent, using which assets. Read ai/README_FOR_MODELS.md first.",
        "project": {"name": project_name, "exportMode": mode, "processorVersion": PROCESSOR_VERSION},
        "video": {"width": manifest.video.width, "height": manifest.video.height, "fps": fps, "fadeInMs": manifest.video.fadeInMs, "fadeOutMs": manifest.video.fadeOutMs},
        "narration": {"assetId": manifest.narration.assetId, "durationMs": manifest.narration.durationMs, "file": files.get("narration"), "sampleRate": nar.sample_rate},
        "scenes": [{"id": sc.id, "title": scene_title.get(sc.id) or sc.title, "script": scene_text.get(sc.id, ""), "startMs": sc.narration.startMs, "endMs": sc.narration.endMs, "characterIds": sc.characterIds, "shotIds": sc.shotIds} for sc in manifest.scenes],
        "characters": storyboard.get("characters", []),
        "shots": shots,
        "audioTracks": [t.model_dump() for t in manifest.audioTracks],
        "assets": assets,
        "diagnostics": diagnostics,
        "constraints": constraints(),
        "currentStoryboard": storyboard,
        "files": files,
        "limits": ["Cut timing and motion were measured on the render, not judged for artistic quality.", "Provenance entries marked licenseVerified=false have not been checked."],
    }


MODEL_README = """# For models: how to read and improve this video

You are given a **StoryMotion Studio** project exported as a package. Your job may be to review it, suggest improvements, or propose a better storyboard.
The human owner makes the final decisions; you cannot render, publish, pay or change files.

## What to read
1. `handoff.json`: every scene (with its script passage), shot (start/duration in ms and frames, mode, intent: `action`, `mustShow`, `avoid`),
   transitions, camera/layer settings, audio beds, assets (ids, sizes, durations, provenance), current diagnostics, and the **constraints** you must respect.
2. `keyframes/` and `contact_sheet_*.jpg`: stills of each shot's start, middle and end (if present). Use them to judge whether the picture shows the `action` and `mustShow`, avoids `avoid`, and flows into the next shot.
3. `script.txt`: the script passage of each scene. The narration audio is `audio/narration.wav` (full exports only); you may not hear audio, so rely on `narration.durationMs` and the shot times.
4. `storyboard.schema.json`: the exact shape of the storyboard you may return.

## What good looks like (check these, report what you find)
- Each shot's picture/clip matches what the narration says at that moment (`intent.action`, `mustShow`), and nothing in `avoid` appears.
- Shots change on or just before the narration changes topic, not mid-sentence; no shot is much longer than its content justifies.
- Transitions suit the moment (cut for quick moves, dissolve for time passing, dip to black for a large break); no stack of long dissolves.
- Camera moves are slow and varied; consecutive shots do not repeat the same move; nothing leaves the picture.
- Music/ambience sits under the voice and is lowered while the narrator speaks.
- The diagnostics list is empty or explained.

## How to answer
- Prefer a short written review first: for each issue give the shot id, the evidence (timecode, keyframe name, field), and the smallest fix.
- If asked for a revised storyboard, return **one JSON object** matching `storyboard.schema.json` (start from `currentStoryboard` in `handoff.json` and change only what you mean to change).
  The owner imports it with **Storyboard tab -> Import scene plan**; the app validates it and shows any timing problems before anything renders.
- Keep every `id` that still exists. Keep times in integer milliseconds, contiguous, ending within 250 ms of the narration length.
- Use only `assetId`s listed in `handoff.json` (`assets`). Never invent pictures, clips, music or licences. Do not use mode `GENERATIVE`.
- Say what you could not judge (for example audio you cannot hear) instead of guessing.

## Limits of this package
Timing and settings are exact. Artistic quality is not measured by the app. Licences marked `licenseVerified: false` are unchecked.
"""

PACKAGE_README = """# StoryMotion export

Produced by StoryMotion Studio. Nothing here was uploaded anywhere; this is a local folder.

## Open in a video editor
- **Shots** (`shots/`): one clip per shot at the project size (video only). Each clip also holds a few extra frames at its end (the "handle") for a following transition.
- **Audio** (`audio/`): `narration.wav`; each music/ambience bed as used (level, start, fades and looping applied, **not ducked**); `final_mix.wav` is the finished mix (ducked and limited).
- **Timeline**: `timeline/timeline.otio` (OpenTimelineIO: DaVinci Resolve 18.5 or newer, and pipeline tools) and `timeline/timeline.edl` (CMX3600; video only; dips to black are written as dissolves).
  Premiere Pro imports the EDL; it does not read OTIO. For both, relink the media if asked: the paths are relative to this folder.
  The files follow the formats' published structure but **have not been opened in any editor by the developer**: treat the first import as a test and tell us what broke.
- Record timecode starts at 01:00:00:00. Frame rate: {fps} fps. Resolution: {width}x{height}.

## Give it to a model
`ai/` holds a structured description (`handoff.json`), stills (`keyframes/`), the script, the storyboard schema, and instructions (`README_FOR_MODELS.md`).
A model's revised storyboard can be imported back with **Storyboard tab -> Import scene plan** because asset ids are the project's own.
Before sending anything to an outside service, check what is in the folder: `shots/` and `audio/` are your media; `ai/keyframes` are frames of your pictures; `handoff.json` holds your script text and file names.
"""


# ------------------------------------------------------------------------------------------------ orchestration
def _contact_sheets(frames: list[tuple[str, Path]], out_dir: Path, per_sheet: int = 20) -> list[str]:
    from PIL import Image, ImageDraw, ImageFont

    names: list[str] = []
    cols, cell_w, cell_h, label_h = 4, 320, 180, 22
    for n, start in enumerate(range(0, len(frames), per_sheet), start=1):
        chunk = frames[start : start + per_sheet]
        rows = (len(chunk) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell_w, rows * (cell_h + label_h)), (20, 22, 28))
        d = ImageDraw.Draw(sheet)
        for i, (label, path) in enumerate(chunk):
            with Image.open(path) as opened:
                thumb = opened.convert("RGB")
            thumb.thumbnail((cell_w, cell_h))
            x, y = (i % cols) * cell_w, (i // cols) * (cell_h + label_h)
            sheet.paste(thumb, (x, y + label_h))
            d.text((x + 4, y + 4), label[:44], fill=(255, 235, 150), font=ImageFont.load_default())
        name = f"contact_sheet_{n}.jpg"
        sheet.save(out_dir / name, quality=85)
        names.append(name)
    return names


def write_audio(
    tools: Toolchain, manifest: Manifest, infos: dict[str, AssetInfo], audio_dir: Path, total_s: float,
    files: dict[str, str], beds: list[dict[str, Any]], timeout: float, tick: Callable[[str], None],
) -> None:
    """narration.wav, each bed as used (not ducked) and final_mix.wav, all 48 kHz stereo PCM."""
    audio_dir.mkdir(exist_ok=True)
    tick("Writing the narration")
    nar_path = infos[manifest.narration.assetId].path
    _ff(tools, ["-i", nar_path, "-af", "aresample=48000,aformat=channel_layouts=stereo", "-c:a", "pcm_s16le", audio_dir / "narration.wav"], "writing the narration", timeout)
    files["narration"] = "audio/narration.wav"
    for j, t in enumerate(manifest.audioTracks, start=1):
        tick(f"Writing music/ambience track {j}")
        src = infos[t.assetId].path
        length = max(0.1, total_s - t.startMs / 1000)
        chain = f"aresample=48000,aformat=channel_layouts=stereo,atrim=end={length:.3f},asetpts=PTS-STARTPTS,volume={t.gainDb:.2f}dB"
        if t.fadeInMs:
            chain += f",afade=t=in:st=0:d={t.fadeInMs / 1000:.3f}"
        if t.fadeOutMs:
            chain += f",afade=t=out:st={max(0.0, length - t.fadeOutMs / 1000):.3f}:d={t.fadeOutMs / 1000:.3f}"
        if t.startMs:
            chain += f",adelay={t.startMs}|{t.startMs}"
        name = f"bed{j}_{t.role}.wav"
        args: list[str | Path] = []
        if t.loop:
            args += ["-stream_loop", "-1"]
        args += ["-i", src, "-af", f"{chain},apad", "-t", f"{total_s:.3f}", "-c:a", "pcm_s16le", audio_dir / name]
        _ff(tools, args, f"writing {name}", timeout)
        files[name] = f"audio/{name}"
        beds.append({"name": f"Bed {j} ({t.role})", "file": f"audio/{name}", "role": t.role, "gainDb": t.gainDb, "startMs": t.startMs, "fadeInMs": t.fadeInMs, "fadeOutMs": t.fadeOutMs, "loop": t.loop, "duckDb": t.duckDb, "note": "level, start, fades and loop are already applied; ducking is not"})
    tick("Writing the final mix")
    from .render import _audio_mix_graph

    argv2: list[str | Path] = [tools.ffmpeg, "-hide_banner", "-nostdin", "-loglevel", "error", "-y"]
    argv2 += _in_args(infos[manifest.narration.assetId].path, still_fps=None)
    for t in manifest.audioTracks:
        if t.loop:
            argv2 += ["-stream_loop", "-1"]
        argv2 += _in_args(infos[t.assetId].path, still_fps=None)
    if manifest.audioTracks:
        graph = ";".join(_audio_mix_graph(manifest, [(t, infos[t.assetId].path) for t in manifest.audioTracks], 0, total_s))
        argv2 += ["-filter_complex", graph, "-map", "[aout]"]
    else:
        argv2 += ["-af", "aresample=48000,aformat=channel_layouts=stereo"]
    argv2 += ["-t", f"{total_s:.3f}", "-c:a", "pcm_s16le", audio_dir / "final_mix.wav"]
    proc = run(argv2, timeout=timeout)
    if proc.returncode != 0:
        raise RenderError(f"FFmpeg failed while writing the final mix. Nothing was published. {proc.stderr.strip()[-400:]}")
    files["final_mix"] = "audio/final_mix.wav"


def build_export(
    manifest: Manifest,
    root: Path,
    dest: Path,
    *,
    storyboard: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    project_name: str,
    options: ExportOptions | None = None,
    tc_tools: Toolchain,
) -> dict[str, Any]:
    """Write the package to ``dest`` (which must not exist). Built in ``dest.parent/.work-<name>`` and moved into place at the end."""
    opts = options or ExportOptions()
    tools = tc_tools
    if opts.mode == "assets":
        from .export_assets import build_assets  # imported here: that module builds on this one

        return build_assets(manifest, root, dest, storyboard=storyboard, diagnostics=diagnostics, project_name=project_name, options=opts, tools=tools)
    full = opts.mode == "full"
    if dest.exists():
        raise RenderError(f"{dest.name} already exists; exports are never overwritten")
    work = dest.parent / f".work-{dest.name}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    fps = manifest.video.fps
    w, h = (manifest.video.width, manifest.video.height) if full else DRAFT_SIZE
    infos = verify_manifest_assets(tools, manifest, root.resolve())
    plans = plan_shots(manifest, fps)
    n_steps = len(plans) * 2 + (len(manifest.audioTracks) + 3 if full else 0) + 3
    done = 0

    def tick(msg: str) -> None:
        nonlocal done
        if opts.cancel is not None and opts.cancel.is_set():
            raise RenderCancelled("The export was cancelled. Nothing was published.")
        if opts.progress is not None:
            opts.progress(min(0.98, done / n_steps), msg)
        done += 1

    t0 = time.perf_counter()
    files: dict[str, str] = {}
    try:
        shots_dir = (work / "shots") if full else (work / ".seg")
        shots_dir.mkdir()
        kf_dir = work / "ai" / "keyframes"
        kf_dir.mkdir(parents=True)
        frames_for_sheet: list[tuple[str, Path]] = []
        for p in plans:
            tick(f"Encoding shot {p.index + 1} of {len(plans)}")
            seg = shots_dir / _clip_name(p)
            argv = build_segment_argv(tools, p, manifest, infos, w, h, fps, seg)
            proc = run(argv, timeout=opts.step_timeout_s)
            if proc.returncode != 0:
                raise RenderError(f"FFmpeg failed while encoding shot '{p.shot.id}'. Nothing was published. {proc.stderr.strip()[-400:]}")
            if full:
                files[_clip_name(p)] = f"shots/{seg.name}"
            tick(f"Picking keyframes for shot {p.index + 1} of {len(plans)}")
            stem = f"{p.index + 1:03d}_{p.shot.id}"
            for tag, frame in (("start", 0), ("mid", p.body_frames // 2), ("end", max(0, p.body_frames - 1))):
                out = kf_dir / f"{stem}_{tag}.jpg"
                _ff(tools, ["-i", seg, "-vf", f"select=eq(n\\,{frame}),scale=640:-2", "-frames:v", "1", "-q:v", "3", out], "picking a keyframe", opts.step_timeout_s)
                files[f"{stem}_{tag}"] = f"ai/keyframes/{out.name}"
                if tag == "mid":
                    frames_for_sheet.append((f"{p.index + 1:03d} {p.shot.id}  {p.shot.startMs / 1000:.1f}s", out))
        sheets = _contact_sheets(frames_for_sheet, work / "ai")
        for s in sheets:
            files[s] = f"ai/{s}"

        beds: list[dict[str, Any]] = []
        total_s = (plans[-1].start_frame + plans[-1].body_frames) / fps
        nar_frames = plans[-1].start_frame + plans[-1].body_frames
        if full:
            write_audio(tools, manifest, infos, work / "audio", total_s, files, beds, opts.step_timeout_s, tick)

            (work / "timeline").mkdir()
            (work / "timeline" / "timeline.edl").write_text(build_edl(project_name, plans, fps), encoding="utf-8", newline="\n")
            otio = build_otio(project_name, plans, fps, nar_frames, beds, "audio/narration.wav")
            (work / "timeline" / "timeline.otio").write_text(json.dumps(otio, indent=2) + "\n", encoding="utf-8", newline="\n")
            files["timeline.edl"], files["timeline.otio"] = "timeline/timeline.edl", "timeline/timeline.otio"
            (work / "README.md").write_text(PACKAGE_README.format(fps=fps, width=w, height=h), encoding="utf-8", newline="\n")
        tick("Writing the model brief")
        if not full:
            shutil.rmtree(shots_dir, ignore_errors=True)
        from .studio.storyboard import Storyboard

        ai = work / "ai"
        (ai / "storyboard.schema.json").write_text(json.dumps(Storyboard.model_json_schema(), indent=2) + "\n", encoding="utf-8", newline="\n")
        (ai / "README_FOR_MODELS.md").write_text(MODEL_README, encoding="utf-8", newline="\n")
        script = "\n\n".join(f"[{sc['id']}] {sc.get('title', '')}\n{sc.get('text', '')}".strip() for sc in storyboard.get("scenes", []))
        (ai / "script.txt").write_text(script + "\n", encoding="utf-8", newline="\n")
        handoff = build_handoff(manifest, plans, storyboard, diagnostics, project_name, infos, opts.mode, files)
        (ai / "handoff.json").write_text(json.dumps(handoff, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        rename_with_retry(work, dest, attempts=20, delay=0.1)  # publish only when everything was written; rides out brief virus-scanner locks
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    listing = []
    total = 0
    for f in sorted(dest.rglob("*")):
        if f.is_file():
            size = f.stat().st_size
            total += size
            listing.append({"path": f.relative_to(dest).as_posix(), "sizeBytes": size})
    return {"folder": dest.name, "mode": opts.mode, "shots": len(plans), "files": len(listing), "totalBytes": total, "seconds": round(time.perf_counter() - t0, 1),
            "handoffSha256": sha256_file(dest / "ai" / "handoff.json"), "listing": listing[:400]}
