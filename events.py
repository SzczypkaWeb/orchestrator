import json
from datetime import datetime, timezone
from fastapi import WebSocket
from telemetry import save_run_event

connected: list[WebSocket] = []

async def broadcast(event: dict) -> None:
    # Persist the event exactly as given - save_run_event()'s signature
    # doesn't know about "created_at" (that timestamp comes from the DB's
    # own createdAt column, read back later via fetch_run_events()).
    await save_run_event(**event)

    # Live WS consumers never see the DB row, so they need their own
    # timestamp to know how recent an event is - used by the frontend to
    # detect a run that's gone quiet for too long (likely an interrupted
    # backend process, not still-in-progress work).
    live_event = {**event, "created_at": datetime.now(timezone.utc).isoformat()}

    dead: list[WebSocket] = []
    for ws in connected:
        try:
            await ws.send_text(json.dumps(live_event))
        except Exception:
            dead.append(ws)

    for ws in dead:
        connected.remove(ws)