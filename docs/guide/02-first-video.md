# Make your first video

This is a start-to-finish walkthrough. Allow an hour for your first video. Every button name is shown in **bold**, exactly as it appears on screen.

**The idea in one minute.** You give StoryMotion a recorded **narration** (the voice), **pictures**, and optionally music and video clips. You split the story into **scenes**, and each scene into **shots**. A shot says "show this picture, from this second to that second, with this camera movement". StoryMotion then builds a finished MP4 video on your computer. The narration is the master clock: every shot is timed against it.

> The app does not decide timings for you. When you import a script, you get scenes but **no shots**. You add the shots and set how long each lasts. The app then checks your timing and tells you what to fix.

## Before you start: gather your files

| You need | Details |
|---|---|
| **Narration** (required) | One audio file: WAV, MP3 or AAC. This sets the length of the whole video |
| **Pictures** | PNG, JPG or WebP. Best: 16:9 shape, at least 1920 x 1080. Larger (for example 2560 x 1440) leaves room for slow zooms |
| **Script** (optional) | A plain text (`.txt`) or Markdown (`.md`) file. See Step 3 for how it is split into scenes |
| **Music or ambience** (optional) | WAV, MP3 or AAC. Make sure you have the right to use it |
| **Video clips** (optional) | MP4 or MOV, for shots a still picture cannot show. 1920 x 1080 at 24 frames per second works best |
| **Cut-outs for moving characters** (optional) | PNG pictures with a transparent background |

Other file types (for example `.m4a`, `.avi`, `.gif`, `.bmp`) are refused with a clear message. Convert them first, or choose a supported type.

**Your original files are never changed or moved.**

## Step 1. Create a project

1. Start the app (see "Download and install") and click **Continue** on the Setup check.
2. On **Your projects**, click **New project** (or **Create your first project** if the list is empty).
3. Type a **Project name**, for example `Jonah episode 1`, and click **Create**.
4. The project opens with three tabs: **Media**, **Storyboard** and **Script & notes**.

On **Your projects**, each project has **Open**, **Rename**, **Duplicate**, **Archive** and **Delete**. See "Where your files go" for what these do.

> Screenshot to add: the Your projects screen with one project card.

## Step 2. Import your files (the Media tab)

1. Click the **Media** tab. You see the **Add media** box.
2. Choose how to add the files:
   - **Copy into the project** (recommended): StoryMotion keeps its own copy, so the project still works if you later move or delete the originals.
   - **Link to the original**: nothing is copied; the project points to your file. If you later move the file, use **Relink...**.
3. Click **Browse...** and choose your files. A normal Windows file window opens; you can select many files at once (hold **Ctrl** or **Shift**). The paths appear in the box.
   - If there is no **Browse...** button, type the full path of each file, one per line, for example `C:\Users\You\Pictures\harbour.png`. Quote marks around a path are fine.
4. Click **Import**.
5. Watch **Activity**. Each file shows progress, then a summary such as "12 added", plus counts for files "already in the project" (duplicates are detected automatically) and files that "could not be imported", each with a reason.
6. Every imported file appears in the **Library** with a preview, size and length. A green **OK** label means it is fine.

Good to know:
- You can import up to 500 files at a time.
- The category menu under each file (character, environment, prop, audio, effect, and so on) is a label to help you keep things tidy. Your video does not depend on it.
- **Remove** takes a file out of the project. It does not delete your original.
- **Check files** re-checks that every file is still there and unchanged. Use it after moving or editing files. The result is reported as "Checked: x fine, y missing, z changed".
- The filter menu (**Everything**, a category, **Missing**, **Changed**) helps you find things in a big library.
- If a file goes **Missing** or **Changed**, a warning appears. Use **Relink...** on that file and give the new location of the same file, or click **Find moved files in a folder...** and choose a folder to search.

> Screenshot to add: the Media tab after importing about ten files, showing the Library grid and the Activity summary.

## Step 3. Import the script (optional but handy)

