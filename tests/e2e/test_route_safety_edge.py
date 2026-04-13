# SPDX-License-Identifier: Apache-2.0
"""Edge-case E2E tests for the KOSMOS query engine (T018-T022).

Tests cover:
- T018: Unknown tool call handling
- T019: Max iterations guard
- T020: LLM stream interruption with retry
- T021: Invalid tool arguments (Pydantic validation failure)
- T022: Preprocessing pipeline with small context window
"""

from __future__ import annotations

import json
from unittest.mock import patch

import httpx
import pytest

from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.events import StopReason
from kosmos.llm.errors import StreamInterruptedError
from kosmos.llm.models import StreamEvent, TokenUsage
from tests.e2e.conftest import (
    TEXT_ANSWER_ROUTE_SAFETY,
    TOOL_CALL_ROAD_RISK,
    E2EFixtureBuilder,
    assert_stop_reason,
    run_e2e_query,
)

# ---------------------------------------------------------------------------
# Shared StreamEvent sequences for edge-case tests
# ---------------------------------------------------------------------------

# T018: LLM requests a tool that is not registered
_UNKNOWN_TOOL_CALL: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_unk_001",
        function_name="nonexistent_magic_tool",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta="{}",
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=80, output_tokens=30),
    ),
    StreamEvent(type="done"),
]

# T019: Tool call that repeats every iteration (never yields text)
# The engine's max_iterations guard must stop the loop.
_INFINITE_TOOL_CALL: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_inf_001",
        function_name="road_risk_score",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        function_args_delta=json.dumps({"si_do": 11, "nx": 61, "ny": 126}),
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=100, output_tokens=40),
    ),
    StreamEvent(type="done"),
]

# T021: road_risk_score called with wrong arguments (missing required fields)
_INVALID_ARGS_TOOL_CALL: list[StreamEvent] = [
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id="call_invalid_001",
        function_name="road_risk_score",
        function_args_delta=None,
    ),
    StreamEvent(
        type="tool_call_delta",
        tool_call_index=0,
        tool_call_id=None,
        function_name=None,
        # Intentionally wrong: missing required si_do, nx, ny fields
        function_args_delta='{"invalid_field": "bad_data"}',
    ),
    StreamEvent(
        type="usage",
        usage=TokenUsage(input_tokens=90, output_tokens=35),
    ),
    StreamEvent(type="done"),
]


