"""TIME-01 / FR-SCRIPT-002 / F-12: validation with field-specific diagnostics."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from storymotion_media.contracts import load_manifest, parse_manifest
from storymotion_media.errors import ManifestValidationError

FIX = Path(__file__).parents[1] / "fixtures" / "jonah" / "manifest.json"


def doc() -> dict[str, Any]:
    return copy.deepcopy(json.loads(FIX.read_text(encoding="utf-8")))


def issues(d: dict[str, Any]) -> list[str]:
    with pytest.raises(ManifestValidationError) as ei:
        parse_manifest(json.dumps(d))
    return [str(i) for i in ei.value.issues]


def test_jonah_fixture_is_valid_and_in_scope() -> None:
    m = load_manifest(FIX)
    assert 8 <= len(m.shots) <= 15  # FX-01
    assert 60_000 <= m.narration.durationMs <= 90_000
    modes = {s.mode for s in m.shots}
    assert modes == {"STATIC", "CINEMATIC", "LAYERED", "GENERATIVE"}
    assert any(s.transition.type == "crossfade" for s in m.shots)
    assert any(s.transition.type == "fadeblack" for s in m.shots)


def test_invalid_json_reports_line_and_column() -> None:
    with pytest.raises(ManifestValidationError) as ei:
        parse_manifest('{\n  "schemaVersion": "1.0.0",\n  oops }')
    assert "line 3" in str(ei.value.issues[0])


def test_negative_duration_has_field_path() -> None:
    d = doc()
    d["shots"][2]["durationMs"] = -5
    assert any(i.startswith("shots[2].durationMs") for i in issues(d))


def test_float_milliseconds_rejected() -> None:
    d = doc()
    d["shots"][0]["durationMs"] = 1000.5
    assert any("shots[0].durationMs" in i for i in issues(d))


def test_gap_and_overlap_detected_with_amounts() -> None:
    d = doc()
    d["shots"][3]["startMs"] += 40
    msgs = " ".join(issues(d))
    assert "gap of 40 ms" in msgs
    d = doc()
    d["shots"][3]["startMs"] -= 25
    assert "overlaps the previous shot by 25 ms" in " ".join(issues(d))


def test_unknown_asset_reference() -> None:
    d = doc()
    d["shots"][0]["sourceAssetIds"] = ["nope"]
    assert any("unknown asset 'nope'" in i for i in issues(d))


@pytest.mark.parametrize(
    "bad",
    [
        "../secrets.png",
        "/etc/passwd.png",
        "C:/x/y.png",
        "a\\b.png",
        "http://evil/x.png",
        "img/../../x.png",
        "ctl\x01.png",
        "x.exe",
    ],
)
def test_hostile_asset_paths_rejected(bad: str) -> None:
    d = doc()
    d["assets"][1]["path"] = bad
    assert any("assets[1]" in i for i in issues(d))


def test_generative_requires_fallback_and_generation() -> None:
    d = doc()
    shot = next(s for s in d["shots"] if s["mode"] == "GENERATIVE")
    del shot["fallbackMode"]
    assert any("fallbackMode" in i for i in issues(d))
    d = doc()
    shot = next(s for s in d["shots"] if s["mode"] == "GENERATIVE")
    del shot["generation"]
    assert any("generation" in i for i in issues(d))


def test_cinematic_requires_camera_and_no_black_border_scale() -> None:
    d = doc()
    cin = next(s for s in d["shots"] if s["mode"] == "CINEMATIC")
    cin["camera"]["start"]["scale"] = 0.9  # would reveal borders
    assert any("camera.start.scale" in i for i in issues(d))
    d = doc()
    cin = next(s for s in d["shots"] if s["mode"] == "CINEMATIC")
    del cin["camera"]
    assert any("CINEMATIC shots require 'camera'" in i for i in issues(d))


def test_secrets_or_provider_fields_cannot_enter_manifest() -> None:
    d = doc()
    shot = next(s for s in d["shots"] if s["mode"] == "GENERATIVE")
    shot["generation"]["apiKey"] = "sk-test-123"
    assert any("apiKey" in i for i in issues(d))


def test_shots_must_cover_narration_within_tolerance() -> None:
    d = doc()
    d["narration"]["durationMs"] += 400
    assert any("tolerance" in i for i in issues(d))


def test_scene_range_must_match_shots() -> None:
    d = doc()
    d["scenes"][0]["narration"]["endMs"] += 7
    assert any("does not match its shots" in i for i in issues(d))


def test_unsupported_schema_major_and_duplicates() -> None:
    d = doc()
    d["schemaVersion"] = "2.0.0"
    assert any("not supported" in i for i in issues(d))
    d = doc()
    d["shots"][1]["id"] = d["shots"][0]["id"]
    assert any("duplicate shot id" in i for i in issues(d))


def test_non_16_9_rejected_and_transition_rules() -> None:
    d = doc()
    d["video"]["height"] = 1000
    assert any("16:9" in i for i in issues(d))
    d = doc()
    d["shots"][1]["transition"] = {"type": "crossfade", "durationMs": 10}
    assert any("durationMs >= 100" in i for i in issues(d))
    d = doc()
    d["shots"][0]["transition"] = {"type": "crossfade", "durationMs": 500}
    assert any("first shot must use a 'cut'" in i for i in issues(d))


def test_narration_must_be_audio() -> None:
    d = doc()
    d["narration"]["assetId"] = "harbor-dawn"
    assert any("must reference an asset of type 'audio'" in i for i in issues(d))
