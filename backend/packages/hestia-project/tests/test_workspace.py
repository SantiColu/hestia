import json
import os
from pathlib import Path

import pytest

from hestia_project.catalog import TemplateId
from hestia_project.errors import (
    NoPathError,
    NoProjectOpenError,
    ProjectLockedError,
    UnsavedChangesError,
)
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.lock import lock_path, read_lock
from hestia_project.schematic import Blueprint, create_system
from hestia_project.workspace import EventType, ProjectEvent, Workspace

AUTHOR = Author(kind=ActorKind.HUMAN, name="ana")


@pytest.fixture
def ws(tmp_path: Path) -> Workspace:
    return Workspace(tmp_path / "home")


def _add_phase0(ws: Workspace) -> None:
    ws.apply(
        Operation.CREATE_SYSTEM,
        AUTHOR,
        "",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )


def _write_foreign_lock(path: Path, pid: int, host: str | None = None) -> None:
    import socket

    lock_path(path).write_text(
        json.dumps(
            {
                "instance_id": "other",
                "pid": pid,
                "host": host or socket.gethostname(),
                "user": "bob",
                "acquired_at": "2026-01-01T00:00:00Z",
            }
        )
    )


def test_requires_open_project(ws: Workspace) -> None:
    with pytest.raises(NoProjectOpenError):
        ws.view()


def test_new_save_as_open_roundtrip(ws: Workspace, tmp_path: Path) -> None:
    ws.new_project()
    _add_phase0(ws)
    assert ws.view().document.dirty
    with pytest.raises(NoPathError):
        ws.save()

    view = ws.save_as(tmp_path / "SAT-M1")
    assert view.document.file_name == "SAT-M1.hestia"
    assert view.project.name == "SAT-M1"
    assert not view.document.dirty
    assert read_lock(tmp_path / "SAT-M1.hestia") is not None
    saved = view.project

    ws.close()
    assert not lock_path(tmp_path / "SAT-M1.hestia").exists()

    reopened = ws.open_project(tmp_path / "SAT-M1.hestia")
    assert reopened.project == saved
    assert len(ws.history()) == 1
    assert not reopened.document.can_undo  # undo stacks are per session


def test_save_writes_changes(ws: Workspace, tmp_path: Path) -> None:
    ws.new_project()
    path = tmp_path / "a.hestia"
    ws.save_as(path)
    _add_phase0(ws)
    ws.save()
    ws.close()
    assert len(ws.open_project(path).project.systems) == 1


def test_save_as_moves_lock(ws: Workspace, tmp_path: Path) -> None:
    ws.new_project()
    ws.save_as(tmp_path / "a.hestia")
    ws.save_as(tmp_path / "b.hestia")
    assert not lock_path(tmp_path / "a.hestia").exists()
    assert lock_path(tmp_path / "b.hestia").exists()
    assert (tmp_path / "a.hestia").exists()


def test_unsaved_changes_guard(ws: Workspace, tmp_path: Path) -> None:
    ws.new_project()
    _add_phase0(ws)
    with pytest.raises(UnsavedChangesError):
        ws.close()
    with pytest.raises(UnsavedChangesError):
        ws.new_project()
    ws.new_project(discard_unsaved=True)
    assert ws.view().project.systems == []
    ws.close()  # clean: no guard


def test_lock_held_by_other_instance(ws: Workspace, tmp_path: Path) -> None:
    path = tmp_path / "a.hestia"
    ws.new_project()
    ws.save_as(path)
    ws.close()
    _write_foreign_lock(path, os.getppid())
    other = Workspace(tmp_path / "home2")
    with pytest.raises(ProjectLockedError) as info:
        other.open_project(path)
    assert info.value.details["holder"]["user"] == "bob"
    other.open_project(path, force=True)
    holder = read_lock(path)
    assert holder is not None and holder.instance_id == other.instance_id


def test_two_workspaces_cannot_open_same_file(tmp_path: Path) -> None:
    path = tmp_path / "a.hestia"
    first = Workspace(tmp_path / "h1")
    first.new_project()
    first.save_as(path)
    second = Workspace(tmp_path / "h2")
    with pytest.raises(ProjectLockedError):
        second.open_project(path)
    first.close()
    second.open_project(path)


def test_stale_lock_is_taken_over(ws: Workspace, tmp_path: Path) -> None:
    path = tmp_path / "a.hestia"
    ws.new_project()
    ws.save_as(path)
    ws.close()
    _write_foreign_lock(path, pid=2**22 + 12345)  # no such process
    ws.open_project(path)


def test_remote_lock_is_not_stale(ws: Workspace, tmp_path: Path) -> None:
    path = tmp_path / "a.hestia"
    ws.new_project()
    ws.save_as(path)
    ws.close()
    _write_foreign_lock(path, pid=2**22 + 12345, host="another-machine")
    with pytest.raises(ProjectLockedError):
        ws.open_project(path)


def test_recents_mark_missing_files(ws: Workspace, tmp_path: Path) -> None:
    for name in ("a", "b"):
        ws.new_project(discard_unsaved=True)
        ws.save_as(tmp_path / name)
    ws.close()
    (tmp_path / "a.hestia").unlink()
    recents = ws.recent_projects()
    assert [(Path(r.path).name, r.exists) for r in recents] == [
        ("b.hestia", True),
        ("a.hestia", False),
    ]
    assert ws.recents.remove(recents[1].path)
    assert len(ws.recent_projects()) == 1


def test_events(ws: Workspace, tmp_path: Path) -> None:
    events: list[ProjectEvent] = []
    ws.subscribe(events.append)
    ws.new_project()
    _add_phase0(ws)
    ws.undo(AUTHOR)
    ws.save_as(tmp_path / "a")
    ws.close()
    assert [e.type for e in events] == [
        EventType.PROJECT_CREATED,
        EventType.PROJECT_CHANGED,
        EventType.PROJECT_CHANGED,
        EventType.PROJECT_SAVED,
        EventType.PROJECT_CLOSED,
    ]
    assert events[1].change is not None
    assert events[1].change.operation is Operation.CREATE_SYSTEM
    assert events[2].revision == 2
