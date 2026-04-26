# SPDX-License-Identifier: Apache-2.0
"""Live observability pipeline verification tests for KOSMOS.

Covers Epic #380 (spec 018, User Story 2): validates that ``MetricsCollector``
and ``ObservabilityEventLogger`` wire correctly through the tool executor and
``LLMClient`` when driven by real KOROAD and FriendliAI traffic.

Prerequisites
-------------
* ``KOSMOS_FRIENDLI_TOKEN`` — FriendliAI Serverless API token
* ``KOSMOS_DATA_GO_KR_API_KEY`` — data.go.kr shared API key (KOROAD)

Both variables are validated by the session-scoped ``friendli_token`` and
``koroad_api_key`` fixtures in ``tests/live/conftest.py``, which call
``pytest.fail()`` when unset.  There is no silent skip or xfail behaviour.

Run this suite with::

    uv run pytest tests/live/test_live_observability.py -m live -v

EVENT-NAME / METRIC-NAME RESOLUTION
------------------------------------
The spec contract uses abstract wire names (``tool.call.started``,
``tool.call.completed``, ``llm.stream.started``, ``llm.stream.completed``).
The real Python implementation differs:

Event types (``src/kosmos/observability/events.py``):
  - ``"tool_call"`` — ONE event per ``ToolExecutor.dispatch()`` call,
    emitted in the ``finally`` block after the call completes (AC-A6).
    There are NO separate start/end pair events.
  - ``"llm_call"``  — ONE event per ``LLMClient.complete()`` or
    ``LLMClient.stream()`` call, emitted by ``_metrics_record_call()``.
    Again no start/end pair.

Metric names (``src/kosmos/tools/executor.py``,
             ``src/kosmos/llm/client.py``):
  - ``tool.call_count``   — labelled ``{tool_id=<name>}``  (NOT ``tool.calls.total``)
  - ``tool.duration_ms``  — labelled ``{tool_id=<name>}``  (NOT ``tool.latency_ms``)
  - ``llm.call_count``    — labelled ``{model=<model>}``   (NOT ``llm.requests.total``)
  - ``llm.call_duration_ms`` — labelled ``{model=<model>}`` (NOT ``llm.tokens.prompt`` etc.)

Note: the LLM client does NOT record token-count histograms.  The spec
assertion "``llm.tokens.prompt`` has ≥1 sample > 0" is therefore adapted
to "``llm.call_duration_ms`` has ≥1 sample > 0" — which is what the real
code writes.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from kosmos.llm.client import LLMClient
from kosmos.llm.models import ChatMessage
from kosmos.observability.event_logger import ObservabilityEventLogger
from kosmos.observability.metrics import MetricsCollector
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_TOOL_ID = "koroad_accident_search"

_KOROAD_ARGS_JSON = json.dumps(
    {
        "search_year_cd": "2025119",  # SearchYearCd.GENERAL_2024
        "si_do": 11,  # SidoCode.SEOUL
        "gu_gun": 680,  # GugunCode.SEOUL_GANGNAM
        "num_of_rows": 1,
        "page_no": 1,
    }
)


def _build_executor(
    *,
    metrics: MetricsCollector | None = None,
    event_logger: ObservabilityEventLogger | None = None,
) -> ToolExecutor:
    """Return a minimal ToolExecutor wired with only the KOROAD tool."""
    from kosmos.tools.koroad.koroad_accident_search import register as reg_koroad

    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry, metrics=metrics, event_logger=event_logger)
    reg_koroad(registry, executor)
    return executor


class _InMemoryLogHandler(logging.Handler):
    """Logging handler that collects all emitted JSON records in memory."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = json.loads(self.formatMessage(record))
            self.records.append(payload)
        except (json.JSONDecodeError, ValueError):
            pass

    def formatMessage(self, record: logging.LogRecord) -> str:  # noqa: N802
        return record.getMessage()


def _attach_capture_handler(logger_name: str = "kosmos.events") -> _InMemoryLogHandler:
    """Attach an in-memory handler to *logger_name* and return it.

    Captures the prior logger level on the handler so ``_detach_handler`` can
    restore it — preventing cross-test leakage when the full live suite runs
    in a single process.
    """
    target = logging.getLogger(logger_name)
    handler = _InMemoryLogHandler()
    handler._prior_level = target.level  # type: ignore[attr-defined]
    handler._logger_name = logger_name  # type: ignore[attr-defined]
    target.addHandler(handler)
    target.setLevel(logging.DEBUG)
    return handler


