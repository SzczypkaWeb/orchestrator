import subprocess

import pytest

from nodes import _target_branch_is_stale


class FakeGit:
    """Stands in for subprocess.run: records every git command and returns
    canned results instead of touching a real repo or the network."""

    def __init__(self, fetch_returncode: int = 0, log_output: str = "") -> None:
        self.fetch_returncode = fetch_returncode
        self.log_output = log_output
        self.calls: list[list[str]] = []

    def __call__(self, args: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        self.calls.append(args)
        if "fetch" in args:
            return subprocess.CompletedProcess(args, self.fetch_returncode, stdout="", stderr="fatal: could not read from remote")
        return subprocess.CompletedProcess(args, 0, stdout=self.log_output, stderr="")


def test_main_is_never_stale_and_runs_no_git(monkeypatch: pytest.MonkeyPatch):
    git = FakeGit()
    monkeypatch.setattr(subprocess, "run", git)

    assert _target_branch_is_stale("/repo", "main") is None
    assert git.calls == []


def test_failed_fetch_raises(monkeypatch: pytest.MonkeyPatch):
    git = FakeGit(fetch_returncode=128)
    monkeypatch.setattr(subprocess, "run", git)

    with pytest.raises(RuntimeError, match="git fetch failed"):
        _target_branch_is_stale("/repo", "staging")
    assert len(git.calls) == 1


def test_up_to_date_branch_is_not_stale(monkeypatch: pytest.MonkeyPatch):
    git = FakeGit(fetch_returncode=0, log_output="")
    monkeypatch.setattr(subprocess, "run", git)

    assert _target_branch_is_stale("/repo", "staging") is None
    assert len(git.calls) == 2


def test_missing_commits_produce_a_warning(monkeypatch: pytest.MonkeyPatch):
    git = FakeGit(fetch_returncode=0, log_output="hotfix: patch prod")
    monkeypatch.setattr(subprocess, "run", git)

    warning = _target_branch_is_stale("/repo", "staging")

    assert warning is not None
    assert "hotfix: patch prod" in warning
