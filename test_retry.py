import pytest

from retry import TransientError, with_retry


async def test_returns_value_on_first_try():
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    result = await with_retry(fn, base_delay=0)

    assert result == "ok"
    assert calls == 1


async def test_retries_transient_errors_then_succeeds():
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        if calls > 2:
            return "ok"

        raise TransientError(f"Transient error (attempt {calls})")

    result = await with_retry(fn, max_attempts=3, base_delay=0)

    assert result == "ok"
    assert calls == 3


async def test_retries_transient_errors_then_max_attempt_error():
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1

        raise TransientError("still failing")

    with pytest.raises(RuntimeError, match="Failed after 3 attempts"):
        await with_retry(fn, base_delay=0, max_attempts=3)

    assert calls == 3


async def test_other_exceptions_are_not_retried():
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        raise ValueError("permanent failure")

    with pytest.raises(ValueError, match="permanent failure"):
        await with_retry(fn, base_delay=0, max_attempts=3)

    assert calls == 1


async def test_rejects_max_attempts_below_one():
    calls = 0

    async def fn() -> str:
        nonlocal calls
        calls += 1
        return "ok"

    with pytest.raises(ValueError, match="max_attempts must be at least 1"):
        await with_retry(fn, base_delay=0, max_attempts=0)

    assert calls == 0
