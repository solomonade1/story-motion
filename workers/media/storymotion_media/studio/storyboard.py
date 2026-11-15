"""Storyboard: the editable scene/shot plan of a Studio project (Phase 2; FR-SCRIPT-001..004, FR-TIME-001/004).

Narration is the master clock (ADR-0002): every time is an integer millisecond on the narration's timeline, and
the narration's duration comes from the imported audio asset, never from the storyboard.

Two layers, deliberately separate so a creator can save half-finished work:
- **Structure errors** (``parse_storyboard``): malformed data - wrong types, non-integer or negative times, a zero
  duration, duplicate ids. Refused with a field-located message; nothing is saved.
- **Diagnostics** (``diagnose``): a well-formed storyboard that is not yet render-ready - gaps, overlaps, shots past
  the end of the narration, missing images. Saved as-is and listed with exact amounts, never silently repaired.

The storyboard is stored in the project document at ``ext["storyboard"]``.
"""

from __future__ import annotations

import json
import re
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from ..contracts import DURATION_TOLERANCE_MS, _loc_to_path
from ..errors import FieldIssue, ManifestValidationError

STORYBOARD_VERSION = "1.1.0"  # 1.1.0: transitions, clip trim/speed, audio tracks, fades (1.0.x still reads)
MAX_SCRIPT_CHARS = 2_000_000
MAX_SCENES = 500
MAX_SHOTS = 5000

Id = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_-]{0,63}$")]
AssetRef = Annotated[str, Field(pattern=r"^a-[0-9a-f]{12}$")]
Text = Annotated[str, Field(max_length=2000)]
Mode = Literal["STATIC", "CINEMATIC", "LAYERED", "RENDERED", "GENERATIVE"]
IMAGE_MODES = {"STATIC", "CINEMATIC", "LAYERED"}


