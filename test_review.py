import subprocess
from unittest.mock import AsyncMock

import pytest

import nodes
import retry
from fakes import FakeClaude, failing_provider, provider_returning
from state import GraphState

pytestmark = pytest.mark.usefixtures("silence_telemetry")


@pytest.fixture
def state(state: GraphState) -> GraphState:
    # Overrides conftest's `state` for this file, building on top of it:
    # a review always runs on a branch the writer already pushed.
    return {**state, "branch": "feat/x"}


@pytest.fixture(autouse=True)
def fast_retries_and_fake_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    # with_retry would otherwise really wait 2s and 4s between Claude attempts.
    monkeypatch.setattr(retry.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(
        subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="+ a changed line\n", stderr="")
    )


async def test_valid_gemini_review_is_used(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    claude = FakeClaude({"verdict": "approved", "notes": "unused"})
    monkeypatch.setattr(nodes, "complete_with_gemini", provider_returning({"verdict": "approved", "notes": "clean diff"}))
    monkeypatch.setattr(nodes, "query", claude)

    result = await nodes.run_security_review(state)

    assert result["review_verdict"] == "approved"
    assert result["review_notes"] == "clean diff"
    assert claude.calls == 0


async def test_invalid_gemini_review_falls_back_to_claude(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_gemini", provider_returning({"verdict": "lgtm", "notes": "ship it"}))
    monkeypatch.setattr(nodes, "query", FakeClaude({"verdict": "changes_requested", "notes": "missing tests"}))

    result = await nodes.run_security_review(state)

    assert result["review_verdict"] == "changes_requested"
    assert result["review_notes"] == "missing tests"
    assert result["review_attempts"] == 1


async def test_invalid_claude_review_is_retried_then_fails(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    claude = FakeClaude({"verdict": "lgtm"})
    monkeypatch.setattr(nodes, "complete_with_gemini", failing_provider)
    monkeypatch.setattr(nodes, "query", claude)

    with pytest.raises(RuntimeError, match="Failed after 3 attempts"):
        await nodes.run_security_review(state)

    assert claude.calls == 3
