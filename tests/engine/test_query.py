# SPDX-License-Identifier: Apache-2.0
"""Unit tests for kosmos.engine.query — the per-turn query loop.

All tests use mocks only; no live API calls are made.
asyncio_mode = "auto" is configured in pyproject.toml, so no explicit
@pytest.mark.asyncio decoration is required (but we add it for clarity).
"""

from __future__ import annotations

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, QueryState
from kosmos.engine.query import query

# LLMClient must be imported (not just under TYPE_CHECKING) so that
# QueryContext.model_rebuild() can resolve the forward reference and accept
# mock objects for the llm_client field.
from kosmos.llm.client import LLMClient  # noqa: F401
from kosmos.llm.models import ChatMessage
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

QueryContext.model_rebuild()


# ---------------------------------------------------------------------------
# Helper: collect all events from the async generator into a list
# ---------------------------------------------------------------------------


async def _collect(ctx: QueryContext) -> list[QueryEvent]:
    """Drain the query() generator and return the ordered event list."""
    events: list[QueryEvent] = []
    async for event in query(ctx):
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Helper: build a QueryContext from fixture objects
# ---------------------------------------------------------------------------


def _make_ctx(
    llm_client: object,
    tool_executor: ToolExecutor,
    tool_registry: ToolRegistry,
    config: QueryEngineConfig,
    *,
    messages: list[ChatMessage] | None = None,
) -> QueryContext:
    """Construct a QueryContext with sensible defaults for testing."""
    if messages is None:
        messages = [
            ChatMessage(role="system", content="You are KOSMOS."),
            ChatMessage(role="user", content="서울 강남구 교통사고 현황"),
        ]
    state = QueryState(
        usage=UsageTracker(budget=100_000),
        messages=list(messages),
    )
    # Use model_construct() to bypass Pydantic's isinstance check against the
    # real LLMClient class — our MockLLMClient objects satisfy the structural
    # interface (stream(), usage property) but don't inherit from LLMClient.
    return QueryContext.model_construct(
        state=state,
        llm_client=llm_client,
        tool_executor=tool_executor,
        tool_registry=tool_registry,
        config=config,
        iteration=0,
    )


# ---------------------------------------------------------------------------
# Test 1: single tool call loop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_tool_call_loop(
    mock_llm_client,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """Single tool call followed by a text answer.

    Expected event sequence:
        tool_use → tool_result → usage_update → text_delta → usage_update → stop(end_turn)
    """
    ctx = _make_ctx(mock_llm_client, tool_executor_with_mocks, populated_registry, sample_config)
    events = await _collect(ctx)

    types = [e.type for e in events]
    assert types == [
        "tool_use",
        "tool_result",
        "usage_update",
        "text_delta",
        "usage_update",
        "stop",
    ]

    # Verify stop reason
    stop_event = events[-1]
    assert stop_event.stop_reason == StopReason.end_turn

    # Verify a tool result message was appended to state.messages
    roles = [m.role for m in ctx.state.messages]
    assert "tool" in roles


