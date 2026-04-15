# SPDX-License-Identifier: Apache-2.0
"""T014 — Tests for execute_tool span produced by ToolExecutor.dispatch().

Covers:
- Success path: span has correct gen_ai attributes, UNSET status.
- Failure path (adapter raises): span has ERROR status and error.type attribute.
- PII check: tool input dict with 'user_email' key must not leak into span
  attributes.

Strategy: monkeypatch the module-level _tracer in executor.py to use a
dedicated TracerProvider backed by an InMemorySpanExporter. This avoids the
SDK singleton guard that blocks multiple trace.set_tracer_provider() calls.
"""

from __future__ import annotations

import json

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pydantic import BaseModel

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Per-test InMemorySpanExporter fixture using _tracer monkeypatching
# ---------------------------------------------------------------------------


@pytest.fixture()
def mem_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Patch _tracer in executor module with a dedicated test TracerProvider."""
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import kosmos.tools.executor as executor_mod

    monkeypatch.setattr(executor_mod, "_tracer", provider.get_tracer("kosmos.tools.executor"))

    exporter.clear()
    return exporter


# ---------------------------------------------------------------------------
# Schema models used by test tools
# ---------------------------------------------------------------------------


class _SimpleInput(BaseModel):
    query: str = "test"


class _SimpleOutput(BaseModel):
    result: str = "ok"


class _PiiInput(BaseModel):
    query: str = "test"
    user_email: str = "user@example.com"


# ---------------------------------------------------------------------------
# Registry + Executor factory helpers
# ---------------------------------------------------------------------------


def _build_registry_and_executor(
    tool_id: str,
    input_model: type[BaseModel] = _SimpleInput,
    output_model: type[BaseModel] = _SimpleOutput,
) -> tuple[ToolRegistry, ToolExecutor]:
    """Create a fresh registry with one tool and a matching executor."""
    registry = ToolRegistry()
    tool = GovAPITool(
        id=tool_id,
        name_ko="테스트 도구",
        provider="TestProvider",
        category=["test"],
        endpoint="http://example.com/api",
        auth_type="public",
        input_schema=input_model,
        output_schema=output_model,
        search_hint="test tool for unit testing",
        requires_auth=False,
        is_concurrency_safe=True,
        is_personal_data=False,
        rate_limit_per_minute=1000,
    )
    registry.register(tool)
    executor = ToolExecutor(registry=registry)
    return registry, executor


# ---------------------------------------------------------------------------
# T014-A: Success path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_success_span_attributes(
    mem_exporter: InMemorySpanExporter,
) -> None:
    """Success path: span has gen_ai attributes and UNSET status."""
    TOOL_ID = "test_success_tool"  # noqa: N806
    registry, executor = _build_registry_and_executor(TOOL_ID)

    async def _adapter(inp: _SimpleInput) -> dict:
        return {"result": "ok"}

    executor.register_adapter(TOOL_ID, _adapter)

    result = await executor.dispatch(TOOL_ID, json.dumps({"query": "hello"}), "call-abc")

    assert result.success is True, f"Expected success, got: {result}"

    spans = mem_exporter.get_finished_spans()
    tool_spans = [s for s in spans if s.name == f"execute_tool {TOOL_ID}"]
    assert len(tool_spans) == 1, (
        f"Expected 1 'execute_tool {TOOL_ID}' span, got {len(tool_spans)}. "
        f"All spans: {[s.name for s in spans]}"
    )
    span = tool_spans[0]
    attrs = dict(span.attributes or {})

    assert attrs.get("gen_ai.operation.name") == "execute_tool", (
        f"gen_ai.operation.name mismatch: {attrs}"
    )
    assert attrs.get("gen_ai.tool.name") == TOOL_ID, f"gen_ai.tool.name mismatch: {attrs}"
    assert attrs.get("gen_ai.tool.type") == "function", f"gen_ai.tool.type mismatch: {attrs}"
    # tool_call_id is set when provided
    assert attrs.get("gen_ai.tool.call.id") == "call-abc", f"gen_ai.tool.call.id mismatch: {attrs}"

    # Status must be UNSET on success (contracts § Span 3)
    assert span.status.status_code == StatusCode.UNSET, (
        f"Expected UNSET status on success, got {span.status.status_code}"
    )


# ---------------------------------------------------------------------------
# T014-B: Failure path (adapter raises exception)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_failure_span_error_status(
    mem_exporter: InMemorySpanExporter,
) -> None:
    """Failure path: adapter raises → span has ERROR status and error.type set."""
    TOOL_ID = "test_fail_tool"  # noqa: N806
    registry, executor = _build_registry_and_executor(TOOL_ID)

    async def _failing_adapter(inp: _SimpleInput) -> dict:
        raise RuntimeError("Simulated adapter failure")

    executor.register_adapter(TOOL_ID, _failing_adapter)

    result = await executor.dispatch(TOOL_ID, json.dumps({"query": "fail"}))

    assert result.success is False, "Expected failure result"
    assert result.error_type is not None, "Expected error_type to be set"

    spans = mem_exporter.get_finished_spans()
    tool_spans = [s for s in spans if s.name == f"execute_tool {TOOL_ID}"]
    assert len(tool_spans) == 1, (
        f"Expected 1 'execute_tool {TOOL_ID}' span. All spans: {[s.name for s in spans]}"
    )
    span = tool_spans[0]
    attrs = dict(span.attributes or {})

    # Status must be ERROR on failure
    assert span.status.status_code == StatusCode.ERROR, (
        f"Expected ERROR status on failure, got {span.status.status_code}"
    )

    # error.type attribute must be set (contracts § Span 3)
    assert "error.type" in attrs, f"Expected 'error.type' attribute on failure span. attrs: {attrs}"
    assert attrs["error.type"] is not None, "error.type must not be None"

    # Span events: executor catches exception internally; if any events were
    # recorded, they must have valid names.
    for ev in span.events:
        assert ev.name, "Span event name must not be empty"


# ---------------------------------------------------------------------------
# T014-B2: Failure via ToolNotFoundError (tool not in registry)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_not_found_span_error(
    mem_exporter: InMemorySpanExporter,
) -> None:
    """ToolNotFoundError path: span has ERROR status, error.type is set."""
    TOOL_ID = "nonexistent_tool"  # noqa: N806
    registry = ToolRegistry()  # empty registry
    executor = ToolExecutor(registry=registry)

    result = await executor.dispatch(TOOL_ID, json.dumps({}))

    assert result.success is False
    assert result.error_type == "not_found"

    spans = mem_exporter.get_finished_spans()
    tool_spans = [s for s in spans if s.name == f"execute_tool {TOOL_ID}"]
    assert len(tool_spans) == 1

    span = tool_spans[0]
    assert span.status.status_code == StatusCode.ERROR, (
        f"Expected ERROR for not_found. Got {span.status.status_code}"
    )
    attrs = dict(span.attributes or {})
    assert "error.type" in attrs, f"Expected error.type. attrs: {attrs}"


# ---------------------------------------------------------------------------
# T014-C: PII check — user_email must not appear in span attributes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_tool_no_pii_in_span_attributes(
    mem_exporter: InMemorySpanExporter,
) -> None:
    """Tool input with user_email must not leak into span attributes."""
    TOOL_ID = "pii_test_tool"  # noqa: N806
    registry, executor = _build_registry_and_executor(
        TOOL_ID,
        input_model=_PiiInput,
        output_model=_SimpleOutput,
    )

    async def _adapter(inp: _PiiInput) -> dict:
        return {"result": "ok"}

    executor.register_adapter(TOOL_ID, _adapter)

    # Dispatch with PII in arguments
    args = json.dumps({"query": "search", "user_email": "victim@example.com"})
    result = await executor.dispatch(TOOL_ID, args)

    assert result.success is True, f"Expected success. Got: {result}"

    spans = mem_exporter.get_finished_spans()
    tool_spans = [s for s in spans if s.name == f"execute_tool {TOOL_ID}"]
    assert len(tool_spans) == 1

    span = tool_spans[0]
    attrs = dict(span.attributes or {})

    # No attribute key or value must contain 'user_email' or the raw email address.
    for key, val in attrs.items():
        assert "user_email" not in key.lower(), f"Span attribute key leaks PII: {key!r}"
        if isinstance(val, str):
            assert "user_email" not in val.lower(), (
                f"Span attribute value leaks PII field name in key={key!r}: {val!r}"
            )
            assert "victim@example.com" not in val, (
                f"Span attribute value leaks PII email in key={key!r}: {val!r}"
            )

    # No attribute key must start with 'tool.input'
    for key in attrs:
        assert not key.lower().startswith("tool.input"), (
            f"Span attribute key looks like tool input leakage: {key!r}"
        )
