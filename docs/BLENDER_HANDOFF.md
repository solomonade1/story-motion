# Blender → StoryMotion handoff

What to export so StoryMotion can use it with no rework. These are recommendations from the pipeline's current
behaviour; **verify with one small test render before producing a whole episode.**

## Folder (one per episode): `projects/<episode>/`
```
audio/   narration.wav (or .mp3)      <- required; narration is the clock
images/  full-frame pictures (PNG/JPG/WebP), 16:9
layers/  transparent cut-outs (PNG with alpha) for things that move on their own
clips/   videos you rendered (MP4/MOV) for shots with real action
```
Then run `python -m storymotion_media scan projects/<episode>` — it registers every file (hash, type, size,
duration), writes `assets.scan.json`, and reports problems. It never changes your files.

## Clips (action shots) → `clips/`
- Resolution **1920×1080**, **24 fps** (30 fps is allowed if the project is 30 fps; other rates are converted).
- **H.264 MP4** (Blender: Output → File Format *FFmpeg Video*, Container *MPEG-4*, Codec *H.264*, quality *High*). No audio needed.
- Colour: set **View Transform = Standard** (the default *Filmic/AgX* can look washed out next to your other pictures).
- Name by shot: `shot-07a_throw.mp4`. Render **a little longer than the shot** (about 0.5 s extra at the start and end):
  the manifest can trim the start (`trimStartMs`) and the end is cut. A clip shorter than its shot holds its last frame
  and the render report warns you.
- Clips are used **as-is** (scaled/cropped to fill the frame). Local effects such as camera moves are not applied on top.

## Layers (moving cut-outs) → `layers/`
- **PNG, RGBA**, Alpha mode **Straight** (Blender: Output → Color *RGBA*). A layer with no transparency is flagged by `scan`.
- Render each character/prop **alone** on a transparent background from the **same camera** as its background plate, so lighting and perspective match.
- Trim empty margins (the layer is positioned by its centre).
- Pieces that need to bend (arm, forearm, head) should be separate PNGs. *Pivot points per layer are not built yet* — rotation is
  around each layer's centre until that is added.

## Images (backgrounds) → `images/`
- 16:9, **at least 1920×1080**; **2560×1440 or larger** gives headroom for push-ins/pans.
- Render the background **without** characters if characters will be layers.
- Optional: render a depth pass with the same name + `_depth` (reserved for future parallax; ignored today).

## Licence and provenance
`scan` sets every file to `licenseVerified: false` with a TODO. Before a video is published, fill in each asset's `source` and
`license` (your own Blender work: say so; purchased/free models: record the licence and keep the receipt/terms).

## Choosing the mode per shot
| You have | Use shot mode |
|---|---|
| One picture, camera moves only | `CINEMATIC` |
| One picture, no movement | `STATIC` |
| Background + cut-outs that move | `LAYERED` |
| A finished Blender clip | `RENDERED` |
| A cloud-generated clip (later, approved + paid) | `GENERATIVE` (with a local fallback) |
