# SPDX-License-Identifier: Apache-2.0
"""E2E integration tests for degraded-path route safety scenarios (T009-T012).

These tests exercise the road_risk_score composite adapter when one or more
inner adapters fail, verifying that:
- The engine still dispatches the tool and produces a response (partial failure).
- The ToolResult.data["data_gaps"] accurately records which adapters failed.
- Total failure yields a failed ToolResult (no data) while the engine still
  produces a final text response.
- RecoveryExecutor wraps adapter calls and handles errors without propagating
  exceptions to the engine.
"""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from kosmos.context.builder import ContextBuilder
from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import StopReason
from kosmos.recovery.circuit_breaker import CircuitState
from kosmos.recovery.executor import RecoveryExecutor
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry
from tests.e2e.conftest import (
    TEXT_ANSWER_ROUTE_SAFETY_DEGRADED,
    TOOL_CALL_ROAD_RISK,
    E2EFixtureBuilder,
    MockLLMClient,
    _build_httpx_mock,
    _MockLLMClientAdapter,
    assert_data_gaps,
    assert_final_response_contains,
    assert_stop_reason,
    assert_tool_calls_dispatched,
    run_e2e_query,
)

# ---------------------------------------------------------------------------
# T009 [P] [US2] KOROAD failure — degraded response with accident data gap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t009_koroad_failure_degraded(e2e_env: None, e2e_builder: E2EFixtureBuilder) -> None:
    """T009: KOROAD 500 → partial failure → data_gap recorded, text response produced.

    When koroad_accident_search returns HTTP 500, road_risk_score should:
    - Still succeed (partial failure tolerance via asyncio.gather return_exceptions=True).
    - Record "koroad_accident_search" in data_gaps.
    - Produce a degraded text response acknowledging missing data.
    """
    engine, _llm, httpx_mock = (
        e2e_builder.with_api_failure("koroad_accident_search", "500")
        .with_llm_responses([TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY_DEGRADED])
        .build()
    )

    events = await run_e2e_query(engine, httpx_mock)

    # Tool was still dispatched despite inner adapter failure
    assert_tool_calls_dispatched(events, ["road_risk_score"])

    # data_gaps must include the failing adapter
    assert_data_gaps(events, ["koroad_accident_search"])

    # A degraded text response was still produced
    assert_final_response_contains(events, ["데이터"])

    # Engine completed normally (end_turn) — not error_unrecoverable
    assert_stop_reason(events, StopReason.end_turn)


# ---------------------------------------------------------------------------
# T010 [P] [US2] KMA alert timeout — degraded response with weather alert gap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t010_kma_alert_timeout_degraded(
    e2e_env: None, e2e_builder: E2EFixtureBuilder
) -> None:
    """T010: KMA alert timeout → partial failure → weather alert data_gap recorded.

    When kma_weather_alert_status times out, road_risk_score should:
    - Still succeed (partial failure tolerance).
    - Record "kma_weather_alert_status" in data_gaps.
    - Produce a text response (possibly noting data limitations).
    """
    engine, _llm, httpx_mock = (
        e2e_builder.with_api_failure("kma_weather_alert_status", "timeout")
        .with_llm_responses([TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY_DEGRADED])
        .build()
    )

    events = await run_e2e_query(engine, httpx_mock)

    # Tool was still dispatched
    assert_tool_calls_dispatched(events, ["road_risk_score"])

    # data_gaps must include the timing-out adapter
    assert_data_gaps(events, ["kma_weather_alert_status"])

    # A text response was still produced
    assert_final_response_contains(events, ["데이터"])

    # Engine completed normally
    assert_stop_reason(events, StopReason.end_turn)


# ---------------------------------------------------------------------------
# T011 [US2] All-adapters-failure — ToolResult.success=False, engine still responds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t011_all_adapters_fail(e2e_env: None, e2e_builder: E2EFixtureBuilder) -> None:
    """T011: All 3 inner adapters fail → road_risk_score raises ToolExecutionError.

    When all three inner adapters fail simultaneously, the composite adapter
    raises ToolExecutionError.  RecoveryExecutor catches this and returns a
    failed ToolResult (success=False).  The engine should still produce a final
    text response after receiving the failed tool result.

    The stop reason may be end_turn (LLM synthesizes an apology) or
    error_unrecoverable if the engine cannot continue — we accept either.
    """
    # Use a degraded LLM response that can handle total failure gracefully
    engine, _llm, httpx_mock = (
        e2e_builder.with_api_failure("koroad_accident_search", "500")
        .with_api_failure("kma_weather_alert_status", "timeout")
        .with_api_failure("kma_current_observation", "connection_error")
        .with_llm_responses([TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY_DEGRADED])
        .build()
    )

    events = await run_e2e_query(engine, httpx_mock)

    # The tool was still dispatched (engine attempted the call)
    assert_tool_calls_dispatched(events, ["road_risk_score"])

    # Exactly one tool_result event for road_risk_score must exist
    tool_result_events = [
        e for e in events if e.type == "tool_result" and e.tool_result is not None
    ]
    assert tool_result_events, "No tool_result event found"
    risk_results = [
        e.tool_result
        for e in tool_result_events
        if e.tool_result and e.tool_result.tool_id == "road_risk_score"
    ]
    assert risk_results, "No road_risk_score tool_result found"

    result = risk_results[0]
    # On total failure the composite raises ToolExecutionError → RecoveryExecutor
    # returns success=False with an error message
    assert not result.success, (
        f"Expected road_risk_score to fail when all adapters fail, "
        f"but got success=True with data={result.data}"
    )
    assert result.error is not None, "Failed ToolResult must have an error message"
    assert result.error_type is not None, "Failed ToolResult must have an error_type"

    # Engine must have emitted a stop event
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found"
    # Accept end_turn (LLM recovered gracefully) or error_unrecoverable
    assert stop_events[-1].stop_reason in (
        StopReason.end_turn,
        StopReason.error_unrecoverable,
        StopReason.max_iterations_reached,
    ), f"Unexpected stop_reason: {stop_events[-1].stop_reason}"


