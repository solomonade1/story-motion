# Troubleshooting

Find the line that matches what you see, then follow the fix. Nothing here needs a terminal unless it says so.

## First, the troubleshooting launcher

If the app will not start or you do not know why, double-click **`Run with console (troubleshooting).bat`** in the app folder. It opens a black window, runs a self-check, starts the app and **keeps the messages on screen**. Read the last lines: they usually say what is wrong. Close the black window when you are done (press any key when asked).

## Starting the app

| What you see | Likely cause | What to do |
|---|---|---|
| Nothing happens when I double-click `StoryMotion Studio.vbs` | You are running it from inside the zip, or the files were not fully extracted | Close any windows from the zip. Right-click the zip, **Extract All...**, then start it from the extracted folder. If still nothing, use the troubleshooting launcher |
| A text editor opens, or a message says **Windows Script Host access is disabled** | A work or school computer policy (or a setting) blocks `.vbs` files | Use **`Run with console (troubleshooting).bat`** instead. It does the same job and shows a black window while the app runs. Ask your administrator if the `.bat` is blocked too |
| **Windows protected your PC** (SmartScreen) | The download is not code-signed, so Windows does not know the publisher | Click **More info**, then **Run anyway**. Only do this for files from the official Releases page |
| "Do you want to run this file?" or "Open File - Security Warning", repeating for many files | The zip was downloaded from the internet and Windows marked it as blocked | Delete the extracted folder. Right-click the **zip**, choose **Properties**, tick **Unblock** (bottom of the General tab), click **OK**, then extract again |
| A message that an **application control policy** or **Smart App Control** blocked a file, or "A policy has blocked this file" | Smart App Control (Windows 11) only runs programs signed by trusted publishers. The bundled video tool `ffmpeg.exe` is not signed | See "Smart App Control blocked a file" below |
| My antivirus deleted or quarantined `ffmpeg.exe` (or says the app is a threat) | Antivirus programs are often wary of unsigned downloads, and FFmpeg is a common false alarm | Restore the file from the antivirus **Quarantine**, and add the app folder as an exception. If you are unsure, download the zip again and compare its checksum (see "Download and install"). Never turn off your antivirus entirely |
| **Microsoft Edge was not found. Install Edge, or set STORYMOTION_BROWSER...** | Edge is missing or was removed | Install Microsoft Edge from Microsoft's website, then start the app again. (Advanced: set the environment variable `STORYMOTION_BROWSER` to the full path of another Chromium-based browser such as Chrome) |
| **StoryMotion is already open on this workspace. Close the other window first...** | Another StoryMotion window (or a hidden leftover from a crash) is using your projects | Look in the taskbar for an open StoryMotion window and close it. If there is none: press **Ctrl + Shift + Esc** to open **Task Manager**, open the **Details** tab, find `pythonw.exe` (or `python.exe`) from the StoryMotion folder, right-click it and choose **End task**, then try again. A restart of the computer also clears it |
| **The app screens are not built yet...** | The folder is incomplete (for example the zip was only partly extracted) | Delete the folder and extract the zip again, completely |
| **The window closed almost at once** | Edge started and stopped immediately | Run the troubleshooting launcher and read the messages. Close other Edge windows and try again |
| A white or blank window | The app is still starting, or the page could not load | Wait 10 seconds. If still blank, close the window and start again. If it repeats, use the troubleshooting launcher |
| The window says **This page needs to be opened from the StoryMotion app...** | You opened a saved address in a normal browser | Close that tab and start the app from `StoryMotion Studio.vbs` or the Desktop shortcut. The address contains a private key and only works for the session that made it |
| **Setup check** shows **Needs attention** for **FFmpeg + ffprobe** | The video tool is missing or was removed by antivirus or a policy | Extract the zip again into a fresh folder. If the warning stays, see the antivirus and Smart App Control lines |
| **Setup check** shows **Needs attention** for **Workspace folder** | The projects folder cannot be written to | Check that the folder shown is not read-only, or choose another with `STORYMOTION_WORKSPACE` (see "Where your files go") |
| **Setup check** shows **Needs attention** or a warning for **Free disk space** | Less than 5 GB is free (it fails below 1 GB) | Free up space on the drive that holds your workspace. See "Disk space" below |
| **Piper voice (optional)** shows **Optional** | The extra voice add-on is not included | Nothing. This is normal and does not affect you |

### Smart App Control blocked a file

Smart App Control is an optional Windows 11 protection. When it is **On**, it blocks programs that are not signed. The app's own launcher parts (Microsoft Edge, Windows Script Host and the standard Python) are signed. The bundled `ffmpeg.exe` is not signed by Microsoft, so on a computer with Smart App Control **On**, it may be blocked. This has **not yet been tested on a computer with Smart App Control turned on**, so if you see this, we would like to hear about it.

Your options, safest first:

