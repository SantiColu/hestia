from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from hestia_api.deps import BrokerDep, WorkspaceDep
from hestia_project.workspace import ProjectEvent

router = APIRouter(tags=["events"])


@router.get("/events", operation_id="stream_events", response_class=EventSourceResponse)
async def stream_events(
    broker: BrokerDep, workspace: WorkspaceDep
) -> AsyncIterator[ServerSentEvent]:
    """Server-Sent Events with every project event (``ProjectEvent``), whoever caused it.

    The first event is ``connected``, carrying the current revision. Clients refetch the
    session when they receive an event.
    """
    async with broker.subscribe() as queue:
        revision = workspace.view().document.revision if workspace.is_open else None
        yield ServerSentEvent(event="connected", data={"revision": revision})
        while True:
            event: ProjectEvent = await queue.get()
            yield ServerSentEvent(event=event.type.value, data=event.model_dump(mode="json"))
