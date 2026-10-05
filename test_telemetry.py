import re
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

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

# --- optional persistence: behavior without / with a broken DATABASE_URL -----


@pytest.fixture
def no_database(monkeypatch):
    """DATABASE_URL unset, fresh module state, and any attempt to open a real
    connection fails the test loudly instead of hanging or hitting a database."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(telemetry, "_pool", None)
    monkeypatch.setattr(telemetry, "_warned_no_database", False)

    async def forbidden(*args, **kwargs):
        raise AssertionError("tried to connect to a database although DATABASE_URL is unset")

    monkeypatch.setattr(telemetry.asyncpg, "create_pool", forbidden)


async def test_reads_return_empty_without_database(no_database):
    assert await telemetry.fetch_run_events() == []
    assert await telemetry.fetch_run_metrics("abc123") == []


async def test_writes_are_skipped_without_database(no_database):
    await telemetry.save_run_event(run_id="abc123", repo="backend", node="writer", provider="claude", status="success")
    await telemetry.record_metric(
        run_id="abc123", repo="backend", node="writer", provider="claude", model="m", duration_ms=1, success=True
    )


async def test_missing_database_is_reported_once_not_per_event(no_database, capsys):
    for _ in range(3):
        await telemetry.save_run_event(run_id="r", repo="backend", node="writer", provider="claude", status="success")
    out = capsys.readouterr().out
    assert out.count("DATABASE_URL is not set") == 1


async def test_unreachable_database_still_raises_on_read(monkeypatch):
    """A configured-but-broken database must NOT look like an empty history."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@127.0.0.1:1/db")
    monkeypatch.setattr(telemetry, "_pool", None)

    async def refuse(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(telemetry.asyncpg, "create_pool", refuse)

    with pytest.raises(OSError):
        await telemetry.fetch_run_events()


async def test_unreachable_database_never_breaks_a_write(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pw@127.0.0.1:1/db")
    monkeypatch.setattr(telemetry, "_pool", None)

    async def refuse(*args, **kwargs):
        raise OSError("connection refused")

    monkeypatch.setattr(telemetry.asyncpg, "create_pool", refuse)

    await telemetry.save_run_event(run_id="r", repo="backend", node="writer", provider="claude", status="success")
    assert "failed to save run event" in capsys.readouterr().out


# --- schema.sql must stay in sync with the SQL this module actually runs ------

SCHEMA_SQL = Path(__file__).parent / "schema.sql"

# Every column telemetry.py reads or writes, per table. If you add a column to an
# INSERT/SELECT in telemetry.py, add it here AND to schema.sql (and to the Prisma
# schema in the sibling backend project, if you share its database).
EXPECTED_COLUMNS = {
    "ExecutionMetric": {
        "id", "runId", "repo", "node", "provider", "model", "inputTokens", "outputTokens",
        "totalCostUsd", "durationMs", "success", "errorMessage", "createdAt",
    },
    "RunEvent": {"id", "runId", "repo", "node", "provider", "status", "detail", "prUrl", "createdAt"},
}


def _columns_in_schema(table: str) -> set[str]:
    sql = SCHEMA_SQL.read_text()
    match = re.search(rf'CREATE TABLE IF NOT EXISTS "{table}" \((.*?)\n\);', sql, re.S)
    assert match, f"schema.sql has no CREATE TABLE for {table}"
    body = re.sub(r"--.*", "", match.group(1))
    return set(re.findall(r'^\s*"([A-Za-z]+)"\s', body, re.M))


@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_schema_sql_defines_every_column_the_code_uses(table):
    assert _columns_in_schema(table) == EXPECTED_COLUMNS[table]


@pytest.mark.parametrize("table", sorted(EXPECTED_COLUMNS))
def test_every_column_in_telemetry_sql_is_expected(table):
    """Guards the guard: columns quoted in telemetry.py's SQL for this table must
    all be in EXPECTED_COLUMNS, so the list above can't silently go stale."""
    source = Path(telemetry.__file__).read_text()
    blocks = re.findall(rf'(?:FROM|INTO) "{table}"(.*?)"""', source, re.S)
    assert blocks, f"no SQL for {table} found in telemetry.py"
    used = {c for block in blocks for c in re.findall(r'"([A-Za-z]+)"', block)}
    assert used <= EXPECTED_COLUMNS[table], used - EXPECTED_COLUMNS[table]
