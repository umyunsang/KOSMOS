# SPDX-License-Identifier: Apache-2.0
"""Tests for RecoveryExecutor."""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel

from kosmos.recovery.circuit_breaker import CircuitBreakerConfig, CircuitState
from kosmos.recovery.executor import RecoveryExecutor
from kosmos.recovery.retry import ToolRetryPolicy
from kosmos.tools.models import GovAPITool


class _DummyInput(BaseModel):
    query: str


class _DummyOutput(BaseModel):
    result: str


@pytest.fixture()
def cacheable_tool() -> GovAPITool:
    return GovAPITool(
        id="cache_tool",
        name_ko="캐시 도구",
        provider="기관",
        category=["test"],
        endpoint="https://api.example.com/",
        auth_type="api_key",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="cache test",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_concurrency_safe=False,
        is_personal_data=False,
        cache_ttl_seconds=60,
        rate_limit_per_minute=100,
    )


@pytest.fixture()
def no_cache_tool() -> GovAPITool:
    return GovAPITool(
        id="no_cache_tool",
        name_ko="캐시없음 도구",
        provider="기관",
        category=["test"],
        endpoint="https://api.example.com/",
        auth_type="api_key",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="no cache test",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_concurrency_safe=False,
        is_personal_data=False,
        cache_ttl_seconds=0,
        rate_limit_per_minute=100,
    )


@pytest.fixture()
def fast_executor() -> RecoveryExecutor:
    """RecoveryExecutor with zero delays and tight circuit config for testing."""
    return RecoveryExecutor(
        retry_policy=ToolRetryPolicy(
            max_retries=2,
            base_delay=0.0,
            multiplier=1.0,
            max_delay=0.0,
        ),
        circuit_config=CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout=60.0,  # won't auto-recover in tests
            half_open_max_calls=1,
        ),
    )


# ---------------------------------------------------------------------------
# Success path
# ---------------------------------------------------------------------------


async def test_success_returns_tool_result(
    fast_executor: RecoveryExecutor,
    no_cache_tool: GovAPITool,
) -> None:
    async def adapter(args: object) -> dict[str, object]:
        return {"result": "ok"}

    result = await fast_executor.execute(no_cache_tool, adapter, _DummyInput(query="hi"))
    assert result.tool_result.success is True
    assert result.tool_result.data == {"result": "ok"}
    assert result.error_context is None


# ---------------------------------------------------------------------------
# Cache hit
# ---------------------------------------------------------------------------


async def test_cache_hit_on_second_call(
    fast_executor: RecoveryExecutor,
    cacheable_tool: GovAPITool,
) -> None:
    call_count = 0

    async def adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"result": "cached"}

    inp = _DummyInput(query="hello")
    await fast_executor.execute(cacheable_tool, adapter, inp)
    result2 = await fast_executor.execute(cacheable_tool, adapter, inp)

    assert call_count == 1  # second call used cache
    assert result2.tool_result.success is True
    assert result2.tool_result.data == {"result": "cached"}
    assert result2.error_context is None


# ---------------------------------------------------------------------------
# No cache when ttl=0
# ---------------------------------------------------------------------------


async def test_no_cache_when_ttl_zero(
    fast_executor: RecoveryExecutor,
    no_cache_tool: GovAPITool,
) -> None:
    call_count = 0

    async def adapter(args: object) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"result": "fresh"}

    inp = _DummyInput(query="hello")
    await fast_executor.execute(no_cache_tool, adapter, inp)
    await fast_executor.execute(no_cache_tool, adapter, inp)
    assert call_count == 2


# ---------------------------------------------------------------------------
# Circuit breaker blocks after threshold
# ---------------------------------------------------------------------------


async def test_circuit_open_blocks_after_threshold(
    fast_executor: RecoveryExecutor,
    no_cache_tool: GovAPITool,
) -> None:
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("503", request=request, response=response)

    async def always_fail(args: object) -> dict[str, object]:
        raise exc

    inp = _DummyInput(query="test")
    # 3 failures needed to open circuit (threshold=3, max_retries=2 so each call = 3 attempts)
    for _ in range(3):
        await fast_executor.execute(no_cache_tool, always_fail, inp)

    # Now circuit should be OPEN
    breaker = fast_executor._registry.get(no_cache_tool.id)  # noqa: SLF001
    assert breaker.state == CircuitState.OPEN

    # Next call should return circuit_open error
    result = await fast_executor.execute(no_cache_tool, always_fail, inp)
    assert result.tool_result.success is False
    assert result.tool_result.error_type == "circuit_open"
    assert result.error_context is not None
    assert result.error_context.circuit_state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Degradation message on exhaustion
# ---------------------------------------------------------------------------


async def test_degradation_message_on_exhaustion(
    fast_executor: RecoveryExecutor,
    no_cache_tool: GovAPITool,
) -> None:
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("503", request=request, response=response)

    async def always_fail(args: object) -> dict[str, object]:
        raise exc

    result = await fast_executor.execute(no_cache_tool, always_fail, _DummyInput(query="test"))
    assert result.tool_result.success is False
    assert result.tool_result.error is not None
    assert no_cache_tool.name_ko in result.tool_result.error
    assert result.error_context is not None
    assert result.error_context.attempt_count > 0


# ---------------------------------------------------------------------------
# Error context populated on failure
# ---------------------------------------------------------------------------


async def test_error_context_populated(
    fast_executor: RecoveryExecutor,
    no_cache_tool: GovAPITool,
) -> None:
    async def always_fail(args: object) -> dict[str, object]:
        raise httpx.ReadTimeout("timeout")

    result = await fast_executor.execute(no_cache_tool, always_fail, _DummyInput(query="x"))
    assert result.error_context is not None
    ctx = result.error_context
    assert ctx.tool_id == no_cache_tool.id
    assert ctx.attempt_count > 0
    assert ctx.elapsed_seconds >= 0.0
    assert ctx.is_cached_fallback is False


# ---------------------------------------------------------------------------
# Never raises
# ---------------------------------------------------------------------------


async def test_executor_never_raises(
    fast_executor: RecoveryExecutor,
    no_cache_tool: GovAPITool,
) -> None:
    async def raise_runtime(args: object) -> dict[str, object]:
        raise RuntimeError("unexpected crash")

    # Should not raise
    result = await fast_executor.execute(no_cache_tool, raise_runtime, _DummyInput(query="boom"))
    assert result.tool_result.success is False
