"""Background jobs with persisted state, progress, cancellation and restart recovery.

State machine (explicit; anything else raises): queued -> running -> completed | failed | cancelled.
A job still ``queued``/``running`` when the worker starts again is marked ``interrupted`` (the process died);
because each imported file is committed on its own, an interrupted import never leaves a half-written asset.
There are no hidden background processes: jobs run on a small thread pool owned by this object and are listed in the UI.
"""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .errors import InvalidInput, JobCancelled, StudioError
from .paths import JOB_ID_RE, new_id
from .store import Project, now_iso

LEGAL = {
    "queued": {"running", "cancelled"},
    "running": {"completed", "failed", "cancelled"},
}
TERMINAL = {"completed", "failed", "cancelled", "interrupted"}
Work = Callable[[Callable[[float, str], None], threading.Event], dict[str, Any]]


class JobManager:
    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="storymotion-job")
        self._cancel: dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ persistence helpers
    @staticmethod
    def _row(row: Any) -> dict[str, Any]:
        d = dict(row)
        d["result"] = json.loads(d.pop("result_json")) if d.get("result_json") else None
        d["params"] = json.loads(d.pop("params_json")) if d.get("params_json") else None
        return d

    def _transition(self, project: Project, jid: str, new: str, **fields: Any) -> None:
        with project.db() as con:
            row = con.execute("SELECT state FROM jobs WHERE id=?", (jid,)).fetchone()
            if row is None:
                raise StudioError("Unknown job.")
            cur = row["state"]
            if new != cur and new not in LEGAL.get(cur, set()):
                raise StudioError(f"A job cannot go from '{cur}' to '{new}'.")
            sets = {"state": new, "updated_at": now_iso(), **fields}
            con.execute(f"UPDATE jobs SET {','.join(f'{k}=?' for k in sets)} WHERE id=?", (*sets.values(), jid))  # noqa: S608

    def _progress(self, project: Project, jid: str, frac: float, msg: str) -> None:
        with project.db() as con:
            con.execute(
                "UPDATE jobs SET progress=?, message=?, updated_at=? WHERE id=? AND state='running'",
                (max(0.0, min(1.0, frac)), msg[:300], now_iso(), jid),
            )

    # ------------------------------------------------------------------ public API
    def start(self, project: Project, kind: str, params: dict[str, Any], work: Work) -> dict[str, Any]:
        jid = new_id("j")
        now = now_iso()
        with project.db() as con:
            con.execute(
                "INSERT INTO jobs(id,kind,state,progress,message,params_json,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (jid, kind, "queued", 0.0, "Waiting to start", json.dumps(params)[:20000], now, now),
            )
        ev = threading.Event()
        with self._lock:
            self._cancel[jid] = ev
        self._pool.submit(self._run, project, jid, work, ev)
        return self.get(project, jid)

    def _run(self, project: Project, jid: str, work: Work, ev: threading.Event) -> None:
        try:
            if ev.is_set():
                self._transition(project, jid, "cancelled", message="Cancelled before it started")
                return
            self._transition(project, jid, "running", message="Starting")
            last = [0.0]

            def report(frac: float, msg: str) -> None:  # throttled: at most ~5 database writes per second
                if time.monotonic() - last[0] > 0.2 or frac >= 1.0:
                    last[0] = time.monotonic()
                    self._progress(project, jid, frac, msg)

            result = work(report, ev)
            if result.get("cancelled") or ev.is_set():
                self._transition(project, jid, "cancelled", message="Cancelled", result_json=json.dumps(result))
            else:
                self._transition(
                    project, jid, "completed", progress=1.0, message="Done", result_json=json.dumps(result)
                )
        except JobCancelled:
            self._transition(project, jid, "cancelled", message="Cancelled")
        except StudioError as exc:
            self._fail(project, jid, str(exc))
        except Exception as exc:  # never let a worker thread die silently: record a readable failure
            self._fail(
                project, jid, f"Something went wrong ({type(exc).__name__}: {str(exc)[:200]}). Nothing was half-saved."
            )
        finally:
            with self._lock:
                self._cancel.pop(jid, None)

    def _fail(self, project: Project, jid: str, msg: str) -> None:
        try:
            self._transition(project, jid, "failed", message="Failed", error=msg[:600])
        except StudioError:
            pass

    def cancel(self, project: Project, jid: str) -> dict[str, Any]:
        if not JOB_ID_RE.match(jid):
            raise InvalidInput("That is not a valid job id.")
        job = self.get(project, jid)
        if job["state"] in TERMINAL:
            return job
        with self._lock:
            ev = self._cancel.get(jid)
        if ev is not None:
            ev.set()
        return self.get(project, jid)

    def get(self, project: Project, jid: str) -> dict[str, Any]:
        if not JOB_ID_RE.match(jid):
            raise InvalidInput("That is not a valid job id.")
        with project.db() as con:
            row = con.execute("SELECT * FROM jobs WHERE id=?", (jid,)).fetchone()
        if row is None:
            raise StudioError("Unknown job.")
        return self._row(row)

    def list_jobs(self, project: Project, limit: int = 50) -> list[dict[str, Any]]:
        with project.db() as con:
            rows = con.execute("SELECT * FROM jobs ORDER BY created_at DESC, id DESC LIMIT ?", (limit,)).fetchall()
        return [self._row(r) for r in rows]

    def reconcile(self, project: Project) -> int:
        """Called when a project is opened: jobs that were running when the process died become 'interrupted'."""
        with self._lock:
            live = set(self._cancel)
        n = 0
        with project.db() as con:
            for row in con.execute("SELECT id FROM jobs WHERE state IN ('queued','running')").fetchall():
                if row["id"] in live:
                    continue
                con.execute(
                    "UPDATE jobs SET state='interrupted', updated_at=?, message=?, error=? WHERE id=?",
                    (
                        now_iso(),
                        "Interrupted",
                        "The app closed or crashed while this was running. Files already imported are safe; run it again to finish.",
                        row["id"],
                    ),
                )
                n += 1
        return n

    def wait(self, project: Project, jid: str, timeout: float = 60.0) -> dict[str, Any]:
        """Test/CLI helper: block until the job is terminal."""
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            job = self.get(project, jid)
            if job["state"] in TERMINAL:
                return job
            time.sleep(0.05)
        raise StudioError("The job did not finish in time.")

    def shutdown(self) -> None:
        with self._lock:
            for ev in self._cancel.values():
                ev.set()
        self._pool.shutdown(wait=True, cancel_futures=True)
