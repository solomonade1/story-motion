# StoryMotion Studio — Implementation Status

**Updated:** 2026-11-14 · **Phase 0 passed (G0, G1 limited scope).** **Phase 1 PARTIAL (shell blocked on a toolchain install the owner must approve).**
**Authoritative inputs:** `docs/PRD.md` (v1.1) and `docs/QUALITY_GATES.md` (**v1.2**, owner-authored; approved as written by DR-002) — identical to the root files
`StoryMotion_Studio_PRD_v1.1.md` / `..._Quality_Gates_v1.1.md`; the unversioned root files are the superseded v1.0.
The phased build prompt (root) defines Phase 0. **Nothing here claims a gate passed without the evidence listed.**

## 1. One-paragraph summary
A Python worker + FFmpeg pipeline now turns a validated scene manifest, local images and narration into a playable
1080p MP4, with a provider-neutral cloud-generation boundary exercised only through a fake provider. A 85.6 s,
13-shot Jonah slice (placeholder art, synthetic narration) renders cloud-free and is probe-verified; rendering is
bit-reproducible on this machine; 77 automated tests pass. **What is proven is the plumbing. Creative quality,
real assets, live-provider behaviour, cost and time outcomes are NOT proven** (see §5–§7).

## 2. Evidence levels per capability
`I` implemented · `T` automated test passed · `TV` technically validated on the fixture · `CV` creatively validated ·
`OV` outcome validated. Only I/T/TV are reached in Phase 0; **no row is CV or OV.**

| Capability | I | T | TV | CV | OV | Notes |
|---|---|---|---|---|---|---|
| Scene-manifest contract v1.0.0 + field-located validation | ✔ | ✔ | ✔ | – | – | JSON Schema exported to `packages/contracts/` |
| Asset verification (containment, sha256, real decode, ffprobe metadata) | ✔ | ✔ | ✔ | – | – | PNG/JPEG/WAV exercised; WebP/MP3/AAC/MOV **not** tested |
| STATIC / CINEMATIC / LAYERED local render, cut/crossfade/fadeblack/fades | ✔ | ✔ | ✔ | – | – | 24 fps only tested |
| Narration-as-clock, integer-ms → frame quantisation | ✔ | ✔ | ✔ | – | – | max cut error 20.67 ms (≤ ½ frame) |
| Output verification (probe, exact frames, full decode, black scan) | ✔ | ✔ | ✔ | – | – | |
| Draft preview + labelled `preview.html` | ✔ | ✔ | ✔ | – | – | proxy fidelity; preview-vs-export cut deviation not measured |
| Bit-reproducible render (same machine/FFmpeg) | ✔ | ✔ | ✔ | – | – | 3 full-length renders, identical SHA-256 |
| Provider-neutral interface + fake provider (quote/approve/submit/poll/download) | ✔ | ✔ (MOCK) | – | – | – | proves app logic only |
| GENERATIVE shot → approved clip **or** declared fallback (never silent) | ✔ | ✔ | ✔ | – | – | mock clip only |
| OG1 baseline protocol + empty CSV templates | ✔ | n/a | n/a | n/a | **NOT VALIDATED** | no manual episode exists |

## 2b. Post-Phase-0 additions (owner-requested integration; 2026-11-14)
- `RENDERED` shot mode + `rendered_video` assets (schema 1.1.0, additive; 1.0.x manifests still load) for creator/Blender clips, with `trimStartMs`
  and hold/cut warnings. **Tested** (real FFmpeg clips: plays as-is, trim selects the right content, short clip warns, contract rules). Not creatively validated.
- `scan` command: registers a drop-folder (hash, type, probe), flags unsupported/corrupt files, opaque "layers", non-16:9/low-res images, odd clip sizes/fps.
  **Tested.** Provenance is left as TODO / `licenseVerified=false` deliberately.
