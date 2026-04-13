# SPDX-License-Identifier: Apache-2.0
"""Integration tests: PermissionPipeline wired into dispatch_tool_calls and QueryContext.

Tests:
1. test_dispatch_without_pipeline: backward-compat — no pipeline uses executor directly
2. test_dispatch_with_pipeline: pipeline present — pipeline.run() is called instead of executor
3. test_query_context_accepts_permission_fields: QueryContext accepts the new optional fields
4. test_query_context_defaults_none: QueryContext without permission fields defaults both to None

All assertions use mocks only; no live API calls, no imports from kosmos.permissions at module
level (avoids circular imports since the permissions package is TYPE_CHECKING-only in sources).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.models import QueryContext, QueryState
from kosmos.engine.query import dispatch_tool_calls
from kosmos.llm.client import LLMClient  # noqa: F401 — needed by model_rebuild
from kosmos.llm.models import FunctionCall, ToolCall
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import ToolResult
from kosmos.tools.registry import ToolRegistry


# Rebuild QueryContext so forward references to PermissionPipeline / SessionContext
# are resolved.  The permissions package does not exist yet (TYPE_CHECKING-only),
# so we supply stub sentinel classes that satisfy Pydantic's type resolution.
class PermissionPipeline:  # noqa: D101 — stub for model_rebuild only
    pass


class SessionContext:  # noqa: D101 — stub for model_rebuild only
    pass


QueryContext.model_rebuild(
    _types_namespace={
        "PermissionPipeline": PermissionPipeline,
        "SessionContext": SessionContext,
    }
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_call(name: str = "echo_tool", arguments: str = "{}") -> ToolCall:
    """Build a minimal ToolCall for testing."""
    return ToolCall(id="call_test", function=FunctionCall(name=name, arguments=arguments))


def _make_registry(
    tool_name: str = "echo_tool",
    *,
    is_concurrency_safe: bool = False,
) -> ToolRegistry:
    """Return a ToolRegistry populated with a single minimal GovAPITool."""
    from pydantic import BaseModel

    from kosmos.tools.models import GovAPITool

    class _In(BaseModel):
        query: str = ""

    class _Out(BaseModel):
        result: str = ""

    tool = GovAPITool(
        id=tool_name,
        name_ko="Echo tool",
        provider="test_provider",
        category=["test"],
        endpoint="https://test.example.com/api",
        auth_type="public",
        input_schema=_In,
        output_schema=_Out,
        search_hint="echo test tool",
        requires_auth=False,
        is_personal_data=False,
        is_concurrency_safe=is_concurrency_safe,
        cache_ttl_seconds=0,
        rate_limit_per_minute=60,
    )
    registry = ToolRegistry()
    registry.register(tool)
    return registry


def _make_executor(registry: ToolRegistry, return_data: dict | None = None) -> ToolExecutor:
    """Return a ToolExecutor with a mock adapter that returns success.

    The adapter must return data that matches the ``_Out`` output schema
    (``{"result": str}``).  The default return is ``{"result": "ok"}``.
    """
    executor = ToolExecutor(registry)

    async def _adapter(validated_input: object) -> dict:
        return return_data or {"result": "ok"}

    executor.register_adapter("echo_tool", _adapter)
    return executor


def _success_tool_result(tool_id: str = "echo_tool") -> ToolResult:
    """Convenience factory for a successful ToolResult."""
    return ToolResult(tool_id=tool_id, success=True, data={"result": "pipeline_output"})


# ---------------------------------------------------------------------------
# Test 1: dispatch without pipeline — backward compatibility
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_without_pipeline() -> None:
    """dispatch_tool_calls without a pipeline must use the executor directly."""
    registry = _make_registry()
    executor = _make_executor(registry)
    tool_calls = [_make_tool_call()]

    results = await dispatch_tool_calls(
        tool_calls,
        registry,
        executor,
        # no permission_pipeline, no session_context
    )

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.tool_id == "echo_tool"
    assert result.data == {"result": "ok"}


# ---------------------------------------------------------------------------
# Test 2: dispatch with pipeline — calls pipeline.run() not executor.dispatch()
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_with_pipeline() -> None:
    """When pipeline + session_context are provided, pipeline.run() is used instead of executor."""
    registry = _make_registry()

    # Real executor whose adapter should NOT be called
    executor_dispatch = AsyncMock(
        side_effect=AssertionError("executor.dispatch should not be called"),
    )
    executor = MagicMock(spec=ToolExecutor)
    executor.dispatch = executor_dispatch

    # Mock PermissionPipeline that returns a known ToolResult
    expected_result = _success_tool_result()
    mock_pipeline = MagicMock()
    mock_pipeline.run = AsyncMock(return_value=expected_result)

    # Mock SessionContext (opaque object — the pipeline owns its contract)
    mock_session_ctx = MagicMock()

    tool_calls = [_make_tool_call("echo_tool", '{"query": "hello"}')]

    results = await dispatch_tool_calls(
        tool_calls,
        registry,
        executor,
        permission_pipeline=mock_pipeline,
        session_context=mock_session_ctx,
    )

    # Pipeline must be called once with correct arguments
    mock_pipeline.run.assert_awaited_once_with(
        tool_id="echo_tool",
        arguments_json='{"query": "hello"}',
        session_context=mock_session_ctx,
    )

    # Executor must NOT have been called
    executor_dispatch.assert_not_awaited()

    # Result must be what the pipeline returned
    assert len(results) == 1
    assert results[0] is expected_result


# ---------------------------------------------------------------------------
# Test 3: QueryContext accepts permission_pipeline and session_context fields
# ---------------------------------------------------------------------------


def test_query_context_accepts_permission_fields() -> None:
    """QueryContext can be constructed with non-None permission_pipeline and session_context."""
    mock_pipeline = MagicMock()
    mock_session_ctx = MagicMock()

    registry = _make_registry()
    executor = _make_executor(registry)
    state = QueryState(usage=UsageTracker(budget=100_000))

    # Use model_construct to bypass isinstance checks for mock objects
    ctx = QueryContext.model_construct(
        state=state,
        llm_client=MagicMock(),
        tool_executor=executor,
        tool_registry=registry,
        config=QueryEngineConfig(),
        iteration=0,
        permission_pipeline=mock_pipeline,
        session_context=mock_session_ctx,
    )

    assert ctx.permission_pipeline is mock_pipeline
    assert ctx.session_context is mock_session_ctx


# ---------------------------------------------------------------------------
# Test 4: QueryContext defaults both fields to None when not provided
# ---------------------------------------------------------------------------


def test_query_context_defaults_none() -> None:
    """QueryContext without permission fields defaults both to None."""
    registry = _make_registry()
    executor = _make_executor(registry)
    state = QueryState(usage=UsageTracker(budget=100_000))

    ctx = QueryContext.model_construct(
        state=state,
        llm_client=MagicMock(),
        tool_executor=executor,
        tool_registry=registry,
        config=QueryEngineConfig(),
        iteration=0,
    )

    assert ctx.permission_pipeline is None
    assert ctx.session_context is None
