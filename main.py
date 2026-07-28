import argparse
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

from repos import REPOS, initial_state_for
from graph import compiled
from lead import run_lead


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead", action="store_true", help="Split a cross-repo task automatically instead of specifying --repo")
    parser.add_argument("--repo", choices=list(REPOS.keys()))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task")
    group.add_argument("--task-file")
    args = parser.parse_args()
    if not args.lead and not args.repo:
        parser.error("--repo is required unless --lead is set")
    return args


async def main():
    args = parse_args()
    task_text = args.task if args.task else open(args.task_file).read()

    if args.lead:
        await run_lead(task_text)
        return

    result = await compiled.ainvoke(initial_state_for(args.repo, task_text))
    print("Model wybrany przez klasyfikator:", result["writer_model"])
    print("Branch:", result["branch"])
    print("PR:", result["pr_url"])
    print("Verdict:", result["review_verdict"])
    print("Notes:", result["review_notes"])


if __name__ == "__main__":
    asyncio.run(main())