def _detach_handler(handler: _InMemoryLogHandler, logger_name: str = "kosmos.events") -> None:
    """Remove *handler* and restore the logger's prior level."""
    target = logging.getLogger(logger_name)
    target.removeHandler(handler)
    prior_level = getattr(handler, "_prior_level", logging.NOTSET)
    target.setLevel(prior_level)


# ---------------------------------------------------------------------------
# T012 — MetricsCollector under live tool call
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_metrics_collector_under_live_tool_call(
    koroad_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify MetricsCollector records a counter and duration histogram for one real
    KOROAD accident-search call routed through ToolExecutor.

    Metric-name mapping (spec → real):
      ``tool.calls.total``  → ``tool.call_count`` labelled {tool_id=koroad_accident_search}
      ``tool.latency_ms``   → ``tool.duration_ms`` labelled {tool_id=koroad_accident_search}

    Both counters are incremented once per dispatch() call.  The duration
    histogram receives exactly one positive-value sample per successful call.
    """
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", koroad_api_key)

    collector = MetricsCollector()
    executor = _build_executor(metrics=collector)

    labels = {"tool_id": _TOOL_ID}

    # --- Pre-call snapshot ---
    pre_count = collector.get_counter("tool.call_count", labels=labels)
    pre_hist = collector.get_histogram_stats("tool.duration_ms", labels=labels)
    pre_samples = int(pre_hist["count"])

    # --- Act: one real KOROAD call ---
    result = await executor.dispatch(_TOOL_ID, _KOROAD_ARGS_JSON)

    # --- Post-call snapshot ---
    post_count = collector.get_counter("tool.call_count", labels=labels)
    post_hist = collector.get_histogram_stats("tool.duration_ms", labels=labels)
    post_samples = int(post_hist["count"])

    # Structural assertions (counter delta, histogram positivity)
    assert post_count - pre_count == 1, (
        f"tool.call_count delta should be 1, got {post_count - pre_count}. "
        f"ToolResult.success={result.success}, error={result.error!r}"
    )
    delta_samples = post_samples - pre_samples
    assert delta_samples >= 1, (
        f"tool.duration_ms should have at least 1 new sample, got delta {delta_samples}"
    )
    assert post_hist["max"] > 0, (
        f"tool.duration_ms max value should be > 0 ms, got {post_hist['max']}"
    )


# ---------------------------------------------------------------------------
# T013 — MetricsCollector under live LLM stream
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_metrics_collector_under_live_llm_stream(
    friendli_token: str,
) -> None:
    """Verify MetricsCollector records a counter and duration histogram for one real
    FriendliAI EXAONE streaming completion via LLMClient.

    Metric-name mapping (spec → real):
      ``llm.requests.total``       → ``llm.call_count``      labelled {model=<model>}
      ``llm.tokens.prompt``        → ``llm.call_duration_ms`` labelled {model=<model>}
      ``llm.tokens.completion``    → (no token histogram exists; duration is the proxy)

    The LLMClient implementation (src/kosmos/llm/client.py) does NOT record
    per-token histograms — it records call count and call duration only.
    Both are asserted here as counter delta ≥ 1 and duration > 0.
    """
    collector = MetricsCollector()

    messages = [ChatMessage(role="user", content="한 단어로 응답해주세요: 안녕")]

    async with LLMClient(metrics=collector) as client:
        model_label = {"model": client._config.model}

        # --- Pre-call snapshot ---
        pre_count = collector.get_counter("llm.call_count", labels=model_label)
        pre_hist = collector.get_histogram_stats("llm.call_duration_ms", labels=model_label)
        pre_samples = int(pre_hist["count"])

        # --- Act: consume the full stream ---
        async for _ in client.stream(messages, max_tokens=512):
            pass

        # --- Post-call snapshot ---
        post_count = collector.get_counter("llm.call_count", labels=model_label)
        post_hist = collector.get_histogram_stats("llm.call_duration_ms", labels=model_label)
        post_samples = int(post_hist["count"])

    assert post_count - pre_count >= 1, (
        f"llm.call_count delta should be ≥ 1, got {post_count - pre_count}"
    )
    assert post_samples - pre_samples >= 1, (
        f"llm.call_duration_ms should have ≥ 1 new sample, got delta {post_samples - pre_samples}"
    )
    assert post_hist["max"] > 0, (
        f"llm.call_duration_ms max value should be > 0 ms, got {post_hist['max']}"
    )


# ---------------------------------------------------------------------------
# T014 — ObservabilityEventLogger emits tool events
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_event_logger_emits_tool_events(
    koroad_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ObservabilityEventLogger emits a valid 'tool_call' event for one real
    KOROAD call through ToolExecutor.

    Event-type mapping (spec → real):
      ``tool.call.started``   → no separate start event; the real code emits ONE
      ``tool.call.completed`` → 'tool_call' event in the finally block of dispatch()
                                 with success=True and duration_ms > 0

    Captured via a custom logging.Handler attached to the 'kosmos.events' logger,
    which is the backing logger for ObservabilityEventLogger.  The handler receives
    log records whose message is the JSON-serialised ObservabilityEvent.

    Schema fields asserted per contracts/test-interfaces.md:
      - event_type == "tool_call"
      - tool_id is a non-empty string (tool identifier)
      - duration_ms is a non-negative float
      - success field is populated (bool)
    """
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", koroad_api_key)

    event_logger = ObservabilityEventLogger()
    handler = _attach_capture_handler()

    try:
        executor = _build_executor(event_logger=event_logger)

        # --- Act ---
        result = await executor.dispatch(_TOOL_ID, _KOROAD_ARGS_JSON)
    finally:
        _detach_handler(handler)

    tool_events = [r for r in handler.records if r.get("event_type") == "tool_call"]

    assert len(tool_events) >= 1, (
        f"Expected ≥1 tool_call event in 'kosmos.events' log, "
        f"got {len(tool_events)}. ToolResult.success={result.success}, error={result.error!r}. "
        f"All captured records: {handler.records!r}"
    )

    for evt in tool_events:
        # tool_id must be a non-empty string
        assert isinstance(evt.get("tool_id"), str) and evt["tool_id"], (
            f"tool_id must be a non-empty string, got {evt.get('tool_id')!r}"
        )
        # duration_ms must be a non-negative number
        dur = evt.get("duration_ms")
        assert isinstance(dur, (int, float)) and dur >= 0, (
            f"duration_ms must be a non-negative number, got {dur!r}"
        )
        # success field must be present and be a bool
        assert "success" in evt, f"'success' field missing from tool_call event: {evt!r}"
        assert isinstance(evt["success"], bool), (
            f"'success' must be bool, got {type(evt['success'])!r}: {evt!r}"
        )


# ---------------------------------------------------------------------------
# T015 — ObservabilityEventLogger emits LLM events
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_event_logger_emits_llm_events(
    friendli_token: str,
) -> None:
    """Verify ObservabilityEventLogger emits a valid 'llm_call' event for one real
    FriendliAI EXAONE streaming completion.

    Event-type mapping (spec → real):
      ``llm.stream.started``   → no separate start event; the real code emits ONE
      ``llm.stream.completed`` → 'llm_call' event via LLMClient._metrics_record_call()
                                  called when the 'done' SSE event is received

    Schema fields asserted per contracts/test-interfaces.md (adapted to real model):
      - event_type == "llm_call"
      - success field is populated (bool)
      - duration_ms is a non-negative float
    """
    event_logger = ObservabilityEventLogger()
    handler = _attach_capture_handler()

    messages = [ChatMessage(role="user", content="한 단어로 응답해주세요: 안녕")]

    try:
        async with LLMClient(event_logger=event_logger) as client:
            async for _ in client.stream(messages, max_tokens=512):
                pass
    finally:
        _detach_handler(handler)

    llm_events = [r for r in handler.records if r.get("event_type") == "llm_call"]

    assert len(llm_events) >= 1, (
        f"Expected ≥1 llm_call event in 'kosmos.events' log, "
        f"got {len(llm_events)}. All captured records: {handler.records!r}"
    )

    for evt in llm_events:
        # success field must be present and be a bool
        assert "success" in evt, f"'success' field missing from llm_call event: {evt!r}"
        assert isinstance(evt["success"], bool), (
            f"'success' must be bool, got {type(evt['success'])!r}: {evt!r}"
        )
        # duration_ms must be a non-negative number when present
        if "duration_ms" in evt and evt["duration_ms"] is not None:
            dur = evt["duration_ms"]
            assert isinstance(dur, (int, float)) and dur >= 0, (
                f"duration_ms must be non-negative, got {dur!r}"
            )
        # event_type must be exactly "llm_call"
        assert evt["event_type"] == "llm_call", (
            f"Expected event_type='llm_call', got {evt['event_type']!r}"
        )
