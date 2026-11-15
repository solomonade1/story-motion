# Download and install

This part gets StoryMotion Studio onto your computer and open for the first time. You do not need a terminal, an account, or an internet connection after the download.

## Download

Get these from the **Releases** page (current version: **0.1.0**):

| What | Link | Size |
|---|---|---|
| **The app (required):** `StoryMotion-Studio-0.1.0-win64.zip` | [Download the zip](https://github.com/solomonade1/story-motion/releases/download/v0.1.0/StoryMotion-Studio-0.1.0-win64.zip) | about 207 MB |
| Checksum file (optional): `StoryMotion-Studio-0.1.0-win64.zip.sha256` | [Download the checksum](https://github.com/solomonade1/story-motion/releases/download/v0.1.0/StoryMotion-Studio-0.1.0-win64.zip.sha256) | tiny |
| All versions, release notes | [Releases page (latest)](https://github.com/solomonade1/story-motion/releases/latest) | |

On the Releases page the files are listed under **Assets**. Pick the one that ends in `-win64.zip`. Ignore **Source code (zip)** and **Source code (tar.gz)**: those are for programmers.

> If the link shows "404" or "Page not found", tell the person who gave you this guide. The project page may be set to private. See "Troubleshooting".

### Check your download (optional, about one minute)

This proves the file is complete and unchanged. Skip it if you trust where you got the file.

1. Open the folder that holds the zip (usually **Downloads**).
2. Click the address bar at the top of the File Explorer window, type `powershell` and press **Enter**. A blue window opens.
3. Type this and press **Enter** (use the real file name if your version differs):
   `Get-FileHash .\StoryMotion-Studio-0.1.0-win64.zip -Algorithm SHA256`
4. Open the `.sha256` file with Notepad. The long string of letters and digits in the **Hash** column must be the same as the one at the start of that file (capital or small letters do not matter).
5. If they differ, delete the zip and download it again.

## System requirements

| | You need |
|---|---|
| Windows | Windows 10 or Windows 11, 64-bit |
| Browser part | **Microsoft Edge** (already part of Windows 10 and 11). The app opens in its own Edge window |
| Disk space | About 1.5 GB free for the app, plus several GB for your projects, previews and videos. The Setup check warns below 5 GB free and fails below 1 GB |
| Memory and screen | No minimum has been tested. A computer with 8 GB of memory and a screen of at least 1280 x 800 is a sensible starting point. Rendering a long video is slower on weaker computers |
| Internet | Only to download the zip. The app itself never connects to the internet |
| Extras | No administrator rights, no installer, no Python, no FFmpeg, no accounts. Everything is inside the folder |

> Not yet tested on a clean computer: this first release has been built and checked by its authors but not yet tried on a brand-new Windows account. If something here does not match what you see, please report it (see "Troubleshooting", last section).

## Install in 5 steps

There is no installer. "Installing" means unpacking the zip into a folder you keep.

1. **Download** the zip (see above). You should see `StoryMotion-Studio-0.1.0-win64.zip` in your **Downloads** folder.
2. **Unblock the zip.** Right-click the zip, choose **Properties**. At the bottom of the **General** tab, if you see a **Security** line with a tick box **Unblock**, tick it and click **OK**. If there is no such box, carry on. You should see the Properties window close.
3. **Extract everything.** Right-click the zip and choose **Extract All...** (on Windows 11: **Show more options**, then **Extract All...** if you do not see it at once). Choose a short, simple place such as `C:\Apps` or your **Documents** folder, then click **Extract**. Wait a minute or two. You should see a new folder called `StoryMotion-Studio-0.1.0-win64` that contains files such as `StoryMotion Studio.vbs`, `USER GUIDE.md` and folders called `python`, `app` and `licenses`.
   Do **not** run anything from inside the zip, and avoid very deep or very long folder names.
4. **Start the app.** Open the new folder and double-click **`StoryMotion Studio.vbs`**. (It may show as **StoryMotion Studio** with a "VBScript" file type.) Nothing flashes and there is no black console window. After a few seconds, a window titled **StoryMotion Studio** opens with the heading **Welcome to StoryMotion Studio**.
5. **Add a shortcut (optional).** Double-click **`Add Desktop Shortcut.vbs`**. A message says a shortcut was added to your Desktop. From now on, double-click **StoryMotion Studio** on your Desktop.

### If Windows warns you

The download is not "code-signed" (signing is a paid certificate), so Windows may be careful the first time. This is expected.

| What you see | What it means | What to do |
|---|---|---|
| **Windows protected your PC** (blue SmartScreen box) | Windows does not recognise the publisher | Click **More info**, then **Run anyway**. Only do this for a file you downloaded from the official Releases page |
| A security warning that says the file came from another computer, or "Open File - Security Warning" | The zip was not unblocked | Click **Run** or **Open**. Next time, do step 2 (Unblock) before extracting |
| Extracted files still ask "Do you want to run this file?" | The zip was extracted before it was unblocked | Delete the extracted folder, unblock the zip (step 2), extract again |
| A message that an application control policy or **Smart App Control** blocked a file | Smart App Control (an optional Windows 11 protection) only allows signed programs, and the bundled video tool `ffmpeg.exe` is not signed by Microsoft | See "Troubleshooting": "Smart App Control blocked a file" |

## First run walkthrough

The first screen is the **Setup check**. It tests your computer and tells you in plain words what works.

1. After step 4 above, the window shows **Welcome to StoryMotion Studio**, a line saying everything runs on this computer, and the heading **Setup check**.
2. Wait for **Checking this computer...** to finish. You then see a list. Each line has a coloured label:

   | Label | Meaning |
   |---|---|
   | **Ready** | This works |
   | **Optional** | Not needed. For example **Piper voice (optional)** is normally "not installed": the app then uses the built-in Windows voice. That is fine |
   | **Needs attention** | Something must be fixed. The line shows **How to fix** |

3. The checks are **Python worker**, **FFmpeg + ffprobe**, **Workspace folder**, **Free disk space**, **Piper voice (optional)** and **Offline mode**.
4. At the bottom you see **Workspace:** followed by a folder path such as `C:\Users\you\StoryMotion Studio`. That folder is where all your projects are saved. You do not need to create it.
5. Click **Continue**. (If something **Needs attention**, the button says **Continue anyway**. You can still organise projects, but importing and previews will not work until it is fixed.) Click **Check again** after fixing something.
6. You arrive at **Your projects**. You can reach the **Setup check** again at any time with the **Setup check** button at the top right.

> Screenshot to add: the Setup check screen with all lines marked Ready.

**Closing the app:** close its window with the normal **X**. This also stops the program behind it. If an import or render is running, the window asks you first.
