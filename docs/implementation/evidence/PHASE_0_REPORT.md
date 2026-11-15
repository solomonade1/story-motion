# StoryMotion Phase 0 — Completion & Quality Evidence

## Scope and git revision
- **Phase / PRD milestone / gate:** Phase 0 / M0 / G0 + G1 (OG1 protocol only). **G0: NOT PASSED (awaiting owner). G1: NOT PASSED — technical slice met, creative PENDING, live-provider BLOCKED.**
- **Branch / commit:** none — the directory is not a git repository (documented limitation).
- **Environment:** Windows 11 Pro 10.0.26300; Intel i7-12800H (14C/20T), 31.6 GB RAM; Python 3.12.10; pydantic 2.14.3, Pillow 13.0.0, pytest 9.2.0, ruff 0.17.5, mypy 2.4.1;
  FFmpeg/ffprobe 9.0.2 `full_build` (Gyan.dev, GPL-3.0; zip SHA-256 `759d0a98…06f6b` verified); no network used by any test or render.

## Delivered working behaviors
| Behavior | Code path | PRD FR-ID | QG-ID | Outcome | Evidence |
|---|---|---|---|---|---|
| Manifest contract + field-located validation | `workers/media/storymotion_media/contracts.py` | FR-SCRIPT-002/004, FR-TIME-004, FR-PROJ-004 (partial) | TIME-01, F-12 | O-03 | `tests/unit/test_contracts.py` (22 tests) |
| Asset verify: containment, hash, decode, metadata | `ingest.py` | FR-MEDIA-001/002/006, FR-PROJ-003 (partial) | DATA-03/04, F-11/13 | O-03 | `tests/faults/test_faults.py` |
| STATIC/CINEMATIC/LAYERED render, cut/crossfade/fadeblack | `render.py` | FR-ANIM-001/002/004, FR-TIME-003, FR-RENDER-001/002/003 (partial) | ANIM-01 (mini), OPS-01 | O-02, O-05 | `tests/integration/test_render_pipeline.py`; `phase0/jonah_phase0_*.report.json` |
| Verified publish (probe, exact frames, decode, black scan, atomic) | `verify_output.py`, `render.py` | FR-RENDER-005 | OPS-01/02/03 | O-05, O-06 | `phase0/ffprobe_*.json` |
| Draft preview + labelled page | `preview.py` | FR-TIME-005 (partial) | TIME-07 (partial) | O-03 | `out/preview/preview.html` |
| Provider-neutral boundary + fake provider + safe client flow | `providers/*` | FR-AI-001..005, FR-BUD-002/005/007 (partial, **MOCK**) | COST-01/02/05/06, F-03/04/07/14 | O-02, O-04 | `tests/unit/test_fake_provider.py`, `phase0/mock_generation_log.json` |
| Clip incorporation without a paid call | `generation_demo.py` | FR-ANIM-003/004 (partial) | ANIM-03 | O-04 | `phase0/jonah_phase0_with_mock_clip.report.json` |
| Baseline protocol, CSV templates, provider checklist | `docs/implementation/` | — | OG1 (protocol only) | O-03 | files exist; **no data** |

## Tests performed
| Command/test | Expected | Actual | PASS/FAIL/NOT RUN | Evidence path |
|---|---|---|---|---|
| `python -m pytest -v` (54 unit, 14 integration w/ real FFmpeg, 9 fault) | all pass | 77 passed, 0 failed, 0 skipped, 71.7 s | **PASS** | `phase0/pytest_full.log` |
| `ruff check .` / `mypy` (strict) | clean | clean / "no issues in 16 files" | **PASS** | (console) |
| `python -m storymotion_media phase0` | valid MP4s + reports | success; 77.3 s and 82.5 s renders | **PASS** | `phase0/phase0_run.log` |
| Reproducibility: 3 independent full renders | same SHA-256 | all `5a1d695d…d805` | **PASS** (same machine) | `phase0/SHA256SUMS.txt` |
| `scripts/determinism_probe.py 3` | 0 differing frames | 13/13 shots identical | **PASS** | (console) |
| Mutation check of the D1 regression test | fails when bug restored | failed as expected | **PASS** | `ADR-0003` |
| Preview vs export cut deviation (TIME-04), 15-min sync (TIME-05), ANIM-01 10-shot sample, ANIM-06, all ledger/COST-03/04/08, OPS-06..09, F-01/02/05/06/08/09/10/15/16/18 | — | not executed | **NOT RUN** | — |
| Live provider quote/approval/quality | — | no authorisation | **BLOCKED** | `PROVIDER_FEASIBILITY_CHECKLIST.md` |
| Creator review of narrative clarity | — | no human review | **PENDING** | — |

