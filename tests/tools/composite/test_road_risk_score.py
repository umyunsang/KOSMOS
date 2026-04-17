# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.tools.composite.road_risk_score."""

from __future__ import annotations

import pytest

from kosmos.tools.composite.road_risk_score import (
    ROAD_RISK_SCORE_TOOL,
    RoadRiskScoreInput,
    RoadRiskScoreOutput,
    _call,
    _compute_risk_score,
    _risk_level,
    register,
)
from kosmos.tools.errors import ToolExecutionError
from kosmos.tools.koroad.code_tables import GugunCode, SearchYearCd, SidoCode

# ---------------------------------------------------------------------------
# Unit tests for pure scoring helpers
# ---------------------------------------------------------------------------


class TestComputeRiskScore:
    def test_zero_inputs_yield_zero(self) -> None:
        score = _compute_risk_score(0, 0, 0.0)
        assert score == 0.0

    def test_max_hotspots_contributes_half(self) -> None:
        # 10 hotspots → hotspot_score=1.0, no weather → score=0.5
        score = _compute_risk_score(10, 0, 0.0)
        assert score == pytest.approx(0.5)

    def test_max_weather_contributes_half(self) -> None:
        # weather_score capped at 1.0, no hotspots → score=0.5
        score = _compute_risk_score(0, 4, 50.0)
        assert score == pytest.approx(0.5)

    def test_both_max_yields_one(self) -> None:
        score = _compute_risk_score(10, 4, 50.0)
        assert score == pytest.approx(1.0)

    def test_score_clamped_at_one(self) -> None:
        score = _compute_risk_score(100, 100, 999.0)
        assert score == 1.0

    def test_precipitation_only(self) -> None:
        # weather_score = 0 + 25/50 = 0.5 → base = 0 * 0.5 + 0.5 * 0.5 = 0.25
        score = _compute_risk_score(0, 0, 25.0)
        assert score == pytest.approx(0.25)


class TestRiskLevel:
    def test_low_boundary(self) -> None:
        assert _risk_level(0.0) == "low"
        assert _risk_level(0.29) == "low"

    def test_moderate_boundary(self) -> None:
        assert _risk_level(0.3) == "moderate"
        assert _risk_level(0.59) == "moderate"

    def test_high_boundary(self) -> None:
        assert _risk_level(0.6) == "high"
        assert _risk_level(0.79) == "high"

    def test_severe_boundary(self) -> None:
        assert _risk_level(0.8) == "severe"
        assert _risk_level(1.0) == "severe"


# ---------------------------------------------------------------------------
# Mock return values (realistic data)
# ---------------------------------------------------------------------------

_KOROAD_OK_5 = {
    "total_count": 5,
    "page_no": 1,
    "num_of_rows": 100,
    "hotspots": [
        {
            "spot_cd": f"A{i}",
            "spot_nm": f"위험지점 {i}",
            "sido_sgg_nm": "서울특별시",
            "bjd_cd": "1100000000",
            "occrrnc_cnt": 3,
            "caslt_cnt": 5,
            "dth_dnv_cnt": 0,
            "se_dnv_cnt": 1,
            "sl_dnv_cnt": 2,
            "wnd_dnv_cnt": 2,
            "la_crd": 37.5,
            "lo_crd": 127.0,
            "geom_json": None,
            "afos_id": "2025119",
            "afos_fid": f"F{i}",
        }
        for i in range(5)
    ],
}

_KOROAD_OK_0 = {
    "total_count": 0,
    "page_no": 1,
    "num_of_rows": 100,
    "hotspots": [],
}

_KMA_ALERT_OK_2 = {
    "total_count": 2,
    "warnings": [
        {
            "stn_id": "108",
            "tm_fc": "202604131200",
            "tm_ef": "202604131800",
            "tm_seq": 1,
            "area_code": "S1151300",
            "area_name": "서울",
            "warn_var": 2,
            "warn_stress": 1,
            "cancel": 0,
            "command": 1,
            "warn_fc": 0,
        },
        {
            "stn_id": "108",
            "tm_fc": "202604131200",
            "tm_ef": "202604132000",
            "tm_seq": 2,
            "area_code": "S1151300",
            "area_name": "서울",
            "warn_var": 7,
            "warn_stress": 0,
            "cancel": 0,
            "command": 1,
            "warn_fc": 0,
        },
    ],
}

