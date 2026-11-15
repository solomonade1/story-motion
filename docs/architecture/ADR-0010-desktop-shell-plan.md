# ADR-0010 — Desktop shell: Tauri 2 (DEFERRED by the owner; source unverified)

- **Status:** **Deferred** (owner decision, 2026-11-14, DR-103). Source written, **not compiled or run**; the build is blocked by Windows Smart App Control (see below). **Source:** PRD §10.2; ADR-0001; phased prompt Phase 1.

## What exists
`apps/desktop` is a React + TypeScript + Vite UI (strict TS, ESLint, 40 component tests) that runs in any browser against the local API (ADR-0009)
and was exercised end-to-end in the in-app browser against the real worker with the owner's Hezekiah clips. It is the exact UI the shell will host.

## State on 2026-11-14 (after the owner approved and carried out the installs)
- **Installed and detected:** Rust 1.100.0 (MSVC target), WebView2 157, Visual Studio Community 2026 with the "Desktop development with C++" workload (MSVC 14.50, `link.exe` present).
  (The first two attempts to install the standalone Build Tools failed with 1602 because the administrator prompt was not granted; the owner then installed Visual Studio itself, and the C++ workload was added to it.)
- **BLOCKED — Windows Smart App Control (state 1, ON):** `tauri build --debug --no-bundle` fails in 37 s with "An Application Control policy has blocked this file (os error 4551)" for every crate build script
  (`proc-macro2`, `typeid`, ...). Code Integrity events (3077/3118, "Smart App Control Block Details") show it refusing to let `cargo.exe` run the freshly compiled, unsigned build helpers. This blocks local Rust builds in general.
  Changing it is a Windows **security setting** the agent will not change; Smart App Control also **cannot be turned back on** once switched off without resetting Windows. Options for the owner: (a) turn it off, (b) build the shell
  on another machine or VM, (c) continue with the browser-hosted UI and defer the desktop shell.
- **Written but NEVER COMPILED OR RUN:** `apps/desktop/src-tauri/`. Treat it as unverified source.
- **Verified without the shell:** the page CSP header (worker-served, tested), native-picker UI behaviour (4 new UI tests), all earlier Phase 1 tests.

## Design of the shell as written (unverified)
Starts the worker (child process, stdin piped), reads the one-line ready JSON, opens a single window at `http://127.0.0.1:<port>/#token=…` whose navigation is restricted to exactly that origin,
grants that page only `dialog:allow-open`, stops the worker on exit (closing stdin → worker exits; hard kill after 5 s), and places the process tree in a Windows job object with kill-on-close so no orphan can survive a crash.
Smoke mode (`STORYMOTION_SMOKE_OUT=<file>`) starts everything, proves the page loaded and the authenticated health call works, writes a report and exits. Development layout only: it uses the repository's `.venv` and built UI;
bundling a private Python/FFmpeg/Piper is the packaging step and needs the GPL decision.

## To resume later
Decision needed on Smart App Control (turn it off, or build on another machine/VM). Once a build is possible: `cargo`-build the shell, run the smoke test, run it by hand, and refresh the Phase 1 evidence. Not claimed until then.

## Addendum 2026-11-15 — interim desktop window without compiling (owner asked for a desktop app without changing Smart App Control)
`python -m storymotion_media launch` (and `StoryMotion Studio.lnk` from `scripts/make_shortcut.ps1`) starts the worker and opens Microsoft Edge in app mode with a private profile in the workspace; closing the window stops the worker.
Smart App Control stays on: only Microsoft-signed Edge and the signed Python are run. A worker-served native chooser (`/api/pick`, Tk in a child process) replaces the Tauri dialog. **This does not replace the Tauri decision:** Tauri remains deferred;
if chosen later, its output must be code-signed to run on SAC machines. See `docs/DEPLOYMENT.md`. Real-window checks and two defects found by them (Edge hand-off ending the launcher early; a no-console note becoming a blocking message box; a needless 15 s wait after close) are fixed and have regression tests.
