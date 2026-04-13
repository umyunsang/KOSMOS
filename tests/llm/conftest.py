# SPDX-License-Identifier: Apache-2.0
"""Shared pytest fixtures for LLM client tests."""

from __future__ import annotations

import json

import pytest

from kosmos.llm.config import LLMClientConfig
from kosmos.llm.models import ChatMessage


@pytest.fixture
def sample_messages() -> list[ChatMessage]:
    """A list of sample ChatMessage objects covering all three common roles."""
    return [
        ChatMessage(role="system", content="You are a helpful Korean public-data assistant."),
        ChatMessage(role="user", content="서울 날씨를 알려주세요."),
        ChatMessage(role="assistant", content="현재 서울의 날씨를 조회하겠습니다."),
    ]


@pytest.fixture
def mock_completion_response() -> dict:
    """A dict matching the OpenAI chat/completions non-streaming response format."""
    return {
        "id": "chatcmpl-test-123",
        "object": "chat.completion",
        "model": "LGAI-EXAONE/K-EXAONE-236B-A23B",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": "Test response"},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 5,
            "total_tokens": 15,
        },
    }


@pytest.fixture
def mock_sse_lines() -> list[bytes]:
    """SSE-formatted byte strings simulating a streaming chat completion response."""
    chunks = [
        {
            "id": "chatcmpl-test-123",
            "object": "chat.completion.chunk",
            "choices": [
                {
                    "index": 0,
                    "delta": {"role": "assistant", "content": "Hello"},
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-test-123",
            "object": "chat.completion.chunk",
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": " world"},
                    "finish_reason": None,
                }
            ],
        },
        {
            "id": "chatcmpl-test-123",
            "object": "chat.completion.chunk",
            "choices": [
                {
                    "index": 0,
                    "delta": {},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15,
            },
        },
    ]
    lines: list[bytes] = [f"data: {json.dumps(chunk)}\n\n".encode() for chunk in chunks]
    lines.append(b"data: [DONE]\n\n")
    return lines


@pytest.fixture
def mock_tool_call_response() -> dict:
    """A dict with tool_calls in the assistant message, matching the OpenAI format."""
    return {
        "id": "chatcmpl-test-456",
        "object": "chat.completion",
        "model": "LGAI-EXAONE/K-EXAONE-236B-A23B",
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
                                "name": "kma_weather_forecast",
                                "arguments": '{"city": "서울"}',
                            },
                        }
                    ],
                },
                "finish_reason": "tool_calls",
            }
        ],
        "usage": {
            "prompt_tokens": 15,
            "completion_tokens": 20,
            "total_tokens": 35,
        },
    }


@pytest.fixture
def llm_config(monkeypatch: pytest.MonkeyPatch) -> LLMClientConfig:
    """An LLMClientConfig instance backed by test environment variables."""
    monkeypatch.setenv("KOSMOS_FRIENDLI_TOKEN", "test-token-12345")
    return LLMClientConfig()
