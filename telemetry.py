import os
import time
import uuid

import asyncpg

# Reuses backend's own DATABASE_URL (Supabase Postgres) - see
# backend/prisma/schema.prisma's ExecutionMetric model for the table shape,
# migrated the normal Prisma way even though the orchestrator itself writes
# to it directly over asyncpg (no Node/Prisma runtime here). Table/column
# names below are quoted to match Prisma's default casing exactly
# (ExecutionMetric, runId, inputTokens, ...) - Postgres folds unquoted
# identifiers to lowercase, which would silently miss the real table.

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(os.environ["DATABASE_URL"], min_size=1, max_size=3)
    return _pool


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
