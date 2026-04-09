"""
SSE stream endpoint.
Clients connect here to receive real-time agent progress events.
Events are pushed via asyncio.Queue stored in a session registry.
"""
import asyncio
import json
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

router = APIRouter()

# In-memory session event queues: session_id -> asyncio.Queue
_queues: dict[str, asyncio.Queue] = {}


def get_or_create_queue(session_id: str) -> asyncio.Queue:
    if session_id not in _queues:
        _queues[session_id] = asyncio.Queue()
    return _queues[session_id]


async def emit_event(session_id: str, event: str, data: dict):
    """Push an event to the session queue. Called from the pipeline."""
    q = get_or_create_queue(session_id)
    await q.put({"event": event, "data": data})


async def close_session(session_id: str):
    """Signal the SSE stream to close after pipeline completes."""
    q = get_or_create_queue(session_id)
    await q.put(None)  # sentinel


@router.get("/stream/{session_id}")
async def stream_events(session_id: str):
    q = get_or_create_queue(session_id)

    async def generator() -> AsyncGenerator[dict, None]:
        try:
            while True:
                try:
                    item = await asyncio.wait_for(q.get(), timeout=60.0)
                except asyncio.TimeoutError:
                    # Send keep-alive comment
                    yield {"event": "ping", "data": ""}
                    continue

                if item is None:
                    # Pipeline finished — send done event and close
                    yield {"event": "done", "data": json.dumps({"status": "completed"})}
                    break

                yield {
                    "event": item["event"],
                    "data": json.dumps(item["data"]),
                }
        finally:
            _queues.pop(session_id, None)

    return EventSourceResponse(generator())
