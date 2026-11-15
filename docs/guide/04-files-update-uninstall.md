# Where your files go, backups, updating and uninstalling

## Where your files go

All your work is saved in one folder, called the **workspace**:

`C:\Users\<your name>\StoryMotion Studio`

The Setup check shows it next to **Workspace:**. You do not need to create it. It is **separate from the app folder**: deleting or replacing the app never touches your projects.

Inside the workspace:

| Item | What it is |
|---|---|
| `projects\p-xxxxxxxxxxxx\` | One folder per project (the name is a code, not your project name) |
| ...`\project.json` | The project itself: its name, script, notes and storyboard. A copy called `project.json.bak` is kept beside it |
| ...`\assets\` | The copies of your pictures, audio and clips (for files added with **Copy into the project**) |
| ...`\thumbs\` and `\proxies\` | Small previews. The app can make these again, so they are safe to lose |
| ...`\renders\` | Your drafts and finals (MP4 files) |
| ...`\exports\` | Your export folders |
| `.trash\` | Projects you deleted (until you delete them forever) |
| `.app-profile\` | The private settings of the app's own window. Not your normal Edge. Safe to ignore |
| `index.sqlite` | A quick project list. Rebuilt automatically if lost |

Folders that start with a dot may be hidden. In File Explorer choose **View, Show, Hidden items** to see them.

Only one StoryMotion window can use a workspace at a time.

### Use a different folder

To keep projects somewhere else (for example a bigger drive), set the Windows environment variable `STORYMOTION_WORKSPACE`:

1. Press the **Start** button, type `environment variables` and open **Edit environment variables for your account**.
2. Under **User variables**, click **New...**.
3. **Variable name:** `STORYMOTION_WORKSPACE`. **Variable value:** the folder, for example `D:\StoryMotion Projects`.
4. Click **OK** twice, then close StoryMotion and start it again.

Your existing projects stay in the old folder. Move the old workspace's contents across (with the app closed) if you want them in the new place.

### Projects, archive and trash

- **Rename** and **Duplicate** do what they say. **Duplicate** is a good way to try something risky.
- **Archive** hides a project from the main list without deleting anything. Tick **Show archived projects** to see it, and click **Unarchive** to bring it back.
- **Delete** asks first, then moves the project to the **Trash**. Nothing is erased yet. Open **Trash (n)** on **Your projects** and click **Restore** to bring a project back.
- **Delete forever...** in the Trash permanently erases a project and its imported files. You must type the project name to confirm. It cannot be undone.

### Backups

StoryMotion saves automatically, but a computer can fail. A simple, safe backup:

1. Close StoryMotion (so no work is half-written).
2. Copy the whole `StoryMotion Studio` folder to a USB drive or a cloud-synced folder.
3. Do this after every working session, or at least weekly.

To restore: close the app, put the folder back in the same place (or point `STORYMOTION_WORKSPACE` at it).

If you only want to keep the results, copy your finished `-final.mp4` files (see "Make your first video", Step 9) and your **Export independent assets** folders.

If you used **Link to the original** for some files, those originals stay where they are and must be backed up as well.

## Update to a new version

1. **Back up** your workspace first (see above).
2. Download the new zip from the **Releases** page and extract it into a **new** folder (do not extract over the old one).
3. Close StoryMotion, then start the new version from its own `StoryMotion Studio.vbs`. Use **Add Desktop Shortcut.vbs** again if you want the Desktop shortcut to point to the new folder.
4. Open your projects. They are picked up automatically because they live in your workspace. If a project was made by an older version, the app updates it and keeps the original file next to it, and a message tells you.
5. When you are happy that everything works, delete the old app folder.

## Uninstall

1. Close StoryMotion.
2. Delete the Desktop shortcut **StoryMotion Studio** if you made one.
3. Delete the app folder (the one that contains `StoryMotion Studio.vbs`). Send it to the Recycle Bin, then empty it if you wish.
4. **Optional, and permanent:** to remove your projects too, delete `C:\Users\<your name>\StoryMotion Studio`. Do this only if you no longer need them, or after you have made a backup.

The app has no installer. As far as we know it does not add anything to the Windows registry, Start menu or settings, and nothing else needs removing. If you set `STORYMOTION_WORKSPACE` or `STORYMOTION_BROWSER`, you can delete those variables in the same place where you created them.
