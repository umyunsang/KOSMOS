# SPDX-License-Identifier: Apache-2.0
"""T022 — Tests for the 429 retry counter and chat span uniqueness.

Verifies:
- kosmos_llm_rate_limit_retries_total increments exactly once per retry
  (two 429 → two increments).
- Exactly one 'chat' span is emitted for the whole logical stream call
  regardless of how many retry attempts are made.
- The single 'chat' span has gen_ai.usage.input_tokens set on success.
- No metric increment occurs when self._metrics is None (None-guard works).

Strategy: monkeypatch kosmos.llm.client._tracer with a dedicated
TracerProvider backed by InMemorySpanExporter (same pattern as
test_query_parent_span.py / test_tool_execute_span.py). Use respx to
mock httpx at the transport level so no real network calls are made.
asyncio.sleep is monkeypatched to a no-op so tests stay under 3s.

Two 429 paths exist in _stream_with_retry:
  1. Pre-stream 429 — response.status_code == 429 before reading SSE lines.
  2. Mid-stream 429 — an SSE line that matches _is_rate_limit_envelope().
Both are tested independently below.
"""

from __future__ import annotations

import json
import os

import httpx
import pytest
import respx
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kosmos.llm.client import LLMClient
from kosmos.llm.config import LLMClientConfig
from kosmos.llm.models import ChatMessage
from kosmos.observability.metrics import MetricsCollector

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_COMPLETIONS_URL = "https://api.friendli.ai/serverless/v1/chat/completions"
_MODEL = "LGAI-EXAONE/EXAONE-236B-A23B"

# ---------------------------------------------------------------------------
# SSE body helpers (mirrors test_streaming.py conventions)
# ---------------------------------------------------------------------------


def _delta_chunk(content: str) -> dict:
    return {
        "id": "chatcmpl-t022",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}],
    }


