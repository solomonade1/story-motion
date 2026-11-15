"""Project document schema versions and migrations (FR-PROJ-004, QG DATA-07).

A migration is a pure function dict -> dict. ``migrate`` applies them in order, never mutates its input,
and is idempotent: running it on an already-current document returns it unchanged.
"""

from __future__ import annotations

import copy
from collections.abc import Callable
from typing import Any

from .errors import SchemaTooNew

CURRENT = "1.0.0"


def _v(s: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in s.split("."))
    return a, b, c


def _0_to_1(doc: dict[str, Any]) -> dict[str, Any]:
    """Pre-release layout: ``title`` / ``created``, no video settings, no revision counter."""
    out = dict(doc)
    out["name"] = out.pop("title", out.get("name", "Untitled project"))
    out["createdAt"] = out.pop("created", out.get("createdAt", "1970-01-01T00:00:00Z"))
    out.setdefault("updatedAt", out["createdAt"])
    out.setdefault("revision", 0)
    out.setdefault("video", {"width": 1920, "height": 1080, "fps": 24})
    out.setdefault("script", "")
    out.setdefault("notes", "")
    out.setdefault("archived", False)
    out.setdefault("ext", {})
    out["schemaVersion"] = "1.0.0"
    return out


MIGRATIONS: list[tuple[str, str, Callable[[dict[str, Any]], dict[str, Any]]]] = [
    ("0.0.0", "1.0.0", _0_to_1),
]


def migrate(doc: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return (document at CURRENT, list of 'from->to' steps applied)."""
    work = copy.deepcopy(doc)
    version = str(work.get("schemaVersion", "0.0.0"))
    if _v(version)[0] > _v(CURRENT)[0]:
        raise SchemaTooNew(
            f"This project was saved by a newer StoryMotion (schema {version}); this version reads up to "
            f"{CURRENT.split('.')[0]}.x. Update the app; the project was not changed."
        )
    applied: list[str] = []
    for src, dst, fn in MIGRATIONS:
        if _v(version) < _v(dst) and _v(version) >= _v(src):
            work = fn(work)
            applied.append(f"{src}->{dst}")
            version = dst
    return work, applied
