# Structured-output contracts for every LLM call. Each one is moving from a
# hand-written JSON schema dict to a Pydantic model: the model is the single
# source of truth for the type (pyright), the runtime validation of what the
# LLM actually returned, and the JSON schema handed to the provider.
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Classification(BaseModel):
    # Groq's strict (OpenAI-compatible) structured output mode requires
    # additionalProperties:false on every object in the schema, including
    # the root - without it, Groq rejects the request outright. extra="forbid"
    # is what makes Pydantic emit it (see test_schemas.py).
    model_config = ConfigDict(extra="forbid")

    complexity: Literal["simple_crud", "novel"]


CLASSIFY_SCHEMA = Classification.model_json_schema()


_PULL_REQUEST_URL = re.compile(r"https://github\.com/[^/]+/[^/]+/pull/\d+/?")


class WriterResult(BaseModel):
    branch: str = Field(description="Name of the git branch that was pushed")
    pr_url: str = Field(description="URL of the opened pull request")

    # The checks below live in Python validators rather than in schema keywords
    # (minLength/pattern) on purpose: the JSON schema handed to the agent stays
    # exactly what it was, so no provider can reject a keyword it doesn't support.
    @field_validator("branch")
    @classmethod
    def branch_is_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("branch must not be empty")
        return value.strip()

    @field_validator("pr_url")
    @classmethod
    def pr_url_points_to_a_pull_request(cls, value: str) -> str:
        if not _PULL_REQUEST_URL.fullmatch(value.strip()):
            raise ValueError(f"not a GitHub pull request URL: {value!r}")
        return value.strip()


WRITER_SCHEMA = WriterResult.model_json_schema()


class Review(BaseModel):
    # No extra="forbid" here, unlike Classification: this schema only goes to
    # Gemini and the Claude Agent SDK (never Groq), and the hand-written dict
    # it replaces never had additionalProperties:false either - keeping the
    # schema the providers see unchanged apart from Pydantic's "title" keys.
    verdict: Literal["approved", "changes_requested"]
    notes: str = Field(description="Explanation for the verdict")


REVIEW_SCHEMA = Review.model_json_schema()
