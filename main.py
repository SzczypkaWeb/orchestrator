import argparse
import asyncio
from dotenv import load_dotenv

load_dotenv(override=True)

from repos import REPOS, initial_state_for, detect_repo_from_cwd
from graph import compiled
from lead import run_lead


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lead", action="store_true", help="Split a cross-repo task automatically instead of specifying --repo")
    parser.add_argument(
        "--repo",
        choices=list(REPOS.keys()),
        help="Defaults to auto-detecting from the current directory if you're running this from inside a known repo (see repos.py / README)",
    )
    parser.add_argument("--branch", help="Continue an existing branch/PR instead of starting a new one (requires --pr-url; not compatible with --lead)")
    parser.add_argument("--pr-url", help="URL of the existing PR being fixed (used together with --branch)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--task")
    group.add_argument("--task-file")
    args = parser.parse_args()

    if not args.lead and not args.repo:
        args.repo = detect_repo_from_cwd()
        if not args.repo:
            parser.error(
                "--repo is required unless --lead is set or this is run from inside a "
                "known repo's own directory (cwd didn't match any entry in REPOS)"
            )

    if args.branch and not args.pr_url:
        parser.error("--branch requires --pr-url")
    if args.branch and args.lead:
        parser.error("--branch cannot be used with --lead")
    return args


async def main():
    args = parse_args()
    task_text = args.task if args.task else open(args.task_file).read()

    if args.lead:
        await run_lead(task_text)
        return

    result = await compiled.ainvoke(
        initial_state_for(args.repo, task_text, existing_branch=args.branch or "", existing_pr_url=args.pr_url or "")
    )
    print("Model chosen by classifier:", result["writer_model"])
    print("Branch:", result["branch"])
    print("PR:", result["pr_url"])
    print("Verify passed:", result.get("verify_passed"))
    if not result.get("verify_passed", True):
        print("Verify output:", result.get("verify_output"))
    print("Verdict:", result["review_verdict"])
    print("Notes:", result["review_notes"])


if __name__ == "__main__":
    asyncio.run(main())