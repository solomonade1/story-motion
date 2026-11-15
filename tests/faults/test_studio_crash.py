"""Hard process kills (TerminateProcess / SIGKILL): the project must survive (FR-PROJ-002; QG DATA-02, F-08, F-09, OPS-05 slice).

These kill REAL worker processes at random moments. They prove survival of the *project files*; they do not exercise the
desktop shell (not built yet) and the 10-second loss bound of DATA-02 is not measured here.
"""

from __future__ import annotations

import http.client
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from storymotion_media.studio.store import Workspace
from storymotion_media.toolchain import Toolchain, run

CHILD_SAVE = """
import sys
from pathlib import Path
from storymotion_media.studio.store import Workspace
p = Workspace(Path(sys.argv[1])).project(sys.argv[2])
rev = p.load()[0].revision
while True:
    rev = p.update({"script": "x" * 900000 + str(rev)}, base_revision=rev).revision
    print(rev, flush=True)
"""

CHILD_IMPORT = """
import sys, threading
from pathlib import Path
from storymotion_media.toolchain import get_toolchain
from storymotion_media.studio.store import Workspace
from storymotion_media.studio.assets import AssetService
p = Workspace(Path(sys.argv[1])).project(sys.argv[2])
svc = AssetService(p, get_toolchain())
res = svc.import_files(sys.argv[3:], progress=lambda f, m: print("PROGRESS", m, flush=True))
print("DONE", len(res.imported), flush=True)
"""


def kill_tree(proc: subprocess.Popen[Any]) -> None:
    if os.name == "nt":  # the venv launcher spawns the real interpreter as a child; kill both, like a crash would
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, check=False)  # noqa: S603, S607
    else:
        proc.kill()
    proc.wait(timeout=20)


def big_video(tc: Toolchain, out: Path, seconds: int = 30) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    p = run(
        [
            tc.ffmpeg,
            "-v",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size=1920x1080:rate=30:duration={seconds}",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-pix_fmt",
            "yuv420p",
            out,
        ],
        timeout=300,
    )
    assert p.returncode == 0, p.stderr
    return out


def test_killing_the_worker_during_autosave_never_corrupts_the_project(tmp_path: Path) -> None:
    ws = Workspace(tmp_path / "ws")
    pid = ws.create("Crash test").projectId
    rng = random.Random(1234)  # noqa: S311
    last_ack = 0
    for i in range(20):
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-c", CHILD_SAVE, str(tmp_path / "ws"), pid],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert proc.stdout is not None
        acks = 0
        while acks < 3:  # let it save a few times first
            line = proc.stdout.readline()
            assert line, f"worker exited early: {proc.stderr.read() if proc.stderr else ''}"
            last_ack, acks = int(line), acks + 1
        time.sleep(rng.uniform(0.0, 0.08))  # land the kill at a random point inside the write cycle
        kill_tree(proc)
        tail = proc.stdout.read().split()
        if tail:
            last_ack = max(last_ack, int(tail[-1]))
        project = Workspace(tmp_path / "ws").project(pid)  # a fresh process opening the folder
        doc, info = project.load()
        assert not info.recovered_from_backup, f"iteration {i}: main file was damaged by the kill"
        assert doc.revision in (last_ack, last_ack + 1), (
            f"iteration {i}: lost an acknowledged save ({doc.revision} < {last_ack})"
        )
        assert doc.script.startswith("x" * 900000)
    leftovers = [p.name for p in (tmp_path / "ws" / "projects" / pid).iterdir() if p.name.endswith(".tmp")]
    assert len(leftovers) <= 2  # at most interrupted temp files; they are ignored and cleaned on the next open
    assert [x["name"] for x in Workspace(tmp_path / "ws").list_projects()] == ["Crash test"]  # index consistent too


@pytest.mark.ffmpeg
def test_killing_the_worker_during_import_leaves_a_consistent_project(tmp_path: Path, tc: Toolchain) -> None:
    from storymotion_media.studio.assets import AssetService

    ws = Workspace(tmp_path / "ws")
    pid = ws.create("Import crash").projectId
    vid = big_video(tc, tmp_path / "src" / "long.mp4")
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", CHILD_IMPORT, str(tmp_path / "ws"), pid, str(vid)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert proc.stdout is not None
    assert "PROGRESS" in proc.stdout.readline()  # the import has started
    time.sleep(0.8)  # somewhere between copying and the preview transcode
    kill_tree(proc)
    out = proc.stdout.read()
    assert "DONE" not in out, "the import finished before the kill; make the source larger"

    project = Workspace(tmp_path / "ws").project(pid)
    doc, info = project.load()
    assert not info.recovered_from_backup and doc.name == "Import crash"  # the project document is intact
    svc = AssetService(project, tc)
    removed = svc.cleanup_orphans(min_age_s=0)  # what the worker does on its first open after a crash
    assets = svc.list_assets()
    assert assets == [] or all(a["status"] == "ok" for a in assets)
    for a in assets:  # any row that exists must have every file it refers to
        for rel in (a["rel_path"], a["thumb_rel"], a["proxy_rel"]):
            assert rel is None or (project.dir / rel).exists()
    for sub in ("assets", "thumbs", "proxies"):  # nothing half-written is left behind
        names = [f.name for f in (project.dir / sub).iterdir()]
        assert not [n for n in names if n.endswith(".part")], names
        assert len(names) == sum(
            1 for a in assets for k in ("rel_path", "thumb_rel", "proxy_rel") if a[k] and a[k].startswith(sub)
        )
    assert removed or assets  # either the crash left debris that we removed, or the import had already committed
    again = svc.import_files([str(vid)])  # and the import can simply be run again
    assert len(again.imported) + len(again.duplicates) == 1 and again.errors == []


