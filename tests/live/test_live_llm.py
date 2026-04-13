# SPDX-License-Identifier: Apache-2.0
"""Live validation tests for the KOSMOS LLM client against the real FriendliAI K-EXAONE API.

These tests hit the actual FriendliAI Serverless endpoint — no mocks.  They are
marked ``@pytest.mark.live`` and are skipped by default; run them with::

    uv run pytest -m live tests/live/test_live_llm.py

Required environment variable:
    KOSMOS_FRIENDLI_TOKEN — FriendliAI API token (validated by the ``friendli_token`` fixture)
"""

from __future__ import annotations

import pytest

from kosmos.llm.client import LLMClient
from kosmos.llm.models import (
    ChatCompletionResponse,
    ChatMessage,
    FunctionSchema,
    StreamEvent,
    ToolDefinition,
)

# ---------------------------------------------------------------------------
# Test 1 — basic streaming
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_llm_stream_basic(friendli_token: str) -> None:
    """Stream a simple Korean greeting and verify the event structure.

    The ``friendli_token`` fixture ensures ``KOSMOS_FRIENDLI_TOKEN`` is set in
    the environment before LLMClient reads it.
    """
    messages = [ChatMessage(role="user", content="안녕하세요, 간단하게 인사해주세요.")]
    events: list[StreamEvent] = []

    async with LLMClient() as client:
        async for event in client.stream(messages, max_tokens=50):
            events.append(event)

    # At least one content_delta event must be present
    content_deltas = [e for e in events if e.type == "content_delta"]
    assert len(content_deltas) >= 1, "Expected at least one content_delta event"

    # Exactly one "done" event
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1, f"Expected exactly one done event, got {len(done_events)}"

    # The "done" event must be the last event in the sequence
    assert events[-1].type == "done", (
        f"Expected last event to be 'done', got {events[-1].type!r}"
    )

    # At least one content_delta must carry non-empty text
    non_empty_deltas = [e for e in content_deltas if e.content]
    assert len(non_empty_deltas) >= 1, (
        "Expected at least one content_delta with non-empty content"
    )


# ---------------------------------------------------------------------------
# Test 2 — streaming with tool definitions
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_llm_stream_with_tool_definitions(friendli_token: str) -> None:
    """Stream a weather-related message with a dummy tool and verify structure.

    The model may choose to emit content_delta events (free-text reply) OR
    tool_call_delta events (function call) — both are valid outcomes.  The test
    only verifies structural correctness, not which path the model took.
    """
    weather_tool = ToolDefinition(
        type="function",
        function=FunctionSchema(
            name="get_current_weather",
            description="Get the current weather for a given location.",
            parameters={
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City name or location, e.g. Seoul, South Korea",
                    },
                },
                "required": ["location"],
            },
        ),
    )

    messages = [
        ChatMessage(role="user", content="What is the current weather in Seoul?")
    ]
    events: list[StreamEvent] = []

    async with LLMClient() as client:
        async for event in client.stream(messages, tools=[weather_tool], max_tokens=50):
            events.append(event)

    # Either content or tool calls must be present — the model chose one path
    content_events = [e for e in events if e.type == "content_delta"]
    tool_call_events = [e for e in events if e.type == "tool_call_delta"]
    assert len(content_events) > 0 or len(tool_call_events) > 0, (
        "Expected at least one content_delta or tool_call_delta event"
    )

    # A "done" event must always be present
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) >= 1, "Expected at least one done event"


# ---------------------------------------------------------------------------
# Test 3 — non-streaming completion
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_llm_complete_basic(friendli_token: str) -> None:
    """Call complete() (non-streaming) and verify the response model structure."""
    messages = [ChatMessage(role="user", content="안녕하세요, 간단하게 인사해주세요.")]

    async with LLMClient() as client:
        result = await client.complete(messages, max_tokens=50)

        # --- Stateful: UsageTracker records real token counts (T020) ---
        tracker = client.usage
        assert tracker.call_count >= 1, (
            f"UsageTracker.call_count should be >=1, got {tracker.call_count}"
        )
        assert tracker.total_used > 0, (
            f"UsageTracker.total_used should be >0, got {tracker.total_used}"
        )
        assert tracker.remaining < tracker.budget, (
            "UsageTracker.remaining should be less than budget after a call"
        )

    # Return value must be a ChatCompletionResponse
    assert isinstance(result, ChatCompletionResponse), (
        f"Expected ChatCompletionResponse, got {type(result)}"
    )

    # Token usage must be positive — hard-fail if the API returned zeros
    assert result.usage.input_tokens > 0, (
        f"Expected input_tokens > 0, got {result.usage.input_tokens}"
    )
    assert result.usage.output_tokens > 0, (
        f"Expected output_tokens > 0, got {result.usage.output_tokens}"
    )

    # finish_reason must be one of the documented values
    valid_finish_reasons = {"stop", "tool_calls", "length"}
    assert result.finish_reason in valid_finish_reasons, (
        f"Unexpected finish_reason {result.finish_reason!r}; "
        f"expected one of {valid_finish_reasons}"
    )
