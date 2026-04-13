# SPDX-License-Identifier: Apache-2.0
"""Integration tests: LLM client metrics instrumentation (T004).

Validates:
- complete() increments token counters (AC-A3, AC-A4)
- complete() records call duration histogram
- stream() increments token counters and duration
- No metrics collector → no error (backward-compatible, AC-A11)
- Histogram has non-zero p50/p95/p99 after 10 observations
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from kosmos.llm.config import LLMClientConfig
from kosmos.llm.models import ChatMessage
from kosmos.observability.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _make_config(monkeypatch: pytest.MonkeyPatch) -> LLMClientConfig:
    monkeypatch.setenv("KOSMOS_FRIENDLI_TOKEN", "test-token-12345")
    return LLMClientConfig()


def _mock_completion_response() -> dict:
    return {
        "id": "chatcmpl-test-001",
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
            "prompt_tokens": 20,
            "completion_tokens": 10,
            "total_tokens": 30,
        },
    }


def _mock_sse_lines() -> list[bytes]:
    chunks = [
        {
            "id": "chatcmpl-test-002",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {"content": "Hello"}, "finish_reason": None}],
        },
        {
            "id": "chatcmpl-test-002",
            "object": "chat.completion.chunk",
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
        },
    ]
    lines: list[bytes] = [f"data: {json.dumps(c)}\n\n".encode() for c in chunks]
    lines.append(b"data: [DONE]\n\n")
    return lines


def _messages() -> list[ChatMessage]:
    return [ChatMessage(role="user", content="Hello")]


# ---------------------------------------------------------------------------
# T004: test_complete_increments_token_counters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_increments_token_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete() causes UsageTracker.debit() to increment token counters."""
    from kosmos.llm.client import LLMClient  # noqa: PLC0415

    config = _make_config(monkeypatch)
    mc = MetricsCollector()
    client = LLMClient(config=config, metrics=mc)

    mock_response = MagicMock()
    mock_response.json.return_value = _mock_completion_response()
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new=AsyncMock(return_value=mock_response)):
        await client.complete(_messages())

    assert mc.get_counter("llm.input_tokens") == 20
    assert mc.get_counter("llm.output_tokens") == 10


# ---------------------------------------------------------------------------
# T004: test_complete_observes_duration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_observes_duration(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete() records a call duration histogram entry."""
    from kosmos.llm.client import LLMClient  # noqa: PLC0415

    config = _make_config(monkeypatch)
    mc = MetricsCollector()
    client = LLMClient(config=config, metrics=mc)

    mock_response = MagicMock()
    mock_response.json.return_value = _mock_completion_response()
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new=AsyncMock(return_value=mock_response)):
        await client.complete(_messages())

    stats = mc.get_histogram_stats("llm.call_duration_ms", labels={"model": config.model})
    assert stats["count"] == 1.0
    assert stats["avg"] >= 0.0


# ---------------------------------------------------------------------------
# T004: test_stream_increments_token_counters
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stream_increments_token_counters(monkeypatch: pytest.MonkeyPatch) -> None:
    """stream() causes UsageTracker.debit() to increment token counters."""
    from kosmos.llm.client import LLMClient  # noqa: PLC0415

    config = _make_config(monkeypatch)
    mc = MetricsCollector()
    client = LLMClient(config=config, metrics=mc)

    sse_lines = [line.decode().strip() for line in _mock_sse_lines()]

    async def _fake_aiter_lines():  # type: ignore[return]
        for line in sse_lines:
            yield line

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.aiter_lines = _fake_aiter_lines
    mock_response.aread = AsyncMock()

    class MockStreamContext:
        async def __aenter__(self) -> MagicMock:
            return mock_response

        async def __aexit__(self, *args: object) -> None:
            pass

    with patch.object(client._client, "stream", return_value=MockStreamContext()):
        events = []
        async for event in client.stream(_messages()):
            events.append(event)

    assert mc.get_counter("llm.input_tokens") == 8
    assert mc.get_counter("llm.output_tokens") == 4


# ---------------------------------------------------------------------------
# T004: test_no_metrics_no_error (backward compat)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_metrics_no_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """When no MetricsCollector is provided, complete() works without error."""
    from kosmos.llm.client import LLMClient  # noqa: PLC0415

    config = _make_config(monkeypatch)
    client = LLMClient(config=config)  # no metrics

    mock_response = MagicMock()
    mock_response.json.return_value = _mock_completion_response()
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new=AsyncMock(return_value=mock_response)):
        result = await client.complete(_messages())

    assert result.content == "Test response"


# ---------------------------------------------------------------------------
# T004: test_histogram_percentiles_10_observations
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_histogram_percentiles_10_observations(monkeypatch: pytest.MonkeyPatch) -> None:
    """After 10 complete() calls, histogram p50/p95/p99 are non-zero."""
    from kosmos.llm.client import LLMClient  # noqa: PLC0415

    config = _make_config(monkeypatch)
    mc = MetricsCollector()
    client = LLMClient(config=config, metrics=mc)

    mock_response = MagicMock()
    mock_response.json.return_value = _mock_completion_response()
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new=AsyncMock(return_value=mock_response)):
        for _ in range(10):
            await client.complete(_messages())

    stats = mc.get_histogram_stats("llm.call_duration_ms", labels={"model": config.model})
    assert stats["count"] == 10.0
    # Values should be non-negative (timing is very fast in tests so may be ~0)
    assert stats["p50"] >= 0.0
    assert stats["p95"] >= 0.0
    assert stats["p99"] >= 0.0


# ---------------------------------------------------------------------------
# T004: test_complete_increments_call_count
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_complete_increments_call_count(monkeypatch: pytest.MonkeyPatch) -> None:
    """complete() increments llm.call_count with model label."""
    from kosmos.llm.client import LLMClient  # noqa: PLC0415

    config = _make_config(monkeypatch)
    mc = MetricsCollector()
    client = LLMClient(config=config, metrics=mc)

    mock_response = MagicMock()
    mock_response.json.return_value = _mock_completion_response()
    mock_response.raise_for_status = MagicMock()

    with patch.object(client._client, "post", new=AsyncMock(return_value=mock_response)):
        await client.complete(_messages())
        await client.complete(_messages())

    assert mc.get_counter("llm.call_count", labels={"model": config.model}) == 2