- `docs/BLENDER_HANDOFF.md`: export conventions. **Unverified against a real Blender export** — validate with one small test render.
- `speed` (slow-down, frame-blended) on RENDERED clips; `build` command (plan.json + scanned folder -> manifest); `scripts/make_narration.py` (script.txt -> SAPI narration + per-line timings). **Tested** (84 tests pass). First real-asset run: `projects/hezekiah-real` (5 owner-supplied clips, draft SAPI voice) -> `out/hezekiah/hezekiah_short_draft_voice.mp4`, 37.8 s, 8 shots; **not creatively reviewed; clip licence unverified**.
- **Piper TTS** (offline neural voice; piper-tts 1.8.0, GPL-3.0 tool; voices in git-ignored `tools/piper-voices/`). Voice licences checked from each MODEL_CARD on 2026-11-14:
  `joe` CC0, `john`/`norman`/`bryce` public domain (commercially usable); **`ryan` and `hfc_male` are CC BY-NC-SA (non-commercial) - do not use for a monetised channel**; `lessac`/`alan` licences unclear - not used.
  `make_narration.py --engine piper` adds single-pass loudness normalisation (-16 LUFS). Plan builder gained `line` cues, `speed: "fit"` and `continue`. Hezekiah cut rebuilt with `en_US-joe-medium`: `out/hezekiah/hezekiah_short_piper_joe.mp4` (34.2 s). **Voice quality not judged by ear by the agent.**
- Transition rework (owner feedback: scene flow not smooth): transitions now start in the narration pause and finish as the next line begins; variants `plan.dissolve.json` / `plan.dip.json` rendered to `out/hezekiah/`. **Awaiting owner choice.**
- **Audio bed mixing** (FR-AUDIO-002 slice, first pass): manifest `audioTracks` (role music/ambience, gain, start, fades, loop, sidechain ducking under narration), limiter with -1 dB headroom (fixed: `alimiter` auto-levels to 0 dBFS unless `level=0`), post-render **clipping check** (peak must be <= -0.3 dB). Ducking verified numerically (0.0 dB when off, 12.5 dB for 12 dB requested). `scripts/make_ambience.py` synthesises an **original** placeholder-grade bed timed to the narration (no third-party licence; **not heard by the agent; quality unjudged**). Real libraries need an account/purchase; none downloaded. Hezekiah v3: `out/hezekiah/hezekiah_piper_joe_with_music.mp4` (6 shots, 34.2 s, -18.3 LUFS, peak -3.4 dB). Owner-reported flow bug (17-20 s showed the first scene again) fixed by removing the reused prophet shot and extending the prayer shot.
- Test suite is now **92 passed** (was 77). Owner replaced `docs/QUALITY_GATES.md` with a v1.2: **not yet reconciled** with the traceability matrix. Evidence owner: the editor (per owner).
- Owner feedback on the Phase 0 clip: plays fine; transitions work but need adjustment; animation needs refinement; assets were generated 2D placeholders, real 3D assets to follow. Specific transition changes not yet specified.

## 2c. Phase 1 — desktop foundation (owner authorised 2026-11-14) — **PARTIAL (desktop shell deferred by the owner)**
Build `p1-20261114-b75743ce627a`; evidence `quality/evidence/p1-20261114-b75743ce627a/` (`GATE_CHECKLIST.md`, `PHASE_REPORT.md`, `DECISION_RECORD.md`, `e2e/`, `security/`, `crash-recovery/`).
- **Done and tested:** project store (versioned JSON + SQLite, atomic autosave, recovery, migrations, trash), media intake (8 formats, hash de-duplication, real decode, thumbnails/proxies, copy/link, relink),
  jobs with progress/cancel/restart recovery, secure loopback API with a strict page CSP, React/TypeScript UI (setup check, projects, media library, script autosave, native-picker support in code).
  **149 Python + 40 UI tests pass**; ruff, strict mypy, strict TypeScript, ESLint and the production build are clean. Verified end-to-end in a browser with the owner's real Hezekiah clips, including a hard kill + restart of the worker.
- **Desktop shell: DEFERRED (DR-103).** Rust and the Visual Studio C++ workload are installed, but Windows **Smart App Control blocks local Rust builds** (error 4551); the agent did not change that security setting.
  `apps/desktop/src-tauri/` is **never-compiled, unverified source**. No installer, no clean-machine test. The product is the **browser-hosted Studio** until this is resumed (ADR-0010).
