-- Standalone schema for the orchestrator's optional Postgres persistence.
--
-- Only needed if you want run history and cost telemetry (the dashboard's
-- History section and per-run token/cost view). Without DATABASE_URL the
-- orchestrator runs fine and the dashboard is live-only.
--
-- This is a plain-SQL copy of the Prisma migrations in the sibling `backend`
-- project (add_execution_metric, add_run_event). If DATABASE_URL points at
-- backend's database these tables already exist and this file is not needed;
-- it is idempotent (IF NOT EXISTS) so running it there is harmless.
--
--   psql "$DATABASE_URL" -f schema.sql
--
-- Identifiers are quoted camelCase on purpose: telemetry.py quotes them the same
-- way, and unquoted names would be folded to lowercase by Postgres.

-- One row per provider call (classify / writer / security_review attempts).
CREATE TABLE IF NOT EXISTS "ExecutionMetric" (
    "id" TEXT NOT NULL,
    -- Groups every row produced by one run (one repo/task pair).
    "runId" TEXT NOT NULL,
    "repo" TEXT NOT NULL,
    "node" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "model" TEXT NOT NULL,
    "inputTokens" INTEGER,
    "outputTokens" INTEGER,
    -- Only populated for Claude Agent SDK calls; NULL for Groq/Gemini rows.
    "totalCostUsd" DECIMAL(10,4),
    "durationMs" INTEGER NOT NULL,
    "success" BOOLEAN NOT NULL,
    "errorMessage" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "ExecutionMetric_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "ExecutionMetric_runId_idx" ON "ExecutionMetric"("runId");
CREATE INDEX IF NOT EXISTS "ExecutionMetric_repo_createdAt_idx" ON "ExecutionMetric"("repo", "createdAt");

-- One row per graph event (the same events broadcast live over the WebSocket),
-- so run history survives restarts. Includes the synthetic nodes
-- `manually_completed` and `pr_merged`.
CREATE TABLE IF NOT EXISTS "RunEvent" (
    "id" TEXT NOT NULL,
    "runId" TEXT NOT NULL,
    "repo" TEXT NOT NULL,
    "node" TEXT NOT NULL,
    "provider" TEXT NOT NULL,
    "status" TEXT NOT NULL,
    "detail" TEXT,
    "prUrl" TEXT,
    "createdAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "RunEvent_pkey" PRIMARY KEY ("id")
);

CREATE INDEX IF NOT EXISTS "RunEvent_runId_idx" ON "RunEvent"("runId");
