import asyncio
import logging
from typing import cast

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from pydantic import ValidationError

from events import broadcast
from graph import compiled
from logging_setup import current_run_id
from repos import REPOS, initial_state_for
from retry import TRANSIENT_STATUS_CODES, TransientError, with_retry
from schemas import LeadPlan, Subtask, lead_schema
from state import GraphState

logger = logging.getLogger(__name__)

LEAD_SCHEMA = lead_schema(REPOS.keys())


async def split_task(high_level_task: str) -> list[Subtask]:
    prompt = f"""
You are a technical lead splitting a cross-cutting engineering request into
repo-scoped subtasks.

Available repos and what they contain:
{chr(10).join(f"- {name}: {cfg['stack_description']}" for name, cfg in REPOS.items())}

Request: {high_level_task}

For each repo that needs a change, produce one subtask with a precise,
self-contained task description an engineer working ONLY in that repo could
follow without seeing the other repos. If a repo needs no change, omit it.
"""

    async def attempt() -> list[Subtask]:
        subtasks: list[Subtask] = []
        async for message in query(
            prompt=prompt,
            options=ClaudeAgentOptions(
                allowed_tools=[],
                model="claude-sonnet-5",
                output_format={"type": "json_schema", "schema": LEAD_SCHEMA},
            ),
        ):
            if isinstance(message, ResultMessage):
                if message.is_error:
                    if message.api_error_status in TRANSIENT_STATUS_CODES:
                        raise TransientError(f"{message.api_error_status}: {message.result}")
                    raise RuntimeError(f"Lead splitting failed ({message.api_error_status}): {message.result}")
                if message.subtype == "success" and message.structured_output:
                    # Retrying is safe here, unlike in the writer: the lead runs
                    # with no tools, so a bad plan has had no side effects yet.
                    try:
                        plan = LeadPlan.model_validate(message.structured_output)
                    except ValidationError as e:
                        raise TransientError(f"Lead returned an invalid plan: {e}") from e
                    unknown = sorted({subtask.repo for subtask in plan.subtasks} - REPOS.keys())
                    if unknown:
                        raise TransientError(f"Lead planned work for unknown repo(s): {', '.join(unknown)}")
                    subtasks = plan.subtasks
                elif message.subtype == "success":
                    raise TransientError("Lead completed without calling structured output")
                else:
                    raise RuntimeError(f"Lead did not return valid structured output: {message.subtype}")
        return subtasks

    return await with_retry(attempt)


async def invoke_run(state: GraphState) -> GraphState:
    """Run the graph for one repo, with every log line it produces tagged with
    the run's id (see logging_setup.current_run_id). The outcome is logged here
    too, while that id is still set: a summary line on success, the traceback
    on failure (before the error propagates)."""
    token = current_run_id.set(state["run_id"])
    try:
        # LangGraph types ainvoke's result as a plain dict; it is the final
        # GraphState, so cast() only tells pyright what it already is.
        result = cast(GraphState, await compiled.ainvoke(state))
    except Exception:
        logger.exception("Run failed for repo %s", state["repo"])
        raise
    else:
        _log_result(result)
        return result
    finally:
        current_run_id.reset(token)


def _log_result(result: GraphState) -> None:
    logger.info(
        "Run finished for repo %s: branch=%s pr=%s verify_passed=%s verdict=%s",
        result["repo"],
        result["branch"],
        result["pr_url"],
        result.get("verify_passed"),
        result["review_verdict"],
    )


async def run_lead(high_level_task: str) -> None:
    subtasks = await split_task(high_level_task)
    if not subtasks:
        logger.info("Lead found no repos requiring changes")
        return

    logger.info("Lead split the task into %d subtask(s): %s", len(subtasks), ", ".join(st.repo for st in subtasks))
    for st in subtasks:
        logger.debug("Subtask for %s: %s", st.repo, st.task)

    # Build each subtask's state once (not inline in the gather() call below)
    # so we can broadcast its "trigger" event - carrying the task text, since
    # that's otherwise never persisted anywhere - right as each run starts,
    # instead of leaving the UI with nothing to show until the first real
    # node (classify_task) finishes several seconds later.
    states: list[GraphState] = []
    for st in subtasks:
        state = initial_state_for(st.repo, st.task)
        await broadcast(
            {
                "run_id": state["run_id"],
                "repo": state["repo"],
                "node": "trigger",
                "provider": "user",
                "status": "success",
                "detail": st.task,
            }
        )
        states.append(state)

    # return_exceptions=True: one failed repo must not cancel the others.
    # Each run's outcome, success or failure, is logged inside invoke_run.
    await asyncio.gather(
        *[invoke_run(state) for state in states],
        return_exceptions=True,
    )


async def run_single(repo: str, task: str) -> None:
    state = initial_state_for(repo, task)
    await broadcast(
        {
            "run_id": state["run_id"],
            "repo": state["repo"],
            "node": "trigger",
            "provider": "user",
            "status": "success",
            "detail": task,
        }
    )
    await invoke_run(state)
