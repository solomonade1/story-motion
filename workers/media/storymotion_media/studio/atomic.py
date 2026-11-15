"""Crash-safe file writes: temp file + fsync + atomic replace, keeping one prior version."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from .errors import StorageError


def _fsync_dir(path: Path) -> None:
    try:  # directories cannot be fsynced on Windows; best effort elsewhere
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def atomic_write_text(target: Path, text: str, *, keep_backup: bool = True) -> None:
    """Write ``text`` to ``target`` so a crash at any instant leaves a complete old or new file.

    Order: write+fsync temp -> copy current to ``<name>.bak`` (via temp) -> ``os.replace`` temp over target.
    The target itself is never opened for writing, so it cannot be left half-written.
    """
    tmp = target.with_name(target.name + ".tmp")
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        if keep_backup and target.exists():
            bak = target.with_name(target.name + ".bak")
            bak_tmp = bak.with_name(bak.name + ".tmp")
            shutil.copyfile(target, bak_tmp)
            os.replace(bak_tmp, bak)
        os.replace(tmp, target)
        _fsync_dir(target.parent)
    except OSError as exc:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise StorageError(
            f"Could not save {target.name}: {exc.strerror or exc}. "
            "Check that the disk has free space and the folder is writable. Your previous version is untouched."
        ) from exc


def rename_with_retry(src: Path, dst: Path, *, attempts: int = 8, delay: float = 0.05) -> None:
    """Rename a folder/file, retrying briefly on transient Windows 'Access is denied' errors.

    Virus scanners and indexers often hold a newly written file for a few milliseconds, which makes a directory
    rename fail once. The retry is bounded; a persistent failure is raised unchanged.
    """
    for i in range(attempts):
        try:
            src.rename(dst)
            return
        except PermissionError:
            if i == attempts - 1:
                raise
            time.sleep(delay * (i + 1))
