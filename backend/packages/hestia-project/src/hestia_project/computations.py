"""Computation stages (ADR 0021): parameters, Update and result.

A computation stage edits its parameters as a form (registered in ``forms.FORMS``, operations
in ``artifacts``) and produces its result when it is updated. Updating is an explicit change of
the history with an author: it takes the resolved context and the applied parameters, calls
``hestia_core`` through the stage's ``ComputationSpec`` and stores the result outside the
history snapshots (``Cell.result_id``).

Status rules:

- ``never_run``: never updated.
- ``up_to_date``: the result matches the current context and parameters.
- ``outdated``: something upstream changed or new parameters were applied. Nothing reruns on
  its own; the previous result is kept and shown as outdated.
- ``failed``: the last update produced no result. ``Cell.problems`` says why: missing context
  types (``missing``), a context stage with problems or without a current result
  (``context_invalid``), invalid parameters or inputs the provider rejects (ADR 0020). The
  previous result, if any, is kept.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from hestia_core.forms import InputRejectedError, Problem, ProblemCode
from hestia_project.artifacts import NoChange, artifact_problems
from hestia_project.base import Schema
from hestia_project.catalog import ORDER, STAGES, StageType
from hestia_project.errors import StageNotImplementedError
from hestia_project.forms import FORMS, PENDING_CHANGE, is_form_stage, new_form_state
from hestia_project.model import (
    Cell,
    CellStatus,
    ContextSource,
    Project,
    Provenance,
    StageResult,
)
from hestia_project.schematic import (
    Outcome,
    context_cells,
    downstream,
    get_cell,
    invalidate,
    missing_requirements,
    new_id,
)

ComputationContext = Mapping[StageType, BaseModel]
"""Inputs of a computation by stage type: the artifact of each form stage and the result of
each computation stage in the cell's context."""


@dataclass(frozen=True)
class ComputationSpec:
    """How a computation stage runs. Its parameters are registered in ``forms.FORMS``."""

    result_model: type[BaseModel]
    run: Callable[[BaseModel, ComputationContext], BaseModel]
    """Parameters and context → result. Pure (``hestia_core``); raises ``InputRejectedError``
    for inputs outside the provider's envelope."""
    provider: str
    provider_version: str
    code_version: str


COMPUTATIONS: dict[StageType, ComputationSpec] = {}
"""Implemented computation stages (registered by ``hestia_project.stages``)."""


def computation_spec(stage: StageType) -> ComputationSpec:
    spec = COMPUTATIONS.get(stage)
    if spec is None:
        raise StageNotImplementedError(
            f"La etapa «{STAGES[stage].default_name}» no tiene cálculo implementado.",
            stage=stage,
        )
    return spec


def _stage_name(stage: StageType) -> str:
    return STAGES[stage].default_name


def _change_of(cell: Cell) -> str | None:
    """Change that set what ``cell`` provides: its applied artifact or its result."""
    if is_form_stage(cell.stage):
        return cell.form.applied_change_id if cell.form else None
    return cell.provenance.change_id if cell.provenance else None


def _inputs(
    project: Project, results: Mapping[str, StageResult], cell: Cell
) -> tuple[dict[StageType, BaseModel], list[ContextSource], list[Problem]]:
    """Resolve the context of ``cell`` into inputs, their provenance and the problems."""
    problems = [
        Problem(
            path="context",
            code=ProblemCode.MISSING,
            message=f"Falta «{_stage_name(stage)}» en su contexto: vinculá una celda que la "
            "provea.",
        )
        for stage in missing_requirements(project, cell.id)
    ]
    inputs: dict[StageType, BaseModel] = {}
    sources: list[ContextSource] = []
    by_type = context_cells(project, cell.id)
    for stage in sorted(by_type, key=ORDER.__getitem__):
        if stage not in STAGES[cell.stage].requires:
            continue
        provider = get_cell(project, by_type[stage][0])
        label = f"«{_stage_name(stage)}» (celda «{provider.name}»)"
        sources.append(ContextSource(stage=stage, cell_id=provider.id, change_id=None))
        if is_form_stage(stage):
            spec = FORMS.get(stage)
            if spec is None or provider.form is None:
                problems.append(_context_invalid(f"{label} no tiene formulario."))
            elif provider.status is CellStatus.NEVER_RUN:
                problems.append(_context_invalid(f"{label} no está aplicada."))
            elif provider.status is not CellStatus.UP_TO_DATE:
                problems.append(_context_invalid(f"{label} tiene problemas: corregilos."))
            else:
                inputs[stage] = spec.model.model_validate(provider.form.artifact)
        else:
            upstream = COMPUTATIONS.get(stage)
            result = results.get(provider.result_id) if provider.result_id else None
            if upstream is None or result is None or provider.status is not CellStatus.UP_TO_DATE:
                problems.append(_context_invalid(f"{label} no está actualizada."))
            else:
                inputs[stage] = upstream.result_model.model_validate(result.data)
        sources[-1].change_id = _change_of(provider)
    return inputs, sources, problems


