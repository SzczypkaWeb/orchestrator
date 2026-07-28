# orchestrator

Agent for writing code (Claude Agent SDK) + LangGraph for coordination,
running across multiple repos (backend, frontend-shell).

## Requirements

- Python 3.12 (via `pyenv`, **not** the latest system version — LangGraph has
  compatibility issues with 3.13/3.14).
- `gh` CLI authenticated (`gh auth login`) with access to the repos listed below.
- One of:
  - `claude login` (Pro/Max subscription — recommended for learning/experiments,
    usage counts against your plan quota), or
  - `ANTHROPIC_API_KEY` in `.env` (API key from Console, pay-as-you-go, billed
    separately).

## Repos this orchestrator operates on

This repo must live as a **sibling** (next to) the repos listed in `REPOS` in
`repos.py`: