# Exporting

Exporting packages your work for someone or something else: a video editor, a collaborator, or an AI assistant. **Nothing is uploaded.** An export is just a new folder on your own computer.

This is different from the finished video. To make the MP4, use **Render draft** and **Render final (full size)** (see "Make your first video"). Use **Export** when you want the separate pieces.

## How to export

1. Open your project and click the **Storyboard** tab.
2. Scroll to the **Export** area, below **Render**.
3. Click one of the three buttons:

   | Button | What you get | Use it when |
   |---|---|---|
   | **Export independent assets** | Plain files that need no editor and no StoryMotion: every shot as its own clip of exactly the right length (each with a small `.json` description and a poster picture), the narration, music and final mix as WAV audio, your original pictures and clips copied unchanged, an `index.json` list, and a `SHA256SUMS.txt` file of checksums | You want to keep or hand over everything in a simple, future-proof form |
   | **Export for editing** | One clip per shot (with a few extra frames so a following transition has room), the narration and each music bed as WAV, `final_mix.wav`, and the timeline as `timeline.otio` and `timeline.edl` | You want to fine-tune the cut in a video editor |
   | **Export brief for AI models** | A folder `ai` with `handoff.json` (every scene, shot, time, setting and problem), still pictures of each shot and contact sheets, the script, the storyboard format description, and `README_FOR_MODELS.md` with instructions for the assistant | You want an AI assistant to review your video or suggest a better storyboard |

4. Watch the progress bar. You can click **Cancel export**. When it is done a green message says how many shots and files were written and how big the export is.
5. Under it, the list **Exports** shows every export you have made. Click **Show folder** next to one to open it in File Explorer.

> Screenshot to add: the Export area with the three buttons and one finished export listed.

Exports are written under your project, in a folder called `exports`. Every export is new: earlier exports are kept. An editing export also contains a `README.md` that explains what is inside.

## Using the editing export

- **DaVinci Resolve 18.5 or newer:** use **File, Import, Timeline...** and choose `timeline.otio` (it is in the `timeline` folder). The clips and audio are in the `shots` and `audio` folders next to it.
- **Premiere Pro and other editors:** import `timeline.edl`. An EDL carries video only, and "dip to black" transitions are written as dissolves. Bring the audio in from `audio\final_mix.wav` (or the separate narration and music files).
- No editor? Open the `shots` folder and join the clips in any editor you like. Each clip is already trimmed to size.

> **Honest note:** these timeline files follow the published formats but have **not yet been tested in any video editor**. Treat your first import as a test. If something does not line up, you still have every clip and the full audio, so you lose nothing. Please report what happened.
> One test did pass: rebuilding a video from the exported clips, the timeline and `final_mix.wav` alone gave pictures identical to the app's own final render.

## Using the AI brief

1. Click **Export brief for AI models** and then **Show folder**.
2. Give an AI assistant the contents of the `ai` folder, starting with `README_FOR_MODELS.md`.
3. The assistant may answer with a revised storyboard (a `.json` file). Bring it back with **Import scene plan (.json)** on the **Storyboard** tab. It is checked first, and you are asked before anything is replaced.

**Privacy:** the brief contains your script text and still frames of your pictures. If you give it to an outside service, that is your choice and your service's rules apply. StoryMotion itself sends nothing anywhere.

## Checking an independent-assets export

`SHA256SUMS.txt` lists a fingerprint (checksum) for each file, so you can prove later that nothing was altered. To check one file, open PowerShell in that folder (click the File Explorer address bar, type `powershell`, press **Enter**) and run `Get-FileHash .\index.json -Algorithm SHA256`. The result should match the line for that file in `SHA256SUMS.txt`.
