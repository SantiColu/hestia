"""``.hestia`` file format (ADR 0010): one SQLite database per project.

Saving builds the whole database in memory and copies it with SQLite's online backup API to a
temporary file next to the target, which then atomically replaces the target. A crash while
saving never leaves a half-written project.
"""

import contextlib
import json
import os
import sqlite3
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from hestia_core.forms import Problem
from hestia_project import __version__
from hestia_project.computations import referenced_results
from hestia_project.errors import ProjectFileError
from hestia_project.forms import new_form_state
from hestia_project.history import Change, ChangeRecord
from hestia_project.migration import recover_applied_changes, relink
from hestia_project.model import (
    SCHEMA_VERSION,
    Cell,
    Link,
    Position,
    Project,
    StageResult,
    System,
)

FILE_EXTENSION = ".hestia"
APPLICATION_ID = 0x48535441  # "HSTA": identifies Hestia files (PRAGMA application_id).

_SCHEMA = """
CREATE TABLE meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE systems (
    id         TEXT PRIMARY KEY,
    ord        INTEGER NOT NULL,
    name       TEXT NOT NULL,
    position_x REAL NOT NULL,
    position_y REAL NOT NULL
);
CREATE TABLE cells (
    id         TEXT PRIMARY KEY,
    system_id  TEXT NOT NULL REFERENCES systems(id),
    ord        INTEGER NOT NULL,
    stage      TEXT NOT NULL,
    name       TEXT NOT NULL,
    status     TEXT NOT NULL,
    provenance TEXT,
    form       TEXT,
    result_id  TEXT,
    problems   TEXT
);
CREATE TABLE links (
    id             TEXT PRIMARY KEY,
    ord            INTEGER NOT NULL,
    source_cell_id TEXT NOT NULL REFERENCES cells(id),
    target_cell_id TEXT NOT NULL REFERENCES cells(id),
    UNIQUE (source_cell_id, target_cell_id)
);
CREATE TABLE results (
    id         TEXT PRIMARY KEY,
    cell_id    TEXT NOT NULL,
    stage      TEXT NOT NULL,
    parameters TEXT NOT NULL,
    data       TEXT NOT NULL
);
CREATE TABLE changes (
    seq         INTEGER PRIMARY KEY,
    id          TEXT NOT NULL UNIQUE,
    change      TEXT NOT NULL,
    before      TEXT NOT NULL,
    after       TEXT NOT NULL
);
"""


def _problems_json(problems: list[Problem]) -> str:
    return json.dumps([p.model_dump(mode="json") for p in problems])


def _build(
    conn: sqlite3.Connection,
    project: Project,
    history: list[ChangeRecord],
    results: Mapping[str, StageResult],
) -> None:
    conn.executescript(_SCHEMA)
    conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    conn.executemany(
        "INSERT INTO meta (key, value) VALUES (?, ?)",
        [
            ("format", "hestia"),
            ("schema_version", str(SCHEMA_VERSION)),
            ("project_id", project.id),
            ("name", project.name),
            ("written_by", f"hestia_project {__version__}"),
        ],
    )
    conn.executemany(
        "INSERT INTO systems VALUES (?, ?, ?, ?, ?)",
        [(s.id, i, s.name, s.position.x, s.position.y) for i, s in enumerate(project.systems)],
    )
    # Cells keep project order; within each system it matches ``System.cell_ids``.
    conn.executemany(
        "INSERT INTO cells VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c.id,
                c.system_id,
                i,
                c.stage.value,
                c.name,
                c.status.value,
                c.provenance.model_dump_json() if c.provenance else None,
                c.form.model_dump_json() if c.form else None,
                c.result_id,
                _problems_json(c.problems) if c.problems else None,
            )
            for i, c in enumerate(project.cells)
        ],
    )
    # Links keep creation order: migrations re-evaluate them in that order.
    conn.executemany(
        "INSERT INTO links VALUES (?, ?, ?, ?)",
        [(lk.id, i, lk.source_cell_id, lk.target_cell_id) for i, lk in enumerate(project.links)],
    )
    # Results referenced by the project or its history (ADR 0021); the others are dropped.
    referenced = referenced_results(
        [project, *(r.before for r in history), *(r.after for r in history)]
    )
    conn.executemany(
        "INSERT INTO results VALUES (?, ?, ?, ?, ?)",
        [
            (r.id, r.cell_id, r.stage.value, json.dumps(r.parameters), json.dumps(r.data))
            for rid, r in results.items()
            if rid in referenced
        ],
    )
    conn.executemany(
        "INSERT INTO changes VALUES (?, ?, ?, ?, ?)",
        [
            (
                r.change.seq,
                r.change.id,
                r.change.model_dump_json(),
                r.before.model_dump_json(),
                r.after.model_dump_json(),
            )
            for r in history
        ],
    )
    conn.commit()


