from collections.abc import AsyncIterator, Callable
from typing import Any
from unittest.mock import AsyncMock

import pytest
from claude_agent_sdk import ResultMessage

import nodes
from repos import REPOS, initial_state_for
from state import GraphState

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-5"

Provider = Callable[[str, dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]


@pytest.fixture
def state() -> GraphState:
    return initial_state_for(next(iter(REPOS)), "add a field")


@pytest.fixture(autouse=True)
def no_side_effects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(nodes, "record_metric", AsyncMock())
    monkeypatch.setattr(nodes, "broadcast", AsyncMock())


def provider_returning(result: dict[str, Any]) -> Provider:
    def complete(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return result, {}

    return complete


def failing_provider(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    raise RuntimeError("provider down")


def claude_returning(structured_output: Any) -> Callable[..., AsyncIterator[ResultMessage]]:
    async def fake_query(**kwargs: Any) -> AsyncIterator[ResultMessage]:
        yield ResultMessage(
            subtype="success",
            duration_ms=1,
            duration_api_ms=1,
            is_error=False,
            num_turns=1,
            session_id="test",
            structured_output=structured_output,
        )

    return fake_query


async def test_invalid_groq_answer_falls_back_to_gemini(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_groq", provider_returning({"complexity": "hard"}))
    monkeypatch.setattr(nodes, "complete_with_gemini", provider_returning({"complexity": "simple_crud"}))

    result = await nodes.classify_task(state)

    assert result["writer_model"] == HAIKU


async def test_claude_fallback_reads_structured_output(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_groq", failing_provider)
    monkeypatch.setattr(nodes, "complete_with_gemini", failing_provider)
    monkeypatch.setattr(nodes, "query", claude_returning({"complexity": "simple_crud"}))

    result = await nodes.classify_task(state)

    assert result["writer_model"] == HAIKU


async def test_invalid_claude_answer_defaults_to_stronger_model(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_groq", failing_provider)
    monkeypatch.setattr(nodes, "complete_with_gemini", failing_provider)
    monkeypatch.setattr(nodes, "query", claude_returning({"complexity": "hard"}))

    result = await nodes.classify_task(state)

    assert result["writer_model"] == SONNET
