"""Opening files saved with schema version 1 (links per input, ADR 0009 → ADR 0016)."""

import sqlite3
from pathlib import Path

from hestia_project.model import SCHEMA_VERSION
from hestia_project.schematic import cell_context
from hestia_project.storage import APPLICATION_ID, read_project_file, write_project
from hestia_project.workspace import EventType, ProjectEvent, Workspace

# A v1 project: the old phase 0 template (no equipment) and phase 1 fed per input from phase 0,
# links in creation order.
V1_CELLS = [
    ("m", "f0", "mission"),
    ("e", "f0", "environment"),
    ("g", "f0", "global_balance"),
    ("t", "f0", "tcs_concept"),
    ("d", "f1", "discretization"),
    ("c", "f1", "couplings"),
    ("l", "f1", "load_cases"),
    ("s", "f1", "solution"),
    ("n", "f1", "margins"),
    ("v", "f1", "sensitivity"),
]
V1_LINKS = [
    ("m", "e", "mission"),
    ("e", "g", "environment"),
    ("g", "t", "global_balance"),
    ("d", "c", "discretization"),
    ("c", "l", "couplings"),
    ("l", "s", "load_cases"),
    ("s", "n", "solution"),
    ("n", "v", "margins"),
    ("m", "d", "mission"),
    ("e", "l", "environment"),
    ("g", "s", "global_balance"),
    ("m", "n", "mission"),
]


def write_v1(path: Path) -> None:
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE systems (id TEXT PRIMARY KEY, ord INTEGER NOT NULL, name TEXT NOT NULL,
            position_x REAL NOT NULL, position_y REAL NOT NULL);
        CREATE TABLE cells (id TEXT PRIMARY KEY, system_id TEXT NOT NULL, ord INTEGER NOT NULL,
            stage TEXT NOT NULL, name TEXT NOT NULL, status TEXT NOT NULL, provenance TEXT);
        CREATE TABLE links (id TEXT PRIMARY KEY, source_cell_id TEXT NOT NULL,
            target_cell_id TEXT NOT NULL, input TEXT NOT NULL, UNIQUE (target_cell_id, input));
        CREATE TABLE changes (seq INTEGER PRIMARY KEY, id TEXT NOT NULL UNIQUE,
            change TEXT NOT NULL, before TEXT NOT NULL, after TEXT NOT NULL);
        """
    )
    conn.execute(f"PRAGMA application_id = {APPLICATION_ID}")
    conn.execute("PRAGMA user_version = 1")
    conn.executemany(
        "INSERT INTO meta VALUES (?, ?)",
        [("format", "hestia"), ("schema_version", "1"), ("project_id", "p"), ("name", "SAT")],
    )
    conn.executemany(
        "INSERT INTO systems VALUES (?, ?, ?, ?, ?)",
        [("f0", 0, "Fase 0", 0, 0), ("f1", 1, "Fase 1", 320, 0)],
    )
    conn.executemany(
        "INSERT INTO cells VALUES (?, ?, ?, ?, ?, ?, NULL)",
        [(cid, sid, i, stage, stage, "never_run") for i, (cid, sid, stage) in enumerate(V1_CELLS)],
    )
    conn.executemany(
        "INSERT INTO links VALUES (?, ?, ?, ?)",
        [(f"{a}{b}", a, b, inp) for a, b, inp in V1_LINKS],
    )
    conn.commit()
    conn.close()


def test_v1_links_are_reevaluated_in_creation_order(tmp_path: Path) -> None:
    path = tmp_path / "old.hestia"
    write_v1(path)
    loaded = read_project_file(path)
    project = loaded.project
    assert project.schema_version == SCHEMA_VERSION
    # Phase 0 chain, phase 1 chain and mission → discretization survive. The other cross-phase
    # links would bring mission a second time into the phase 1 chain.
    assert [lk.id for lk in project.links] == ["me", "eg", "gt", "dc", "cl", "ls", "sn", "nv", "md"]
    assert len(loaded.warnings) == 3
    assert all(w.startswith("Se descartó el vínculo") for w in loaded.warnings)
    assert "«environment» → «load_cases»" in loaded.warnings[0]
    # No equipment cell is added to the old phase 0 system.
    assert [c.stage.value for c in project.cells] == [stage for _, _, stage in V1_CELLS]
    assert cell_context(project, "g").missing == ["equipment"]
    # History is untouched.
    assert loaded.history == []


def test_migrated_project_saves_as_current_version(tmp_path: Path) -> None:
    path = tmp_path / "old.hestia"
    write_v1(path)
    project = read_project_file(path).project
    write_project(path, project, [])
    again = read_project_file(path)
    assert again.project == project
    assert again.warnings == []
    conn = sqlite3.connect(path)
    assert conn.execute("PRAGMA user_version").fetchone() == (SCHEMA_VERSION,)
    conn.close()


def test_open_reports_warnings_without_history(tmp_path: Path) -> None:
    path = tmp_path / "old.hestia"
    write_v1(path)
    ws = Workspace(tmp_path / "home")
    events: list[ProjectEvent] = []
    ws.subscribe(events.append)
    view = ws.open_project(path)
    (opened,) = events
    assert opened.type is EventType.PROJECT_OPENED
    assert len(opened.warnings) == 3
    assert ws.history() == []
    assert view.document.dirty is False
    ws.shutdown()
