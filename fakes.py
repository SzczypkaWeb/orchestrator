"""Test doubles shared by the test suite - never imported by production code.

Lives next to the source only because this project has a flat layout; it moves
into tests/ together with the test files once the code becomes a package.
"""

from collections.abc import AsyncIterator, Callable
from typing import Any

from claude_agent_sdk import ResultMessage

# Signature of providers.complete_with_groq / complete_with_gemini.
Provider = Callable[[str, dict[str, Any]], tuple[dict[str, Any], dict[str, Any]]]


def provider_returning(result: dict[str, Any]) -> Provider:
    """A Groq/Gemini stand-in that answers every prompt with `result`."""

    def complete(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        return result, {}

    return complete


def failing_provider(prompt: str, schema: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """A Groq/Gemini stand-in that is always down."""
    raise RuntimeError("provider down")


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
