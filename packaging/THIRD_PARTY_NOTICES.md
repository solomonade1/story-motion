# Third-party software in this download

| Component | Licence | Where it is |
|---|---|---|
| Python (embeddable) | PSF License | `python\` — https://www.python.org/ |
| Tcl/Tk (file chooser) | Tcl/Tk License (BSD-style) | `python\tcl`, `python\*.dll` |
| pydantic, pydantic-core | MIT | `python\Lib\site-packages` |
| Pillow | MIT-CMU (HPND) | `python\Lib\site-packages` |
| React, React DOM (UI) | MIT | compiled into `app\apps\desktop\dist` |
| **FFmpeg 9.0.2 "full" build (Gyan.dev)** | **GPL v3** (includes x264 and other GPL parts) | `app\tools\ffmpeg\bin\ffmpeg.exe`, `ffprobe.exe` |

## FFmpeg and the GPL
FFmpeg is a separate program that StoryMotion Studio starts as a child process; it is not linked into StoryMotion's own code.
The bundled build is licensed GPL v3. Its licence text is in `licenses\`. Source code for FFmpeg is available at
https://ffmpeg.org/download.html#get-sources and the exact build is documented at https://www.gyan.dev/ffmpeg/builds/
(release tag 9.0.2 at https://github.com/GyanD/codexffmpeg). If you need the corresponding source and cannot get it from those places,
open an issue on this project's release page and it will be provided.

> **Maintainer note (not legal advice):** before wide public distribution, review this decision (see `docs/architecture/ADR-0007-ffmpeg-provisioning.md`).
> Alternatives: ship an LGPL FFmpeg build (would lose libx264, which the renderer requires today), or have users install FFmpeg themselves.
