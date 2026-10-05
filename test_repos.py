from pathlib import Path

import pytest

import repos
from repos import ConfigError, load_repos

ROOT = Path(__file__).parent


def write(tmp_path, text):
    f = tmp_path / "cfg.yaml"
    f.write_text(text, encoding="utf-8")
    return f


def test_example_config_loads():
    loaded = load_repos(ROOT / "orchestrator.example.yaml")
    assert set(loaded) == {"my-api", "my-web"}
    assert loaded["my-api"]["target_branch"] == "main"
    # list form is joined into one string
    assert loaded["my-web"]["stack_description"] == "React + TypeScript + Vite. Run tests with `pnpm test`."


def test_author_example_loads():
    loaded = load_repos(ROOT / "examples" / "szczypka-web.yaml")
    assert list(loaded) == ["backend", "frontend-shell", "react-app", "shared-ui", "next-app", "e2e-tests"]
    assert loaded["backend"]["target_branch"] == "staging"
    assert loaded["next-app"]["target_branch"] == "main"


def test_relative_paths_resolve_against_config_dir_not_cwd(tmp_path, monkeypatch):
    f = write(tmp_path, "repos:\n  a:\n    path: ../sibling\n    stack_description: s\n    review_focus: r\n")
    monkeypatch.chdir("/")
    assert load_repos(f)["a"]["path"] == str((tmp_path.parent / "sibling").resolve())


def test_missing_file_has_helpful_message(tmp_path):
    with pytest.raises(ConfigError, match="orchestrator.example.yaml"):
        load_repos(tmp_path / "nope.yaml")


@pytest.mark.parametrize(
    "body, match",
    [
        ("", "top-level `repos:`"),
        ("repos: []\n", "top-level `repos:`"),
        ("repos:\n  a: 1\n", "must be a mapping"),
        ("repos:\n  a:\n    path: x\n    review_focus: r\n", "missing required key.*stack_description"),
        ("repos:\n  a:\n    path: x\n    stack_description: s\n    review_focus: r\n    typo: 1\n", "unknown key.*typo"),
        ("repos:\n  a:\n    path: x\n    stack_description: ''\n    review_focus: r\n", "stack_description"),
        ("repos:\n  a:\n    path: x\n    stack_description: s\n    review_focus: r\n    target_branch: ''\n", "target_branch"),
        ("repos: [unclosed\n", "invalid YAML"),
    ],
)
def test_invalid_configs_are_rejected(tmp_path, body, match):
    with pytest.raises(ConfigError, match=match):
        load_repos(write(tmp_path, body))


def test_unsafe_yaml_tags_are_not_executed(tmp_path):
    body = "repos: !!python/object/apply:os.system ['echo pwned']\n"
    with pytest.raises(ConfigError):
        load_repos(write(tmp_path, body))


def test_detect_repo_from_cwd(tmp_path, monkeypatch):
    repo_dir = tmp_path / "proj"
    (repo_dir / "src").mkdir(parents=True)
    monkeypatch.setitem(repos.REPOS, "proj", {**repos.REPOS["my-api"], "path": str(repo_dir)})
    monkeypatch.chdir(repo_dir / "src")
    assert repos.detect_repo_from_cwd() == "proj"
    monkeypatch.chdir(tmp_path)
    assert repos.detect_repo_from_cwd() is None


def test_initial_state_uses_config_values():
    state = repos.initial_state_for("my-api", "do x")
    assert state["repo"] == "my-api" and state["target_branch"] == "main"
    assert state["repo_path"] == repos.REPOS["my-api"]["path"]
