from unittest.mock import AsyncMock

import pytest

import nodes
from fakes import FakeClaude
from state import GraphState

pytestmark = pytest.mark.usefixtures("silence_telemetry")

PR_URL = "https://github.com/acme/app/pull/42"


@pytest.fixture
def state(state: GraphState, monkeypatch: pytest.MonkeyPatch) -> GraphState:
    # A fresh run: the stale-branch git check is covered by test_stale_check.py.
    monkeypatch.setattr(nodes, "_target_branch_is_stale", lambda repo_path, target_branch: None)
    return {**state, "writer_model": "claude-haiku-4-5"}


async def test_valid_result_is_stored_in_state(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "query", FakeClaude({"branch": "feat/x", "pr_url": PR_URL}))

    result = await nodes.run_writer(state)

    assert result["branch"] == "feat/x"
    assert result["pr_url"] == PR_URL


async def test_invalid_result_fails_without_retrying(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    claude = FakeClaude({"branch": "feat/x", "pr_url": "PR opened successfully"})
    monkeypatch.setattr(nodes, "query", claude)

    with pytest.raises(RuntimeError, match="invalid result"):
        await nodes.run_writer(state)

    # One run only: a retry would redo the whole task and open a second PR.
    assert claude.calls == 1


async def test_invalid_result_is_broadcast_as_failed_without_pr_url(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    broadcast = AsyncMock()
    monkeypatch.setattr(nodes, "broadcast", broadcast)
    monkeypatch.setattr(nodes, "query", FakeClaude({"branch": "feat/x", "pr_url": "PR opened successfully"}))

    with pytest.raises(RuntimeError):
        await nodes.run_writer(state)

    assert broadcast.await_args is not None
    event = broadcast.await_args.args[0]
    assert event["status"] == "failed"
    assert event["pr_url"] is None
