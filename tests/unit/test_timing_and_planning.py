"""Narration-as-clock timing maths and GENERATIVE fallback planning (ANIM-03, ANIM-04)."""

from __future__ import annotations

from pathlib import Path

import pytest

from storymotion_media.contracts import load_manifest
from storymotion_media.render import frame_edges, ms_to_frame, plan_shots

FIX = Path(__file__).parents[1] / "fixtures" / "jonah" / "manifest.json"


@pytest.mark.parametrize(
    ("ms", "fps", "frame"),
    [(0, 24, 0), (41, 24, 1), (20, 24, 0), (21, 24, 1), (1000, 24, 24), (1000, 30, 30), (85606, 24, 2055)],
)
def test_ms_to_frame_integer_rounding(ms: int, fps: int, frame: int) -> None:
    assert ms_to_frame(ms, fps) == frame


@pytest.mark.parametrize("fps", [24, 30])
def test_frame_edges_are_contiguous_and_within_half_frame(fps: int) -> None:
    m = load_manifest(FIX)
    edges = frame_edges(list(m.shots), fps)
    assert edges[0] == 0 and all(b > a for a, b in zip(edges, edges[1:], strict=False))
    half_frame_ms = 500 / fps
    for s, e in zip(m.shots, edges, strict=False):
        assert abs(e * 1000 / fps - s.startMs) <= half_frame_ms + 1e-9


def test_plan_without_clip_falls_back_and_never_stays_generative() -> None:
    m = load_manifest(FIX)
    plans = plan_shots(m, 24)
    gen = [p for p in plans if p.shot.mode == "GENERATIVE"]
    assert len(gen) == 2
    for p in gen:
        assert p.effective_mode == "CINEMATIC"
        assert p.fallback_reason == "no generated clip attached"


def test_tails_only_where_next_shot_has_a_fade() -> None:
    m = load_manifest(FIX)
    plans = plan_shots(m, 24)
    for cur, nxt in zip(plans, plans[1:], strict=False):
        assert (cur.tail_frames > 0) == (nxt.shot.transition.type != "cut")
    assert plans[-1].tail_frames == 0
