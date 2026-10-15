import asyncio
import io
import logging
from collections.abc import Iterator
from typing import Any

import pytest

import lead
from logging_setup import configure_logging, current_run_id
from retry import TransientError, with_retry
from state import GraphState


@pytest.fixture
def log_output() -> Iterator[io.StringIO]:
    """Routes logging into a buffer with the real format, then puts the root
    logger back the way pytest had it, so later tests are not affected."""
    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    buffer = io.StringIO()
    configure_logging(stream=buffer)
    yield buffer
    root.handlers, root.level = saved_handlers, saved_level


def test_lines_carry_a_placeholder_outside_a_run(log_output: io.StringIO):
    logging.getLogger("orchestrator.test").info("hello")

    assert "[-] orchestrator.test: hello" in log_output.getvalue()


async def test_invoke_run_tags_lines_with_the_run_id_and_resets_it(
    monkeypatch: pytest.MonkeyPatch, log_output: io.StringIO, state: GraphState
):
    async def fake_ainvoke(graph_state: GraphState) -> GraphState:
        logging.getLogger("nodes").info("inside the graph")
        return graph_state

    monkeypatch.setattr(lead.compiled, "ainvoke", fake_ainvoke)

    await lead.invoke_run(state)

    assert f"[{state['run_id']}] nodes: inside the graph" in log_output.getvalue()
    assert current_run_id.get() == "-"


async def test_parallel_runs_never_see_each_others_id(
    monkeypatch: pytest.MonkeyPatch, log_output: io.StringIO, state: GraphState
):
    async def fake_ainvoke(graph_state: GraphState) -> GraphState:
        # Yield to the other run between the two lines, so they interleave.
        logging.getLogger("nodes").info("start %s", graph_state["run_id"])
        await asyncio.sleep(0)
        logging.getLogger("nodes").info("end %s", graph_state["run_id"])
        return graph_state

    monkeypatch.setattr(lead.compiled, "ainvoke", fake_ainvoke)
    first: GraphState = {**state, "run_id": "run-1"}
    second: GraphState = {**state, "run_id": "run-2"}

    await asyncio.gather(lead.invoke_run(first), lead.invoke_run(second))

    node_lines = [line for line in log_output.getvalue().splitlines() if "] nodes: " in line]
    assert len(node_lines) == 4
    for line in node_lines:
        run_id_in_brackets = line.split("[")[1].split("]")[0]
        assert line.endswith(run_id_in_brackets), line


async def test_a_failed_run_is_logged_with_its_traceback_and_run_id(
    monkeypatch: pytest.MonkeyPatch, log_output: io.StringIO, state: GraphState
):
    async def failing_ainvoke(graph_state: GraphState) -> Any:
        raise RuntimeError("writer blew up")

    monkeypatch.setattr(lead.compiled, "ainvoke", failing_ainvoke)

    with pytest.raises(RuntimeError):
        await lead.invoke_run(state)

    output = log_output.getvalue()
    assert f"ERROR   [{state['run_id']}] lead: Run failed" in output
    assert "Traceback" in output
    assert "writer blew up" in output


async def test_retries_are_logged_as_warnings(monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture):
    calls = 0

    async def flaky() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TransientError("rate limited")
        return "ok"

    await with_retry(flaky, base_delay=0)

    [record] = [r for r in caplog.records if r.name == "retry"]
    assert record.levelname == "WARNING"
    assert "rate limited" in record.getMessage()


async def test_the_run_summary_is_logged_under_the_run_id(
    monkeypatch: pytest.MonkeyPatch, log_output: io.StringIO, state: GraphState
):
    async def fake_ainvoke(graph_state: GraphState) -> GraphState:
        return {**graph_state, "branch": "feat/x", "review_verdict": "approved"}

    monkeypatch.setattr(lead.compiled, "ainvoke", fake_ainvoke)

    await lead.invoke_run(state)

    assert f"[{state['run_id']}] lead: Run finished for repo" in log_output.getvalue()