def _stop_chunk(prompt_tokens: int = 12, completion_tokens: int = 4) -> dict:
    return {
        "id": "chatcmpl-t022",
        "object": "chat.completion.chunk",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _sse_body(*chunks: dict, done: bool = True) -> bytes:
    lines = [f"data: {json.dumps(c)}\n\n" for c in chunks]
    if done:
        lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()


def _sse_response(body: bytes, status: int = 200) -> httpx.Response:
    return httpx.Response(
        status,
        content=body,
        headers={"content-type": "text/event-stream"},
    )


def _sse_rate_limit_envelope() -> str:
    """A single SSE data line containing a mid-stream 429 error envelope."""
    payload = {"error": {"status": 429, "type": "rate_limited", "message": "rate limit hit"}}
    return f"data: {json.dumps(payload)}\n\n"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Strip KOSMOS_ env vars and inject a known test token."""
    for key in list(os.environ):
        if key.startswith("KOSMOS_"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("KOSMOS_FRIENDLI_TOKEN", "test-token-t022")
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)


@pytest.fixture()
def mem_exporter(monkeypatch: pytest.MonkeyPatch) -> InMemorySpanExporter:
    """Patch kosmos.llm.client._tracer with a dedicated in-memory TracerProvider."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    import kosmos.llm.client as client_mod

    monkeypatch.setattr(client_mod, "_tracer", provider.get_tracer("kosmos.llm.client"))

    exporter.clear()
    return exporter


@pytest.fixture()
def sample_messages() -> list[ChatMessage]:
    return [ChatMessage(role="user", content="test message")]


@pytest.fixture()
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace asyncio.sleep with a no-op to keep tests fast."""

    async def _noop(delay: float) -> None:  # noqa: ARG001
        pass

    monkeypatch.setattr("asyncio.sleep", _noop)


# ---------------------------------------------------------------------------
# T022-A: pre-stream 429 × 2, then succeed — counter = 2, spans = 1
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_prestream_429_counter_and_single_chat_span(
    mem_exporter: InMemorySpanExporter,
    sample_messages: list[ChatMessage],
    no_sleep: None,
) -> None:
    """Pre-stream 429 twice then success: counter incremented exactly twice,
    exactly one 'chat' span exported."""
    success_body = _sse_body(_delta_chunk("hi"), _stop_chunk())

    respx.post(_COMPLETIONS_URL).mock(
        side_effect=[
            # attempt 0 → 429
            _sse_response(b"rate limited", status=429),
            # attempt 1 → 429
            _sse_response(b"rate limited", status=429),
            # attempt 2 → success
            _sse_response(success_body),
        ]
    )

    config = LLMClientConfig()
    metrics = MetricsCollector()
    client = LLMClient(config=config, metrics=metrics)

    # max_retries default is 3 → max_attempts = 4; two 429s + one success is fine.
    events = []
    async for event in client.stream(sample_messages):
        events.append(event)

    await client.close()

    # --- Assertion 1: counter incremented exactly 2 times ---
    count = metrics.get_counter(
        "kosmos_llm_rate_limit_retries_total",
        labels={"provider": "friendliai", "model": _MODEL},
    )
    assert count == 2, (
        f"Expected retry counter == 2 (one per 429 retry), got {count}. "
        f"Counters snapshot: {metrics.snapshot()['counters']}"
    )

    # --- Assertion 2: exactly one 'chat' span ---
    spans = mem_exporter.get_finished_spans()
    chat_spans = [s for s in spans if s.name == "chat"]
    assert len(chat_spans) == 1, (
        f"Expected exactly 1 'chat' span regardless of retry count, "
        f"got {len(chat_spans)}. All spans: {[s.name for s in spans]}"
    )

    # --- Assertion 3: span has input_tokens > 0 ---
    attrs = dict(chat_spans[0].attributes or {})
    input_tokens = attrs.get("gen_ai.usage.input_tokens", 0)
    assert int(input_tokens) > 0, (
        f"Expected gen_ai.usage.input_tokens > 0 on success path. attrs: {attrs}"
    )


# ---------------------------------------------------------------------------
# T022-B: mid-stream 429 × 2, then succeed — counter = 2, spans = 1
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_midstream_429_counter_and_single_chat_span(
    mem_exporter: InMemorySpanExporter,
    sample_messages: list[ChatMessage],
    no_sleep: None,
) -> None:
    """Mid-stream 429 envelope twice then success: counter incremented exactly twice,
    exactly one 'chat' span exported.

    Mid-stream 429 is detected by _is_rate_limit_envelope() inside the SSE line
    iteration loop. We inject a 200 response whose body contains a 429 error
    envelope line followed by no [DONE], causing the retry logic to kick in.
    """
    # A body that begins streaming normally, then hits a rate-limit envelope.
    mid_stream_429_body = (
        f"data: {json.dumps(_delta_chunk('partial'))}\n\n" + _sse_rate_limit_envelope()
    ).encode()

    success_body = _sse_body(_delta_chunk("done"), _stop_chunk())

    respx.post(_COMPLETIONS_URL).mock(
        side_effect=[
            # attempt 0 → mid-stream 429 envelope
            _sse_response(mid_stream_429_body),
            # attempt 1 → mid-stream 429 envelope again
            _sse_response(mid_stream_429_body),
            # attempt 2 → clean success
            _sse_response(success_body),
        ]
    )

    config = LLMClientConfig()
    metrics = MetricsCollector()
    client = LLMClient(config=config, metrics=metrics)

    events = []
    async for event in client.stream(sample_messages):
        events.append(event)

    await client.close()

    # --- Assertion 1: counter incremented exactly 2 times ---
    count = metrics.get_counter(
        "kosmos_llm_rate_limit_retries_total",
        labels={"provider": "friendliai", "model": _MODEL},
    )
    assert count == 2, (
        f"Expected retry counter == 2 for mid-stream retries, got {count}. "
        f"Counters snapshot: {metrics.snapshot()['counters']}"
    )

    # --- Assertion 2: exactly one 'chat' span ---
    spans = mem_exporter.get_finished_spans()
    chat_spans = [s for s in spans if s.name == "chat"]
    assert len(chat_spans) == 1, (
        f"Expected exactly 1 'chat' span, got {len(chat_spans)}. "
        f"All spans: {[s.name for s in spans]}"
    )


# ---------------------------------------------------------------------------
# T022-C: metrics=None — no increment, no crash
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_no_metrics_increment_when_metrics_is_none(
    mem_exporter: InMemorySpanExporter,
    sample_messages: list[ChatMessage],
    no_sleep: None,
) -> None:
    """When LLMClient is initialized without a MetricsCollector (metrics=None),
    a 429 retry must not raise and the stream must still complete successfully."""
    success_body = _sse_body(_delta_chunk("hello"), _stop_chunk())

    respx.post(_COMPLETIONS_URL).mock(
        side_effect=[
            _sse_response(b"rate limited", status=429),
            _sse_response(success_body),
        ]
    )

    config = LLMClientConfig()
    # Explicitly pass metrics=None — the None guard in _stream_with_retry must handle this.
    client = LLMClient(config=config, metrics=None)

    events = []
    async for event in client.stream(sample_messages):
        events.append(event)

    await client.close()

    # Stream must complete — at least one done event.
    done_events = [e for e in events if e.type == "done"]
    assert len(done_events) == 1, (
        f"Expected stream to complete with one 'done' event, got: {[e.type for e in events]}"
    )

    # Exactly one chat span still emitted.
    spans = mem_exporter.get_finished_spans()
    chat_spans = [s for s in spans if s.name == "chat"]
    assert len(chat_spans) == 1, (
        f"Expected 1 'chat' span even with metrics=None. All spans: {[s.name for s in spans]}"
    )
