"""Logging for every entry point (the CLI in main.py and the control server).

Modules only ever do `logger = logging.getLogger(__name__)` and log; this file
decides where those records go and what they look like. Every line carries the
id of the run it belongs to, taken from `current_run_id`, so the interleaved
output of several runs in parallel (lead.py) can be told apart and matched to
the RunEvent/ExecutionMetric rows with the same id.

Named logging_setup.py, never logging.py: a module called `logging` here would
shadow the standard library for every `import logging` in the project.
"""

import logging
import os
import sys
from contextvars import ContextVar
from typing import TextIO

# A ContextVar, not a global: each asyncio task gets its own copy, so parallel
# runs never see each other's id, and the value follows the run into LangGraph
# nodes and into asyncio.to_thread worker threads.
current_run_id: ContextVar[str] = ContextVar("current_run_id", default="-")

LOG_FORMAT = "%(asctime)s %(levelname)-7s [%(run_id)s] %(name)s: %(message)s"


class RunIdFilter(logging.Filter):
    """Stamps every record with the current run id (or "-" outside a run)."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.run_id = current_run_id.get()
        return True


def configure_logging(stream: TextIO | None = None) -> None:
    """Send all log records to stderr (or `stream`) in LOG_FORMAT.

    The level comes from LOG_LEVEL (default INFO), e.g. LOG_LEVEL=DEBUG.
    Replaces any handlers already on the root logger, so calling it twice
    (uvicorn --reload re-imports the app) never duplicates every line."""
    handler = logging.StreamHandler(stream or sys.stderr)
    handler.addFilter(RunIdFilter())
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO").upper())
