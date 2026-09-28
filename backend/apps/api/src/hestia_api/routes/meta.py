from fastapi import APIRouter

from hestia_api import __version__
from hestia_project.catalog import Catalog, catalog

router = APIRouter()


@router.get("/health", tags=["system"], operation_id="health")
def health() -> dict[str, str]:
    """Liveness probe. No domain logic."""
    return {"status": "ok", "version": __version__}


@router.get("/catalog", tags=["catalog"], operation_id="get_catalog")
def get_catalog() -> Catalog:
    """Stage types, phases and templates, with the inputs each stage type accepts."""
    return catalog()
