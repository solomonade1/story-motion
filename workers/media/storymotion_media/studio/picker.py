"""Native file/folder chooser for the Studio when it runs in a plain app window (no Tauri).

The worker opens the chooser on the user's own desktop, in a short-lived child process (Tk must own its thread), and returns
only what the user picked. It is reachable only through the authenticated loopback API, and only when the app was launched
with the picker enabled; it never reads or lists anything itself.

Run as ``python -m storymotion_media.studio.picker`` with one JSON request on stdin; prints a JSON list of paths.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any

from .errors import InvalidInput, StudioError

_EXT = re.compile(r"^[a-z0-9]{1,8}$")
TIMEOUT_S = 600.0


def check_request(body: dict[str, Any]) -> dict[str, Any]:
    kind = body.get("kind", "files")
    if kind not in ("files", "folder"):
        raise InvalidInput("'kind' must be 'files' or 'folder'.")
    exts = body.get("extensions") or []
    if not isinstance(exts, list) or len(exts) > 30 or not all(isinstance(e, str) and _EXT.match(e) for e in exts):
        raise InvalidInput("'extensions' must be a short list of file extensions such as 'png'.")
    name = body.get("filterName", "Files")
    if not isinstance(name, str) or len(name) > 40 or any(ord(c) < 32 for c in name):
        raise InvalidInput("'filterName' must be a short plain label.")
    return {"kind": kind, "multiple": body.get("multiple") is True, "extensions": exts, "filterName": name}


def run_picker(body: dict[str, Any]) -> list[str]:
    """Open the chooser (blocks until the user answers) and return the chosen absolute paths ([] if cancelled)."""
    req = check_request(body)
    try:
        proc = subprocess.run(  # noqa: S603 - fixed argv, request passed on stdin, no shell
            [sys.executable, "-m", "storymotion_media.studio.picker"],
            input=json.dumps(req), capture_output=True, text=True, timeout=TIMEOUT_S, check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise StudioError("The file chooser did not respond. Try again, or type the path instead.") from exc
    if proc.returncode != 0:
        raise StudioError("The file chooser could not open on this computer. Type the path instead.")
    try:
        paths = json.loads(proc.stdout or "[]")
    except ValueError as exc:
        raise StudioError("The file chooser returned something unreadable. Type the path instead.") from exc
    return [p for p in paths if isinstance(p, str)]


def _main() -> int:  # pragma: no cover - needs a desktop; exercised by hand
    req = json.loads(sys.stdin.read().lstrip("﻿") or "{}")
    import tkinter
    from tkinter import filedialog

    root = tkinter.Tk()
    root.withdraw()
    root.attributes("-topmost", True)  # a hidden parent would otherwise leave the dialog behind the app window
    try:
        if req.get("kind") == "folder":
            chosen: Any = filedialog.askdirectory(mustexist=True)
            paths = [chosen] if chosen else []
        else:
            types = []
            if req.get("extensions"):
                pats = " ".join(f"*.{e}" for e in req["extensions"])
                types = [(req.get("filterName", "Files"), pats), ("All files", "*.*")]
            if req.get("multiple"):
                chosen = filedialog.askopenfilenames(filetypes=types)
                paths = list(chosen)
            else:
                one = filedialog.askopenfilename(filetypes=types)
                paths = [one] if one else []
    finally:
        root.destroy()
    # Tk returns forward slashes; the rest of the app expects native Windows paths
    sys.stdout.write(json.dumps([str(__import__("pathlib").Path(p)) for p in paths]))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
