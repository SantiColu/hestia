import sqlite3
from pathlib import Path

import pytest

from hestia_project.catalog import TemplateId
from hestia_project.document import ProjectDocument
from hestia_project.errors import ProjectFileError
from hestia_project.history import ActorKind, Author, Operation
from hestia_project.model import CellStatus, Provenance
from hestia_project.schematic import Blueprint, branch, create_system, delete_system, rename_cell
from hestia_project.storage import APPLICATION_ID, read_project, write_project

AUTHOR = Author(kind=ActorKind.AGENT, name="stefan")


def _document() -> ProjectDocument:
    doc = ProjectDocument.new("SAT-M1")
    doc.apply(
        Operation.CREATE_SYSTEM,
        AUTHOR,
        "base",
        lambda p: create_system(p, Blueprint(template=TemplateId.PHASE_0)),
    )
    doc.apply(
        Operation.BRANCH,
        AUTHOR,
        "variant",
        lambda p: branch(p, p.cells[0].id, Blueprint(template=TemplateId.PHASE_1)),
    )
    doc.apply(
        Operation.RENAME_CELL, AUTHOR, "", lambda p: rename_cell(p, p.cells[1].id, "Entorno SSO")
    )
    doc.undo(AUTHOR, "oops")
    return doc


def test_roundtrip(tmp_path: Path) -> None:
    doc = _document()
    doc.project.cells[0].status = CellStatus.FAILED
    doc.project.cells[0].provenance = Provenance(
        produced_at=doc.changes()[0].timestamp, code_version="0.1.0", input_cell_ids=["x"]
    )
    path = tmp_path / "sat.hestia"
    write_project(path, doc.project, doc.history)

    project, history = read_project(path)
    assert project == doc.project
    assert [r.change for r in history] == doc.changes()
    assert [r.before for r in history] == [r.before for r in doc.history]
    assert [r.after for r in history] == [r.after for r in doc.history]


def test_file_is_sqlite_with_hestia_ids(tmp_path: Path) -> None:
    path = tmp_path / "sat.hestia"
    write_project(path, _document().project, [])
    conn = sqlite3.connect(path)
    assert conn.execute("PRAGMA application_id").fetchone() == (APPLICATION_ID,)
    assert conn.execute("SELECT count(*) FROM cells").fetchone() == (11,)
    conn.close()
    assert [p.name for p in tmp_path.iterdir()] == ["sat.hestia"]  # no temp leftovers


def test_overwrite_is_atomic_replace(tmp_path: Path) -> None:
    path = tmp_path / "sat.hestia"
    doc = _document()
    write_project(path, doc.project, doc.history)
    delete_system(doc.project, doc.project.systems[-1].id)
    write_project(path, doc.project, doc.history)
    project, _ = read_project(path)
    assert len(project.systems) == 1


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ProjectFileError, match="No existe"):
        read_project(tmp_path / "nope.hestia")


def test_not_a_database(tmp_path: Path) -> None:
    path = tmp_path / "junk.hestia"
    path.write_text("hello")
    with pytest.raises(ProjectFileError):
        read_project(path)


def test_foreign_sqlite_file(tmp_path: Path) -> None:
    path = tmp_path / "other.hestia"
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE t (x)")
    conn.close()
    with pytest.raises(ProjectFileError, match="no es un proyecto"):
        read_project(path)


def test_newer_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.hestia"
    write_project(path, _document().project, [])
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA user_version = 999")
    conn.close()
    with pytest.raises(ProjectFileError, match="v999"):
        read_project(path)
