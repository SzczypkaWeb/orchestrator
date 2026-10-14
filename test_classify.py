import pytest

import nodes
from fakes import FakeClaude, failing_provider, provider_returning
from state import GraphState

pytestmark = pytest.mark.usefixtures("silence_telemetry")

HAIKU = "claude-haiku-4-5"
SONNET = "claude-sonnet-5"


async def test_invalid_groq_answer_falls_back_to_gemini(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_groq", provider_returning({"complexity": "hard"}))
    monkeypatch.setattr(nodes, "complete_with_gemini", provider_returning({"complexity": "simple_crud"}))

    result = await nodes.classify_task(state)

    assert result["writer_model"] == HAIKU


async def test_claude_fallback_reads_structured_output(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_groq", failing_provider)
    monkeypatch.setattr(nodes, "complete_with_gemini", failing_provider)
    monkeypatch.setattr(nodes, "query", FakeClaude({"complexity": "simple_crud"}))

    result = await nodes.classify_task(state)

    assert result["writer_model"] == HAIKU


async def test_invalid_claude_answer_defaults_to_stronger_model(monkeypatch: pytest.MonkeyPatch, state: GraphState):
    monkeypatch.setattr(nodes, "complete_with_groq", failing_provider)
    monkeypatch.setattr(nodes, "complete_with_gemini", failing_provider)
    monkeypatch.setattr(nodes, "query", FakeClaude({"complexity": "hard"}))

    result = await nodes.classify_task(state)

    assert result["writer_model"] == SONNET