- **Not done:** native pickers in a real window (typed paths in the browser), ≤10 s autosave-loss measurement, formal offline/network-monitor checks, first-time-user test, opening Phase 0 episode folders as Studio projects.
- **Defects found and fixed this phase:** bad import requests accepted then failed later → refused up front; health check ignored the configured FFmpeg; crashed imports left orphan files → cleaned on first open;
  recovery from a damaged project file could overwrite the good backup (caught on re-reading) → fixed + test; Windows folder-rename "Access is denied" (virus scanner) → bounded retry; several of my own tests were first too weak
  to catch the bug they claimed to guard → strengthened (mutation-checked). **One unexplained intermittent test failure** was seen once and did not recur in 8 targeted re-runs or 3 full-suite runs. **One full run took 62 min vs ~3 min** (all passed; cause unknown, kept in evidence).
- Open S0/S1 defects known: none. **G2 not claimed.** Owner sign-off for Phase 1 has **not** been requested.

## 3. Quality gates
Stamped on build `p0-20261114-fe27e05256e2` (source-tree hash; no git). Evidence: `quality/evidence/p0-20261114-fe27e05256e2/` (`GATE_CHECKLIST.md`, `DECISION_RECORD.md`, `signoff.md`). Approver: project owner, by written instruction, 2026-11-14.

| Gate | Status | Basis |
|---|---|---|
| **G0** Requirements baseline | **PASS** (exceptions E-1, E-2) | PRD v1.1 baselined; thresholds approved as written in QG v1.2; versioned schema 1.1.0 / `BUDGET_POLICY.md` / `PROJECT_LAYOUT.md`; roles + incident response in DR-002; evidence owner = the editor |
| **G1** Feasibility | **PASS — limited scope** | 85.6 s, 13-shot slice, reproducible (fresh run bit-identical), narration + still animation + MOCK/layered action; owner approved narrative/flow (quotes in DR); **no live provider tested (E-2)** |
| §7.1 mini-gate | **PASS** (exception DR-001) | 92 tests, ruff, mypy, ffprobe, creator review, $0 spend |
| G2–G5, RG, OG1–OG4 | **NOT RUN / NOT VALIDATED** | later phases / real-world evidence |
**Exceptions:** E-1 Hezekiah clip + SAPI voice licences unverified (private review only; Piper joe is CC0) · E-2 provider behaviour unverified, deferred to Phase 4, spend $0 · E-3 no git · E-4 owner-requested animation/transition refinement pending.
**Permitted claim:** technical concept feasible (limited scope). **Not permitted:** 15-minute workflow, cost, time saved, cadence, creative score, live-provider quality.

## 4. Tests executed (final run, this machine)
| Check | Command | Result |
|---|---|---|
| Unit (54) + integration with real FFmpeg (14) + faults (9) | `python -m pytest -v` | **77 passed**, 0 failed, 0 skipped, 71.7 s — `evidence/phase0/pytest_full.log` |
| Lint | `ruff check .` | pass |
| Types | `mypy` (strict, 16 source files) | pass |
| Full Phase 0 demo | `python -m storymotion_media phase0` | success; reports in `evidence/phase0/` |
| Reproducibility | 3 independent full renders + `scripts/determinism_probe.py` | identical SHA-256 `5a1d695d…`; 13/13 shots frame-identical across runs |
Fault IDs exercised (mock/fixture): F-03, F-04, F-07, F-11 (partial), F-12, F-13, F-14, F-17.
**NOT RUN:** F-01, F-02 (invalid key), F-05, F-06 (ledger), F-08, F-09 (real mid-render kill; only timeout-kill), F-10, F-15, F-16, F-18, OPS-06/07/08/09,
TIME-04 (preview vs export), TIME-05 (15-min sync), ANIM-01 10-shot sample, ANIM-06 action review, all QG-COST ledger tests.

