from unittest.mock import AsyncMock

import pytest

import lead
import retry
from fakes import FakeClaude
from repos import REPOS

KNOWN_REPO = next(iter(REPOS))


@pytest.fixture(autouse=True)
def fast_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    # with_retry would otherwise really wait 2s and 4s between attempts.
    monkeypatch.setattr(retry.asyncio, "sleep", AsyncMock())


def test_lead_schema_lists_the_configured_repos():
    assert lead.LEAD_SCHEMA["$defs"]["Subtask"]["properties"]["repo"]["enum"] == sorted(REPOS)


async def test_valid_plan_is_returned_as_subtasks(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(lead, "query", FakeClaude({"subtasks": [{"repo": KNOWN_REPO, "task": "add a field"}]}))

    subtasks = await lead.split_task("add a field everywhere")

    assert [(subtask.repo, subtask.task) for subtask in subtasks] == [(KNOWN_REPO, "add a field")]


async def test_unknown_repo_is_retried_then_fails(monkeypatch: pytest.MonkeyPatch):
    claude = FakeClaude({"subtasks": [{"repo": "not-a-repo", "task": "add a field"}]})
    monkeypatch.setattr(lead, "query", claude)

    with pytest.raises(RuntimeError, match="unknown repo"):
        await lead.split_task("add a field everywhere")

    assert claude.calls == 3


async def test_invalid_plan_is_retried_then_fails(monkeypatch: pytest.MonkeyPatch):
    claude = FakeClaude({"subtasks": [{"repo": KNOWN_REPO, "task": "a"}, {"repo": KNOWN_REPO, "task": "b"}]})
    monkeypatch.setattr(lead, "query", claude)

    with pytest.raises(RuntimeError, match="invalid plan"):
        await lead.split_task("add a field everywhere")

    assert claude.calls == 3
