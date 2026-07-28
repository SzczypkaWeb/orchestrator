from pathlib import Path

REPOS = {
    "backend": {
        "path": str(Path("../backend").resolve()),
        "stack_description": "Nest.js + Prisma (PostgreSQL). Run tests with `pnpm test`.",
        "review_focus": "secrets in code, missing input validation, SQL injection, overly permissive CORS, missing tests for new logic",
    },
    "frontend-shell": {
        "path": str(Path("../frontend-shell").resolve()),
        "stack_description": "React + TypeScript, webpack (Module Federation host / app-shell for microfrontends).",
        "review_focus": "secrets or API keys hardcoded in client-side code, XSS risks, missing input validation on forms, unsafe eval/Function usage, missing tests for new logic",
    },
}

def initial_state_for(repo_name: str, task_text: str) -> dict:
    cfg = REPOS[repo_name]
    return {
        "task": task_text,
        "repo_path": cfg["path"],
        "stack_description": cfg["stack_description"],
        "review_focus": cfg["review_focus"],
        "writer_model": "",
        "branch": "", "pr_url": "", "review_verdict": "", "review_notes": "",
    }