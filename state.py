from typing import TypedDict

class GraphState(TypedDict):
    task: str
    # REPOS key this run targets (backend, frontend-shell, ...) - see
    # repos.py. Kept separate from repo_path since telemetry rows want the
    # short logical name, not a filesystem path.
    repo: str
    # Groups every telemetry row this run produces (classify + writer +
    # review, possibly several review-retry rows) - see telemetry.py and
    # repos.py's initial_state_for().
    run_id: str
    repo_path: str
    stack_description: str
    review_focus: str
    # Base branch the writer opens its PR against and the reviewer diffs
    # against - "staging" for repos with a staging deploy environment
    # (backend, frontend-shell, react-app all deploy on push to `staging`
    # before anything reaches `main` - see repos.py/RUNBOOK.md), "main"
    # everywhere else. Set by repos.py's initial_state_for() - never
    # hardcode "main" directly in a prompt or a `git diff`/`gh pr create`
    # call, or it silently targets the wrong branch for these three repos.
    target_branch: str
    writer_model: str
    branch: str
    pr_url: str
    review_verdict: str
    review_notes: str
    existing_branch: str
    existing_pr_url: str
    # Number of times security_review has sent this task back to the writer
    # after a "changes_requested" verdict (see route_after_review in nodes.py).
    # Not set by initial_state_for() - defaults to 0 via state.get(...) at
    # every read site, so existing callers don't need to change.
    review_attempts: int
    # Deterministic gate run between writer and security_review - actually
    # runs `pnpm lint`/`pnpm test` on the branch rather than trusting the
    # writer's own tool calls succeeded (see run_verification in nodes.py).
    # Separate counter/fields from review_* on purpose: a lint/test failure
    # is a different kind of feedback than an LLM review verdict, and gets
    # its own small retry budget so it can't eat into review's. Also not set
    # by initial_state_for() - same state.get(..., default) pattern.
    verify_passed: bool
    verify_output: str
    verify_attempts: int