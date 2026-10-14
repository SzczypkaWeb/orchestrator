import pytest

from nodes import route_after_review, route_after_verify
from repos import REPOS, initial_state_for
from state import GraphState


@pytest.fixture
def state() -> GraphState:
    return initial_state_for(next(iter(REPOS)), "some task")


@pytest.mark.parametrize(
    ("verify_passed", "verify_attempts", "expected"),
    [
        (True, 0, "proceed"),
        (True, 2, "proceed"),
        (False, 0, "retry"),
        (False, 1, "retry"),
        (False, 2, "blocked"),
    ],
)
def test_route_after_verify(
    state: GraphState, verify_passed: bool, verify_attempts: int, expected: str
):
    result = route_after_verify(
        {**state, "verify_passed": verify_passed, "verify_attempts": verify_attempts}
    )

    assert result == expected


@pytest.mark.parametrize(
    ("review_verdict", "review_attempts", "expected"),
    [
        ("approved", 0, "done"),
        ("approved", 2, "done"),
        ("changes_requested", 0, "retry"),
        ("changes_requested", 1, "retry"),
        ("changes_requested", 2, "blocked"),
    ],
)
def test_route_after_review(
    state: GraphState, review_verdict: str, review_attempts: int, expected: str
):
    result = route_after_review(
        {**state, "review_verdict": review_verdict, "review_attempts": review_attempts}
    )

    assert result == expected
