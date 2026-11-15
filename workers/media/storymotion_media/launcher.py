"""Desktop-style launcher: starts the local worker and opens the Studio in its own Edge *app window*.

Why this and not a compiled shell: Windows Smart App Control blocks unsigned programs we compile ourselves, but it allows
Microsoft-signed Edge and the signed Python already used here. So this needs no security setting changed and no build step.

Behaviour (all tested except the real window, which was checked by hand):
- one worker per workspace (the workspace lock); a second launch says so instead of starting;
- the window uses its OWN browser profile inside the workspace (``.app-profile``), so it is a separate process that
  we can wait on, and it shares no cookies, history or sign-ins with the user's normal Edge;
- when the window closes, the worker stops and the lock is released; running jobs are cancelled (the UI warns first);
- the session token travels only in the URL fragment of the window we start (never to a server, never logged).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Callable
from pathlib import Path

from .errors import ToolchainError
from .studio.api import ApiServer
from .studio.locking import WorkspaceLock
from .studio.store import Workspace

REPO = Path(__file__).resolve().parents[3]
BROWSER_ENV = "STORYMOTION_BROWSER"


def find_browser() -> Path | None:
    """Edge (preinstalled on Windows 11), or the executable named in STORYMOTION_BROWSER."""
    override = os.environ.get(BROWSER_ENV)
    if override:
        p = Path(override)
        return p if p.is_file() else None
    roots = [os.environ.get(k) for k in ("ProgramFiles(x86)", "ProgramFiles", "LOCALAPPDATA")]
    for root in filter(None, roots):
        p = Path(root) / "Microsoft" / "Edge" / "Application" / "msedge.exe"
        if p.is_file():
            return p
    return None


def app_window_command(browser: Path, url: str, profile: Path) -> list[str]:
    return [
        str(browser),
        f"--app={url}",
        f"--user-data-dir={profile}",  # own profile => own process that lives exactly as long as the window
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-sync",
        "--window-size=1280,900",
    ]


def profile_in_use(profile: Path) -> bool:
    """Is a browser still running on this profile? Chromium holds ``lockfile`` open with no sharing while it runs."""
    lock = profile / "lockfile"
    if not lock.exists():
        return False
    try:
        with lock.open("ab"):
            return False  # we could open it, so nobody holds it (a stale file from a crash)
    except PermissionError:
        return True
    except OSError:
        return False


def wait_for_window(profile: Path, *, grace: float, poll: float = 0.5) -> None:
    """Edge's first process often hands the window to another process and exits at once. Keep serving until the profile is free."""
    deadline = time.monotonic() + grace
    while time.monotonic() < deadline and not profile_in_use(profile):
        time.sleep(min(0.2, poll))
    while profile_in_use(profile):
        time.sleep(poll)


def launch(
    workspace: Path,
    *,
    static_dir: Path | None = None,
    command: Callable[[str, Path], list[str]] | None = None,
    picker: Callable[[dict[str, object]], list[str]] | None = None,
    min_open_seconds: float = 3.0,
    handoff_grace: float = 15.0,
    handoff_window: float = 10.0,
    out: Callable[[str], None] = print,
    err: Callable[[str], None] | None = None,
) -> int:
    """Run the worker and one app window until the window is closed. Returns a process exit code."""
    err = err or out  # failures go to ``err`` (a message box when there is no console); progress notes go to ``out``
    static = static_dir or REPO / "apps" / "desktop" / "dist"
    if not (static / "index.html").is_file():
        err(f"The app screens are not built yet. Run:  cd apps\\desktop ; npm install ; npm run build   (looked in {static})")
        return 2
    if command is None:
        browser = find_browser()
        if browser is None:
            err(f"Microsoft Edge was not found. Install Edge, or set {BROWSER_ENV} to a Chromium browser's .exe path.")
            return 2

        def command(url: str, profile: Path) -> list[str]:  # noqa: F811
            return app_window_command(browser, url, profile)

    workspace.mkdir(parents=True, exist_ok=True)
    lock = WorkspaceLock(workspace)
    lock.acquire()  # a clear StudioError if StoryMotion is already open on this workspace
    server: ApiServer | None = None
    try:
        server = ApiServer(Workspace(workspace), static_dir=static, picker=picker)
        server.start_background()
        url = f"http://127.0.0.1:{server.port}/#token={server.token}&picker={'1' if picker else '0'}"
        profile = server.ws.root / ".app-profile"
        profile.mkdir(exist_ok=True)
        started = time.monotonic()
        try:
            proc = subprocess.Popen(command(url, profile), stdin=subprocess.DEVNULL)  # noqa: S603 - argv list, no shell
        except OSError as exc:
            raise ToolchainError(f"The app window could not be started: {exc.strerror or exc}") from exc
        out(f"StoryMotion Studio is open. Workspace: {server.ws.root}. Close the window to stop it.")
        code = proc.wait()
        # Only a process that exits soon after starting can have handed the window to another process. One that ran
        # for a while IS the window, and has just been closed: no grace period then (it would only delay shutdown).
        handed_off = time.monotonic() - started < handoff_window
        wait_for_window(profile, grace=handoff_grace if handed_off else 0.0)
        if time.monotonic() - started < min_open_seconds:
            err("The window closed almost at once. If it did not appear, run 'python -m storymotion_media serve' and open the URL in a browser.")
        return 0 if code in (0, None) else 1
    finally:
        if server is not None:
            server.shutdown()
        lock.release()


def _note(message: str) -> None:
    """Progress notes: printed when there is a console, otherwise dropped (never a blocking box)."""
    if sys.stdout is not None:
        print(message)


def _show(message: str) -> None:
    """Failures: printed when there is a console; with no console (started from a shortcut) a message box, so they are never silent."""
    if sys.stdout is not None:
        print(message)
        return
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, message, "StoryMotion Studio", 0x10)  # type: ignore[attr-defined,unused-ignore]
    except (AttributeError, OSError):
        pass


def run_cli_launch(workspace: Path | None, static: Path | None) -> int:
    from .errors import StoryMotionError
    from .studio.paths import default_workspace
    from .studio.picker import run_picker

    try:
        return launch(workspace or default_workspace(), static_dir=static, picker=run_picker, out=_note, err=_show)
    except StoryMotionError as exc:
        _show(str(exc))
        return 2


__all__ = ["BROWSER_ENV", "app_window_command", "find_browser", "launch", "run_cli_launch"]
