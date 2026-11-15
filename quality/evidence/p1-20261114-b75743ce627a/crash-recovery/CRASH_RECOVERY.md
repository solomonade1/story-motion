# Crash and recovery evidence — Phase 1 (build `p1-20261114-b75743ce627a`)

Tests: `tests/faults/test_studio_crash.py` (real processes, hard-killed with `taskkill /F /T`), `tests/unit/test_studio_store.py`, `tests/integration/test_studio_assets.py`.

| Scenario | What was done | Result |
|---|---|---|
| Kill during autosave | a worker saving a ~900 KB document in a loop, killed at a random moment (20 iterations, seeded) then reopened by a fresh process | `project.json` never damaged; every acknowledged save present (revision ∈ {last acknowledged, +1}); index consistent |
| Atomic-save invariant | spy on `Path.open` / `copyfile`: the live `project.json` is **never** opened for writing | holds; **mutation-checked** (an in-place write fails this test deterministically; the random kill test alone did *not* catch it — the write window is tiny — which is why the invariant test exists) |
| Rename/save fails mid-way (simulated ENOSPC) | final rename raises | previous file intact, message "Your previous version is untouched", no temp file left |
| Damaged `project.json` | truncated file | restored from `.bak`; damaged copy kept as `project.json.corrupt-<stamp>`; **good backup not overwritten** (bug found by re-reading, fixed, tested) |
| Both files damaged | garbage in both | clear message; nothing modified |
| Kill during import | worker killed while a 30 s 1080p video is copying/transcoding | project document intact; no half-written asset rows; orphan files removed on next open; the import can be run again |
| Kill the whole API server mid-job | server tree killed during an import job, then restarted | job shown as `interrupted` with a plain explanation; assets and files consistent; **no orphans**; new import completes; the workspace lock was released by the OS |
| Second worker on the same workspace | started while the first runs | refused: "StoryMotion is already open on this workspace…" |
| Live, manual (in-app browser, real clips) | worker killed after an autosave, restarted | project, script rev 1, 5 assets, jobs and thumbnails all intact (see `e2e/E2E_OBSERVATIONS.md`) |

## Limits
Disk-full/read-only are **simulated**. The kill tests exercise the **worker and its files**; a desktop shell does not exist, so *application* crash recovery and the QG DATA-02 "≤ 10 s of committed UI edits lost" bound are **not measured**
(autosave debounce is 0.8 s; the UI also saves when a panel closes). Power-loss durability depends on the OS honouring `fsync`; not tested.
