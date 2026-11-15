# StoryMotion Studio

Local-first tool that turns a Bible-story script, existing illustrations and narration into an animated video.
**Current state: Phase 0 (technical feasibility), headless.** There is no desktop UI yet (Phase 1).
Read `docs/IMPLEMENTATION_STATUS.md` first: it says what is implemented, what is tested, and what is **not** proven.

> Fixtures are **placeholders**: procedurally drawn art (clearly labelled on every image) and a synthetic
> Windows-SAPI voice. They prove the pipeline, not creative quality. Real creator assets are still required.

## Download and use (no setup)
Download `StoryMotion-Studio-<version>-win64.zip` from the **Releases** page, extract it, double-click `StoryMotion Studio.vbs`. Full instructions: [`packaging/USER_GUIDE.md`](packaging/USER_GUIDE.md) (also shipped inside the zip).
Maintainers: see "Releasing" in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Layout
```
docs/PRD.md, docs/QUALITY_GATES.md      authoritative v1.1 copies (the unversioned files in the root are older v1.0)
docs/IMPLEMENTATION_STATUS.md           living status, gates, risks, next tasks
docs/implementation/                    traceability, phase status, baseline protocol, provider checklist, evidence/
docs/architecture/ADR-*.md              decisions
workers/media/storymotion_media/        Python worker (contracts, ingest, render, preview, providers/)
packages/contracts/                     exported JSON Schema for the scene manifest
tests/{unit,integration,faults}/        automated checks;  tests/fixtures/jonah/  placeholder Jonah slice
scripts/make_fixtures.py                regenerates fixtures (Windows only: uses the SAPI voice)
```

## Setup (Windows 11, PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```
FFmpeg/ffprobe is required (>= 7; a build with libx264). Either put them on `PATH`, set `STORYMOTION_FFMPEG_DIR`
to their folder, or place them in `tools\ffmpeg\bin`. The dev machine used the pinned build described in
`docs/architecture/ADR-0007-ffmpeg-provisioning.md` (GPL build: dev use only; redistribution needs review).

```powershell
.venv\Scripts\python -m storymotion_media doctor     # verifies ffmpeg, ffprobe, filters, encoders
```

## Run the Phase 0 demo (reproducible; no network, no paid calls)
```powershell
.venv\Scripts\python -m storymotion_media phase0     # ~3-4 min; writes to .\out
```
Produces in `out/`:
- `jonah_phase0_local_only.mp4` – cloud-free render; GENERATIVE shots use their declared local fallback.
- `jonah_phase0_with_mock_clip.mp4` – same, with one **MOCK** "generated" clip incorporated via the fake provider.
- `*.report.json` – commands (paths redacted), per-shot timings, ffprobe verification, fallbacks, asset hashes.
- `mock_generation_log.json` – quote → approval → submit → poll → verified download (MOCK, no network).
- `preview/preview.html` – draft proxy preview (open in a browser); labelled as proxy fidelity.

Individual commands:
```powershell
.venv\Scripts\python -m storymotion_media validate tests\fixtures\jonah\manifest.json --check-assets
.venv\Scripts\python -m storymotion_media render tests\fixtures\jonah\manifest.json out\x.mp4 [--draft] [--overwrite]
.venv\Scripts\python -m storymotion_media preview tests\fixtures\jonah\manifest.json out\preview
.venv\Scripts\python -m storymotion_media scan projects\jonah-real   # register your dropped assets (see docs\BLENDER_HANDOFF.md)
.venv\Scripts\python -m storymotion_media schema packages\contracts\scene-manifest.schema.json
```

## The Studio (Phase 1): projects + media library in a browser window
No installer yet. The desktop shell source exists (`apps/desktop/src-tauri`) but could not be built on the development PC: Windows Smart App Control blocks Rust build helpers (see `docs/architecture/ADR-0010-desktop-shell-plan.md`).
For now the worker serves the UI on your own computer only:
```powershell
cd apps\desktop; npm install; npm run build; cd ..\..
.venv\Scripts\python -m storymotion_media serve --workspace .\workspace   # prints {"url": "http://127.0.0.1:PORT/#token=..."}
```
Open that URL in a browser (the `#token=` part is a private session key; keep it to yourself). The worker listens on 127.0.0.1 only,
makes no network connections, and stops when you press Ctrl+C. Close it before opening the same workspace again (one worker per workspace).
UI development with hot reload: `npm run dev` in `apps\desktop`, start the worker with `--origin http://127.0.0.1:5173`, then open
`http://127.0.0.1:5173/#token=<token>&api=http://127.0.0.1:<port>`. UI checks: `npm run typecheck`, `npm run lint`, `npm test`.
Your projects live in the workspace folder (default `~/StoryMotion Studio`); deleted projects go to its `.trash` folder first.

