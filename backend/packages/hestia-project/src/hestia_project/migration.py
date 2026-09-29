"""Upgrade projects saved with an older ``SCHEMA_VERSION`` (``docs/workflow-fases-0-1.md``).

Migrations never write to the history: a project opens as it was, upgraded, and the dropped
parts are reported as warnings (shown in Messages).
"""

from hestia_project.errors import InvalidOperationError
from hestia_project.history import ChangeRecord
from hestia_project.model import Cell, CellStatus, Link, Project
from hestia_project.schematic import check_link, get_cell


def relink(project: Project, links: list[Link]) -> list[str]:
    """Re-evaluate ``links`` in creation order with the current link rules (ADR 0016).

    Valid links are added to ``project``; the others are dropped. Returns one warning per
    dropped link. ``project`` must have no links yet.
    """
    warnings: list[str] = []
    for lk in links:
        try:
            check_link(project, lk.source_cell_id, lk.target_cell_id)
        except InvalidOperationError as exc:
            source = get_cell(project, lk.source_cell_id)
            target = get_cell(project, lk.target_cell_id)
            warnings.append(
                f"Se descartó el vínculo «{source.name}» → «{target.name}» al actualizar el "
                f"proyecto a las reglas nuevas: {exc.message}"
            )
            continue
        project.links.append(lk)
    return warnings


def recover_applied_changes(project: Project, history: list[ChangeRecord]) -> None:
    """Set ``FormState.applied_change_id`` of applied form cells from the history (v3 → v4).

    The change is the last one after which the cell holds its current artifact while it did
    not before (apply, paste, undo…). Left null when the history does not show it.
    """
    for cell in project.cells:
        if cell.form is None or cell.status is CellStatus.NEVER_RUN:
            continue
        for record in reversed(history):
            after = _cell(record.after, cell.id)
            if after is None or after.form is None or after.form.artifact != cell.form.artifact:
                continue
            before = _cell(record.before, cell.id)
            if (
                before is None
                or before.form is None
                or before.form.artifact != cell.form.artifact
                or before.status is CellStatus.NEVER_RUN
            ):
                cell.form.applied_change_id = record.change.id
                break


def _cell(project: Project, cell_id: str) -> Cell | None:
    return next((c for c in project.cells if c.id == cell_id), None)
