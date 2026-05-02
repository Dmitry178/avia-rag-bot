"""In-memory SSE pub/sub for chat-sideband events (errors, future trace)."""

import asyncio

from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from app.core.logs import logger


class SSEManager:
    """
    Fan-out hub keyed by client_id (frontend-generated correlation id).

    Used for error notifications during synchronous POST /messages; streaming LLM comes later.
    """

    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def subscribe(self, client_id: str) -> asyncio.Queue[dict[str, Any]]:
        """
        Register a new SSE consumer queue.
        """

        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        
        async with self._lock:
            self._queues[client_id].append(queue)
        
        logger.debug("sse_subscribed", client_id=client_id)
        
        return queue

    async def unsubscribe(self, client_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """
        Remove consumer queue on disconnect.
        """

        async with self._lock:
            if client_id not in self._queues:
                return
            self._queues[client_id] = [item for item in self._queues[client_id] if item is not queue]
            if not self._queues[client_id]:
                del self._queues[client_id]
        
        logger.debug("sse_unsubscribed", client_id=client_id)

    @asynccontextmanager
    async def subscription(self, client_id: str) -> AsyncIterator[asyncio.Queue[dict[str, Any]]]:
        """
        Subscribe for the duration of the context; unsubscribe on exit.
        """

        queue = await self.subscribe(client_id)
        
        try:
            yield queue
        finally:
            await self.unsubscribe(client_id, queue)

    async def publish(self, client_id: str, event: str, data: dict[str, Any]) -> None:
        """
        Push event to all queues for client_id.
        """

        async with self._lock:
            queues = list(self._queues.get(client_id, []))

        for queue in queues:
            await queue.put({"event": event, "data": data})

        if queues:
            logger.debug("sse_published", client_id=client_id, event=event)


sse_manager = SSEManager()
