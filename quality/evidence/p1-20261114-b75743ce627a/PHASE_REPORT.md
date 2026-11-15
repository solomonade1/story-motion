# PHASE_REPORT — Phase 1 (desktop foundation, durable projects, media intake) — build `p1-20261114-b75743ce627a`

**Verdict: PARTIAL — desktop shell deferred by the owner (DR-103).** The backend, media intake and UI are built and tested. The **Tauri desktop shell and installer are NOT built**: the toolchain is installed but Windows Smart App Control blocks Rust
builds on this PC (error 4551). **G2 is not claimed.** Checklist per criterion: `GATE_CHECKLIST.md`. Decision log: ADR-0008, -0009, -0010.

## Scope
Phase 1 only (owner authorisation: "Yes, start Phase 1", 2026-11-14). No timeline, no cloud provider, no budget ledger. Phase 0 render commands are unchanged.

## Implementation (paths)
`workers/media/storymotion_media/studio/` — `store.py` (workspace, project documents, lifecycle), `atomic.py`, `migrations.py`, `assets.py` (intake, previews, relink, cleanup), `jobs.py`, `api.py`
(loopback API), `locking.py`, `paths.py`, `errors.py`; CLI `serve`. `apps/desktop/` — React + TypeScript UI (`src/*.tsx`, 40 tests; native-picker support). Docs: ADR-0008/0009/0010, README "The Studio", `docs/PROJECT_LAYOUT.md` v1.1.0-phase1.

## Commands run on this build (Windows 11, i7-12800H, 31.6 GB; Python 3.12.10; Node 24.12.0; FFmpeg 9.0.2)
| Command | Result | Log |
|---|---|---|
| `pytest -v --durations=15` (149 collected: 75 unit, 61 integration, 13 fault-injection) | **149 passed**, 0 failed, 0 skipped, **2 min 51 s** | `unit-and-integration/pytest.log` |
| the same suite, an earlier run on identical sources | 149 passed, 0 failed — but wall time **62 min 10 s**. Per-test timings were not recorded and the cause is **unknown** (most likely the PC sleeping or being busy: the test that prints its own timing reported a normal 5.8 s). Kept, not hidden | `unit-and-integration/pytest-run-A-62min-anomaly.log` |
| `ruff check .` · `mypy` (strict, 28 files) | clean · clean | `ruff.log`, `mypy.log` |
| `npm run typecheck` (strict) · `npm run lint` | clean · clean (run on the same UI sources; only a Python test file was added after) | `ts-typecheck.log`, `eslint.log` |
| `npm test` (Vitest, 7 files) | **40 passed** | `vitest.log` |
| `npm run build` | built; JS 173.0 kB (55.4 kB gzip) | `vite-build.log`, `SHA256SUMS.txt` |
| Manual end-to-end in the in-app browser against the real worker | see observations (incl. hard kill + restart) | `e2e/E2E_OBSERVATIONS.md` |

## Quality of the tests (not just their count)
Key guards were **mutation-checked** — the behaviour was deliberately broken and the test had to fail: duplicate detection, the real-decode check (audio), relink hash check, cancel cleanup,
atomic-save invariant, token check, Host check, Origin check, query-token restriction, path-traversal (both layers), autosave debounce, failed-save text retention, conflict stop, typed-name purge.
Four tests were found too weak on first attempt (they still passed with the bug) and were rewritten. Real disk-full/read-only conditions are **simulated**, and crash tests prove survival of
**project files**, not of a desktop application.

## Measurements (this machine; not product claims)
Import of 24 files (11 JPEG + 3 PNG + 7 PNG/WebP generated + the 85.6 s narration WAV, with thumbnails and proxies): **≈10 s**. Worker restart after a hard kill: immediate (lock released by the OS).

## Costs
No paid action; **$0**. No network connection is made by any Phase 1 code path (not verified with a network monitor). npm packages installed for the UI: 2 runtime (React, React-DOM) + 15 dev tools.

## Outcome contribution (no unmeasured claims)
Gives the creator a place to hold a story's script and media safely (recoverable projects, de-duplicated and previewed assets, flagged missing files). Whether this reduces effort (O-03) or improves
reliability (O-06) is **NOT measured**; no baseline exists.

## Blockers / risks / dependencies
1. **Desktop shell deferred**: Smart App Control blocks Rust builds; resuming needs an owner decision (turn it off, or build elsewhere). 2. Bundling FFmpeg (GPL build) and Piper (GPL-3) needs a licensing decision before an installer.
3. Typed file paths until native pickers exist. 4. One unexplained intermittent test failure seen once in development (not reproduced in 8 targeted re-runs / 3 full runs). 5. Single-writer assumption (enforced by a lock) —
no multi-user. 6. Phase 0 episode folders are not yet openable as Studio projects; rendering is still CLI-driven.

## Next recommended step (not started)
Phase 2 (script/storyboard editor, timeline, cinematic motion) on the owner's separate authorisation. The desktop shell resumes whenever the Smart App Control question is settled.
