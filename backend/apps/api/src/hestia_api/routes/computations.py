"""Computation stages (ADR 0021): update a cell and read its result. Each endpoint only
delegates to ``hestia_project.computations``."""

from fastapi import APIRouter

from hestia_api.deps import AuthorDep, WorkspaceDep
from hestia_api.errors import ERROR_RESPONSES
from hestia_api.schemas import UpdateCellRequest, UpdateCellResult
from hestia_core.environment.result import OrbitProfile
from hestia_project import computations
from hestia_project.computations import CellResult

router = APIRouter(prefix="/project/cells", tags=["computations"], responses=ERROR_RESPONSES)


@router.post("/{cell_id}/update", operation_id="update_cell")
def update_cell(
    cell_id: str, body: UpdateCellRequest, workspace: WorkspaceDep, author: AuthorDep
) -> UpdateCellResult:
    """Update (run) a computation cell (environment) with its applied parameters and its
    context, in one change of the history (one undo). The justification may be empty.

    Success: `up_to_date` with a new result and everything downstream outdated. Otherwise
    `failed` with the problems (`missing`, `context_invalid`, invalid parameters,
    `eccentricity_out_of_range`…) and the previous result kept. `change` is null when the cell
    was already up to date or fails again the same way. 422 `stage_not_implemented` for stages
    without a computation.
    """
    change, view = workspace.update_cell(cell_id, author, body.justification)
    result = workspace.query_results(lambda p, r: computations.read_result(p, r, cell_id))
    return UpdateCellResult(change=change, view=view, result=result)


@router.get("/{cell_id}/result", operation_id="get_cell_result")
def get_cell_result(cell_id: str, workspace: WorkspaceDep) -> CellResult:
    """Status, problems, provenance and last result of a computation cell (possibly outdated:
    check `status`). SI units, angles in rad. The orbit profiles are listed by condition and
    attitude mode; read each one with `get_orbit_profile`."""
    return workspace.query_results(lambda p, r: computations.read_result(p, r, cell_id))


@router.get("/{cell_id}/result/orbit-profile", operation_id="get_orbit_profile")
def get_orbit_profile(
    cell_id: str, condition_id: str, mode_id: str, workspace: WorkspaceDep
) -> OrbitProfile:
    """One orbit of a condition in an attitude mode from an environment result: time, inertial
    position and velocity, Sun vector, sunlit fraction, body quaternion (body → inertial,
    `[w, x, y, z]`), Earth rotation angle and incident fluxes per face. 404 if the result has no
    such profile."""
    return workspace.query_results(
        lambda p, r: computations.read_orbit_profile(p, r, cell_id, condition_id, mode_id)
    )
