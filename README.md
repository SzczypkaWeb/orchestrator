# orchestrator

A multi-agent coding pipeline: give it a task in plain English and it classifies
it, writes the code in the right repo (Claude Agent SDK), proves the result with
the repo's own lint and tests, has a *different* model family review the diff,
and opens a pull request. Cross-cutting tasks are split per repo and run in
parallel. A small web dashboard shows every run live.

Built with [LangGraph](https://github.com/langchain-ai/langgraph) (coordination),
the [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)
(the agent that writes code), FastAPI + WebSockets (live events) and a
React/TypeScript dashboard.

> **Status: personal project, local use only.** It runs real commands against
> your real repos and the control server has **no authentication yet**. Read
> [Safety model](#safety-model) before running it anywhere but your own machine.

## How a run works

```mermaid
flowchart LR
    T[task] --> C[classify_task<br/>Groq → Gemini → Claude Haiku]
    C --> W[writer<br/>Claude Agent SDK<br/>branch + PR]
    W --> V[verify<br/>real pnpm lint + pnpm test]
    V -- pass --> R[security_review<br/>Gemini → Claude Haiku]
    V -- fail, retries left --> W
    V -- out of retries --> B[(blocked)]
    R -- done --> D[(done)]
    R -- changes_requested --> W
    R -- out of retries --> B
```

- **Cheap models for cheap decisions.** `classify_task` is a single structured-JSON
  call, so it tries Groq, then Gemini, and only falls back to Claude Haiku if both
  fail.
- **A different model reviews the code.** `security_review` reads
  `git diff <target>...<branch>` and sends it to Gemini; a second Claude call
  reviewing Claude's output shares its blind spots. Claude Haiku (agentic, can
  read the repo) is the fallback.
- **Verification is a real exit code, not an opinion.** `verify` runs `pnpm lint`
  and then `pnpm test` as subprocesses in the target repo. The review step is never
  spent on a diff that fails its own checks.
- **Two independent retry budgets** (2 each, in `nodes.py`): failed verification
  and `changes_requested` reviews both loop back to `writer`, which checks out the
  branch it already pushed and fixes exactly what was reported. It never starts over
  or opens a second PR.
- **Parallel multi-repo tasks.** With `--lead`, a planning call splits one
  high-level task into per-repo subtasks (`lead.py`) and runs the graph for each
  concurrently with `asyncio.gather`. Each subtask gets its own `run_id`.
- **Observability.** Every provider call writes a cost/token row, and every graph
  event is persisted and broadcast over WebSocket (`events.py`, `telemetry.py`), so
  the dashboard can show live progress *and* history.

## Requirements

- Python 3.12 (LangGraph has had compatibility problems with 3.13+).
- [`uv`](https://docs.astral.sh/uv/) (recommended) or `pip`.
- `pnpm` and the [GitHub CLI](https://cli.github.com/) (`gh auth login`) - the
  pipeline shells out to both.
- Claude access: `claude login` (subscription) **or** `ANTHROPIC_API_KEY`.
- `GROQ_API_KEY` and `GEMINI_API_KEY` (free tiers work).
- Optional, for run history that survives restarts: a Postgres database (see
  [Database](#database-optional)).

## Quick start

```bash
git clone <this repo> && cd orchestrator
uv sync                      # or: python -m venv .venv && pip install -r requirements.txt
cp .env.example .env         # then fill in your own keys - .env is gitignored
```

Run one task against one repo:

```bash
uv run main.py --repo backend --task "Add a DELETE /listings/:id endpoint"
```

Let the orchestrator split a cross-cutting task across repos and run them in parallel:

```bash
uv run main.py --lead --task "Add a favorites feature: backend endpoint + UI toggle"
```

Other flags: `--task-file <path>` (long task descriptions), `--branch <name>
--pr-url <url>` (continue fixing an existing PR instead of opening a new one).

### Run it from inside a repo

If `--repo` is omitted, `main.py` matches your current directory against the
configured repos (it also works from a subdirectory). A shell helper makes this
convenient:

```bash
# ~/.zshrc  (point ORCH_DIR at your checkout of this repo)
orc() { uv run --project "$ORCH_DIR" "$ORCH_DIR/main.py" --task "$*"; }
```

```bash
cd ../frontend-shell && orc "add a 'phone' field to the registration form"
```

(`--project` tells uv where the virtualenv is without changing the working
directory, which `detect_repo_from_cwd()` relies on.)

## Dashboard

```bash
# terminal 1 - API + WebSocket (binds to 127.0.0.1 by default; keep it that way)
uv run uvicorn control_server:app

# terminal 2 - UI
cd dashboard && cp .env.example .env && pnpm install && pnpm dev   # http://localhost:5173
```

It lets you trigger a task, shows runs as they progress node by node, keeps the
history across restarts, shows the PR status (open / merged / closed) and
per-run token and cost telemetry. Runs move from **Active** to **History** once
their PR is merged or you mark a stalled run as done.

API surface (`control_server.py`): `POST /runs`, `GET /runs`,
`GET /runs/{run_id}/metrics`, `GET /pr-status`, `GET /repos`, `POST /runs/complete`,
`POST /runs/pr-merged`, `GET /ping`, and `WS /ws`.

The frontend is organised by feature (`src/features/{runs,trigger-form,connection-status}`)
rather than by file type; `App.tsx` is only a composition root.

The UI is built from [shadcn/ui](https://ui.shadcn.com)-style components (Radix primitives +
Tailwind v4) that live in `dashboard/src/components/ui/` as plain source, so
`pnpm install` needs nothing but the public npm registry.

## Database (optional)

Postgres is optional. It stores run history (`RunEvent`) and per-call cost telemetry
(`ExecutionMetric`) via `asyncpg`, enabled by setting `DATABASE_URL`.

**Without `DATABASE_URL`** everything still works: runs execute normally, writes are
skipped (one warning is logged), and `GET /runs` / `GET /runs/{id}/metrics` return
empty lists, so the dashboard is a live-only view. History is gone on restart.

**To enable history**, create the tables in any Postgres you control:

```bash
psql "$DATABASE_URL" -f schema.sql     # idempotent (IF NOT EXISTS)
```

`schema.sql` is a plain-SQL copy of the Prisma migrations of the author's sibling
`backend` project, which shares this database in the author's setup; if you point
`DATABASE_URL` at such a database the tables already exist. A configured-but-unreachable
database is **not** treated as "empty": reads raise, so a broken connection can't be
mistaken for a clean history (writes stay best-effort and never fail a run).
A test keeps `schema.sql` in sync with the SQL in `telemetry.py`.

## Configuring the repos it can operate on

The registry is a YAML file, not code. Copy the template and edit it:

```bash
cp orchestrator.example.yaml orchestrator.yaml    # gitignored - your local setup
```

For each repo it holds the `path`, a `stack_description` (given to the writer), a
`review_focus` checklist (given to the reviewer) and the `target_branch` PRs are
opened against (default `main`). Relative paths resolve against the config file's
directory, so `../my-api` means a sibling checkout. To keep the file elsewhere, set
`ORCHESTRATOR_CONFIG=/path/to/file.yaml`. The file is parsed with `yaml.safe_load`
and validated on startup (unknown keys, missing fields and empty values are
rejected with a readable error). Keep the descriptions specific: they are the main
lever on output quality. Each target repo's own `CLAUDE.md` and `.claude/skills/`
are also loaded by the writer, so project conventions can live in the target repo.
`examples/szczypka-web.yaml` is the author's real six-repo setup as a worked example.

## Tests and linting

```bash
uv run pytest                 # unit tests (asyncio_mode=auto)
uv run ruff check .           # lint (rule set E, F, I - see pyproject.toml)
cd dashboard && pnpm lint && pnpm build   # oxlint + tsc -b + vite build
```

The Python suite covers the control-server endpoints (using FastAPI's
`TestClient` with the broadcast layer stubbed) and the telemetry/persistence layer
(with `asyncpg` mocked), so it needs neither a database nor any API keys. There is
no automated test coverage of the LLM nodes themselves; they are exercised by real
runs. CI (`.github/workflows/`) runs the Python lint + tests, the dashboard lint + build, and the secret scan.

## Safety model

Be explicit about what this tool does, because it is the reason it is not public-facing:

- The **writer agent has `Bash`, `Edit` and `Write`** inside the target repo, and
  `verify` runs `pnpm lint` / `pnpm test` there. That is arbitrary code execution
  driven by the task text, with your user's permissions and your repo's
  dependencies. There is **no sandbox**.
- The **control server has no authentication**. Anyone who can reach it can start
  runs. It binds to localhost by default and CORS only allows the dashboard origin
  (`DASHBOARD_ORIGIN`), which is not a security boundary against non-browser
  clients. **Do not expose it to a network, tunnel, or the public internet** until
  runs execute in an isolated environment and requests are authenticated.
- Only give it tasks you wrote, against repos you trust. Treat task text like a
  shell command.
- Secrets live only in `.env` (gitignored). Never commit it; `.env.example` holds
  placeholders only.

CI scans the full git history for secrets on every PR
(`.github/workflows/secret-scan.yml`, gitleaks). Planned hardening: ephemeral
sandboxed execution and authentication on the control server.

## Repository layout

| Path | Purpose |
|---|---|
| `graph.py`, `state.py` | LangGraph definition and shared run state |
| `nodes.py` | `classify_task`, `run_writer`, `run_verification`, `run_security_review` and routing |
| `lead.py` | Splits a task across repos and runs subtasks in parallel |
| `repos.py` | Loads and validates the repo registry from YAML |
| `orchestrator.example.yaml`, `examples/` | Registry template and the author's worked example |
| `providers.py`, `retry.py`, `schemas.py` | Provider clients, retry helper, structured-output schemas |
| `events.py`, `telemetry.py` | Event broadcast/persistence and cost telemetry |
| `github.py` | PR status through the `gh` CLI |
| `control_server.py` | FastAPI HTTP + WebSocket API for the dashboard |
| `dashboard/` | React + TypeScript + Vite dashboard |
| `skills/` | Example Claude skill loaded by the writer |
| `test_*.py` | Python tests |

## License

MIT
