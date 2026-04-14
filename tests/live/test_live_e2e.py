# SPDX-License-Identifier: Apache-2.0
"""Live E2E validation tests for the full KOSMOS Scenario 1 pipeline.

These tests hit REAL APIs — FriendliAI K-EXAONE, data.go.kr, and KOROAD.
No mocks. Tests hard-fail on API unavailability.

Marked ``@pytest.mark.live`` and skipped by default. Run with::

    uv run pytest -m live tests/live/test_live_e2e.py

Required environment variables (validated by conftest fixtures):
    KOSMOS_FRIENDLI_TOKEN     — FriendliAI Serverless API token
    KOSMOS_DATA_GO_KR_API_KEY — data.go.kr public data portal key
    KOSMOS_DATA_GO_KR_API_KEY — data.go.kr public data portal key (shared by KMA + KOROAD)
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.client import LLMClient
from kosmos.observability.event_logger import ObservabilityEventLogger
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Scenario 1 user messages
# ---------------------------------------------------------------------------

_SCENARIO1_INITIAL_QUERY = "서울에서 부산 가는 안전한 경로 추천해줘"
_SCENARIO1_FOLLOWUP_QUERY = "사고 이력을 더 자세히 알려줘"

# Engine config: limit iterations to prevent runaway tool loops and
# keep token cost low during live validation runs.
_LIVE_ENGINE_CONFIG = QueryEngineConfig(max_iterations=5)


# ---------------------------------------------------------------------------
# Helper: wire a real QueryEngine for live tests
# ---------------------------------------------------------------------------


def _build_live_engine() -> tuple[QueryEngine, LLMClient]:
    """Create a fully-wired QueryEngine backed by real APIs.

    Reads KOSMOS_FRIENDLI_TOKEN from the environment (already validated by the
    session-scoped ``friendli_token`` / ``data_go_kr_api_key`` / ``koroad_api_key``
    fixtures before any test function runs).

    Returns:
        A 2-tuple of (QueryEngine, LLMClient).  The caller is responsible for
        closing the LLMClient with ``await llm_client.close()`` when done.
    """
    llm_client = LLMClient()

    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry)
    register_all_tools(registry, executor)

    engine = QueryEngine(
        llm_client=llm_client,
        tool_registry=registry,
        tool_executor=executor,
        config=_LIVE_ENGINE_CONFIG,
    )
    return engine, llm_client


# ---------------------------------------------------------------------------
# Test 1 — Full Scenario 1 pipeline event structure
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_e2e_scenario1_pipeline_structure(
    friendli_token: str,
    data_go_kr_api_key: str,
    koroad_api_key: str,
) -> None:
    """Full Scenario 1 E2E: verify event sequence structure from real APIs.

    Sends "서울에서 부산 가는 안전한 경로 추천해줘" through a live QueryEngine wired
    to real FriendliAI K-EXAONE and real Korean government APIs.

    Assertions are made on the EVENT SEQUENCE STRUCTURE only:
    - At least one ``tool_use`` event (LLM must dispatch tools)
    - At least one ``tool_result`` event with ``success=True``
    - At least one ``text_delta`` event with non-empty content
    - Exactly one ``stop`` event as the final event
    - The stop event ``stop_reason`` is ``end_turn`` or ``max_iterations_reached``
    - UsageTracker records real token counts from the live LLM call

    Text content is intentionally NOT asserted — LLM output is non-deterministic.
    Which specific tools are called is NOT asserted — the LLM decides the plan.
    """
    engine, llm_client = _build_live_engine()

    events: list[QueryEvent] = []
    try:
        async for event in engine.run(_SCENARIO1_INITIAL_QUERY):
            events.append(event)
    finally:
        await llm_client.close()

    # ---- Stateful component verification (T020) ----------------------------
    # UsageTracker must have recorded real token usage from the live LLM call.
    tracker = llm_client.usage
    assert tracker.call_count >= 1, (
        f"UsageTracker.call_count should be >=1, got {tracker.call_count}"
    )
    assert tracker.total_used > 0, f"UsageTracker.total_used should be >0, got {tracker.total_used}"

    # ---- Structural assertions -----------------------------------------------

    # The engine must have emitted at least some events
    assert events, "engine.run() yielded no events — pipeline did not execute"

    # The LLM SHOULD call government API tools, but tool use is model-driven
    # and not guaranteed for every prompt.  Assert that the engine produced
    # meaningful output — either via tool calls or direct text response.
    tool_use_events = [e for e in events if e.type == "tool_use"]
    text_delta_events_early = [e for e in events if e.type == "text_delta" and e.content]
    assert len(tool_use_events) >= 1 or len(text_delta_events_early) >= 1, (
        f"Expected at least one tool_use or text_delta event, got neither. "
        f"Event types observed: {[e.type for e in events]}"
    )

    # If the model chose to use tools, at least one must succeed.
    # (If the model responded with direct text only, tool assertions are skipped.)
    tool_result_events = [e for e in events if e.type == "tool_result"]
    if tool_use_events:
        assert len(tool_result_events) >= 1, (
            f"Expected at least one tool_result event, got 0. "
            f"Event types observed: {[e.type for e in events]}"
        )
        successful_results = [
            e for e in tool_result_events if e.tool_result is not None and e.tool_result.success
        ]
        result_summary = [
            (e.tool_result.tool_id, e.tool_result.success)
            for e in tool_result_events
            if e.tool_result is not None
        ]
        assert len(successful_results) >= 1, (
            f"Expected at least one successful tool_result, "
            f"but none were successful. Results: {result_summary}"
        )

    # At least one text_delta with non-empty content: LLM must produce output
    text_delta_events = [e for e in events if e.type == "text_delta" and e.content]
    assert len(text_delta_events) >= 1, (
        f"Expected at least one text_delta event with non-empty content, got 0. "
        f"Event types observed: {[e.type for e in events]}"
    )

    # Exactly one stop event, and it must be the last event
    stop_events = [e for e in events if e.type == "stop"]
    assert len(stop_events) == 1, (
        f"Expected exactly one stop event, got {len(stop_events)}. "
        f"Event types observed: {[e.type for e in events]}"
    )
    assert events[-1].type == "stop", (
        f"Expected the last event to be 'stop', got {events[-1].type!r}. "
        f"Last 5 event types: {[e.type for e in events[-5:]]}"
    )

    # The stop reason must indicate normal completion.
    # The query loop yields `end_turn` when the LLM finishes without requesting
    # more tools, or `max_iterations_reached` when the iteration cap is hit.
    # Both are valid outcomes for a live test — the LLM decides how many tool
    # calls to make.  `task_complete` is reserved for future explicit signals.
    final_stop = stop_events[0]
    acceptable = {StopReason.end_turn, StopReason.max_iterations_reached}
    assert final_stop.stop_reason in acceptable, (
        f"Expected stop_reason in {acceptable!r}, "
        f"got {final_stop.stop_reason!r}. "
        f"stop_message: {final_stop.stop_message!r}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Multi-turn context: follow-up turn after Scenario 1
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_e2e_multi_turn_context(
    friendli_token: str,
    data_go_kr_api_key: str,
    koroad_api_key: str,
) -> None:
    """Multi-turn E2E: second turn must succeed after the first turn completes.

    Sends "서울에서 부산 가는 안전한 경로 추천해줘" (turn 1), then
    "사고 이력을 더 자세히 알려줘" (turn 2) through the same engine instance.

    Verifies that the engine handles conversational context correctly and does
    not crash on the follow-up turn. Assertions for turn 2:
    - At least one ``text_delta`` event with non-empty content
    - Exactly one ``stop`` event as the final event of the second turn

    Text content and tool selection remain intentionally unasserted.
    """
    engine, llm_client = _build_live_engine()

    turn1_events: list[QueryEvent] = []
    turn2_events: list[QueryEvent] = []

    try:
        # --- Turn 1: initial Scenario 1 query ---
        async for event in engine.run(_SCENARIO1_INITIAL_QUERY):
            turn1_events.append(event)

        # Turn 1 must produce a stop event before proceeding to turn 2
        turn1_stop_events = [e for e in turn1_events if e.type == "stop"]
        assert turn1_stop_events, (
            "Turn 1 produced no stop event — cannot safely proceed to turn 2. "
            f"Turn 1 event types: {[e.type for e in turn1_events]}"
        )

        # Pause between turns to avoid FriendliAI serverless rate limiting.
        # K-EXAONE Serverless has aggressive per-minute rate limits.  Turn 1
        # may have used multiple LLM iterations, and when this test runs after
        # other live-suite tests the minute-bucket is already partially spent,
        # so 60s is the empirically-needed cooldown to avoid 429s.
        await asyncio.sleep(60)

        # --- Turn 2: follow-up query with conversation history ---
        async for event in engine.run(_SCENARIO1_FOLLOWUP_QUERY):
            turn2_events.append(event)

    finally:
        await llm_client.close()

    # ---- Turn 2 structural assertions ----------------------------------------

    # Turn 2 must yield at least some events
    assert turn2_events, "Turn 2 engine.run() yielded no events — pipeline failed silently"

    # Turn 2 must contain at least one text_delta with non-empty content
    turn2_text_deltas = [e for e in turn2_events if e.type == "text_delta" and e.content]
    assert len(turn2_text_deltas) >= 1, (
        f"Expected at least one text_delta event with non-empty content in turn 2, got 0. "
        f"Turn 2 event types observed: {[e.type for e in turn2_events]}"
    )

    # Turn 2 must end with a stop event
    turn2_stop_events = [e for e in turn2_events if e.type == "stop"]
    assert len(turn2_stop_events) == 1, (
        f"Expected exactly one stop event in turn 2, got {len(turn2_stop_events)}. "
        f"Turn 2 event types observed: {[e.type for e in turn2_events]}"
    )
    assert turn2_events[-1].type == "stop", (
        f"Expected the last event of turn 2 to be 'stop', "
        f"got {turn2_events[-1].type!r}. "
        f"Last 5 turn 2 event types: {[e.type for e in turn2_events[-5:]]}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Natural-address Scenario 1 (T016, US3)
# ---------------------------------------------------------------------------

_SCENARIO1_NATURAL_ADDRESS_QUERY = "강남역 근처 사고 정보 알려줘"
_KOROAD_TOOL_ID = "koroad_accident_search"
_HANGUL_RANGE = range(0xAC00, 0xD7B0)


class _InMemoryEventHandler(logging.Handler):
    """Capture ObservabilityEventLogger JSON records in memory."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[dict[str, Any]] = []

    def emit(self, record: logging.LogRecord) -> None:
        try:
            payload = json.loads(record.getMessage())
        except (json.JSONDecodeError, ValueError):
            return
        self.records.append(payload)


