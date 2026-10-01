# orchestrator

## Stack
Python 3.12 + LangGraph + Claude Agent SDK. Dispatches coding tasks to
Claude (with Groq/Gemini fallbacks for classification) against the sibling
repos in this monorepo, opens PRs. FastAPI (`control_server.py`) + a React
dashboard (`dashboard/`, see its own conventions in
`dashboard/src/features/*`) expose this over HTTP/WebSocket.

## Run / test
- `python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
- `python main.py --repo backend --task "..."` — single-repo run.
- `python main.py --lead --task "..."` — cross-repo, split + parallel dispatch.
- `uvicorn control_server:app --reload` — dashboard backend.
- `pytest` — unit tests (`test_*.py`, colocated with source).
- `ruff check .` — lint (conservative rule set: `E`, `F`, `I` — see
  `pyproject.toml` for why).
- No Python typecheck configured yet (no mypy) — dashboard's own
  `pnpm typecheck` covers the TS side.

## Structure
- `repos.py` — repo registry (path, stack description, review checklist).
- `state.py` — graph state type (`GraphState`).
- `schemas.py` — JSON schemas for structured output.
- `nodes.py` — agent logic (`classify_task`, `run_writer`, `run_security_review`).
- `graph.py` — wires nodes into a LangGraph graph.
- `lead.py` — splits cross-repo tasks into per-repo subtasks, dispatches in parallel.
- `main.py` — CLI entry point.
- `retry.py` — retry helper for transient provider errors.
- `github.py` — PR status via `gh` subprocess.
- `telemetry.py` — per-call cost/token logging straight to backend's Postgres.
- `control_server.py` — FastAPI dashboard backend (`/runs`, `/ws`, `/pr-status`).
- `dashboard/` — React + TS dashboard, feature-folder structure
  (`src/features/connection-status`, `src/features/trigger-form`,
  `src/features/runs`) — see that folder's own conventions before adding to it.

## Conventions
- Each target repo (`backend`, `frontend-shell`, ...) has its own CLAUDE.md
  (always loaded) and `.claude/skills/` (loaded on demand) — read the target
  repo's conventions before writing code into it, don't assume this
  repo's conventions apply there.
- `load_dotenv(override=True)` must run before any import that reads env
  vars at import time — see `control_server.py`/`main.py`'s import order
  (and their `ruff` per-file E402 ignore).
- System-detected facts (e.g. a merged PR) get persisted as a real
  `RunEvent`/broadcast, not just re-derived live on every request — see
  `runStatus.ts`'s comment in the dashboard for why.

## Never do
- Never let `verify`/security-review subprocess calls (`pnpm lint`/`pnpm test`
  in a target repo) run against untrusted, free-text task input from
  anyone but you — this is real code execution, not sandboxed (see
  BLOG_NOTES.md on why the public dashboard idea was shelved).
- Never commit `.env` or real API keys/tokens.
- Never widen a workflow's `permissions:` beyond the job that actually needs
  it (see `backend`'s `deploy-gcp.yml` id-token/Dependabot incident for why).
- Never merge with a red `pytest`/`ruff check`.
