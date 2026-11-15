"""Workspace + project persistence: versioned project JSON, SQLite metadata, safe lifecycle operations.

Layout (docs/PROJECT_LAYOUT.md, schema 1.0.0 of the *project document*):
  <workspace>/index.sqlite                   fast project list (a cache; rebuilt from the folders by ``rescan``)
  <workspace>/projects/<p-id>/project.json   source of truth for the project document (+ .bak, atomic writes)
  <workspace>/projects/<p-id>/project.sqlite assets and jobs
  <workspace>/projects/<p-id>/{assets,thumbs,proxies}/
  <workspace>/.trash/<p-id>-<UTC stamp>/     deleted projects (recoverable until purged)
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .atomic import atomic_write_text, rename_with_retry
from .errors import InvalidInput, ProjectCorrupt, ProjectNotFound, StaleRevision, StorageError
from .migrations import CURRENT, migrate
from .paths import TRASH_RE, check_project_id, new_id, validate_name

PROJECT_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS assets (
  id TEXT PRIMARY KEY, sha256 TEXT NOT NULL UNIQUE, category TEXT NOT NULL, kind TEXT NOT NULL,
  mode TEXT NOT NULL, rel_path TEXT, abs_path TEXT, orig_name TEXT NOT NULL, size INTEGER NOT NULL,
  mtime_ns INTEGER, width INTEGER, height INTEGER, duration_ms INTEGER, fps REAL, sample_rate INTEGER,
  channels INTEGER, thumb_rel TEXT, proxy_rel TEXT, status TEXT NOT NULL DEFAULT 'ok', status_detail TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY, kind TEXT NOT NULL, state TEXT NOT NULL, progress REAL NOT NULL DEFAULT 0,
  message TEXT, result_json TEXT, error TEXT, params_json TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
"""


def now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class VideoSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    width: int = Field(default=1920, gt=0)
    height: int = Field(default=1080, gt=0)
    fps: Literal[24, 30] = 24


