# End-to-end observations — Phase 1 (manual, in the in-app browser against the REAL worker)

**Method:** `python -m storymotion_media serve --workspace out/e2e-ws` (real worker, real FFmpeg), UI built with `npm run build` and served by the worker,
driven in the in-app browser pane (Chromium). The owner's five Hezekiah clips were imported by path. This is a **manual session**; the screenshots live in the
tool-results store, not in this folder, and no video recording exists. Treat it as observation, not automated evidence (the automated evidence is `pytest.log`/`vitest.log`).

| Step | Observed |
|---|---|
| Open `http://127.0.0.1:<port>/#token=…` | Setup check listed 6 checks, all "Ready" (Python 3.12.10, FFmpeg 9.0.2, workspace writable, 134.8 GB free, Piper installed, offline mode) |
| Create project "Hezekiah - the added years" | Project created and opened; appears in the list |
| Import 5 clips (copy mode) + 1 non-existent path | 5 assets added with correct metadata: 1280×720/24 fps/10.0 s ×3, 1344×768/24 fps/5.2 s, 1926×1074/30 fps/5.0 s; each with a thumbnail and a proxy; the missing file reported by name ("was not found. Check the path, or that the drive is connected") |
| Import the same 5 again | "0 added, 5 already in the project" — duplicate detection by content |
| Library view | thumbnails render, badges `OK` / `Copied`, category selector (default "rendered video"), sizes shown |
| Script & notes tab: type 2 lines | status "Unsaved changes…" → "All changes saved" after the debounce; server shows revision 1 with the text |
| **Hard-kill the worker** (`taskkill /F /T`), start a new one on the same workspace | lock acquired immediately; project, script (rev 1), 5 assets all `ok`, 2 jobs `completed`, thumbnails served (HTTP 200 image/jpeg) |
| Phone width (375 px) | no horizontal scroll; buttons wrap; readable |
| Stop test worker | no worker process left running |

**Not observed / limits:** a missing-file relink in the live UI (covered by automated tests), a real narrow-screen keyboard-only pass, screen-reader use, light theme
(the pane rendered dark), and anything in a native window (no desktop shell exists). One tooling quirk: setting a textarea through the browser tool did not notify React; it is
not an app defect (typing/`input` events work, as the component tests and a second run confirmed).
