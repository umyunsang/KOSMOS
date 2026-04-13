# SPDX-License-Identifier: Apache-2.0
"""Live validation tests for the road_risk_score composite adapter.

Hits the real KOROAD and KMA APIs — no mocks.  Tests hard-fail if either
``KOSMOS_KOROAD_API_KEY`` or ``KOSMOS_DATA_GO_KR_API_KEY`` is unset.
All assertions are structural (types, ranges, keys); no specific values.
"""

from __future__ import annotations

import pytest

from kosmos.tools.composite.road_risk_score import (
    RoadRiskScoreInput,
    RoadRiskScoreOutput,
    _call,
)
from kosmos.tools.koroad.code_tables import SidoCode

# Seoul KMA grid coordinates (standard reference point)
_SEOUL_NX = 60
_SEOUL_NY = 127

_VALID_RISK_LEVELS = {"low", "moderate", "high", "severe"}

_EXPECTED_KEYS = {
    "risk_score",
    "risk_level",
    "hotspot_count",
    "active_warnings",
    "precipitation_mm",
    "temperature_c",
    "data_gaps",
    "summary",
}


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_road_risk_score_basic(
    koroad_api_key: str,
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call the real composite adapter with Seoul params and verify response structure.

    Does NOT assert specific values — only structure, types, and valid ranges.
    Hard-fails if any required env var is missing (via conftest fixtures).
    """
    monkeypatch.setenv("KOSMOS_KOROAD_API_KEY", koroad_api_key)
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    inp = RoadRiskScoreInput(
        si_do=SidoCode.SEOUL,
        nx=_SEOUL_NX,
        ny=_SEOUL_NY,
    )
    result = await _call(inp)

    # Result must be a dict
    assert isinstance(result, dict), f"Expected dict, got {type(result)}"

    # All required keys must be present
    missing = _EXPECTED_KEYS - result.keys()
    assert not missing, f"Missing output keys: {missing}"

    # risk_score: float in [0.0, 1.0]
    assert isinstance(result["risk_score"], float), (
        f"risk_score must be float, got {type(result['risk_score'])}"
    )
    assert 0.0 <= result["risk_score"] <= 1.0, f"risk_score out of range: {result['risk_score']}"

    # risk_level: one of the valid literals
    assert result["risk_level"] in _VALID_RISK_LEVELS, (
        f"risk_level {result['risk_level']!r} not in {_VALID_RISK_LEVELS}"
    )

    # hotspot_count: non-negative int
    assert isinstance(result["hotspot_count"], int), (
        f"hotspot_count must be int, got {type(result['hotspot_count'])}"
    )
    assert result["hotspot_count"] >= 0, (
        f"hotspot_count must be >= 0, got {result['hotspot_count']}"
    )

    # active_warnings: non-negative int
    assert isinstance(result["active_warnings"], int), (
        f"active_warnings must be int, got {type(result['active_warnings'])}"
    )
    assert result["active_warnings"] >= 0, (
        f"active_warnings must be >= 0, got {result['active_warnings']}"
    )

    # data_gaps: list (may be empty if all adapters succeed)
    assert isinstance(result["data_gaps"], list), (
        f"data_gaps must be list, got {type(result['data_gaps'])}"
    )

    # summary: non-empty string (Korean summary)
    assert isinstance(result["summary"], str), f"summary must be str, got {type(result['summary'])}"
    assert result["summary"], "summary must not be empty"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_road_risk_score_parses_to_model(
    koroad_api_key: str,
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the raw _call() dict parses cleanly into RoadRiskScoreOutput."""
    monkeypatch.setenv("KOSMOS_KOROAD_API_KEY", koroad_api_key)
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    inp = RoadRiskScoreInput(
        si_do=SidoCode.SEOUL,
        nx=_SEOUL_NX,
        ny=_SEOUL_NY,
    )
    result = await _call(inp)

    # model_validate must succeed without raising ValidationError
    output = RoadRiskScoreOutput.model_validate(result)
    assert isinstance(output, RoadRiskScoreOutput)
    assert 0.0 <= output.risk_score <= 1.0
    assert output.risk_level in _VALID_RISK_LEVELS
    assert output.hotspot_count >= 0
    assert output.active_warnings >= 0
    assert isinstance(output.data_gaps, list)
    assert output.summary


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_road_risk_score_partial_failure_tolerance(
    koroad_api_key: str,
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Document that composite adapter records data_gaps on sub-adapter failure.

    When hitting real APIs, all three adapters may succeed (data_gaps=[]).
    This test only asserts that data_gaps is a list — it may be empty.
    The structural contract (partial failure → non-empty data_gaps) is
    covered by unit tests using mocked inner adapters.
    """
    monkeypatch.setenv("KOSMOS_KOROAD_API_KEY", koroad_api_key)
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    inp = RoadRiskScoreInput(
        si_do=SidoCode.SEOUL,
        nx=_SEOUL_NX,
        ny=_SEOUL_NY,
    )
    result = await _call(inp)

    # data_gaps is always a list: empty when all adapters succeed,
    # non-empty when one or more fail.
    assert isinstance(result["data_gaps"], list), (
        f"data_gaps must be list regardless of partial failures, got {type(result['data_gaps'])}"
    )

    # If any gaps were recorded, they must be known adapter names
    known_adapters = {
        "koroad_accident_search",
        "kma_weather_alert_status",
        "kma_current_observation",
    }
    for gap in result["data_gaps"]:
        assert isinstance(gap, str), f"Each data_gap entry must be str, got {type(gap)}"
        assert gap in known_adapters, (
            f"Unexpected data_gap value {gap!r}; expected one of {known_adapters}"
        )
