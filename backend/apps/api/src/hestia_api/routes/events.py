from collections.abc import AsyncIterator

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from hestia_api.deps import BrokerDep, WorkspaceDep
from hestia_project.workspace import EventType, ProjectEvent

router = APIRouter(tags=["events"])


@router.get("/events", operation_id="stream_events", response_class=EventSourceResponse)
async def stream_events(broker: BrokerDep, workspace: WorkspaceDep) -> AsyncIterator[ProjectEvent]:
    """Server-Sent Events: one ``ProjectEvent`` per change of the workspace, whoever caused it.

    The SSE event name is the event ``type``. The first event is ``connected`` with the current
    revision. Clients refetch the session when they receive an event.
    """
    async with broker.subscribe() as queue:
        revision = workspace.view().document.revision if workspace.is_open else None
        yield _sse(ProjectEvent(type=EventType.CONNECTED, message="Conectado.", revision=revision))
        while True:
            yield _sse(await queue.get())


def _sse(event: ProjectEvent) -> ProjectEvent:
    # FastAPI sends ServerSentEvent items as-is (named event); the annotation above documents
    # the payload in the contract.
    return ServerSentEvent(event=event.type.value, data=event.model_dump(mode="json"))  # type: ignore[return-value]
