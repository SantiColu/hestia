"""Shared pieces of form stages (ADR 0017): validation problems."""

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


class Problem(BaseModel):
    """A validation problem of a form artifact. Validating never produces values."""

    path: str
    """Field path: ``orbit.altitude``, ``attitude_modes[2].name``; the list itself for
    list-level problems (``attitude_modes``)."""
    code: ProblemCode
    message: str
    """In Spanish, for people."""