## 5. Defects found and fixed during Phase 0 (all by running things, not by inspection)
| # | Severity (proposed) | Defect | Fix / guard |
|---|---|---|---|
| D1 | S2 | Full-length renders were **not reproducible**: `rotate=…:c=none` left unwritten pixels (23–204 of ~200 frames differed in 2 shots; a short test had passed) | `c=black@0`; RGBA-pinned overlay base; regression test is mutation-checked (fails if the bug returns) |
| D2 | S2 | A PNG header + garbage **passed ingest** (ffprobe reads headers only) | real decode check at ingest; `test_DATA04_*` |
| D3 | S3 | Validator flagged the planned `fadeblack` as "unplanned black" | black allowed only inside declared fades |
| D4 | S3 | JPEG sources leaked `yuvj420p`/full-range into the MP4 | normalised to limited-range BT.709 |
| D5 | S3 | Mock log contained a hard-coded `network_calls: 0` (an unmeasured claim) | removed; the real proof is a socket-blocking test |
Also: a fixture narration first came out 92.9 s (> 90 s) and was re-timed; my first test helper had a directory bug (test-only).

## 6. Known risks, limitations and blockers
**Open items for the owner (none block Phase 0, which has passed):** (a) record the Hezekiah clips' generating tool and licence, and any narration licence you rely on (E-1); (b) a written authorisation + quote + cap before *any* live provider test (`PROVIDER_FEASIBILITY_CHECKLIST.md`, E-2); (c) review the Hezekiah v3 cut (ambient bed); (d) authorise Phase 1.
**Limitations:** all art is procedural **placeholder**; narration is a Windows SAPI synthetic voice whose redistribution terms are
**unverified**; shot-09 (fish emerges/swallows) renders as a plain fallback pan with **no fish** and shot-07a uses a crude **MOCK** silhouette —
neither demonstrates action accuracy (ANIM-06 not run); only one machine/OS build tested; no clean-machine install; FFmpeg is a GPL build
(redistribution needs Phase 5 review); no git repository, so no commit hash is recorded; two encode generations per frame (quality
vs. caching trade-off, ADR-0003); no caching, progress UI, cancel/resume, waveform, music/SFX, project persistence.
**Environment gaps for Phase 1:** Rust/Cargo/Tauri CLI not installed (Node 24 is); WebView2 not checked.
**Open S0/S1 defects known to me:** none. (A phase-end self-assessment is not a QA sign-off.)

## 7. What is *not* claimed
No claim is made about O-01 (cadence), O-02 (≤$50/month — Phase 0 spent **$0**; the mock quote of 0.25 is an invented number), O-03 (≥50% time saving — no
baseline), O-04 (usable paid clips — no real provider), O-05 (creative ≥4/5 — no human review), or O-06. The render took ~77 s for 85.6 s of video on
an i7-12800H/31.6 GB machine; that is a **machine timing**, not a productivity measure.

## 8. Technical decisions (see `docs/architecture/`)
ADR-0001 Tauri shell + Python worker (shell deferred) · 0002 narration-as-clock/integer ms · 0003 deterministic FFmpeg render (+ the D1 finding) ·
0004 provider-neutral generation behind approval · 0005 segment cache (design only) · 0006 SQLite budget ledger (design only) · 0007 FFmpeg provisioning/licence.
**Deviations:** none from PRD/QG. Phase 0 is headless per the phased prompt. File layout simplified from the suggested tree (no `apps/`
yet). Both `docs/IMPLEMENTATION_STATUS.md` (requested) and `docs/implementation/PHASE_STATUS.md` (phased prompt) exist.

## 9. Next tasks (Phase 1 needs the owner's explicit go-ahead)
1. Owner: authorise Phase 1; decide whether to move segment caching earlier than Phase 3 (needs a decision record); record clip/voice licences (E-1).
2. `git init` + first commit so later evidence can cite a commit hash (E-3).
3. Phase 1: install Rust/Tauri (system change; ask first), build the shell, SQLite project index, import UI, atomic autosave, relinking, recovery tests. GPL licensing decision for bundling FFmpeg/Piper before packaging.
4. Phase 2 follow-ups already requested by the owner: transition/animation refinement on real 3D assets, layer pivot points.

## 10. Reproduce
See `README.md`. `python -m storymotion_media phase0` (≈3 min) → `out/`. Artifact checksums: `quality/evidence/p0-20261114-fe27e05256e2/exports/SHA256SUMS.txt`.
