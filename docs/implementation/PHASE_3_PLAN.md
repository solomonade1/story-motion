# Phase 3 plan — long-form narration, audio, caching, reliable export (PRD M2 / G3)

**Status:** PLAN ONLY. Nothing here is built. Phase 2 is still open for G2 (real Jonah episode, time log, scores). Phase 3 work may start on the
owner's authorisation; per the Quality Gates, G3 cannot be formally passed until G2 passes.
**Source:** Phased prompt §D Phase 3, PRD M2, QG v1.2 (TIME-03/05/06, OPS-01–04/06/07/09/10, ANIM-04, F-09/10/11/16, G3 checklist).

## 1. Where we start (facts from the code today)
| Area | Today | Gap for ~15 min |
|---|---|---|
| Composition | one FFmpeg run: every shot segment is an input; xfade/concat chained in one filter graph; whole video re-encoded at the end | ~100–200 inputs and a 100+ filter chain at 24 fps × 900 s (21,600 frames): time and memory **unmeasured**; every re-export repeats the whole compose |
| Caching | none; every render re-encodes **all** segments (ADR-0005 is design only) | OPS-06, ANIM-04, F-16 cannot pass |
| Progress / cancel | progress and cancel are checked **between** FFmpeg steps; the long final step cannot be cancelled or show %, | FR-RENDER-004; cancel must work inside the final step |
| Recovery | interrupted job is marked `interrupted`; partial work is deleted; a re-run starts from zero | F-09 needs "recoverable": a restart must not redo finished segments |
| Waveform / timeline | none; shots edited by number, scrub shows a still | FR-AUDIO-001, FR-TIME-002 (waveform, drag boundary, snap) |
| Audio | narration + beds (gain, fades, loop, ducking); post-render clipping check **fails** the render above −0.3 dB | no SFX cues, no trim, no source-clipping or missing-narration preflight (FR-AUDIO-002/004) |
| Sync check | A/V delta from stream durations only | TIME-05 needs begin/middle/end checkpoints against known markers |
| Disk-full | not handled specially | F-10 / OPS-10 |

## 2. Slices (each is shippable and tested before the next starts)
**S0 — Measure first (spike, no product change).** Build a ~15-min placeholder episode (synthetic pictures, Piper narration, ~100 shots) and run today's renderer:
wall time, peak memory, temp disk, final size. Also time a 50- and 100-xfade chain. Output: numbers + **ADR-0011 (compose strategy)**. This decides S2's shape; it is the main schedule risk.

**S1 — Interruptible, observable FFmpeg steps.** Run FFmpeg as a supervised process: real progress from `-progress` (frames done / total → %, rough remaining-work estimate), cancel that
kills the process tree within ~2 s, below-normal priority and a thread cap so the UI stays responsive (OPS-09), disk-space preflight (estimate segments + output; warn/refuse), readable errors
for "no space left" / codec failures with partial files cleaned and prior exports untouched (OPS-10, F-10). Tests: cancel mid-step, simulated disk-full (injected; labelled *simulated*), API latency during a render.

