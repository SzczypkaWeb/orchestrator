from typing import Literal
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from state import GraphState
from schemas import CLASSIFY_SCHEMA, WRITER_SCHEMA, REVIEW_SCHEMA

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
"""
    model = "claude-sonnet-5"  # default;
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
                raise RuntimeError(f"Agent run failed ({message.api_error_status}): {message.result}")
            if message.subtype == "success" and message.structured_output:
                branch = message.structured_output["branch"]
                pr_url = message.structured_output["pr_url"]
            else:
                  raise RuntimeError(f"Writer agent did not return valid structured output: {message.subtype}")

    return {**state, "branch": branch, "pr_url": pr_url}


async def run_security_review(state: GraphState) -> GraphState:
    prompt = f"""
Review the changes on branch {state['branch']} in this repo
(e.g. `git diff main...{state['branch']}`). Stack: {state['stack_description']}

Check specifically for: {state['review_focus']}

Based on your review, decide on a verdict: "approved" if you find no
significant issues, or "changes_requested" if you find problems that
must be fixed before merging. Write your review notes in English,
explaining the reasoning behind your verdict.
"""
    verdict, notes = "", ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            cwd=state["repo_path"],
            allowed_tools=["Read", "Bash", "Glob", "Grep"],
            model="claude-haiku-4-5",
            output_format={"type": "json_schema", "schema": REVIEW_SCHEMA},
        ),
    ):
        if isinstance(message, ResultMessage):
            if message.is_error:
                raise RuntimeError(f"Agent run failed ({message.api_error_status}): {message.result}")
            if message.subtype == "success" and message.structured_output:
                verdict = message.structured_output["verdict"]
                notes = message.structured_output["notes"]
            else:
                raise RuntimeError(f"Security review agent did not return valid structured output: {message.subtype}")

    return {**state, "review_verdict": verdict, "review_notes": notes}


def route_after_review(state: GraphState) -> Literal["done", "blocked"]:
  return "done" if state["review_verdict"] == "approved" else "blocked"
