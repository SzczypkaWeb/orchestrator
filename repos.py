"""Registry of the repos the orchestrator may operate on, loaded from YAML.

The registry is *data*, not code: see ``orchestrator.example.yaml`` for the
format. The config file is located via the ``ORCHESTRATOR_CONFIG`` environment
variable, falling back to ``orchestrator.yaml`` next to this file. It is read
with ``yaml.safe_load`` (plain data only, no object construction).
"""

import os
import uuid
from pathlib import Path

import yaml

_HERE = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = _HERE / "orchestrator.yaml"

_REQUIRED_KEYS = ("path", "stack_description", "review_focus")
_ALLOWED_KEYS = {*_REQUIRED_KEYS, "target_branch"}
_DEFAULT_TARGET_BRANCH = "main"


class ConfigError(Exception):
    """The repo registry config is missing or invalid."""


def config_path() -> Path:
    env = os.environ.get("ORCHESTRATOR_CONFIG")
    return Path(env).expanduser().resolve() if env else DEFAULT_CONFIG_PATH


def _text(name: str, key: str, value: object) -> str:
    # A YAML list is joined with spaces so long descriptions can be written as
    # several short lines/items.
    if isinstance(value, list):
        if not all(isinstance(v, str) for v in value):
            raise ConfigError(f"repos.{name}.{key}: list items must all be strings")
        value = " ".join(v.strip() for v in value)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"repos.{name}.{key}: must be a non-empty string (or a list of strings)")
    return value.strip()


def load_repos(path: Path | None = None) -> dict[str, dict]:
    """Parse and validate the registry. Relative ``path`` values are resolved
    against the config file's directory (not the cwd), so the result does not
    depend on where the process was started."""
    cfg_file = path or config_path()
    if not cfg_file.is_file():
        raise ConfigError(
            f"Repo config not found: {cfg_file}\n"
            "Copy orchestrator.example.yaml to orchestrator.yaml and edit it, "
            "or point ORCHESTRATOR_CONFIG at your own file."
        )
    try:
        data = yaml.safe_load(cfg_file.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"{cfg_file}: invalid YAML: {exc}") from exc

    repos = data.get("repos") if isinstance(data, dict) else None
    if not isinstance(repos, dict) or not repos:
        raise ConfigError(f"{cfg_file}: expected a top-level `repos:` mapping with at least one repo")

    result: dict[str, dict] = {}
    for name, entry in repos.items():
        if not isinstance(entry, dict):
            raise ConfigError(f"repos.{name}: must be a mapping")
        missing = [k for k in _REQUIRED_KEYS if k not in entry]
        if missing:
            raise ConfigError(f"repos.{name}: missing required key(s): {', '.join(missing)}")
        unknown = sorted(set(entry) - _ALLOWED_KEYS)
        if unknown:
            raise ConfigError(f"repos.{name}: unknown key(s): {', '.join(unknown)} (allowed: {', '.join(sorted(_ALLOWED_KEYS))})")

        raw_path = entry["path"]
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ConfigError(f"repos.{name}.path: must be a non-empty string")
        repo_path = Path(raw_path).expanduser()
        if not repo_path.is_absolute():
            repo_path = cfg_file.parent / repo_path

        branch = entry.get("target_branch", _DEFAULT_TARGET_BRANCH)
        if not isinstance(branch, str) or not branch.strip():
            raise ConfigError(f"repos.{name}.target_branch: must be a non-empty string")

        result[str(name)] = {
            "path": str(repo_path.resolve()),
            "stack_description": _text(name, "stack_description", entry["stack_description"]),
            "review_focus": _text(name, "review_focus", entry["review_focus"]),
            "target_branch": branch.strip(),
        }
    return result


REPOS = load_repos()


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
        "target_branch": cfg["target_branch"],
        "writer_model": "",
        "branch": "", "pr_url": "", "review_verdict": "", "review_notes": "",
        "existing_branch": existing_branch,
        "existing_pr_url": existing_pr_url,
    }
