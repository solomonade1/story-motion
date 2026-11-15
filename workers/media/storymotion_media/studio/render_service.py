"""Storyboard -> scene manifest -> verified MP4 (Phase 2; FR-RENDER-001..005, FR-ANIM-001, FR-TIME-005).

Rules:
- Nothing renders while the storyboard has problems the editor reports (gaps, overlaps, missing pictures, ...).
  The renderer never "fixes" timing; it refuses and says what to change.
- Source files are never modified. Linked files outside the project are hard-linked (or copied) into
  ``renders/_linked`` so the manifest only ever holds contained relative paths.
- Every render is a new numbered file in ``<project>/renders``; earlier renders are never overwritten.
"""

from __future__ import annotations

import dataclasses
import json
import os
import re
import shutil
import threading
from pathlib import Path, PurePosixPath
from typing import Any

from ..contracts import SCHEMA_VERSION, Manifest, parse_manifest
from ..errors import RenderCancelled
from ..export_pack import ExportOptions, build_export
from ..render import RenderOptions, render
from ..toolchain import Toolchain
from .assets import AssetService
from .atomic import atomic_write_text
from .errors import InvalidInput, StudioError
from .paths import new_id
from .presets import HOLD, camera_for
from .store import Project
from .storyboard import Storyboard, blocking, diagnose, parse_storyboard

EXPORT_NAME_RE = r"^x-[0-9a-f]{12}-(full|brief|assets)$"
RENDER_NAME_RE = r"^r-[0-9a-f]{12}-(draft|final)\.(mp4|json)$"
# Warnings that make a render pointless or misleading: the creator must resolve them first.
MUST_FIX = {
    "gap", "overlap", "late-start", "past-narration", "short-of-narration", "no-narration", "no-image", "no-clip", "no-shots", "no-layers", "first-transition", "transition-too-long", "bed-after-narration",
}
IMAGE_CATEGORIES = {"character", "environment", "prop", "effect"}


class NotRenderReady(StudioError):
    code = "not_render_ready"
    http_status = 409


class RenderNotFound(StudioError):
    code = "render_not_found"
    http_status = 404


