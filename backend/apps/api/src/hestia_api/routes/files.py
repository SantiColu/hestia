"""Project file lifecycle: new, open, save, save as, close and recent projects."""

from pathlib import Path

from fastapi import APIRouter

from hestia_api.deps import WorkspaceDep
from hestia_api.errors import ERROR_RESPONSES
from hestia_api.schemas import (
    CloseProjectRequest,
    NewProjectRequest,
    OpenProjectRequest,
    RemoveRecentRequest,
    SaveAsRequest,
    Session,
)
from hestia_project.document import ProjectView
from hestia_project.recents import RecentProject

router = APIRouter(tags=["files"], responses=ERROR_RESPONSES)


@router.get("/session", operation_id="get_session")
def get_session(workspace: WorkspaceDep) -> Session:
    """The open project (schematic and file state), or null if none is open."""
    return Session(project=workspace.view() if workspace.is_open else None)


@router.get("/recents", operation_id="list_recent_projects")
def list_recent_projects(workspace: WorkspaceDep) -> list[RecentProject]:
    """Recently opened projects, newest first. ``exists`` is false for moved or deleted files."""
    return workspace.recent_projects()


@router.delete("/recents", operation_id="remove_recent_project")
def remove_recent_project(
    body: RemoveRecentRequest, workspace: WorkspaceDep
) -> list[RecentProject]:
    """Forget a recent project (the file is not touched)."""
    workspace.recents.remove(body.path)
    return workspace.recent_projects()


@router.post("/project/new", operation_id="new_project")
def new_project(body: NewProjectRequest, workspace: WorkspaceDep) -> ProjectView:
    """Start an empty, unsaved project. Fails with ``unsaved_changes`` unless discarding."""
    return workspace.new_project(body.name, discard_unsaved=body.discard_unsaved)


@router.post("/project/open", operation_id="open_project")
def open_project(body: OpenProjectRequest, workspace: WorkspaceDep) -> ProjectView:
    """Open a .hestia file. Fails with ``project_locked`` (423) if another instance has it."""
    return workspace.open_project(
        Path(body.path), force=body.force, discard_unsaved=body.discard_unsaved
    )


@router.post("/project/save", operation_id="save_project")
def save_project(workspace: WorkspaceDep) -> ProjectView:
    """Save to the current file. Fails with ``no_path`` if it was never saved."""
    return workspace.save()


@router.post("/project/save-as", operation_id="save_project_as")
def save_project_as(body: SaveAsRequest, workspace: WorkspaceDep) -> ProjectView:
    """Save to a new file and keep working on it."""
    return workspace.save_as(Path(body.path))


@router.post("/project/close", operation_id="close_project")
def close_project(body: CloseProjectRequest, workspace: WorkspaceDep) -> Session:
    """Close the project. Fails with ``unsaved_changes`` unless discarding."""
    workspace.close(discard_unsaved=body.discard_unsaved)
    return Session(project=None)
