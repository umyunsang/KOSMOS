# SPDX-License-Identifier: Apache-2.0
"""Unit tests for LLMClient.complete() using respx for httpx mocking."""

from __future__ import annotations

import os

import httpx
import pytest
import respx

from kosmos.llm.client import LLMClient
from kosmos.llm.config import LLMClientConfig
from kosmos.llm.errors import (
    AuthenticationError,
    BudgetExceededError,
    ConfigurationError,
    LLMConnectionError,
    LLMResponseError,
)
from kosmos.llm.models import ChatMessage, FunctionSchema, ToolDefinition

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

CHAT_COMPLETIONS_URL = "https://api.friendli.ai/v1/chat/completions"


@pytest.fixture
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove all KOSMOS_* env vars then inject a safe test token."""
    for key in list(os.environ):
        if key.startswith("KOSMOS_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("KOSMOS_FRIENDLI_TOKEN", "test-token-12345")


# ---------------------------------------------------------------------------
# LLMClient initialization
# ---------------------------------------------------------------------------


async def test_client_init_with_config(
    _clean_env: None,
) -> None:
    """Client accepts an explicit LLMClientConfig and initializes without error."""
    config = LLMClientConfig()
    client = LLMClient(config)
    assert client._config is config
    await client.close()


async def test_client_init_from_env(
    _clean_env: None,
) -> None:
    """Client reads configuration from environment variables when config=None."""
    client = LLMClient(config=None)
    assert client._config.token.get_secret_value() == "test-token-12345"
    await client.close()


async def test_client_init_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Client raises ConfigurationError when KOSMOS_FRIENDLI_TOKEN is absent."""
    for key in list(os.environ):
        if key.startswith("KOSMOS_"):
            monkeypatch.delenv(key, raising=False)

    with pytest.raises(ConfigurationError):
        LLMClient(config=None)


async def test_client_context_manager(_clean_env: None) -> None:
    """Client works correctly as an async context manager."""
    config = LLMClientConfig()
    async with LLMClient(config) as client:
        assert client._config is config
    # After __aexit__ the underlying httpx client should be closed (no assertion
    # needed for the internal transport state; reaching here without error is
    # sufficient).


# ---------------------------------------------------------------------------
# LLMClient.complete() — success path
# ---------------------------------------------------------------------------


@respx.mock
async def test_complete_success(
    _clean_env: None,
    sample_messages: list[ChatMessage],
    mock_completion_response: dict,
) -> None:
    """complete() parses a successful 200 response into ChatCompletionResponse."""
    respx.post(CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(200, json=mock_completion_response)
    )

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        response = await client.complete(sample_messages)

    assert response.id == "chatcmpl-test-123"
    assert response.content == "Test response"
    assert response.model == "dep89a2fde0e09"
    assert response.finish_reason == "stop"


@respx.mock
async def test_complete_token_usage(
    _clean_env: None,
    sample_messages: list[ChatMessage],
    mock_completion_response: dict,
) -> None:
    """complete() correctly extracts prompt_tokens / completion_tokens from usage."""
    respx.post(CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(200, json=mock_completion_response)
    )

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        response = await client.complete(sample_messages)

    assert response.usage.input_tokens == 10
    assert response.usage.output_tokens == 5
    assert response.usage.total_tokens == 15


# ---------------------------------------------------------------------------
# LLMClient.complete() — error paths
# ---------------------------------------------------------------------------


@respx.mock
async def test_complete_auth_error(
    _clean_env: None,
    sample_messages: list[ChatMessage],
) -> None:
    """complete() raises AuthenticationError on a 401 response."""
    respx.post(CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(401, json={"error": "Unauthorized"})
    )

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        with pytest.raises(AuthenticationError) as exc_info:
            await client.complete(sample_messages)

    assert exc_info.value.status_code == 401


@respx.mock
async def test_complete_bad_request(
    _clean_env: None,
    sample_messages: list[ChatMessage],
) -> None:
    """complete() raises LLMResponseError on a 400 response."""
    respx.post(CHAT_COMPLETIONS_URL).mock(
        return_value=httpx.Response(400, json={"error": "Bad Request"})
    )

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        with pytest.raises(LLMResponseError) as exc_info:
            await client.complete(sample_messages)

    assert exc_info.value.status_code == 400


@respx.mock
async def test_complete_connection_error(
    _clean_env: None,
    sample_messages: list[ChatMessage],
) -> None:
    """complete() raises LLMConnectionError when the transport raises ConnectError."""
    respx.post(CHAT_COMPLETIONS_URL).mock(side_effect=httpx.ConnectError("Connection refused"))

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        with pytest.raises(LLMConnectionError):
            await client.complete(sample_messages)


# ---------------------------------------------------------------------------
# LLMClient.complete() — tool-use flow
# ---------------------------------------------------------------------------


