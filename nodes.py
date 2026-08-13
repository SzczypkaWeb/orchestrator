import asyncio
import subprocess
from typing import Literal
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from state import GraphState
from schemas import CLASSIFY_SCHEMA, WRITER_SCHEMA, REVIEW_SCHEMA
from retry import with_retry, TransientError, TRANSIENT_STATUS_CODES
from providers import complete_with_groq, complete_with_gemini

# Reviewer is deliberately a different model family than the writer (Claude) -
# a second Claude call reviewing Claude's own output shares the same blind
# spots; Gemini looking at the same diff catches a genuinely different set of
# mistakes. Same reasoning for classify_task using Groq/Gemini first: cheaper/
# faster for a trivial classification, and moves this project off being
# Claude-only for every single call, not just the code-writing one.
MAX_REVIEW_ATTEMPTS = 2


async def classify_task(state: GraphState) -> GraphState:
    prompt = f"""
Classify the following development task by complexity:

Task: {state['task']}

- "simple_crud": a straightforward, repetitive CRUD-style change (e.g. add a
  standard REST endpoint, add a field, add basic validation, add pagination/
  sorting to an existing list endpoint) that follows patterns already
  established in this codebase.
- "novel": anything requiring new architecture, new integrations, security-
  sensitive design decisions, or patterns not already established.

When in doubt, classify as "novel" — it's safer to use the more careful model.

Respond with JSON matching this schema: {CLASSIFY_SCHEMA}
"""
    complexity = None

    # Groq first (cheapest/fastest), then Gemini, then Claude Haiku as the
    # last-resort fallback - classification must never hard-fail just because
    # a non-Claude provider had an off day, since it gates which model writes
    # the actual code.
    for provider_name, complete in (("groq", complete_with_groq), ("gemini", complete_with_gemini)):
        try:
            result = await asyncio.to_thread(complete, prompt, CLASSIFY_SCHEMA)
            complexity = result["complexity"]
            break
        except Exception as e:
            print(f"[classify_task] {provider_name} failed ({e}), trying next provider...")

    if complexity is None:
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=[],
                model="claude-haiku-4-5",
                output_format={"type": "json_schema", "schema": CLASSIFY_SCHEMA},
            ),
        ):
            if isinstance(message, ResultMessage):
                if not message.is_error and message.subtype == "success" and message.structured_output:
                    complexity = message.structured_output["complexity"]

    model = "claude-haiku-4-5" if complexity == "simple_crud" else "claude-sonnet-5"
    return {**state, "writer_model": model}


async def run_writer(state: GraphState) -> GraphState:
    # Three distinct situations, in priority order:
    #  1. Retrying after a "changes_requested" review verdict (review_attempts
    #     > 0) - continue on the branch/PR THIS run already created, fix the
    #     specific review feedback.
    #  2. Continuing an existing branch/PR passed in from the CLI (--branch/
    #     --pr-url) - a human-initiated follow-up task on prior work.
    #  3. Starting fresh - new branch, new PR.
    is_review_retry = state.get("review_attempts", 0) > 0
    continue_branch = state.get("existing_branch") or (state["branch"] if is_review_retry else "")
    continue_pr_url = state.get("existing_pr_url") or (state["pr_url"] if is_review_retry else "")

    if is_review_retry:
        prompt = f"""
You are working in a repo with this stack: {state['stack_description']}
Original task: {state['task']}

A code review of your previous changes on branch {continue_branch} (PR:
{continue_pr_url}) requested changes. Address this feedback — do NOT start
over or re-litigate the original task, just fix what's raised below:

{state['review_notes']}

Do the following steps in order:
1. git fetch origin && git checkout {continue_branch} && git pull origin {continue_branch}.
2. Fix the issues raised in the review feedback above. Add/update tests if the
   feedback implies missing coverage.
3. Run the linter (pnpm lint) and the test suite (pnpm test), fix anything that
   fails or produces warnings/errors.
4. Commit your changes (conventional commits).
5. Push to the SAME branch: git push origin {continue_branch}
   (this updates the existing PR automatically — do not run `gh pr create`).
6. Write all commit messages and code comments in English.

When you are finished, report exactly:
branch: {continue_branch}
pr_url: {continue_pr_url}
"""
    elif continue_branch:
        prompt = f"""
You are working in a repo with this stack: {state['stack_description']}
Task: {state['task']}

You are CONTINUING work on an EXISTING branch and an already-open pull request —
do NOT create a new branch and do NOT open a new PR.

Do the following steps in order:
1. git fetch origin && git checkout {continue_branch} && git pull origin {continue_branch}.
2. Write test(s) for the new behavior described above, if not already covered.
3. Implement the task so those tests pass.
4. Run the linter (pnpm lint) and the test suite (pnpm test), fix anything that
   fails or produces warnings/errors. Do not suppress lint errors with
   eslint-disable comments — fix the underlying type issue instead, unless you
   have a genuinely strong reason to suppress (state it explicitly if so).
5. Commit your changes (conventional commits).
6. Push to the SAME branch: git push origin {continue_branch}
   (this updates the existing PR automatically — do not run `gh pr create`).
7. Write all commit messages and code comments in English.

When you are finished, report exactly:
branch: {continue_branch}
pr_url: {continue_pr_url}
"""
    else:
        prompt = f"""
You are working in a repo with this stack: {state['stack_description']}
Task: {state['task']}

Do the following steps in order:
1. git checkout main && git pull, then create a new branch with a sensible name (feat/<something>).
2. Write test(s) based directly on the task specification above, BEFORE writing any
   implementation. These tests describe the expected contract/behavior, independent
   of how you will implement it.
3. Implement the task so those tests pass.
4. Run the test suite, fix anything that fails (fix the implementation, not the
   test, unless a test was genuinely wrong given the spec).
5. Commit your changes (conventional commits).
6. Push the branch and open a PR: gh pr create --base main --head <branch> --fill
7. Write all commit messages, the PR title/description, and any code comments in English.

When you are finished, clearly state in your final answer: the exact name of
the branch you created, and the full URL of the pull request you opened.
"""

    async def attempt():
        branch, pr_url = "", ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=state["repo_path"],
                allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep", "Skill"],
                model=state["writer_model"],
                output_format={"type": "json_schema", "schema": WRITER_SCHEMA},
                setting_sources=["user", "project"],
                skills="all",
            ),
        ):
            if isinstance(message, ResultMessage):
                if message.is_error:
                    if message.api_error_status in TRANSIENT_STATUS_CODES:
                        raise TransientError(f"{message.api_error_status}: {message.result}")
                    raise RuntimeError(f"Agent run failed ({message.api_error_status}): {message.result}")
                if message.subtype == "success" and message.structured_output:
                    branch = message.structured_output["branch"]
                    pr_url = message.structured_output["pr_url"]
                elif message.subtype == "success":
                    raise TransientError("Writer agent completed without calling structured output")
                else:
                    raise RuntimeError(f"Writer agent did not return valid structured output: {message.subtype}")
        return branch, pr_url

    branch, pr_url = await with_retry(attempt)
    return {**state, "branch": branch, "pr_url": pr_url}