1. Click the **Storyboard** tab.
2. Click **Import script (.txt, .md)** and choose your script file.
3. StoryMotion splits it into scenes:
   - **Markdown (.md):** each heading that starts with `#`, `##` or `###` begins a new scene. The text under it is that scene's passage.
   - **Plain text (.txt):** each paragraph (separated by a blank line) is a scene. If the file has no blank lines, each line becomes a scene.
4. If the project already has scenes, a box asks **Replace the current storyboard?** Choose **Keep what I have** or **Replace it**. Nothing is replaced without asking. Your chosen narration and characters are kept.

You can also type or paste your script on the **Script & notes** tab. That text is kept with the project; it is not turned into scenes by itself.

Instead of a script, you can click **Import scene plan (.json)** to bring in a ready-made plan file, for example one that an AI assistant revised from your exported brief (see "Exporting"). The plan is checked before anything is accepted, and any problem is listed with where it is.

> Screenshot to add: the Storyboard tab right after importing a script, showing the scenes.

## Step 4. Choose the narration

1. At the top of the **Storyboard** tab, open the menu **Narration (the clock for every shot)** and choose your narration file. Its length is shown next to its name.
2. A line then reads **Narration length: ...**. All shot times are measured on this clock, in **milliseconds** (1000 ms = 1 second).

Optional: type a name next to **Add a character** and click **Add character** to list the people in your story. You can tick them on each shot later. This is for your own bookkeeping and for the AI brief; it does not change the picture.

## Step 5. Add and arrange shots

For each scene:

1. Click **Add shot to this scene**. A new shot appears (a STATIC shot of up to 3 seconds that starts where the last shot ended) and its editor opens near the bottom of the page.
2. In the editor, set:
   - **Picture**: choose one of your pictures.
   - **Duration (ms)**: how long the shot lasts. Example: `8000` is 8 seconds. **Start (ms)** is filled in for you.
   - **Animation mode**:

     | Mode | Use it for |
     |---|---|
     | **STATIC** | One picture that does not move |
     | **CINEMATIC** | One picture with a slow camera move (see **Motion preset**) |
     | **LAYERED** | A background picture plus separate transparent cut-outs that move (see below) |
     | **RENDERED** | A video clip you made elsewhere (choose it under **Video clip**) |
     | **GENERATIVE** | Not available in this version. The shot uses a plain local fallback and the app tells you so |

   - **Motion preset** (for CINEMATIC shots): `slow-push-in`, `slow-pull-out`, `pan-left`, `pan-right`, `reveal` or `hold` (no movement). STATIC shots stay still.
   - **Transition into this shot**: **Cut**, **Crossfade (dissolve)** or **Dip to black**, plus **Transition length (ms)**. The very first shot cannot have a transition; use **Video fade-in (ms)** (above the timeline) for that.
   - **Action**, **Must show (one per line)**, **Avoid (one per line)**: notes about what happens in the shot. They do not change the picture, but they travel with your exports and help any editor or AI that reads them.
3. Use the up and down arrow buttons next to each shot to move it inside its scene, and the arrows next to a scene title to move whole scenes. **Add scene** adds an empty scene. **Remove scene** removes one (you can **Undo** straight away).

More options:
- **RENDERED** shots also have **Trim start of clip (ms)** and **Clip speed** (normal, a few slower speeds, or **Slow to fit the shot**).
- **LAYERED** shots show **Moving layers (drawn back to front)**. Click **Add layer**, pick a transparent PNG as the **Layer picture**, and set where it starts and ends (position, size, tilt). A small stage preview and a slider show the movement. Layers are flat pictures: they can slide, grow, tilt and rock, but not bend.
- **Music and ambience** (above the timeline): click **Add music or ambience**, pick a file, set its **Level (dB)**, how much to lower it while the narrator speaks (**Lower under narration by (dB)**), its fades, and whether it repeats. Import the audio on the **Media** tab first.
- **Video fade-in (ms)** and **Video fade-out (ms)** fade the whole video from and to black.
- Every change is **saved automatically** a moment after you stop. The label in the corner reads **All changes saved** when it is done. Many removals show an **Undo** button.

> Screenshot to add: the shot editor for a CINEMATIC shot, with Picture, Duration and Motion preset visible.

