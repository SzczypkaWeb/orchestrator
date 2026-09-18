from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import telemetry

async def test_save_run_event_inserts_expected_row(monkeypatch):
    mock_conn = AsyncMock()
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None

    async def fake_get_pool():
        return mock_pool

    monkeypatch.setattr(telemetry, "_get_pool", fake_get_pool)

    await telemetry.save_run_event(
        run_id="abc123",
        repo="backend",
        node="writer",
        provider="claude",
        status="success",
        detail=None,
        pr_url="https://github.com/x/pull/1",
    )

    mock_conn.execute.assert_awaited_once()
    sql, *params = mock_conn.execute.call_args.args
    assert 'INSERT INTO "RunEvent"' in sql
    assert "abc123" in params
    assert "https://github.com/x/pull/1" in params
    
    
async def test_fetch_run_events_maps_columns(monkeypatch):
    created_at = datetime(2026, 9, 16, 12, 0, 0, tzinfo=timezone.utc)
    fake_rows = [
        {
            "runId": "abc123",
            "repo": "backend",
            "node": "writer",
            "provider": "claude",
            "status": "success",
            "detail": None,
            "prUrl": "https://github.com/x/pull/1",
            "createdAt": created_at,
        }
    ]

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = fake_rows
    mock_pool = MagicMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    mock_pool.acquire.return_value.__aexit__.return_value = None

    async def fake_get_pool():
        return mock_pool

    monkeypatch.setattr(telemetry, "_get_pool", fake_get_pool)

    events = await telemetry.fetch_run_events()

    assert events == [
        {
            "run_id": "abc123",
            "repo": "backend",
            "node": "writer",
            "provider": "claude",
            "status": "success",
            "detail": None,
            "pr_url": "https://github.com/x/pull/1",
            "created_at": created_at.isoformat(),
        }
    ]