# SPDX-License-Identifier: Apache-2.0
"""Unit tests for retry_with_backoff and RetryPolicy in kosmos.llm.retry."""

from __future__ import annotations

import httpx
import pytest

from kosmos.llm.errors import AuthenticationError, LLMConnectionError, LLMResponseError
from kosmos.llm.retry import RetryPolicy, retry_with_backoff

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

fast_policy = RetryPolicy(
    max_retries=3,
    base_delay=0.001,  # 1ms — fast for tests
    multiplier=1.0,
    max_delay=0.01,
)


def make_http_error(status_code: int) -> httpx.HTTPStatusError:
    """Build an httpx.HTTPStatusError with the given status code."""
    response = httpx.Response(
        status_code, request=httpx.Request("POST", "https://test.com")
    )
    return httpx.HTTPStatusError(
        f"HTTP {status_code}",
        request=response.request,
        response=response,
    )


class MockCallable:
    """Async callable that fails a fixed number of times before succeeding."""

    def __init__(
        self,
        fail_times: int,
        error: Exception,
        result: str = "success",
    ) -> None:
        self.call_count = 0
        self.fail_times = fail_times
        self.error = error
        self.result = result

    async def __call__(self) -> str:
        self.call_count += 1
        if self.call_count <= self.fail_times:
            raise self.error
        return self.result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_success_no_retry() -> None:
    """Function succeeds on first try — no retry should occur."""
    mock = MockCallable(fail_times=0, error=make_http_error(200))
    result = await retry_with_backoff(mock, fast_policy)
    assert result == "success"
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_429_retries_then_succeeds() -> None:
    """Function fails with 429 twice, then succeeds on the third attempt."""
    mock = MockCallable(fail_times=2, error=make_http_error(429))
    result = await retry_with_backoff(mock, fast_policy)
    assert result == "success"
    assert mock.call_count == 3


@pytest.mark.asyncio
async def test_503_retries_then_succeeds() -> None:
    """Function fails with 503 once, then succeeds on the second attempt."""
    mock = MockCallable(fail_times=1, error=make_http_error(503))
    result = await retry_with_backoff(mock, fast_policy)
    assert result == "success"
    assert mock.call_count == 2


@pytest.mark.asyncio
async def test_401_immediate_failure() -> None:
    """Function fails with 401 — AuthenticationError raised immediately, no retry."""
    mock = MockCallable(fail_times=99, error=make_http_error(401))
    with pytest.raises(AuthenticationError) as exc_info:
        await retry_with_backoff(mock, fast_policy)
    assert exc_info.value.status_code == 401
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_403_immediate_failure() -> None:
    """Function fails with 403 — AuthenticationError raised immediately, no retry."""
    mock = MockCallable(fail_times=99, error=make_http_error(403))
    with pytest.raises(AuthenticationError) as exc_info:
        await retry_with_backoff(mock, fast_policy)
    assert exc_info.value.status_code == 403
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_400_immediate_failure() -> None:
    """Function fails with 400 — LLMResponseError raised immediately, no retry."""
    mock = MockCallable(fail_times=99, error=make_http_error(400))
    with pytest.raises(LLMResponseError) as exc_info:
        await retry_with_backoff(mock, fast_policy)
    assert exc_info.value.status_code == 400
    assert mock.call_count == 1


@pytest.mark.asyncio
async def test_retry_exhaustion() -> None:
    """Function always fails with 429 — LLMConnectionError after max_retries exhausted."""
    mock = MockCallable(fail_times=99, error=make_http_error(429))
    with pytest.raises(LLMConnectionError):
        await retry_with_backoff(mock, fast_policy)
    # 1 initial attempt + 3 retries = 4 total calls
    assert mock.call_count == fast_policy.max_retries + 1


@pytest.mark.asyncio
async def test_connection_error_retries() -> None:
    """Function raises httpx.ConnectError, retries, then succeeds."""
    connect_error = httpx.ConnectError(
        "Connection refused",
        request=httpx.Request("POST", "https://test.com"),
    )
    mock = MockCallable(fail_times=2, error=connect_error)
    result = await retry_with_backoff(mock, fast_policy)
    assert result == "success"
    assert mock.call_count == 3
