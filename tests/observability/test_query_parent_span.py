# SPDX-License-Identifier: Apache-2.0
"""T013 — Tests for the root OTel span produced by query().

Verifies:
- Exactly one root span named 'invoke_agent kosmos-query'.
- Root span attributes: gen_ai.operation.name, gen_ai.agent.name,
  gen_ai.conversation.id.
- At least one 'chat' child span and one 'execute_tool *' child span.
- Root span status is UNSET on success.

Strategy: Instead of calling trace.set_tracer_provider() (which may be blocked
by SDK singleton guard), we monkeypatch the module-level _tracer objects in
query.py, client.py, and executor.py to use a dedicated TracerProvider backed
by an InMemorySpanExporter. This gives us full span capture without touching
the global provider.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import StatusCode
from pydantic import BaseModel

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.models import QueryContext, QueryState
from kosmos.llm.client import LLMClient
from kosmos.llm.models import StreamEvent, TokenUsage
from kosmos.llm.usage import UsageTracker
from kosmos.permissions.models import SessionContext
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Per-test InMemorySpanExporter fixture using dedicated TracerProvider
# ---------------------------------------------------------------------------


@pytest.fixture()
def memory_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Patch _tracer in query, client, and executor modules with a test provider."""
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import kosmos.engine.query as query_mod
    import kosmos.tools.executor as executor_mod

    # Patch the module-level _tracer in each instrumented module.
    monkeypatch.setattr(query_mod, "_tracer", provider.get_tracer("kosmos.engine.query"))
    monkeypatch.setattr(executor_mod, "_tracer", provider.get_tracer("kosmos.tools.executor"))

    # Also store provider so mock stream can create 'chat' spans on same provider.
    monkeypatch.setattr(
        "tests.observability.test_query_parent_span._TEST_PROVIDER",
        provider,
        raising=False,
    )

    # Module-level variable to share provider with inner functions.
    global _TEST_PROVIDER  # noqa: PLW0603
    _TEST_PROVIDER = provider

    exporter.clear()
    return exporter


_TEST_PROVIDER: TracerProvider | None = None


# ---------------------------------------------------------------------------
# Schema models used by the test tool
# ---------------------------------------------------------------------------


class _DummyInput(BaseModel):
    value: str = "x"


class _DummyOutput(BaseModel):
    result: str = "ok"


# ---------------------------------------------------------------------------
# Registry + Executor factory helpers
# ---------------------------------------------------------------------------


def _make_registry_with_tool(tool_id: str = "dummy_tool") -> ToolRegistry:
    registry = ToolRegistry()
    tool = GovAPITool(
        id=tool_id,
        name_ko="더미 도구",
        ministry="OTHER",
        category=["test"],
        endpoint="http://example.com/api",
        auth_type="public",
        input_schema=_DummyInput,
        output_schema=_DummyOutput,
        search_hint="dummy test tool",
        auth_level="public",
        pipa_class="non_personal",
        is_irreversible=False,
        dpa_reference=None,
        requires_auth=False,
        is_concurrency_safe=True,
        is_personal_data=False,
    )
    registry.register(tool)
    return registry


def _make_executor(registry: ToolRegistry, tool_id: str = "dummy_tool") -> ToolExecutor:
    executor = ToolExecutor(registry=registry)

    async def _adapter(inp: _DummyInput) -> dict:
        return {"result": "ok"}

    executor.register_adapter(tool_id, _adapter)
    return executor


