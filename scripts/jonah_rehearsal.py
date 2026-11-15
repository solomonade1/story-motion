"""PLACEHOLDER REHEARSAL of the Jonah production: proves the Studio handles a 3-5 minute, 20+ picture episode.

  python scripts/jonah_rehearsal.py [--out out/rehearsal] [--voice tools/piper-voices/en_US-joe-medium.onnx]

It makes 24 clearly labelled procedural pictures, narrates an ORIGINAL 30-line retelling with a local Piper voice,
builds the storyboard through the Studio's own HTTP API (as the UI does), renders a draft and a final, measures
cut timing (TIME-04), closes and reopens the workspace, and edits one shot to prove the others are untouched.

This is NOT G2 evidence: the pictures are not creator art, nobody judged the result, and no creator time was logged.
It exists to find scale problems before the real assets arrive. Everything is offline: a guard raises if any
Python code in this process opens a non-loopback network connection.
"""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "workers" / "media"))

from storymotion_media.studio.api import ApiServer  # noqa: E402
from storymotion_media.studio.store import Workspace  # noqa: E402
from storymotion_media.timing_check import check_render, draft_vs_final  # noqa: E402
from storymotion_media.toolchain import get_toolchain  # noqa: E402

SCRIPT = """\
Long ago, the word of the Lord came to a prophet named Jonah.
Go to Nineveh, the great city, and warn its people, for their wickedness has risen before me.
But Jonah got up and went the other way, down to the harbour at Joppa.
He found a ship bound for Tarshish, paid the fare, and went below deck, far from the Lord's call.
Then the Lord sent a great wind upon the sea, and the ship threatened to break apart.
The sailors were afraid, and each one cried out to his own god.
They threw the cargo into the sea to lighten the ship.
All this time, Jonah was fast asleep in the hold.
The captain found him and said, how can you sleep? Get up and call on your God.
The sailors cast lots to learn who had brought this trouble upon them, and the lot fell on Jonah.
Tell us, they said, who are you, and where do you come from?
I am a Hebrew, he answered, and I worship the Lord, who made the sea and the dry land.
The men were terrified, for Jonah had told them he was running away from the Lord.
What should we do to you to make the sea calm for us? they asked.
Pick me up and throw me into the sea, he said, and it will become calm.
Still the men rowed hard to get back to land, but they could not, for the storm grew wilder.
At last they cried to the Lord, and then they took Jonah and threw him overboard.
At once the raging sea grew calm, and the men were filled with awe.
Now the Lord provided a great fish to swallow Jonah, and he was inside it three days and three nights.
From inside the fish Jonah prayed, and said, in my distress I called, and you answered me.
Then the Lord commanded the fish, and it vomited Jonah onto dry land.
The word of the Lord came to Jonah a second time: go to Nineveh and proclaim what I tell you.
This time Jonah obeyed, and he began to walk through the city, a day's journey in.
Forty more days, and Nineveh will be overthrown, he called out.
The people of Nineveh believed God, and from the greatest to the least they put on sackcloth.
When the king heard, he rose from his throne, and called everyone to turn from their evil ways.
God saw what they did, and he had compassion, and did not bring the destruction he had threatened.
But Jonah was greatly displeased, and he went out and sat east of the city to see what would happen.
The Lord made a vine grow over him for shade, and Jonah was very happy about the vine.
Should I not be concerned about that great city? the Lord asked, a city of more than a hundred and twenty thousand people.
""".strip().split("\n")

_real_connect = socket.socket.connect


def _offline_guard(self: socket.socket, address: Any) -> Any:
    host = address[0] if isinstance(address, tuple) else str(address)
    if host not in ("127.0.0.1", "::1", "localhost"):
        raise RuntimeError(f"OFFLINE GUARD: blocked a connection to {address!r}")
    return _real_connect(self, address)


