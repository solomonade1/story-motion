"""Scene-manifest contract v1.0.0 (PRD 11.2).

Invariants enforced here (Charter C3, PRD 11.2 "Validation rules"):
- all times are integer milliseconds; durations are positive;
- shots are contiguous: no gaps, no overlaps, first shot starts at 0;
- every referenced asset exists in the manifest; asset paths are relative and cannot traverse;
- GENERATIVE shots must declare a fallback (FR-ANIM-004) and carry no provider secrets;
- shot coverage ends within 250 ms of the narration duration (QG OPS-02 tolerance).
"""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .errors import FieldIssue, ManifestValidationError

SCHEMA_VERSION = "1.2.0"  # 1.1.0: RENDERED mode + rendered_video assets; 1.2.0: layer pivot (earlier 1.x still reads)
DURATION_TOLERANCE_MS = 250

Ms = Annotated[int, Field(strict=True, ge=0)]
PosMs = Annotated[int, Field(strict=True, gt=0)]
Id = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

AnimationMode = Literal["STATIC", "CINEMATIC", "LAYERED", "GENERATIVE", "RENDERED"]
AssetType = Literal["character", "environment", "prop", "audio", "generated_video", "rendered_video", "effect"]
Easing = Literal["linear", "easeIn", "easeOut", "easeInOut"]
ProvenanceKind = Literal["placeholder", "synthetic", "creator_supplied", "licensed", "mock_provider_output"]

IMAGE_EXT = {".png", ".jpg", ".jpeg", ".webp"}
AUDIO_EXT = {".wav", ".mp3", ".aac"}
VIDEO_EXT = {".mp4", ".mov"}


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Video(_Model):
    width: PosMs
    height: PosMs
    fps: Literal[24, 30]
    fadeInMs: Ms = 0
    fadeOutMs: Ms = 0

    @model_validator(mode="after")
    def _sixteen_nine(self) -> Video:
        if self.width * 9 != self.height * 16:
            raise ValueError("video must be 16:9 (PRD FR-RENDER-002)")
        return self


class Provenance(_Model):
    kind: ProvenanceKind
    source: str = Field(min_length=1)
    license: str = Field(min_length=1)
    licenseVerified: bool
    notes: str = ""


class Asset(_Model):
    id: Id
    type: AssetType
    path: str
    sha256: Sha256
    provenance: Provenance
    characterId: Id | None = None

    @model_validator(mode="after")
    def _safe_path(self) -> Asset:
        p = self.path
        if not p or any(ord(c) < 32 for c in p):
            raise ValueError("path must be non-empty and contain no control characters")
        if "\\" in p or p.startswith("/") or re.match(r"^[A-Za-z]:", p):
            raise ValueError("path must be a relative POSIX path (no backslashes, drive or root)")
        parts = PurePosixPath(p).parts
        if ".." in parts or "." in parts:
            raise ValueError("path must not contain '.' or '..' segments")
        if "://" in p:
            raise ValueError("remote URLs are not allowed; assets are local files (TRUST-02)")
        ext = PurePosixPath(p).suffix.lower()
        if ext not in IMAGE_EXT | AUDIO_EXT | VIDEO_EXT:
            raise ValueError(f"unsupported file extension '{ext}'")
        return self

    @property
    def media_kind(self) -> Literal["image", "audio", "video"]:
        ext = PurePosixPath(self.path).suffix.lower()
        return "image" if ext in IMAGE_EXT else "audio" if ext in AUDIO_EXT else "video"


class Narration(_Model):
    assetId: Id
    durationMs: PosMs


class CameraPose(_Model):
    scale: float = Field(ge=1.0, le=4.0)  # >=1 guarantees no black borders (ANIM-01)
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)


class Camera(_Model):
    start: CameraPose
    end: CameraPose
    easing: Easing = "easeInOut"


class LayerPose(_Model):
    x: float = Field(ge=-0.5, le=1.5)  # normalised frame coords; may start/end off-screen
    y: float = Field(ge=-0.5, le=1.5)
    widthFrac: float = Field(gt=0.0, le=2.0)  # layer width as a fraction of frame width
    rotateDeg: float = Field(default=0.0, ge=-360.0, le=360.0)


