import json
from fastapi import WebSocket

connected: list[WebSocket] = []

async def broadcast(event: dict) -> None:
    dead: list[WebSocket] = []
    for ws in connected:
        try:
            await ws.send_text(json.dumps(event))
        except Exception:
            dead.append(ws)

    for ws in dead:
        connected.remove(ws)