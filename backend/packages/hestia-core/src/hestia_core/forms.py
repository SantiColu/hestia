"""Shared pieces of form and computation stages (ADR 0017, 0021): validation problems and
helpers to declare and validate fields."""

from enum import StrEnum

from pydantic import BaseModel
from pydantic.config import JsonDict


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


class Problems:
    """Collects the problems of a validation, in form order."""

    def __init__(self) -> None:
        self.items: list[Problem] = []

    def add(self, path: str, code: ProblemCode, message: str) -> None:
        self.items.append(Problem(path=path, code=code, message=message))

    def required(self, path: str, value: object, label: str) -> bool:
        """Report a missing value. Returns whether the value is present."""
        if value is None or (isinstance(value, str) and not value.strip()):
            self.add(path, ProblemCode.REQUIRED, f"Falta {label}.")
            return False
        return True

    def positive(self, path: str, value: float | None, label: str) -> None:
        if value is not None and not value > 0:
            self.add(path, ProblemCode.MIN, f"{label} tiene que ser mayor que 0.")

    def non_negative(self, path: str, value: float | None, label: str) -> None:
        if value is not None and value < 0:
            self.add(path, ProblemCode.MIN, f"{label} no puede ser negativo.")

    def unique_name(
        self, path: str, name: str | None, seen: set[str], label: str, taken: str
    ) -> None:
        """Require the name of a list item and report it if ``seen`` already holds it (compared
        without case and extra spaces): «{taken} «name».». Adds it to ``seen``."""
        if not self.required(path, name, label):
            return
        assert name is not None
        key = " ".join(name.split()).casefold()
        if key in seen:
            self.add(path, ProblemCode.DUPLICATE_NAME, f"{taken} «{name.strip()}».")
        seen.add(key)


def unit(si: str, display: str | None = None, extra: JsonDict | None = None) -> JsonDict:
    """JSON Schema extensions of a physical field: stored SI unit and the unit shown."""
    return {"x-unit": si, "x-display-unit": display or si, **(extra or {})}


def capitalize(text: str) -> str:
    """First letter in upper case, the rest as is."""
    return text[:1].upper() + text[1:]


def format_km(value_m: float) -> str:
    """A length in m shown in whole km with thin grouping: ``5 970 km``."""
    return f"{value_m / 1000:,.0f}".replace(",", " ") + " km"


class InputRejectedError(Exception):
    """A computation refuses its inputs (e.g. outside its provider's envelope, ADR 0020).

    Never a silently wrong result: the cell becomes ``failed`` with these problems.
    """

    def __init__(self, problems: list[Problem]) -> None:
        super().__init__("; ".join(p.message for p in problems))
        self.problems = problems