def _build_review_prompt(state: GraphState, diff: str) -> str:
    return f"""Review the following diff (branch {state['branch']} vs main) in a repo
with this stack: {state['stack_description']}

Check specifically for: {state['review_focus']}

Diff:
{diff}

Based on your review, decide on a verdict: "approved" if you find no
significant issues, or "changes_requested" if you find problems that must be
fixed before merging. Write your review notes in English, explaining the
reasoning behind your verdict.

Respond with JSON matching this schema: {REVIEW_SCHEMA}
"""


async def _review_with_gemini(state: GraphState) -> tuple[str, str]:
    # Plain text-completion review (no agentic tool use - Gemini here isn't
    # browsing the repo itself), so the diff has to be fetched and handed to
    # it directly. Deliberately synchronous subprocess call wrapped in
    # to_thread rather than an asyncio subprocess - `git diff` is fast enough
    # that the extra plumbing isn't worth it, even though lead.py may run
    # several of these concurrently across repos.
    diff = await asyncio.to_thread(
        lambda: subprocess.run(
            ["git", "-C", state["repo_path"], "diff", f"main...{state['branch']}"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    if not diff.strip():
        raise RuntimeError(f"Empty diff for branch {state['branch']} vs main - nothing to review")

    result = await asyncio.to_thread(complete_with_gemini, _build_review_prompt(state, diff), REVIEW_SCHEMA)
    return result["verdict"], result["notes"]


async def _review_with_claude(state: GraphState) -> tuple[str, str]:
    # Original implementation, kept as the fallback: a real agentic Claude
    # review (can run `git diff`/read files itself) for when Gemini is
    # unavailable or misconfigured.
    prompt = f"""
Review the changes on branch {state['branch']} in this repo
(e.g. `git diff main...{state['branch']}`). Stack: {state['stack_description']}

Check specifically for: {state['review_focus']}

Based on your review, decide on a verdict: "approved" if you find no
significant issues, or "changes_requested" if you find problems that
must be fixed before merging. Write your review notes in English,
explaining the reasoning behind your verdict.
"""

    async def attempt():
        verdict, notes = "", ""
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                cwd=state["repo_path"],
                allowed_tools=["Read", "Bash", "Glob", "Grep", "Skill"],
                model="claude-haiku-4-5",
                output_format={"type": "json_schema", "schema": REVIEW_SCHEMA},
                setting_sources=["user", "project"],
                skills="all",
            ),
        ):
            if isinstance(message, ResultMessage):
                if message.is_error:
                    if message.api_error_status in TRANSIENT_STATUS_CODES:
                        raise TransientError(f"{message.api_error_status}: {message.result}")
                    raise RuntimeError(f"Agent run failed ({message.api_error_status}): {message.result}")
                if message.subtype == "success" and message.structured_output:
                    verdict = message.structured_output["verdict"]
                    notes = message.structured_output["notes"]
                elif message.subtype == "success":
                    raise TransientError("Security review agent completed without calling structured output")
                else:
                    raise RuntimeError(f"Security review agent did not return valid structured output: {message.subtype}")
        return verdict, notes

    return await with_retry(attempt)


async def run_security_review(state: GraphState) -> GraphState:
    try:
        verdict, notes = await _review_with_gemini(state)
    except Exception as e:
        print(f"[run_security_review] Gemini review failed ({e}), falling back to Claude...")
        verdict, notes = await _review_with_claude(state)

    review_attempts = state.get("review_attempts", 0) + (1 if verdict == "changes_requested" else 0)
    return {**state, "review_verdict": verdict, "review_notes": notes, "review_attempts": review_attempts}


def route_after_review(state: GraphState) -> Literal["done", "retry", "blocked"]:
    if state["review_verdict"] == "approved":
        return "done"
    if state.get("review_attempts", 0) < MAX_REVIEW_ATTEMPTS:
        return "retry"
    return "blocked"