## Media and correctness
- **Input fixtures and licenses:** `tests/fixtures/jonah/` — 11 JPEG backgrounds + 3 PNG layers drawn by `scripts/make_fixtures.py` (CC0, own work; every image carries a visible "PLACEHOLDER ART" tag); narration = Windows SAPI "Microsoft David Desktop" reading an original paraphrase of the Book of Jonah — **redistribution terms unverified**. Provenance: `tests/fixtures/jonah/PROVENANCE.json`.
- **Rendered artifacts (git-ignored, in `out/`):**
  - `jonah_phase0_local_only.mp4` — SHA-256 `5a1d695d1f1ea057757c9b70cd84e14af750eda7d193c7747afcf064ed71d805`, 14,459,427 B (2 GENERATIVE shots rendered as declared local fallback)
  - `jonah_phase0_with_mock_clip.mp4` — SHA-256 `1caf0db4aa49cdc3e4bb30895003c53c41c30625d8b552b5d526b0ca96c58a1a`, 13,884,819 B (shot-07a uses the **MOCK** clip; shot-09 still falls back)
  - `preview/preview_draft.mp4` + `preview.html` — 640×360 proxy
- **ffprobe (independent run, `phase0/ffprobe_jonah_phase0_local_only.json`):** H.264 High, 1920×1080, yuv420p (tv), 24/1 fps, **2055 frames** decoded, 85.625 s; AAC LC, 48 kHz, stereo, 85.612 s; container mov/mp4. 13 shots, 85,606 ms narration.
- **Preview/export timing and sync:** end-to-end A/V duration delta 12.8 ms; audio vs narration 6.2 ms; start offset 0 ms; max cut quantisation error 20.67 ms (≤ ½ frame). Only the *end* is measured; mid-file sync and preview-vs-export deviation are **not** measured (TIME-04/05 not run). Full decode with `-xerror`: no errors. Black frames: one segment 63.71–64.04 s, inside the declared `fadeblack` into shot-10 (planned).
- **Render time (this machine):** 77.3 s (segments 33.4 s, compose 33.1 s, verify 9.3 s) for the local-only render.
- **Human creative-review status:** **NOT DONE.** Observations from a contact sheet (`phase0/contact_sheet_with_mock_clip.jpg`) by the agent, not a review: shots differ visually and cuts/fades behave; the layered ship rocks; **shot-09 shows no fish** (fallback pan) and the mock "throw" is a tumbling silhouette that does not clearly cross a railing.

## Cloud and costs
- **Provider and model:** MOCK only (`mock-video`, "fake-i2v-v0"). No external endpoint exists in the code; a test blocks sockets and the flow still succeeds.
- **Approved request reference / quote time:** harness-simulated approval (`approvalSimulatedByHarness: true`) of a MOCK quote; **not** a human approval.
- **Reserved / actual billed amount:** **$0.00 actual.** The mock provider's invented charge record is 250,000 micro-USD ("$0.25") and is not a real price.
- **Reconciliation / remaining cap:** n/a — no ledger exists yet (Phase 4).

## Risks, decisions and next steps
- **Open S0/S1/S2/S3 defects:** S0 none, S1 none, S2 none known (two S2s found and fixed: D1 non-reproducible render, D2 corrupt image accepted). S3 open: placeholder-only visuals; shot-09 no depiction; untested formats (WebP/MP3/AAC/MOV, 30 fps); no git history; GPL FFmpeg redistribution. (Severities are my proposals.)
- **Important ADRs / departures:** ADR-0001..0007; no departure from PRD/QG. Phase 0 is headless per the phased prompt, so Tauri/React/SQLite are not built and Rust is not installed.
- **Tests or user validation still needed:** owner approval of thresholds; real Jonah assets + narration and a creator review; the live-provider checklist if/when authorised; manual baseline per `BASELINE_PROTOCOL.md`.
- **Gate verdict and why:** G0 **NOT PASSED** (owner approvals/roles outstanding). G1 **NOT PASSED** — all *technical* criteria met on placeholder fixtures; creator approval PENDING; provider test BLOCKED. Technical feasibility of the local pipeline is **supported**, product feasibility is **unproven**.
- **Next recommended phase (not started):** Phase 1 — desktop foundation, durable projects and media intake — after owner review.
