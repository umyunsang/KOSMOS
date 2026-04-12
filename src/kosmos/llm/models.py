# SPDX-License-Identifier: Apache-2.0
"""Pydantic v2 message and response models for the KOSMOS LLM client."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator


class FunctionCall(BaseModel):
    """Function name and serialized arguments requested by the model."""

    model_config = ConfigDict(frozen=True)

    name: str
    arguments: str  # JSON-serialized string


class ToolCall(BaseModel):
    """Tool invocation requested by the model."""

    model_config = ConfigDict(frozen=True)

    id: str
    type: Literal["function"] = "function"
    function: FunctionCall


class ChatMessage(BaseModel):
    """A single message in a conversation, following the OpenAI chat format."""

    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant", "tool"]
    content: str | None = None
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None

    @model_validator(mode="after")
    def _validate_role_constraints(self) -> ChatMessage:
        """Enforce role-specific field requirements."""
        if self.role == "tool" and self.tool_call_id is None:
            raise ValueError("ChatMessage with role='tool' must provide tool_call_id")
        if self.role in ("system", "user") and self.content is None:
            raise ValueError(f"ChatMessage with role='{self.role}' must provide content")
        if self.tool_calls is not None and self.role != "assistant":
            raise ValueError("tool_calls is only valid on role='assistant' messages")
        if self.tool_call_id is not None and self.role != "tool":
            raise ValueError("tool_call_id is only valid on role='tool' messages")
        return self


class TokenUsage(BaseModel):
    """Token counts reported by a single LLM call."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    cache_write_tokens: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def total_tokens(self) -> int:
        """Sum of input and output tokens."""
        return self.input_tokens + self.output_tokens


class ChatCompletionResponse(BaseModel):
    """Complete response from a non-streaming LLM call."""

    model_config = ConfigDict(frozen=True)

    id: str
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    usage: TokenUsage
    model: str
    finish_reason: Literal["stop", "tool_calls", "length"]


class StreamEvent(BaseModel):
    """A single event emitted during a streaming LLM response."""

    model_config = ConfigDict(frozen=True)

    type: Literal["content_delta", "tool_call_delta", "usage", "done", "error"]
    content: str | None = None
    tool_call_index: int | None = None
    tool_call_id: str | None = None
    function_name: str | None = None
    function_args_delta: str | None = None
    usage: TokenUsage | None = None


class FunctionSchema(BaseModel):
    """Schema definition for a function/tool."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    # dict[str, Any] is acceptable here: this field holds an external JSON Schema
    # object whose structure is defined by the OpenAI/FriendliAI spec, not by KOSMOS
    # internal I/O contracts. Using Any is the only correct representation.
    parameters: dict[str, Any]


class ToolDefinition(BaseModel):
    """Tool schema sent to the model for function calling."""

    model_config = ConfigDict(frozen=True)

    type: Literal["function"] = "function"
    function: FunctionSchema