def write_project(
    path: Path,
    project: Project,
    history: list[ChangeRecord],
    results: Mapping[str, StageResult] | None = None,
) -> None:
    """Write the project to ``path`` atomically (backup API + rename)."""
    path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        memory = sqlite3.connect(":memory:")
        try:
            _build(memory, project, history, results or {})
            target = sqlite3.connect(tmp)
            try:
                memory.backup(target)
            finally:
                target.close()
        finally:
            memory.close()
        tmp.replace(path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


@dataclass
class ProjectFile:
    """A project read from disk."""

    project: Project
    history: list[ChangeRecord]
    warnings: list[str] = field(default_factory=list[str])
    """What an upgrade from an older schema version dropped (e.g. links that are no longer
    valid). Not part of the history."""
    results: dict[str, StageResult] = field(default_factory=dict[str, StageResult])
    """Results of computation cells by id (ADR 0021)."""


def read_project(path: Path) -> tuple[Project, list[ChangeRecord]]:
    """Read a ``.hestia`` file. Raises ``ProjectFileError`` if it is not a valid project."""
    loaded = read_project_file(path)
    return loaded.project, loaded.history


def read_project_file(path: Path) -> ProjectFile:
    """Read a ``.hestia`` file, upgrading older schema versions, with the upgrade warnings."""
    if not path.is_file():
        raise ProjectFileError(f"No existe el archivo {str(path)!r}.", path=str(path))
    try:
        conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise ProjectFileError(f"No se pudo abrir {path.name}: {exc}", path=str(path)) from exc
    try:
        return _read(conn, path)
    except sqlite3.DatabaseError as exc:
        raise ProjectFileError(
            f"{path.name} no es un proyecto de Hestia válido.", path=str(path)
        ) from exc
    except (ValidationError, ValueError, KeyError) as exc:
        raise ProjectFileError(f"{path.name} está dañado: {exc}", path=str(path)) from exc
    finally:
        with contextlib.suppress(sqlite3.Error):
            conn.close()


def _read(conn: sqlite3.Connection, path: Path) -> ProjectFile:
    (app_id,) = conn.execute("PRAGMA application_id").fetchone()
    if app_id != APPLICATION_ID:
        raise ProjectFileError(f"{path.name} no es un proyecto de Hestia.", path=str(path))
    (version,) = conn.execute("PRAGMA user_version").fetchone()
    if version > SCHEMA_VERSION:
        raise ProjectFileError(
            f"{path.name} usa el esquema v{version}; esta versión de Hestia admite hasta "
            f"v{SCHEMA_VERSION}.",
            path=str(path),
            schema_version=version,
        )
    meta = dict(conn.execute("SELECT key, value FROM meta").fetchall())
    systems: list[System] = []
    by_id: dict[str, System] = {}
    for sid, name, x, y in conn.execute(
        "SELECT id, name, position_x, position_y FROM systems ORDER BY ord"
    ):
        system = System(id=sid, name=name, position=Position(x=x, y=y))
        systems.append(system)
        by_id[sid] = system
    cells: list[Cell] = []
    # Version < 3 has no ``form``: form cells get the library defaults, as new cells do.
    form_column = "form" if version >= 3 else "NULL"
    # Version < 4 has no results: computation cells never ran and their provenance was always
    # empty; their parameters get the library defaults.
    result_columns = "result_id, problems" if version >= 4 else "NULL, NULL"
    for cid, system_id, stage, name, status, provenance, form, result_id, problems in conn.execute(
        f"SELECT id, system_id, stage, name, status, provenance, {form_column}, "
        f"{result_columns} FROM cells ORDER BY ord"
    ):
        cell = Cell.model_validate(
            {
                "id": cid,
                "system_id": system_id,
                "stage": stage,
                "name": name,
                "status": status,
                "provenance": json.loads(provenance) if provenance and version >= 4 else None,
                "form": json.loads(form) if form else None,
                "result_id": result_id,
                "problems": json.loads(problems) if problems else [],
            }
        )
        if cell.form is None:
            cell.form = new_form_state(cell.stage, change_id=None)
        cells.append(cell)
        by_id[system_id].cell_ids.append(cid)
    # Version 1 has no ``ord``: rows were inserted in creation order.
    order = "rowid" if version < 2 else "ord"
    links = [
        Link(id=lid, source_cell_id=src, target_cell_id=dst)
        for lid, src, dst in conn.execute(
            f"SELECT id, source_cell_id, target_cell_id FROM links ORDER BY {order}"
        )
    ]
    project = Project(
        schema_version=SCHEMA_VERSION,
        id=meta["project_id"],
        name=meta["name"],
        systems=systems,
        cells=cells,
        links=[] if version < 2 else links,
    )
    warnings: list[str] = []
    if version < 2:
        # Context through the chain (ADR 0016): re-evaluate the links with the new rules.
        warnings = relink(project, links)
    history = [
        ChangeRecord(
            change=Change.model_validate_json(change),
            before=Project.model_validate_json(before),
            after=Project.model_validate_json(after),
        )
        for change, before, after in conn.execute(
            "SELECT change, before, after FROM changes ORDER BY seq"
        )
    ]
    results: dict[str, StageResult] = {}
    if version >= 4:
        for rid, cell_id, stage, parameters, data in conn.execute(
            "SELECT id, cell_id, stage, parameters, data FROM results"
        ):
            results[rid] = StageResult.model_validate(
                {
                    "id": rid,
                    "cell_id": cell_id,
                    "stage": stage,
                    "parameters": json.loads(parameters),
                    "data": json.loads(data),
                }
            )
    else:
        # Applies older than version 4 record no change id: recover it from the history.
        recover_applied_changes(project, history)
    return ProjectFile(project=project, history=history, warnings=warnings, results=results)
