# Requirements Traceability — P0 FR-IDs → Quality Gates → phase → evidence

**Baseline:** PRD v1.1 (`docs/PRD.md`, SHA-256 `6e5363538c53…b2751`) and Quality Gates **v1.2** (`docs/QUALITY_GATES.md`,
SHA-256 `12d363ffd7c9…4856`, approved as written, DR-002; v1.2 preserves the same 48 P0 rows of Appendix A). **Evidence owner for every row: the editor.**
**Status vocabulary** (never skip a level): `Implemented` → `Tested` (automated test exists and passed) →
`Tech-validated` (meets the gate's technical threshold on real fixtures) → `Creative-validated` (human review) →
`Outcome-validated` (O-IDs). Phase 0 reaches at most *Tested* for partial slices; **no row is Creative- or
Outcome-validated.** "Not started" means no code exists.

Outcome IDs: O-01 cadence, O-02 ≤$50/month, O-03 ≥50% less hands-on time, O-04 ≥70% usable first paid clip,
O-05 creative ≥4/5, O-06 on-time ≥95%, O-07 cost per accepted AI second (diagnostic).

| FR-ID | QG tests | Planned phase | O-IDs | Phase 0 status | Evidence / gap |
|---|---|---|---|---|---|
| FR-PROJ-001 | DATA-01 | 1 | O-03 | Not started | project CRUD is Phase 1 |
| FR-PROJ-002 | DATA-02, F-08 | 1 | O-01,O-06 | Not started | autosave/atomic manifest save; only atomic *render publish* exists |
| FR-PROJ-003 | DATA-03, F-11 | 1 | O-03 | Partial · Tested | missing/changed asset is detected & listed per asset (`test_F11_*`); no relink UI |
| FR-PROJ-004 | DATA-07 | 1 | O-06 | Partial · Implemented | `schemaVersion` + major check (`test_unsupported_schema_major…`); no migrations |
| FR-MEDIA-001 | DATA-04 | 1 | O-03 | Partial · Tested | PNG/JPEG/WAV exercised; WebP/MP3/AAC/MOV allowed by contract but **not tested** |
| FR-MEDIA-002 | DATA-04,05 | 1 | O-03 | Partial · Tested | sha256, dims, duration, sample rate, channels, fps via ffprobe (`ingest.py`) |
| FR-MEDIA-003 | DATA-06 | 1 | O-03 | Not started | no thumbnails/asset proxies (draft *output* preview exists, see FR-TIME-005) |
| FR-MEDIA-004 | DATA-06 | 1 | O-03 | Partial · Implemented | asset `type` categories in contract; no UI |
| FR-MEDIA-006 | DATA-04,05, F-13 | 1 | O-03 | Partial · Tested | corrupt-file error (`test_DATA04_*`); hash recorded; **duplicate detection not implemented** |
| FR-SCRIPT-001 | TIME-01 | 2 | O-03 | Not started | TXT/MD import is Phase 2 |
| FR-SCRIPT-002 | TIME-01, F-12 | 2 | O-03 | Partial · Tested | JSON manifest validated with field paths + line/col (`test_contracts.py`, `test_F12_*`); CLI only |
| FR-SCRIPT-003 | TIME-02 | 2 | O-03 | Partial · Implemented | contract fields exist (characters, action, mustShow, avoid, mode, duration); **no editor** |
| FR-SCRIPT-004 | TIME-02 | 2 | O-01 | Partial · Tested | scene/shot narration ranges validated against narration length |
| FR-TIME-001 | TIME-03 | 2–3 | O-03 | Partial | narration + visual track only; music/SFX/titles tracks absent |
| FR-TIME-002 | TIME-03 | 2–3 | O-03 | Not started | waveform, scrubber, snapping, drag editing |
| FR-TIME-003 | TIME-03 | 2 | O-05 | Partial · Tested | cut, crossfade, fadeblack, fade in/out rendered; trim/position/opacity controls absent |
| FR-TIME-004 | TIME-03 | 2 | O-05 | Partial · Tested | gap/overlap/negative/missing-ref reported with amounts (`test_contracts.py`) |
| FR-TIME-005 | TIME-04, TIME-07 | 2 | O-03 | Partial · Tested | draft proxy render + `preview.html` labelled "proxy fidelity" (`test_preview_page_*`); preview-vs-export cut deviation **not measured** |
| FR-ANIM-001 | ANIM-01 | 2 | O-02,O-05 | Partial · Tested | pan/zoom/easing/crop/reframe + flash effect; no particle effects; 10-shot ANIM-01 sample **not run** |
| FR-ANIM-002 | ANIM-02 | 2 | O-02,O-05 | Partial · Tested | translate/rotate/scale(widthFrac)/sway with easing; centre pivot only; save/reopen not applicable yet |
| FR-ANIM-003 | ANIM-03 | 4 | O-04 | Partial · MOCK | request/validate against fake provider only; **no live provider** |
| FR-ANIM-004 | ANIM-03 | 2 | O-02 | Partial · Tested | mode + required `fallbackMode`; fallback reported, never silent (`test_generative_without_clip_*`) |
| FR-ANIM-005 | ANIM-04, ANIM-05 | 3–4 | O-04 | Not started | immutable versions / revert not built; `approval` field only |
| FR-AI-001 | COST-01 | 4 | O-04 | Partial · MOCK | provider-neutral protocol; manifest cannot hold provider fields/secrets |
| FR-AI-002 | COST-09 | 4 | O-02 | Partial · MOCK | capabilities object (formats, durations, resolutions, price, cancel); values invented |
| FR-AI-003 | COST-01 | 4 | O-04 | Partial · MOCK | request validation (`test_unsupported_requests_rejected_before_quote`) |
| FR-AI-004 | COST-06,07, F-04, F-14 | 4 | O-04 | Partial · MOCK | submit/poll/lookup/download/hash verify; **job state not persisted** |
| FR-AI-005 | COST-05,06 | 4 | O-02 | Partial · MOCK | bounded transport retry vs new approval; no blind resubmit (`test_lost_response_*`) |
| FR-AI-006 | COST-07, ANIM-05 | 4 | O-04 | Not started | per-shot approve/reject/regenerate UI & versions |
| FR-AI-007 | COST-01 | 4 | O-04 | Partial · MOCK | capability `warnings` field only; no UI display |
| FR-BUD-001 | COST-03 | 4 | O-02 | Not started | caps/currency config |
| FR-BUD-002 | COST-09, F-03 | 4 | O-02 | Partial · MOCK | integer micro-USD quote with min-billable rounding |
| FR-BUD-003 | COST-04,08 | 4 | O-02 | Not started | reservations/ledger (ADR-0006 design only) |
| FR-BUD-004 | COST-03,04, F-05 | 4 | O-02 | Not started | `spent+reserved+new ≤ cap` check |
| FR-BUD-005 | COST-01,05 | 4 | O-02 | Partial · MOCK | approval object requires explicit confirmation; no UI |
| FR-BUD-006 | COST-08,11 | 4 | O-02 | Not started | ledger record incl. discrepancy (mock provider charge list only) |
| FR-BUD-007 | COST-02, F-03 | 4 | O-02 | Partial · MOCK | unknown price ⇒ `PricingUnavailable`, zero submissions (`test_unknown_price_fails_closed`) |
| FR-BUD-008 | COST-08 | 4 | O-02 | Not started | 50/75/90/100% warnings |
| FR-AUDIO-001 | TIME-03,05 | 3 | O-03 | Partial | narration length drives the timeline; no waveform |
| FR-AUDIO-002 | TIME-03,06 | 3 | O-05 | Not started | music/SFX mixing |
| FR-AUDIO-003 | TIME-05,06 | 3 | O-05 | Partial · Tested | AAC 48 kHz stereo verified by ffprobe in every render |
| FR-AUDIO-004 | TIME-06, OPS-02 | 3 | O-05 | Partial · Tested | narration/audio/video duration-mismatch checks; no clipping or missing-narration warnings |
| FR-RENDER-001 | OPS-01 | 0–3 | O-03 | Partial · Tested | FFmpeg subprocess, argv lists, whitelist, timeouts, temp output → atomic publish |
| FR-RENDER-002 | OPS-01 | 0–3 | O-03 | Partial · Tested | 1920×1080 H.264/AAC MP4 @24 fps; **30 fps untested** |
| FR-RENDER-003 | OPS-04 | 0–3 | O-03 | Partial · Tested | 640×360 draft + final presets |
| FR-RENDER-004 | OPS-04,09 | 3 | O-06 | Partial · Tested | timeout-kill leaves no output (`test_step_timeout_*`); no progress, cancel, resume |
| FR-RENDER-005 | OPS-01,02,03 | 0–3 | O-05,O-06 | Partial · Tested | existence, codecs, dims, fps, exact frame count, full decode, black-frame scan, A/V delta |
| FR-RENDER-006 | OPS-06, F-16 | 3 | O-03 | Not started | caching is ADR-0005 design only |

## Additions since the first matrix (owner-authorised, DR-001) — row updates
FR-AUDIO-002 (music/SFX overlay with volume, fades, trim): **Partial · Tested** — bed tracks with gain/start/fades/loop/ducking (`tests/integration/test_audio_mix.py`); SFX uses the same mechanism, untested as SFX.
FR-AUDIO-004 (warn on clipping): **Partial · Tested** — post-render peak check fails a render above −0.3 dB. FR-AUDIO-003: unchanged (AAC 48 kHz stereo).
FR-ANIM-004/FR-TIME-003: `RENDERED` mode, clip `speed`/`trimStartMs`, pause-timed dissolve/dip transitions — **Partial · Tested**.
FR-MEDIA-001/-006: `scan` flags unsupported/corrupt files and mis-filed videos — **Partial · Tested**; MP4 clips now exercised, WebP/MP3/AAC/MOV(+30 fps) still **not tested**.
No row has moved to Creative- or Outcome-validated.

## Phase 1 row updates (build `p1-20261114-b75743ce627a`; evidence `quality/evidence/p1-20261114-b75743ce627a/`)
Statuses move to **Tested** only where an automated test passed on this build. Nothing here is Creative- or Outcome-validated. The desktop shell is **not built**, so no row is validated "in the desktop app".

| FR-ID | QG | Phase 1 status | Evidence / remaining gap |
|---|---|---|---|
| FR-PROJ-001 | DATA-01 | **Tested** (browser-hosted UI + API) | create/rename/open/duplicate/archive/delete (+ trash/restore/purge): `test_studio_store.py`, `test_studio_api.py`, `Projects.test.tsx` |
| FR-PROJ-002 | DATA-02, F-08 | **Partial · Tested** | atomic writes + `.bak` + recovery; 20 random hard kills + never-opened-for-write invariant (mutation-checked). **≤10 s loss bound not measured; app/shell crash not tested** |
| FR-PROJ-003 | DATA-03, F-11 | **Tested** | relative paths for copied assets, absolute for linked; missing/changed flagged; relink by path and by folder search (hash-verified) |
| FR-PROJ-004 | DATA-07 | **Tested** | version field, ordered migrations (1 real: pre-release layout), originals preserved, newer major refused |
| FR-MEDIA-001 | DATA-04 | **Tested** | PNG, JPEG, WebP, WAV, MP3, AAC, MP4, MOV all imported (previously untested formats now covered) |
| FR-MEDIA-002 | DATA-04..06 | **Tested** | SHA-256, size, dimensions, duration, sample rate, channels, fps |
| FR-MEDIA-003 | DATA-06 | **Tested** | 320 px thumbnails (image/video frame/waveform); 360p H.264 / 1280 px JPEG / AAC proxies |
| FR-MEDIA-004 | DATA-06 | **Tested** | categories assignable and validated (7 incl. rendered_video) |
| FR-MEDIA-006 | DATA-04, 05, F-13 | **Tested** | duplicate by hash, corrupt/empty/wrong-type/missing errors, copy vs link, hostile file names inert |
| FR-SCRIPT-001 | TIME-01 | **Partial** | the script is stored and autosaved as text; TXT/MD *file* import not built |
| FR-RENDER-004 | OPS-04 | **Partial** | progress + cancel exist for import/check jobs only; render progress/cancel/resume still absent |
| FR-TIME-005 | TIME-07 | **Partial** | proxies exist and are served; the labelled preview *player* in the UI is not built |
Unchanged and still **Not started**: FR-TIME-001/002/004 (timeline), FR-ANIM-005, FR-AI-006, FR-BUD-001/003/004/006/008, FR-RENDER-006.

## Gate checklist status — G0 and G1 (see `quality/evidence/p0-20261114-fe27e05256e2/GATE_CHECKLIST.md`)

| Gate | Status |
|---|---|
| G0 | **PASS** (exceptions E-1 licences unverified, E-2 provider unverified) |
| G1 | **PASS — limited scope** (technical criteria met on placeholder + real-asset cuts; no live provider; owner approved narrative/flow) |
| G2 onward | NOT RUN |

## Phase 2 slice 1 row updates (storyboard backend; 175 tests pass on this machine; no UI yet, so nothing is "validated in the app")
| FR-ID | QG | Status | Evidence / remaining gap |
|---|---|---|---|
| FR-SCRIPT-001 | TIME-01 | **Partial · Tested** | TXT/MD import -> editable scenes (`tests/unit/test_storyboard.py`, `tests/integration/test_storyboard_api.py`); no file picker/editor UI |
| FR-SCRIPT-002 | TIME-01 | **Partial · Tested** | plan JSON import: invalid JSON -> line/column, bad fields -> `scenes[0].shots[0].durationMs` style paths, nothing saved on error (HTTP 422); no UI |
| FR-SCRIPT-003 | TIME-02 | **Partial · Tested** | characters, image, startMs, durationMs, action, mustShow, avoid, mode, preset stored and validated; no editor UI |
| FR-SCRIPT-004 | TIME-02 | **Partial · Tested** | save/reopen via project document; narration length read live from the audio asset; shots past the end flagged |
| FR-TIME-004 | TIME-03 | **Partial · Tested** | gap/overlap/late-start/short-of-narration reported with exact ms; saved, not repaired; no timeline UI |
Still **Not started** in Phase 2: FR-TIME-002 (scrub/trim/reorder UI), FR-TIME-005 preview accuracy (TIME-04), presets + motion engine from the editor (ANIM-01/02 in the app), storyboard -> manifest -> render, 3-5 min Jonah production, active-time capture.

## Phase 2 slice 2 (storyboard UI; 54 UI tests, jsdom only - NOT yet checked in a real browser window)
FR-SCRIPT-001..003 and FR-TIME-004: UI added (`apps/desktop/src/Storyboard.tsx`, `Storyboard.test.tsx`): file import with replace confirmation, field-located error display, shot editor with whole-ms validation, gap/overlap list with jump-to-shot.
FR-TIME-002: **Partial · Tested (jsdom)** - scrub slider, reorder (up/down), explicit "close gaps"/"fit to narration"; no drag-trim, no waveform (Phase 3). FR-TIME-005/TIME-04: scrub shows a labelled draft *still*; preview-vs-export timing **not measured**.

## Phase 2 slice 3 (storyboard -> render; 180 Python + 59 UI tests; draft renders only exercised on tiny synthetic fixtures)
| FR-ID | QG | Status | Evidence / gap |
|---|---|---|---|
| FR-ANIM-001 | ANIM-01 | **Partial · Tested** | presets map to camera moves with scale >= 1 (no borders); `test_motion_presets_really_move_the_picture` shows frames differ over time. 10-shot real-image ANIM-01 sample **not run** |
| FR-ANIM-004 | ANIM-03 | **Partial · Tested** | GENERATIVE renders its local fallback, reported in warnings + `fallbacks`; no AI request |
| FR-RENDER-001/003/005 | OPS-01/04 | **Partial · Tested** | storyboard render via API: draft 640x360 + final presets, post-render verification, new file per render, never overwrites |
| FR-RENDER-004 | OPS-04, F-09 | **Partial · Tested** | progress + cancel between steps (a running FFmpeg step is not interrupted); cancelled render publishes nothing. Resume/restart-in-render **not run** |
| FR-TIME-005 | TIME-04/07 | **Partial** | rendered draft playable in the UI with a DRAFT badge; preview-vs-export cut deviation **not measured** |
Refusals tested: render is blocked (HTTP 409, with reasons) on gaps, overlaps, missing pictures, LAYERED shots, no narration.

## Phase 2 slice 4 (transitions, clip speed, audio beds, fades in the storyboard; 186 Python + 67 UI tests)
FR-TIME-003 (trim, crossfade, fades): **Partial · Tested** - crossfade/dip transitions, clip trim, speed (incl. fit), video fades from the storyboard; "finish transition at shot start" helper. FR-AUDIO-002 (music/SFX, volume, fades): **Partial · Tested** - beds with level, start, fades, loop, ducking in the UI; SFX as separate cues and waveform editing remain Phase 3.
Real-asset check (not a creative review): Hezekiah cut rebuilt in Studio - final MP4 video stream md5 identical to `out/hezekiah/hezekiah_piper_joe_with_music.mp4`, -18.3 LUFS / -3.3 dBFS peak same, audio difference ~-81 dB mean. Quality not judged by ear or eye by the agent.

## Jonah setup (189 Python + 67 UI tests)
FR-TIME-005 / TIME-04: **Partial · Tested (placeholder rehearsal + synthetic test)** - `timing-check` measures hard-cut frames in a render against its report; rehearsal: median 0, max 0 frames (draft and final, 7 cuts). Crossfades not measured. Real-episode measurement pending.
TIME-07 offline: rehearsal ran with a Python socket guard (no non-loopback connection); FFmpeg subprocesses not instrumented; real-episode offline check pending.

## LAYERED shots in the Studio (203 Python + 75 UI tests)
FR-ANIM-002 / QG ANIM-02: **Partial · Tested** - layer transforms with easing, **pivot points** (centre and off-centre; `test_layer_pivot.py` measures the layer's centroid at 0/90/180 deg about edge pivots), layer order, rocking; stored in the storyboard and reproduced after save/reopen (`test_storyboard_layers.py`). Editor preview matches the render on one synthetic figure. **Not creative-validated; not tried on creator art.** Gaps: per-layer keyframes beyond start/end, no alpha check at import.
FR-SCRIPT-003 (animation modes selectable): all of STATIC / CINEMATIC / LAYERED / RENDERED / GENERATIVE(fallback) now usable from the editor.

## Export package (221 Python + 85 UI tests)
Not a PRD P0 row: added at the owner's request (editor hand-off and AI-model hand-off). Evidence: `tests/integration/test_export_pack.py` (clips probed for body+handle frames; OTIO ranges vs real frame counts; EDL timecodes; handoff content; round trip through Import scene plan; brief mode; refusals; cancel leaves nothing) and a pixel-identical re-assembly on real Hezekiah assets. Gaps: no editor import test, no FCP7 XML/FCPXML, no SFX/stems beyond beds, EDL video only.
