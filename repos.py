import uuid
from pathlib import Path

# All repo paths below are resolved relative to THIS FILE's location, not the
# process's current working directory. Previously they used bare
# `Path("../backend")` (relative to cwd), which only worked by accident
# because main.py was always invoked from inside orchestrator/ itself - it
# silently resolved to the wrong path when run from any other directory
# (e.g. a sibling repo). Anchoring to __file__ makes path resolution
# invocation-location-independent, which is what makes detect_repo_from_cwd()
# below (and running `main.py` from inside a repo's own directory - see
# README) actually safe.
_SIBLINGS_DIR = Path(__file__).resolve().parent.parent

# Shared design-token/Tailwind v4 convention, referenced by every consumer app
# below (frontend-shell, react-app, next-app) so writer agents don't
# accidentally hand-roll what shared-ui already publishes.
_TAILWIND_CONSUMER_NOTE = (
    "Tailwind v4, CSS-first config (no tailwind.config.js). Design tokens and the "
    "postcss plugin config are NOT defined locally - they're imported from "
    "@szczypkaweb/shared-ui: `@import \"@szczypkaweb/shared-ui/globals.css\";` in the "
    "app's CSS entry point (plus `@source \"../node_modules/@szczypkaweb/shared-ui/dist\";` "
    "so Tailwind's content scanner picks up shared-ui's own compiled utility classes), "
    "and `module.exports = require('@szczypkaweb/shared-ui/postcss.config');` (or the "
    "ESM equivalent) in postcss.config. Never redefine color/radius tokens or the "
    "postcss plugin list locally - update shared-ui and bump the dependency instead."
)

