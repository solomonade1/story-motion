# Questions and answers, and glossary

## Frequently asked questions

### Is my work private? Does anything get uploaded?
Nothing is uploaded. The app runs only on your computer, listens only to your own computer, and makes no internet connections. There are no accounts, no tracking and no crash reports. Your pictures, script and narration stay in your workspace folder. The only time anything leaves is when **you** hand an export to someone else.

### Does it work offline?
Yes, completely. You need the internet only to download the zip. Writing, importing, previewing, rendering and exporting all work with the network off.

### What does it cost?
The app is free to download and use. It has no cloud features in this version, so there are no usage charges. (A budget system for future paid AI services is planned but not active; nothing can spend money today.)

### Do I need to install Python, FFmpeg or anything else?
No. Everything is inside the folder. It does not change any Python you already have.

### Does it need administrator rights?
No. Extract it anywhere you can write to, such as `C:\Apps` or **Documents**.

### Will it work on my computer?

| | |
|---|---|
| Windows 10 or 11, 64-bit | Yes |
| Windows 7 or 8, 32-bit Windows, Mac, Linux, phones | No |
| Microsoft Edge present | Needed (it comes with Windows 10 and 11) |

### What video do I get?
A standard MP4 (H.264 video with AAC audio), which plays in Windows, on phones and on video sites. Final renders use the project's size, normally 1920 x 1080 at 24 frames per second (the app has no screen for changing this yet). Drafts are smaller (640 x 360) on purpose.

### How long can a video be?
The design target is 3 to 5 minutes per episode, and it has been rehearsed at about that size. Longer videos may work but are not yet tested.

### Which files can I import?
Pictures: PNG, JPG, WebP. Audio: WAV, MP3, AAC. Video: MP4, MOV. See "Make your first video".

### What is a draft and what is a final?
A **draft** is a quick, small preview with a "DRAFT" badge to check timing and motion. The **final** is the full-size video. See the glossary below.

### Is it finished software?
It is an early release (version 0.1.0). The core path (import, storyboard, draft, final, export) is built and automatically tested, but it has not yet been tried on a brand-new computer by a first-time user, and a few features are marked "not available yet" in this guide. Please report anything surprising.

### Who owns what I make?
You do. The only mark StoryMotion adds is the "DRAFT" badge on drafts. You are responsible for having the rights to the pictures, voice and music you put in.

### Software licences
StoryMotion Studio includes other free software. The most important: **FFmpeg 9.0.2** (video tool, **GPL v3 licence**), Python (PSF licence) and others. The full list and licence texts are in the `licenses` folder inside the app folder, in `THIRD_PARTY_NOTICES.md`. FFmpeg runs as a separate program. If you need FFmpeg's source code, see the links in that notice.

### Why does Windows warn me about it?
The app is not "code-signed". Signing costs money each year, and it has not been bought yet. The warnings (SmartScreen and similar) are about the missing signature, not about anything found in the file. See "Download and install" and "Troubleshooting" for exactly what to click.

### Can two people use it at once?
Not on the same projects folder at the same time. Each computer has its own workspace. To work on one project on two computers, copy the project folder (after closing the app) rather than sharing a live folder.

### Can I move my projects to another computer?
Yes: close the app and copy the whole `StoryMotion Studio` workspace folder to the same place on the other computer. If you used **Link to the original** for some files, copy those originals too and use **Relink...**.

## Glossary

| Word | Plain meaning |
|---|---|
| **Project** | One story or episode: its script, pictures, clips, narration, storyboard and finished videos |
| **Workspace** | The folder on your computer that holds all your projects. Normally `C:\Users\<you>\StoryMotion Studio` |
| **Media** (or asset) | Any file you imported: a picture, a sound or a video clip |
| **Library** | The list of all media in a project (on the **Media** tab) |
| **Storyboard** | The plan of your video: scenes, each made of shots, timed against the narration |
| **Scene** | A part of the story, for example "Jonah boards the ship". A scene holds one or more shots |
| **Shot** | One continuous piece of the video: one picture (or clip) shown for a set time, with an optional camera move and a transition |
| **Narration** | The recorded voice of the story. It is the **narration clock**: the master timeline that every shot is measured against |
| **Narration clock** | The timeline set by the length of your narration file. All times in the Storyboard are milliseconds (ms) on it. 1000 ms is 1 second |
| **Animation mode** | How a shot is made: **STATIC** (still), **CINEMATIC** (camera move), **LAYERED** (moving cut-outs), **RENDERED** (a video clip you supply), **GENERATIVE** (AI clip; not available in this version) |
| **Motion preset** | A ready-made camera move for CINEMATIC shots, such as `slow-push-in` or `pan-left` |
| **Transition** | How one shot changes to the next: **Cut** (instant), **Crossfade (dissolve)** (blend), **Dip to black** |
| **Layer** | A separate picture with a transparent background (a character or object) that moves over a shot's background picture |
| **Music bed** (or ambience) | Background audio that plays under the narration and is lowered ("ducked") while the narrator speaks |
| **Draft render** | A small, quick (640 x 360) preview with a "DRAFT" badge, for checking timing and motion. Not final quality |
| **Final render** | The full-size finished MP4 video |
| **Proxy preview** | A smaller stand-in copy used for quick previews (the **Scrub** picture and the draft). It is for checking, not for judging quality; the final render is the real thing |
| **Export** | A folder with your shots, audio and timelines for editors or AI, written on your computer. Not the same as rendering the video |
| **Checksum** | A fingerprint of a file. If the file changes at all, the fingerprint changes |
| **Unblock** | A Windows option that tells Windows that a file you downloaded is safe to open normally |
| **SmartScreen** | A Windows feature that warns about downloads it does not recognise |
| **Smart App Control** | An optional Windows 11 protection that only allows signed programs |
| **FFmpeg** | The free video tool inside the app that actually builds your video |
