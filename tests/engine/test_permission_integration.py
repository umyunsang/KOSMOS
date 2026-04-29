# SPDX-License-Identifier: Apache-2.0
"""Integration tests: dispatch_tool_calls and QueryContext.

Tests:
1. test_dispatch_without_pipeline: executor is called directly (no pipeline)
2. test_query_context_accepts_session_context: QueryContext accepts session_context field
3. test_query_context_defaults_none: QueryContext without session_context defaults to None

Epic δ #2295: PermissionPipeline removed; tests 2+3 from previous version deleted.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.models import QueryContext, QueryState
from kosmos.engine.query import dispatch_tool_calls
from kosmos.llm.client import LLMClient  # noqa: F401 — needed by model_rebuild
from kosmos.llm.models import FunctionCall, ToolCall
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

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
        ministry="OTHER",
        category=["test"],
        endpoint="https://test.example.com/api",
        auth_type="public",
        input_schema=_In,
        output_schema=_Out,
        search_hint="echo test tool",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
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


# ---------------------------------------------------------------------------
# Test 1: dispatch without pipeline — executor is called directly
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_without_pipeline() -> None:
    """dispatch_tool_calls must use the executor directly."""
    registry = _make_registry()
    executor = _make_executor(registry)
    tool_calls = [_make_tool_call()]

    results = await dispatch_tool_calls(
        tool_calls,
        registry,
        executor,
        # no session_context
    )

    assert len(results) == 1
    result = results[0]
    assert result.success is True
    assert result.tool_id == "echo_tool"
    assert result.data == {"result": "ok"}


# ---------------------------------------------------------------------------
# Test 2: QueryContext accepts session_context field
# ---------------------------------------------------------------------------


def test_query_context_accepts_session_context() -> None:
    """QueryContext can be constructed with a non-None session_context."""
    mock_session_ctx = MagicMock()

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
        session_context=mock_session_ctx,
    )

    assert ctx.session_context is mock_session_ctx


# ---------------------------------------------------------------------------
# Test 3: QueryContext defaults session_context to None when not provided
# ---------------------------------------------------------------------------


def test_query_context_defaults_none() -> None:
    """QueryContext without session_context defaults to None."""
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

    assert ctx.session_context is None
