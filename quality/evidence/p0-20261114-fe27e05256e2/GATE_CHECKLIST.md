# Gate checklist — G0, G1 and the §7.1 mini-gate — build `p0-20261114-fe27e05256e2`

Result vocabulary: PASS · PASS-WITH-EXCEPTION (see DECISION_RECORD DR-004) · NOT RUN. Nothing is marked PASS without a file or command below.
Paths are relative to this folder unless they start with `docs/` or `projects/`.

## G0 — Requirements baseline (QG §8)
| Criterion | Result | Evidence |
|---|---|---|
| PRD v1.1 in repo, immutable baseline identified | **PASS** | `docs/PRD.md` SHA-256 `6e5363538c53…b2751` (`exports/SHA256SUMS.txt`) |
| Every P0 FR has ≥1 named test and an evidence owner | **PASS** (mapping) | `docs/implementation/REQUIREMENTS_TRACEABILITY.md` (48 rows → QG test IDs); evidence owner = the editor (DR-002). Row *results* stay honestly "Not started / Partial" |
| [QA proposal] thresholds approved or modified | **PASS** | approved as written in v1.2 (DR-002); `docs/QUALITY_GATES.md` SHA-256 `12d363ff…4856` |
| Scene-plan schema, budget policy, storage layout, renderer contract versioned | **PASS** | schema 1.1.0 (`packages/contracts/scene-manifest.schema.json`), `docs/BUDGET_POLICY.md` 0.1.0, `docs/PROJECT_LAYOUT.md` 1.0.0-phase0, `PROCESSOR_VERSION` phase0-1 |
| Fixture licensing checked; provider pricing source and quote TTL documented | **PASS-WITH-EXCEPTION (E-1, E-2)** | Jonah fixtures: own CC0 (`tests/fixtures/jonah/PROVENANCE.json`); Piper joe CC0 (MODEL_CARD); SAPI voice and Hezekiah clips **unverified**; pricing source: none authorised; TTL: MOCK 300 s, real TTL deferred (`docs/BUDGET_POLICY.md`) |
| S0/S1 definitions, incident response, approval roles agreed | **PASS** | QG §2.3; DR-002 |

**G0 verdict: PASS (with E-1, E-2).**

## G1 — Feasibility (QG §8, PRD M0)
| Criterion | Result | Evidence |
|---|---|---|
| 60–90 s Jonah slice with narration, still animation, ≥1 advanced action representation | **PASS** (technical) | `exports/jonah_phase0_local_only.report.json`, `exports/ffprobe/jonah_phase0_local_only.json`: 85.625 s, H.264 1920×1080 24 fps, 2055 frames, AAC 48 kHz. Pan/zoom/static + layered rocking ship + incorporated **MOCK** generated clip (`exports/jonah_phase0_with_mock_clip.report.json`, `exports/mock_generation_log.json`) |
| 8–15 shots, visually different but coherent | **PASS** | 13 shots; owner: "The video play fine" (DR basis 1) |
| FFmpeg command, assets, settings, artifact reproducible | **PASS** | fresh `python -m storymotion_media phase0`: identical SHA-256 to every earlier run (`exports/phase0_run.log`); `scripts/determinism_probe.py` (13/13 shots frame-identical) |
| Cloud provider test (if used) | **N/A — not used** | owner deferred; all provider behaviour is MOCK (E-2) |
| Creator approves narrative clarity; limitations needing fallbacks marked | **PASS** (limited scope) | owner statements (DR basis 1 and 3); limitations: shot-09 fish absent (fallback pan), mock throw crude, animation refinement pending (E-4) — `creative-reviews/CREATIVE_REVIEW.md` |

**G1 verdict: PASS — limited scope** (DR-003). Permitted claim: *technical concept feasible (limited scope)*.
**Not permitted:** any claim about the 15-minute workflow, cost, time saved, cadence, or provider quality (O-01..O-07 remain NOT VALIDATED).

## §7.1 Development-phase mini-gate
| Item | Result | Evidence |
|---|---|---|
| Scope explicit, traced to FR-IDs; no unapproved later-phase work | **PASS-WITH-EXCEPTION** | traceability matrix; later-phase work recorded as owner-authorised (DR-001) |
| Real workflow / reproducible command demonstrates the objective | **PASS** | `python -m storymotion_media phase0`; Hezekiah: `scan` → `build` → `render` |
| Automated checks run; commands and failures recorded | **PASS** | `unit-and-integration/pytest.log` (**92 passed**, 0 failed/skipped), `ruff.log` (clean), `mypy.log` (strict, clean). Defects found and fixed are listed in `docs/IMPLEMENTATION_STATUS.md` §5 |
| Negative tests exercised; future-phase gates stay NOT TESTED | **PASS** | `tests/faults/`, provider failure suite; later gates not marked FAIL |
| Media inspected with ffprobe and a creator review | **PASS** | `exports/ffprobe/*.json` (Jonah ×2, Hezekiah); owner review (DR basis 1, 3) |
| No paid provider call without approval and envelope; mocks identified | **PASS** | no live provider exists in code; mock outputs labelled; spend **$0**; free downloads only: Piper tool and 4 CC0/public-domain voice models (licences read first) |
| Gaps, risks, measurements, next-phase dependencies documented | **PASS** | `PHASE_REPORT.md`, `docs/IMPLEMENTATION_STATUS.md` |
| Evidence under `quality/evidence/<build-id>/`; approval decision recorded | **PASS** | this folder; `DECISION_RECORD.md`; `signoff.md` |

**Mini-gate verdict: PASS (with exception DR-001).**
