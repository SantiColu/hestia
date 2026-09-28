"""Request-scoped dependencies: the workspace and the author of a write."""

import getpass
from typing import Annotated

from fastapi import Depends, Header, Request

from hestia_api.events import EventBroker
from hestia_project.history import ActorKind, Author
from hestia_project.workspace import Workspace


def get_workspace(request: Request) -> Workspace:
    workspace: Workspace = request.app.state.workspace
    return workspace


def get_broker(request: Request) -> EventBroker:
    broker: EventBroker = request.app.state.broker
    return broker


def get_author(
    x_hestia_actor: Annotated[
        str | None,
        Header(description="Author name. Defaults to the OS user running the API."),
    ] = None,
    x_hestia_actor_kind: Annotated[
        ActorKind,
        Header(description="`human` (UI) or `agent` (MCP and other agents)."),
    ] = ActorKind.HUMAN,
) -> Author:
    """Author of a write, from the request headers (ADR 0011)."""
    name = (x_hestia_actor or "").strip() or getpass.getuser()
    return Author(kind=x_hestia_actor_kind, name=name)


WorkspaceDep = Annotated[Workspace, Depends(get_workspace)]
AuthorDep = Annotated[Author, Depends(get_author)]
BrokerDep = Annotated[EventBroker, Depends(get_broker)]
