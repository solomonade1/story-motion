"""Storyboard model, script import and timing diagnostics (TIME-01, TIME-02, TIME-03 gap/overlap reporting)."""

from __future__ import annotations

import json
from typing import Any

import pytest

from storymotion_media.errors import ManifestValidationError
from storymotion_media.studio.storyboard import (
    Storyboard,
    blocking,
    diagnose,
    import_script,
    parse_plan_text,
    parse_storyboard,
)

IMG = "a-000000000001"
IMG2 = "a-000000000002"
NAR = "a-0000000000aa"
LIB: dict[str, dict[str, Any]] = {
    IMG: {"kind": "image", "status": "ok"},
    IMG2: {"kind": "image", "status": "ok"},
    NAR: {"kind": "audio", "status": "ok"},
}


def shot(i: str, start: int, dur: int, **kw: Any) -> dict[str, Any]:
    return {"id": i, "startMs": start, "durationMs": dur, "mode": "STATIC", "imageAssetId": IMG, **kw}


def sb(*shots: dict[str, Any], characters: list[dict[str, str]] | None = None, nar: str | None = NAR) -> Storyboard:
    return parse_storyboard(
        {
            "narrationAssetId": nar,
            "characters": characters or [],
            "scenes": [{"id": "s1", "title": "One", "shots": list(shots)}],
        }
    )


def codes(d: list[dict[str, Any]]) -> list[str]:
    return [x["code"] for x in d]


# ---------------------------------------------------------------- structure errors (refused, field-located)
@pytest.mark.parametrize(
    ("patch", "where"),
    [
        ({"startMs": -1}, "scenes[0].shots[0].startMs"),
        ({"durationMs": 0}, "scenes[0].shots[0].durationMs"),
        ({"durationMs": -500}, "scenes[0].shots[0].durationMs"),
        ({"durationMs": 1500.5}, "scenes[0].shots[0].durationMs"),
        ({"startMs": "0"}, "scenes[0].shots[0].startMs"),
        ({"mode": "TELEPORT"}, "scenes[0].shots[0].mode"),
        ({"imageAssetId": "../../etc/passwd"}, "scenes[0].shots[0].imageAssetId"),
        ({"id": "Has Space"}, "scenes[0].shots[0].id"),
    ],
)
def test_bad_shot_fields_are_located(patch: dict[str, Any], where: str) -> None:
    with pytest.raises(ManifestValidationError) as ei:
        sb(shot("x", 0, 1000, **patch))
    assert where in [i.path for i in ei.value.issues]


def test_unknown_fields_duplicate_ids_and_unknown_characters_are_refused() -> None:
    with pytest.raises(ManifestValidationError) as ei:
        sb(shot("x", 0, 1000, surprise=1))
    assert any("surprise" in i.path for i in ei.value.issues)
    with pytest.raises(ManifestValidationError, match="duplicate id x"):
        sb(shot("x", 0, 1000), shot("x", 1000, 1000))
    with pytest.raises(ManifestValidationError) as ei2:
        sb(shot("x", 0, 1000, characterIds=["jonah"]))
    assert "unknown character 'jonah'" in str(ei2.value)


def test_newer_storyboard_major_is_refused() -> None:
    with pytest.raises(ManifestValidationError, match="not supported"):
        parse_storyboard({"storyboardVersion": "2.0.0"})


# ---------------------------------------------------------------- plan JSON import (TIME-01 invalid JSON)
def test_plan_with_invalid_json_reports_line_and_column() -> None:
    with pytest.raises(ManifestValidationError) as ei:
        parse_plan_text('{\n  "scenes": [\n    {"id": "s1",,}\n  ]\n}')
    assert ei.value.issues[0].path.startswith("line 3, column")
    with pytest.raises(ManifestValidationError, match="must be a JSON object"):
        parse_plan_text("[1, 2]")


def test_valid_plan_round_trips_unchanged() -> None:
    plan = {
        "storyboardVersion": "1.0.0",
        "narrationAssetId": NAR,
        "characters": [{"id": "jonah", "name": "Jonah"}],
        "scenes": [
            {
                "id": "s1",
                "title": "The call",
                "text": "God spoke to Jonah.",
                "characterIds": ["jonah"],
                "shots": [shot("a", 0, 4000, characterIds=["jonah"], action="Jonah listens", mustShow=["Jonah"], avoid=["fish"])],
            }
        ],
    }
    parsed = parse_plan_text(json.dumps(plan))
    again = parse_plan_text(json.dumps(parsed.model_dump()))
    assert again == parsed
    assert parsed.scenes[0].shots[0].avoid == ["fish"] and parsed.scenes[0].shots[0].preset is None


# ---------------------------------------------------------------- script import (TIME-01 valid import editable)
def test_markdown_headings_become_scenes() -> None:
    text = "# The call\nGod spoke to Jonah.\nGo to Nineveh.\n\n## The storm\nA great wind rose.\n"
    scenes = import_script(text, filename="jonah.md").scenes
    assert [s.title for s in scenes] == ["The call", "The storm"]
    assert scenes[0].text == "God spoke to Jonah. Go to Nineveh."
    assert [s.id for s in scenes] == ["scene-1", "scene-2"] and all(not s.shots for s in scenes)


