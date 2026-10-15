import asyncio
import logging
from collections.abc import Awaitable, Callable

logger = logging.getLogger(__name__)

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 529}


class TransientError(Exception):
    """Raised for retryable API errors (rate limits, overload, transient server errors)."""


async def with_retry[T](fn: Callable[[], Awaitable[T]], max_attempts: int = 3, base_delay: float = 2.0) -> T:
    """Retries an async fn() on TransientError, with exponential backoff.
    Any other exception (e.g. RuntimeError for permanent failures) propagates immediately."""

    if max_attempts < 1:
        raise ValueError(f"max_attempts must be at least 1, got {max_attempts}")

    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except TransientError as e:
            if attempt == max_attempts:
                raise RuntimeError(f"Failed after {max_attempts} attempts (last error: {e})") from e
            delay = base_delay * (2 ** (attempt - 1))
            logger.warning("Transient error (attempt %d/%d): %s. Retrying in %.0fs", attempt, max_attempts, e, delay)
            await asyncio.sleep(delay)

    raise AssertionError("unreachable: the loop always returns or raises")
