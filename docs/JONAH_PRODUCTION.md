# Jonah production runbook (Phase 2 / G2)

**Goal (Phased prompt, Phase 2):** a real 3–5 minute, cloud-free Jonah video with narration and at least 20 imported pictures, made in
the Studio, with your active time and quality feedback recorded, cut timing compared preview vs export, and close/reopen/offline checks.
**This is a creator task: the agent cannot supply your artwork, narration, time log or quality scores.** Until it is done, G2 is **not claimed**.

## 1. What you supply (put it in `projects/jonah-real/` or any folder you like)
| Need | Detail | Notes |
|---|---|---|
| Narration | one WAV or MP3, 3–5 min | the clock for every shot. A recorded voice, or Piper/SAPI (`scripts/make_narration.py`). Record the voice licence. |
| Pictures | **at least 20** distinct images, 16:9, 1920×1080 or larger (2560×1440 gives room for push-ins) | PNG/JPG/WebP. Full-frame; each is used as-is with camera moves. Record source + licence per image. |
| Script | TXT or MD (one narration line per line, or blank-line paragraphs, or `#` headings per scene) | Imported as scenes. |
| Action clips (optional) | MP4/MOV, 1920×1080, 24 fps, from Blender | for shots a flat picture cannot do (thrown overboard, fish). See `docs/BLENDER_HANDOFF.md`. Without them, say how each action is depicted instead. |
| Music / ambience (optional) | WAV/MP3 | ducked under the narration. **Record its licence**; a bought track needs the receipt. |

Layers: a moving character or prop is a separate **PNG with a transparent background**, placed over the shot's background picture (shot mode LAYERED, Storyboard tab → shot → Moving layers). Set the **pivot** (e.g. the shoulder) so arms and heads turn about the right point. A layer is a flat picture: it can slide, grow, tilt and rock, but it cannot bend. Pieces that must bend (arm, forearm) need separate PNGs.

Not supported yet (so plan around it): shot-level sound effects, waveform editing, per-layer keyframes beyond start/end, depth/parallax, and AI-generated clips.

## 2. Make the episode in the Studio
1. `python -m storymotion_media serve --workspace .\workspace`, open the printed URL (keep the `#token` private). Close it before starting a second copy.
2. **Projects → New project** ("Jonah episode 1").
3. **Media tab:** import the narration, music (if any), clips (if any), and all pictures. Fix any import error shown; tag each picture's category.
4. **Storyboard tab:** choose the narration → **Import script**. Add the characters. Add one shot per scene (or more), set each shot's picture, `Start`/`Duration`, mode (STATIC / CINEMATIC / RENDERED), preset, action, must-show, avoid.
   Use **Finish the transition where this shot starts** for dissolves, **Close gaps and overlaps** and **Fit last shot to narration end** to tidy timing. Add the bed and the video fades.
5. Clear every item under **Timeline checks** (nothing renders while problems remain), then **Render draft**, watch it, fix, repeat. Then **Render final**.
6. Check cut timing of the final and the draft (TIME-04):
   ```powershell
   .venv\Scripts\python -m storymotion_media timing-check .\workspace\projects\<p-id>\renders\<r-id>-final.mp4
   ```
   Exit 0 and `"withinTime04": true` means hard cuts land within the limits (median ≤ 1 frame, max ≤ 2). Crossfades are not measured (no single cut frame).
7. Close the Studio, reopen it, and confirm the storyboard and renders are unchanged (the rehearsal below proves the mechanism; do it once for real).
8. Offline check: disconnect from the network (or use airplane mode), open the project, preview, render a draft. It must all work.

## 3. Record the evidence (you; the agent must not fake any of this)
- **Time:** one row per work block in `docs/implementation/templates/time_logs.csv` (copy it next to your episode): `condition=studio`, stage from the baseline protocol, **active** minutes separate from **waiting** (render time) minutes.
- **Quality:** score the final in `creative_reviews.csv` on the six dimensions (1–5) with timecoded defects. Prefer a second reviewer.
- **Outcome row:** `episode_outcomes.csv` (final duration, revisions, failed exports, export SHA-256).
- Keep the final MP4, its `.json` render report (commands, warnings, fallbacks, hashes) and the timing-check output.

## 4. What G2 needs (QG v1.2) and where this stands
| Check | Needs | Status now |
|---|---|---|
| TIME-01/02 import + shot editing, save/reopen | UI + persistence | built and tested (browser UI) |
| TIME-03 trim/crossfade/scrub, gap/overlap reporting | UI | built; waveform + drag-trim are Phase 3 |
| TIME-04 preview vs export cut timing | measurement | tool built (`timing-check`); placeholder rehearsal measured; **your real episode not yet** |
| TIME-07 offline preview with proxy labelled | UI | built (draft badge + label); offline check on your episode pending |
| ANIM-01 pan/zoom on 10 real shots, no black borders | your pictures | **pending your pictures** (a visual review of ≥10 shots) |
| ANIM-02 layered transforms, pivots, ordering, save/reopen | LAYERED in the storyboard | **built** (layers with start/end pose, easing, pivot, rocking, draw order; preview + render agree on a test figure). **Not yet reviewed on your art** |
| ANIM-03 mode fallback | UI | built (GENERATIVE reports a local fallback) |
| ANIM-04 only the changed shot invalidated | cache | **Phase 3** (ADR-0005); today every render re-encodes all shots |
| Active time + quality feedback | you | **pending** |
G2 is eligible to PASS only when the real episode exists, these are evidenced, and **you** sign it. The agent will not self-certify.

## 5. Placeholder rehearsal (readiness only, not G2 evidence)
`python scripts\jonah_rehearsal.py` builds 24 labelled procedural pictures, narrates an original 30-line retelling with Piper, drives the Studio API
through import → storyboard → draft + final render → timing check → close/reopen → single-shot edit, and writes `out\rehearsal\rehearsal_report.json`.
It exists to find scale problems before your assets arrive. The pictures are not art and nobody judged the video.

## 6. Known limits
- Cancel stops between FFmpeg steps, not inside one.
- Re-rendering re-encodes every shot (no caching until Phase 3), so a ~3–5 min final takes a couple of minutes.
- Cut-timing measurement needs hard cuts and clearly different pictures either side; it reports a weak cut's score so a doubtful match is visible.
- The draft is a proxy: it is not a quality reference.