def _context_invalid(message: str) -> Problem:
    return Problem(path="context", code=ProblemCode.CONTEXT_INVALID, message=message)


def update_cell(project: Project, results: Mapping[str, StageResult], cell_id: str) -> Outcome:
    """Update (run) a computation cell with its applied parameters and resolved context.

    On success the cell is ``up_to_date`` with a new result and everything downstream becomes
    outdated. Otherwise it is ``failed`` with the problems and keeps its previous result.
    Raises ``NoChange`` when the cell is already up to date with this provider version, or
    fails again with the same problems.
    """
    cell = get_cell(project, cell_id)
    spec = computation_spec(cell.stage)
    # Any change of the inputs outdates the cell, so an up-to-date cell would give the same.
    if (
        cell.status is CellStatus.UP_TO_DATE
        and cell.provenance is not None
        and cell.provenance.provider_version == spec.provider_version
    ):
        raise NoChange
    if cell.form is None:
        cell.form = new_form_state(cell.stage, change_id=None)
    assert cell.form is not None
    form = FORMS[cell.stage]
    parameters = form.model.model_validate(cell.form.artifact)
    inputs, sources, problems = _inputs(project, results, cell)
    problems += artifact_problems(project, cell)

    result_model: BaseModel | None = None
    if not problems:
        try:
            result_model = spec.run(parameters, inputs)
        except InputRejectedError as exc:
            problems = exc.problems

    if result_model is None:
        if cell.status is CellStatus.FAILED and cell.problems == problems:
            raise NoChange
        cell.status = CellStatus.FAILED
        cell.problems = problems
        count = "1 problema" if len(problems) == 1 else f"{len(problems)} problemas"
        return Outcome(summary=f"Actualizó «{cell.name}»: falló ({count}).")

    result = StageResult(
        id=new_id("result"),
        cell_id=cell.id,
        stage=cell.stage,
        parameters=cell.form.artifact,
        data=result_model.model_dump(mode="json"),
    )
    cell.result_id = result.id
    cell.status = CellStatus.UP_TO_DATE
    cell.problems = []
    cell.provenance = Provenance(
        produced_at=datetime.now(UTC),
        change_id=PENDING_CHANGE,
        provider=spec.provider,
        provider_version=spec.provider_version,
        code_version=spec.code_version,
        context=sources,
        parameters_change_id=cell.form.applied_change_id,
    )
    return Outcome(
        summary=f"Actualizó «{cell.name}».",
        outdated_cell_ids=invalidate(project, downstream(project, [cell.id])),
        results=[result],
    )


# ---------------------------------------------------------------- reading


class CellResult(Schema):
    """State of a computation cell and its last result (possibly outdated)."""

    cell_id: str
    stage: StageType
    status: CellStatus
    problems: list[Problem]
    """Why the last update failed (status ``failed``)."""
    provenance: Provenance | None
    """What produced the result: context cells and their changes, parameters, provider."""
    result_id: str | None
    parameters: dict[str, Any] | None
    """Parameters the result was computed with (SI)."""


def read_result(
    project: Project, results: Mapping[str, StageResult], cell_id: str
) -> tuple[CellResult, StageResult | None]:
    """The cell's state and its stored result (None if it never produced one)."""
    cell = get_cell(project, cell_id)
    computation_spec(cell.stage)
    stored = results.get(cell.result_id) if cell.result_id else None
    return (
        CellResult(
            cell_id=cell.id,
            stage=cell.stage,
            status=cell.status,
            problems=cell.problems,
            provenance=cell.provenance,
            result_id=cell.result_id,
            parameters=stored.parameters if stored else None,
        ),
        stored,
    )


def referenced_results(projects: list[Project]) -> set[str]:
    """Result ids referenced by ``projects`` (the current one and the history snapshots)."""
    return {c.result_id for p in projects for c in p.cells if c.result_id}
