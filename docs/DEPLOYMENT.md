# Deployment: what exists, what is pending

## Releasing (portable Windows bundle, added 2026-11-15)
`.github/workflows/release.yml` builds a **portable zip** on GitHub's `windows-latest`: checks (ruff, pytest minus FFmpeg tests, UI typecheck/lint/tests) -> UI build ->
`scripts/build_release.ps1` (embeddable Python 3.12.10 + tkinter copied from the matching full install, pydantic/Pillow wheels, worker source, built UI, checksum-pinned FFmpeg 9.0.2 GPL build)
-> smoke test using only the bundle's own Python (imports, `doctor`) -> zip + `.sha256`.
- **Publish:** `git tag v0.1.1 && git push origin v0.1.1` (for example; v0.1.0 already exists) creates a GitHub Release with the zip. **Dry run:** Actions -> *Release* -> *Run workflow* (zip is kept as a workflow artifact).
- **Local build:** `cd apps\desktop; npm ci; npm run build; cd ..\..; .\scripts\build_release.ps1 -Version 0.0.0-local` (needs the same Python version as `-PythonVersion`).
- **Layout contract:** the code finds the UI and FFmpeg relative to `app\` (`REPO = parents[3]`), and `python\python312._pth` adds `app\workers\media` to the path. Don't move folders without updating both.
- **Not signed, not an installer, not tested on a clean machine (OPS-08).** Users see SmartScreen warnings (documented in `packaging/USER_GUIDE.md`); Smart App Control machines may block the unsigned `ffmpeg.exe`. Signing is a paid owner decision.
- **GPL:** the bundle ships the GPL FFmpeg; `packaging/THIRD_PARTY_NOTICES.md` carries the notice/source offer. The licence review in ADR-0007 is still open.
- **Status:** **v0.1.0 is published** at https://github.com/solomonade1/story-motion/releases/latest (zip + `.sha256`). The workflow and build script have run on GitHub; the resulting zip has not been tested on a clean machine.
- **Docs:** end-user instructions are in the root `README.md` and the pages in `docs/guide/`. Those pages are the source of `packaging/USER_GUIDE.md` (the file shipped in the zip as `USER GUIDE.md`): after editing them run `.\scripts\make_user_guide.ps1`. Release steps and the private-repository (404) note are under "For developers and maintainers" in `README.md`.
- Piper voices (243 MB) are not bundled; narration falls back to the Windows voice.

## What you can run today (this machine, no security setting changed)
| How | What it is | Needs |
|---|---|---|
| **App window** — `StoryMotion Studio.lnk` / `python -m storymotion_media launch` | The Studio in its own Edge app window, worker started and stopped with it, native file chooser, warning before closing during a job | this project folder, its `.venv`, built UI (`apps\desktop\dist`), Microsoft Edge |
| Browser tab — `python -m storymotion_media serve` | Same UI in any browser; typed paths instead of the chooser | same, minus Edge |

Why this works with Smart App Control (SAC) on: SAC blocks **unsigned programs that we compile**. The app window uses Microsoft-signed Edge and the signed Python that already runs here;
no new executable is built or run. Verified on this machine: the shortcut starts the worker, opens a window titled "StoryMotion Studio", and closing it stops the worker in about 1.5 s.
Real-window verification covered startup, the page loading and calling the worker, graceful close, hard kill, and the no-console shortcut path. The native chooser was confirmed to open (then closed by the test), not used to import real files.

## What this is not
- Not an installer and not standalone: it runs from the project folder and `.venv`. Another PC would need Python, the dependencies, FFmpeg, Node (once, to build the screens) and Edge.
- Not a signed program: there is no `.exe` of ours. The taskbar shows Edge's icon for the window (the shortcut has our icon).
- Not tested on a clean machine (OPS-08), and the first-run flow on a fresh Windows account is untested.

## Pending for a real, shippable desktop product
1. **Decide the shell.** (a) Keep the Edge app window as the product shell (no compile step, needs Edge: preinstalled on Windows 11). (b) Compiled Tauri shell (`apps/desktop/src-tauri`, never compiled): needs a build
   machine where unsigned build helpers may run (another PC, a VM, or CI), **and** its output must be **code-signed** to run on a PC with SAC on — an unsigned CI-built `.exe` would be blocked here too. A signing certificate costs money and is the owner's decision.
2. **Packaging.** Bundle a private Python, the worker, the built UI, FFmpeg, ffprobe (and optionally Piper) into one folder or installer, so no `.venv`/Node is needed.
3. **Licences (GPL).** The FFmpeg build and Piper are GPL. Choose: ship a GPL-compliant bundle with source offer, switch to an LGPL FFmpeg build, or have the user install FFmpeg themselves (ADR-0007).
4. **Clean-machine test (OPS-08).** Install on a fresh Windows 11 x64 account/VM, first-run readiness checks, a guided test export, offline use.
5. **Product work still open:** G2 (real Jonah episode + review), Phase 3 (15-minute pipeline, caching, recovery), Phase 4 (cloud generation + budget controls), Phase 5 (hardening, pilot, release sign-off by the owner).
6. **Housekeeping:** no git repository yet; one intermittent test failure unexplained; project-data backup/update story; crash reporting policy (none now: nothing leaves the machine).
