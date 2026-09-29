"""Upgrade projects saved with an older ``SCHEMA_VERSION`` (``docs/workflow-fases-0-1.md``).

Migrations never write to the history: a project opens as it was, upgraded, and the dropped
parts are reported as warnings (shown in Messages).
"""

from hestia_project.errors import InvalidOperationError
from hestia_project.model import Link, Project
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
