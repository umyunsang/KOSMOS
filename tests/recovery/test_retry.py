# SPDX-License-Identifier: Apache-2.0
"""Tests for the retry policy and retry_tool_call loop."""

from __future__ import annotations

import httpx
import pytest

from kosmos.recovery.classifier import DataGoKrErrorClassifier, ErrorClass
from kosmos.recovery.retry import ToolRetryPolicy, retry_tool_call


@pytest.fixture()
def classifier() -> DataGoKrErrorClassifier:
    return DataGoKrErrorClassifier()


@pytest.fixture()
def fast_policy() -> ToolRetryPolicy:
    """Policy with zero delays for testing."""
    return ToolRetryPolicy(
        max_retries=3,
        base_delay=0.0,
        multiplier=1.0,
        max_delay=0.0,
    )


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


async def test_success_on_first_attempt(
    classifier: DataGoKrErrorClassifier,
    fast_policy: ToolRetryPolicy,
) -> None:
    call_count = 0

    async def good_adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"data": "ok"}

    result, err, attempts = await retry_tool_call(
        good_adapter, None, classifier, fast_policy, is_foreground=True
    )
    assert result == {"data": "ok"}
    assert err is None
    assert attempts == 1
    assert call_count == 1


# ---------------------------------------------------------------------------
# Retry on 429 (rate limit)
# ---------------------------------------------------------------------------


async def test_retry_on_rate_limit_429(
    classifier: DataGoKrErrorClassifier,
    fast_policy: ToolRetryPolicy,
) -> None:
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(429, request=request)
    exc = httpx.HTTPStatusError("429", request=request, response=response)

    async def flaky_adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise exc
        return {"data": "ok"}

    result, err, attempts = await retry_tool_call(
        flaky_adapter, None, classifier, fast_policy, is_foreground=True
    )
    assert result == {"data": "ok"}
    assert err is None
    assert attempts == 3
    assert call_count == 3


# ---------------------------------------------------------------------------
# Retry on timeout
# ---------------------------------------------------------------------------


async def test_retry_on_timeout(
    classifier: DataGoKrErrorClassifier,
    fast_policy: ToolRetryPolicy,
) -> None:
    call_count = 0

    async def timeout_adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise httpx.ReadTimeout("read timed out")
        return {"data": "ok"}

    result, err, attempts = await retry_tool_call(
        timeout_adapter, None, classifier, fast_policy, is_foreground=True
    )
    assert result == {"data": "ok"}
    assert attempts == 2


# ---------------------------------------------------------------------------
# No retry on non-retryable errors
# ---------------------------------------------------------------------------


async def test_no_retry_on_400(
    classifier: DataGoKrErrorClassifier,
    fast_policy: ToolRetryPolicy,
) -> None:
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(400, request=request)
    exc = httpx.HTTPStatusError("400 Bad Request", request=request, response=response)

    async def bad_adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise exc

    result, err, attempts = await retry_tool_call(
        bad_adapter, None, classifier, fast_policy, is_foreground=True
    )
    assert result is None
    assert err is not None
    assert err.error_class == ErrorClass.INVALID_REQUEST
    assert attempts == 1
    assert call_count == 1


async def test_no_retry_on_401(
    classifier: DataGoKrErrorClassifier,
    fast_policy: ToolRetryPolicy,
) -> None:
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(401, request=request)
    exc = httpx.HTTPStatusError("401", request=request, response=response)

    async def auth_fail_adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise exc

    result, err, attempts = await retry_tool_call(
        auth_fail_adapter, None, classifier, fast_policy, is_foreground=True
    )
    assert result is None
    assert err is not None
    assert err.error_class == ErrorClass.AUTH_FAILURE
    assert attempts == 1
    assert call_count == 1  # no retries


# ---------------------------------------------------------------------------
# max_retries=0
# ---------------------------------------------------------------------------


async def test_max_retries_zero(
    classifier: DataGoKrErrorClassifier,
) -> None:
    policy = ToolRetryPolicy(max_retries=0, base_delay=0.0, multiplier=1.0, max_delay=0.0)
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("503", request=request, response=response)

    async def fail_adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise exc

    result, err, attempts = await retry_tool_call(
        fail_adapter, None, classifier, policy, is_foreground=True
    )
    assert result is None
    assert err is not None
    assert attempts == 1
    assert call_count == 1


# ---------------------------------------------------------------------------
# Foreground vs background retry cap
# ---------------------------------------------------------------------------


async def test_background_retry_cap(
    classifier: DataGoKrErrorClassifier,
) -> None:
    """Background calls should be capped at min(1, max_retries)."""
    policy = ToolRetryPolicy(max_retries=3, base_delay=0.0, multiplier=1.0, max_delay=0.0)
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(429, request=request)
    exc = httpx.HTTPStatusError("429", request=request, response=response)

    async def always_fail(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise exc

    result, err, attempts = await retry_tool_call(
        always_fail, None, classifier, policy, is_foreground=False
    )
    assert result is None
    # Background: min(1, 3) = 1, so total attempts = initial + 1 = 2
    assert call_count <= 2


async def test_foreground_uses_full_budget(
    classifier: DataGoKrErrorClassifier,
) -> None:
    """Foreground calls use the full max_retries budget."""
    policy = ToolRetryPolicy(max_retries=3, base_delay=0.0, multiplier=1.0, max_delay=0.0)
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("503", request=request, response=response)

    async def always_fail(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise exc

    result, err, attempts = await retry_tool_call(
        always_fail, None, classifier, policy, is_foreground=True
    )
    assert result is None
    assert call_count == 4  # 1 initial + 3 retries


# ---------------------------------------------------------------------------
# Returns attempt count correctly on exhaustion
# ---------------------------------------------------------------------------


async def test_attempt_count_on_exhaustion(
    classifier: DataGoKrErrorClassifier,
    fast_policy: ToolRetryPolicy,
) -> None:
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("503", request=request, response=response)

    async def always_fail(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        raise exc

    result, err, attempts = await retry_tool_call(
        always_fail, None, classifier, fast_policy, is_foreground=True
    )
    assert result is None
    assert err is not None
    assert err.error_class == ErrorClass.TRANSIENT
    assert attempts == 4  # 1 initial + 3 retries
    assert call_count == 4