_KMA_ALERT_OK_0 = {
    "total_count": 0,
    "warnings": [],
}

_KMA_OBS_OK_RAIN = {
    "base_date": "20260413",
    "base_time": "1200",
    "nx": 60,
    "ny": 127,
    "t1h": 12.0,
    "rn1": 20.0,
    "uuu": None,
    "vvv": None,
    "wsd": 3.5,
    "reh": 80.0,
    "pty": 1,
    "vec": None,
}

_KMA_OBS_OK_DRY = {
    "base_date": "20260413",
    "base_time": "1200",
    "nx": 60,
    "ny": 127,
    "t1h": 18.0,
    "rn1": 0.0,
    "uuu": None,
    "vvv": None,
    "wsd": 1.0,
    "reh": 50.0,
    "pty": 0,
    "vec": None,
}


# ---------------------------------------------------------------------------
# Integration-style tests using mocked inner adapters (T038)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_high_risk_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    """5 hotspots + 2 warnings + 20mm precipitation → risk_level high or severe."""
    from unittest.mock import AsyncMock

    import kosmos.tools.composite.road_risk_score as mod

    monkeypatch.setattr(mod, "_koroad_call", AsyncMock(return_value=_KOROAD_OK_5))
    monkeypatch.setattr(mod, "_kma_alert_call", AsyncMock(return_value=_KMA_ALERT_OK_2))
    monkeypatch.setattr(mod, "_kma_obs_call", AsyncMock(return_value=_KMA_OBS_OK_RAIN))

    inp = RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=127)
    result = await _call(inp)

    output = RoadRiskScoreOutput(**result)
    assert output.risk_level in ("high", "severe")
    assert output.hotspot_count == 5
    assert output.active_warnings == 2
    assert output.precipitation_mm == pytest.approx(20.0)
    assert output.data_gaps == []
    assert output.temperature_c == pytest.approx(12.0)
    assert "위험도" in output.summary
    assert output.risk_score > 0.5


@pytest.mark.asyncio
async def test_low_risk_scenario(monkeypatch: pytest.MonkeyPatch) -> None:
    """0 hotspots + 0 warnings + 0mm precipitation → risk_level=low."""
    from unittest.mock import AsyncMock

    import kosmos.tools.composite.road_risk_score as mod

    monkeypatch.setattr(mod, "_koroad_call", AsyncMock(return_value=_KOROAD_OK_0))
    monkeypatch.setattr(mod, "_kma_alert_call", AsyncMock(return_value=_KMA_ALERT_OK_0))
    monkeypatch.setattr(mod, "_kma_obs_call", AsyncMock(return_value=_KMA_OBS_OK_DRY))

    inp = RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=127)
    result = await _call(inp)

    output = RoadRiskScoreOutput(**result)
    assert output.risk_level == "low"
    assert output.hotspot_count == 0
    assert output.active_warnings == 0
    assert output.precipitation_mm == pytest.approx(0.0)
    assert output.data_gaps == []
    assert output.risk_score == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_partial_failure_kma_obs(monkeypatch: pytest.MonkeyPatch) -> None:
    """KOROAD ok + kma_alert ok + kma_obs raises → data_gaps=['kma_current_observation']."""
    from unittest.mock import AsyncMock

    import kosmos.tools.composite.road_risk_score as mod

    monkeypatch.setattr(mod, "_koroad_call", AsyncMock(return_value=_KOROAD_OK_5))
    monkeypatch.setattr(mod, "_kma_alert_call", AsyncMock(return_value=_KMA_ALERT_OK_2))
    monkeypatch.setattr(
        mod,
        "_kma_obs_call",
        AsyncMock(side_effect=ToolExecutionError("kma_current_observation", "network timeout")),
    )

    inp = RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=127)
    result = await _call(inp)

    output = RoadRiskScoreOutput(**result)
    assert "kma_current_observation" in output.data_gaps
    assert output.hotspot_count == 5
    assert output.active_warnings == 2
    assert output.precipitation_mm == pytest.approx(0.0)  # fallback
    assert output.temperature_c is None  # fallback
    # Score is still computed from available data
    assert 0.0 <= output.risk_score <= 1.0