REPOS = {
    "backend": {
        "path": str(_SIBLINGS_DIR / "backend"),
        "stack_description": "Nest.js + Prisma (PostgreSQL, hosted on Supabase). Deployed to GCP Cloud Run via Workload Identity Federation (keyless GitHub Actions auth, no static service-account keys). Run tests with `pnpm test`.",
        "review_focus": "secrets in code, missing input validation, SQL injection, overly permissive CORS, missing tests for new logic. lint errors or eslint-disable comments suppressing type-safety rules without justification",
    },
    "frontend-shell": {
        "path": str(_SIBLINGS_DIR / "frontend-shell"),
        "stack_description": (
            "React + TypeScript, webpack (Module Federation host / app-shell for "
            "microfrontends, consumes react-app's exposed './Widget' remote and also "
            "exposes its own './authStore' as MF container 'shell'). Deploy target: "
            "Azure Static Web Apps (in progress - see staticwebapp.config.json for the "
            "CORS headers on this app's own remoteEntry.js/chunks and the SPA "
            "navigationFallback rule; no dedicated Azure workflow yet, unlike react-app). "
            + _TAILWIND_CONSUMER_NOTE
        ),
        "review_focus": (
            "secrets or API keys hardcoded in client-side code, XSS risks, missing input "
            "validation on forms, unsafe eval/Function usage, missing tests for new logic, "
            "hand-copied design tokens or postcss config instead of importing from "
            "@szczypkaweb/shared-ui, Module Federation `shared` config drifting out of sync "
            "with react-app's (react/react-dom must stay singleton), changes to what this "
            "app exposes/serves at the root without a matching staticwebapp.config.json update"
        ),
    },
    "react-app": {
        "path": str(_SIBLINGS_DIR / "react-app"),
        "stack_description": (
            "React + TypeScript, webpack (Module Federation remote, exposes './Widget' "
            "consumed by frontend-shell). Deploy target: Azure Static Web Apps (workflow "
            "already exists at .github/workflows/azure-static-web-apps.yml; deployed URL is "
            "echoed to the job summary for use as frontend-shell's REACT_APP_REMOTE_URL). "
            "staticwebapp.config.json sets Access-Control-Allow-Origin on remoteEntry.js and "
            "MF chunk files - required because Azure Static Web Apps doesn't add CORS headers "
            "to static files by default, and frontend-shell loads this app's remoteEntry.js "
            "cross-origin once both are deployed as separate Static Web Apps. "
            + _TAILWIND_CONSUMER_NOTE
        ),
        "review_focus": (
            "secrets or API keys hardcoded in client-side code, XSS risks, missing tests for "
            "new logic, correct Module Federation shared/exposes config (react and react-dom "
            "marked as singleton to avoid duplicate React instances), hand-copied design "
            "tokens or postcss config instead of importing from @szczypkaweb/shared-ui, new "
            "static entry points (remoteEntry.js-like files, new chunks) missing a matching "
            "CORS route in staticwebapp.config.json"
        ),
    },
    "shared-ui": {
        "path": str(_SIBLINGS_DIR / "shared-ui"),
        "stack_description": (
            "React + TypeScript component library, built with tsup (ESM+CJS), documented "
            "with Storybook, versioned with Changesets, published to GitHub Packages as "
            "@szczypkaweb/shared-ui. Consumed by frontend-shell, react-app and next-app. "
            "Tailwind v4 (shadcn/ui conventions, `cn()` from src/lib/utils.ts merges classes "
            "via clsx+tailwind-merge) - components are styled with literal Tailwind utility "
            "class strings (so consumers' content scanners pick them up from the compiled "
            "dist output), never with hand-authored CSS classes/stylesheets. Publishes two "
            "extra subpath exports besides the component library itself: `./globals.css` "
            "(shared design tokens + @theme mapping + dark-mode custom variant) and "
            "`./postcss.config` (the shared @tailwindcss/postcss plugin config, as a plain "
            ".cjs file so it stays require()-able from CJS consumers despite this package's "
            "own \"type\": \"module\") - both exist specifically so frontend-shell/react-app/"
            "next-app don't each redefine the same tokens/config and drift out of sync."
        ),
        "review_focus": (
            "components must not reference `window`/`document` at module scope (breaks SSR "
            "consumers later), no secrets in code, missing tests for new components, correct "
            "ESM+CJS build output, new components styled with legacy hand-authored CSS "
            "classes instead of Tailwind utility classes (a stylesheet defining those classes "
            "likely doesn't exist anymore post-Tailwind-migration, so they'd render "
            "unstyled), changes to globals.css or postcss-preset.cjs without checking whether "
            "the package.json `exports`/`files` fields still cover them"
        ),
    },
    "next-app": {
        "path": str(_SIBLINGS_DIR / "next-app"),
        "stack_description": (
            "Next.js (App Router) + TypeScript marketing/SEO site (domena.pl), deployed to "
            "Vercel. This is an app, NOT the component library - it's a consumer of "
            "@szczypkaweb/shared-ui (installed as a normal registry dependency), not the "
            "thing being published. Run tests with `pnpm test` (Vitest). " + _TAILWIND_CONSUMER_NOTE
        ),
        "review_focus": (
            "secrets or API keys hardcoded in client-side code, missing tests for new logic, "
            "Server Component vs Client Component boundaries (no `window`/`document`/browser "
            "APIs in Server Components), hand-copied design tokens or postcss config instead "
            "of importing from @szczypkaweb/shared-ui, SEO regressions (missing/incorrect "
            "metadata) given this app's entire purpose is marketing/SEO"
        ),
    },
    "e2e-tests": {
        "path": str(_SIBLINGS_DIR / "e2e-tests"),
        "stack_description": (
            "Playwright, standalone repo (not owned by next-app or frontend-shell, since "
            "some tests cross both). tests/marketing = next-app only (baseURL=MARKETING_URL), "
            "tests/app = frontend-shell + real backend/DB (baseURL=APP_URL, "
            "tests/app/global-setup.ts seeds a fixture user directly in Postgres via "
            "E2E_DATABASE_URL - must match backend's actual DATABASE_URL, currently Supabase "
            "not local Postgres), tests/flows = cross-domain journeys using full URLs, no "
            "baseURL. CI (.github/workflows/e2e.yml) currently runs marketing+flows only "
            "(tests/app needs a live backend+DB in CI, not wired up yet) against staging, "
            "triggered by workflow_dispatch / repository_dispatch (type staging-deployed, "
            "see README 'Wiring into other repos' CI') / nightly cron. No other repo currently "
            "sends that dispatch event yet."
        ),
        "review_focus": (
            "tests asserting on implementation details instead of user-visible behavior, "
            "flaky waits (arbitrary timeouts instead of Playwright auto-waiting/expect "
            "polling), hardcoded credentials instead of E2E_TEST_EMAIL/E2E_TEST_PASSWORD env "
            "vars, tests/app changes that assume a local Postgres instead of the real "
            "Supabase-backed E2E_DATABASE_URL, missing global-teardown cleanup for anything "
            "seeded in global-setup"
        ),
    },
}

def detect_repo_from_cwd() -> str | None:
    """Returns the REPOS key whose path contains the current working
    directory (walking up parents, so it also works from a subdirectory like
    frontend-shell/src), or None if cwd isn't inside any known repo.

    Lets main.py be invoked directly from inside a repo's own directory
    (e.g. via the `orc` shell function - see README) without passing --repo
    explicitly."""
    cwd = Path.cwd().resolve()
    for name, cfg in REPOS.items():
        repo_path = Path(cfg["path"]).resolve()
        if cwd == repo_path or repo_path in cwd.parents:
            return name
    return None


def initial_state_for(repo_name: str, task_text: str, existing_branch: str = "", existing_pr_url: str = "") -> dict:
    cfg = REPOS[repo_name]
    return {
        "task": task_text,
        "repo": repo_name,
        # One id per invocation of this function, i.e. one per compiled.ainvoke()
        # call - a single lead.py run produces several distinct run_ids (one
        # per subtask), each of which can still fan out into multiple
        # telemetry rows internally (classify + writer + review, plus any
        # review-retry rows) - see telemetry.py.
        "run_id": str(uuid.uuid4()),
        "repo_path": cfg["path"],
        "stack_description": cfg["stack_description"],
        "review_focus": cfg["review_focus"],
        "writer_model": "",
        "branch": "", "pr_url": "", "review_verdict": "", "review_notes": "",
        "existing_branch": existing_branch,
        "existing_pr_url": existing_pr_url,
    }