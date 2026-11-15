"""One worker per workspace. An OS file lock is released automatically if the process dies, so it can never go stale."""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO

from .errors import StudioError


class WorkspaceLock:
    def __init__(self, root: Path) -> None:
        self.path = root / ".worker.lock"
        self._fh: IO[bytes] | None = None

    def acquire(self) -> None:
        fh = self.path.open("a+b")
        try:
            if os.name == "nt":
                import msvcrt

                if fh.seek(0, os.SEEK_END) == 0:
                    fh.write(b"x")
                    fh.flush()
                fh.seek(0)
                msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)  # type: ignore[attr-defined,unused-ignore]
            else:
                import fcntl

                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined,unused-ignore]
        except OSError as exc:
            fh.close()
            raise StudioError(
                "StoryMotion is already open on this workspace. Close the other window first "
                "(two copies working on the same projects could damage them)."
            ) from exc
        self._fh = fh

    def release(self) -> None:
        if self._fh is not None:
            self._fh.close()  # closing the handle drops the lock
            self._fh = None

    def __enter__(self) -> WorkspaceLock:
        self.acquire()
        return self

    def __exit__(self, *_a: object) -> None:
        self.release()
