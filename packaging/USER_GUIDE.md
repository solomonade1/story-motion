# StoryMotion Studio — User Guide (portable Windows download)

StoryMotion Studio turns your script, illustrations and narration into an animated video. Everything runs **on your own computer**:
nothing is uploaded and the app makes no network connections.

## What you need
- Windows 10 or 11, 64-bit
- **Microsoft Edge** (already installed on Windows 10/11). The Studio opens in its own Edge-based app window.
- About 1.5 GB free disk space, plus room for your projects and rendered videos
- No Python, Node, FFmpeg or administrator rights needed — they are all inside this folder.

## Install
1. Download `StoryMotion-Studio-<version>-win64.zip` from the project's **Releases** page.
2. *(Optional)* Check the download: in PowerShell, `Get-FileHash .\StoryMotion-Studio-<version>-win64.zip` must match the `.sha256` file.
3. **Right-click the zip → Extract All…** to a normal folder such as `C:\Apps` or `Documents`.
   Do **not** run it from inside the zip, and avoid very long folder paths. No admin rights are needed.
4. Open the extracted folder and double-click **`StoryMotion Studio.vbs`**.
5. *(Optional)* Double-click **`Add Desktop Shortcut.vbs`** to put a shortcut on your Desktop.

### If Windows warns you
This download is not code-signed, so Windows may show warnings the first time:
- **"Windows protected your PC" (SmartScreen):** choose *More info → Run anyway*. Only do this for a download from the official Releases page.
- **Files downloaded from the internet are "blocked":** right-click the **zip** before extracting → *Properties* → tick **Unblock** → OK, then extract.
- **Smart App Control = On:** it blocks unsigned programs. This bundle runs Microsoft-signed Edge and Windows Script Host and python.org's signed `python.exe`,
  but the bundled FFmpeg is not signed by Microsoft. If a block appears, see Troubleshooting.

## Using the Studio
- **Projects:** create a project, then import your pictures, narration, music and clips with **Browse…** (a normal Windows file chooser).
- **Storyboard:** import a script/plan, adjust scenes and shots (camera moves, transitions, music, fades), check timing against the narration, then render a **draft** and a **final**.
- **Export:** *Export independent assets* (plain clips + audio + checksums), *Export for editing* (clips + `timeline.otio` / `timeline.edl` for DaVinci Resolve / Premiere),
  or *Export brief for AI models*.
- **Closing the window stops the app.** If an import or render is running you are asked first.

### Where your work is stored
In **`C:\Users\<you>\StoryMotion Studio`** (your user profile). Deleting the app folder does **not** delete your projects.
Deleted projects go to the `.trash` folder inside it first. To keep projects elsewhere, set the environment variable `STORYMOTION_WORKSPACE` to that folder before launching.
Only one StoryMotion window can use a workspace at a time.

### Updating
Download the newer zip, extract it to a **new** folder, and use that one. Your projects are in your profile folder (above) and carry over. Keep the old folder until you have checked the new version.

### Uninstalling
Delete the app folder and the Desktop shortcut. Optionally delete `C:\Users\<you>\StoryMotion Studio` (this **permanently removes your projects**).

## Troubleshooting
| Symptom | What to do |
|---|---|
| Nothing happens when double-clicking | Run **`Run with console (troubleshooting).bat`**; it prints the reason. Make sure you extracted the zip first. |
| "Microsoft Edge was not found" | Install Edge, or set the `STORYMOTION_BROWSER` environment variable to a Chromium browser's `.exe` path. |
| "already open on this workspace" | Close the other StoryMotion window (check Task Manager for `pythonw.exe` if you cannot see one), then retry. |
| Windows says an application control policy blocked a file | Smart App Control blocks the unsigned `ffmpeg.exe`. Either install FFmpeg yourself from a trusted source and set `STORYMOTION_FFMPEG_DIR` to its folder, or ask your administrator. Do not turn security features off unless you understand the trade-off (Smart App Control cannot be re-enabled without resetting Windows). |
| Antivirus quarantines `ffmpeg.exe` | Restore it and add the app folder as an exception, or use your own FFmpeg as above. |
| File chooser does not open | Type the file path into the field instead. |
| Narration voice | The built-in Windows voice is used. The optional Piper voices are not in this download. |

When asking for help, include `VERSION.txt` and the output of the troubleshooting `.bat`. Do not share the `#token=…` part of any URL.

## What is inside the folder
```
StoryMotion Studio.vbs            start the app (no console window)
Add Desktop Shortcut.vbs          create a Desktop shortcut
Run with console (troubleshooting).bat
python\                           private Python runtime (does not touch any Python you have installed)
app\                              the Studio (worker, screens) and FFmpeg
licenses\                         third-party licences (FFmpeg is GPL v3, see THIRD_PARTY_NOTICES.md)
VERSION.txt
```
