import asyncio
import json


async def fetch_pr_status(pr_url: str) -> str:
    """Live PR status ('open', 'merged', or 'closed') via the same `gh` CLI
    already authenticated locally for the writer node's own `gh pr create`
    calls - no separate GitHub token/auth needed here.

    Unlike save_run_event/record_metric, this is NOT best-effort: it backs
    a real GET endpoint whose whole job is answering "what's the PR status
    right now" - if `gh` fails (bad URL, not logged in, PR deleted), that
    should surface as a real error, not silently come back as something
    that looks like a valid status.
    """
    proc = await asyncio.create_subprocess_exec(
        "gh", "pr", "view", pr_url, "--json", "state",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(f"gh pr view failed for {pr_url}: {stderr.decode().strip()}")

    data = json.loads(stdout)
    return data["state"].lower()
