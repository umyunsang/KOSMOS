# SPDX-License-Identifier: Apache-2.0
"""E2E happy-path tests for Scenario 1 Route Safety (030 rebase).

Verifies the full resolve→search→fetch×2→synthesize pipeline using:
- MockLLMClient scripted to the 6-turn sequence (FR-003).
- Recorded JSON fixtures for Kakao, KOROAD, KMA (no live API calls).
- RunReport aggregate (schema_version="030-runreport-v1").
"""

from __future__ import annotations

import pytest

from tests.e2e.conftest import (
    TRIGGER_QUERY,
    run_scenario,
)

# ---------------------------------------------------------------------------
# T011 [US1] Happy-path E2E — 6-turn scripted sequence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t011_happy_path_resolve_lookup_synthesize() -> None:
    """US1 AC1-4: full 6-turn pipeline with scripted mock LLM and recorded fixtures.

    Verifies:
    - tool_call_order follows resolve x2, lookup x4 (search+fetch for each adapter).
    - stop_reason == "end_turn".
    - final_response is non-empty Korean text.
    - final_response mentions a KOROAD hazard spot name.
    - final_response mentions a KMA forecast field reference.
    """
    report = await run_scenario("happy")

    # AC1: tool call order — resolve x2, then lookup x4
    assert "resolve_location" in report.tool_call_order, (
        f"Expected 'resolve_location' in tool_call_order, got {report.tool_call_order!r}"
    )
    assert "lookup" in report.tool_call_order, (
        f"Expected 'lookup' in tool_call_order, got {report.tool_call_order!r}"
    )

    # Two resolve_location calls
    resolve_calls = [t for t in report.tool_call_order if t == "resolve_location"]
    assert len(resolve_calls) >= 2, (
        f"Expected ≥2 resolve_location calls, got {len(resolve_calls)}: {report.tool_call_order}"
    )

    # At least 4 lookup calls (2 search + 2 fetch)
    lookup_calls = [t for t in report.tool_call_order if t == "lookup"]
    assert len(lookup_calls) >= 4, (
        f"Expected ≥4 lookup calls, got {len(lookup_calls)}: {report.tool_call_order}"
    )

    # AC2: resolve calls precede all lookup calls
    first_lookup_idx = next(i for i, t in enumerate(report.tool_call_order) if t == "lookup")
    last_resolve_idx = max(
        i for i, t in enumerate(report.tool_call_order) if t == "resolve_location"
    )
    assert last_resolve_idx < first_lookup_idx, (
        "All resolve_location calls must precede the first lookup call. "
        f"last_resolve_idx={last_resolve_idx}, first_lookup_idx={first_lookup_idx}"
    )

    # AC3: stop_reason == "end_turn"
    assert report.stop_reason == "end_turn", (
        f"Expected stop_reason='end_turn', got {report.stop_reason!r}"
    )

    # AC4: final_response is non-empty Korean text
    assert report.final_response, "final_response must not be empty or None"

    # Korean content checks (FR-023)
    response_text = report.final_response
    assert any(ord(c) >= 0xAC00 for c in response_text), (
        f"final_response must contain Korean characters, got: {response_text[:200]!r}"
    )

    # Must mention a KOROAD hazard spot name from the fixture
    koroad_keywords = ["강남구", "개포동", "삼성동", "사고", "위험"]
    assert any(kw in response_text for kw in koroad_keywords), (
        f"final_response must reference a KOROAD hazard spot. "
        f"Expected one of {koroad_keywords} in: {response_text[:300]!r}"
    )

    # Must mention a KMA weather field
    kma_keywords = ["날씨", "기온", "강수", "예보", "℃", "°C", "%"]
    assert any(kw in response_text for kw in kma_keywords), (
        f"final_response must reference a KMA weather field. "
        f"Expected one of {kma_keywords} in: {response_text[:300]!r}"
    )


@pytest.mark.asyncio
async def test_t011b_happy_path_token_accounting() -> None:
    """US1 AC3: usage_totals == sum of per-call mock token counts (0% tolerance).

    With 7 LLM calls (6 tool calls + 1 synthesis) at TokenUsage(200, 50) each for
    tool calls and TokenUsage(800, 150) for synthesis:
    - input_tokens = 6*200 + 1*800 = 2000
    - output_tokens = 6*50 + 1*150 = 450
    """
    report = await run_scenario("happy")

    assert report.usage_totals.input_tokens == 2000, (
        f"Expected total input_tokens=2000 (6×200 + 800), "
        f"got {report.usage_totals.input_tokens}"
    )
    assert report.usage_totals.output_tokens == 450, (
        f"Expected total output_tokens=450 (6×50 + 150), "
        f"got {report.usage_totals.output_tokens}"
    )


@pytest.mark.asyncio
async def test_t011c_happy_path_fetched_adapters() -> None:
    """US1: both lookup-fetch calls target the expected adapters.

    fetched_adapter_ids must contain exactly koroad_accident_hazard_search
    and kma_forecast_fetch (order-preserving).
    """
    report = await run_scenario("happy")

    expected = ("koroad_accident_hazard_search", "kma_forecast_fetch")
    assert report.fetched_adapter_ids == expected, (
        f"Expected fetched_adapter_ids={expected!r}, got {report.fetched_adapter_ids!r}"
    )


@pytest.mark.asyncio
async def test_t011d_happy_path_trigger_query_preserved() -> None:
    """US1: trigger_query is preserved verbatim in the RunReport."""
    report = await run_scenario("happy")
    assert report.trigger_query == TRIGGER_QUERY, (
        f"Expected trigger_query={TRIGGER_QUERY!r}, got {report.trigger_query!r}"
    )
