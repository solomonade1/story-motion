# PHASE_REPORT — Phase 0 (G0 + G1) — build `p0-20261114-fe27e05256e2`

**Verdicts:** G0 **PASS** (exceptions E-1, E-2) · G1 **PASS — limited scope** · §7.1 mini-gate **PASS** (exception DR-001). Decision record: `DECISION_RECORD.md`.
Checklist with evidence per criterion: `GATE_CHECKLIST.md`. Earlier detailed report: `docs/implementation/evidence/PHASE_0_REPORT.md`.

## Scope
Phase 0 headless proof of concept (PRD M0). Owner-authorised additions (DR-001): RENDERED clip shots, clip speed/trim, `scan`, plan `build`, Piper/SAPI narration,
audio bed mixing with ducking, clipping check, synthesised ambience.

## Implementation (paths)
`workers/media/storymotion_media/` (contracts, ingest, scan, plan, render, verify_output, preview, providers/*), `scripts/` (fixtures, narration, ambience, determinism probe),
`tests/{unit,integration,faults}`, `docs/` (PRD, Quality Gates v1.2, ADR-0001..0007, BUDGET_POLICY, PROJECT_LAYOUT, traceability, baseline protocol).

## Commands run on this build (this machine: Windows 11, i7-12800H, 31.6 GB; FFmpeg 9.0.2; Python 3.12.10)
| Command | Result | Log |
|---|---|---|
| `ruff check .` | pass | `unit-and-integration/ruff.log` |
| `mypy` (strict, 18 files) | pass | `unit-and-integration/mypy.log` |
| `pytest -v` | **92 passed**, 0 failed, 0 skipped, 149.9 s | `unit-and-integration/pytest.log` |
| `python -m storymotion_media phase0` | success; Jonah renders **identical SHA-256** to all earlier runs | `exports/phase0_run.log` |
| Hezekiah: `scan` → `build` → `render` → `volumedetect`/`ebur128` | success; verified (see below) | `exports/hezekiah_piper_joe_with_music.report.json` |

## Artifacts (SHA-256 in `exports/SHA256SUMS.txt`)
- `out/jonah_phase0_local_only.mp4` `5a1d695d…d805` — 85.625 s, 2055 frames
- `out/jonah_phase0_with_mock_clip.mp4` `1caf0db4…8a1a` — MOCK clip incorporated
- `out/hezekiah/hezekiah_piper_joe_with_music.mp4` `b681339b…2f8` — 34.2 s, 821 frames, 6 shots; audio mean −20.6 dB, peak −3.4 dB, −18.3 LUFS; A/V delta 6.6 ms; no unplanned black; no decode errors

## Checks that passed / failed / not run
Passed: see the table above and `GATE_CHECKLIST.md`. Failed: none on this build (defects found and fixed earlier are in `docs/IMPLEMENTATION_STATUS.md` §5).
**NOT RUN** (later gates, not failures): F-01, F-02, F-05, F-06, F-08, F-09 (real kill), F-10, F-15, F-16, F-18; OPS-06..09; TIME-04/05; ANIM-01 10-shot sample, ANIM-06; COST ledger tests; all of G2–G5, RG, OG1–OG4.

## Costs
No paid action. Actual spend **$0**. Free downloads only: Piper (GPL-3.0 tool) and four voice models whose licences were read first (CC0 / public domain). Mock provider charge records are invented values.

## Outcome contribution (no unmeasured claims)
The pipeline turns a plan + clips + narration + bed into a verified 1080p MP4 locally with no paid call, which *supports* lower cost and less manual assembly. **No** cost, time-saving, cadence, creative-score or reliability outcome is claimed.

## Blockers / risks / dependencies
E-1 clip and voice licences unverified (private review only) · E-2 provider behaviour unverified (Phase 4 dependency) · E-3 no git · E-4 refinement requested on animation/transitions · Rust/Tauri not installed ·
FFmpeg and Piper are GPL (bundling needs a licence decision before packaging) · no manual baseline yet (O-03 NOT VALIDATED).

## Next recommended phase (not started)
Phase 1 — desktop foundation, durable projects and media intake (needs the owner's explicit authorisation). Proposed with it: segment caching earlier than Phase 3 so GUI edits are fast (needs a decision record), plus `git init`.
