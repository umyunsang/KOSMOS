# SPDX-License-Identifier: Apache-2.0
"""Tests for StreamInterruptedError retry logic in query.py."""

from __future__ import annotations

from collections.abc import AsyncIterator

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.engine.models import QueryContext, QueryState
from kosmos.engine.query import query
from kosmos.llm.client import LLMClient  # noqa: F401 — needed for model_rebuild
from kosmos.llm.errors import StreamInterruptedError
from kosmos.llm.models import ChatMessage, StreamEvent, TokenUsage
from kosmos.llm.usage import UsageTracker
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

# Rebuild QueryContext so model_construct() works with mock llm_client objects
QueryContext.model_rebuild()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _content_event(text: str) -> StreamEvent:
    return StreamEvent(
        type="content_delta",
        content=text,
        tool_call_index=None,
        tool_call_id=None,
        function_name=None,
        function_args_delta=None,
        usage=None,
    )


def _usage_event() -> StreamEvent:
    return StreamEvent(
        type="usage",
        content=None,
        tool_call_index=None,
        tool_call_id=None,
        function_name=None,
        function_args_delta=None,
        usage=TokenUsage(input_tokens=10, output_tokens=5),
    )


async def _collect(ctx: QueryContext) -> list[QueryEvent]:
    events: list[QueryEvent] = []
    async for event in query(ctx):  # type: ignore[arg-type]
        events.append(event)
    return events


# ---------------------------------------------------------------------------
# Mock LLM client
# ---------------------------------------------------------------------------


class _MockInterruptingClient:
    """LLM client that raises StreamInterruptedError on the first call,
    then yields normal events on subsequent calls."""

    def __init__(self) -> None:
        self.call_count = 0
        self.usage = UsageTracker(budget=100_000)

    async def stream(
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[StreamEvent]:
        self.call_count += 1
        if self.call_count == 1:
            raise StreamInterruptedError("stream cut on first call")
        yield _content_event("hello")
        yield _usage_event()


class _MockAlwaysInterruptingClient:
    """LLM client that always raises StreamInterruptedError."""

    def __init__(self) -> None:
        self.call_count = 0
        self.usage = UsageTracker(budget=100_000)

    async def stream(
        self,
        messages: list[ChatMessage],
        **kwargs: object,
    ) -> AsyncIterator[StreamEvent]:
        self.call_count += 1
        raise StreamInterruptedError("stream always cut")
        yield  # type: ignore[misc]  # make it an async generator


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_ctx(llm_client: object) -> QueryContext:
    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)
    usage = UsageTracker(budget=100_000)
    state = QueryState(
        usage=usage,
        messages=[ChatMessage(role="user", content="hello")],
    )
    config = QueryEngineConfig(max_iterations=5)
    return QueryContext.model_construct(
        state=state,
        config=config,
        llm_client=llm_client,
        tool_registry=registry,
        tool_executor=executor,
        permission_pipeline=None,
        session_context=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestStreamInterruptedErrorRetry:
    async def test_first_interruption_retries(self) -> None:
        """On the first StreamInterruptedError, query retries and succeeds."""
        client = _MockInterruptingClient()
        ctx = _make_ctx(client)

        events = await _collect(ctx)

        stop_events = [e for e in events if e.type == "stop"]
        assert len(stop_events) == 1
        assert stop_events[0].stop_reason == StopReason.end_turn
        assert client.call_count == 2

    async def test_second_interruption_is_unrecoverable(self) -> None:
        """On the second StreamInterruptedError, query stops with error_unrecoverable."""
        client = _MockAlwaysInterruptingClient()
        ctx = _make_ctx(client)

        events = await _collect(ctx)

        stop_events = [e for e in events if e.type == "stop"]
        assert len(stop_events) == 1
        assert stop_events[0].stop_reason == StopReason.error_unrecoverable
        assert "interrupted" in (stop_events[0].stop_message or "").lower()
        assert client.call_count == 2  # initial + one retry

    async def test_interruption_count_resets_across_turns(self) -> None:
        """The interrupted count tracks per iteration of the while loop."""
        # Each call to stream() raises StreamInterruptedError; after 2 raises
        # the engine gives up with error_unrecoverable.
        client = _MockAlwaysInterruptingClient()
        ctx = _make_ctx(client)

        events = await _collect(ctx)

        stop_events = [e for e in events if e.type == "stop"]
        assert stop_events[-1].stop_reason == StopReason.error_unrecoverable
