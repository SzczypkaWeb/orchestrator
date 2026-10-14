from collections.abc import Iterator
from unittest.mock import AsyncMock

import pytest

import events
from events import RunEvent

EVENT: RunEvent = {
    "run_id": "r1",
    "repo": "backend",
    "node": "writer",
    "provider": "claude",
    "status": "success",
}


@pytest.fixture(autouse=True)
def isolated_events(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(events, "save_run_event", AsyncMock())
    events.connected.clear()
    yield
    events.connected.clear()


async def test_broadcast_drops_dead_socket_and_keeps_live_one():
    live = AsyncMock()
    dead = AsyncMock()
    dead.send_text.side_effect = RuntimeError("socket closed")
    events.connected.update({live, dead})

    await events.broadcast(EVENT)

    live.send_text.assert_awaited_once()
    assert events.connected == {live}


async def test_disconnect_after_broadcast_already_dropped_it_does_not_raise():
    ws = AsyncMock()
    ws.send_text.side_effect = RuntimeError("socket closed")
    events.connected.add(ws)

    await events.broadcast(EVENT)
    events.disconnect(ws)

    assert events.connected == set()
