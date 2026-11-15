"""Editor-independent asset folder: ordinary MP4/WAV/picture/JSON files that need no editor and no StoryMotion to use.

Unlike the editing package, nothing here depends on a timeline: each shot clip is exactly the shot's length (no transition baked in, no
extra frames), every asset has a small JSON file saying what it is and where it came from, the original source files are copied unchanged,
and SHA256SUMS.txt lets anyone check that nothing was altered or damaged.
"""

from __future__ import annotations

import dataclasses
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

from . import PROCESSOR_VERSION
from .contracts import Manifest
from .errors import RenderCancelled, RenderError
from .export_pack import ExportOptions, _ff, write_audio
from .ingest import sha256_file, verify_manifest_assets
from .render import build_segment_argv, plan_shots
from .studio.atomic import rename_with_retry
from .toolchain import Toolchain, ffprobe_json, run

ASSETS_VERSION = "storymotion.assets/1"
ASSETS_README = """# Independent assets

Plain files that need no editor and no StoryMotion to use. Everything is an ordinary MP4, WAV, picture or JSON file.

- `shots/<shot>.mp4`: one video-only clip per shot at the project size, **exactly** the shot's length. No transition is baked in and there are no extra frames.
  `shots/<shot>.json` says what the clip is: its place in the story, what it should show, its settings, and which source files it came from. `shots/<shot>.jpg` is a poster frame.
- `audio/`: `narration.wav`; each music/ambience bed as used (level, start, fades, loop applied; **not ducked**); `final_mix.wav` is the finished mix. A `.json` beside each says how it was made.
- `sources/`: your original pictures and clips, copied unchanged, named `<asset id>-<original name>`.
- `index.json`: the list of everything above with times, frame numbers, hashes and settings; `SHA256SUMS.txt` lets you check that nothing was changed or damaged.

Times are integer milliseconds on the narration clock, with the matching frame at the project frame rate. A transition into a shot is described in its `.json` (`transitionIn`); apply it with any tool you like.
Nothing here was uploaded anywhere. Licences marked `licenseVerified: false` have not been checked.
"""


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._ -]+", "_", name).strip(" .")[:80] or "file"