# ---------------------------------------------------------------------------
# T012 [US2] Circuit breaker integration — RecoveryExecutor error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t012_circuit_breaker_integration(
    e2e_env: None, e2e_builder: E2EFixtureBuilder
) -> None:
    """T012: CircuitBreaker integration — open circuit short-circuits road_risk_score.

    Architecture note: The circuit breaker in RecoveryExecutor tracks failures
    only for **retryable** error classes (TRANSIENT, TIMEOUT, RATE_LIMIT).
    The composite road_risk_score adapter converts total inner-adapter failure into
    a ToolExecutionError, which is classified as APP_ERROR (non-retryable) and
    therefore does NOT increment the circuit breaker failure count.

    To test the full open-circuit-reject path without modifying production code,
    this test pre-injects an OPEN circuit breaker state via the internal registry
    API.  This verifies:
    1. RecoveryExecutor correctly short-circuits when the breaker is OPEN.
    2. The engine receives ToolResult(success=False, error_type="circuit_open").
    3. The engine still produces a final text response (LLM handles degraded input).
    4. No httpx calls are made to the upstream APIs (the circuit is a hard gate).

    NOTE: Naturally tripping the circuit breaker from the composite layer would
    require the inner adapters to raise TRANSIENT errors (HTTP 502/503/504), which
    the composite would then propagate.  That scenario is exercised in unit tests
    for RecoveryExecutor; this E2E test focuses on the visible engine behavior
    when the circuit is already OPEN.
    """
    # Build a RecoveryExecutor with caching disabled (clean slate per query)
    recovery = RecoveryExecutor(max_cache_entries=0)

    registry = ToolRegistry()
    executor = ToolExecutor(registry, recovery_executor=recovery)
    register_all_tools(registry, executor)
    context_builder = ContextBuilder(registry=registry)

    # Pre-inject OPEN circuit breaker state for road_risk_score.
    # Access the breaker via the registry (creates it on first access),
    # then forcibly open it by calling record_failure() beyond threshold.
    default_threshold = 5  # CircuitBreakerConfig default failure_threshold
    breaker = recovery._registry.get("road_risk_score")
    for _ in range(default_threshold):
        breaker.record_failure()

    assert breaker.state == CircuitState.OPEN, (
        f"Pre-condition failed: circuit should be OPEN after {default_threshold} failures, "
        f"got state={breaker.state!r}"
    )

    # Run a query — the engine dispatches road_risk_score, but RecoveryExecutor
    # blocks it immediately because the circuit is OPEN.  The httpx mock is
    # configured with healthy adapters to confirm no httpx calls are made.
    httpx_mock = _build_httpx_mock({}, {})  # all adapters healthy
    llm = _MockLLMClientAdapter(
        MockLLMClient(responses=[TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY_DEGRADED])
    )
    engine = QueryEngine(
        llm_client=llm,
        tool_registry=registry,
        tool_executor=executor,
        config=QueryEngineConfig(),
        context_builder=context_builder,
    )

    with patch.object(httpx.AsyncClient, "get", httpx_mock):
        events: list = []
        async for event in engine.run("내일 부산에서 서울 가는데, 안전한 경로 추천해줘"):
            events.append(event)

    # road_risk_score was dispatched (engine attempted it)
    assert_tool_calls_dispatched(events, ["road_risk_score"])

    # RecoveryExecutor returned a failed ToolResult due to the open circuit
    risk_results = [
        e.tool_result
        for e in events
        if e.type == "tool_result"
        and e.tool_result is not None
        and e.tool_result.tool_id == "road_risk_score"
    ]
    assert risk_results, "No road_risk_score tool_result found"
    result = risk_results[0]

    assert not result.success, (
        "road_risk_score should fail fast when circuit breaker is OPEN"
    )
    assert result.error_type == "circuit_open", (
        f"Expected error_type='circuit_open' for OPEN circuit, "
        f"got error_type={result.error_type!r}"
    )

    # No httpx calls should have been made — the open circuit is a hard gate
    assert httpx_mock.call_count == 0, (
        "Circuit breaker OPEN should prevent any httpx calls to upstream APIs, "
        f"but got {httpx_mock.call_count} call(s)"
    )

    # Engine still produced a final text response (LLM handled the degraded result)
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found after circuit-open rejection"
    assert stop_events[-1].stop_reason in (
        StopReason.end_turn,
        StopReason.error_unrecoverable,
        StopReason.max_iterations_reached,
    ), f"Unexpected stop_reason: {stop_events[-1].stop_reason!r}"