class _M(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Character(_M):
    id: Id
    name: Annotated[str, Field(min_length=1, max_length=120)]


class SbTransition(_M):
    """Transition *into* this shot. It starts when the shot starts and lasts ``durationMs``."""

    type: Literal["cut", "crossfade", "fadeblack"] = "cut"
    durationMs: Annotated[int, Field(strict=True, ge=0, le=5000)] = 0

    @model_validator(mode="after")
    def _consistent(self) -> SbTransition:
        if self.type == "cut" and self.durationMs != 0:
            raise ValueError("a 'cut' must have durationMs 0")
        if self.type != "cut" and self.durationMs < 100:
            raise ValueError(f"'{self.type}' needs durationMs of at least 100")
        return self


class SbAudioTrack(_M):
    """Music or ambience under the narration; it ducks while the narrator speaks."""

    assetId: AssetRef
    role: Literal["music", "ambience"] = "music"
    gainDb: Annotated[float, Field(ge=-60.0, le=12.0)] = -20.0
    startMs: Annotated[int, Field(strict=True, ge=0)] = 0
    fadeInMs: Annotated[int, Field(strict=True, ge=0)] = 0
    fadeOutMs: Annotated[int, Field(strict=True, ge=0)] = 0
    loop: bool = True
    duckDb: Annotated[float, Field(ge=0.0, le=30.0)] = 10.0


Easing = Literal["linear", "easeIn", "easeOut", "easeInOut"]


class SbLayerPose(_M):
    """Where a layer's pivot is in the frame (0..1 of width/height; may start or end off-screen), its size and tilt."""

    x: Annotated[float, Field(ge=-0.5, le=1.5)]
    y: Annotated[float, Field(ge=-0.5, le=1.5)]
    widthFrac: Annotated[float, Field(gt=0.0, le=2.0)]  # layer width as a fraction of frame width
    rotateDeg: Annotated[float, Field(ge=-360.0, le=360.0)] = 0.0


class SbLayer(_M):
    """A separate picture with transparency (a character, a prop) that moves over the shot's background picture."""

    assetId: AssetRef
    start: SbLayerPose
    end: SbLayerPose
    easing: Easing = "easeInOut"
    pivotX: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5  # turning point inside the layer picture (0 = left edge)
    pivotY: Annotated[float, Field(ge=0.0, le=1.0)] = 0.5  # (0 = top edge)
    swayDeg: Annotated[float, Field(ge=0.0, le=45.0)] = 0.0  # gentle rocking amplitude
    swayPeriodMs: Annotated[int, Field(strict=True, gt=0, le=60000)] = 4000


class SbShot(_M):
    id: Id
    startMs: Annotated[int, Field(strict=True, ge=0)]
    durationMs: Annotated[int, Field(strict=True, gt=0)]
    mode: Mode = "STATIC"
    imageAssetId: AssetRef | None = None  # picture (STATIC/CINEMATIC/LAYERED)
    clipAssetId: AssetRef | None = None  # creator-rendered clip (RENDERED)
    characterIds: list[Id] = Field(default_factory=list, max_length=32)
    action: Text = ""
    mustShow: list[Text] = Field(default_factory=list, max_length=32)
    avoid: list[Text] = Field(default_factory=list, max_length=32)
    preset: Id | None = None  # named camera/motion preset (moves CINEMATIC shots)
    transition: SbTransition = Field(default_factory=SbTransition)
    trimStartMs: Annotated[int, Field(strict=True, ge=0)] = 0  # RENDERED: skip this much of the clip's start
    speed: Annotated[float, Field(ge=0.5, le=1.5)] = 1.0  # RENDERED: below 1 slows the clip (frames are blended)
    layers: list[SbLayer] = Field(default_factory=list, max_length=8)  # LAYERED: back to front
    fitSpeed: bool = False  # RENDERED: slow the clip just enough to fill the shot (never faster than 1x, never below 0.6x)

    @property
    def endMs(self) -> int:
        return self.startMs + self.durationMs


class SbScene(_M):
    id: Id
    title: Annotated[str, Field(max_length=200)] = ""
    text: Annotated[str, Field(max_length=20000)] = ""  # the script passage this scene narrates
    characterIds: list[Id] = Field(default_factory=list, max_length=32)
    shots: list[SbShot] = Field(default_factory=list, max_length=500)


class Storyboard(_M):
    storyboardVersion: str = STORYBOARD_VERSION
    narrationAssetId: AssetRef | None = None
    fadeInMs: Annotated[int, Field(strict=True, ge=0, le=10000)] = 0  # video fade from black at the start
    fadeOutMs: Annotated[int, Field(strict=True, ge=0, le=10000)] = 0  # video fade to black at the end
    audioTracks: list[SbAudioTrack] = Field(default_factory=list, max_length=8)
    characters: list[Character] = Field(default_factory=list, max_length=64)
    scenes: list[SbScene] = Field(default_factory=list, max_length=MAX_SCENES)

    @model_validator(mode="after")
    def _unique_and_known(self) -> Storyboard:
        errs: list[str] = []
        if self.storyboardVersion.split(".")[0] != STORYBOARD_VERSION.split(".")[0]:
            errs.append(
                f"storyboardVersion {self.storyboardVersion} is not supported (this build reads "
                f"{STORYBOARD_VERSION.split('.')[0]}.x)"
            )
        for label, ids in (
            ("characters", [c.id for c in self.characters]),
            ("scenes", [s.id for s in self.scenes]),
            ("shots", [sh.id for s in self.scenes for sh in s.shots]),
        ):
            dup = sorted({i for i in ids if ids.count(i) > 1})
            if dup:
                errs.append(f"{label}: duplicate id {', '.join(dup)}")
        if sum(len(s.shots) for s in self.scenes) > MAX_SHOTS:
            errs.append(f"shots: at most {MAX_SHOTS} shots per storyboard")
        known = {c.id for c in self.characters}
        for i, sc in enumerate(self.scenes):
            for cid in sc.characterIds:
                if cid not in known:
                    errs.append(f"scenes[{i}] ({sc.id}).characterIds: unknown character '{cid}'")
            for j, sh in enumerate(sc.shots):
                for cid in sh.characterIds:
                    if cid not in known:
                        errs.append(f"scenes[{i}].shots[{j}] ({sh.id}).characterIds: unknown character '{cid}'")
        if errs:
            raise ValueError("\n".join(errs))
        return self

    def all_shots(self) -> list[SbShot]:
        return [sh for sc in self.scenes for sh in sc.shots]


def parse_storyboard(raw: object) -> Storyboard:
    """Validate parsed JSON. Raises ManifestValidationError carrying one FieldIssue per problem."""
    try:
        return Storyboard.model_validate(raw)
    except ValidationError as exc:
        issues: list[FieldIssue] = []
        for e in exc.errors():
            msg = str(e["msg"]).removeprefix("Value error, ")
            for line in msg.splitlines():
                issues.append(FieldIssue(_loc_to_path(e["loc"]), line))
        raise ManifestValidationError(issues) from exc


def parse_plan_text(text: str) -> Storyboard:
    """Import a scene-plan JSON document (same shape as the stored storyboard)."""
    if len(text) > MAX_SCRIPT_CHARS:
        raise ManifestValidationError([FieldIssue("$", "the plan file is too large")])
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ManifestValidationError(
            [FieldIssue(f"line {exc.lineno}, column {exc.colno}", f"invalid JSON: {exc.msg}")]
        ) from exc
    if not isinstance(raw, dict):
        raise ManifestValidationError([FieldIssue("$", "a scene plan must be a JSON object")])
    return parse_storyboard(raw)


# ------------------------------------------------------------------------------------------------ script import
_HEADING = re.compile(r"^\s{0,3}#{1,3}\s+(.+?)\s*#*\s*$")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _slug(n: int) -> str:
    return f"scene-{n}"


def import_script(text: str, *, filename: str = "") -> Storyboard:
    """Turn a TXT/MD script into scenes (no shots yet: timing comes from the narration).

    Markdown: each ``#``/``##``/``###`` heading starts a scene; the text under it is that scene's passage.
    Plain text: each blank-line-separated paragraph is a scene. Text before the first heading is its own scene.
    """
    if not isinstance(text, str) or not text.strip():
        raise ManifestValidationError([FieldIssue("script", "the script is empty")])
    if len(text) > MAX_SCRIPT_CHARS:
        raise ManifestValidationError([FieldIssue("script", f"the script is longer than {MAX_SCRIPT_CHARS} characters")])
    text = _CONTROL.sub("", text.replace("\r\n", "\n").replace("\r", "\n"))
    is_md = filename.lower().endswith((".md", ".markdown")) or any(_HEADING.match(ln) for ln in text.split("\n"))
    blocks: list[tuple[str, list[str]]] = []  # (title, paragraph lines)
    if is_md:
        title = ""
        body: list[str] = []
        for ln in text.split("\n"):
            m = _HEADING.match(ln)
            if m:
                if title or any(b.strip() for b in body):
                    blocks.append((title, body))
                title, body = m.group(1).strip(), []
            else:
                body.append(ln)
        if title or any(b.strip() for b in body):
            blocks.append((title, body))
    else:
        paras = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
        if len(paras) == 1:  # no blank lines at all: the script is one narration line per line
            paras = [ln for ln in paras[0].split("\n") if ln.strip()]
        for para in paras:
            blocks.append(("", para.split("\n")))
    scenes: list[SbScene] = []
    for n, (title, body) in enumerate(blocks, start=1):
        passage = re.sub(r"\s*\n\s*", " ", "\n".join(body).strip())
        passage = re.sub(r"[ \t]{2,}", " ", passage)
        if not title and not passage:
            continue
        scenes.append(
            SbScene(id=_slug(n), title=(title or f"Scene {n}")[:200], text=passage[:20000])
        )
        if len(scenes) > MAX_SCENES:
            raise ManifestValidationError([FieldIssue("script", f"more than {MAX_SCENES} scenes; split the script")])
    if not scenes:
        raise ManifestValidationError([FieldIssue("script", "no scenes were found in the script")])
    return Storyboard(scenes=scenes)


# ------------------------------------------------------------------------------------------------ diagnostics
Severity = Literal["error", "warning", "info"]


def _d(sev: Severity, code: str, where: str, message: str, shot: str | None = None) -> dict[str, Any]:
    return {"severity": sev, "code": code, "where": where, "message": message, "shotId": shot}


def diagnose(sb: Storyboard, *, narration_ms: int | None, assets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Everything that stops this storyboard rendering, with exact amounts.

    ``assets`` maps asset id -> the project's asset record (category, kind, status). Order of shots is the
    order they play: scenes in order, shots in order inside each scene.
    """
    out: list[dict[str, Any]] = []
    shots = sb.all_shots()
    if sb.narrationAssetId is None:
        out.append(_d("warning", "no-narration", "narrationAssetId", "Choose the narration. Shot times are measured on it."))
    else:
        a = assets.get(sb.narrationAssetId)
        if a is None:
            out.append(_d("error", "narration-missing", "narrationAssetId", "The chosen narration is no longer in the media library."))
        elif a.get("kind") != "audio":
            out.append(_d("error", "narration-not-audio", "narrationAssetId", "The chosen narration is not an audio file."))
        elif a.get("status") != "ok":
            out.append(_d("error", "narration-unavailable", "narrationAssetId", "The narration file is missing or changed; relink it in the media library."))
    if not shots:
        out.append(_d("info", "no-shots", "scenes", "No shots yet. Add shots to each scene to build the timeline."))
        return out

    prev_end = last_end = 0
    for k, sh in enumerate(shots):
        w = f"shot {sh.id}"
        if sh.startMs > prev_end:
            out.append(_d("warning", "gap", w, f"Gap of {sh.startMs - prev_end} ms before this shot (expected start {prev_end} ms).", sh.id))
        elif sh.startMs < prev_end:
            out.append(_d("warning", "overlap", w, f"Overlaps the previous shot by {prev_end - sh.startMs} ms (expected start {prev_end} ms).", sh.id))
        if k == 0 and sh.startMs != 0:
            out.append(_d("warning", "late-start", w, f"The first shot starts at {sh.startMs} ms, so the opening {sh.startMs} ms would be black."))
        prev_end = sh.endMs
        last_end = max(last_end, sh.endMs)
        if narration_ms is not None and sh.startMs >= narration_ms:
            out.append(_d("error", "after-narration", w, f"Starts at {sh.startMs} ms, after the narration ends ({narration_ms} ms).", sh.id))
        elif narration_ms is not None and sh.endMs > narration_ms + DURATION_TOLERANCE_MS:
            out.append(_d("warning", "past-narration", w, f"Ends {sh.endMs - narration_ms} ms after the narration (allowed {DURATION_TOLERANCE_MS} ms).", sh.id))
        if sh.mode in IMAGE_MODES:
            ref = sh.imageAssetId
            if ref is None:
                out.append(_d("warning", "no-image", w, f"{sh.mode} shots need a picture.", sh.id))
            else:
                a = assets.get(ref)
                if a is None:
                    out.append(_d("error", "image-missing", w, "The chosen picture is no longer in the media library.", sh.id))
                elif a.get("kind") != "image":
                    out.append(_d("error", "image-not-image", w, "The chosen file is not a picture.", sh.id))
                elif a.get("status") != "ok":
                    out.append(_d("error", "image-unavailable", w, "The picture file is missing or changed; relink it in the media library.", sh.id))
        elif sh.mode == "RENDERED":
            a = assets.get(sh.clipAssetId) if sh.clipAssetId else None
            if sh.clipAssetId is None:
                out.append(_d("warning", "no-clip", w, "RENDERED shots need a video clip.", sh.id))
            elif a is None or a.get("kind") != "video":
                out.append(_d("error", "clip-invalid", w, "The chosen clip is missing from the library or is not a video.", sh.id))
            elif a.get("status") != "ok":
                out.append(_d("error", "clip-unavailable", w, "The clip file is missing or changed; relink it in the media library.", sh.id))
        if sh.mode == "LAYERED":
            if not sh.layers:
                out.append(_d("warning", "no-layers", w, "LAYERED shots need at least one layer (a picture with transparency).", sh.id))
            for j, ly in enumerate(sh.layers):
                la = assets.get(ly.assetId)
                where = f"{w}, layer {j + 1}"
                if la is None:
                    out.append(_d("error", "layer-missing", where, "The layer picture is no longer in the media library.", sh.id))
                elif la.get("kind") != "image":
                    out.append(_d("error", "layer-not-image", where, "The layer file is not a picture.", sh.id))
                elif la.get("status") != "ok":
                    out.append(_d("error", "layer-unavailable", where, "The layer picture is missing or changed; relink it in the media library.", sh.id))
        elif sh.layers:
            out.append(_d("info", "layers-ignored", w, f"This {sh.mode} shot has layers, which only LAYERED shots use.", sh.id))
        if sh.mode == "STATIC" and sh.preset not in (None, "hold"):
            out.append(_d("info", "preset-ignored", w, f"The '{sh.preset}' preset only moves CINEMATIC shots; this STATIC shot will not move.", sh.id))
        if sh.mode == "GENERATIVE":
            out.append(_d("warning", "generative-unavailable", w, "AI-generated motion is not available in this version; this shot will use a local fallback.", sh.id))
    if narration_ms is not None and last_end < narration_ms - DURATION_TOLERANCE_MS:
        out.append(_d("warning", "short-of-narration", "timeline", f"The shots end {narration_ms - last_end} ms before the narration does (allowed {DURATION_TOLERANCE_MS} ms)."))
    for k, sh in enumerate(shots):
        tr = sh.transition
        if tr.type != "cut":
            if k == 0:
                out.append(_d("warning", "first-transition", f"shot {sh.id}", "The first shot cannot have a transition into it. Use the video fade-in instead.", sh.id))
            elif tr.durationMs > min(sh.durationMs, shots[k - 1].durationMs):
                out.append(_d("warning", "transition-too-long", f"shot {sh.id}", f"The {tr.durationMs} ms transition is longer than a neighbouring shot ({min(sh.durationMs, shots[k - 1].durationMs)} ms).", sh.id))
        if sh.mode == "RENDERED" and sh.clipAssetId:
            clip = assets.get(sh.clipAssetId)
            clip_ms = clip.get("duration_ms") if clip else None
            if clip_ms and sh.trimStartMs >= clip_ms:
                out.append(_d("error", "trim-past-clip", f"shot {sh.id}", f"Trim start {sh.trimStartMs} ms is past the end of the clip ({clip_ms} ms).", sh.id))
    for i, t in enumerate(sb.audioTracks):
        w = f"audio track {i + 1}"
        a = assets.get(t.assetId)
        if a is None:
            out.append(_d("error", "bed-missing", w, "This music/ambience file is no longer in the media library."))
        elif a.get("kind") != "audio":
            out.append(_d("error", "bed-not-audio", w, "This music/ambience file is not an audio file."))
        elif a.get("status") != "ok":
            out.append(_d("error", "bed-unavailable", w, "The music/ambience file is missing or changed; relink it in the media library."))
        elif t.assetId == sb.narrationAssetId:
            out.append(_d("error", "bed-is-narration", w, "The narration cannot also be a music/ambience track."))
        if narration_ms is not None and t.startMs >= narration_ms:
            out.append(_d("warning", "bed-after-narration", w, f"Starts at {t.startMs} ms, after the narration ends ({narration_ms} ms)."))
    for sc in sb.scenes:
        if not sc.shots:
            out.append(_d("info", "empty-scene", f"scene {sc.id}", f"Scene '{sc.title or sc.id}' has no shots yet."))
    return out


def blocking(diagnostics: list[dict[str, Any]]) -> bool:
    return any(d["severity"] == "error" for d in diagnostics)
