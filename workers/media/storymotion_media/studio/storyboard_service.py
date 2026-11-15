"""Load/save a project's storyboard and attach live diagnostics (narration length + asset state come from the library)."""

from __future__ import annotations

from typing import Any

from ..errors import FieldIssue, ManifestValidationError
from .assets import AssetService
from .errors import InvalidInput
from .store import Project
from .storyboard import Storyboard, diagnose, import_script, parse_plan_text, parse_storyboard


class StoryboardService:
    def __init__(self, project: Project, assets: AssetService) -> None:
        self.p, self.assets = project, assets

    def _view(self, sb: Storyboard, revision: int) -> dict[str, Any]:
        lib = {a["id"]: a for a in self.assets.list_assets()}
        nar = lib.get(sb.narrationAssetId) if sb.narrationAssetId else None
        narration_ms = nar.get("duration_ms") if nar and nar.get("kind") == "audio" and nar.get("status") == "ok" else None
        return {
            "storyboard": sb.model_dump(),
            "narrationMs": narration_ms,
            "diagnostics": diagnose(sb, narration_ms=narration_ms, assets=lib),
            "revision": revision,
        }

    def get(self) -> dict[str, Any]:
        doc, _ = self.p.load()
        raw = doc.ext.get("storyboard")
        sb = parse_storyboard(raw) if raw is not None else Storyboard()
        return self._view(sb, doc.revision)

    def _save(self, sb: Storyboard, base_revision: int | None) -> dict[str, Any]:
        with self.p.lock:
            doc, _ = self.p.load()
            ext = dict(doc.ext)
            ext["storyboard"] = sb.model_dump()
            new = self.p.update({"ext": ext}, base_revision)
        return self._view(sb, new.revision)

    def put(self, raw: object, base_revision: int | None) -> dict[str, Any]:
        return self._save(parse_storyboard(raw), base_revision)

    def import_script(self, text: object, filename: object, *, replace: bool, base_revision: int | None) -> dict[str, Any]:
        if not isinstance(text, str):
            raise InvalidInput("'text' must be the script text.")
        if not isinstance(filename, str):
            filename = ""
        incoming = import_script(text, filename=filename)
        current = self.get()["storyboard"]
        if any(sc["shots"] for sc in current["scenes"]) and not replace:
            raise InvalidInput(
                "This project already has shots. Importing a script would replace the scenes and their shots. "
                "Confirm the replacement to continue."
            )
        keep = Storyboard.model_validate({**incoming.model_dump(), "narrationAssetId": current["narrationAssetId"],
                                          "characters": current["characters"]})
        return self._save(keep, base_revision)

    def import_plan(self, text: object, *, replace: bool, base_revision: int | None) -> dict[str, Any]:
        if not isinstance(text, str):
            raise InvalidInput("'text' must be the plan JSON.")
        incoming = parse_plan_text(text)
        current = self.get()["storyboard"]
        if (current["scenes"]) and not replace:
            raise InvalidInput(
                "This project already has a storyboard. Importing a plan would replace it. Confirm the replacement to continue."
            )
        return self._save(incoming, base_revision)


__all__ = ["FieldIssue", "ManifestValidationError", "StoryboardService"]
