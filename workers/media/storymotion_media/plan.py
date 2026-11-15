"""Build a manifest from a short, human-written ``plan.json`` plus the scanned drop-folder.

You say *where each shot starts in the narration* and which clip/picture it uses; durations, scene ranges,
hashes and asset ids are derived. Nothing is invented: files must exist, be decodable and be listed in the plan.

plan.json
{
  "projectId": "hezekiah-real", "title": "...",
  "video": {"fps": 24, "fadeInMs": 600, "fadeOutMs": 1500},
  "narration": "audio/narration.wav",
  "provenance": {"clips": {...}, "audio": {...}, "images": {...}, "layers": {...}},   # optional overrides
  "scenes": [{"id": "scene-1", "title": "...", "shots": [
      {"id": "s1", "startMs": 0, "clip": "clips/a.mp4", "trimStartMs": 0, "speed": 1.0,
       "transition": {"type": "crossfade", "durationMs": 500}, "action": "..."}   # RENDERED shot
      # or {"id": "s2", "startMs": 3000, "image": "images/b.jpg", "camera": {...}}  # CINEMATIC/STATIC
  ]}]
}
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .contracts import SCHEMA_VERSION, Manifest, parse_manifest
from .errors import FieldIssue, ManifestValidationError
from .scan import scan_project
from .toolchain import Toolchain


def build_manifest(tc: Toolchain, root: Path, plan: dict[str, Any]) -> Manifest:
    scan = scan_project(tc, root)
    if scan.problems:
        raise ManifestValidationError([FieldIssue("scan", p) for p in scan.problems])
    by_path = {a["path"]: a for a in scan.assets}
    issues: list[FieldIssue] = []

    def ref(rel: str, where: str) -> str:
        if rel not in by_path:
            issues.append(FieldIssue(where, f"'{rel}' was not found by the scan (is it in the right folder?)"))
            return "missing"
        return str(by_path[rel]["id"])

    narration_id = ref(plan["narration"], "narration")
    shots: list[dict[str, Any]] = []
    scenes: list[dict[str, Any]] = []
    flat = [(sc, sh) for sc in plan["scenes"] for sh in sc["shots"]]
    timing_path = root / "narration.timing.json"
    nlines = json.loads(timing_path.read_text(encoding="utf-8"))["lines"] if timing_path.exists() else []
    for _sc, sh in flat:  # "line": N  ->  the shot starts when narration line N starts
        if "line" in sh:
            n = int(sh["line"])
            if not 1 <= n <= len(nlines):
                issues.append(FieldIssue(f"{sh['id']}.line", f"line {n} is not in narration.timing.json"))
                sh["startMs"] = 0
            else:
                sh["startMs"] = 0 if n == 1 else nlines[n - 1]["speechStartMs"]
                tr = sh.get("transition", {})
                if n > 1 and tr.get("type", "cut") != "cut" and not sh.get("noLead"):
                    # start the transition early so it finishes exactly when the line begins (it plays in the pause)
                    sh["startMs"] -= int(tr["durationMs"])
    nar_ms = by_path.get(plan["narration"], {}).get("_probe", {}).get("durationMs") or 0
    for i, (sc, sh) in enumerate(flat):
        end = flat[i + 1][1]["startMs"] if i + 1 < len(flat) else nar_ms
        shot: dict[str, Any] = {
            "id": sh["id"],
            "sceneId": sc["id"],
            "startMs": sh["startMs"],
            "durationMs": end - sh["startMs"],
            "action": sh.get("action", ""),
            "mustShow": sh.get("mustShow", []),
            "avoid": sh.get("avoid", []),
            "transition": sh.get("transition", {"type": "cut", "durationMs": 0}),
            "approval": "approved",
        }
        if "clip" in sh:
            shot["mode"] = "RENDERED"
            trim = sh.get("trimStartMs", 0)
            prev = shots[-1] if shots else None
            if sh.get("continue") and prev and prev.get("rendered"):  # resume the same clip where the last shot stopped
                if by_path.get(sh["clip"], {}).get("id") != prev["rendered"]["assetId"]:
                    issues.append(FieldIssue(f"{sh['id']}.continue", "previous shot does not use the same clip"))
                trim = prev["rendered"]["trimStartMs"] + round(prev["durationMs"] * prev["rendered"]["speed"])
            speed = sh.get("speed", 1.0)
            if speed == "fit":  # slow the clip just enough to fill the shot (never faster than 1x, never below 0.6x)
                clip_ms = by_path.get(sh["clip"], {}).get("_probe", {}).get("durationMs") or 0
                need = end - sh["startMs"]
                speed = round(min(1.0, max(0.6, (clip_ms - trim) / need)), 3) if need > 0 and clip_ms else 1.0
            shot["rendered"] = {"assetId": ref(sh["clip"], f"{sh['id']}.clip"), "trimStartMs": trim, "speed": speed}
        else:
            shot["mode"] = sh.get("mode", "CINEMATIC" if "camera" in sh else "STATIC")
            shot["sourceAssetIds"] = [ref(sh["image"], f"{sh['id']}.image")]
            for k in ("camera", "layers", "effects"):
                if k in sh:
                    shot[k] = sh[k]
            for lay in shot.get("layers", []):
                lay["assetId"] = ref(lay.pop("layer"), f"{sh['id']}.layer")
        shots.append(shot)
    for sc in plan["scenes"]:
        mem = [s for s in shots if s["sceneId"] == sc["id"]]
        scenes.append(
            {
                "id": sc["id"],
                "title": sc["title"],
                "characterIds": sc.get("characterIds", []),
                "narration": {"startMs": mem[0]["startMs"], "endMs": mem[-1]["startMs"] + mem[-1]["durationMs"]},
                "shotIds": [m["id"] for m in mem],
            }
        )
    tracks = []
    for i, t in enumerate(plan.get("audioTracks", [])):
        entry = {k: v for k, v in t.items() if k != "file"}
        entry["assetId"] = ref(t["file"], f"audioTracks[{i}].file")
        tracks.append(entry)
    if issues:
        raise ManifestValidationError(issues)

    prov_over = plan.get("provenance", {})
    kind_of = {
        "environment": "images",
        "prop": "layers",
        "character": "layers",
        "audio": "audio",
        "rendered_video": "clips",
    }
    assets = []
    for a in scan.assets:
        entry = {k: v for k, v in a.items() if not k.startswith("_")}
        if kind_of[entry["type"]] in prov_over:
            entry["provenance"] = prov_over[kind_of[entry["type"]]]
        assets.append(entry)
    doc = {
        "schemaVersion": SCHEMA_VERSION,
        "projectId": plan["projectId"],
        "title": plan["title"],
        "video": {"width": 1920, "height": 1080, **plan.get("video", {"fps": 24})},
        "narration": {"assetId": narration_id, "durationMs": nar_ms},
        "audioTracks": tracks,
        "assets": assets,
        "scenes": scenes,
        "shots": shots,
    }
    return parse_manifest(json.dumps(doc))