class RenderService:
    def __init__(self, project: Project, assets: AssetService, tc: Toolchain) -> None:
        self.p, self.assets, self.tc = project, assets, tc
        self.dir = project.dir / "renders"

    # ------------------------------------------------------------------ preparation
    def _stage(self, a: dict[str, Any]) -> str:
        """Project-relative POSIX path for an asset; linked files are staged inside the project first."""
        if a["mode"] == "copy" and a["rel_path"]:
            return str(a["rel_path"]).replace("\\", "/")
        src = Path(a["abs_path"])
        dest = self.dir / "_linked" / f"{a['id']}{src.suffix.lower()}"
        if not dest.exists() or dest.stat().st_size != src.stat().st_size:
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".tmp")
            tmp.unlink(missing_ok=True)
            try:
                os.link(src, tmp)  # no extra disk space when source and project share a drive
            except OSError:
                shutil.copyfile(src, tmp)
            os.replace(tmp, dest)
        return PurePosixPath(dest.relative_to(self.p.dir).as_posix()).as_posix()

    def prepare(self) -> tuple[Manifest, list[str]]:
        """Build the manifest or raise NotRenderReady listing exactly what to fix. Returns (manifest, notes)."""
        doc, _ = self.p.load()
        raw = doc.ext.get("storyboard")
        if raw is None:
            raise NotRenderReady("There is no storyboard yet. Add scenes and shots on the Storyboard tab first.")
        sb: Storyboard = parse_storyboard(raw)
        lib = {a["id"]: a for a in self.assets.list_assets()}
        nar = lib.get(sb.narrationAssetId) if sb.narrationAssetId else None
        nar_ms = nar.get("duration_ms") if nar and nar["kind"] == "audio" and nar["status"] == "ok" else None
        diags = diagnose(sb, narration_ms=nar_ms, assets=lib)
        stoppers = [d for d in diags if d["severity"] == "error" or d["code"] in MUST_FIX]
        notes: list[str] = []
        if stoppers or nar_ms is None or sb.narrationAssetId is None:
            shown = "; ".join(d["message"] for d in stoppers[:6])
            more = f" (and {len(stoppers) - 6} more)" if len(stoppers) > 6 else ""
            raise NotRenderReady(f"The storyboard is not ready to render: {shown}{more}")

        shots: list[dict[str, Any]] = []
        scenes: list[dict[str, Any]] = []
        used: set[str] = {sb.narrationAssetId}
        for sc in sb.scenes:
            if not sc.shots:
                notes.append(f"Scene '{sc.title or sc.id}' has no shots and is skipped.")
                continue
            for sh in sc.shots:
                entry: dict[str, Any] = {
                    "id": sh.id, "sceneId": sc.id, "startMs": sh.startMs, "durationMs": sh.durationMs, "action": sh.action,
                    "mustShow": sh.mustShow, "avoid": sh.avoid, "approval": "approved",
                }
                cam = camera_for(sh.preset)
                if sh.mode == "RENDERED":
                    assert sh.clipAssetId is not None
                    speed = sh.speed
                    if sh.fitSpeed:  # slow the clip just enough to fill the shot; never faster than 1x, never below 0.6x
                        clip_ms = lib[sh.clipAssetId].get("duration_ms") or 0
                        speed = round(min(1.0, max(0.6, (clip_ms - sh.trimStartMs) / sh.durationMs)), 3) if clip_ms else 1.0
                    entry |= {"mode": "RENDERED", "rendered": {"assetId": sh.clipAssetId, "trimStartMs": sh.trimStartMs, "speed": speed}}
                    used.add(sh.clipAssetId)
                else:
                    assert sh.imageAssetId is not None
                    used.add(sh.imageAssetId)
                    entry["sourceAssetIds"] = [sh.imageAssetId]
                    if sh.mode == "GENERATIVE":
                        entry |= {"mode": "GENERATIVE", "generation": {"providerProfileId": "none"}}
                        entry["fallbackMode"] = "STATIC" if cam is None else "CINEMATIC"
                        if cam is not None:
                            entry["camera"] = cam
                        notes.append(f"Shot {sh.id} is GENERATIVE: no AI request is made; it renders with its local fallback.")
                    elif sh.mode == "LAYERED":
                        entry |= {"mode": "LAYERED"}
                        if cam is not None and sh.preset not in (None, HOLD):  # the camera moves only if a preset asks for it
                            entry["camera"] = cam
                        entry["layers"] = [ly.model_dump() for ly in sh.layers]
                        used.update(ly.assetId for ly in sh.layers)
                    elif sh.mode == "CINEMATIC" and cam is not None:
                        entry |= {"mode": "CINEMATIC", "camera": cam}
                    else:  # STATIC, or CINEMATIC + 'hold'
                        entry["mode"] = "STATIC"
                        if sh.mode == "STATIC" and sh.preset not in (None, HOLD):
                            notes.append(f"Shot {sh.id}: preset '{sh.preset}' is ignored because the mode is STATIC. Use CINEMATIC to apply it.")
                if sh.transition.type != "cut":
                    entry["transition"] = {"type": sh.transition.type, "durationMs": sh.transition.durationMs}
                shots.append(entry)
            ms = [s for s in shots if s["sceneId"] == sc.id]
            scenes.append(
                {
                    "id": sc.id, "title": sc.title or sc.id, "characterIds": sc.characterIds,
                    "narration": {"startMs": ms[0]["startMs"], "endMs": ms[-1]["startMs"] + ms[-1]["durationMs"]},
                    "shotIds": [m["id"] for m in ms],
                }
            )
        tracks = []
        for t in sb.audioTracks:
            used.add(t.assetId)
            tracks.append(t.model_dump())
        assets = []
        for aid in sorted(used):
            a = lib[aid]
            typ = "audio" if a["kind"] == "audio" else "rendered_video" if a["kind"] == "video" else (
                a["category"] if a["category"] in IMAGE_CATEGORIES else "environment"
            )
            assets.append(
                {
                    "id": aid, "type": typ, "path": self._stage(a), "sha256": a["sha256"],
                    "provenance": {
                        "kind": "creator_supplied", "source": f"Studio import: {a['orig_name']}"[:200],
                        "license": "creator-supplied (not verified in Studio)", "licenseVerified": False,
                    },
                }
            )
        manifest = parse_manifest(
            json.dumps(
                {
                    "schemaVersion": SCHEMA_VERSION, "projectId": doc.projectId.replace("p-", "studio-"), "title": doc.name,
                    "video": {"width": doc.video.width, "height": doc.video.height, "fps": doc.video.fps, "fadeInMs": sb.fadeInMs, "fadeOutMs": sb.fadeOutMs},
                    "audioTracks": tracks,
                    "narration": {"assetId": sb.narrationAssetId, "durationMs": nar_ms},
                    "assets": assets, "scenes": scenes, "shots": shots,
                }
            )
        )
        return manifest, notes

    # ------------------------------------------------------------------ rendering
    def run(self, manifest: Manifest, notes: list[str], *, draft: bool, progress: Any, cancel: threading.Event) -> dict[str, Any]:
        rid = new_id("r")
        stem = f"{rid}-{'draft' if draft else 'final'}"
        self.dir.mkdir(exist_ok=True)
        out = self.dir / f"{stem}.mp4"
        try:
            rep = render(manifest, self.p.dir, out, RenderOptions(draft=draft, progress=progress, cancel=cancel), self.tc)
        except RenderCancelled:
            return {"cancelled": True}
        atomic_write_text(self.dir / f"{stem}.json", json.dumps(dataclasses.asdict(rep), indent=2) + "\n")
        return {
            "file": out.name, "report": f"{stem}.json", "draft": draft, "sha256": rep.output["sha256"],
            "sizeBytes": rep.output["sizeBytes"], "frames": rep.output["frames"], "width": rep.width, "height": rep.height,
            "fps": rep.fps, "seconds": rep.timings_s.get("total"), "warnings": rep.warnings + notes, "fallbacks": rep.fallbacks,
            "fidelity": "draft proxy (640x360, badge)" if draft else "final export",
        }

    # ------------------------------------------------------------------ export package (editors, AI models)
    def export(self, manifest: Manifest, mode: str, *, progress: Any, cancel: threading.Event) -> dict[str, Any]:
        from ..errors import RenderCancelled

        doc, _ = self.p.load()
        sb = parse_storyboard(doc.ext["storyboard"])
        lib = {a["id"]: a for a in self.assets.list_assets()}
        nar = lib.get(sb.narrationAssetId) if sb.narrationAssetId else None
        diags = diagnose(sb, narration_ms=nar.get("duration_ms") if nar else None, assets=lib)
        eid = new_id("x")
        dest = self.p.dir / "exports" / f"{eid}-{mode}"
        dest.parent.mkdir(exist_ok=True)
        try:
            res = build_export(
                manifest, self.p.dir, dest, storyboard=sb.model_dump(), diagnostics=diags, project_name=doc.name,
                options=ExportOptions(mode="full" if mode == "full" else "assets" if mode == "assets" else "brief", progress=progress, cancel=cancel), tc_tools=self.tc,
            )
        except RenderCancelled:
            return {"cancelled": True}
        return res

    def list_exports(self) -> list[dict[str, Any]]:
        d = self.p.dir / "exports"
        out: list[dict[str, Any]] = []
        if d.is_dir():
            for f in sorted((x for x in d.iterdir() if x.is_dir() and re.match(EXPORT_NAME_RE, x.name)), key=lambda x: x.stat().st_mtime, reverse=True):
                size = sum(q.stat().st_size for q in f.rglob("*") if q.is_file())
                out.append({"folder": f.name, "mode": f.name.rsplit("-", 1)[1], "sizeBytes": size, "modified": f.stat().st_mtime})
        return out

    def export_folder(self, name: str) -> Path:
        if not re.match(EXPORT_NAME_RE, name):
            raise InvalidInput("That is not an export folder name.")
        f = self.p.dir / "exports" / name
        if not f.is_dir():
            raise RenderNotFound("That export no longer exists.")
        return f

    def list_renders(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        if not self.dir.is_dir():
            return out
        for f in sorted(self.dir.glob("r-*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
            out.append({"file": f.name, "draft": f.stem.endswith("-draft"), "sizeBytes": f.stat().st_size, "modified": f.stat().st_mtime})
        return out

    def file(self, name: str) -> Path:
        if not re.match(RENDER_NAME_RE, name):
            raise InvalidInput("That is not a render file name.")
        f = self.dir / name
        if not f.is_file():
            raise RenderNotFound("That render no longer exists.")
        return f


__all__ = ["NotRenderReady", "RenderService", "blocking"]