# ---------------------------------------------------------------------------
# Test 2: no-tool direct answer
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_tool_direct_answer(
    mock_llm_client_no_tools,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """LLM returns a direct text answer without any tool calls.

    Expected event sequence: text_delta → usage_update → stop(end_turn)
    """
    ctx = _make_ctx(
        mock_llm_client_no_tools, tool_executor_with_mocks, populated_registry, sample_config
    )
    events = await _collect(ctx)

    types = [e.type for e in events]
    assert types == ["text_delta", "usage_update", "stop"]

    stop_event = events[-1]
    assert stop_event.stop_reason == StopReason.end_turn

    # The last appended message must be an assistant message without tool_calls
    assistant_msgs = [m for m in ctx.state.messages if m.role == "assistant"]
    assert assistant_msgs, "Expected at least one assistant message in history"
    last_assistant = assistant_msgs[-1]
    assert last_assistant.tool_calls is None


# ---------------------------------------------------------------------------
# Test 3: two simultaneous tool calls in one response
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_two_sequential_tool_calls(
    mock_llm_client_two_tools,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """LLM requests two tools in a single response.

    Expected sequence for iteration 1:
        tool_use, tool_use, tool_result, tool_result, usage_update
    Followed by text answer:
        text_delta, usage_update, stop(end_turn)
    """
    ctx = _make_ctx(
        mock_llm_client_two_tools, tool_executor_with_mocks, populated_registry, sample_config
    )
    events = await _collect(ctx)

    types = [e.type for e in events]

    # Count event types
    assert types.count("tool_use") == 2
    assert types.count("tool_result") == 2

    # Verify both tools were dispatched (tool_use events carry correct names)
    tool_use_events = [e for e in events if e.type == "tool_use"]
    dispatched_names = {e.tool_name for e in tool_use_events}
    assert "traffic_accident_search" in dispatched_names
    assert "weather_info" in dispatched_names

    # Final stop must be end_turn
    stop_event = events[-1]
    assert stop_event.type == "stop"
    assert stop_event.stop_reason == StopReason.end_turn


# ---------------------------------------------------------------------------
# Test 4: unknown tool error injection
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_tool_error_injection(
    mock_llm_client_unknown_tool,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """LLM requests a non-existent tool on the first call.

    The executor must return success=False without raising, the loop injects a
    tool_result with success=False, and continues to the next LLM call which
    returns a text answer.
    """
    ctx = _make_ctx(
        mock_llm_client_unknown_tool, tool_executor_with_mocks, populated_registry, sample_config
    )
    events = await _collect(ctx)

    # There must be a failed tool_result
    tool_result_events = [e for e in events if e.type == "tool_result"]
    assert len(tool_result_events) >= 1
    failed_result = tool_result_events[0]
    assert failed_result.tool_result is not None
    assert failed_result.tool_result.success is False

    # Loop must continue — final event is stop(end_turn), not stop(error_unrecoverable)
    stop_event = events[-1]
    assert stop_event.type == "stop"
    assert stop_event.stop_reason == StopReason.end_turn

    # No exception was raised — the test completing without error confirms this


# ---------------------------------------------------------------------------
# Test 5: max iterations termination
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_max_iterations_termination(
    mock_llm_client_infinite_tools,
    tool_executor_with_mocks,
    populated_registry,
):
    """Engine must stop with max_iterations_reached after hitting the limit.

    Uses max_iterations=3 so we do not loop forever.
    """
    config = QueryEngineConfig(max_iterations=3)
    ctx = _make_ctx(
        mock_llm_client_infinite_tools, tool_executor_with_mocks, populated_registry, config
    )
    events = await _collect(ctx)

    stop_event = events[-1]
    assert stop_event.type == "stop"
    assert stop_event.stop_reason == StopReason.max_iterations_reached

    # There should be exactly 3 usage_update events (one per tool-calling iteration)
    usage_events = [e for e in events if e.type == "usage_update"]
    assert len(usage_events) == 3

    # The LLM must have been called exactly 3 times
    assert mock_llm_client_infinite_tools.call_count == 3


# ---------------------------------------------------------------------------
# Test 6: usage_update event emission with correct values
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_usage_update_contains_token_counts(
    mock_llm_client_no_tools,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """usage_update event must carry a TokenUsage with expected counts.

    The no-tools mock emits TokenUsage(input_tokens=50, output_tokens=20).
    """
    ctx = _make_ctx(
        mock_llm_client_no_tools, tool_executor_with_mocks, populated_registry, sample_config
    )
    events = await _collect(ctx)

    usage_events = [e for e in events if e.type == "usage_update"]
    assert len(usage_events) == 1

    usage = usage_events[0].usage
    assert usage is not None
    assert usage.input_tokens == 50
    assert usage.output_tokens == 20
    assert usage.total_tokens == 70


# ---------------------------------------------------------------------------
# Test 7: cancellation via break (FR-010)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancellation_via_break(
    mock_llm_client,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """Breaking out of the async for loop must not raise any exception.

    This validates FR-010: the generator must support early cancellation
    cleanly via a plain break.
    """
    ctx = _make_ctx(mock_llm_client, tool_executor_with_mocks, populated_registry, sample_config)

    collected: list[QueryEvent] = []
    # We intentionally break after the first text_delta (or any first event)
    async for event in query(ctx):
        collected.append(event)
        break  # cancel immediately

    # No exception raised — reaching this point confirms clean cancellation
    assert len(collected) == 1


# ---------------------------------------------------------------------------
# Test 8: immutable snapshot verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_immutable_snapshot_is_a_copy(
    mock_llm_client_inspectable,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """The LLM client must receive a copy of state.messages, not the same object.

    After at least one stream() call, mock_llm_client_inspectable.last_messages
    must be a different list object than ctx.state.messages.
    """
    ctx = _make_ctx(
        mock_llm_client_inspectable, tool_executor_with_mocks, populated_registry, sample_config
    )
    # Drain all events to ensure stream() was called
    await _collect(ctx)

    last_messages = mock_llm_client_inspectable.last_messages
    assert last_messages is not None, "stream() was never called"

    # The snapshot passed to the LLM must not be the same list object as
    # ctx.state.messages (which grows as tool results are appended).
    assert last_messages is not ctx.state.messages


# ---------------------------------------------------------------------------
# Test 9: LLM stream exception yields stop(error_unrecoverable)
# ---------------------------------------------------------------------------


class _ErrorLLMClient:
    """Mock LLM client that always raises an exception during streaming."""

    call_count: int = 0

    @property
    def usage(self):  # noqa: ANN201
        from kosmos.llm.usage import UsageTracker

        return UsageTracker(budget=100_000)

    async def stream(self, messages, **kwargs):  # noqa: ANN001, ANN201
        self.call_count += 1
        raise RuntimeError("Simulated LLM failure")
        yield  # make this an async generator


@pytest.mark.asyncio
async def test_llm_stream_exception_yields_error_stop(
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """An exception from the LLM stream must be captured and produce stop(error_unrecoverable).

    The generator must NOT propagate the exception to the caller.
    """
    error_client = _ErrorLLMClient()
    ctx = _make_ctx(error_client, tool_executor_with_mocks, populated_registry, sample_config)
    events = await _collect(ctx)

    assert len(events) == 1
    stop_event = events[0]
    assert stop_event.type == "stop"
    assert stop_event.stop_reason == StopReason.error_unrecoverable
    assert stop_event.stop_message is not None
    assert "LLM stream error" in stop_event.stop_message


# ---------------------------------------------------------------------------
# Test 10: tool result message appended to state.messages after dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_tool_result_message_appended_to_history(
    mock_llm_client,
    tool_executor_with_mocks,
    populated_registry,
    sample_config,
):
    """After a successful tool dispatch, a role='tool' message must appear in state.messages."""
    initial_messages = [
        ChatMessage(role="system", content="You are KOSMOS."),
        ChatMessage(role="user", content="서울 강남구 교통사고 현황"),
    ]
    ctx = _make_ctx(
        mock_llm_client,
        tool_executor_with_mocks,
        populated_registry,
        sample_config,
        messages=initial_messages,
    )
    await _collect(ctx)

    tool_messages = [m for m in ctx.state.messages if m.role == "tool"]
    assert len(tool_messages) >= 1
    # The tool message must carry a tool_call_id matching the call from the mock
    assert tool_messages[0].tool_call_id == "call_001"
