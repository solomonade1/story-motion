# Phase 1 checklist — build `p1-20261114-b75743ce627a`

Vocabulary: PASS (automated or observed evidence) · PARTIAL · NOT RUN · BLOCKED. Test names are in `unit-and-integration/pytest.log` and `vitest.log`.

## QG-DATA (project integrity and media handling)
| Test | Result | Evidence |
|---|---|---|
| DATA-01 create/rename/open/duplicate/archive/delete; reopened data matches | **PASS** | `test_studio_store.py` (lifecycle, duplicate independence, trash/restore/purge), `test_studio_api.py::test_project_lifecycle_over_http`, `Projects.test.tsx` (8) |
| DATA-02 kill during autosave; recover; ≤10 s of edits lost | **PARTIAL** | 20 random hard kills of a real saving process never damaged `project.json` and never lost an acknowledged save; deterministic test that the live file is never opened for writing (mutation-checked). **The ≤10 s bound is NOT measured** (UI/app crash not tested; shell does not exist). Autosave debounce is 0.8 s |
| DATA-03 move/delete one source; reopen and relink | **PASS** | `test_studio_assets.py::test_move_then_relink…`, `…modified_source…`, `…deleted_project_copy…`; unaffected assets stay `ok` |
| DATA-04 import supported formats and corrupt samples | **PASS** | all 8 formats imported (PNG, JPEG, WebP, WAV, MP3, AAC, MP4, MOV); corrupt: junk PNG, mid-file-corrupt PNG, mid-file-corrupt MP3, truncated MP4, empty, wrong type, folder, missing, relative path — each an actionable error, batch continues. Video damaged mid-file imports with a **warning** (limit recorded in ADR-0008) |
| DATA-05 identical bytes twice | **PASS** | duplicate recognised by hash, one copy on disk |
| DATA-06 thumbnails/proxies/category | **PASS** | every valid import has a thumbnail and a decodable proxy; 360p H.264 video proxy verified |
| DATA-07 open an old-schema project after migration | **PASS** (infrastructure + 1 real migration) | `test_migration_from_prerelease_layout…`: original preserved, repeatable, newer major refused unchanged |

## Fault-injection (QG §7) — Phase 1 relevant
F-08 kill during manifest save: **PASS** (project.json, real kills + simulated rename failure) · F-09 kill worker during FFmpeg work: **PARTIAL** (kill during import/preview transcode; not a
render) · F-10 disk full: **PARTIAL — simulated only** (ENOSPC injected) · F-11 source moved/modified: **PASS** · F-12 malformed input: **PASS** (API JSON/body limits) · F-13 hostile names/paths:
**PASS** (import + API traversal) · F-17 FFmpeg missing: **PASS** (readiness check "needs attention" + 503 with fix; API still answers) · F-01 no internet: **by design**, not measured with a network
monitor (**NOT RUN** as a test). F-02..F-07, F-14..F-16, F-18: later phases.

## QG-TRUST / OPS slices
TRUST-01 secrets: no secrets exist this phase; token not in responses/logs (**PASS**, test). TRUST-02 traversal/hostile/remote reads: **PASS** for API + import (mutation-checked; layered defence).
TRUST-03 uploads/network: no network code exists; **not verified with a network monitor → NOT RUN**. TRUST-04 first-time-user flow in ≤30 min: **NOT RUN** (needs a real user).
OPS-05 kill app/provider job + reopen: **PARTIAL** (worker kill + restart recovered; no provider jobs yet). OPS-07 offline journey: **NOT RUN** formally. OPS-08 clean-machine install: **BLOCKED** (no installer).

## Phase 1 deliverables (phased prompt)
| Deliverable | Status |
|---|---|
| Windows-first **Tauri 2** shell | **DEFERRED by the owner (DR-103).** Toolchain installed; build blocked by Windows Smart App Control (os error 4551); source never compiled |
| React + TypeScript UI: create/open/rename/duplicate/archive/delete, asset library, import, relink, first-run setup, progress/cancel, empty/error states, offline note | **DONE** (`apps/desktop`, 36 UI tests, manual e2e) |
| Supervised Python worker, narrow secure IPC | **DONE** as loopback API with session token (ADR-0009); shell supervision pending |
| Versioned project JSON + SQLite, autosave, atomic writes, migrations, restart recovery | **DONE** (ADR-0008) |
| Import with ffprobe, hashes, thumbnails/proxies, duplicate detection, corrupt errors, relinking | **DONE** |
| Validate 20+ assets and a narration file import | **PARTIAL**: 8 formats and 5 real clips; **a 20+ asset batch was not run** |
| Windows desktop dev/build smoke | **NOT RUN — unverified** (shell deferred); the browser-hosted UI was exercised on Windows 11 |
| Timeline | correctly **not built** (Phase 2) |

**Verdict: Phase 1 = PARTIAL — the desktop shell/installer were deferred by the owner (DR-103).** Backend, media intake and UI are complete and tested. **G2 is not claimed** (it needs Phase 2 anyway).
