"""Generate the Phase 0 development fixtures (FX-01): PLACEHOLDER art + synthetic narration.

Everything here is a development stand-in. It is NOT final Jonah character art and does NOT
validate creative quality (G1 creative check stays pending until creator-supplied assets are used).

Run (Windows, needs the SAPI voice):  python scripts/make_fixtures.py
Outputs are committed under tests/fixtures/jonah so tests do not need to regenerate them.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "jonah"
IMG_DIR = OUT / "assets" / "images"
LAYER_DIR = OUT / "assets" / "layers"
AUDIO_DIR = OUT / "assets" / "audio"
W, H = 2560, 1440
LEAD_MS, GAP_MS, TAIL_MS = 600, 500, 1600

# Original paraphrase of the Book of Jonah (author-written for this fixture; not a translation).
LINES = [
    "Long ago, God told a prophet named Jonah to go to the great city of Nineveh and warn its people.",
    "But Jonah was afraid, and he ran the other way. He boarded a ship sailing far across the sea.",
    "Then God sent a mighty storm. The waves crashed, the wind roared, and the ship was ready to break apart.",
    "The frightened sailors cried out, and threw their cargo overboard to lighten the ship.",
    "Down below, Jonah was fast asleep, until the captain woke him and begged him to pray.",
    "The sailors cast lots to learn who had brought this trouble upon them, and the lot fell on Jonah.",
    "Jonah said, throw me into the sea, and the storm will stop. So, with great sorrow, they lifted him up and let him go.",
    "At once the sea became calm, and the sailors were amazed.",
    "But God had prepared a great fish, which rose from the deep and swallowed Jonah whole.",
    "Inside the fish, in the dark, Jonah stayed for three days and three nights.",
    "There he prayed, and he thanked God for hearing him, even from so deep a place.",
    "Then God spoke to the fish, and it carried Jonah safely to dry land. Now, Jonah was ready to obey.",
]

FONT = ImageFont.load_default(size=26)


# ------------------------------------------------------------------ drawing helpers
def vgrad(img: Image.Image, top: tuple[int, int, int], bot: tuple[int, int, int], y0: int = 0, y1: int = H) -> None:
    d = ImageDraw.Draw(img)
    for y in range(y0, y1):
        t = (y - y0) / max(1, y1 - y0 - 1)
        d.line([(0, y), (W, y)], fill=tuple(round(a + (b - a) * t) for a, b in zip(top, bot, strict=True)))


def wave_band(img: Image.Image, base: int, amp: int, wl: int, color: tuple[int, int, int], phase: float = 0.0) -> None:
    d = ImageDraw.Draw(img)
    pts = [(x, base + amp * math.sin((x / wl) * 2 * math.pi + phase)) for x in range(0, W + 16, 16)]
    d.polygon([*pts, (W, H), (0, H)], fill=color)


def glow(img: Image.Image, cx: int, cy: int, r: int, color: tuple[int, int, int], strength: float) -> None:
    mask = Image.radial_gradient("L").resize((2 * r, 2 * r))
    mask = mask.point(lambda v: int((255 - v) * strength))
    img.paste(Image.new("RGB", (2 * r, 2 * r), color), (cx - r, cy - r), mask)


def person(d: ImageDraw.ImageDraw, x: int, y: int, h: int, color: tuple[int, int, int], arms_up: bool = False) -> None:
    """Simple silhouette; (x, y) is the foot position."""
    head = h // 7
    d.ellipse([x - head, y - h, x + head, y - h + 2 * head], fill=color)
    d.polygon(
        [
            (x - head, y - h + 2 * head),
            (x + head, y - h + 2 * head),
            (x + int(head * 1.4), y - h // 3),
            (x - int(head * 1.4), y - h // 3),
        ],
        fill=color,
    )
    d.rectangle([x - head, y - h // 3, x + head, y], fill=color)
    if arms_up:
        d.line([(x - head, y - h + 3 * head), (x - 2 * head, y - h + head)], fill=color, width=head // 2)
        d.line([(x + head, y - h + 3 * head), (x + 2 * head, y - h + head)], fill=color, width=head // 2)


def ship(img: Image.Image, cx: int, base: int, scale: float, hull=(70, 45, 30), sail=(235, 225, 200)) -> None:
    d = ImageDraw.Draw(img)
    s = scale
    d.polygon(
        [(cx - 300 * s, base - 120 * s), (cx + 320 * s, base - 120 * s), (cx + 220 * s, base), (cx - 220 * s, base)],
        fill=hull,
    )
    d.rectangle([cx - 8 * s, base - 520 * s, cx + 8 * s, base - 120 * s], fill=(55, 35, 25))
    d.polygon([(cx + 14 * s, base - 500 * s), (cx + 230 * s, base - 200 * s), (cx + 14 * s, base - 190 * s)], fill=sail)
    d.polygon(
        [(cx - 14 * s, base - 460 * s), (cx - 190 * s, base - 200 * s), (cx - 14 * s, base - 190 * s)],
        fill=tuple(max(0, c - 25) for c in sail),
    )


def tag(img: Image.Image, name: str) -> Image.Image:
    d = ImageDraw.Draw(img)
    d.rectangle([20, H - 62, 760, H - 20], fill=(0, 0, 0))
    d.text((32, H - 54), f"PLACEHOLDER ART - not final - {name}", fill=(255, 220, 80), font=FONT)
    return img


# ------------------------------------------------------------------ scenes
def harbor_dawn() -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (250, 160, 110), (255, 225, 170), 0, 900)
    glow(img, 1500, 880, 520, (255, 235, 180), 0.9)
    d = ImageDraw.Draw(img)
    d.ellipse([1400, 780, 1600, 980], fill=(255, 245, 210))
    vgrad(img, (120, 140, 160), (40, 70, 100), 900, H)
    rnd = random.Random(1)
    x = 0
    while x < W:  # distant city skyline (Joppa-style silhouette)
        wd, ht = rnd.randint(60, 150), rnd.randint(90, 300)
        d.rectangle([x, 900 - ht, x + wd, 900], fill=(60, 45, 50))
        x += wd + rnd.randint(0, 10)
    wave_band(img, 1050, 14, 220, (50, 85, 115))
    wave_band(img, 1200, 20, 300, (35, 65, 95), 1.0)
    ship(img, 600, 1130, 0.5)
    return tag(img, "harbor_dawn")


def sea_day(calm: bool = False) -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (110, 170, 230), (210, 235, 250), 0, 800)
    glow(img, 400, 260, 420, (255, 250, 220), 0.8)
    vgrad(img, (70, 140, 190), (20, 70, 120), 800, H)
    amp = 8 if calm else 26
    for i, (b, c) in enumerate([(830, (60, 130, 180)), (980, (40, 105, 160)), (1160, (25, 80, 135))]):
        wave_band(img, b, amp + i * 4, 260 + i * 60, c, i)
    return tag(img, "sea_calm" if calm else "sea_day")


def storm_sea() -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (25, 30, 45), (80, 90, 105), 0, 760)
    d = ImageDraw.Draw(img)
    rnd = random.Random(7)
    for _ in range(40):
        cx, cy = rnd.randint(0, W), rnd.randint(40, 520)
        rx, ry = rnd.randint(200, 520), rnd.randint(50, 130)
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(45, 50, 62))
    vgrad(img, (35, 60, 80), (10, 25, 40), 760, H)
    for i, (b, c) in enumerate([(780, (40, 70, 92)), (930, (28, 55, 78)), (1110, (16, 36, 58))]):
        wave_band(img, b, 70 + 20 * i, 380 + 40 * i, c, 1.7 * i)
    for _ in range(260):  # rain
        x, y = rnd.randint(0, W), rnd.randint(0, H)
        d.line([(x, y), (x - 30, y + 90)], fill=(150, 165, 185), width=2)
    return tag(img, "storm_sea")


def ship_deck() -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (35, 42, 58), (95, 105, 120), 0, 560)
    vgrad(img, (25, 45, 65), (15, 30, 48), 560, 700)
    d = ImageDraw.Draw(img)
    vgrad(img, (120, 85, 55), (70, 45, 30), 700, H)
    for x in range(-200, W + 200, 160):  # planks
        d.line([(x + (x - W // 2) // 6, 700), (x * 1.5 - W // 4, H)], fill=(55, 35, 25), width=4)
    d.rectangle([0, 640, W, 700], fill=(95, 65, 40))  # rail
    for x in range(40, W, 220):
        d.rectangle([x, 640, x + 26, 760], fill=(85, 55, 35))
    d.rectangle([W // 2 - 26, 40, W // 2 + 26, 700], fill=(60, 40, 28))  # mast
    for x, hgt, up in [(520, 520, True), (700, 480, False), (1700, 500, True), (1900, 470, False)]:
        person(d, x, 1100, hgt, (28, 22, 24), arms_up=up)
    person(d, 1220, 1180, 560, (110, 60, 50))  # Jonah (reddish silhouette)
    return tag(img, "ship_deck")


def below_deck() -> Image.Image:
    img = Image.new("RGB", (W, H), (28, 20, 16))
    vgrad(img, (45, 30, 22), (20, 14, 12), 0, H)
    d = ImageDraw.Draw(img)
    for x in range(0, W, 180):
        d.line([(x, 0), (x, H)], fill=(35, 24, 18), width=5)
    glow(img, 1900, 520, 700, (255, 170, 70), 0.85)
    d.ellipse([1860, 480, 1940, 560], fill=(255, 215, 130))
    d.ellipse([900, 1000, 1500, 1260], fill=(110, 60, 50))  # curled sleeping figure
    d.ellipse([1420, 1020, 1560, 1160], fill=(130, 80, 65))
    return tag(img, "below_deck")


def deck_group() -> Image.Image:
    img = ship_deck()
    d = ImageDraw.Draw(img)
    d.rectangle([0, 700, W, H], fill=(80, 52, 34))
    for i, x in enumerate(range(300, 2300, 330)):
        person(d, x, 1250 - (i % 2) * 40, 640 + (i % 3) * 30, (26, 20, 22), arms_up=i % 2 == 0)
    return tag(img, "deck_group")


def underwater() -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (30, 110, 140), (6, 22, 48), 0, H)
    d = ImageDraw.Draw(img, "RGBA")
    for x in range(-200, W, 300):
        d.polygon([(x, 0), (x + 160, 0), (x + 560, H), (x + 140, H)], fill=(180, 230, 240, 28))
    rnd = random.Random(3)
    for _ in range(70):
        x, y, r = rnd.randint(0, W), rnd.randint(0, H), rnd.randint(6, 26)
        d.ellipse([x - r, y - r, x + r, y + r], outline=(200, 235, 245, 120), width=3)
    return tag(img, "underwater")


def inside_fish() -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (70, 28, 30), (22, 8, 12), 0, H)
    d = ImageDraw.Draw(img)
    for i in range(9):
        x = 150 + i * 260
        d.arc([x - 420, -300, x + 420, H + 300], 100, 260, fill=(120, 70, 60), width=18)
    glow(img, W // 2, 900, 800, (255, 190, 120), 0.35)
    person(d, W // 2, 1180, 420, (20, 12, 14))
    return tag(img, "inside_fish")


def prayer() -> Image.Image:
    img = Image.new("RGB", (W, H), (8, 6, 10))
    d = ImageDraw.Draw(img, "RGBA")
    d.polygon([(1100, 0), (1500, 0), (1750, H), (850, H)], fill=(255, 235, 170, 60))
    glow(img, W // 2, H - 220, 700, (255, 220, 150), 0.5)
    d = ImageDraw.Draw(img)
    d.ellipse([W // 2 - 70, 880, W // 2 + 70, 1020], fill=(12, 8, 12))
    d.polygon(
        [(W // 2 - 110, 1020), (W // 2 + 110, 1020), (W // 2 + 170, 1250), (W // 2 - 170, 1250)], fill=(12, 8, 12)
    )
    return tag(img, "prayer")


def shore() -> Image.Image:
    img = Image.new("RGB", (W, H))
    vgrad(img, (255, 190, 130), (255, 235, 190), 0, 760)
    glow(img, 1900, 700, 600, (255, 245, 210), 0.8)
    vgrad(img, (70, 130, 170), (40, 95, 140), 760, 980)
    wave_band(img, 960, 18, 260, (225, 235, 235))
    vgrad(img, (225, 195, 140), (190, 155, 100), 1000, H)
    d = ImageDraw.Draw(img)
    person(d, 900, 1240, 520, (60, 35, 30))
    return tag(img, "shore")


# ------------------------------------------------------------------ RGBA layers
def layer_ship() -> Image.Image:
    img = Image.new("RGBA", (900, 760), (0, 0, 0, 0))
    ship(img, 450, 720, 1.1)  # type: ignore[arg-type]
    return img


def layer_fish() -> Image.Image:
    img = Image.new("RGBA", (1400, 600), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse([60, 120, 1100, 520], fill=(38, 60, 82, 255))
    d.polygon([(1000, 320), (1380, 100), (1320, 320), (1380, 540)], fill=(38, 60, 82, 255))
    d.ellipse([220, 230, 290, 300], fill=(240, 240, 230, 255))
    d.ellipse([240, 250, 275, 285], fill=(10, 10, 10, 255))
    return img


def layer_jonah() -> Image.Image:
    img = Image.new("RGBA", (260, 520), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    person(d, 130, 510, 500, (110, 60, 50, 255), arms_up=True)  # type: ignore[arg-type]
    return img


# ------------------------------------------------------------------ narration
def build_narration(tmp: Path) -> tuple[Path, list[tuple[int, int]]]:
    texts = tmp / "texts.json"
    texts.write_text(json.dumps(LINES), encoding="utf-8")
    subprocess.run(  # noqa: S603
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts" / "tts_sapi.ps1"),
            "-TextsJson",
            str(texts),
            "-OutDir",
            str(tmp),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    pcm = b""
    spans: list[tuple[int, int]] = []
    params = None
    sr = 22050

    def silence(ms: int) -> bytes:
        return b"\x00\x00" * (sr * ms // 1000)

    cursor_ms = 0
    for i in range(len(LINES)):
        with wave.open(str(tmp / f"line-{i:02d}.wav"), "rb") as wf:
            p = (wf.getnchannels(), wf.getsampwidth(), wf.getframerate())
            params = params or p
            assert p == params == (1, 2, sr), p
            data = wf.readframes(wf.getnframes())
        lead = LEAD_MS if i == 0 else 0
        trail = TAIL_MS if i == len(LINES) - 1 else GAP_MS
        chunk = silence(lead) + data + silence(trail)
        dur_ms = len(chunk) // 2 * 1000 // sr
        spans.append((cursor_ms, dur_ms))
        cursor_ms += dur_ms
        pcm += chunk
    out = tmp / "narration.wav"
    with wave.open(str(out), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm)
    return out, spans


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ------------------------------------------------------------------ manifest
PH = {
    "kind": "placeholder",
    "source": "scripts/make_fixtures.py (procedural Pillow drawing)",
    "license": "CC0-1.0 (generated by this repository; no third-party material)",
    "licenseVerified": True,
    "notes": "PLACEHOLDER art, not final Jonah character art. Creative validation pending (G1).",
}
SYN = {
    "kind": "synthetic",
    "source": "Windows SAPI voice 'Microsoft David Desktop' via scripts/tts_sapi.ps1; "
    "script text is an original paraphrase written for this fixture",
    "license": "Windows speech-synthesis output; redistribution terms NOT verified - replace "
    "with creator narration before any public use",
    "licenseVerified": False,
    "notes": "Synthetic dev narration. Not the creator's voice.",
}


def cam(s0: float, x0: float, y0: float, s1: float, x1: float, y1: float, ease: str = "easeInOut") -> dict:
    return {"start": {"scale": s0, "x": x0, "y": y0}, "end": {"scale": s1, "x": x1, "y": y1}, "easing": ease}


def build_manifest(spans: list[tuple[int, int]], total_ms: int, files: dict[str, Path]) -> dict:
    def asset(aid: str, typ: str, key: str, prov: dict) -> dict:
        p = files[key]
        return {"id": aid, "type": typ, "path": p.relative_to(OUT).as_posix(), "sha256": sha(p), "provenance": prov}

    assets = [
        asset("narration", "audio", "narration", SYN),
        asset("harbor-dawn", "environment", "harbor_dawn", PH),
        asset("sea-day", "environment", "sea_day", PH),
        asset("sea-calm", "environment", "sea_calm", PH),
        asset("storm-sea", "environment", "storm_sea", PH),
        asset("ship-deck", "environment", "ship_deck", PH),
        asset("below-deck", "environment", "below_deck", PH),
        asset("deck-group", "environment", "deck_group", PH),
        asset("underwater", "environment", "underwater", PH),
        asset("inside-fish", "environment", "inside_fish", PH),
        asset("prayer", "environment", "prayer", PH),
        asset("shore", "environment", "shore", PH),
        asset("ship-layer", "prop", "layer_ship", PH),
        asset("fish-layer", "character", "layer_fish", PH),
        asset("jonah-layer", "character", "layer_jonah", PH),
    ]
    S = spans
    shots = [
        {
            "id": "shot-01",
            "sceneId": "scene-1",
            "mode": "CINEMATIC",
            "sourceAssetIds": ["harbor-dawn"],
            "action": "Establishing: dawn over the harbour; slow push-in",
            "camera": cam(1.0, 0.5, 0.5, 1.22, 0.56, 0.58),
        },
        {
            "id": "shot-02",
            "sceneId": "scene-1",
            "mode": "LAYERED",
            "sourceAssetIds": ["sea-day"],
            "action": "Ship sails across the horizon",
            "mustShow": ["ship moves left to right"],
            "layers": [
                {
                    "assetId": "ship-layer",
                    "start": {"x": 0.12, "y": 0.60, "widthFrac": 0.22},
                    "end": {"x": 0.80, "y": 0.58, "widthFrac": 0.26},
                    "easing": "easeInOut",
                    "swayDeg": 2.5,
                    "swayPeriodMs": 3200,
                }
            ],
            "transition": {"type": "crossfade", "durationMs": 600},
        },
        {
            "id": "shot-03",
            "sceneId": "scene-2",
            "mode": "LAYERED",
            "sourceAssetIds": ["storm-sea"],
            "action": "Ship tossed in a thunderstorm",
            "mustShow": ["ship rocks", "lightning flash"],
            "camera": cam(1.0, 0.5, 0.5, 1.12, 0.5, 0.55, "linear"),
            "layers": [
                {
                    "assetId": "ship-layer",
                    "start": {"x": 0.5, "y": 0.62, "widthFrac": 0.34, "rotateDeg": -4},
                    "end": {"x": 0.52, "y": 0.64, "widthFrac": 0.36, "rotateDeg": 4},
                    "easing": "linear",
                    "swayDeg": 9,
                    "swayPeriodMs": 2100,
                }
            ],
            "effects": [{"type": "flash", "atMs": [1500, 4200], "intensity": 0.45}],
            "transition": {"type": "crossfade", "durationMs": 700},
        },
        {
            "id": "shot-04",
            "sceneId": "scene-2",
            "mode": "CINEMATIC",
            "sourceAssetIds": ["ship-deck"],
            "action": "Sailors panic; pan across the deck",
            "camera": cam(1.25, 0.25, 0.55, 1.25, 0.75, 0.55, "easeInOut"),
            "transition": {"type": "cut", "durationMs": 0},
        },
        {
            "id": "shot-05",
            "sceneId": "scene-2",
            "mode": "STATIC",
            "sourceAssetIds": ["below-deck"],
            "action": "Jonah asleep below deck (held beat)",
            "transition": {"type": "cut", "durationMs": 0},
        },
        {
            "id": "shot-06",
            "sceneId": "scene-3",
            "mode": "CINEMATIC",
            "sourceAssetIds": ["deck-group"],
            "action": "Sailors cast lots; slow push toward the group",
            "camera": cam(1.0, 0.5, 0.5, 1.3, 0.62, 0.6),
            "transition": {"type": "crossfade", "durationMs": 500},
        },
        {
            "id": "shot-07a",
            "sceneId": "scene-3",
            "mode": "GENERATIVE",
            "fallbackMode": "CINEMATIC",
            "sourceAssetIds": ["ship-deck", "jonah-layer"],
            "action": "Sailors lift Jonah and throw him over the railing",
            "mustShow": ["Jonah crosses the railing", "Jonah moves outward and downward"],
            "avoid": ["Jonah jumping voluntarily", "face replacement", "duplicated limbs"],
            "camera": cam(1.0, 0.5, 0.55, 1.25, 0.5, 0.6),
            "generation": {"providerProfileId": "mock-video", "clipAssetId": None},
            "approval": "pending",
            "transition": {"type": "cut", "durationMs": 0},
        },
        {
            "id": "shot-07b",
            "sceneId": "scene-3",
            "mode": "CINEMATIC",
            "sourceAssetIds": ["ship-deck"],
            "action": "Aftermath: sailors at the rail; slow drift toward the sea",
            "camera": cam(1.2, 0.5, 0.5, 1.35, 0.7, 0.42, "easeOut"),
            "transition": {"type": "cut", "durationMs": 0},
        },
        {
            "id": "shot-08",
            "sceneId": "scene-4",
            "mode": "CINEMATIC",
            "sourceAssetIds": ["sea-calm"],
            "action": "The sea falls calm; slow pull-back",
            "camera": cam(1.3, 0.5, 0.6, 1.0, 0.5, 0.5, "easeOut"),
            "transition": {"type": "crossfade", "durationMs": 800},
        },
        {
            "id": "shot-09",
            "sceneId": "scene-4",
            "mode": "GENERATIVE",
            "fallbackMode": "CINEMATIC",
            "sourceAssetIds": ["underwater"],
            "action": "A great fish rises from the deep and swallows Jonah",
            "mustShow": ["fish emerges from below", "Jonah swallowed"],
            "camera": cam(1.0, 0.5, 0.3, 1.3, 0.5, 0.75, "easeIn"),
            "generation": {"providerProfileId": "mock-video", "clipAssetId": None},
            "approval": "pending",
            "transition": {"type": "crossfade", "durationMs": 600},
        },
        {
            "id": "shot-10",
            "sceneId": "scene-5",
            "mode": "STATIC",
            "sourceAssetIds": ["inside-fish"],
            "action": "Darkness inside the fish (three days)",
            "transition": {"type": "fadeblack", "durationMs": 900},
        },
        {
            "id": "shot-11",
            "sceneId": "scene-5",
            "mode": "CINEMATIC",
            "sourceAssetIds": ["prayer"],
            "action": "Jonah prays; slow push-in on the light",
            "camera": cam(1.0, 0.5, 0.55, 1.35, 0.5, 0.65, "easeInOut"),
            "transition": {"type": "crossfade", "durationMs": 700},
        },
        {
            "id": "shot-12",
            "sceneId": "scene-6",
            "mode": "LAYERED",
            "sourceAssetIds": ["shore"],
            "action": "The fish swims away from the shore; Jonah is safe",
            "layers": [
                {
                    "assetId": "fish-layer",
                    "start": {"x": 0.62, "y": 0.66, "widthFrac": 0.34},
                    "end": {"x": 1.25, "y": 0.62, "widthFrac": 0.34},
                    "easing": "easeIn",
                    "swayDeg": 1.5,
                    "swayPeriodMs": 2600,
                }
            ],
            "camera": cam(1.0, 0.5, 0.5, 1.12, 0.45, 0.5, "linear"),
            "transition": {"type": "crossfade", "durationMs": 900},
        },
    ]
    S = list(S)
    st7, du7 = S[6]
    S[6:7] = [(st7, 5000), (st7 + 5000, du7 - 5000)]
    for sh, (st, du) in zip(shots, S, strict=True):
        sh["startMs"], sh["durationMs"] = st, du
        sh.setdefault("mustShow", [])
        sh.setdefault("avoid", [])
    scenes = []
    titles = {
        "scene-1": "The call and the flight",
        "scene-2": "The storm",
        "scene-3": "Overboard",
        "scene-4": "Calm and the great fish",
        "scene-5": "In the fish",
        "scene-6": "Dry land",
    }
    for sid, title in titles.items():
        mem = [s for s in shots if s["sceneId"] == sid]
        scenes.append(
            {
                "id": sid,
                "title": title,
                "characterIds": ["jonah"],
                "narration": {"startMs": mem[0]["startMs"], "endMs": mem[-1]["startMs"] + mem[-1]["durationMs"]},
                "shotIds": [m["id"] for m in mem],
            }
        )
    return {
        "schemaVersion": "1.0.0",
        "projectId": "jonah-phase0",
        "title": "Jonah - Phase 0 feasibility slice (placeholder art, synthetic narration)",
        "video": {"width": 1920, "height": 1080, "fps": 24, "fadeInMs": 600, "fadeOutMs": 1200},
        "narration": {"assetId": "narration", "durationMs": total_ms},
        "assets": assets,
        "scenes": scenes,
        "shots": shots,
    }


def main() -> int:
    for d in (IMG_DIR, LAYER_DIR, AUDIO_DIR):
        d.mkdir(parents=True, exist_ok=True)
    files: dict[str, Path] = {}
    for key, fn in {
        "harbor_dawn": harbor_dawn,
        "sea_day": sea_day,
        "storm_sea": storm_sea,
        "ship_deck": ship_deck,
        "below_deck": below_deck,
        "deck_group": deck_group,
        "underwater": underwater,
        "inside_fish": inside_fish,
        "prayer": prayer,
        "shore": shore,
    }.items():
        p = IMG_DIR / f"{key}.jpg"
        fn().save(p, quality=90, optimize=True)
        files[key] = p
    p = IMG_DIR / "sea_calm.jpg"
    sea_day(calm=True).save(p, quality=90, optimize=True)
    files["sea_calm"] = p
    for key, fn in {"layer_ship": layer_ship, "layer_fish": layer_fish, "layer_jonah": layer_jonah}.items():
        p = LAYER_DIR / f"{key.removeprefix('layer_')}.png"
        fn().save(p, optimize=True)
        files[key] = p
    with tempfile.TemporaryDirectory() as t:
        wav, spans = build_narration(Path(t))
        dest = AUDIO_DIR / "narration.wav"
        dest.write_bytes(wav.read_bytes())
        files["narration"] = dest
    total_ms = sum(d for _, d in spans)
    manifest = build_manifest(spans, total_ms, files)
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    prov = [{"id": a["id"], "path": a["path"], "sha256": a["sha256"], **a["provenance"]} for a in manifest["assets"]]
    (OUT / "PROVENANCE.json").write_text(json.dumps(prov, indent=2) + "\n", encoding="utf-8")
    print(f"narration {total_ms} ms, shots={len(manifest['shots'])}, assets={len(manifest['assets'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
