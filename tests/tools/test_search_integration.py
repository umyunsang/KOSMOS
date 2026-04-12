# SPDX-License-Identifier: Apache-2.0
"""Search discovery and flow simulation integration tests (T040, T041)."""

from __future__ import annotations

import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry


class TestSearchDiscovery:
    """T040: Verify tool discovery via ToolRegistry.search()."""

    def _setup_registry(self) -> ToolRegistry:
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register_all_tools(registry, executor)
        return registry

    def test_korean_query_finds_road_risk(self) -> None:
        """'오늘 서울 가는 길 안전해' finds road_risk_score in top 5."""
        registry = self._setup_registry()
        results = registry.search("오늘 서울 가는 길 안전해", max_results=5)
        tool_ids = [r.tool.id for r in results]
        assert "road_risk_score" in tool_ids, (
            f"road_risk_score not in top-5 results: {tool_ids}"
        )

    def test_english_query_finds_accident(self) -> None:
        """'accident hotspot' finds koroad_accident_search."""
        registry = self._setup_registry()
        results = registry.search("accident hotspot", max_results=5)
        tool_ids = [r.tool.id for r in results]
        assert "koroad_accident_search" in tool_ids

    def test_weather_query_finds_kma_tools(self) -> None:
        """'weather alert warning' finds at least one KMA tool."""
        registry = self._setup_registry()
        results = registry.search("weather alert warning", max_results=5)
        tool_ids = [r.tool.id for r in results]
        kma_tools = {"kma_weather_alert_status", "kma_current_observation"}
        assert kma_tools & set(tool_ids), (
            f"No KMA tools in results: {tool_ids}"
        )

    def test_search_returns_search_result_type(self) -> None:
        """Results are ToolSearchResult instances."""
        from kosmos.tools.models import ToolSearchResult

        registry = self._setup_registry()
        results = registry.search("weather", max_results=3)
        for r in results:
            assert isinstance(r, ToolSearchResult)


class TestScenario1FlowSimulation:
    """T041: Simulate Scenario 1 flow with mocked inner adapters."""

    @pytest.mark.asyncio
    async def test_road_risk_score_with_mocked_adapters(self) -> None:
        """road_risk_score._call() with mocked adapters returns valid result."""
        from unittest.mock import AsyncMock, patch

        from kosmos.tools.composite.road_risk_score import RoadRiskScoreInput, _call
        from kosmos.tools.koroad.code_tables import SearchYearCd, SidoCode

        # Mocks return dicts matching model_dump() output of each inner adapter.
        # koroad_accident_search returns KoroadAccidentSearchOutput.model_dump()
        koroad_response = {
            "total_count": 5,
            "page_no": 1,
            "num_of_rows": 100,
            "hotspots": [],
        }

        # kma_weather_alert_status returns KmaWeatherAlertStatusOutput.model_dump()
        kma_alert_response = {
            "total_count": 0,
            "warnings": [],
        }

        # kma_current_observation returns KmaCurrentObservationOutput.model_dump()
        kma_obs_response = {
            "base_date": "20260413",
            "base_time": "1200",
            "nx": 61,
            "ny": 126,
            "t1h": 15.0,
            "rn1": 0.0,
            "uuu": None,
            "vvv": None,
            "wsd": 3.5,
            "reh": 60.0,
            "pty": 0,
            "vec": None,
        }

        with (
            patch(
                "kosmos.tools.composite.road_risk_score._koroad_call",
                new_callable=AsyncMock,
                return_value=koroad_response,
            ),
            patch(
                "kosmos.tools.composite.road_risk_score._kma_alert_call",
                new_callable=AsyncMock,
                return_value=kma_alert_response,
            ),
            patch(
                "kosmos.tools.composite.road_risk_score._kma_obs_call",
                new_callable=AsyncMock,
                return_value=kma_obs_response,
            ),
        ):
            test_input = RoadRiskScoreInput(
                si_do=SidoCode.SEOUL,
                search_year_cd=SearchYearCd.GENERAL_2024,
                nx=61,
                ny=126,
            )
            result = await _call(test_input)

        assert isinstance(result, dict)
        assert "risk_level" in result
        assert result["risk_level"] in {"low", "moderate", "high", "severe"}
        assert "summary" in result
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    async def test_road_risk_score_partial_failure(self) -> None:
        """road_risk_score tolerates partial inner adapter failure."""
        from unittest.mock import AsyncMock, patch

        from kosmos.tools.composite.road_risk_score import RoadRiskScoreInput, _call
        from kosmos.tools.errors import ToolExecutionError
        from kosmos.tools.koroad.code_tables import SearchYearCd, SidoCode

        kma_alert_response = {
            "total_count": 1,
            "warnings": [],
        }
        kma_obs_response = {
            "base_date": "20260413",
            "base_time": "1200",
            "nx": 61,
            "ny": 126,
            "t1h": 10.0,
            "rn1": 5.0,
            "uuu": None,
            "vvv": None,
            "wsd": None,
            "reh": None,
            "pty": 1,
            "vec": None,
        }

        with (
            patch(
                "kosmos.tools.composite.road_risk_score._koroad_call",
                new_callable=AsyncMock,
                side_effect=ToolExecutionError("koroad_accident_search", "simulated failure"),
            ),
            patch(
                "kosmos.tools.composite.road_risk_score._kma_alert_call",
                new_callable=AsyncMock,
                return_value=kma_alert_response,
            ),
            patch(
                "kosmos.tools.composite.road_risk_score._kma_obs_call",
                new_callable=AsyncMock,
                return_value=kma_obs_response,
            ),
        ):
            test_input = RoadRiskScoreInput(
                si_do=SidoCode.SEOUL,
                search_year_cd=SearchYearCd.GENERAL_2024,
                nx=61,
                ny=126,
            )
            result = await _call(test_input)

        assert isinstance(result, dict)
        assert result["risk_level"] in {"low", "moderate", "high", "severe"}
        assert "koroad_accident_search" in result["data_gaps"]

    @pytest.mark.asyncio
    async def test_road_risk_score_all_fail_raises(self) -> None:
        """road_risk_score raises ToolExecutionError when all adapters fail."""
        from unittest.mock import AsyncMock, patch

        from kosmos.tools.composite.road_risk_score import RoadRiskScoreInput, _call
        from kosmos.tools.errors import ToolExecutionError
        from kosmos.tools.koroad.code_tables import SearchYearCd, SidoCode

        with (
            patch(
                "kosmos.tools.composite.road_risk_score._koroad_call",
                new_callable=AsyncMock,
                side_effect=ToolExecutionError("koroad_accident_search", "fail"),
            ),
            patch(
                "kosmos.tools.composite.road_risk_score._kma_alert_call",
                new_callable=AsyncMock,
                side_effect=ToolExecutionError("kma_weather_alert_status", "fail"),
            ),
            patch(
                "kosmos.tools.composite.road_risk_score._kma_obs_call",
                new_callable=AsyncMock,
                side_effect=ToolExecutionError("kma_current_observation", "fail"),
            ),
        ):
            test_input = RoadRiskScoreInput(
                si_do=SidoCode.SEOUL,
                search_year_cd=SearchYearCd.GENERAL_2024,
                nx=61,
                ny=126,
            )
            with pytest.raises(ToolExecutionError):
                await _call(test_input)