@pytest.mark.ffmpeg
def test_killing_the_api_server_mid_job_is_recovered_on_restart(tmp_path: Path, tc: Toolchain) -> None:
    vid = big_video(tc, tmp_path / "src" / "long.mp4")
    ws_dir = tmp_path / "ws"

    def start() -> tuple[subprocess.Popen[str], int, str]:
        proc = subprocess.Popen(  # noqa: S603
            [sys.executable, "-m", "storymotion_media", "serve", "--workspace", str(ws_dir)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert proc.stdout is not None
        ready = json.loads(proc.stdout.readline())
        return proc, ready["port"], ready["token"]

    def call(port: int, token: str, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        conn.request(
            method,
            path,
            body=json.dumps(body) if body is not None else None,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Host": f"127.0.0.1:{port}",
            },
        )
        r = conn.getresponse()
        data = json.loads(r.read() or b"null")
        conn.close()
        return r.status, data

    proc, port, token = start()
    pid = call(port, token, "POST", "/api/projects", {"name": "Server crash"})[1]["projectId"]
    st, job = call(port, token, "POST", f"/api/projects/{pid}/assets/import", {"paths": [str(vid)], "mode": "copy"})
    assert st == 202
    for _ in range(100):  # wait until it is really running
        if call(port, token, "GET", f"/api/projects/{pid}/jobs/{job['id']}")[1]["state"] == "running":
            break
        time.sleep(0.05)
    time.sleep(0.3)
    kill_tree(proc)  # the whole worker dies mid-import

    proc2, port2, token2 = start()  # the lock is released by the OS, so a restart works immediately
    try:
        st, body = call(port2, token2, "GET", f"/api/projects/{pid}")
        assert st == 200 and body["document"]["name"] == "Server crash"
        jobs = call(port2, token2, "GET", f"/api/projects/{pid}/jobs")[1]["jobs"]
        assert jobs[0]["id"] == job["id"] and jobs[0]["state"] == "interrupted" and "safe" in jobs[0]["error"]
        assets = call(port2, token2, "GET", f"/api/projects/{pid}/assets")[1]["assets"]  # also runs the orphan cleanup
        proj_dir = ws_dir / "projects" / pid
        referenced = {a[k] for a in assets for k in ("rel_path", "thumb_rel", "proxy_rel") if a[k]}
        on_disk = {f"{sub}/{f.name}" for sub in ("assets", "thumbs", "proxies") for f in (proj_dir / sub).iterdir()}
        assert on_disk == referenced, f"orphans left: {on_disk - referenced}"
        st, job2 = call(
            port2, token2, "POST", f"/api/projects/{pid}/assets/import", {"paths": [str(vid)], "mode": "copy"}
        )
        for _ in range(600):
            j = call(port2, token2, "GET", f"/api/projects/{pid}/jobs/{job2['id']}")[1]
            if j["state"] in ("completed", "failed", "cancelled"):
                break
            time.sleep(0.1)
        assert j["state"] == "completed"
        assert len(call(port2, token2, "GET", f"/api/projects/{pid}/assets")[1]["assets"]) == 1
    finally:
        kill_tree(proc2)


def test_a_second_worker_on_the_same_workspace_is_refused_and_a_crash_releases_the_lock(tmp_path: Path) -> None:
    ws_dir = tmp_path / "ws"
    cmd = [sys.executable, "-m", "storymotion_media", "serve", "--workspace", str(ws_dir)]
    first = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)  # noqa: S603
    try:
        assert first.stdout is not None and json.loads(first.stdout.readline())["event"] == "ready"
        second = subprocess.run(cmd, capture_output=True, text=True, timeout=60)  # noqa: S603
        assert second.returncode != 0 and "already open" in second.stderr
    finally:
        kill_tree(first)
    third = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)  # noqa: S603
    try:
        assert (
            third.stdout is not None and json.loads(third.stdout.readline())["event"] == "ready"
        )  # no stale lock after a crash
    finally:
        kill_tree(third)
