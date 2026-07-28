import asyncio

TRANSIENT_STATUS_CODES = {429, 500, 502, 503, 529}


class TransientError(Exception):
    """Raised for retryable API errors (rate limits, overload, transient server errors)."""


async def with_retry(fn, max_attempts: int = 3, base_delay: float = 2.0):
    """Retries an async fn() on TransientError, with exponential backoff.
    Any other exception (e.g. RuntimeError for permanent failures) propagates immediately."""
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except TransientError as e:
            if attempt == max_attempts:
                raise RuntimeError(f"Failed after {max_attempts} attempts (last error: {e})") from e
            delay = base_delay * (2 ** (attempt - 1))
            print(f"Transient error (attempt {attempt}/{max_attempts}): {e}. Retrying in {delay:.0f}s...")
            await asyncio.sleep(delay)