@respx.mock
async def test_complete_with_tools(
    _clean_env: None,
    sample_messages: list[ChatMessage],
) -> None:
    """complete() includes tools in the request payload and parses tool_calls in the response."""
    tool_response = {
        "id": "chatcmpl-tool-test",
        "object": "chat.completion",
        "model": "dep89a2fde0e09",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_abc123",
                            "type": "function",
                            "function": {
                                "name": "get_weather",
                                "arguments": '{"city": "Seoul"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {"prompt_tokens": 20, "completion_tokens": 10},
    }

    captured_request: list[httpx.Request] = []

    def _capture(request: httpx.Request) -> httpx.Response:
        captured_request.append(request)
        return httpx.Response(200, json=tool_response)

    respx.post(CHAT_COMPLETIONS_URL).mock(side_effect=_capture)

    func_schema = FunctionSchema(
        name="get_weather",
        description="Get weather",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}},
    )
    tool_def = ToolDefinition(type="function", function=func_schema)

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        response = await client.complete(sample_messages, tools=[tool_def])

    # Verify tools were sent in the request payload
    import json as _json

    assert len(captured_request) == 1
    payload = _json.loads(captured_request[0].content)
    assert "tools" in payload
    assert len(payload["tools"]) == 1
    assert payload["tools"][0]["function"]["name"] == "get_weather"

    # Verify response.tool_calls is populated correctly
    assert len(response.tool_calls) == 1
    tc = response.tool_calls[0]
    assert tc.id == "call_abc123"
    assert tc.function.name == "get_weather"
    assert tc.function.arguments == '{"city": "Seoul"}'
    assert response.finish_reason == "tool_calls"


@respx.mock
async def test_complete_tool_result_continuation(
    _clean_env: None,
) -> None:
    """complete() accepts a tool-result turn (role='tool') and serializes it correctly."""
    continuation_response = {
        "id": "chatcmpl-continuation-test",
        "object": "chat.completion",
        "model": "dep89a2fde0e09",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": "The weather in Seoul is sunny, 22°C.",
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 30, "completion_tokens": 15},
    }

    captured_request: list[httpx.Request] = []

    def _capture(request: httpx.Request) -> httpx.Response:
        captured_request.append(request)
        return httpx.Response(200, json=continuation_response)

    respx.post(CHAT_COMPLETIONS_URL).mock(side_effect=_capture)

    # Build a message sequence that includes a tool-result turn
    messages = [
        ChatMessage(role="user", content="What is the weather in Seoul?"),
        ChatMessage(
            role="assistant",
            content=None,
            tool_calls=[
                {
                    "id": "call_xyz789",
                    "type": "function",
                    "function": {"name": "get_weather", "arguments": '{"city": "Seoul"}'},
                }
            ],
        ),
        ChatMessage(
            role="tool",
            content="sunny, 22°C",
            tool_call_id="call_xyz789",
        ),
    ]

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        response = await client.complete(messages)

    # Verify the request was made and the tool message was serialized
    import json as _json

    assert len(captured_request) == 1
    payload = _json.loads(captured_request[0].content)
    assert len(payload["messages"]) == 3

    tool_msg = payload["messages"][2]
    assert tool_msg["role"] == "tool"
    assert tool_msg["tool_call_id"] == "call_xyz789"
    assert tool_msg["content"] == "sunny, 22°C"

    # Verify the continuation response was parsed correctly
    assert response.content == "The weather in Seoul is sunny, 22°C."
    assert response.finish_reason == "stop"


@respx.mock
async def test_complete_budget_exhaustion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """complete() raises BudgetExceededError once the session token budget is exceeded."""
    # Set all KOSMOS_ vars then configure a very tight budget (30 tokens)
    for key in list(os.environ):
        if key.startswith("KOSMOS_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("KOSMOS_FRIENDLI_TOKEN", "test-token-12345")
    monkeypatch.setenv("KOSMOS_LLM_SESSION_BUDGET", "30")

    # First response uses 20 tokens (within budget)
    first_response = {
        "id": "chatcmpl-budget-1",
        "object": "chat.completion",
        "model": "dep89a2fde0e09",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "First response."},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 5},
    }

    # Second response uses 20 more tokens — pushes total to 40, exceeding budget of 30
    second_response = {
        "id": "chatcmpl-budget-2",
        "object": "chat.completion",
        "model": "dep89a2fde0e09",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Second response."},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 5},
    }

    respx.post(CHAT_COMPLETIONS_URL).mock(
        side_effect=[
            httpx.Response(200, json=first_response),
            httpx.Response(200, json=second_response),
        ]
    )

    messages = [ChatMessage(role="user", content="Hello")]

    config = LLMClientConfig()
    async with LLMClient(config) as client:
        # First call succeeds (20 tokens used, budget=30, still within limit)
        result = await client.complete(messages)
        assert result.content == "First response."

        # Second call causes total=40 which exceeds budget=30 and raises at debit
        with pytest.raises(BudgetExceededError):
            await client.complete(messages)
