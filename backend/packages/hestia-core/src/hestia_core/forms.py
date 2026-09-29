"""Shared pieces of form and computation stages (ADR 0017, 0021): validation problems."""

from enum import StrEnum

from pydantic import BaseModel


class ProblemCode(StrEnum):
    """Stable codes of validation problems (``docs/etapas/*.md``)."""

    REQUIRED = "required"
    MIN = "min"
    MAX = "max"
    ORDER = "order"
    NOT_ALLOWED = "not_allowed"
    FORMAT = "format"
    SSO_ALTITUDE = "sso_altitude"
    PARALLEL = "parallel"
    DUPLICATE_NAME = "duplicate_name"
    DUPLICATE = "duplicate"
    MISSING = "missing"
    """A required stage type is absent from the cell's context (update of a computation)."""
    CONTEXT_INVALID = "context_invalid"
    """A stage of the context has problems or no current result (update of a computation)."""
    ECCENTRICITY_OUT_OF_RANGE = "eccentricity_out_of_range"
    """The orbit is outside the envelope of the environment provider (ADR 0020)."""


class Problem(BaseModel):
    """A validation problem of a form artifact. Validating never produces values."""

    path: str
    """Field path: ``orbit.altitude``, ``attitude_modes[2].name``; the list itself for
    list-level problems (``attitude_modes``)."""
    code: ProblemCode
    message: str
    """In Spanish, for people."""


class InputRejectedError(Exception):
    """A computation refuses its inputs (e.g. outside its provider's envelope, ADR 0020).

    Never a silently wrong result: the cell becomes ``failed`` with these problems.
    """

    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(p.message for p in problems))
        self.problems = problems
