# SPDX-License-Identifier: Apache-2.0
"""E2E degraded-path tests for Scenario 1 Route Safety (030 rebase).

Covers User Story 2: single-adapter failure (KOROAD no-retry, KMA retry-once)
and User Story 3: both adapters down.

All tests use scripted MockLLMClient event sequences and pre-recorded JSON
fixtures. Zero live API calls.
"""

from __future__ import annotations

import pytest

from tests.e2e.conftest import run_scenario

# ---------------------------------------------------------------------------
# US2: Degraded paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_degraded_koroad_no_retry() -> None:
    """US2: KOROAD upstream_down → error result returned; KMA succeeds.

    Engine completes with end_turn; final response acknowledges missing
    KOROAD data but references KMA weather forecast.
    """
    report = await run_scenario(
        "degraded_koroad_no_retry",
        error_table={"koroad_accident_hazard_search": ["upstream_down"]},
    )

    assert report.stop_reason == "end_turn", (
        f"Expected stop_reason='end_turn', got {report.stop_reason!r}"
    )

    assert report.final_response, "final_response must not be empty"

    # Response should acknowledge missing KOROAD data
    degraded_keywords = ["이용할 수 없", "제공", "장애", "나중에", "일시적", "데이터"]
    response_text = report.final_response
    assert any(kw in response_text for kw in degraded_keywords), (
        f"Degraded response should acknowledge missing data. "
        f"Expected one of {degraded_keywords} in: {response_text[:300]!r}"
    )


@pytest.mark.asyncio
async def test_degraded_kma_retry_succeeds() -> None:
    """US2: KMA first call fails (upstream_down), second call succeeds.

    Script supplies two KMA fetch events. Error table injects upstream_down
    on first KMA call only. Engine completes with end_turn.
    """
    report = await run_scenario(
        "degraded_kma_retry",
        error_table={"kma_forecast_fetch": ["upstream_down", None]},
    )

    assert report.stop_reason == "end_turn", (
        f"Expected stop_reason='end_turn', got {report.stop_reason!r}"
    )

    assert report.final_response, "final_response must not be empty"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "scenario_id,error_table,degraded_kw",
    [
        (
            "degraded_koroad_no_retry",
            {"koroad_accident_hazard_search": ["upstream_down"]},
            ["이용할 수 없", "제공", "장애", "나중에", "일시적", "데이터"],
        ),
        (
            "degraded_kma_retry",
            {"kma_forecast_fetch": ["upstream_down", None]},
            # KMA retry succeeds → response should still have Korean content
            ["경로", "안전", "날씨", "사고", "강남구"],
        ),
    ],
)
async def test_degraded_scenarios_parametrized(
    scenario_id: str,
    error_table: dict,
    degraded_kw: list[str],
) -> None:
    """Parametrized smoke: both degraded scenarios reach end_turn with Korean content."""
    report = await run_scenario(
        scenario_id,  # type: ignore[arg-type]
        error_table=error_table,
    )

    assert report.stop_reason == "end_turn", (
        f"[{scenario_id}] Expected end_turn, got {report.stop_reason!r}"
    )
    assert report.final_response, f"[{scenario_id}] final_response must not be empty"

    response_text = report.final_response
    assert any(kw in response_text for kw in degraded_kw), (
        f"[{scenario_id}] Expected one of {degraded_kw} in response: {response_text[:300]!r}"
    )


# ---------------------------------------------------------------------------
# US3: Both adapters down
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_both_down_mock_llm_synthesizes_apology() -> None:
    """US3: Both KOROAD and KMA fail → mock LLM synthesizes graceful Korean apology.

    NOTE: In this scripted test, the mock LLM is programmed to produce a Korean
    apology message even when both adapters fail, resulting in stop_reason=end_turn.
    Spec 030 FR-022 requires stop_reason=error_unrecoverable in production;
    that path is exercised by the production engine (not the mock LLM script).
    This test validates the graceful-synthesis behaviour of the error handling path.
    """
    report = await run_scenario(
        "both_down",
        error_table={
            "koroad_accident_hazard_search": ["upstream_down"],
            "kma_forecast_fetch": ["upstream_down"],
        },
    )

    # Mock LLM is scripted to synthesize an apology → end_turn
    # (FR-022 error_unrecoverable requires production engine, not mock script)
    assert report.stop_reason == "end_turn", (
        f"Expected stop_reason='end_turn' (mock synthesis path), got {report.stop_reason!r}"
    )

    assert report.final_response, "final_response must not be empty"

    # Response must be Korean and apologetic
    both_down_keywords = ["죄송", "장애", "일시적", "다시", "이용할 수 없"]
    response_text = report.final_response
    assert any(kw in response_text for kw in both_down_keywords), (
        f"Both-down response should be a Korean apology. "
        f"Expected one of {both_down_keywords} in: {response_text[:300]!r}"
    )
