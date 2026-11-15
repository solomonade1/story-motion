"""Named motion presets -> the deterministic camera moves the renderer already supports (FR-ANIM-001).

Every pose keeps ``scale >= 1`` so the crop never leaves the picture: no black borders (QG ANIM-01).
A preset is a *move on a flat picture* (push, pull, pan, reveal). It does not animate characters.
"""

from __future__ import annotations

from typing import Any

PRESET_CAMERAS: dict[str, dict[str, Any]] = {
    "slow-push-in": {"start": {"scale": 1.0, "x": 0.5, "y": 0.5}, "end": {"scale": 1.15, "x": 0.5, "y": 0.5}, "easing": "easeInOut"},
    "slow-pull-out": {"start": {"scale": 1.15, "x": 0.5, "y": 0.5}, "end": {"scale": 1.0, "x": 0.5, "y": 0.5}, "easing": "easeInOut"},
    "pan-left": {"start": {"scale": 1.2, "x": 0.62, "y": 0.5}, "end": {"scale": 1.2, "x": 0.38, "y": 0.5}, "easing": "easeInOut"},
    "pan-right": {"start": {"scale": 1.2, "x": 0.38, "y": 0.5}, "end": {"scale": 1.2, "x": 0.62, "y": 0.5}, "easing": "easeInOut"},
    "reveal": {"start": {"scale": 1.4, "x": 0.5, "y": 0.35}, "end": {"scale": 1.0, "x": 0.5, "y": 0.5}, "easing": "easeOut"},
}
HOLD = "hold"  # no movement: a STATIC shot
DEFAULT_CINEMATIC = "slow-push-in"
KNOWN = set(PRESET_CAMERAS) | {HOLD}


def camera_for(preset: str | None) -> dict[str, Any] | None:
    """Camera dict for a CINEMATIC shot (``None`` for 'hold'). Unknown/empty presets use the default push-in."""
    if preset == HOLD:
        return None
    cam: dict[str, Any] = PRESET_CAMERAS.get(preset or "", PRESET_CAMERAS[DEFAULT_CINEMATIC])
    return cam
