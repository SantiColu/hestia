from fastapi import FastAPI

from hestia_api import __version__

app = FastAPI(title="Hestia API", version=__version__)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    """Liveness probe. No domain logic."""
    return {"status": "ok", "version": __version__}
