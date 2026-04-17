# SPDX-License-Identifier: Apache-2.0
"""Integration tests: RecoveryExecutor wired into ToolExecutor."""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel

from kosmos.recovery.executor import RecoveryExecutor
from kosmos.recovery.retry import ToolRetryPolicy
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry


class _In(BaseModel):
    query: str


class _Out(BaseModel):
    result: str


@pytest.fixture()
def tool() -> GovAPITool:
    return GovAPITool(
        id="integ_tool",
        name_ko="통합 테스트 도구",
        provider="기관",
        category=["test"],
        endpoint="https://api.example.com/",
        auth_type="api_key",
        input_schema=_In,
        output_schema=_Out,
        search_hint="integration test 통합테스트",
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
def recovery() -> RecoveryExecutor:
    return RecoveryExecutor(
        retry_policy=ToolRetryPolicy(
            max_retries=1,
            base_delay=0.0,
            multiplier=1.0,
            max_delay=0.0,
        ),
    )


@pytest.fixture()
def registry_with_tool(tool: GovAPITool) -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(tool)
    return registry


# ---------------------------------------------------------------------------
# Backward compatibility: no RecoveryExecutor
# ---------------------------------------------------------------------------


async def test_tool_executor_without_recovery(
    tool: GovAPITool,
    registry_with_tool: ToolRegistry,
) -> None:
    """ToolExecutor works normally without a RecoveryExecutor."""
    executor = ToolExecutor(registry=registry_with_tool)

    async def adapter(args: _In) -> dict[str, object]:
        return {"result": "direct"}

    executor.register_adapter("integ_tool", adapter)
    result = await executor.dispatch("integ_tool", '{"query": "hello"}')
    assert result.success is True
    assert result.data == {"result": "direct"}


# ---------------------------------------------------------------------------
# With RecoveryExecutor: success path
# ---------------------------------------------------------------------------


async def test_tool_executor_with_recovery_success(
    tool: GovAPITool,
    registry_with_tool: ToolRegistry,
    recovery: RecoveryExecutor,
) -> None:
    """ToolExecutor with RecoveryExecutor succeeds on clean adapter."""
    executor = ToolExecutor(registry=registry_with_tool, recovery_executor=recovery)

    async def adapter(args: _In) -> dict[str, object]:
        return {"result": "via_recovery"}

    executor.register_adapter("integ_tool", adapter)
    result = await executor.dispatch("integ_tool", '{"query": "hello"}')
    assert result.success is True
    assert result.data == {"result": "via_recovery"}


# ---------------------------------------------------------------------------
# With RecoveryExecutor: retried failure
# ---------------------------------------------------------------------------


async def test_tool_executor_with_recovery_retries(
    tool: GovAPITool,
    registry_with_tool: ToolRegistry,
    recovery: RecoveryExecutor,
) -> None:
    """ToolExecutor delegates retries to RecoveryExecutor."""
    call_count = 0
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(503, request=request)
    exc = httpx.HTTPStatusError("503", request=request, response=response)

    async def flaky_adapter(args: _In) -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise exc
        return {"result": "recovered"}

    executor = ToolExecutor(registry=registry_with_tool, recovery_executor=recovery)
    executor.register_adapter("integ_tool", flaky_adapter)
    result = await executor.dispatch("integ_tool", '{"query": "test"}')
    assert result.success is True
    assert call_count == 2  # one retry


# ---------------------------------------------------------------------------
# With RecoveryExecutor: non-retryable failure passes through
# ---------------------------------------------------------------------------


async def test_tool_executor_with_recovery_non_retryable(
    tool: GovAPITool,
    registry_with_tool: ToolRegistry,
    recovery: RecoveryExecutor,
) -> None:
    """Non-retryable errors result in ToolResult(success=False)."""
    request = httpx.Request("GET", "https://api.example.com/")
    response = httpx.Response(401, request=request)
    exc = httpx.HTTPStatusError("401", request=request, response=response)

    async def auth_fail_adapter(args: _In) -> dict[str, object]:
        raise exc

    executor = ToolExecutor(registry=registry_with_tool, recovery_executor=recovery)
    executor.register_adapter("integ_tool", auth_fail_adapter)
    result = await executor.dispatch("integ_tool", '{"query": "test"}')
    assert result.success is False
    assert result.error_type in ("auth_expired", "execution", "api_error")
