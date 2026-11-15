"""Project lifecycle, atomic saves, corruption recovery, migrations (FR-PROJ-001..004; QG DATA-01/02/07, F-08)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from storymotion_media.studio import atomic
from storymotion_media.studio.errors import (
    InvalidInput,
    ProjectCorrupt,
    ProjectNotFound,
    SchemaTooNew,
    StaleRevision,
    StorageError,
)
from storymotion_media.studio.migrations import CURRENT, migrate
from storymotion_media.studio.store import Workspace


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "ws")


def test_create_list_reopen_rename_archive(ws: Workspace, tmp_path: Path) -> None:
    a = ws.create("  Hezekiah  ")
    b = ws.create("Jonah")
    assert a.name == "Hezekiah" and a.schemaVersion == CURRENT and a.revision == 0
    assert {p["name"] for p in ws.list_projects()} == {"Hezekiah", "Jonah"}
    ws.rename(a.projectId, "Hezekiah v2")
    ws.set_archived(b.projectId, True)
    ws2 = Workspace(tmp_path / "ws")  # a fresh process opening the same folder
    assert [p["name"] for p in ws2.list_projects()] == ["Hezekiah v2"]
    assert [p["name"] for p in ws2.list_projects(archived=True)] == ["Jonah"]
    doc, info = ws2.project(a.projectId).load()
    assert doc.name == "Hezekiah v2" and doc.revision == 1 and not info.recovered_from_backup
    ws2.set_archived(b.projectId, False)
    assert len(ws2.list_projects()) == 2


@pytest.mark.parametrize("bad", ["", "   ", "x" * 121, "a\x00b", "line\nbreak", 5, None])
def test_invalid_names_rejected(ws: Workspace, bad: object) -> None:
    with pytest.raises(InvalidInput):
        ws.create(bad)  # type: ignore[arg-type]


def test_hostile_names_are_plain_text_never_paths(ws: Workspace) -> None:
    d = ws.create("../../evil; rm -rf / & $(x)")
    folders = sorted(p.name for p in ws.projects_dir.iterdir())
    assert folders == [d.projectId] and d.projectId.startswith("p-") and len(folders[0]) == 14
    for bad in ("../x", "p-123", "p-zzzzzzzzzzzz", "", "p-0123456789ab/../.."):
        with pytest.raises(InvalidInput):
            ws.project(bad)
    with pytest.raises(ProjectNotFound):
        ws.project("p-0123456789ab")


def test_duplicate_is_independent(ws: Workspace) -> None:
    a = ws.create("Original")
    p = ws.project(a.projectId)
    p.update({"script": "line one"}, base_revision=0)
    (p.dir / "assets" / "x.bin").write_bytes(b"data")
    with p.db() as con:
        con.execute(
            "INSERT INTO jobs(id,kind,state,created_at,updated_at) VALUES('j-000000000001','t','completed','n','n')"
        )
    c = ws.duplicate(a.projectId)
    assert c.projectId != a.projectId and c.name == "Original (copy)" and c.revision == 0
    cp = ws.project(c.projectId)
    assert (cp.dir / "assets" / "x.bin").read_bytes() == b"data" and cp.load()[0].script == "line one"
    with cp.db() as con:
        assert con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] == 1
    cp.update({"script": "changed copy"}, base_revision=0)
    assert p.load()[0].script == "line one"  # the original is untouched
    assert not list(ws.projects_dir.glob("*.tmp"))


def test_delete_goes_to_trash_and_can_be_restored_or_purged(ws: Workspace) -> None:
    a = ws.create("Doomed")
    t = ws.delete(a.projectId)
    assert ws.list_projects() == [] and [x["name"] for x in ws.trash_list()] == ["Doomed"]
    with pytest.raises(ProjectNotFound):
        ws.project(a.projectId)
    assert ws.restore(t).name == "Doomed" and len(ws.list_projects()) == 1
    t2 = ws.delete(a.projectId)
    with pytest.raises(InvalidInput):
        ws.purge(t2, confirm=False)
    assert ws.trash_list()  # still there
    ws.purge(t2, confirm=True)
    assert ws.trash_list() == []
    with pytest.raises(ProjectNotFound):
        ws.purge("p-0123456789ab-20260101T000000Z", confirm=True)
    with pytest.raises(ProjectNotFound):
        ws.restore("../../etc")


def test_stale_revision_and_unknown_fields(ws: Workspace) -> None:
    p = ws.project(ws.create("P").projectId)
    d1 = p.update({"script": "a"}, base_revision=0)
    assert d1.revision == 1
    with pytest.raises(StaleRevision):
        p.update({"script": "b"}, base_revision=0)
    with pytest.raises(InvalidInput):
        p.update({"name": "hack"}, base_revision=1)
    with pytest.raises(InvalidInput):
        p.update({"video": {"width": 1920, "height": 1080, "fps": 25}}, base_revision=1)
    assert p.load()[0].script == "a"


def test_crash_during_save_leaves_a_complete_old_or_new_file(ws: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    """F-08 (simulated): the final rename fails; project.json must still be the complete previous version."""
    p = ws.project(ws.create("P").projectId)
    p.update({"script": "good"}, base_revision=0)
    real_replace = os.replace

    def boom(src: object, dst: object) -> None:
        if str(dst).endswith("project.json"):
            raise OSError(28, "No space left on device")
        real_replace(src, dst)  # type: ignore[arg-type]

    monkeypatch.setattr(atomic.os, "replace", boom)
    with pytest.raises(StorageError, match="previous version is untouched"):
        p.update({"script": "bad"}, base_revision=1)
    monkeypatch.undo()
    doc, info = p.load()
    assert doc.script == "good" and doc.revision == 1 and not info.recovered_from_backup
    assert not list(p.dir.glob("*.tmp"))


def test_corrupt_main_file_recovers_from_backup_and_keeps_evidence(ws: Workspace) -> None:
    p = ws.project(ws.create("P").projectId)
    p.update({"script": "v1"}, base_revision=0)
    p.update({"script": "v2"}, base_revision=1)  # .bak now holds v1
    p.doc_path.write_text('{"schemaVersion": "1.0.0", "projectId": ', encoding="utf-8")  # truncated mid-write
    doc, info = p.load()
    assert info.recovered_from_backup and doc.script == "v1" and "previous saved version" in info.warnings[0]
    assert list(p.dir.glob("project.json.corrupt-*"))  # the damaged file is kept, not destroyed
    again, info2 = p.load()
    assert again.script == "v1" and not info2.recovered_from_backup  # main repaired
    good_backup = json.loads(p.doc_path.with_name("project.json.bak").read_text(encoding="utf-8"))
    assert good_backup["script"] == "v1"  # the good backup was not overwritten by the damaged file


def test_both_files_corrupt_is_reported_without_touching_anything(ws: Workspace) -> None:
    p = ws.project(ws.create("P").projectId)
    p.update({"script": "x"}, base_revision=0)
    bak = p.doc_path.with_name("project.json.bak")
    p.doc_path.write_text("garbage", encoding="utf-8")
    bak.write_text("also garbage", encoding="utf-8")
    before = (p.doc_path.read_bytes(), bak.read_bytes())
    with pytest.raises(ProjectCorrupt, match="copy the project folder"):
        p.load()
    assert (p.doc_path.read_bytes(), bak.read_bytes()) == before


def test_one_bad_project_does_not_hide_the_others(ws: Workspace, tmp_path: Path) -> None:
    good = ws.create("Good")
    bad = ws.create("Bad")
    bp = ws.project(bad.projectId)
    bp.doc_path.write_text("nope", encoding="utf-8")
    bp.doc_path.with_name("project.json.bak").unlink(missing_ok=True)
    ws2 = Workspace(tmp_path / "ws")
    assert [p["id"] for p in ws2.list_projects()] == [good.projectId]


def test_migration_from_prerelease_layout_is_preserved_and_repeatable(ws: Workspace) -> None:
    pid = "p-aaaaaaaaaaaa"
    folder = ws.projects_dir / pid
    folder.mkdir()
    old = {"projectId": pid, "title": "Old project", "created": "2026-01-02T03:04:05Z", "script": "keep me"}
    (folder / "project.json").write_text(json.dumps(old), encoding="utf-8")
    p = ws.project(pid)
    doc, info = p.load()
    assert info.migrated == ["0.0.0->1.0.0"] and doc.name == "Old project" and doc.script == "keep me"
    assert doc.createdAt == "2026-01-02T03:04:05Z" and doc.schemaVersion == CURRENT and doc.video.fps == 24
    pre = list(folder.glob("project.json.premigration-*"))
    assert len(pre) == 1 and json.loads(pre[0].read_text(encoding="utf-8")) == old  # original content preserved
    doc2, info2 = p.load()
    assert info2.migrated == [] and doc2 == doc  # repeatable: nothing left to migrate
    assert migrate(doc.model_dump())[1] == []  # idempotent on a current document


def test_newer_schema_is_refused_unchanged(ws: Workspace) -> None:
    p = ws.project(ws.create("P").projectId)
    data = json.loads(p.doc_path.read_text(encoding="utf-8"))
    data["schemaVersion"] = "2.0.0"
    p.doc_path.write_text(json.dumps(data), encoding="utf-8")
    before = p.doc_path.read_bytes()
    with pytest.raises((SchemaTooNew, ProjectCorrupt)):
        p.load()
    assert p.doc_path.read_bytes() == before


def test_index_is_rebuilt_from_folders(ws: Workspace, tmp_path: Path) -> None:
    ws.create("A")
    ws.create("B")
    (tmp_path / "ws" / "index.sqlite").unlink()
    for extra in ("index.sqlite-wal", "index.sqlite-shm"):
        (tmp_path / "ws" / extra).unlink(missing_ok=True)
    assert {p["name"] for p in Workspace(tmp_path / "ws").list_projects()} == {"A", "B"}


def test_unwritable_workspace_gives_actionable_error(tmp_path: Path) -> None:
    blocker = tmp_path / "file-not-folder"
    blocker.write_text("x")
    with pytest.raises(StorageError, match="Choose a folder you can write to"):
        Workspace(blocker / "ws")


def test_the_live_project_file_is_never_opened_for_writing(ws: Workspace, monkeypatch: pytest.MonkeyPatch) -> None:
    """The atomic-save invariant: project.json changes only by renaming a finished temp file over it, so no instant exists
    at which a crash could leave it half-written. (A random kill test cannot reliably hit that tiny window.)"""
    import shutil

    p = ws.project(ws.create("P").projectId)
    p.update({"script": "first"}, base_revision=0)  # make sure a previous version (and .bak) exist
    target = p.doc_path.resolve()
    touched: list[str] = []
    real_open, real_copy = Path.open, shutil.copyfile

    def spy_open(self: Path, mode: str = "r", *a: object, **k: object):  # noqa: ANN202
        if self.resolve() == target and any(c in mode for c in "wax+"):
            touched.append(f"open({mode})")
        return real_open(self, mode, *a, **k)  # type: ignore[arg-type]

    def spy_copy(src: object, dst: object, *a: object, **k: object):  # noqa: ANN202
        if Path(str(dst)).resolve() == target:
            touched.append("copyfile")
        return real_copy(src, dst, *a, **k)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", spy_open)
    monkeypatch.setattr(shutil, "copyfile", spy_copy)
    for i in range(3):
        p.update({"script": f"v{i}" * 1000}, base_revision=p.load()[0].revision)
    assert touched == []
