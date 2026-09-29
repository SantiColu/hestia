"""Domain errors. Messages are user-facing (UI and agents) and therefore in Spanish."""

from typing import Any


class ProjectError(Exception):
    """Base error. ``code`` is stable and machine-readable; ``message`` is for people."""

    code = "project_error"

    def __init__(self, message: str, **details: Any) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(ProjectError):
    code = "not_found"


class InvalidOperationError(ProjectError):
    """The operation is not allowed on the current schematic (e.g. an invalid link)."""

    code = "invalid_operation"


class InvalidFragmentError(ProjectError):
    """Clipboard content that is not a usable fragment (unknown version, broken structure)."""

    code = "invalid_fragment"


class StageNotImplementedError(ProjectError):
    """The stage has no editor or computation yet, or is not a form stage."""

    code = "stage_not_implemented"


class JustificationRequiredError(ProjectError):
    code = "justification_required"


class NothingToUndoError(ProjectError):
    code = "nothing_to_undo"


class NothingToRedoError(ProjectError):
    code = "nothing_to_redo"


class NoProjectOpenError(ProjectError):
    code = "no_project_open"


class UnsavedChangesError(ProjectError):
    """Closing or replacing the open project would discard unsaved changes."""

    code = "unsaved_changes"


class NoPathError(ProjectError):
    """The project was never saved: use save-as."""

    code = "no_path"


class ProjectLockedError(ProjectError):
    """The file is open in another Hestia instance."""

    code = "project_locked"


class ProjectFileError(ProjectError):
    """The file does not exist, is not a Hestia project or has an unsupported version."""

    code = "invalid_project_file"