def test_plain_text_paragraphs_become_scenes_and_crlf_is_handled() -> None:
    scenes = import_script("First part.\r\nStill first.\r\n\r\n\r\nSecond part.", filename="a.txt").scenes
    assert [s.text for s in scenes] == ["First part. Still first.", "Second part."]
    assert [s.title for s in scenes] == ["Scene 1", "Scene 2"]


def test_plain_text_without_blank_lines_is_one_scene_per_line() -> None:
    scenes = import_script("Hezekiah was dying.\nScripture does not.\n\n").scenes  # the owner's real script style
    assert [s.text for s in scenes] == ["Hezekiah was dying.", "Scripture does not."]
    assert len(import_script("Just one line.").scenes) == 1


def test_script_import_rejects_empty_and_strips_control_characters() -> None:
    for bad in ("", "   \n\n  ", 5):
        with pytest.raises(ManifestValidationError):
            import_script(bad)  # type: ignore[arg-type]
    only = import_script("Hello\x00 world\x07.")
    assert only.scenes[0].text == "Hello world."


def test_imported_script_is_editable_and_saves_as_a_valid_storyboard() -> None:
    imp = import_script("# A\nText.")
    assert parse_storyboard(imp.model_dump()) == imp


# ---------------------------------------------------------------- diagnostics (never silently repaired)
def test_clean_timeline_has_no_blocking_diagnostics() -> None:
    d = diagnose(sb(shot("a", 0, 5000), shot("b", 5000, 5000, imageAssetId=IMG2)), narration_ms=10000, assets=LIB)
    assert d == []


def test_gap_and_overlap_are_reported_with_exact_amounts() -> None:
    d = diagnose(sb(shot("a", 0, 4000), shot("b", 4500, 2000), shot("c", 6000, 2000)), narration_ms=8000, assets=LIB)
    msgs = {x["code"]: x["message"] for x in d}
    assert "Gap of 500 ms" in msgs["gap"] and "expected start 4000" in msgs["gap"]
    assert "Overlaps the previous shot by 500 ms" in msgs["overlap"]
    assert not blocking(d)  # saved and flagged, not refused


def test_timeline_must_not_run_past_or_stop_short_of_the_narration() -> None:
    assert codes(diagnose(sb(shot("a", 0, 12000)), narration_ms=10000, assets=LIB)) == ["past-narration"]
    assert codes(diagnose(sb(shot("a", 0, 6000)), narration_ms=10000, assets=LIB)) == ["short-of-narration"]
    assert diagnose(sb(shot("a", 0, 10200)), narration_ms=10000, assets=LIB) == []  # within the 250 ms tolerance
    d = diagnose(sb(shot("a", 0, 5000), shot("b", 10000, 1000)), narration_ms=10000, assets=LIB)
    assert "after-narration" in codes(d) and blocking(d)
    assert "late-start" in codes(diagnose(sb(shot("a", 300, 9700)), narration_ms=10000, assets=LIB))


def test_missing_wrong_type_and_unavailable_assets_are_flagged_per_shot() -> None:
    lib = {**LIB, IMG2: {"kind": "image", "status": "missing"}, "a-000000000003": {"kind": "audio", "status": "ok"}}
    d = diagnose(
        sb(
            shot("a", 0, 1000, imageAssetId="a-0000000000ff"),
            shot("b", 1000, 1000, imageAssetId="a-000000000003"),
            shot("c", 2000, 1000, imageAssetId=IMG2),
            shot("d", 3000, 1000, imageAssetId=None),
        ),
        narration_ms=4000,
        assets=lib,
    )
    assert [x["code"] for x in d] == ["image-missing", "image-not-image", "image-unavailable", "no-image"]
    assert [x["shotId"] for x in d] == ["a", "b", "c", "d"]


def test_narration_problems_and_empty_states() -> None:
    assert codes(diagnose(sb(shot("a", 0, 1000), nar=None), narration_ms=None, assets=LIB)) == ["no-narration"]
    assert "narration-not-audio" in codes(diagnose(sb(shot("a", 0, 1000), nar=IMG), narration_ms=None, assets=LIB))
    assert "narration-missing" in codes(diagnose(sb(shot("a", 0, 1000), nar="a-0000000000ee"), narration_ms=None, assets=LIB))
    only_scene = parse_storyboard({"scenes": [{"id": "s1", "title": "Empty"}]})
    assert codes(diagnose(only_scene, narration_ms=None, assets=LIB)) == ["no-narration", "no-shots"]


def test_generative_is_flagged_as_unavailable_not_silently_accepted() -> None:
    d = diagnose(sb(shot("a", 0, 1000, mode="GENERATIVE")), narration_ms=1000, assets=LIB)
    assert codes(d) == ["generative-unavailable"] and "local fallback" in d[0]["message"]