## Desktop app (no install, no security setting changed)
Run the Studio in its own window, like a desktop program:
```powershell
cd apps\desktop; npm install; npm run build; cd ..\..        # once: build the screens
.\scripts\make_shortcut.ps1                                    # once: creates "StoryMotion Studio.lnk" here (add -Desktop or -StartMenu to pin it)
```
Double-click **StoryMotion Studio** (or `python -m storymotion_media launch`). It starts the local worker and opens Microsoft Edge in a chromeless *app window*
with its **own browser profile** inside your workspace (no tabs, no address bar, nothing shared with your normal Edge). **Closing the window stops the worker**;
if an import or render is running, the window asks first. The file chooser ("Browse…") is a normal Windows dialog. If something is wrong (Edge missing, screens
not built, already open) you get a message box instead of silence.
This works with Windows Smart App Control left **on**: it only runs Microsoft-signed Edge and the signed Python already used here. It is not a standalone installer:
it needs this project folder and its `.venv`. The compiled Tauri shell (ADR-0010) stays deferred; see `docs/DEPLOYMENT.md`.

## Export for video editors and AI models
On the Storyboard tab, **Export** writes a folder under the project (`exports/x-...-full` or `-brief`); nothing is uploaded.
- **Export independent assets:** plain files that need no editor and no StoryMotion: every shot as its own exact-length clip with a `.json` description and poster, narration/music/final mix as WAV, your original pictures and clips copied unchanged, `index.json`, and `SHA256SUMS.txt` (check with `sha256sum -c SHA256SUMS.txt`).
- **Export for editing:** one clip per shot (with a few extra frames for the following transition), the narration and each music bed as WAV, `final_mix.wav`, and the timeline as
  `timeline.otio` (OpenTimelineIO: DaVinci Resolve 18.5+) and `timeline.edl` (CMX3600: Premiere and others; video only, dips written as dissolves).
- **Export brief for AI models:** `ai/handoff.json` (every scene, shot, time, setting, asset and diagnostic, plus what a model may change), keyframe stills and contact sheets, the script,
  the storyboard JSON Schema and `README_FOR_MODELS.md`. A model's revised storyboard comes back through **Import scene plan** (same asset ids, validated before anything renders).
Checked on your Hezekiah cut: re-assembling a video from the exported clips, `timeline.otio` and `final_mix.wav` alone gives **pixel-identical frames** to the project's own final render.
**Not tested in any editor yet** (no editor is installed here): treat the first Resolve/Premiere import as a test. See `docs/implementation/PHASE_STATUS.md`.

## Phase 2: storyboard, motion and rendering in the Studio
The Studio's **Storyboard** tab imports a script/plan, edits scenes and shots (pictures or your clips, camera presets, transitions, music bed, fades),
checks timing against the narration, and renders drafts and finals. See `docs/JONAH_PRODUCTION.md` for the Jonah production runbook.
```powershell
.venv\Scripts\python -m storymotion_media timing-check .\workspace\projects\<p-id>\renders\<r-id>-final.mp4   # cut timing vs plan (TIME-04)
.venv\Scripts\python scripts\jonah_rehearsal.py      # placeholder end-to-end rehearsal (not G2 evidence)
```

## Test and quality checks
```powershell
.venv\Scripts\python -m pytest -q                    # unit + integration + faults (integration needs FFmpeg)
.venv\Scripts\python -m ruff check .
.venv\Scripts\python -m mypy
```
A test that cannot run (e.g. no FFmpeg) is reported as skipped = **NOT RUN**, never as passed.

## Safety defaults
No API keys, uploads or network calls exist in this phase. The fake provider cannot reach the network (a test
blocks sockets to prove it). Source assets are never modified; outputs are never overwritten without `--overwrite`.