# ---------------------------------------------------------------------------
# T018: Unknown tool handling test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t018_unknown_tool_graceful_handling(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """T018: Engine handles a non-existent tool call without crashing.

    The LLM requests "nonexistent_magic_tool" which is not registered.
    The ToolExecutor returns ToolResult(success=False, error_type="not_found").
    The engine then continues into a second iteration where the LLM produces a
    text answer after receiving the error result in the conversation history.

    Verifies:
    - The engine does NOT crash or raise an exception.
    - A tool_use event is emitted for the unknown tool name.
    - A tool_result event is emitted with success=False.
    - The engine continues and eventually emits a stop event.
    """
    engine, _llm_client, httpx_mock = e2e_builder.with_llm_responses(
        [_UNKNOWN_TOOL_CALL, TEXT_ANSWER_ROUTE_SAFETY]
    ).build()

    events = await run_e2e_query(
        engine,
        httpx_mock,
        user_message="마법 도구로 경로 분석해줘",
    )

    # Verify a tool_use event was emitted for the unknown tool
    tool_use_events = [e for e in events if e.type == "tool_use"]
    assert tool_use_events, "Expected at least one tool_use event"
    unknown_tool_uses = [e for e in tool_use_events if e.tool_name == "nonexistent_magic_tool"]
    assert unknown_tool_uses, (
        f"Expected tool_use event for 'nonexistent_magic_tool', "
        f"got: {[e.tool_name for e in tool_use_events]}"
    )

    # Verify a tool_result event with success=False was emitted
    tool_result_events = [e for e in events if e.type == "tool_result"]
    assert tool_result_events, "Expected at least one tool_result event"
    failed_results = [e for e in tool_result_events if e.tool_result and not e.tool_result.success]
    assert failed_results, (
        "Expected tool_result with success=False for unknown tool, "
        f"got results: {
            [(e.tool_result.success if e.tool_result else None) for e in tool_result_events]
        }"
    )
    # Error type must be 'not_found'
    not_found_results = [
        e for e in failed_results if e.tool_result and e.tool_result.error_type == "not_found"
    ]
    assert not_found_results, (
        "Expected error_type='not_found' for unknown tool, "
        f"got: {[e.tool_result.error_type if e.tool_result else None for e in failed_results]}"
    )

    # Engine must produce a stop event (not crash)
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found — engine may have crashed"


# ---------------------------------------------------------------------------
# T019: Max iterations guard test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t019_max_iterations_guard(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """T019: Engine stops after max_iterations and emits max_iterations_reached.

    A MockLLMClient is configured to always return a tool call, so the engine
    would loop forever without the iteration guard. The engine is configured
    with max_iterations=2.

    Verifies:
    - The engine stops after exactly max_iterations iterations.
    - The stop event carries stop_reason=max_iterations_reached.
    - The engine never raises an exception.
    """
    # Single response repeated forever — LLM always requests a tool call
    config = QueryEngineConfig(max_iterations=2)

    engine, _llm_client, httpx_mock = (
        e2e_builder
        # _INFINITE_TOOL_CALL is the only response; MockLLMClient repeats last entry
        .with_llm_responses([_INFINITE_TOOL_CALL])
        .with_config(config)
        .build()
    )

    events = await run_e2e_query(
        engine,
        httpx_mock,
        user_message="무한 루프 테스트",
    )

    # Must terminate with max_iterations_reached
    assert_stop_reason(events, StopReason.max_iterations_reached)

    # Must have at least max_iterations tool_use events (2 iterations × 1 tool each)
    tool_use_events = [e for e in events if e.type == "tool_use"]
    assert len(tool_use_events) >= config.max_iterations, (
        f"Expected at least {config.max_iterations} tool_use events, got {len(tool_use_events)}"
    )


# ---------------------------------------------------------------------------
# T020: Stream interruption retry test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t020_stream_interruption_retry(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """T020: Engine retries once on StreamInterruptedError, then succeeds.

    Per query.py, the engine retries the LLM stream once on the first
    StreamInterruptedError (continue to the next loop iteration). On a second
    interruption it yields stop(error_unrecoverable).

    This test verifies the happy-path retry: first stream call raises
    StreamInterruptedError, second call returns a valid text response.
    The engine emits a text_delta restart marker and then the final answer.

    Implementation note: MockLLMClient only supports pre-configured StreamEvent
    sequences and cannot raise exceptions. We patch MockLLMClient.stream() via
    unittest.mock to simulate the exception on the first call.
    """
    engine, llm_client, httpx_mock = e2e_builder.with_llm_responses(
        [TEXT_ANSWER_ROUTE_SAFETY]
    ).build()

    call_count = 0
    original_stream = llm_client.stream

    async def _stream_with_first_interruption(messages, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # Simulate stream interruption on the very first call
            raise StreamInterruptedError("Simulated network interruption")
        # Subsequent calls delegate to the original mock
        async for event in original_stream(messages, **kwargs):
            yield event

    with (
        patch.object(llm_client, "stream", _stream_with_first_interruption),
        patch.object(httpx.AsyncClient, "get", httpx_mock),
    ):
        events: list = []
        async for event in engine.run("스트림 중단 후 재시도 테스트"):
            events.append(event)

    # The engine must have attempted the stream at least twice (1 fail + 1 retry)
    # call_count tracks both the failed attempt and the successful retry
    assert call_count >= 2, (
        f"Expected at least 2 stream attempts (1 fail + 1 retry), got {call_count}"
    )

    # After retry, the engine should succeed and emit a stop event
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found after stream interruption retry"

    # The stop reason must NOT be error_unrecoverable on a single interruption
    # (the engine retries once before giving up)
    final_stop = stop_events[-1]
    assert final_stop.stop_reason != StopReason.error_unrecoverable, (
        f"Engine gave up on first interruption (stop_reason={final_stop.stop_reason!r}), "
        "but should retry once before yielding error_unrecoverable"
    )


# ---------------------------------------------------------------------------
# T021: Invalid tool arguments test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t021_invalid_tool_arguments(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """T021: Pydantic validation failure on tool input is handled gracefully.

    The LLM calls road_risk_score with {"invalid_field": "bad_data"} instead
    of the required {si_do, nx, ny} fields. The ToolExecutor catches the
    Pydantic ValidationError and returns ToolResult(success=False,
    error_type="validation").

    Verifies:
    - A tool_use event is emitted for road_risk_score.
    - A tool_result event is emitted with success=False, error_type="validation".
    - The engine continues (does not crash) and emits a stop event.
    """
    engine, _llm_client, httpx_mock = e2e_builder.with_llm_responses(
        [_INVALID_ARGS_TOOL_CALL, TEXT_ANSWER_ROUTE_SAFETY]
    ).build()

    events = await run_e2e_query(
        engine,
        httpx_mock,
        user_message="잘못된 인자로 도구 호출 테스트",
    )

    # road_risk_score tool_use must have been emitted
    tool_use_events = [e for e in events if e.type == "tool_use"]
    road_risk_uses = [e for e in tool_use_events if e.tool_name == "road_risk_score"]
    assert road_risk_uses, (
        f"Expected tool_use event for 'road_risk_score', "
        f"got: {[e.tool_name for e in tool_use_events]}"
    )

    # A tool_result with validation failure must be emitted
    tool_result_events = [e for e in events if e.type == "tool_result"]
    road_risk_results = [
        e
        for e in tool_result_events
        if e.tool_result and e.tool_result.tool_id == "road_risk_score"
    ]
    assert road_risk_results, "Expected tool_result event for road_risk_score"

    validation_failures = [
        e
        for e in road_risk_results
        if e.tool_result and not e.tool_result.success and e.tool_result.error_type == "validation"
    ]
    assert validation_failures, (
        "Expected ToolResult with success=False and error_type='validation', "
        f"got: {
            [
                (e.tool_result.success, e.tool_result.error_type) if e.tool_result else None
                for e in road_risk_results
            ]
        }"
    )

    # Engine must not crash — stop event required
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found — engine may have crashed on validation failure"


# ---------------------------------------------------------------------------
# T022: Preprocessing pipeline test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t022_preprocessing_pipeline_small_context(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """T022: Engine completes successfully even with a very small context_window.

    The PreprocessingPipeline is triggered when estimated message tokens exceed
    (context_window * preprocessing_threshold). With context_window=1000 and
    preprocessing_threshold=0.1, the threshold is 100 tokens — low enough that
    preprocessing will fire on any non-trivial conversation.

    NOTE: The preprocessing pipeline compresses messages in-place but does not
    guarantee a measurably smaller output in all cases (e.g. empty turn
    attachments add nothing to compress). This test primarily verifies that
    a very small context_window does NOT cause an api_budget_exceeded stop
    unless the assembled context truly exceeds the hard limit.

    Verifies:
    - The engine completes the happy-path flow (tool call + text response).
    - The stop event is end_turn (not error_unrecoverable or api_budget_exceeded
      caused solely by the small preprocessing threshold).
    - TODO: When PreprocessingPipeline implements real compression strategies
      (snipping, micro-compaction), add a test that verifies message count
      decreases after preprocessing fires.
    """
    # context_window=1000 with preprocessing_threshold=0.1 → threshold of
    # 100 tokens. The system prompt alone likely exceeds this, triggering
    # aggressive preprocessing on the first iteration.
    #
    # However, the BudgetEstimator hard limit (context_window=1000) is
    # separate from the preprocessing threshold. The engine only stops with
    # api_budget_exceeded if the assembled context (system prompt + tools)
    # exceeds the hard_limit. To avoid that, we use a context_window large
    # enough that the budget check passes but small enough that preprocessing
    # is triggered during the iteration loop.
    config = QueryEngineConfig(
        context_window=8000,  # Passes budget guard for assembled context
        preprocessing_threshold=0.01,  # 1% → ~80 tokens → triggers preprocessing immediately
        max_iterations=10,
    )

    engine, _llm_client, httpx_mock = (
        e2e_builder.with_llm_responses([TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY])
        .with_config(config)
        .build()
    )

    events = await run_e2e_query(
        engine,
        httpx_mock,
        user_message="전처리 파이프라인 테스트: 부산에서 서울로 가는 안전 경로",
    )

    # Engine must complete — stop event required
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found — engine failed during preprocessing"

    final_stop = stop_events[-1]

    # The engine should NOT fail due to preprocessing itself
    assert final_stop.stop_reason != StopReason.error_unrecoverable, (
        f"Engine raised error_unrecoverable during preprocessing pipeline: "
        f"stop_message={final_stop.stop_message!r}"
    )

    # The happy-path flow should complete with end_turn
    # (api_budget_exceeded is acceptable if the system prompt alone exceeds the
    # hard context_window limit — but we sized context_window=8000 to avoid that)
    assert final_stop.stop_reason in (
        StopReason.end_turn,
        StopReason.task_complete,
    ), (
        f"Unexpected stop reason after preprocessing: {final_stop.stop_reason!r}. "
        f"stop_message={final_stop.stop_message!r}"
    )

    # road_risk_score must have been dispatched (full pipeline ran)
    tool_use_events = [e for e in events if e.type == "tool_use"]
    road_risk_uses = [e for e in tool_use_events if e.tool_name == "road_risk_score"]
    assert road_risk_uses, (
        "road_risk_score tool was not dispatched — "
        "preprocessing may have disrupted the conversation history"
    )
