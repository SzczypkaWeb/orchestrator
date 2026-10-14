import pytest
from pydantic import ValidationError

from schemas import CLASSIFY_SCHEMA, REVIEW_SCHEMA, WRITER_SCHEMA, Classification, Review, WriterResult


@pytest.mark.parametrize("complexity", ["simple_crud", "novel"])
def test_classification_accepts_known_values(complexity: str):
    result = Classification.model_validate({"complexity": complexity})

    assert result.complexity == complexity


@pytest.mark.parametrize(
    "data",
    [
        {"complexity": "hard"},
        {},
        {"complexity": "novel", "reason": "extra field"},
    ],
)
def test_classification_rejects_invalid_data(data: dict[str, str]):
    with pytest.raises(ValidationError):
        Classification.model_validate(data)


def test_classify_schema_forbids_extra_properties():
    assert CLASSIFY_SCHEMA["additionalProperties"] is False


@pytest.mark.parametrize("verdict", ["approved", "changes_requested"])
def test_review_accepts_known_verdicts(verdict: str):
    review = Review.model_validate({"verdict": verdict, "notes": "looks fine"})

    assert review.verdict == verdict


@pytest.mark.parametrize(
    "data",
    [
        {"verdict": "lgtm", "notes": "looks fine"},
        {"verdict": "approved"},
        {"notes": "looks fine"},
    ],
)
def test_review_rejects_invalid_data(data: dict[str, str]):
    with pytest.raises(ValidationError):
        Review.model_validate(data)


def test_review_schema_keeps_the_notes_description():
    assert REVIEW_SCHEMA["properties"]["notes"]["description"] == "Explanation for the verdict"


def test_writer_result_accepts_a_pull_request_url():
    result = WriterResult.model_validate({"branch": " feat/x ", "pr_url": "https://github.com/acme/app/pull/42"})

    assert result.branch == "feat/x"
    assert result.pr_url == "https://github.com/acme/app/pull/42"


@pytest.mark.parametrize(
    "data",
    [
        {"branch": "", "pr_url": "https://github.com/acme/app/pull/42"},
        {"branch": "feat/x", "pr_url": "PR opened successfully"},
        {"branch": "feat/x", "pr_url": "https://github.com/acme/app/compare/main...feat/x"},
        {"branch": "feat/x"},
    ],
)
def test_writer_result_rejects_invalid_data(data: dict[str, str]):
    with pytest.raises(ValidationError):
        WriterResult.model_validate(data)


def test_writer_schema_has_no_constraint_keywords():
    # Validation rules live in Python validators, not in the schema the agent sees.
    assert set(WRITER_SCHEMA["properties"]["pr_url"]) == {"type", "title", "description"}
