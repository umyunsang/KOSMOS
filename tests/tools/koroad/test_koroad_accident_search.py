# SPDX-License-Identifier: Apache-2.0
"""Tests for the KOROAD accident hotspot search adapter.

Covers:
  - _normalize_items: single-dict / list / empty / unexpected-type quirks
  - _parse_response: success, single-item, empty, error-code paths
  - KoroadAccidentSearchInput: valid construction and legacy-sido cross-validator
  - _call: happy path, missing API key, XML content-type guard
  - KOROAD_ACCIDENT_SEARCH_TOOL: GovAPITool field assertions
  - register(): wires tool into ToolRegistry and ToolExecutor
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import ValidationError

from kosmos.tools.errors import ConfigurationError, ToolExecutionError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.koroad.code_tables import GugunCode, SearchYearCd, SidoCode
from kosmos.tools.koroad.koroad_accident_search import (
    KOROAD_ACCIDENT_SEARCH_TOOL,
    KoroadAccidentSearchInput,
    KoroadAccidentSearchOutput,
    _call,
    _normalize_items,
    _parse_response,
    register,
)
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Fixture file helpers
# ---------------------------------------------------------------------------

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES_DIR / name).read_text())


# ---------------------------------------------------------------------------
# TestNormalizeItems
# ---------------------------------------------------------------------------


class TestNormalizeItems:
    """_normalize_items handles KOROAD single-item/list/empty quirks."""

    def test_list_passthrough(self) -> None:
        items = [{"spot_cd": "A"}, {"spot_cd": "B"}]
        result = _normalize_items(items)
        assert result is items

    def test_single_dict_wrapped(self) -> None:
        item = {"spot_cd": "A"}
        result = _normalize_items(item)
        assert result == [item]

    def test_none_returns_empty(self) -> None:
        assert _normalize_items(None) == []

    def test_empty_string_returns_empty(self) -> None:
        assert _normalize_items("") == []

    def test_unexpected_type_returns_empty(self) -> None:
        # Integer input is unexpected; should silently return empty list.
        assert _normalize_items(42) == []  # type: ignore[arg-type]
        assert _normalize_items(3.14) == []  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# TestParseResponse
# ---------------------------------------------------------------------------


class TestParseResponse:
    """_parse_response extracts hotspots from full API response JSON."""

    def test_success_with_fixture(self) -> None:
        raw = _load_fixture("koroad_success.json")
        output = _parse_response(raw)
        assert isinstance(output, KoroadAccidentSearchOutput)
        assert output.total_count == 2
        assert output.page_no == 1
        assert output.num_of_rows == 10
        assert len(output.hotspots) == 2
        first = output.hotspots[0]
        assert first.spot_cd == "2025119.0001"
        assert first.spot_nm == "강남대로 교차로"
        assert first.occrrnc_cnt == 15
        assert first.la_crd == pytest.approx(37.4979)
        assert first.geom_json is None

    def test_single_item_fixture(self) -> None:
        raw = _load_fixture("koroad_single_item.json")
        output = _parse_response(raw)
        assert output.total_count == 1
        assert len(output.hotspots) == 1
        hotspot = output.hotspots[0]
        assert hotspot.spot_cd == "2025119.0099"
        assert hotspot.sido_sgg_nm == "서울 서초구"

    def test_empty_results(self) -> None:
        raw = _load_fixture("koroad_empty.json")
        output = _parse_response(raw)
        assert output.total_count == 0
        assert output.hotspots == []

    def test_nodata_error_returns_empty(self) -> None:
        raw = {"resultCode": "03", "resultMsg": "NODATA_ERROR", "pageNo": 1, "numOfRows": 10}
        output = _parse_response(raw)
        assert output.total_count == 0
        assert output.hotspots == []
        assert output.page_no == 1

    def test_error_code_raises(self) -> None:
        raw = _load_fixture("koroad_error.json")
        with pytest.raises(ToolExecutionError) as exc_info:
            _parse_response(raw)
        assert "30" in str(exc_info.value)
        assert "SERVICE_KEY_IS_NOT_REGISTERED_ERROR" in str(exc_info.value)

    def test_coerce_numeric_string_fields(self) -> None:
        """Real KOROAD API returns afos_fid as int; Pydantic should coerce to str."""
        raw = {
            "resultCode": "00",
            "resultMsg": "NORMAL_CODE",
            "items": {
                "item": {
                    "spot_cd": "2025119.0001",
                    "spot_nm": "강남대로 교차로",
                    "sido_sgg_nm": "서울 강남구",
                    "bjd_cd": "1168010100",
                    "occrrnc_cnt": 15,
                    "caslt_cnt": 22,
                    "dth_dnv_cnt": 0,
                    "se_dnv_cnt": 3,
                    "sl_dnv_cnt": 10,
                    "wnd_dnv_cnt": 9,
                    "la_crd": 37.4979,
                    "lo_crd": 127.0276,
                    "geom_json": None,
                    "afos_id": "2025119",
                    "afos_fid": 7192978,
                }
            },
            "totalCount": 1,
            "numOfRows": 1,
            "pageNo": 1,
        }
        output = _parse_response(raw)
        assert len(output.hotspots) == 1
        assert output.hotspots[0].afos_fid == "7192978"


# ---------------------------------------------------------------------------
# TestKoroadAccidentSearchInput
# ---------------------------------------------------------------------------


class TestKoroadAccidentSearchInput:
    """Input validation including legacy sido cross-validator."""

    def test_valid_construction(self) -> None:
        inp = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
        )
        assert inp.si_do == SidoCode.SEOUL
        assert inp.search_year_cd == SearchYearCd.GENERAL_2024
        assert inp.gu_gun == GugunCode.SEOUL_GANGNAM
        assert inp.num_of_rows == 10
        assert inp.page_no == 1

    def test_gangwon_legacy_with_2024_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            KoroadAccidentSearchInput(
                search_year_cd=SearchYearCd.GENERAL_2024,
                si_do=SidoCode.GANGWON_LEGACY,
                gu_gun=GugunCode.SEOUL_GANGNAM,
            )
        assert "42" in str(exc_info.value) or "강원도" in str(exc_info.value)

    def test_jeonbuk_legacy_with_2024_raises(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            KoroadAccidentSearchInput(
                search_year_cd=SearchYearCd.GENERAL_2024,
                si_do=SidoCode.JEONBUK_LEGACY,
                gu_gun=GugunCode.SEOUL_GANGNAM,
            )
        assert "45" in str(exc_info.value) or "전라북도" in str(exc_info.value)

    def test_gangwon_legacy_with_2022_ok(self) -> None:
        # GENERAL_2022 has year=2022, which is < GANGWON_NEW_CODE_YEAR(2023)
        inp = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2022,
            si_do=SidoCode.GANGWON_LEGACY,
            gu_gun=GugunCode.SEOUL_GANGNAM,
        )
        assert inp.si_do == SidoCode.GANGWON_LEGACY

    def test_missing_gugun_raises(self) -> None:
        """gu_gun is required by the KOROAD API — omitting it must raise."""
        with pytest.raises(ValidationError):
            KoroadAccidentSearchInput(
                search_year_cd=SearchYearCd.GENERAL_2024,
                si_do=SidoCode.SEOUL,
            )

    def test_num_of_rows_too_large_raises(self) -> None:
        with pytest.raises(ValidationError):
            KoroadAccidentSearchInput(
                search_year_cd=SearchYearCd.GENERAL_2024,
                si_do=SidoCode.SEOUL,
                gu_gun=GugunCode.SEOUL_GANGNAM,
                num_of_rows=101,
            )

    def test_num_of_rows_zero_raises(self) -> None:
        with pytest.raises(ValidationError):
            KoroadAccidentSearchInput(
                search_year_cd=SearchYearCd.GENERAL_2024,
                si_do=SidoCode.SEOUL,
                gu_gun=GugunCode.SEOUL_GANGNAM,
                num_of_rows=0,
            )

    def test_num_of_rows_boundary_valid(self) -> None:
        inp_low = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
            num_of_rows=1,
        )
        inp_high = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
            num_of_rows=100,
        )
        assert inp_low.num_of_rows == 1
        assert inp_high.num_of_rows == 100


# ---------------------------------------------------------------------------
# TestCall
# ---------------------------------------------------------------------------


class TestCall:
    """_call async adapter with mocked httpx."""

    async def test_success_flow(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key")
        fixture_data = _load_fixture("koroad_success.json")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = fixture_data
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        inp = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
        )
        result = await _call(inp, client=mock_client)

        assert result["total_count"] == 2
        assert len(result["hotspots"]) == 2
        assert result["hotspots"][0]["spot_cd"] == "2025119.0001"

    async def test_missing_api_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KOSMOS_DATA_GO_KR_API_KEY", raising=False)
        inp = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
        )
        with pytest.raises(ConfigurationError) as exc_info:
            await _call(inp)
        assert "KOSMOS_DATA_GO_KR_API_KEY" in str(exc_info.value)

    async def test_xml_content_type_guard(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key")

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/xml; charset=UTF-8"}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        inp = KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=SidoCode.SEOUL,
            gu_gun=GugunCode.SEOUL_GANGNAM,
        )
        with pytest.raises(ToolExecutionError) as exc_info:
            await _call(inp, client=mock_client)
        assert "XML" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TestToolDefinition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    """KOROAD_ACCIDENT_SEARCH_TOOL GovAPITool definition."""

    def test_tool_id(self) -> None:
        assert KOROAD_ACCIDENT_SEARCH_TOOL.id == "koroad_accident_search"

    def test_auth_type(self) -> None:
        assert KOROAD_ACCIDENT_SEARCH_TOOL.auth_type == "api_key"

    def test_is_core(self) -> None:
        assert KOROAD_ACCIDENT_SEARCH_TOOL.is_core is True

    def test_is_personal_data(self) -> None:
        assert KOROAD_ACCIDENT_SEARCH_TOOL.is_personal_data is False

    def test_input_schema(self) -> None:
        assert KOROAD_ACCIDENT_SEARCH_TOOL.input_schema is KoroadAccidentSearchInput

    def test_output_schema(self) -> None:
        assert KOROAD_ACCIDENT_SEARCH_TOOL.output_schema is KoroadAccidentSearchOutput


# ---------------------------------------------------------------------------
# TestRegister
# ---------------------------------------------------------------------------


class TestRegister:
    """register() wires tool into registry and executor."""

    def test_register(self) -> None:
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register(registry, executor)

        assert "koroad_accident_search" in registry
        tool = registry.lookup("koroad_accident_search")
        assert tool.id == "koroad_accident_search"
        assert "koroad_accident_search" in executor._adapters
        assert callable(executor._adapters["koroad_accident_search"])
