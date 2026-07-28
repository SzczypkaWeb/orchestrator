import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage
from repos import REPOS, initial_state_for
from graph import compiled

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
    # print("=== DEBUG PROMPT ===")
    # print(prompt)
    # print("=== /DEBUG PROMPT ===")

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
            # print("=== DEBUG MESSAGE ===")
            # print(repr(message))
            # print("=== /DEBUG MESSAGE ===")
            if message.is_error:
                raise RuntimeError(f"Lead splitting failed ({message.api_error_status}): {message.result}")
            if message.subtype == "success" and message.structured_output:
                subtasks = message.structured_output["subtasks"]
            else:
                raise RuntimeError(f"Lead nie zwrocil poprawnego structured output: {message.subtype}")
    return subtasks

async def run_lead(high_level_task: str) -> None:
    subtasks = await split_task(high_level_task)
    if not subtasks:
        print("Lead nie znalazl zadnych repo do zmiany.")
        return

    print("Podzial na pod-zadania:")
    for st in subtasks:
        print(f"  - {st['repo']}: {st['task']}")

    results = await asyncio.gather(
        *[compiled.ainvoke(initial_state_for(st["repo"], st["task"])) for st in subtasks],
        return_exceptions=True,
    )

    print("\n=== Wyniki ===")
    for st, result in zip(subtasks, results):
        print(f"\n[{st['repo']}]")
        if isinstance(result, Exception):
            print(f"  BLAD: {result}")
        else:
            print(f"  Branch: {result['branch']}")
            print(f"  PR: {result['pr_url']}")
            print(f"  Verdict: {result['review_verdict']}")
            print(f"  Notes: {result['review_notes']}")