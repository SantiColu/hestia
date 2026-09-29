import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from hestia_api import __version__, errors
from hestia_api.events import EventBroker
from hestia_api.routes import clipboard, events, files, history, meta, schematic
from hestia_project.workspace import Workspace

# Origins of the UI: Vite dev server and the Tauri webview (macOS/Linux and Windows).
DEFAULT_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "tauri://localhost",
    "http://tauri.localhost",
]


def hestia_home() -> Path:
    """Per-user Hestia directory (recent projects, instance file)."""
    return Path(os.environ.get("HESTIA_HOME", Path.home() / ".hestia")).expanduser()


def create_app(home: Path | None = None) -> FastAPI:
    workspace = Workspace(home or hestia_home())
    broker = EventBroker()
    workspace.subscribe(broker.publish)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
        yield
        workspace.shutdown()

    app = FastAPI(title="Hestia API", version=__version__, lifespan=lifespan)
    app.state.workspace = workspace
    app.state.broker = broker
    origins = os.environ.get("HESTIA_CORS_ORIGINS")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins.split(",") if origins else DEFAULT_ORIGINS,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    errors.install(app)
    for module in (meta, files, schematic, clipboard, history, events):
        app.include_router(module.router)
    return app


app = create_app()