## Step 6. Check the timing

The **Timeline** shows one block per shot along the narration, with a marker where the narration ends. Click a block to edit that shot. Drag the **Scrub** slider to see a still picture of the shot at that moment. This is only a quick look: it shows no motion, transitions or sound.

Under the timeline is the list **Timeline checks** (or the message **No timing problems found.**). Each item is labelled:

| Label | Meaning |
|---|---|
| **Problem** | Must be fixed before you can render (for example a picture was removed from the project) |
| **Check** | Usually must be fixed too: a gap or overlap between shots, shots that end well before or after the narration, a shot with no picture, a transition longer than its neighbours |
| **Note** | Information only |

Each item has a **Show** button that jumps to the shot. Two buttons fix the most common timing problems:

- **Close gaps and overlaps**: keeps the order and lengths, and makes each shot start when the previous one ends.
- **Fit last shot to narration end**: stretches the last shot so the video ends with the narration.

A reliable routine: set each shot's **Duration (ms)**, click **Close gaps and overlaps**, then **Fit last shot to narration end**, then clear whatever **Timeline checks** still lists. Small differences (up to 250 ms at the end) are tolerated.

The app refuses to render while serious items remain, and says exactly what to fix.

## Step 7. Render a draft

1. Scroll down to the **Render** area.
2. Click **Render draft**. A progress bar and percentage appear. You can click **Cancel render**; cancelling takes effect when the current step ends, and nothing is published.
3. When it finishes, the video appears in a player, labelled **Draft proxy: not final quality**. A draft is small (640 x 360) with a "DRAFT" badge. It is for checking timing, order and motion, not picture quality.
4. Press play. Fix anything you dislike, render another draft, and repeat.

Do not close the window while a render is running. The app warns you if you try.

## Step 8. Render the final video

1. When the draft looks right, click **Render final (full size)**.
2. Wait. A few minutes is normal for a 3 to 5 minute video, and longer on a slower computer. Each render builds the whole video again.
3. The result is labelled **Final export**. The app checks the finished file (streams, length, unplanned black frames) and reports its size, frame rate and any warnings.
4. Every render is a **new file**. Earlier drafts and finals are kept. Choose between them in the **Rendered videos** menu.

## Step 9. Find your finished video file

The finished MP4 files are stored inside your project folder. The app does not yet have a "show in folder" button for renders (it does for exports), so use this route:

1. Open File Explorer and go to `C:\Users\<your name>\StoryMotion Studio\projects`. (If you changed the workspace, use that folder instead.)
2. Open the folder whose name starts with `p-` and was changed most recently (click the **Date modified** column to sort). If you have several projects, open them one by one and look for a `renders` folder with your latest file.
3. Open the `renders` folder. Files ending in `-final.mp4` are final renders. Files ending in `-draft.mp4` are drafts. Each also has a small report file next to it.
4. **Copy** the final MP4 somewhere you will find it (Desktop, Videos, a USB drive). Copy rather than move, so the project keeps its history.

> Screenshot to add: File Explorer showing the renders folder with a -final.mp4 file.

## Reference: what the screens contain

| Screen | What it is for |
|---|---|
| **Setup check** | Tests your computer. Shown each time you start; **Continue** moves on |
| **Your projects** | The list of projects, **New project**, **Show archived projects**, **Trash**, **Setup check** |
| **Media** tab | **Add media**, **Activity**, **Library** (with **Check files** and a filter) |
| **Storyboard** tab | Narration, script and plan import, characters, fades, music, timeline, **Timeline checks**, scenes and shots, **Render**, **Export** |
| **Script & notes** tab | Free text for your script and notes; saved automatically |

## What is not available yet

So you do not look for it:

- AI-generated video clips and any cloud service. The app works fully offline.
- Sound effects on individual shots, waveform editing, and dragging clip edges on the timeline.
- Depth (parallax) effects, and animation beyond a layer's start and end positions.
- An in-app voice recorder or voice generator: bring your own narration file.
- Opening old command-line "episode folders" as Studio projects.