def build_assets(
    manifest: Manifest,
    root: Path,
    dest: Path,
    *,
    storyboard: dict[str, Any],
    diagnostics: list[dict[str, Any]],
    project_name: str,
    options: ExportOptions,
    tools: Toolchain,
) -> dict[str, Any]:
    """Write the folder in ``dest.parent/.work-<name>`` and move it to ``dest`` only when complete (never overwrites)."""
    if dest.exists():
        raise RenderError(f"{dest.name} already exists; exports are never overwritten")
    work = dest.parent / f".work-{dest.name}"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    fps = manifest.video.fps
    infos = verify_manifest_assets(tools, manifest, root.resolve())
    plans = [dataclasses.replace(p, tail_frames=0) for p in plan_shots(manifest, fps)]  # exact shot length: no transition handle
    used_ids = {
        i for p in plans for i in (p.shot.sourceAssetIds + [ly.assetId for ly in p.shot.layers] + ([p.shot.rendered.assetId] if p.shot.rendered else []))
    }
    n_steps = len(plans) * 2 + len(manifest.audioTracks) + len(manifest.assets) + 6
    done = 0

    def tick(msg: str) -> None:
        nonlocal done
        if options.cancel is not None and options.cancel.is_set():
            raise RenderCancelled("The export was cancelled. Nothing was published.")
        if options.progress is not None:
            options.progress(min(0.98, done / n_steps), msg)
        done += 1

    t0 = time.perf_counter()
    timeout = options.step_timeout_s
    try:
        # ---- sources: the originals, byte for byte
        (work / "sources").mkdir()
        source_rows: list[dict[str, Any]] = []
        file_of: dict[str, str] = {}
        for a in manifest.assets:
            orig = a.provenance.source.replace("Studio import: ", "")
            tick(f"Copying {orig[:40]}")
            name = f"{a.id}-{_safe_name(Path(orig).stem)}{Path(a.path).suffix}"
            shutil.copyfile(infos[a.id].path, work / "sources" / name)
            file_of[a.id] = f"sources/{name}"
            i = infos[a.id]
            source_rows.append(
                {
                    "assetId": a.id, "file": file_of[a.id], "type": a.type, "kind": a.media_kind, "originalName": orig, "sha256": a.sha256,
                    "width": i.width, "height": i.height, "durationMs": i.duration_ms, "usedInShots": a.id in used_ids, "provenance": a.provenance.model_dump(),
                }
            )
        # ---- shot clips: exact length, with a sidecar and a poster each
        (work / "shots").mkdir()
        shot_rows: list[dict[str, Any]] = []
        for p in plans:
            s = p.shot
            tick(f"Encoding shot {p.index + 1} of {len(plans)}")
            clip = work / "shots" / f"{s.id}.mp4"
            proc = run(build_segment_argv(tools, p, manifest, infos, manifest.video.width, manifest.video.height, fps, clip), timeout=timeout)
            if proc.returncode != 0:
                raise RenderError(f"FFmpeg failed while encoding shot '{s.id}'. Nothing was published. {proc.stderr.strip()[-400:]}")
            probe = ffprobe_json(tools, clip, count_frames=True)
            v = next(x for x in probe["streams"] if x["codec_type"] == "video")
            frames = int(v["nb_read_frames"])
            if frames != p.body_frames or any(x["codec_type"] != "video" for x in probe["streams"]):
                raise RenderError(f"The clip for shot '{s.id}' came out with {frames} frames instead of {p.body_frames}. Nothing was published.")
            tick(f"Poster for shot {p.index + 1} of {len(plans)}")
            _ff(tools, ["-i", clip, "-vf", f"select=eq(n\\,{frames // 2}),scale=640:-2", "-frames:v", "1", "-q:v", "3", work / "shots" / f"{s.id}.jpg"], "making a poster", timeout)
            src_ids = list(dict.fromkeys(s.sourceAssetIds + [ly.assetId for ly in s.layers] + ([s.rendered.assetId] if s.rendered else [])))
            preset = next((sh.get("preset") for sc in storyboard.get("scenes", []) for sh in sc.get("shots", []) if sh["id"] == s.id), None)
            side: dict[str, Any] = {
                "assetsVersion": ASSETS_VERSION, "assetKind": "shot-clip", "id": s.id, "file": f"shots/{s.id}.mp4", "poster": f"shots/{s.id}.jpg", "sha256": sha256_file(clip),
                "video": {"codec": v["codec_name"], "width": int(v["width"]), "height": int(v["height"]), "fps": fps, "frames": frames, "durationMs": round(frames * 1000 / fps), "audio": False},
                "story": {"sceneId": s.sceneId, "order": p.index + 1, "startMs": s.startMs, "endMs": s.endMs, "durationMs": s.durationMs, "startFrame": p.start_frame},
                "intent": {"action": s.action, "mustShow": s.mustShow, "avoid": s.avoid}, "mode": s.mode, "preset": preset,
                "camera": s.camera.model_dump() if s.camera else None, "layers": [ly.model_dump() for ly in s.layers],
                "clip": {"trimStartMs": s.rendered.trimStartMs, "speed": s.rendered.speed} if s.rendered else None,
                "transitionIn": s.transition.model_dump(), "sources": [{"assetId": i, "file": file_of[i]} for i in src_ids],
                "note": "Exact shot length, video only, no transition baked in.",
            }
            (work / "shots" / f"{s.id}.json").write_text(json.dumps(side, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
            shot_rows.append({"id": s.id, "file": side["file"], "sidecar": f"shots/{s.id}.json", "poster": side["poster"], **side["story"], "frames": frames, "mode": s.mode, "transitionIn": side["transitionIn"]})
        # ---- audio
        total_s = (plans[-1].start_frame + plans[-1].body_frames) / fps
        files: dict[str, str] = {}
        beds: list[dict[str, Any]] = []
        write_audio(tools, manifest, infos, work / "audio", total_s, files, beds, timeout, tick)
        audio_rows: list[dict[str, Any]] = []
        nar = manifest.narration
        for key, rel in files.items():
            f = work / rel
            base: dict[str, Any] = {
                "assetsVersion": ASSETS_VERSION, "assetKind": "audio", "file": rel, "sha256": sha256_file(f), "sampleRate": 48000, "channels": 2,
                "format": "pcm_s16le", "durationMs": round(total_s * 1000),
            }
            if key == "narration":
                base |= {"role": "narration", "sourceAssetId": nar.assetId, "sourceFile": file_of[nar.assetId]}
            elif key == "final_mix":
                base |= {"role": "final-mix", "note": "ducked and limited exactly as in the final render"}
            else:
                t = manifest.audioTracks[int(key.split("_")[0].removeprefix("bed")) - 1]
                base |= {
                    "role": t.role, "sourceAssetId": t.assetId, "sourceFile": file_of[t.assetId],
                    "applied": {"gainDb": t.gainDb, "startMs": t.startMs, "fadeInMs": t.fadeInMs, "fadeOutMs": t.fadeOutMs, "loop": t.loop},
                    "notApplied": {"duckDb": t.duckDb}, "note": "level, start, fades and looping are in the file; ducking is not",
                }
            side_path = f.with_suffix(".json")
            side_path.write_text(json.dumps(base, indent=2) + "\n", encoding="utf-8", newline="\n")
            audio_rows.append({"file": rel, "sidecar": side_path.relative_to(work).as_posix(), "role": base["role"], "sha256": base["sha256"]})
        # ---- index, readme, checksums
        tick("Writing the index")
        index = {
            "assetsVersion": ASSETS_VERSION, "project": {"name": project_name, "processorVersion": PROCESSOR_VERSION},
            "video": {"width": manifest.video.width, "height": manifest.video.height, "fps": fps, "fadeInMs": manifest.video.fadeInMs, "fadeOutMs": manifest.video.fadeOutMs},
            "narration": {"assetId": nar.assetId, "durationMs": nar.durationMs},
            "scenes": [{"id": sc.id, "title": sc.title, "shotIds": sc.shotIds, "startMs": sc.narration.startMs, "endMs": sc.narration.endMs} for sc in manifest.scenes],
            "shots": shot_rows, "audio": audio_rows, "sources": source_rows, "diagnostics": diagnostics,
            "howToUse": "See README.md. Every file is a standard format; sha256 values are in SHA256SUMS.txt.",
        }
        (work / "index.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
        (work / "README.md").write_text(ASSETS_README, encoding="utf-8", newline="\n")
        tick("Writing checksums")
        sums = [f"{sha256_file(f)}  {f.relative_to(work).as_posix()}" for f in sorted(work.rglob("*")) if f.is_file()]
        (work / "SHA256SUMS.txt").write_text("\n".join(sums) + "\n", encoding="utf-8", newline="\n")
        rename_with_retry(work, dest, attempts=20, delay=0.1)  # rides out brief virus-scanner locks on Windows
    except BaseException:
        shutil.rmtree(work, ignore_errors=True)
        raise
    files_total = [f for f in dest.rglob("*") if f.is_file()]
    return {
        "folder": dest.name, "mode": "assets", "shots": len(plans), "files": len(files_total), "totalBytes": sum(f.stat().st_size for f in files_total),
        "seconds": round(time.perf_counter() - t0, 1), "indexSha256": sha256_file(dest / "index.json"),
    }