@pytest.mark.asyncio
async def test_partial_failure_kma_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """KOROAD ok + kma_obs ok + kma_alert raises → data_gaps=['kma_weather_alert_status']."""
    from unittest.mock import AsyncMock

    import kosmos.tools.composite.road_risk_score as mod

    monkeypatch.setattr(mod, "_koroad_call", AsyncMock(return_value=_KOROAD_OK_5))
    monkeypatch.setattr(
        mod,
        "_kma_alert_call",
        AsyncMock(side_effect=ToolExecutionError("kma_weather_alert_status", "API unavailable")),
    )
    monkeypatch.setattr(mod, "_kma_obs_call", AsyncMock(return_value=_KMA_OBS_OK_RAIN))

    inp = RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=127)
    result = await _call(inp)

    output = RoadRiskScoreOutput(**result)
    assert "kma_weather_alert_status" in output.data_gaps
    assert output.hotspot_count == 5
    assert output.active_warnings == 0  # fallback
    assert output.precipitation_mm == pytest.approx(20.0)
    assert 0.0 <= output.risk_score <= 1.0


@pytest.mark.asyncio
async def test_total_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """All three inner adapters raise → ToolExecutionError is raised."""
    from unittest.mock import AsyncMock

    import kosmos.tools.composite.road_risk_score as mod

    monkeypatch.setattr(
        mod,
        "_koroad_call",
        AsyncMock(side_effect=ToolExecutionError("koroad_accident_search", "HTTP 503")),
    )
    monkeypatch.setattr(
        mod,
        "_kma_alert_call",
        AsyncMock(side_effect=ToolExecutionError("kma_weather_alert_status", "HTTP 503")),
    )
    monkeypatch.setattr(
        mod,
        "_kma_obs_call",
        AsyncMock(side_effect=ToolExecutionError("kma_current_observation", "HTTP 503")),
    )

    inp = RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=127)
    with pytest.raises(ToolExecutionError):
        await _call(inp)


# ---------------------------------------------------------------------------
# Model and tool definition tests
# ---------------------------------------------------------------------------


class TestRoadRiskScoreInput:
    def test_default_search_year(self) -> None:
        inp = RoadRiskScoreInput(
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
            nx=60,
            ny=127,
        )
        assert inp.search_year_cd == SearchYearCd.GENERAL_2024

    def test_explicit_search_year_preserved(self) -> None:
        inp = RoadRiskScoreInput(
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
            nx=60,
            ny=127,
            search_year_cd=SearchYearCd.GENERAL_2024,
        )
        assert inp.search_year_cd == SearchYearCd.GENERAL_2024

    def test_nx_bounds(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=0, ny=127)
        with pytest.raises(ValidationError):
            RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=150, ny=127)

    def test_ny_bounds(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=0)
        with pytest.raises(ValidationError):
            RoadRiskScoreInput(si_do=SidoCode.SEOUL, gu_gun=GugunCode.SEOUL_GANGNAM, nx=60, ny=254)


class TestRoadRiskScoreTool:
    def test_tool_id(self) -> None:
        assert ROAD_RISK_SCORE_TOOL.id == "road_risk_score"

    def test_tool_is_core(self) -> None:
        assert ROAD_RISK_SCORE_TOOL.is_core is True

    def test_tool_not_personal_data(self) -> None:
        assert ROAD_RISK_SCORE_TOOL.is_personal_data is False

    def test_tool_requires_auth(self) -> None:
        # V6: auth_type='api_key' delegates to api_key inner tools; requires AAL1+.
        assert ROAD_RISK_SCORE_TOOL.requires_auth is True

    def test_tool_has_search_hint(self) -> None:
        assert ROAD_RISK_SCORE_TOOL.search_hint.strip() != ""


class TestRegister:
    def test_register_adds_tool_and_adapter(self) -> None:
        from kosmos.tools.executor import ToolExecutor
        from kosmos.tools.registry import ToolRegistry

        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register(registry, executor)

        tool = registry.lookup("road_risk_score")
        assert tool.id == "road_risk_score"