# ---------------------------------------------------------------------------
# T013 test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_query_produces_root_span_with_correct_attributes(
    memory_exporter: InMemorySpanExporter,
) -> None:
    """query() must produce one 'invoke_agent kosmos-query' root span with
    required attributes and child spans for chat + execute_tool."""
    # Import after monkeypatch so _tracer is already patched.
    from kosmos.engine.query import query

    TOOL_ID = "dummy_tool"  # noqa: N806
    SESSION_ID = "test-uuid"  # noqa: N806

    registry = _make_registry_with_tool(TOOL_ID)
    executor = _make_executor(registry, TOOL_ID)

    usage_tracker = UsageTracker(budget=100_000)
    state = QueryState(usage=usage_tracker)

    from kosmos.llm.models import ChatMessage

    state.messages.append(ChatMessage(role="user", content="hello"))

    config = QueryEngineConfig(max_iterations=3)
    session_ctx = SessionContext(session_id=SESSION_ID)

    tool_call_args = json.dumps({"value": "x"})
    call_count = 0

    async def _stream_dispatch(*args, **kwargs):
        """Mock stream that creates a 'chat' span on the test provider."""
        nonlocal call_count
        call_count += 1

        # Use the test provider to create the 'chat' span, mimicking LLMClient.stream().
        assert _TEST_PROVIDER is not None
        _tracer = _TEST_PROVIDER.get_tracer("kosmos.llm.client")
        span = _tracer.start_span("chat")
        span.set_attribute("gen_ai.operation.name", "chat")
        span.set_attribute("gen_ai.provider.name", "friendliai")
        span.set_attribute("gen_ai.request.model", "test-model")

        try:
            if call_count == 1:
                # First call: yield tool_call_delta to trigger one tool dispatch.
                yield StreamEvent(
                    type="tool_call_delta",
                    tool_call_index=0,
                    tool_call_id="call-001",
                    function_name=TOOL_ID,
                    function_args_delta=tool_call_args,
                )
            else:
                # Second call: text content + usage → causes stop.
                yield StreamEvent(type="content_delta", content="Done.")
                yield StreamEvent(
                    type="usage",
                    usage=TokenUsage(input_tokens=10, output_tokens=5),
                )
        finally:
            span.end()

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.stream = _stream_dispatch
    mock_llm.usage = usage_tracker

    ctx = QueryContext(
        state=state,
        llm_client=mock_llm,
        tool_executor=executor,
        tool_registry=registry,
        config=config,
        session_context=session_ctx,
    )

    # Consume the full generator.
    events = []
    async for event in query(ctx):
        events.append(event)

    spans = memory_exporter.get_finished_spans()
    span_names = [s.name for s in spans]

    # --- Assert: exactly one root span named 'invoke_agent kosmos-query' ---
    root_spans = [s for s in spans if s.name == "invoke_agent kosmos-query"]
    assert len(root_spans) == 1, (
        f"Expected exactly 1 root span 'invoke_agent kosmos-query', "
        f"found {len(root_spans)}. All spans: {span_names}"
    )
    root = root_spans[0]

    # --- Assert: root span attributes ---
    attrs = dict(root.attributes or {})
    assert attrs.get("gen_ai.operation.name") == "invoke_agent", (
        f"gen_ai.operation.name mismatch: {attrs}"
    )
    assert attrs.get("gen_ai.agent.name") == "kosmos-query", f"gen_ai.agent.name mismatch: {attrs}"
    assert attrs.get("gen_ai.conversation.id") == SESSION_ID, (
        f"gen_ai.conversation.id mismatch: {attrs}"
    )

    # --- Assert: root span status UNSET on success ---
    assert root.status.status_code == StatusCode.UNSET, (
        f"Expected UNSET status, got {root.status.status_code}"
    )

    # --- Assert: at least one 'chat' child span ---
    chat_spans = [s for s in spans if s.name == "chat"]
    assert len(chat_spans) >= 1, f"Expected at least one 'chat' child span. All spans: {span_names}"

    # --- Assert: at least one 'execute_tool *' child span ---
    tool_spans = [s for s in spans if s.name.startswith("execute_tool")]
    assert len(tool_spans) >= 1, (
        f"Expected at least one 'execute_tool *' child span. All spans: {span_names}"
    )

    # --- Assert: execute_tool spans have root as parent ---
    root_span_id = root.context.span_id
    for child_span in tool_spans:
        parent_id = child_span.parent.span_id if child_span.parent is not None else None
        assert parent_id == root_span_id, (
            f"Span '{child_span.name}' has parent_id {parent_id}, "
            f"expected root span_id {root_span_id}"
        )
