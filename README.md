# orchestrator

Agent for writing code (Claude Agent SDK) + LangGraph for coordination,
running across multiple repos (backend, frontend-shell, react-app, shared-ui,
next-app, e2e-tests).

## Requirements

- Python 3.12 (via `pyenv`, **not** the latest system version — LangGraph has
  compatibility issues with 3.13/3.14).
- `gh` CLI authenticated (`gh auth login`) with access to the repos listed below.
- One of:
  - `claude login` (Pro/Max subscription — recommended for learning/experiments,
    usage counts against your plan quota), or
  - `ANTHROPIC_API_KEY` in `.env` (API key from Console, pay-as-you-go, billed
    separately).
- `GROQ_API_KEY` and `GEMINI_API_KEY` in `.env` — see `.env.example`. Same
  accounts already used by `ai-service`.

## Multi-provider flow (not Claude-only)

Two nodes deliberately don't go straight to Claude:

- `classify_task` tries Groq, then Gemini, then falls back to Claude Haiku
  only if both fail. Cheap/fast structured JSON call, no agentic tool use
  needed for a single enum decision.
- `security_review` reviews the writer's diff with Gemini first (fetches
  `git diff main...<branch>` itself and hands it to Gemini as plain text),
  falling back to the original agentic Claude Haiku review if Gemini errors.
  Using a different model family than the writer for review is the point —
  a second Claude call reviewing Claude's own output shares the same blind
  spots.

## Self-healing retry loop

`security_review` no longer only returns `"done"` or `"blocked"`. A
`"changes_requested"` verdict now routes back to `writer` (via
`route_after_review` in `nodes.py` / the conditional edge in `graph.py`), up
to `MAX_REVIEW_ATTEMPTS` (2) times before giving up and reporting `blocked`.
On a retry, `run_writer` checks out the same branch it already pushed and
fixes exactly the review feedback — it does not start over or open a second
PR. State tracked via `review_attempts` in `state.py`.

## Running it from inside a repo (no `cd` into `orchestrator/` needed)

`--repo` is optional — if omitted (and `--lead` isn't set), `main.py` checks
`cwd` and matches it against one of the repos in `REPOS` (see
`detect_repo_from_cwd()` in `repos.py`; also works from a subdirectory, e.g.
`frontend-shell/src`). This makes it convenient to add a function to
`~/.zshrc`:

```bash
orc() {
  uv run --project /Users/piotrszczypka/Documents/szczypka-web/orchestrator \
    /Users/piotrszczypka/Documents/szczypka-web/orchestrator/main.py --task "$*"
}
```

(`--project` only tells uv where `pyproject.toml`/the venv is - it does NOT
change the `cwd` of the running script, unlike `--directory`. This matters,
because `detect_repo_from_cwd()` needs to see your actual directory.)

Usage from any repo:

```bash
cd ../frontend-shell
orc "add a 'phone' field to the registration form"
```

For `--lead`, `--branch`/`--pr-url`, or when you want to force a different
repo than the one you're standing in - call the script directly (with the
full flags), `orc` only covers the most common case of "one task, one repo,
the one I'm in".

## Repos this orchestrator operates on

This repo must live as a **sibling** (next to) the repos listed in `REPOS` in
`repos.py`: `backend`, `frontend-shell`, `react-app`, `shared-ui`, `next-app`,
`e2e-tests`. `repos.py` is the single source of truth for the path, stack
description and review focus of each - update it there, not here, when a repo's
conventions change.

`ai-service` and `infra` (Terraform + docker-compose, siblings of this repo)
are **not** currently registered here - see the note left in `repos.py` history/
PR discussion before adding them, since their review focus (IAM scope, Terraform
state handling, LLM-provider-facing input for ai-service) is different enough
from the app repos above that it deserves its own `review_focus` written
deliberately, not copy-pasted.