class Layer(_Model):
    assetId: Id
    start: LayerPose
    end: LayerPose
    easing: Easing = "easeInOut"
    pivotX: float = Field(default=0.5, ge=0.0, le=1.0)  # rotation centre inside the layer picture (0 = left edge)
    pivotY: float = Field(default=0.5, ge=0.0, le=1.0)  # (0 = top edge). x/y above then place the PIVOT in the frame.
    swayDeg: float = Field(default=0.0, ge=0.0, le=45.0)  # sinusoidal rocking amplitude
    swayPeriodMs: PosMs = 4000


class Effect(_Model):
    type: Literal["flash"]
    atMs: list[Ms] = Field(min_length=1)  # relative to shot start
    intensity: float = Field(default=0.35, gt=0.0, le=1.0)


class Transition(_Model):
    """Transition *into* this shot from the previous one."""

    type: Literal["cut", "crossfade", "fadeblack"] = "cut"
    durationMs: Ms = 0

    @model_validator(mode="after")
    def _consistent(self) -> Transition:
        if self.type == "cut" and self.durationMs != 0:
            raise ValueError("a 'cut' must have durationMs 0")
        if self.type != "cut" and self.durationMs < 100:
            raise ValueError(f"'{self.type}' needs durationMs >= 100")
        return self


class Generation(_Model):
    """Provider-neutral generation info. Never holds credentials or provider-specific fields."""

    providerProfileId: Id
    clipAssetId: Id | None = None  # an approved, already-downloaded clip (type generated_video)


class RenderedClip(_Model):
    """A clip rendered elsewhere by the creator (e.g. Blender). Used as-is, never regenerated."""

    assetId: Id  # asset of type rendered_video
    trimStartMs: Ms = 0  # skip this much of the clip's start
    speed: float = Field(default=1.0, ge=0.5, le=1.5)  # <1 slows the clip down (frames are blended)


class Shot(_Model):
    id: Id
    sceneId: Id
    startMs: Ms
    durationMs: PosMs
    mode: AnimationMode
    fallbackMode: Literal["STATIC", "CINEMATIC"] | None = None
    sourceAssetIds: list[Id] = Field(default_factory=list)
    action: str = ""
    mustShow: list[str] = Field(default_factory=list)
    avoid: list[str] = Field(default_factory=list)
    camera: Camera | None = None
    layers: list[Layer] = Field(default_factory=list)
    effects: list[Effect] = Field(default_factory=list)
    transition: Transition = Field(default_factory=Transition)
    generation: Generation | None = None
    rendered: RenderedClip | None = None
    approval: Literal["pending", "approved", "rejected"] = "pending"

    @property
    def endMs(self) -> int:
        return self.startMs + self.durationMs

    @model_validator(mode="after")
    def _mode_rules(self) -> Shot:
        if self.mode == "RENDERED":
            if self.rendered is None:
                raise ValueError("RENDERED shots require 'rendered'")
            if self.generation is not None or self.fallbackMode is not None:
                raise ValueError("RENDERED shots must not use 'generation' or 'fallbackMode'")
        else:
            if self.rendered is not None:
                raise ValueError("'rendered' is only valid on RENDERED shots")
            if not self.sourceAssetIds:
                raise ValueError("'sourceAssetIds' needs at least one image")
        if self.mode == "CINEMATIC" and self.camera is None:
            raise ValueError("CINEMATIC shots require 'camera'")
        if self.mode == "LAYERED" and not self.layers:
            raise ValueError("LAYERED shots require at least one entry in 'layers'")
        if self.mode == "GENERATIVE":
            if self.generation is None:
                raise ValueError("GENERATIVE shots require 'generation'")
            if self.fallbackMode is None:
                raise ValueError("GENERATIVE shots require 'fallbackMode' (FR-ANIM-004)")
            if self.fallbackMode == "CINEMATIC" and self.camera is None:
                raise ValueError("fallbackMode CINEMATIC requires 'camera'")
        elif self.generation is not None:
            raise ValueError("'generation' is only valid on GENERATIVE shots")
        for e in self.effects:
            if any(t >= self.durationMs for t in e.atMs):
                raise ValueError("effect 'atMs' must be inside the shot duration")
        return self