def placeholder_image(path: Path, n: int, total: int, caption: str) -> None:
    w, h = 1920, 1080
    img = Image.new("RGB", (w, h))
    px = img.load()
    assert px is not None
    hue = (n * 47) % 255
    for y in range(0, h, 4):  # cheap vertical gradient, distinct per picture
        c = (40 + hue // 2 + y // 30, 60 + (hue * 3) % 120 + y // 40, 90 + (255 - hue) // 2)
        for x in range(0, w, 4):
            col = (min(255, c[0] + x // 40), min(255, c[1]), min(255, c[2]))
            for dy in range(4):
                for dx in range(4):
                    px[x + dx, y + dy] = col
    d = ImageDraw.Draw(img)
    try:
        big, small = ImageFont.truetype("arial.ttf", 120), ImageFont.truetype("arial.ttf", 44)
    except OSError:
        big = small = ImageFont.load_default()
    d.text((120, 300), f"PLACEHOLDER {n}/{total}", fill=(255, 255, 255), font=big)
    d.text((120, 480), "procedural test picture, not creator art", fill=(255, 235, 150), font=small)
    d.text((120, 560), caption[:80], fill=(255, 255, 255), font=small)
    d.ellipse([w - 520 - n * 8, 200, w - 120, 600], outline=(255, 255, 255), width=10)  # something to move in a push/pan
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=92)


class Studio:
    def __init__(self, ws_dir: Path) -> None:
        self.srv = ApiServer(Workspace(ws_dir), static_dir=None)
        self.srv.start_background()

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.srv.port}{path}", method=method, data=json.dumps(body).encode() if body is not None else None,
            headers={"Authorization": f"Bearer {self.srv.token}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=600) as r:  # noqa: S310 - loopback URL built above
                return r.status, json.loads(r.read() or b"null")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"null")

    def wait(self, pid: str, jid: str) -> dict[str, Any]:
        while True:
            _, j = self.call("GET", f"/api/projects/{pid}/jobs/{jid}")
            if j["state"] in ("completed", "failed", "cancelled", "interrupted"):
                return j  # type: ignore[no-any-return]
            time.sleep(0.5)

    def close(self) -> None:
        self.srv.shutdown()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "out" / "rehearsal")
    ap.add_argument("--voice", type=Path, default=ROOT / "tools" / "piper-voices" / "en_US-joe-medium.onnx")
    a = ap.parse_args()
    out: Path = a.out.resolve()
    src, ws_dir = out / "src", out / "workspace"
    for d in (src / "images", src / "audio"):
        d.mkdir(parents=True, exist_ok=True)
    tc = get_toolchain()
    log: dict[str, Any] = {"label": "PLACEHOLDER REHEARSAL - not G2 evidence", "toolchain": tc.version, "steps": {}}
    t_all = time.perf_counter()

    def step(name: str, t0: float) -> None:
        log["steps"][name] = round(time.perf_counter() - t0, 1)
        print(f"{name}: {log['steps'][name]} s", flush=True)

    # ---- material
    t0 = time.perf_counter()
    (src / "script.txt").write_text("\n".join(SCRIPT) + "\n", encoding="utf-8")
    n_img = 24
    for i in range(n_img):
        placeholder_image(src / "images" / f"placeholder-{i + 1:02d}.jpg", i + 1, n_img, SCRIPT[i % len(SCRIPT)])
    step("make_pictures", t0)
    t0 = time.perf_counter()
    voice = [sys.executable, str(ROOT / "scripts" / "make_narration.py"), str(src), "--engine", "piper", "--model", str(a.voice), "--length-scale", "1.35"]
    subprocess.run(voice, check=True, capture_output=True)  # noqa: S603
    subprocess.run([sys.executable, str(ROOT / "scripts" / "make_ambience.py"), str(src)], check=True, capture_output=True)  # noqa: S603
    step("make_narration_and_bed", t0)
    timing = json.loads((src / "narration.timing.json").read_text(encoding="utf-8"))
    lines = timing["lines"]

    # ---- Studio, offline
    socket.socket.connect = _offline_guard  # type: ignore[method-assign]
    if ws_dir.exists():
        import shutil

        shutil.rmtree(ws_dir)
    s = Studio(ws_dir)
    t0 = time.perf_counter()
    st, doc = s.call("POST", "/api/projects", {"name": "Jonah rehearsal (placeholder)"})
    pid = doc["projectId"]
    files = [str(p) for p in sorted((src / "images").glob("*.jpg"))] + [str(src / "audio" / "narration.wav"), str(src / "audio" / "ambience.wav")]
    job = s.wait(pid, s.call("POST", f"/api/projects/{pid}/assets/import", {"paths": files, "mode": "copy"})[1]["id"])
    assert job["state"] == "completed" and not job["result"]["errors"], job
    step("studio_import_26_files", t0)
    assets = s.call("GET", f"/api/projects/{pid}/assets")[1]["assets"]
    imgs = [x["id"] for x in sorted((x for x in assets if x["kind"] == "image"), key=lambda x: x["orig_name"])]
    nar = next(x for x in assets if x["orig_name"] == "narration.wav")
    bed = next(x for x in assets if x["orig_name"] == "ambience.wav")
    log["counts"] = {"pictures": len(imgs), "narrationSeconds": round(nar["duration_ms"] / 1000, 1), "shots": len(lines)}

    _, view = s.call("POST", f"/api/projects/{pid}/storyboard/import-script", {"text": "\n".join(SCRIPT), "filename": "script.txt"})
    sb = view["storyboard"]
    assert len(sb["scenes"]) == len(lines)
    sb |= {"narrationAssetId": nar["id"], "fadeInMs": 600, "fadeOutMs": 1500,
           "audioTracks": [{"assetId": bed["id"], "role": "ambience", "gainDb": 4.0, "fadeInMs": 1500, "fadeOutMs": 3000, "loop": True, "duckDb": 9.0}]}
    presets = ["slow-push-in", "slow-pull-out", "pan-left", "pan-right", "reveal"]
    starts: list[int] = []
    for k, ln in enumerate(lines):
        cut = k % 4 == 0  # every 4th shot is a hard cut (measurable by TIME-04); the rest dissolve in the pause
        starts.append(0 if k == 0 else ln["speechStartMs"] - (0 if cut else 500))
    for k, sc in enumerate(sb["scenes"]):
        end = starts[k + 1] if k + 1 < len(starts) else nar["duration_ms"]
        static = k % 3 == 0
        sc["shots"] = [{
            "id": f"shot-{k + 1}", "startMs": starts[k], "durationMs": end - starts[k], "mode": "STATIC" if static else "CINEMATIC",
            "imageAssetId": imgs[k % len(imgs)], "preset": None if static else presets[k % len(presets)],
            "transition": {"type": "cut", "durationMs": 0} if k % 4 == 0 else {"type": "crossfade", "durationMs": 500},
            "action": SCRIPT[k][:100], "mustShow": [], "avoid": [], "characterIds": [],
        }]
    st, saved = s.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": sb})
    assert st == 200, saved
    problems = [d for d in saved["diagnostics"] if d["severity"] != "info"]
    log["storyboardProblems"] = problems
    print("storyboard saved;", len(problems), "problems", flush=True)

    # ---- render + TIME-04
    mp4s: dict[str, Path] = {}
    for label, draft in (("draft", True), ("final", False)):
        t0 = time.perf_counter()
        st, j = s.call("POST", f"/api/projects/{pid}/storyboard/render", {"draft": draft})
        assert st == 202, j
        done = s.wait(pid, j["id"])
        assert done["state"] == "completed", done
        r = done["result"]
        mp4s[label] = s.srv.ws.project(pid).dir / "renders" / r["file"]
        step(f"render_{label}", t0)
        log[label] = {k: r[k] for k in ("file", "width", "height", "fps", "frames", "sizeBytes", "sha256")} | {"warnings": r["warnings"]}
    t0 = time.perf_counter()
    timing_res = {k: check_render(tc, p, p.with_suffix(".json")) for k, p in mp4s.items()}
    step("timing_check", t0)
    log["time04"] = {k: {x: v[x] for x in ("hardCutsExpected", "measured", "medianAbsDeviationFrames", "maxAbsDeviationFrames", "withinTime04")}
                     for k, v in timing_res.items()} | {"draftVsFinal": draft_vs_final(timing_res["draft"], timing_res["final"])}

    # ---- close / reopen / edit preservation
    before = s.call("GET", f"/api/projects/{pid}/storyboard")[1]
    s.close()
    s = Studio(ws_dir)
    after = s.call("GET", f"/api/projects/{pid}/storyboard")[1]
    log["reopenIdentical"] = before["storyboard"] == after["storyboard"] and before["diagnostics"] == after["diagnostics"]
    chk = s.wait(pid, s.call("POST", f"/api/projects/{pid}/assets/check", {"verifyHash": True})[1]["id"])
    log["assetsAfterReopen"] = chk["result"]["counts"]
    edited = json.loads(json.dumps(after["storyboard"]))
    edited["scenes"][9]["shots"][0]["preset"] = "pan-right"
    edited["scenes"][9]["shots"][0]["mode"] = "CINEMATIC"
    st, _v = s.call("PUT", f"/api/projects/{pid}/storyboard", {"storyboard": edited})
    changed = [i for i, (x, y) in enumerate(zip(after["storyboard"]["scenes"], edited["scenes"], strict=True)) if x != y]
    log["editTouchedOnlyShot"] = changed
    renders = s.call("GET", f"/api/projects/{pid}/renders")[1]["renders"]
    log["previousRendersKeptAfterEdit"] = len(renders)
    s.close()
    socket.socket.connect = _real_connect  # type: ignore[method-assign]
    log["offlineGuard"] = "no non-loopback connection was attempted by this Python process (FFmpeg runs as a separate process and was not instrumented)"
    log["totalSeconds"] = round(time.perf_counter() - t_all, 1)
    (out / "rehearsal_report.json").write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: log[k] for k in ("counts", "time04", "reopenIdentical", "assetsAfterReopen", "editTouchedOnlyShot", "totalSeconds")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
