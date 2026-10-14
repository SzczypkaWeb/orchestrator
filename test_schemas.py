import pytest
from pydantic import ValidationError

from schemas import CLASSIFY_SCHEMA, Classification


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
