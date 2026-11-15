"""Desktop-style launcher and native chooser plumbing (no real window: a stand-in 'browser' process is used)."""

from __future__ import annotations

import json
import socket
import sys
from pathlib import Path
from typing import Any

import pytest
from test_studio_api import Client

from storymotion_media.launcher import BROWSER_ENV, app_window_command, find_browser, launch
from storymotion_media.studio.api import ApiServer
from storymotion_media.studio.errors import InvalidInput, StudioError
from storymotion_media.studio.locking import WorkspaceLock
from storymotion_media.studio.picker import check_request
from storymotion_media.studio.store import Workspace

pytestmark = pytest.mark.ffmpeg

# Stand-in for the app window: reads the URL it was given, calls the worker like the UI would, records what it saw, exits.
FAKE_WINDOW = r"""
import json, sys, time, urllib.request
from urllib.parse import urlsplit, parse_qs
url, out = sys.argv[1], sys.argv[2]
parts = urlsplit(url)
frag = parse_qs(parts.fragment)
req = urllib.request.Request(f"http://{parts.netloc}/api/health", headers={"Authorization": "Bearer " + frag["token"][0]})
with urllib.request.urlopen(req) as r:
    health = json.loads(r.read())
index = urllib.request.urlopen(f"http://{parts.netloc}/").read()[:20]
json.dump({"ok": health["ok"], "picker": frag["picker"][0], "index": index.decode(), "has_token_in_query": bool(parts.query)}, open(out, "w"))
time.sleep(0.3)
"""


def hold_profile(profile: Path) -> Any:
    """Open ``lockfile`` with NO sharing, as Chromium does while it runs (Windows only)."""
    import ctypes

    profile.mkdir(parents=True, exist_ok=True)
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined,unused-ignore]
    k32.CreateFileW.restype = ctypes.c_void_p
    handle = k32.CreateFileW(str(profile / "lockfile"), 0xC0000000, 0, None, 4, 0x04000000, None)  # share none, delete on close
    assert handle not in (None, ctypes.c_void_p(-1).value)
    return lambda: k32.CloseHandle(ctypes.c_void_p(handle))


@pytest.mark.skipif(sys.platform != "win32", reason="Chromium's profile lock is a Windows file-sharing lock")
def test_launcher_keeps_serving_after_edge_hands_the_window_to_another_process(tmp_path: Path) -> None:
    """The real-world case that broke the first version: the process we start exits at once, the window lives on."""
    import threading
    import time

    from storymotion_media.launcher import profile_in_use, wait_for_window

    profile = tmp_path / "ws" / ".app-profile"
    assert profile_in_use(profile) is False
    release = hold_profile(profile)
    assert profile_in_use(profile) is True
    done = threading.Event()
    threading.Thread(target=lambda: (wait_for_window(profile, grace=0.0, poll=0.05), done.set()), daemon=True).start()
    time.sleep(0.4)
    assert not done.is_set()  # still waiting: the window is open
    release()
    assert done.wait(5)  # closing the window ends the wait
    assert profile_in_use(profile) is False
    (profile / "lockfile").write_bytes(b"stale")  # a leftover file from a crash must not hang the launcher
    assert profile_in_use(profile) is False


def static_dir(tmp: Path) -> Path:
    d = tmp / "static"
    d.mkdir(exist_ok=True)
    (d / "index.html").write_text("<html>app</html>")
    return d


def test_launch_runs_the_worker_for_the_life_of_the_window_then_stops_it(tmp_path: Path) -> None:
    seen = tmp_path / "seen.json"
    ws = tmp_path / "ws"
    msgs: list[str] = []
    profiles: list[Path] = []

    def command(url: str, profile: Path) -> list[str]:
        profiles.append(profile)
        return [sys.executable, "-c", FAKE_WINDOW, url, str(seen)]

    code = launch(ws, static_dir=static_dir(tmp_path), command=command, picker=lambda b: [], min_open_seconds=0.0, handoff_grace=0.0, out=msgs.append)
    assert code == 0
    got = json.loads(seen.read_text())
    assert got == {"ok": True, "picker": "1", "index": "<html>app</html>", "has_token_in_query": False}  # token only in the fragment
    assert profiles == [ws.resolve() / ".app-profile"] and profiles[0].is_dir()  # its own browser profile, inside the workspace
    assert any("Close the window to stop it" in m for m in msgs)
    with WorkspaceLock(ws):  # the lock was released: a new session can start
        pass


def test_the_worker_is_really_gone_after_the_window_closes(tmp_path: Path) -> None:
    ports: list[int] = []

    def command(url: str, profile: Path) -> list[str]:
        ports.append(int(url.split(":")[2].split("/")[0]))
        return [sys.executable, "-c", "pass"]

    assert launch(tmp_path / "ws", static_dir=static_dir(tmp_path), command=command, min_open_seconds=0.0, handoff_grace=0.0, out=lambda m: None) == 0
    with pytest.raises(OSError), socket.create_connection(("127.0.0.1", ports[0]), timeout=2):
        pass  # nothing is listening any more


