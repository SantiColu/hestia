"""Map domain errors to HTTP responses with a stable, machine-readable body."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import Field

from hestia_project.base import Schema
from hestia_project.errors import (
    InvalidFragmentError,
    InvalidOperationError,
    JustificationRequiredError,
    NoPathError,
    NoProjectOpenError,
    NotFoundError,
    NothingToRedoError,
    NothingToUndoError,
    ProjectError,
    ProjectFileError,
    ProjectLockedError,
    StageNotImplementedError,
    UnsavedChangesError,
)


class ApiError(Schema):
    """Error body. ``code`` is stable (e.g. ``project_locked``); ``message`` is for people."""

    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict[str, Any])


STATUS: dict[type[ProjectError], int] = {
    NotFoundError: 404,
    InvalidOperationError: 422,
    InvalidFragmentError: 422,
    JustificationRequiredError: 422,
    ProjectFileError: 422,
    StageNotImplementedError: 422,
    NothingToUndoError: 409,
    NothingToRedoError: 409,
    NoProjectOpenError: 409,
    UnsavedChangesError: 409,
    NoPathError: 409,
    ProjectLockedError: 423,
}

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    status: {"model": ApiError} for status in sorted(set(STATUS.values()))
}


def _status_for(exc: ProjectError) -> int:
    for cls in type(exc).__mro__:
        if cls in STATUS:
            return STATUS[cls]  # type: ignore[index]
    return 400


async def _handle(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ProjectError)
    body = ApiError(code=exc.code, message=exc.message, details=exc.details)
    return JSONResponse(status_code=_status_for(exc), content=body.model_dump(mode="json"))


def install(app: FastAPI) -> None:
    app.add_exception_handler(ProjectError, _handle)
