"""Fan-out of project events to Server-Sent Events subscribers (ADR 0012).

The workspace publishes from worker threads; each subscriber is an asyncio queue bound to the
event loop that serves its connection.
"""

import asyncio
import contextlib
import threading
from collections.abc import AsyncGenerator

from hestia_project.workspace import ProjectEvent

_QUEUE_SIZE = 256


class EventBroker:
    def __init__(self) -> None:
        self._subscribers: set[tuple[asyncio.AbstractEventLoop, asyncio.Queue[ProjectEvent]]] = (
            set()
        )
        self._lock = threading.Lock()

    def publish(self, event: ProjectEvent) -> None:
        with self._lock:
            subscribers = list(self._subscribers)
        for loop, queue in subscribers:
            with contextlib.suppress(RuntimeError):  # loop already closed
                loop.call_soon_threadsafe(_offer, queue, event)

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncGenerator[asyncio.Queue[ProjectEvent], None]:
        entry = (asyncio.get_running_loop(), asyncio.Queue[ProjectEvent](maxsize=_QUEUE_SIZE))
        with self._lock:
            self._subscribers.add(entry)
        try:
            yield entry[1]
        finally:
            with self._lock:
                self._subscribers.discard(entry)

    @property
    def subscriber_count(self) -> int:
        with self._lock:
            return len(self._subscribers)


def _offer(queue: asyncio.Queue[ProjectEvent], event: ProjectEvent) -> None:
    # A slow client drops events rather than blocking everyone; it refetches on the next one.
    with contextlib.suppress(asyncio.QueueFull):
        queue.put_nowait(event)