def test_a_second_launch_on_the_same_workspace_is_refused_clearly(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    with WorkspaceLock(ws), pytest.raises(StudioError, match="already open"):
        launch(ws, static_dir=static_dir(tmp_path), command=lambda u, p: [sys.executable, "-c", "pass"], out=lambda m: None)


def test_missing_ui_or_browser_gives_actionable_messages(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    msgs: list[str] = []
    assert launch(tmp_path / "w1", static_dir=tmp_path / "nope", out=msgs.append) == 2
    assert "npm run build" in msgs[0]
    monkeypatch.setenv(BROWSER_ENV, str(tmp_path / "missing.exe"))
    assert launch(tmp_path / "w2", static_dir=static_dir(tmp_path), out=msgs.append) == 2
    assert "Edge was not found" in msgs[1] and BROWSER_ENV in msgs[1]


def test_an_instantly_closing_window_is_explained_and_a_failing_start_is_reported(tmp_path: Path) -> None:
    msgs: list[str] = []
    launch(tmp_path / "w", static_dir=static_dir(tmp_path), command=lambda u, p: [sys.executable, "-c", "pass"], handoff_grace=0.0, out=msgs.append)
    assert any("closed almost at once" in m for m in msgs)
    with pytest.raises(Exception, match="could not be started"):
        launch(tmp_path / "w2", static_dir=static_dir(tmp_path), command=lambda u, p: [str(tmp_path / "no-such-browser.exe")], out=msgs.append)
    with WorkspaceLock(tmp_path / "w2"):  # even a failed start releases the lock
        pass


def test_edge_is_found_and_started_in_app_mode_with_its_own_profile(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fake = tmp_path / "msedge.exe"
    fake.write_text("")
    monkeypatch.setenv(BROWSER_ENV, str(fake))
    assert find_browser() == fake
    cmd = app_window_command(fake, "http://127.0.0.1:1/#token=t", tmp_path / "prof")
    assert cmd[0] == str(fake) and "--app=http://127.0.0.1:1/#token=t" in cmd and f"--user-data-dir={tmp_path / 'prof'}" in cmd
    assert "--no-first-run" in cmd and not any(c.startswith("--remote-debugging") for c in cmd)  # no debugging port opened


# ---------------------------------------------------------------- native chooser
def test_chooser_requests_are_validated() -> None:
    assert check_request({"kind": "files", "multiple": True, "extensions": ["png", "mp4"], "filterName": "Media"}) == {
        "kind": "files", "multiple": True, "extensions": ["png", "mp4"], "filterName": "Media"}
    assert check_request({})["kind"] == "files"
    for bad in ({"kind": "root"}, {"extensions": ["../x"]}, {"extensions": "png"}, {"extensions": ["png"] * 40}, {"filterName": "a\nb"}):
        with pytest.raises(InvalidInput):
            check_request(bad)


def test_chooser_endpoint_is_off_unless_the_app_window_enabled_it(tmp_path: Path) -> None:
    off = ApiServer(Workspace(tmp_path / "a"))
    off.start_background()
    seen: list[dict[str, Any]] = []
    on = ApiServer(Workspace(tmp_path / "b"), picker=lambda body: (seen.append(body), [str(tmp_path / "x.png")])[1])
    on.start_background()
    try:
        c_off, c_on = Client(off.port, off.token), Client(on.port, on.token)
        st, err, _ = c_off.call("POST", "/api/pick", {"kind": "files"})
        assert st == 409 and err["error"]["code"] == "picker_unavailable"
        st, res, _ = c_on.call("POST", "/api/pick", {"kind": "files", "multiple": True, "extensions": ["png"]})
        assert st == 200 and res == {"paths": [str(tmp_path / "x.png")]}
        assert seen == [{"kind": "files", "multiple": True, "extensions": ["png"], "filterName": "Files"}]  # only validated fields pass on
        assert c_on.call("POST", "/api/pick", {"kind": "root"})[0] == 400
        assert c_on.call("POST", "/api/pick", {"kind": "files"}, token=None)[0] == 401
        assert c_on.call("GET", "/api/pick")[0] == 405
    finally:
        off.shutdown()
        on.shutdown()


def test_progress_notes_never_become_message_boxes_and_failures_do(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression: started from a shortcut (no console), the 'is open' note popped up as a blocking box and hung the launcher."""
    from storymotion_media import launcher

    boxes: list[str] = []
    monkeypatch.setattr(sys, "stdout", None)  # what pythonw.exe gives us
    monkeypatch.setattr(launcher, "_note", launcher._note)  # the real functions
    import ctypes

    class FakeUser32:
        @staticmethod
        def MessageBoxW(_h: int, text: str, _title: str, _flags: int) -> int:  # noqa: N802
            boxes.append(text)
            return 1

    monkeypatch.setattr(ctypes, "windll", type("W", (), {"user32": FakeUser32}), raising=False)
    launcher._note("StoryMotion Studio is open.")
    assert boxes == []  # a note with no console is silent
    launcher._show("Microsoft Edge was not found.")
    assert boxes == ["Microsoft Edge was not found."]  # a failure is never silent


def test_no_handoff_grace_after_a_window_that_ran_for_a_while(tmp_path: Path) -> None:
    """Regression: under pythonw the window process lives until it is closed; the 15 s hand-off wait then only delayed shutdown."""
    import time

    t0 = time.monotonic()
    code = launch(
        tmp_path / "ws", static_dir=static_dir(tmp_path), command=lambda u, p: [sys.executable, "-c", "import time; time.sleep(1.0)"],
        min_open_seconds=0.0, handoff_grace=30.0, handoff_window=0.3, out=lambda m: None,
    )
    assert code == 0 and time.monotonic() - t0 < 10  # returned promptly instead of waiting out the 30 s grace
