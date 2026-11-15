"""Domain errors. Every error carries an actionable message (PRD 13.2, QG OPS-10)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldIssue:
    """A validation problem with its location, e.g. ``shots[3].durationMs``."""

    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


class StoryMotionError(Exception):
    """Base class for expected, user-actionable failures."""


class ManifestValidationError(StoryMotionError):
    def __init__(self, issues: list[FieldIssue]) -> None:
        self.issues = issues
        lines = "\n".join(f"  - {i}" for i in issues)
        super().__init__(f"Manifest is invalid ({len(issues)} problem(s)):\n{lines}")


class ToolchainError(StoryMotionError):
    """FFmpeg/ffprobe missing, incompatible or failed (QG F-17)."""


class MediaError(StoryMotionError):
    """A media file is missing, corrupt or unsupported."""


class RenderError(StoryMotionError):
    """A render step failed; partial outputs were not published."""


class RenderCancelled(RenderError):
    """The user cancelled a render; temporary files were removed and nothing was published."""


class OutputValidationError(StoryMotionError):
    def __init__(self, problems: list[str]) -> None:
        self.problems = problems
        super().__init__("Rendered output failed validation:\n" + "\n".join(f"  - {p}" for p in problems))