**S2 — Segment cache, invalidation report, resumable export.** Implement ADR-0005: content-addressed segment cache under the project, key = shot JSON + source SHA-256s + video spec + processor and FFmpeg versions
(+ the *next* shot's transition, because it adds tail frames). A render reports per shot **reused / rebuilt / why** (edited, asset changed, transition changed, spec changed). Segments are verified (frame count) before reuse; a corrupt
or missing one is rebuilt (F-11). Cache size cap with least-recently-used pruning. A killed render keeps its finished segments, so re-running **resumes** (F-09). Depending on S0, compose is either kept as is or becomes
*chunked*: chunks that end on a hard cut are composed and cached separately, then joined by stream copy, and audio is mixed once and muxed — so editing one shot re-composes one chunk, not 15 minutes.
Evidence: with 80 shots, edit one → count real FFmpeg segment invocations (= 1) and prove unrelated segments are byte-identical (OPS-06, ANIM-04, F-16).

**S3 — Audio: waveform data, preflight, SFX/trim.** Server-side peaks per audio asset (cached; ~100 points/s) for the timeline. Audio preflight before render: narration missing/unavailable, **source** clipping (peak at/near 0 dBFS), long silence, duration mismatch, bed
louder than narration; shown as warnings (FR-AUDIO-004). Audio tracks gain `trimStartMs`, a length cap, and an SFX kind (one-shot at a time, no ducking). Final-mix clipping stays a hard check. Loudness (LUFS) reported, not enforced. Tests: TIME-06.

**S4 — Timeline UI for 15 minutes.** Waveform timeline with zoom and horizontal scroll, shot blocks you can **drag to move/trim with snap** (to neighbours, to waveform silences, to the playhead), scene bands, gap/overlap markers, playhead scrub.
Preview = an **animatic**: plays the narration (proxy AAC) and swaps each shot's still/clip poster at the right millisecond, labelled proxy fidelity; the rendered draft remains the motion reference. Virtualised lists so 150+ shots stay responsive. Tests: UI tests + a real-browser check at 15-min scale.

**S5 — Long-form proofs and evidence.** (a) Placeholder 15-min rehearsal end to end offline: render, cache edit test, kill/restart test, probe checks OPS-01–03, **TIME-05** with known markers (a beep and a flash frame at begin/middle/end; offset measured in the MP4; limit ≤ 100 ms, no cumulative drift),
memory/time/disk numbers. (b) Real episode runbook (extends `JONAH_PRODUCTION.md`): the owner's ~15-min narration and pictures, human creative review. `evidence/PHASE_3_REPORT.md` in the standard handoff format.

**S6 — Close-out.** Traceability and gate checklist updated; ADR-0011 accepted; PROCESSOR_VERSION bumped and determinism baselines re-recorded (a new compose path changes bytes); risks reviewed.

Order: S0 → S1 → S2 → S3 → S4 → S5 → S6 (S3 and S4 can swap; S4 needs S3's peaks).

## 3. Quality-gate coverage (what will be evidenced, and what stays human)
| Test | Slice | Evidence type |
|---|---|---|
| TIME-03 waveform, drag boundary, scrub, trim, crossfade, multi-track | S3, S4 | UI + browser check |
| TIME-05 sync begin/mid/end of ~15 min | S5 | marker measurement on the placeholder 15-min file; real episode later |
| TIME-06 mix + preflight, no clipping | S3 | automated |
| OPS-01–03 probe, duration ≤ 250 ms, completeness | S5 | ffprobe/black scan on the 15-min file |
| OPS-04 cancel/pause/terminate | S1, S2 | automated |
| OPS-06 / ANIM-04 / F-16 one edit → one segment | S2 | invocation count, 80 shots |
| OPS-07 offline | S5 | network guard (Python only; FFmpeg not instrumented) |
| OPS-09 UI responsive during render | S1 | API latency measured while rendering |
| OPS-10 / F-10 disk full | S1 | **simulated**; a true full-disk test is manual |
| F-09 kill worker mid-render | S2 | real process kill, restart, resume |
| F-11 changed source | S2 | cache invalidation test |
| Creative rubric on the 15-min export | S5 | **human only**; the agent cannot supply it |
| OPS-08 clean-machine install | — | Phase 5 (desktop shell still blocked by Smart App Control) |

**G3 can pass only when:** the real ~15-min episode exists, the checklist rows above are evidenced (placeholder runs count for engineering rows, not for the creative review), no open S0/S1 defects, and the owner signs. The agent will not self-certify.

## 4. Decisions needed from the owner
1. **Compose strategy** — decided after S0 numbers (recommendation: chunked compose if the single graph is slow or memory-heavy at 15 min).
2. **Cache budget** — default cap on cache disk use (suggest 20 GB, LRU pruning, "clear cache" button). 15 min of final-quality segments is a few GB.
3. **Preview** — animatic (stills + narration, instant) plus rendered draft for motion; or draft only. Recommendation: animatic + draft.
4. **Real 15-min episode** — which script/narration/pictures, and when; ideally the OG1 manual baseline episode is chosen at the same time (a comparable pair).
5. **Loudness** — report only (recommended), or enforce a target such as −16 LUFS?
6. **Piper narration for placeholders** — OK to spend ~10 min of CPU per placeholder 15-min narration (offline, free).

## 5. Risks
- **Single-graph compose may not scale** (time, memory, file handles) — S0 exists to find out before building on it.
- **Stream-copy joins** need chunk encodes with identical parameters and closed GOPs; A/V sync must be re-measured after joining (S5).
- **Process control on Windows** (killing FFmpeg's whole tree, antivirus file locks seen earlier) may need retries.
- **Intermittent test failure** `test_the_live_project_file_is_never_opened_for_writing` (2 sightings, cause unknown) — diagnose early in S1 by capturing the failure text.
- **Disk-full** can only be simulated automatically; say so in the report.
- **Bit-reproducibility**: the chunked path will not be byte-identical to today's; re-baseline deliberately and keep "same inputs → same bytes" as a tested property of the new path.
- **15-min placeholder** proves plumbing, not quality or the creator's time-saving (O-03 stays NOT VALIDATED).

## 6. Out of scope for Phase 3
Cloud generation and budgets (Phase 4), installer/clean-machine and three-episode pilot (Phase 5), outcome measurement (Phase 6), automatic transcription alignment (P1), auto-ducking beyond today's, doctrinal checking.
