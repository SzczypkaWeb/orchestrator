# Structured-output contracts for every LLM call. Each one is moving from a
# hand-written JSON schema dict to a Pydantic model: the model is the single
# source of truth for the type (pyright), the runtime validation of what the
# LLM actually returned, and the JSON schema handed to the provider.
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Classification(BaseModel):
    # Groq's strict (OpenAI-compatible) structured output mode requires
    # additionalProperties:false on every object in the schema, including
    # the root - without it, Groq rejects the request outright. extra="forbid"
    # is what makes Pydantic emit it (see test_schemas.py).
    model_config = ConfigDict(extra="forbid")

    complexity: Literal["simple_crud", "novel"]


CLASSIFY_SCHEMA = Classification.model_json_schema()


WRITER_SCHEMA = {
    "type": "object",
    "properties": {
        "branch": {"type": "string", "description": "Name of the git branch that was pushed"},
        "pr_url": {"type": "string", "description": "URL of the opened pull request"},
    },
    "required": ["branch", "pr_url"],
}


class Review(BaseModel):
    # No extra="forbid" here, unlike Classification: this schema only goes to
    # Gemini and the Claude Agent SDK (never Groq), and the hand-written dict
    # it replaces never had additionalProperties:false either - keeping the
    # schema the providers see unchanged apart from Pydantic's "title" keys.
    verdict: Literal["approved", "changes_requested"]
    notes: str = Field(description="Explanation for the verdict")


REVIEW_SCHEMA = Review.model_json_schema()
