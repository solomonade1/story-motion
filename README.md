# StoryMotion Studio

**[Download for Windows (v0.1.0)](https://github.com/solomonade1/story-motion/releases/download/v0.1.0/StoryMotion-Studio-0.1.0-win64.zip)** (about 207 MB) | [All downloads and release notes](https://github.com/solomonade1/story-motion/releases/latest) | [Checksum file](https://github.com/solomonade1/story-motion/releases/download/v0.1.0/StoryMotion-Studio-0.1.0-win64.zip.sha256)

## Contents
1. [What it is](#what-it-is)
2. [Download](#download)
3. [Install in 5 steps](#install-in-5-steps)
4. [First run walkthrough](#first-run-walkthrough)
5. [Make your first video](#make-your-first-video)
6. [Exporting](#exporting-for-editors-and-ai)
7. [Where your files go and backups](#where-your-files-go-and-backups)
8. [Update and uninstall](#update-and-uninstall)
9. [Troubleshooting](#troubleshooting)
10. [FAQ](#faq)
11. [System requirements](#system-requirements) and [Glossary](#glossary)
12. [For developers and maintainers](#for-developers-and-maintainers)

The full, step-by-step guide is split into pages you can read here, and the same text ships inside the download as `USER GUIDE.md`:
[Download and install](docs/guide/01-install.md) | [Make your first video](docs/guide/02-first-video.md) | [Exporting](docs/guide/03-exporting.md) | [Files, update, uninstall](docs/guide/04-files-update-uninstall.md) | [Troubleshooting](docs/guide/05-troubleshooting.md) | [FAQ and glossary](docs/guide/06-faq-glossary.md)

## What it is

StoryMotion Studio is a Windows program that turns a Bible-story script, your own illustrations and your own narration into an animated video. You arrange pictures into scenes and shots, choose camera moves and transitions, add music, check the timing against the narration, and render an MP4. Everything happens on your own computer: no account, no internet connection, nothing uploaded.

**Honest status:** this is an early release (v0.1.0). The core path (import, storyboard, draft render, final render, export) is built and covered by automated tests, and has been tried on the author's computer with placeholder and real sample material. It has **not yet been tried on a clean Windows computer by someone new**, it is **not code-signed** (Windows will show a warning the first time), and the exports for video editors have **not yet been opened in any editor**. AI-generated video clips are not part of this version. Test pictures in the project are placeholders; real creator assets are still needed to judge creative quality.

## Download

| You want | Get this |
|---|---|
| **The app** | [`StoryMotion-Studio-0.1.0-win64.zip`](https://github.com/solomonade1/story-motion/releases/download/v0.1.0/StoryMotion-Studio-0.1.0-win64.zip) (about 207 MB) |
| Proof the download is intact (optional) | [`StoryMotion-Studio-0.1.0-win64.zip.sha256`](https://github.com/solomonade1/story-motion/releases/download/v0.1.0/StoryMotion-Studio-0.1.0-win64.zip.sha256) |
| A newer version, or release notes | [Releases page](https://github.com/solomonade1/story-motion/releases/latest). Under **Assets**, pick the file ending in `-win64.zip`. Ignore "Source code" |

**Check the download (optional):** in File Explorer, open the folder with the zip, click the address bar, type `powershell`, press Enter, then run `Get-FileHash .\StoryMotion-Studio-0.1.0-win64.zip -Algorithm SHA256`. The result must equal the text at the start of the `.sha256` file. [More detail](docs/guide/01-install.md#check-your-download-optional-about-one-minute).

## Install in 5 steps

There is no installer. You unpack a folder and open it. No administrator rights are needed.

1. **Download** the zip. You should see it in your **Downloads** folder.
2. **Unblock it:** right-click the zip, **Properties**, tick **Unblock** at the bottom of the General tab (if you see it), **OK**.
3. **Extract everything:** right-click the zip, **Extract All...**, pick a short folder such as `C:\Apps` or **Documents**, **Extract**. You should see a folder `StoryMotion-Studio-0.1.0-win64` containing `StoryMotion Studio.vbs`, `USER GUIDE.md` and folders `python`, `app`, `licenses`.
4. **Start it:** open that folder and double-click **`StoryMotion Studio.vbs`**. After a few seconds a window titled **StoryMotion Studio** opens with **Welcome to StoryMotion Studio**. If Windows says **Windows protected your PC**, click **More info**, then **Run anyway**.
5. **Optional shortcut:** double-click **`Add Desktop Shortcut.vbs`**. A shortcut appears on your Desktop.

If something goes wrong, see [Troubleshooting](#troubleshooting). Full detail: [Download and install](docs/guide/01-install.md).

> Screenshot to add: the extracted folder in File Explorer showing StoryMotion Studio.vbs and the other items.

## First run walkthrough

1. The first screen is the **Setup check**. Wait for **Checking this computer...** to finish.
2. Each line is **Ready**, **Optional** or **Needs attention**. A line that needs attention shows **How to fix**. **Piper voice (optional)** normally says **Optional**, which is fine.
3. The bottom line shows **Workspace:** (normally `C:\Users\<you>\StoryMotion Studio`). Your projects are saved there.
4. Click **Continue**. You arrive at **Your projects**.
5. Close the window with the normal **X** when you are done. This also stops the app.

> Screenshot to add: the Setup check with all checks Ready.

## Make your first video

A short version of the full tutorial ([Make your first video](docs/guide/02-first-video.md)). You need a narration file (WAV, MP3 or AAC) and some pictures (PNG, JPG or WebP; 16:9, at least 1920 x 1080 is best). A script (`.txt` or `.md`), music and clips are optional.

1. **Create a project.** On **Your projects** click **New project**, type a name, click **Create**. Three tabs appear: **Media**, **Storyboard**, **Script & notes**.
2. **Import your files.** On **Media**, under **Add media**, leave **Copy into the project** selected, click **Browse...**, select your narration and pictures (Ctrl or Shift to select many), click **Import**. Watch **Activity**; every file should get a green **OK** in the **Library**.
3. **Import the script (optional).** On **Storyboard**, click **Import script (.txt, .md)**. Each heading (`#` in Markdown) or each blank-line paragraph (in text) becomes a scene. No shots are created yet. (**Import scene plan (.json)** loads a ready-made plan instead.)
4. **Choose the narration.** Open **Narration (the clock for every shot)** and pick your narration file. Shot times are measured on it.
5. **Arrange shots.** In each scene click **Add shot to this scene**, choose a **Picture**, set **Duration (ms)** (8000 means 8 seconds), choose an **Animation mode** (**STATIC** still picture, **CINEMATIC** slow camera move with a **Motion preset**, **LAYERED** moving cut-outs, **RENDERED** your own video clip), and a **Transition into this shot** (**Cut**, **Crossfade (dissolve)**, **Dip to black**). Optionally use **Add music or ambience** and the **Video fade-in/out** boxes. Everything saves automatically.
6. **Check timing.** Click **Close gaps and overlaps**, then **Fit last shot to narration end**. Read **Timeline checks**: clear every **Problem** and **Check** (use **Show** to jump to a shot). Rendering is refused until they are fixed. The goal is **No timing problems found.**
7. **Render a draft.** In **Render**, click **Render draft**. The result is a small 640 x 360 preview labelled **Draft proxy: not final quality**. Watch it, fix, repeat.
8. **Render the final.** Click **Render final (full size)**. Wait a few minutes. It is labelled **Final export**.
9. **Find the file.** In File Explorer open `C:\Users\<you>\StoryMotion Studio\projects`, open the most recently changed folder that starts with `p-`, then `renders`. The file ending in `-final.mp4` is your video. Copy it somewhere handy.

Not available in this version: AI-generated clips, sound effects per shot, waveform editing, depth effects. See the full guide for details.

> Screenshot to add: the Storyboard tab with scenes, the timeline and Timeline checks showing "No timing problems found."
> Screenshot to add: the Render area with a finished final render in the player.

## Exporting for editors and AI

The **Export** area (Storyboard tab, below **Render**) writes a new folder on your computer. Nothing is uploaded.

| Button | What it gives you |
|---|---|
| **Export independent assets** | Plain files that need no editor and no StoryMotion: each shot as its own exact-length clip with a `.json` description and a poster, narration/music/final mix as WAV, your original pictures and clips unchanged, `index.json` and `SHA256SUMS.txt` |
| **Export for editing** | One clip per shot, narration and music as WAV, `final_mix.wav`, and the timeline as `timeline.otio` (DaVinci Resolve 18.5 or newer) and `timeline.edl` (Premiere and others; video only, dips become dissolves) |
| **Export brief for AI models** | An `ai` folder: `handoff.json`, still frames and contact sheets, the script, the storyboard format and `README_FOR_MODELS.md`. A model's revised storyboard comes back with **Import scene plan (.json)** |

Click **Show folder** beside an export in the **Exports** list to open it. **The timeline files have not been tested in any editor yet**: treat your first import as a test. A rebuild from the exported clips, timeline and mix alone did match the app's own final render frame for frame. More: [Exporting](docs/guide/03-exporting.md).

## Where your files go and backups

- Your work lives in the **workspace**: `C:\Users\<you>\StoryMotion Studio` (set the environment variable `STORYMOTION_WORKSPACE` to use another folder). Each project is a folder `projects\p-<code>` containing `renders` (your videos) and `exports`.
- The app folder is separate. Deleting or replacing it never touches your projects.
- **Delete** moves a project to **Trash**; **Restore** brings it back; **Delete forever...** erases it (you must type its name).
- **Back up** by closing the app and copying the whole `StoryMotion Studio` folder to a USB drive or cloud-synced folder.
- Your original pictures and audio are never changed or moved.

More: [Where your files go, backups, update, uninstall](docs/guide/04-files-update-uninstall.md).

## Update and uninstall

- **Update:** back up the workspace, download the new zip, extract it to a **new** folder, start the new `StoryMotion Studio.vbs`. Your projects carry over. Delete the old folder once you are happy.
- **Uninstall:** close the app, delete the app folder and the Desktop shortcut. To also remove your projects (permanent), delete `C:\Users\<you>\StoryMotion Studio`.

## Troubleshooting

First try **`Run with console (troubleshooting).bat`** in the app folder: it keeps the messages on screen.

| Symptom | Cause | Fix |
|---|---|---|
| **Windows protected your PC** | The app is not code-signed | **More info**, then **Run anyway** (only for the official download) |
| Repeated "Do you want to run this file?" warnings | The zip is "blocked" because it came from the internet | Delete the extracted folder; right-click the zip, **Properties**, **Unblock**, **OK**; extract again |
| Blocked by an application control policy / Smart App Control | Windows 11 allows only signed programs; bundled `ffmpeg.exe` is unsigned | See [Smart App Control](docs/guide/05-troubleshooting.md#smart-app-control-blocked-a-file). Try another computer or ask your administrator |
| Antivirus removed `ffmpeg.exe` | False alarm on an unsigned download | Restore it from Quarantine, add the app folder as an exception |
| Double-click does nothing, or Windows Script Host is disabled | Extracted incorrectly, or a policy blocks `.vbs` | Extract fully first; otherwise use the troubleshooting `.bat` |
| **Microsoft Edge was not found** | Edge is missing | Install Edge and start again |
| **StoryMotion is already open on this workspace** | Another window, or a hidden leftover | Close it; or **Task Manager**, **Details**, end `pythonw.exe`; or restart |
| Blank window, or **This page needs to be opened from the StoryMotion app** | Opened in a normal browser, or still starting | Wait 10 seconds; start from `StoryMotion Studio.vbs` |
| **Setup check**: FFmpeg **Needs attention** | `ffmpeg.exe` is missing or blocked | Extract again to a fresh folder; see antivirus and Smart App Control lines |
| Import message `... is not supported` | Wrong file type | Use PNG, JPG, WebP, WAV, MP3, AAC, MP4 or MOV |
| File shows **Missing** or **Changed** | Moved or edited after import | **Relink...** or **Find moved files in a folder...** |
| **The storyboard is not ready to render** | Timing problems | Fix **Timeline checks**; use **Close gaps and overlaps** and **Fit last shot to narration end** |
| **The last render failed** | Disk full, antivirus, or a missing file | Read the reason, free space, fix, render again |
| No sound or no voice | No narration chosen, or none provided | Choose a narration file; the Studio does not generate voices, so bring your own |
| Not enough disk space | Under 5 GB free | Delete old drafts and exports, empty **Trash**, or move the workspace |
| Path or "file name too long" errors | Very long folder path | Extract to a short path such as `C:\Apps` |

Full table with more cases and what to include when you ask for help: [Troubleshooting](docs/guide/05-troubleshooting.md).

## FAQ

- **Is it private?** Yes. Nothing is uploaded and the app makes no network connections. No accounts, no tracking.
- **Does it work offline?** Completely. You need the internet only to download the zip.
- **Does it cost anything?** No. This version has no paid or cloud features.
- **Do I need to install Python or FFmpeg?** No. Everything is inside the folder.
- **Why the Windows warning?** The app is not code-signed (signing is a paid certificate). The warning is about that missing signature.
- **Licences?** Includes FFmpeg 9.0.2 (GPL v3), Python and other free software. See `licenses\THIRD_PARTY_NOTICES.md` inside the app folder, or [packaging/THIRD_PARTY_NOTICES.md](packaging/THIRD_PARTY_NOTICES.md).
- **Which files?** Pictures PNG, JPG, WebP; audio WAV, MP3, AAC; video MP4, MOV.

More: [FAQ and glossary](docs/guide/06-faq-glossary.md).

## System requirements

| | You need |
|---|---|
| Windows | Windows 10 or 11, 64-bit |
| Browser part | Microsoft Edge (included with Windows 10 and 11) |
| Disk space | About 1.5 GB for the app, plus several GB for projects and videos. The Setup check warns under 5 GB free |
| Memory and screen | Not formally tested; 8 GB of memory and a screen of 1280 x 800 or more is a sensible start |
| Internet | Only to download. The app never connects |
| Not needed | Administrator rights, Python, FFmpeg, accounts, a terminal |

## Glossary

| Word | Meaning |
|---|---|
| **Scene** | A part of the story that holds one or more shots |
| **Shot** | One continuous piece of video: a picture or clip shown for a set time with an optional camera move and transition |
| **Storyboard** | The plan of scenes and shots, timed against the narration |
| **Narration clock** | The timeline set by your narration file. Every shot time is milliseconds on it |
| **Draft render** | A small, quick (640 x 360) preview with a DRAFT badge, to check timing and motion |
| **Final render** | The full-size finished MP4 |
| **Proxy preview** | A smaller stand-in used for quick previews (drafts and the **Scrub** picture); not for judging quality |
| **Workspace** | The folder that holds all your projects (`C:\Users\<you>\StoryMotion Studio`) |

More terms: [glossary](docs/guide/06-faq-glossary.md#glossary).

---

# For developers and maintainers

Everything below is for people who build or release the app. End users do not need it.

## Project status (technical)
Local-first tool that turns a Bible-story script, existing illustrations and narration into an animated video.
Read `docs/IMPLEMENTATION_STATUS.md` first: it says what is implemented, what is tested, and what is **not** proven. The original headless Phase 0 pipeline is still here; the Studio UI (Phase 1) and storyboard/rendering (Phase 2) sit on top of it. The compiled Tauri shell is deferred (see the "Desktop app" section below).

> Fixtures are **placeholders**: procedurally drawn art (clearly labelled on every image) and a synthetic
> Windows-SAPI voice. They prove the pipeline, not creative quality. Real creator assets are still required.

## Maintainer notes: release link, private repository, cutting a release
- **Release downloads:** https://github.com/solomonade1/story-motion/releases/latest . Asset names are `StoryMotion-Studio-<version>-win64.zip` and `...zip.sha256`. When you cut a new version, update the version in the download links at the top of this README and in `docs/guide/01-install.md`.
- **If the release link shows a 404** for people who are not signed in, the repository (or the release) is probably **private**. Anonymous visitors cannot see private releases. Fix: make the repository public (GitHub: Settings, General, Danger Zone, Change visibility), or add the person as a collaborator (Settings, Collaborators). When last checked the repository was public and v0.1.0 was published with the zip and checksum.
- **Cut a release:** commit on `main`, then `git tag v0.1.1` and `git push origin v0.1.1`. The workflow `.github/workflows/release.yml` runs the checks, builds the portable zip with `scripts/build_release.ps1`, smoke-tests it and publishes a GitHub Release with the zip and `.sha256`. A dry run (no release): GitHub, Actions, **Release**, **Run workflow**.
- **User guide:** the pages in `docs/guide/` are the source. Before tagging, run `.\scripts\make_user_guide.ps1`; it rebuilds `packaging/USER_GUIDE.md`, which `build_release.ps1` copies into the zip as `USER GUIDE.md`. The guide pages must not contain relative links (the zip has no repository) and the script refuses if they do.
- **Not yet done:** a test on a clean Windows machine (OPS-08), and a Smart App Control test. Details: `docs/DEPLOYMENT.md`.

## Repository layout
```
docs/PRD.md, docs/QUALITY_GATES.md      authoritative v1.1 copies (the unversioned files in the root are older v1.0)
docs/IMPLEMENTATION_STATUS.md           living status, gates, risks, next tasks
docs/implementation/                    traceability, phase status, baseline protocol, provider checklist, evidence/
docs/architecture/ADR-*.md              decisions
docs/guide/                             end-user guide pages (source of packaging/USER_GUIDE.md)
workers/media/storymotion_media/        Python worker (contracts, ingest, render, preview, providers/)
packages/contracts/                     exported JSON Schema for the scene manifest
tests/{unit,integration,faults}/        automated checks;  tests/fixtures/jonah/  placeholder Jonah slice
scripts/make_fixtures.py                regenerates fixtures (Windows only: uses the SAPI voice)
scripts/build_release.ps1               assembles the portable Windows zip (CI runs it)
scripts/make_user_guide.ps1             builds packaging/USER_GUIDE.md from docs/guide/
packaging/                              files that go into the zip (user guide, notices, launcher templates)
```

## Setup (Windows 11, PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
```
FFmpeg/ffprobe is required (>= 7; a build with libx264). Either put them on `PATH`, set `STORYMOTION_FFMPEG_DIR`
to their folder, or place them in `tools\ffmpeg\bin`. The dev machine used the pinned build described in
`docs/architecture/ADR-0007-ffmpeg-provisioning.md` (GPL build: the portable zip now ships it with a notice; the licence review in ADR-0007 is still open).

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
The portable zip (above) is the way end users get the Studio. The compiled desktop shell source exists (`apps/desktop/src-tauri`) but could not be built on the development PC: Windows Smart App Control blocks Rust build helpers (see `docs/architecture/ADR-0010-desktop-shell-plan.md`).
From source, the worker serves the UI on your own computer only:
```powershell
cd apps\desktop; npm install; npm run build; cd ..\..
.venv\Scripts\python -m storymotion_media serve --workspace .\workspace   # prints {"url": "http://127.0.0.1:PORT/#token=..."}
```
Open that URL in a browser (the `#token=` part is a private session key; keep it to yourself). The worker listens on 127.0.0.1 only,
makes no network connections, and stops when you press Ctrl+C. Close it before opening the same workspace again (one worker per workspace).
UI development with hot reload: `npm run dev` in `apps\desktop`, start the worker with `--origin http://127.0.0.1:5173`, then open
`http://127.0.0.1:5173/#token=<token>&api=http://127.0.0.1:<port>`. UI checks: `npm run typecheck`, `npm run lint`, `npm test`.
Your projects live in the workspace folder (default `~/StoryMotion Studio`); deleted projects go to its `.trash` folder first.

## Desktop app from source (no install, no security setting changed)
Run the Studio in its own window, like a desktop program:
```powershell
cd apps\desktop; npm install; npm run build; cd ..\..        # once: build the screens
.\scripts\make_shortcut.ps1                                    # once: creates "StoryMotion Studio.lnk" here (add -Desktop or -StartMenu to pin it)
```
Double-click **StoryMotion Studio** (or `python -m storymotion_media launch`). It starts the local worker and opens Microsoft Edge in a chromeless *app window*
with its **own browser profile** inside your workspace (no tabs, no address bar, nothing shared with your normal Edge). **Closing the window stops the worker**;
if an import or render is running, the window asks first. The file chooser ("Browse…") is a normal Windows dialog. If something is wrong (Edge missing, screens
not built, already open) you get a message box instead of silence.
This works with Windows Smart App Control left **on**: it only runs Microsoft-signed Edge and the signed Python already used here. From source it needs this project folder and its `.venv`; the portable zip bundles its own Python.
The compiled Tauri shell (ADR-0010) stays deferred; see `docs/DEPLOYMENT.md`.

## Export for video editors and AI models (technical detail)
On the Storyboard tab, **Export** writes a folder under the project (`exports/x-...-full` or `-brief`; independent assets use `-assets`); nothing is uploaded.
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
