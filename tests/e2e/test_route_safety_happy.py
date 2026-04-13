# SPDX-License-Identifier: Apache-2.0
"""E2E happy-path tests for the route safety citizen query flow (T006-T008).

Tests verify the full pipeline from a Korean citizen query through LLM tool
dispatch, composite adapter fan-out to 3 Korean public APIs, and final
Korean text synthesis — using recorded fixtures and zero live API calls.
"""

from __future__ import annotations

import pytest

from kosmos.engine.events import StopReason
from tests.e2e.conftest import (
    TEXT_ANSWER_ROUTE_SAFETY,
    TOOL_CALL_ROAD_RISK,
    E2EFixtureBuilder,
    assert_final_response_contains,
    assert_no_data_gaps,
    assert_tool_calls_dispatched,
    run_e2e_query,
)

# ---------------------------------------------------------------------------
# T006 [US1] Happy-path E2E test
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t006_happy_path_route_safety(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """Full E2E: citizen query dispatches road_risk_score, receives Korean response.

    Verifies that:
    - The engine dispatches road_risk_score via a tool_use event.
    - The final response contains Korean route safety text.
    - The stop reason is task_complete or end_turn.
    - No data gaps are reported from the composite adapter.
    """
    engine, _llm_client, httpx_mock = e2e_builder.with_llm_responses(
        [TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY]
    ).build()

    events = await run_e2e_query(
        engine,
        httpx_mock,
        user_message="내일 부산에서 서울 가는데, 안전한 경로 추천해줘",
    )

    # road_risk_score tool must have been dispatched
    assert_tool_calls_dispatched(events, ["road_risk_score"])

    # Final text must contain Korean route safety keywords
    assert_final_response_contains(events, ["경로", "안전"])

    # Stop reason must indicate successful completion
    stop_events = [e for e in events if e.type == "stop"]
    assert stop_events, "No stop event found in response"
    assert stop_events[-1].stop_reason in (
        StopReason.task_complete,
        StopReason.end_turn,
    ), f"Unexpected stop reason: {stop_events[-1].stop_reason}"

    # No data gaps — all 3 inner adapters should have succeeded
    assert_no_data_gaps(events)


# ---------------------------------------------------------------------------
# T007 [US1] Conversation history verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t007_conversation_history_accumulates(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """Verify that message history accumulates correctly across two LLM calls.

    The engine calls the LLM twice:
      - Iteration 1: LLM requests road_risk_score tool.
      - Iteration 2: LLM synthesizes the Korean answer with tool results injected.

    After the second call, llm_client.last_messages must contain the accumulated
    history including a role="user" message and a role="tool" message.
    """
    engine, llm_client, httpx_mock = e2e_builder.with_llm_responses(
        [TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY]
    ).build()

    await run_e2e_query(
        engine,
        httpx_mock,
        user_message="내일 부산에서 서울 가는데, 안전한 경로 추천해줘",
    )

    # The LLM must have been called exactly twice (tool call + text synthesis)
    assert llm_client.call_count == 2, f"Expected 2 LLM calls, got {llm_client.call_count}"

    # last_messages reflects the history sent on the second (text synthesis) call
    assert llm_client.last_messages is not None, "last_messages should not be None"

    roles = [msg.role for msg in llm_client.last_messages]

    # Must include at least one user message (the citizen's original query)
    assert "user" in roles, f"Expected role='user' in message history, got roles: {roles}"

    # Must include a tool result message fed back to the LLM
    assert "tool" in roles, (
        f"Expected role='tool' in message history on 2nd call, got roles: {roles}"
    )


# ---------------------------------------------------------------------------
# T008 [US1] Multi-tool fan-out verification
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t008_multi_tool_fan_out(
    e2e_env: None,
    e2e_builder: E2EFixtureBuilder,
) -> None:
    """Verify that the road_risk_score composite adapter invokes all 3 inner APIs.

    Checks:
    - httpx mock received at least 3 GET calls (one per inner adapter).
    - Each inner adapter URL pattern appears in the call arguments.
    """
    engine, _llm_client, httpx_mock = e2e_builder.with_llm_responses(
        [TOOL_CALL_ROAD_RISK, TEXT_ANSWER_ROUTE_SAFETY]
    ).build()

    await run_e2e_query(
        engine,
        httpx_mock,
        user_message="내일 부산에서 서울 가는데, 안전한 경로 추천해줘",
    )

    # All 3 inner adapters must have made HTTP GET calls
    call_count = httpx_mock.call_count
    assert call_count >= 3, (
        f"Expected at least 3 httpx GET calls (one per inner adapter), got {call_count}"
    )

    # Collect all URL strings from call arguments
    called_urls: list[str] = []
    for call in httpx_mock.call_args_list:
        # call.args[0] is the URL positional argument to AsyncClient.get()
        if call.args:
            called_urls.append(str(call.args[0]))
        elif call.kwargs.get("url"):
            called_urls.append(str(call.kwargs["url"]))

    all_urls = " ".join(called_urls)

    # Verify each inner adapter's URL pattern is present
    expected_patterns = [
        "getRestFrequentzoneLg",  # koroad_accident_search
        "getWthrWrnList",  # kma_weather_alert_status
        "getUltraSrtNcst",  # kma_current_observation
    ]
    for pattern in expected_patterns:
        assert pattern in all_urls, (
            f"Expected URL pattern {pattern!r} not found in httpx calls.\n"
            f"Called URLs: {called_urls}"
        )
