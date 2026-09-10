import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from repos import REPOS, initial_state_for
from graph import compiled
from retry import with_retry, TransientError, TRANSIENT_STATUS_CODES

LEAD_SCHEMA = {
    "type": "object",
    "properties": {
        "subtasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "repo": {"type": "string", "enum": list(REPOS.keys())},
                    "task": {"type": "string"},
                },
                "required": ["repo", "task"],
            },
        },
    },
    "required": ["subtasks"],
}

async def split_task(high_level_task: str) -> list[dict]:
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

    async def attempt():
        subtasks = []
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
                    subtasks = message.structured_output["subtasks"]
                elif message.subtype == "success":
                    raise TransientError("Lead completed without calling structured output")
                else:
                    raise RuntimeError(f"Lead did not return valid structured output: {message.subtype}")
        return subtasks

    return await with_retry(attempt)

async def run_lead(high_level_task: str) -> None:
    subtasks = await split_task(high_level_task)
    if not subtasks:
        print("Lead found no repos requiring changes.")
        return

    print("Subtask breakdown:")
    for st in subtasks:
        print(f"  - {st['repo']}: {st['task']}")

    results = await asyncio.gather(
        *[compiled.ainvoke(initial_state_for(st["repo"], st["task"])) for st in subtasks],
        return_exceptions=True,
    )

    print("\n=== Results ===")
    for st, result in zip(subtasks, results):
        print(f"\n[{st['repo']}]")
        if isinstance(result, Exception):
            print(f"  ERROR: {result}")
        else:
            print(f"  Branch: {result['branch']}")
            print(f"  PR: {result['pr_url']}")
            print(f"  Verify passed: {result.get('verify_passed')}")
            print(f"  Verdict: {result['review_verdict']}")
            print(f"  Notes: {result['review_notes']}")