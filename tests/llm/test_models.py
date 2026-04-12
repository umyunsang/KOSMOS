# SPDX-License-Identifier: Apache-2.0
"""Unit tests for Pydantic model validation in kosmos.llm.models."""

import pytest
from pydantic import ValidationError

from kosmos.llm.models import (
    ChatCompletionResponse,
    ChatMessage,
    FunctionCall,
    StreamEvent,
    TokenUsage,
    ToolCall,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tool_call(id: str = "call_abc") -> ToolCall:  # noqa: A002
    return ToolCall(id=id, function=FunctionCall(name="my_tool", arguments="{}"))


# ---------------------------------------------------------------------------
# ChatMessage — validation failures
# ---------------------------------------------------------------------------


def test_system_message_requires_content() -> None:
    """system role without content must raise ValidationError."""
    with pytest.raises(ValidationError):
        ChatMessage(role="system")


def test_user_message_requires_content() -> None:
    """user role without content must raise ValidationError."""
    with pytest.raises(ValidationError):
        ChatMessage(role="user")


def test_tool_message_requires_tool_call_id() -> None:
    """tool role without tool_call_id must raise ValidationError."""
    with pytest.raises(ValidationError):
        ChatMessage(role="tool", content="result")


# ---------------------------------------------------------------------------
# ChatMessage — valid construction
# ---------------------------------------------------------------------------


def test_assistant_message_allows_no_content() -> None:
    """assistant role with content=None is valid (tool_calls path)."""
    msg = ChatMessage(role="assistant", content=None)
    assert msg.content is None


def test_valid_system_message() -> None:
    """system role with content constructs without error."""
    msg = ChatMessage(role="system", content="You are a helpful assistant.")
    assert msg.role == "system"
    assert msg.content == "You are a helpful assistant."


def test_valid_user_message() -> None:
    """user role with content constructs without error."""
    msg = ChatMessage(role="user", content="Hello!")
    assert msg.role == "user"
    assert msg.content == "Hello!"


def test_valid_tool_message() -> None:
    """tool role with tool_call_id and content constructs without error."""
    msg = ChatMessage(role="tool", tool_call_id="call_xyz", content="42")
    assert msg.tool_call_id == "call_xyz"
    assert msg.content == "42"


def test_valid_assistant_with_tool_calls() -> None:
    """assistant with a non-empty tool_calls list constructs without error."""
    tc = _make_tool_call()
    msg = ChatMessage(role="assistant", tool_calls=[tc])
    assert len(msg.tool_calls) == 1  # type: ignore[arg-type]
    assert msg.tool_calls[0].id == "call_abc"  # type: ignore[index]


# ---------------------------------------------------------------------------
# TokenUsage
# ---------------------------------------------------------------------------


def test_total_tokens_computed() -> None:
    """total_tokens equals input_tokens + output_tokens."""
    usage = TokenUsage(input_tokens=10, output_tokens=25)
    assert usage.total_tokens == 35


def test_default_values() -> None:
    """All TokenUsage fields default to 0."""
    usage = TokenUsage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.cache_read_tokens == 0
    assert usage.cache_write_tokens == 0
    assert usage.total_tokens == 0


# ---------------------------------------------------------------------------
# StreamEvent
# ---------------------------------------------------------------------------


def test_content_delta_event() -> None:
    """StreamEvent of type content_delta carries the content field."""
    event = StreamEvent(type="content_delta", content="Hello")
    assert event.type == "content_delta"
    assert event.content == "Hello"


def test_usage_event() -> None:
    """StreamEvent of type usage carries a TokenUsage payload."""
    usage = TokenUsage(input_tokens=5, output_tokens=8)
    event = StreamEvent(type="usage", usage=usage)
    assert event.type == "usage"
    assert event.usage is not None
    assert event.usage.total_tokens == 13


def test_done_event() -> None:
    """StreamEvent of type done constructs with no extra fields set."""
    event = StreamEvent(type="done")
    assert event.type == "done"
    assert event.content is None
    assert event.usage is None


# ---------------------------------------------------------------------------
# ChatCompletionResponse
# ---------------------------------------------------------------------------


def test_valid_response() -> None:
    """ChatCompletionResponse with all fields populated constructs correctly."""
    usage = TokenUsage(input_tokens=10, output_tokens=20)
    response = ChatCompletionResponse(
        id="resp_001",
        content="The answer is 42.",
        usage=usage,
        model="exaone-3.5",
        finish_reason="stop",
    )
    assert response.id == "resp_001"
    assert response.content == "The answer is 42."
    assert response.usage.total_tokens == 30
    assert response.model == "exaone-3.5"
    assert response.finish_reason == "stop"


def test_tool_calls_default_empty() -> None:
    """tool_calls defaults to an empty list when not provided."""
    usage = TokenUsage(input_tokens=1, output_tokens=1)
    response = ChatCompletionResponse(
        id="resp_002",
        usage=usage,
        model="exaone-3.5",
        finish_reason="tool_calls",
    )
    assert response.tool_calls == []
