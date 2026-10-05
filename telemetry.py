import os
import time
import uuid

import asyncpg

# Optional Postgres persistence (run history + cost telemetry). Table/column
# names below are quoted to match the DDL in schema.sql exactly (ExecutionMetric,
# runId, inputTokens, ...) - Postgres folds unquoted identifiers to lowercase,
# which would silently miss the real table. schema.sql is a plain-SQL copy of
# the Prisma migrations in the sibling `backend` project, so you can either point
# DATABASE_URL at backend's database (nothing to create) or load schema.sql into
# any empty Postgres.
#
# DATABASE_URL is OPTIONAL. Without it the orchestrator still runs end to end:
# writes are skipped and reads come back empty (see _get_pool), so the dashboard
# works as a live-only view.

_pool: asyncpg.Pool | None = None
_warned_no_database = False


def database_configured() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


async def _get_pool() -> asyncpg.Pool | None:
    """The shared connection pool, or None when DATABASE_URL isn't set.

    "Not configured" is a normal, supported mode (not an error): callers treat
    None as "persistence is off". It is deliberately different from "configured
    but unreachable", which still raises here (asyncpg's own error) so that a
    broken database is never silently mistaken for an empty one.
    """
    global _pool, _warned_no_database
    if not database_configured():
        if not _warned_no_database:
            print(
                "[telemetry] DATABASE_URL is not set - run history and cost "
                "telemetry are disabled (see schema.sql to enable them)."
            )
            _warned_no_database = True
        return None
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=3)
    return _pool


async def fetch_run_events() -> list[dict]:
    """All persisted RunEvent rows, oldest first - same flat shape as the
    live broadcast() events, so the frontend can feed both history and
    live events into the same useGroupedRuns logic.

    Unlike save_run_event/record_metric, a failed read is NOT swallowed:
    those are side-effects that must never break an otherwise-successful
    run, but this function's whole job is returning real data to GET /runs -
    an unreachable database should surface as a real error there, not
    silently come back as an empty result. (No DATABASE_URL at all is
    different: that is "persistence is off", so the history is just empty.)
    """
    pool = await _get_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT "runId", repo, node, provider, status, detail, "prUrl", "createdAt"
            FROM "RunEvent"
            ORDER BY "createdAt" ASC
            """
        )
    return [
        {
            "run_id": row["runId"],
            "repo": row["repo"],
            "node": row["node"],
            "provider": row["provider"],
            "status": row["status"],
            "detail": row["detail"],
            "pr_url": row["prUrl"],
            "created_at": row["createdAt"].isoformat(),
        }
        for row in rows
    ]

async def fetch_run_metrics(run_id: str) -> list[dict]:
    """All ExecutionMetric rows for one run, oldest first - the token/cost/
    duration telemetry `record_metric` (below) already writes on every
    provider call, but which the dashboard has never surfaced anywhere until
    now (see the run-details modal). Same "not best-effort" contract as
    fetch_run_events: a failed read surfaces as a real error rather than
    silently looking like "no metrics"; only a missing DATABASE_URL yields [].
    """
    pool = await _get_pool()
    if pool is None:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT node, provider, model, "inputTokens", "outputTokens",
                   "totalCostUsd", "durationMs", success, "errorMessage", "createdAt"
            FROM "ExecutionMetric"
            WHERE "runId" = $1
            ORDER BY "createdAt" ASC
            """,
            run_id,
        )
    return [
        {
            "node": row["node"],
            "provider": row["provider"],
            "model": row["model"],
            "input_tokens": row["inputTokens"],
            "output_tokens": row["outputTokens"],
            # asyncpg returns NUMERIC/Decimal columns as Python Decimal -
            # not JSON-serializable as-is, so convert to float for the
            # response (some precision loss is fine for a cost estimate
            # that's only ever displayed, never recomputed with).
            "total_cost_usd": float(row["totalCostUsd"]) if row["totalCostUsd"] is not None else None,
            "duration_ms": row["durationMs"],
            "success": row["success"],
            "error_message": row["errorMessage"],
            "created_at": row["createdAt"].isoformat(),
        }
        for row in rows
    ]

async def save_run_event(
    *,
    run_id: str,
    repo: str,
    node: str,
    provider: str,
    status: str,
    detail: str | None = None,
    pr_url: str | None = None,
) -> None:
    """Best-effort persistence of one broadcast() event, so run history
    survives past the live WebSocket view (and app restarts). Same
    fire-and-log-don't-raise contract as record_metric below - a failed
    history write must never break the run itself."""
    try:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO "RunEvent"
                    (id, "runId", repo, node, provider, status, detail, "prUrl")
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                str(uuid.uuid4()),
                run_id,
                repo,
                node,
                provider,
                status,
                detail,
                pr_url,
            )
    except Exception as e:
        print(f"[runEvent] failed to save run event ({node}/{provider}): {e}")
        

async def record_metric(
    *,
    run_id: str,
    repo: str,
    node: str,
    provider: str,
    model: str,
    duration_ms: int,
    success: bool,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    total_cost_usd: float | None = None,
    error_message: str | None = None,
) -> None:
    """Best-effort telemetry write. Must never break an otherwise-successful
    (or already-failing) orchestrator run just because the DB write itself
    had a hiccup - errors are logged, not raised."""
    try:
        pool = await _get_pool()
        if pool is None:
            return
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO "ExecutionMetric"
                    (id, "runId", repo, node, provider, model, "inputTokens",
                     "outputTokens", "totalCostUsd", "durationMs", success, "errorMessage")
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
                """,
                str(uuid.uuid4()),
                run_id,
                repo,
                node,
                provider,
                model,
                input_tokens,
                output_tokens,
                total_cost_usd,
                duration_ms,
                success,
                error_message,
            )
    except Exception as e:
        print(f"[telemetry] failed to record metric ({node}/{provider}): {e}")


class Timer:
    """Tiny wall-clock stopwatch - `with Timer() as t: ...` then read
    `t.duration_ms`. Used around each provider call so duration is measured
    consistently whether the call succeeds or raises (see nodes.py)."""

    def __enter__(self) -> "Timer":
        self._start = time.monotonic()
        self.duration_ms = 0
        return self

    def __exit__(self, *exc_info) -> None:
        self.duration_ms = int((time.monotonic() - self._start) * 1000)
