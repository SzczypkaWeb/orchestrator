"""Point the repo registry at the committed example config for every test run,
so the suite never depends on a developer's local (gitignored) orchestrator.yaml.
This must happen before `repos` is first imported (it loads the config at import),
which is why the project imports below live inside the fixtures."""

import os
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from state import GraphState  # side-effect free, safe to import before the env var

os.environ["ORCHESTRATOR_CONFIG"] = str(Path(__file__).parent / "orchestrator.example.yaml")


@pytest.fixture
def state() -> GraphState:
    """A complete, valid GraphState for the first repo in the example config."""
    from repos import REPOS, initial_state_for

    return initial_state_for(next(iter(REPOS)), "add a field")


@pytest.fixture
def silence_telemetry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the node-level telemetry/broadcast calls with mocks, so node
    tests never touch Postgres or WebSocket clients. Opt in per file with
    `pytestmark = pytest.mark.usefixtures("silence_telemetry")`."""
    import nodes

    monkeypatch.setattr(nodes, "record_metric", AsyncMock())
    monkeypatch.setattr(nodes, "broadcast", AsyncMock())
