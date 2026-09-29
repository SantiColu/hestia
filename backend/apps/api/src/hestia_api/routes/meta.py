from typing import Any

from fastapi import APIRouter

from hestia_api import __version__
from hestia_api.errors import ERROR_RESPONSES
from hestia_project.catalog import Catalog, StageType, catalog
from hestia_project.forms import artifact_schema

router = APIRouter()


@router.get("/health", tags=["system"], operation_id="health")
def health() -> dict[str, str]:
    """Liveness probe. No domain logic."""
    return {"status": "ok", "version": __version__}


@router.get("/catalog", tags=["catalog"], operation_id="get_catalog")
def get_catalog() -> Catalog:
    """Stage types in catalog order (class, required context types, implemented), phases and
    templates."""
    return catalog()


@router.get(
    "/catalog/stages/{stage}/artifact-schema",
    tags=["catalog"],
    operation_id="get_artifact_schema",
    responses=ERROR_RESPONSES,
)
def get_artifact_schema(stage: StageType) -> dict[str, Any]:
    """JSON Schema of the artifact of a form stage (e.g. mission), with the SI unit and display
    unit of each physical field (`x-unit`, `x-display-unit`) and the other `x-` hints used to
    build the form. 422 `stage_not_implemented` for stages without a form."""
    return artifact_schema(stage)