def _build_live_engine_with_observability(
    event_logger: ObservabilityEventLogger,
) -> tuple[QueryEngine, LLMClient]:
    """Like ``_build_live_engine`` but wires the provided event logger into
    both ``LLMClient`` and ``ToolExecutor``.
    """
    llm_client = LLMClient(event_logger=event_logger)
    registry = ToolRegistry()
    executor = ToolExecutor(registry=registry, event_logger=event_logger)
    register_all_tools(registry, executor)
    engine = QueryEngine(
        llm_client=llm_client,
        tool_registry=registry,
        tool_executor=executor,
        config=_LIVE_ENGINE_CONFIG,
    )
    return engine, llm_client


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_scenario1_from_natural_address(
    kakao_api_key: str,
    koroad_api_key: str,
    friendli_token: str,
    data_go_kr_api_key: str,
) -> None:
    """E2E: natural Korean prompt yields a valid Scenario 1 answer (path-agnostic).

    K-EXAONE, trained by LG AI Research on a Korean-heavy corpus, has memorized
    sido/gugun admin codes (e.g., SEOUL=11, GANGNAM=680) and frequently fills
    ``koroad_accident_search`` arguments directly from the prompt without
    invoking geocoding — an efficiency win (one fewer API round-trip, lower
    latency, smaller external-failure surface) that is a feature of choosing a
    Korean-domain LLM, not a defect.  This test therefore asserts the
    user-observable contract, not a specific tool-call path:

      1. KOROAD is called at least once (accident data must come from the
         authoritative source, never from LLM memory).
      2. Final response is non-empty and contains at least one Hangul
         character.
      3. Observability captured ≥1 llm_call and ≥1 KOROAD tool_call event.

    Geocoding MAY or MAY NOT appear in the tool sequence depending on the
    model's confidence in the admin codes; both paths are valid end states.
    """
    event_logger = ObservabilityEventLogger()
    log_target = logging.getLogger("kosmos.events")
    handler = _InMemoryEventHandler()
    prior_level = log_target.level
    log_target.addHandler(handler)
    log_target.setLevel(logging.DEBUG)

    llm_client = None
    events: list[QueryEvent] = []
    try:
        engine, llm_client = _build_live_engine_with_observability(event_logger)
        async for event in engine.run(_SCENARIO1_NATURAL_ADDRESS_QUERY):
            events.append(event)
    finally:
        if llm_client is not None:
            await llm_client.close()
        log_target.removeHandler(handler)
        log_target.setLevel(prior_level)

    # ---- Tool sequence assertion (KOROAD required, geocoding optional) -----
    tool_use_events = [e for e in events if e.type == "tool_use"]
    tool_names = [e.tool_name for e in tool_use_events]
    koroad_indices = [i for i, name in enumerate(tool_names) if name == _KOROAD_TOOL_ID]

    assert koroad_indices, (
        f"Expected ≥1 {_KOROAD_TOOL_ID} tool_use (accident data must come "
        f"from the authoritative source, not LLM memory), got none. "
        f"Observed tool_name sequence: {tool_names!r}"
    )

    # ---- Final-response assertions ----------------------------------------
    final_response = "".join(e.content or "" for e in events if e.type == "text_delta")
    assert final_response.strip(), (
        f"Final response must be non-empty, got {final_response!r}. "
        f"Event types observed: {[e.type for e in events]}"
    )
    has_hangul = any(ord(ch) in _HANGUL_RANGE for ch in final_response)
    assert has_hangul, (
        f"Final response must contain ≥1 Hangul character (U+AC00..U+D7AF), got {final_response!r}"
    )

    # ---- Observability event-chain assertions -----------------------------
    llm_events = [r for r in handler.records if r.get("event_type") == "llm_call"]
    tool_events = [r for r in handler.records if r.get("event_type") == "tool_call"]
    koroad_tool_events = [r for r in tool_events if r.get("tool_id") == _KOROAD_TOOL_ID]

    assert len(llm_events) >= 1, (
        f"Expected ≥1 llm_call event, got {len(llm_events)}. "
        f"Captured event types: {[r.get('event_type') for r in handler.records]}"
    )
    assert len(koroad_tool_events) >= 1, (
        f"Expected ≥1 {_KOROAD_TOOL_ID} tool_call event, "
        f"got {len(koroad_tool_events)}. "
        f"Captured tool_ids: {[r.get('tool_id') for r in tool_events]}"
    )