class ProjectDoc(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schemaVersion: str
    projectId: str
    name: str
    createdAt: str
    updatedAt: str
    revision: int = Field(ge=0)
    archived: bool = False
    video: VideoSettings = Field(default_factory=VideoSettings)
    script: str = ""
    notes: str = ""
    ext: dict[str, Any] = Field(default_factory=dict)  # reserved for later phases (plan, tracks)


EDITABLE = {"script", "notes", "video", "ext"}
MAX_TEXT = 2_000_000


@dataclass
class LoadInfo:
    recovered_from_backup: bool = False
    migrated: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _parse(path: Path) -> tuple[ProjectDoc, list[str]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("document is not a JSON object")
    doc, applied = migrate(raw)
    return ProjectDoc.model_validate(doc), applied


class Project:
    def __init__(self, ws: Workspace, pid: str, folder: Path) -> None:
        self.ws, self.id, self.dir = ws, pid, folder
        self.doc_path = folder / "project.json"
        self.db_path = folder / "project.sqlite"
        self.lock = ws.lock_for(pid)

    # ---- document
    def load(self) -> tuple[ProjectDoc, LoadInfo]:
        info = LoadInfo()
        errors: list[str] = []
        with self.lock:
            for label, path in (
                ("project.json", self.doc_path),
                ("project.json.bak", self.doc_path.with_name("project.json.bak")),
            ):
                if not path.exists():
                    errors.append(f"{label}: missing")
                    continue
                try:
                    doc, applied = _parse(path)
                except (ValueError, ValidationError, OSError) as exc:
                    errors.append(f"{label}: {str(exc).splitlines()[0][:160]}")
                    continue
                if label.endswith(".bak"):
                    info.recovered_from_backup = True
                    info.warnings.append(
                        "The latest project file was damaged, so the previous saved version was restored. "
                        "The damaged file was kept next to it."
                    )
                    self._quarantine_main()
                if applied:
                    info.migrated = applied
                    self._preserve_pre_migration(path)
                if info.recovered_from_backup or applied:
                    # when recovering, do NOT rotate: the damaged main file must not overwrite the good backup
                    self.write(doc, keep_backup=not info.recovered_from_backup)
                return doc, info
        raise ProjectCorrupt(
            "This project's files could not be read and no earlier version could be restored "
            f"({'; '.join(errors)}). Nothing was changed; copy the project folder somewhere safe before trying anything else."
        )

    def _quarantine_main(self) -> None:
        if self.doc_path.exists():
            stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            try:
                shutil.copyfile(self.doc_path, self.doc_path.with_name(f"project.json.corrupt-{stamp}"))
            except OSError:
                pass

    def _preserve_pre_migration(self, source: Path) -> None:
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        try:
            shutil.copyfile(source, self.doc_path.with_name(f"project.json.premigration-{stamp}"))
        except OSError:
            pass

    def write(self, doc: ProjectDoc, *, keep_backup: bool = True) -> None:
        text = json.dumps(doc.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
        atomic_write_text(self.doc_path, text, keep_backup=keep_backup)

    def update(self, patch: dict[str, Any], base_revision: int | None) -> ProjectDoc:
        """Autosave entry point: merge allowed fields, bump revision, write atomically."""
        unknown = set(patch) - EDITABLE
        if unknown:
            raise InvalidInput(f"These fields cannot be edited here: {', '.join(sorted(unknown))}.")
        for key in ("script", "notes"):
            if key in patch and (not isinstance(patch[key], str) or len(patch[key]) > MAX_TEXT):
                raise InvalidInput(f"'{key}' must be text of at most {MAX_TEXT} characters.")
        with self.lock:
            doc, _ = self.load()
            if base_revision is not None and base_revision != doc.revision:
                raise StaleRevision(
                    f"This project changed since you opened it (you have revision {base_revision}, "
                    f"the saved one is {doc.revision}). Reload before saving."
                )
            data = doc.model_dump()
            data.update(patch)
            data["revision"] = doc.revision + 1
            data["updatedAt"] = now_iso()
            try:
                new = ProjectDoc.model_validate(data)
            except ValidationError as exc:
                raise InvalidInput(f"Invalid project data: {exc.errors()[0]['loc']} {exc.errors()[0]['msg']}") from exc
            self.write(new)
            self.ws.index_upsert(new)
            return new

    # ---- sqlite
    @contextmanager
    def db(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.db_path, timeout=30, check_same_thread=False)
        try:
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            con.execute("PRAGMA foreign_keys=ON")
            con.executescript(PROJECT_SCHEMA_SQL)
            yield con
            con.commit()
        except sqlite3.Error as exc:
            con.rollback()
            raise StorageError(f"The project database could not be used: {exc}") from exc
        finally:
            con.close()


class Workspace:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.projects_dir = self.root / "projects"
        self.trash_dir = self.root / ".trash"
        self._locks: dict[str, threading.RLock] = {}
        self._locks_guard = threading.Lock()
        try:
            self.projects_dir.mkdir(parents=True, exist_ok=True)
            self.trash_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise StorageError(
                f"The workspace folder {self.root} cannot be created or written: {exc.strerror or exc}. "
                "Choose a folder you can write to."
            ) from exc
        self._index_path = self.root / "index.sqlite"
        with self._index() as con:
            con.execute(
                "CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL,"
                " updated_at TEXT NOT NULL, archived INTEGER NOT NULL DEFAULT 0)"
            )
        self._clean_stale_tmp()
        self.rescan()

    def _clean_stale_tmp(self) -> None:
        """A create/duplicate that was killed half-way leaves ``p-*.tmp``; nothing else can be using it at start-up."""
        for d in self.projects_dir.glob("p-*.tmp"):
            shutil.rmtree(d, ignore_errors=True)

    def lock_for(self, pid: str) -> threading.RLock:
        with self._locks_guard:
            return self._locks.setdefault(pid, threading.RLock())

    @contextmanager
    def _index(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self._index_path, timeout=30, check_same_thread=False)
        try:
            con.row_factory = sqlite3.Row
            con.execute("PRAGMA journal_mode=WAL")
            yield con
            con.commit()
        except sqlite3.Error as exc:
            con.rollback()
            raise StorageError(f"The project index could not be used: {exc}") from exc
        finally:
            con.close()

    def index_upsert(self, d: ProjectDoc) -> None:
        with self._index() as con:
            con.execute(
                "INSERT INTO projects(id,name,created_at,updated_at,archived) VALUES(?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET name=excluded.name, updated_at=excluded.updated_at, archived=excluded.archived",
                (d.projectId, d.name, d.createdAt, d.updatedAt, int(d.archived)),
            )

    def rescan(self) -> list[str]:
        """Rebuild the index from the project folders (the folders are the truth). Returns problems found."""
        problems: list[str] = []
        seen: set[str] = set()
        for folder in sorted(self.projects_dir.iterdir()) if self.projects_dir.exists() else []:
            if not folder.is_dir() or not folder.name.startswith("p-") or folder.name.endswith(".tmp"):
                continue
            try:
                check_project_id(folder.name)
                doc, _ = Project(self, folder.name, folder).load()
                self.index_upsert(doc)
                seen.add(doc.projectId)
            except Exception as exc:  # a broken project must not stop the others from listing
                problems.append(f"{folder.name}: {exc}")
        with self._index() as con:
            for row in con.execute("SELECT id FROM projects").fetchall():
                if row["id"] not in seen:
                    con.execute("DELETE FROM projects WHERE id=?", (row["id"],))
        return problems

    # ---- lifecycle
    def project(self, pid: str) -> Project:
        check_project_id(pid)
        folder = self.projects_dir / pid
        if not folder.is_dir():
            raise ProjectNotFound("That project no longer exists.")
        return Project(self, pid, folder)

    def create(self, name: str) -> ProjectDoc:
        name = validate_name(name)
        pid = new_id("p")
        tmp = self.projects_dir / f"{pid}.tmp"
        final = self.projects_dir / pid
        now = now_iso()
        doc = ProjectDoc(schemaVersion=CURRENT, projectId=pid, name=name, createdAt=now, updatedAt=now, revision=0)
        try:
            for sub in ("assets", "thumbs", "proxies"):
                (tmp / sub).mkdir(parents=True)
            Project(self, pid, tmp).write(doc)
            with Project(self, pid, tmp).db():
                pass
            rename_with_retry(tmp, final)  # the project appears all at once or not at all
        except (OSError, StorageError) as exc:
            shutil.rmtree(tmp, ignore_errors=True)
            raise StorageError(f"Could not create the project: {getattr(exc, 'strerror', None) or exc}") from exc
        self.index_upsert(doc)
        return doc

    def list_projects(self, *, archived: bool = False) -> list[dict[str, Any]]:
        with self._index() as con:
            rows = con.execute(
                "SELECT id,name,created_at,updated_at,archived FROM projects WHERE archived=? "
                "ORDER BY updated_at DESC, name",
                (int(archived),),
            ).fetchall()
        return [dict(r) for r in rows]

    def rename(self, pid: str, name: str) -> ProjectDoc:
        name = validate_name(name)
        p = self.project(pid)
        with p.lock:
            doc, _ = p.load()
            new = doc.model_copy(update={"name": name, "updatedAt": now_iso(), "revision": doc.revision + 1})
            p.write(new)
            self.index_upsert(new)
            return new

    def set_archived(self, pid: str, archived: bool) -> ProjectDoc:
        p = self.project(pid)
        with p.lock:
            doc, _ = p.load()
            new = doc.model_copy(
                update={"archived": bool(archived), "updatedAt": now_iso(), "revision": doc.revision + 1}
            )
            p.write(new)
            self.index_upsert(new)
            return new

    def duplicate(self, pid: str, name: str | None = None) -> ProjectDoc:
        src = self.project(pid)
        with src.lock:
            doc, _ = src.load()
            new_name = validate_name(name or f"{doc.name} (copy)")
            nid = new_id("p")
            tmp = self.projects_dir / f"{nid}.tmp"
            try:
                shutil.copytree(
                    src.dir,
                    tmp,
                    ignore=shutil.ignore_patterns(
                        "project.sqlite*", "*.tmp", "project.json.corrupt-*", "project.json.premigration-*"
                    ),
                )
                if src.db_path.exists():  # consistent copy even while the source database is in use
                    con = sqlite3.connect(src.db_path)
                    dst = sqlite3.connect(tmp / "project.sqlite")
                    try:
                        con.backup(dst)
                    finally:
                        dst.close()
                        con.close()
                now = now_iso()
                new = doc.model_copy(
                    update={
                        "projectId": nid,
                        "name": new_name,
                        "createdAt": now,
                        "updatedAt": now,
                        "revision": 0,
                        "archived": False,
                    }
                )
                Project(self, nid, tmp).write(new)
                rename_with_retry(tmp, self.projects_dir / nid)
            except (OSError, sqlite3.Error) as exc:
                shutil.rmtree(tmp, ignore_errors=True)
                raise StorageError(f"Could not duplicate the project: {getattr(exc, 'strerror', None) or exc}") from exc
        self.index_upsert(new)
        return new

    def delete(self, pid: str) -> str:
        """Move to the trash (recoverable). Returns the trash entry name."""
        p = self.project(pid)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        name = f"{pid}-{stamp}"
        with p.lock:
            try:
                rename_with_retry(p.dir, self.trash_dir / name)
            except OSError as exc:
                raise StorageError(
                    f"The project could not be moved to the trash ({exc.strerror or exc}). "
                    "Close anything that may be using its files and try again; nothing was deleted."
                ) from exc
        with self._index() as con:
            con.execute("DELETE FROM projects WHERE id=?", (pid,))
        return name

    def trash_list(self) -> list[dict[str, str]]:
        out = []
        for d in sorted(self.trash_dir.iterdir()):
            if d.is_dir() and TRASH_RE.match(d.name):
                try:
                    doc, _ = _parse(d / "project.json")
                    out.append({"trashId": d.name, "projectId": doc.projectId, "name": doc.name})
                except (ValueError, ValidationError, OSError):
                    out.append({"trashId": d.name, "projectId": d.name[:14], "name": "(unreadable project)"})
        return out

    def _trash_entry(self, trash_id: str) -> Path:
        if not TRASH_RE.match(trash_id) or not (self.trash_dir / trash_id).is_dir():
            raise ProjectNotFound("That item is not in the trash.")
        return self.trash_dir / trash_id

    def restore(self, trash_id: str) -> ProjectDoc:
        src = self._trash_entry(trash_id)
        pid = trash_id[:14]
        dest = self.projects_dir / pid
        if dest.exists():
            raise InvalidInput("A project with this id already exists; rename or delete it first.")
        rename_with_retry(src, dest)
        doc, _ = Project(self, pid, dest).load()
        self.index_upsert(doc)
        return doc

    def purge(self, trash_id: str, *, confirm: bool) -> None:
        """Permanent deletion. Requires explicit confirmation from the caller."""
        if not confirm:
            raise InvalidInput("Permanent deletion needs explicit confirmation.")
        shutil.rmtree(self._trash_entry(trash_id))