class SceneNarration(_Model):
    startMs: Ms
    endMs: PosMs


class Scene(_Model):
    id: Id
    title: str
    narration: SceneNarration
    characterIds: list[Id] = Field(default_factory=list)
    shotIds: list[Id] = Field(min_length=1)


class AudioTrack(_Model):
    """A bed under the narration (music or ambience). Ducks while the narrator speaks."""

    assetId: Id
    role: Literal["music", "ambience"] = "music"
    gainDb: float = Field(default=-20.0, ge=-60.0, le=12.0)  # level before ducking
    startMs: Ms = 0
    fadeInMs: Ms = 0
    fadeOutMs: Ms = 0
    loop: bool = True  # repeat if shorter than the video
    duckDb: float = Field(default=10.0, ge=0.0, le=30.0)  # 0 disables ducking under narration


class Manifest(_Model):
    schemaVersion: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    projectId: Id
    title: str
    video: Video
    narration: Narration
    assets: list[Asset] = Field(min_length=1)
    scenes: list[Scene] = Field(min_length=1)
    shots: list[Shot] = Field(min_length=1)
    audioTracks: list[AudioTrack] = Field(default_factory=list)

    @model_validator(mode="after")
    def _cross_field(self) -> Manifest:
        errs: list[str] = []
        if self.schemaVersion.split(".")[0] != SCHEMA_VERSION.split(".")[0]:
            errs.append(
                f"schemaVersion {self.schemaVersion} is not supported (this build reads "
                f"{SCHEMA_VERSION.split('.')[0]}.x)"
            )
        assets = {a.id: a for a in self.assets}
        if len(assets) != len(self.assets):
            errs.append("assets: duplicate asset id")
        shot_ids = [s.id for s in self.shots]
        if len(set(shot_ids)) != len(shot_ids):
            errs.append("shots: duplicate shot id")

        nar = assets.get(self.narration.assetId)
        if nar is None:
            errs.append(f"narration.assetId '{self.narration.assetId}' is not in assets")
        elif nar.type != "audio":
            errs.append("narration.assetId must reference an asset of type 'audio'")

        for i, t in enumerate(self.audioTracks):
            a = assets.get(t.assetId)
            if a is None:
                errs.append(f"audioTracks[{i}].assetId: unknown asset '{t.assetId}'")
            elif a.type != "audio":
                errs.append(f"audioTracks[{i}].assetId: '{t.assetId}' must be an asset of type 'audio'")
            elif t.assetId == self.narration.assetId:
                errs.append(f"audioTracks[{i}].assetId: the narration cannot also be a bed track")
            if t.startMs >= self.narration.durationMs:
                errs.append(f"audioTracks[{i}].startMs is after the end of the narration")

        for i, s in enumerate(self.shots):
            for ref in s.sourceAssetIds:
                a = assets.get(ref)
                if a is None:
                    errs.append(f"shots[{i}] ({s.id}).sourceAssetIds: unknown asset '{ref}'")
                elif a.media_kind != "image":
                    errs.append(f"shots[{i}] ({s.id}).sourceAssetIds: '{ref}' must be an image")
            for j, lay in enumerate(s.layers):
                a = assets.get(lay.assetId)
                if a is None:
                    errs.append(f"shots[{i}] ({s.id}).layers[{j}]: unknown asset '{lay.assetId}'")
                elif a.media_kind != "image":
                    errs.append(f"shots[{i}] ({s.id}).layers[{j}]: '{lay.assetId}' must be an image")
            if s.rendered is not None:
                a = assets.get(s.rendered.assetId)
                if a is None:
                    errs.append(f"shots[{i}] ({s.id}).rendered.assetId: unknown asset '{s.rendered.assetId}'")
                elif a.type != "rendered_video" or a.media_kind != "video":
                    errs.append(f"shots[{i}] ({s.id}).rendered.assetId must be a rendered_video asset")
            if s.generation and s.generation.clipAssetId:
                a = assets.get(s.generation.clipAssetId)
                if a is None:
                    errs.append(f"shots[{i}] ({s.id}).generation.clipAssetId: unknown asset")
                elif a.type != "generated_video" or a.media_kind != "video":
                    errs.append(f"shots[{i}] ({s.id}).generation.clipAssetId must be a generated_video asset")

        prev_end = 0
        for i, s in enumerate(self.shots):
            if s.startMs > prev_end:
                errs.append(
                    f"shots[{i}] ({s.id}): gap of {s.startMs - prev_end} ms before this shot "
                    f"(expected startMs {prev_end})"
                )
            elif s.startMs < prev_end:
                errs.append(
                    f"shots[{i}] ({s.id}): overlaps the previous shot by {prev_end - s.startMs} ms "
                    f"(expected startMs {prev_end})"
                )
            prev_end = s.endMs
            if i == 0 and s.transition.type != "cut":
                errs.append("shots[0]: first shot must use a 'cut' transition (use video.fadeInMs)")
            if i > 0 and s.transition.type != "cut":
                prev = self.shots[i - 1]
                if s.transition.durationMs > min(s.durationMs, prev.durationMs):
                    errs.append(f"shots[{i}] ({s.id}).transition.durationMs exceeds a neighbouring shot's duration")
        if abs(prev_end - self.narration.durationMs) > DURATION_TOLERANCE_MS:
            errs.append(
                f"shots end at {prev_end} ms but narration is {self.narration.durationMs} ms "
                f"(tolerance {DURATION_TOLERANCE_MS} ms)"
            )

        by_id = {s.id: s for s in self.shots}
        seen_in_scene: set[str] = set()
        scene_ids = [sc.id for sc in self.scenes]
        if len(set(scene_ids)) != len(scene_ids):
            errs.append("scenes: duplicate scene id")
        for i, sc in enumerate(self.scenes):
            members = []
            for sid in sc.shotIds:
                sh = by_id.get(sid)
                if sh is None:
                    errs.append(f"scenes[{i}] ({sc.id}).shotIds: unknown shot '{sid}'")
                    continue
                if sh.sceneId != sc.id:
                    errs.append(f"scenes[{i}] ({sc.id}): shot '{sid}' declares sceneId '{sh.sceneId}'")
                if sid in seen_in_scene:
                    errs.append(f"shot '{sid}' appears in more than one scene")
                seen_in_scene.add(sid)
                members.append(sh)
            if members:
                lo, hi = min(m.startMs for m in members), max(m.endMs for m in members)
                if (sc.narration.startMs, sc.narration.endMs) != (lo, hi):
                    errs.append(
                        f"scenes[{i}] ({sc.id}).narration {sc.narration.startMs}-"
                        f"{sc.narration.endMs} ms does not match its shots ({lo}-{hi} ms)"
                    )
        for sid in shot_ids:
            if sid not in seen_in_scene:
                errs.append(f"shot '{sid}' is not listed in any scene")

        if errs:
            raise ValueError("\n".join(errs))
        return self

    def asset(self, asset_id: str) -> Asset:
        return next(a for a in self.assets if a.id == asset_id)


def _loc_to_path(loc: tuple[int | str, ...]) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "$"


def parse_manifest(text: str) -> Manifest:
    """Parse + validate manifest JSON. Raises ManifestValidationError with locations."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(
            [FieldIssue(f"line {exc.lineno}, column {exc.colno}", f"invalid JSON: {exc.msg}")]
        ) from exc
    try:
        return Manifest.model_validate(raw, strict=False)
    except ValidationError as exc:
        issues: list[FieldIssue] = []
        for e in exc.errors():
            msg = str(e["msg"]).removeprefix("Value error, ")
            for line in msg.splitlines():
                issues.append(FieldIssue(_loc_to_path(e["loc"]), line))
        raise ManifestValidationError(issues) from exc


def load_manifest(path: Path) -> Manifest:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ManifestValidationError([FieldIssue(str(path), f"cannot read manifest: {exc}")]) from exc
    return parse_manifest(text)


def export_json_schema() -> dict[str, object]:
    return Manifest.model_json_schema()