1. Try on another computer that does not have Smart App Control on.
2. Ask your administrator or IT person.
3. Switch Smart App Control to **Evaluation** or **Off** under **Windows Security, App and browser control, Smart App Control settings**. **Be aware:** once turned off it cannot be turned on again without reinstalling or resetting Windows. This guide does not recommend it unless you understand that trade-off.

## Using the app

| What you see | Likely cause | What to do |
|---|---|---|
| There is no **Browse...** button | The app was opened in a normal browser, not its own window | Start it from `StoryMotion Studio.vbs`. Or type the full file path in the box instead |
| **Browse...** does nothing or the file window seems hidden | The Windows file window opened behind the app | Press **Alt + Tab** to find it, or type the path in the box |
| An import says `'name' was not found. Check the path, or that the drive is connected.` | The path is wrong, or the file is on a drive that is not plugged in | Check the path, connect the drive, and try again |
| `...is a .xyz file, which is not supported. Supported: PNG, JPG, WebP images; WAV, MP3, AAC audio; MP4, MOV video.` | The file type is not supported | Convert the file (for example `.m4a` to `.mp3`) and import the converted copy |
| `...is empty (0 bytes)` or a message saying the file looks damaged or unreadable | The file did not copy or save properly | Get the file again or re-export it from where it was made |
| `...could not be copied into the project... The disk may be full or read-only` | No room on the disk | Free up disk space (see below) |
| A file shows **Missing** or **Changed** | It was moved, renamed or edited after import | Click **Relink...** on it, or **Find moved files in a folder...** at the top |
| **Could not save** | The disk is full or protected, or the project folder is unavailable | Your text stays on screen. Free space or fix access, then click **Try again** |
| **This project was changed somewhere else** | The same project was changed from another window or copy | Click **Reload project** (or **Reload storyboard**). Only one window should use a workspace |
| The Timeline shows **Problem** or **Check** items and **Render draft** says "The storyboard is not ready to render: ..." | Shots have gaps, overlaps or missing pictures, or no narration is chosen | Read the message: it names what to fix. Use **Show** on each item, and the buttons **Close gaps and overlaps** and **Fit last shot to narration end** |
| `Your latest edits could not be saved, so nothing was rendered` | The last edit could not be saved | Fix the save problem first (see **Could not save**) |
| **The last render failed: ...** | See the next lines | Read the reason shown. Common reasons: disk full, antivirus blocking `ffmpeg.exe`, a picture or clip that went missing. Fix it and render again. Nothing half-finished is kept |
| **The last render was interrupted when the app closed** | The window was closed or the computer shut down during a render | Render again |
| The render is very slow | Long video, many layers, slow or busy computer | Close other programs and wait. A 3 to 5 minute final often takes a few minutes. A draft is much quicker |
| The draft or final has no sound | No narration is chosen, or the narration file is silent | On the **Storyboard** tab, check **Narration (the clock for every shot)** and that the file really contains audio. Also check your computer's volume and the player's speaker button |
| I want a narrator voice but the app has none | StoryMotion does not record or generate narration inside the Studio window | Record your narration, or create it with another tool, save it as WAV, MP3 or AAC and import it. The Windows voice and the optional Piper voices are used only by developer tools, and Piper is not in this download |
| Music is too loud or too quiet | Level not set | Change **Level (dB)** (more negative is quieter), and **Lower under narration by (dB)** on the music track. Re-render a draft to listen |
| The video has black frames or ends too early | A gap between shots, or the last shot stops before the narration does | Click **Close gaps and overlaps**, then **Fit last shot to narration end**, then check **Timeline checks** |
| The window asks before closing | An import, render or export is running | Wait for it to finish, or choose to leave if you are sure. Unfinished work is discarded safely |

## Disk space

Videos, previews and exports are large. The **Setup check** warns when the drive holding your workspace has less than 5 GB free.

To make room:
1. Delete old drafts you no longer need from `...\projects\p-...\renders` (File Explorer, with the app closed).
2. Delete exports you no longer need from `...\projects\p-...\exports`.
3. Empty the project **Trash** (**Delete forever...**), only for projects you really do not want.
4. Move the whole workspace to a bigger drive (see "Where your files go").
5. Use **Link to the original** instead of **Copy into the project** for very large clips.

## Very long folder paths

Windows can fail on very long folder paths (about 260 characters). If extraction or the app complains about a path or "file name too long", extract the app to a short place such as `C:\Apps` and keep your project and file names reasonably short.

## When you need help

Please send:
- The text of `VERSION.txt` from the app folder.
- What you clicked and the exact words of any message (or a screenshot).
- The messages shown by `Run with console (troubleshooting).bat`.
- Your Windows version (press **Windows key + R**, type `winver`, press **Enter**).

Do **not** send the long web address that contains `#token=`; it is a private key for that session.

Report problems at the project's **Issues** page: https://github.com/solomonade1/story-motion/issues (you need a free GitHub account), or tell the person who gave you the app.
