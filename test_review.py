import subprocess
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock

import pytest
from claude_agent_sdk import ResultMessage

import nodes
import retry
from repos import REPOS, initial_state_for
from state import GraphState


@pytest.fixture
def state() -> GraphState:
    return {**initial_state_for(next(iter(REPOS)), "add a field"), "branch": "feat/x"}


@pytest.fixture(autouse=True)
def no_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nodes, "record_metric", AsyncMock())
    monkeypatch.setattr(nodes, "broadcast", AsyncMock())
    # with_retry would otherwise really wait 2s and 4s between Claude attempts.
    monkeypatch.setattr(retry.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(
        subprocess, "run", lambda args, **kwargs: subprocess.CompletedProcess(args, 0, stdout="+ a changed line\n", stderr="")
    )


def gemini_returning(result: dict[str, Any]):
    def complete(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return result, {}

    return complete


def gemini_failing(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raise RuntimeError("gemini down")


class FakeClaude:
    """Stands in for claude_agent_sdk.query: yields one successful result
    message with the given structured output and counts how often it ran."""

    def __init__(self, structured_output: Any) -> None:
        self.structured_output = structured_output
        self.calls = 0

    async def __call__(self, **kwargs: Any) -> AsyncIterator[ResultMessage]:
        self.calls += 1
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="test",
            structured_output=self.structured_output,
        )


async def test_valid_gemini_review_is_used(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    claude = FakeClaude({"verdict": "approved", "notes": "unused"})
    monkeypatch.setattr(nodes, "complete_with_gemini", gemini_returning({"verdict": "approved", "notes": "clean diff"}))
    monkeypatch.setattr(nodes, "query", claude)

    result = await nodes.run_security_review(state)

    assert result["review_verdict"] == "approved"
    assert result["review_notes"] == "clean diff"
    assert claude.calls == 0


async def test_invalid_gemini_review_falls_back_to_claude(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_gemini", gemini_returning({"verdict": "lgtm", "notes": "ship it"}))
    monkeypatch.setattr(nodes, "query", FakeClaude({"verdict": "changes_requested", "notes": "missing tests"}))

    result = await nodes.run_security_review(state)

    assert result["review_verdict"] == "changes_requested"
    assert result["review_notes"] == "missing tests"
    assert result["review_attempts"] == 1


async def test_invalid_claude_review_is_retried_then_fails(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    claude = FakeClaude({"verdict": "lgtm"})
    monkeypatch.setattr(nodes, "complete_with_gemini", gemini_failing)
    monkeypatch.setattr(nodes, "query", claude)

    with pytest.raises(RuntimeError, match="Failed after 3 attempts"):
        await nodes.run_security_review(state)

    assert claude.calls == 3
