# SPDX-License-Identifier: Apache-2.0
"""Spec 2522 Phase 8 US6 — v4 tests for KOROAD 2-tool surface.

Covers:
  T037-A  koroad_accident_search live happy path (siDo="11", guGun="680")
  T037-B  koroad_accident_search live NODATA comparison (siDo="1100" → ValidationError)
  T037-C  geom_json strip verification on _strip_geom_json helper
  T037-D  koroad_accident_hazard_search live happy path (adm_cd derived from
          서울 강남구 prefix "1168000000", year=2024)
  T037-E  _strip_geom_json applied in handle() — output items must not contain geom_json

2-digit + 3-digit wire param scheme confirmed by evidence:
  /tmp/kosmos-evidence/koroad-mohw-evidence.md § "siDo/guGun Code Scheme"
  Live: siDo=11 / guGun=680 → HTTP 200, resultCode="00", totalCount=3
  4-digit values (siDo=1100) are rejected by SidoCode enum validation.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from pydantic import ValidationError

from kosmos.tools.koroad._short_references import KOROAD_SIDO_SHORT_REFERENCE
from kosmos.tools.koroad.accident_hazard_search import (
    AccidentHazardSearchInput,
    _strip_geom_json,
    handle,
)
from kosmos.tools.koroad.code_tables import GugunCode, SearchYearCd, SidoCode
from kosmos.tools.koroad.koroad_accident_search import (
    KoroadAccidentSearchInput,
    _call,
)


# ---------------------------------------------------------------------------
# T037-A  koroad_accident_search — live happy path siDo=11 / guGun=680
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_accident_search_live_seoul_gangnam() -> None:
    """Live: siDo=11 (서울), guGun=680 (강남구) returns ≥1 hotspot with valid fields."""
    inp = KoroadAccidentSearchInput(
        search_year_cd=SearchYearCd.GENERAL_2024,
        si_do=SidoCode.SEOUL,
        gu_gun=GugunCode.SEOUL_GANGNAM,
        num_of_rows=5,
        page_no=1,
    )
    result = await _call(inp)

    assert isinstance(result, dict)
    assert result["total_count"] >= 1, (
        f"Expected ≥1 hotspot for Seoul/Gangnam (siDo=11, guGun=680), got {result['total_count']}"
    )
    hotspots = result["hotspots"]
    assert len(hotspots) >= 1

    first = hotspots[0]
    # Mandatory fields present and non-empty
    assert first["spot_nm"], "spot_nm must be non-empty"
    assert first["sido_sgg_nm"], "sido_sgg_nm must be non-empty"
    assert isinstance(first["occrrnc_cnt"], int)
    assert isinstance(first["caslt_cnt"], int)
    assert isinstance(first["la_crd"], float)
    assert isinstance(first["lo_crd"], float)


# ---------------------------------------------------------------------------
# T037-B  koroad_accident_search — 4-digit siDo "1100" rejected by enum
# ---------------------------------------------------------------------------


def test_accident_search_invalid_sido_4digit_raises() -> None:
    """4-digit siDo value (e.g. 1100) is invalid; SidoCode enum rejects it."""
    with pytest.raises((ValidationError, ValueError)):
        KoroadAccidentSearchInput(
            search_year_cd=SearchYearCd.GENERAL_2024,
            si_do=1100,  # type: ignore[arg-type]  # 4-digit — must fail
            gu_gun=GugunCode.SEOUL_GANGNAM,
        )


# ---------------------------------------------------------------------------
# T037-C  _strip_geom_json helper unit tests
# ---------------------------------------------------------------------------


class TestStripGeomJson:
    """_strip_geom_json removes geom_json from item dicts without mutating input."""

    def test_removes_geom_json_field(self) -> None:
        item: dict[str, Any] = {
            "spot_nm": "강남역 부근",
            "geom_json": '{"type":"Polygon","coordinates":[[[127.0,37.4]]]}',
            "occrrnc_cnt": 10,
        }
        result = _strip_geom_json(item)
        assert "geom_json" not in result
        assert result["spot_nm"] == "강남역 부근"
        assert result["occrrnc_cnt"] == 10

    def test_original_not_mutated(self) -> None:
        item: dict[str, Any] = {
            "spot_nm": "테헤란로",
            "geom_json": "some_polygon_data",
        }
        _strip_geom_json(item)
        # Original dict must remain unchanged
        assert "geom_json" in item

    def test_no_geom_json_key_is_noop(self) -> None:
        item: dict[str, Any] = {"spot_nm": "역삼역", "occrrnc_cnt": 5}
        result = _strip_geom_json(item)
        assert result == item
        assert "geom_json" not in result

    def test_all_other_fields_preserved(self) -> None:
        item: dict[str, Any] = {
            "spot_nm": "서초구 방배동",
            "spot_cd": "11650001",
            "sido_sgg_nm": "서울 서초구",
            "occrrnc_cnt": 7,
            "caslt_cnt": 9,
            "dth_dnv_cnt": 0,
            "la_crd": 37.48,
            "lo_crd": 126.99,
            "geom_json": "large_polygon_string_x500",
        }
        result = _strip_geom_json(item)
        for key in ("spot_nm", "spot_cd", "sido_sgg_nm", "occrrnc_cnt",
                    "caslt_cnt", "dth_dnv_cnt", "la_crd", "lo_crd"):
            assert key in result, f"Expected key {key!r} in stripped result"
        assert "geom_json" not in result


# ---------------------------------------------------------------------------
# T037-D  koroad_accident_hazard_search — live happy path adm_cd 강남구
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_accident_hazard_search_live_gangnam() -> None:
    """Live: adm_cd='1168000000' (강남구 adm prefix), year=2024 returns ≥1 spot."""
    inp = AccidentHazardSearchInput(adm_cd="1168000000", year=2024)
    result = await handle(inp)

    assert result["kind"] == "collection"
    assert result["total_count"] >= 1, (
        f"Expected ≥1 hazard spot for adm_cd=1168000000, year=2024, "
        f"got total_count={result['total_count']}"
    )
    items = result["items"]
    assert len(items) >= 1

    first = items[0]
    assert first["spot_nm"], "spot_nm must be non-empty"
    assert "geom_json" not in first, (
        "geom_json must be stripped from output items by _strip_geom_json; "
        f"found key in first item: {list(first.keys())}"
    )


# ---------------------------------------------------------------------------
# T037-E  handle() strips geom_json via mock (no live call needed)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_handle_strips_geom_json_via_mock(monkeypatch: pytest.MonkeyPatch) -> None:
    """handle() must strip geom_json from all output items (mock-based, no API key needed)."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key")

    raw_response: dict[str, Any] = {
        "resultCode": "00",
        "resultMsg": "NORMAL_CODE",
        "totalCount": 1,
        "pageNo": 1,
        "numOfRows": 10,
        "items": {
            "item": {
                "spot_nm": "강남역 부근",
                "spot_cd": "11680001",
                "sido_sgg_nm": "서울 강남구",
                "bjd_cd": "1168010100",
                "occrrnc_cnt": 63,
                "caslt_cnt": 68,
                "dth_dnv_cnt": 0,
                "se_dnv_cnt": 12,
                "sl_dnv_cnt": 52,
                "wnd_dnv_cnt": 4,
                "geom_json": '{"type":"Polygon","coordinates":[[[127.02,37.49]]]}',
                "lo_crd": 127.02,
                "la_crd": 37.49,
                "afos_id": "2025119",
                "afos_fid": 6967684,
            }
        },
    }

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = raw_response
    mock_response.raise_for_status = MagicMock()

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response

    inp = AccidentHazardSearchInput(adm_cd="1168010100", year=2024)
    result = await handle(inp, client=mock_client)

    assert result["kind"] == "collection"
    assert result["total_count"] == 1
    assert len(result["items"]) == 1

    item = result["items"][0]
    assert "geom_json" not in item, (
        f"geom_json was NOT stripped from item. Keys present: {list(item.keys())}"
    )
    # Verify key fields still present after strip
    assert item["spot_nm"] == "강남역 부근"
    assert item["occrrnc_cnt"] == 63
    assert item["la_crd"] == pytest.approx(37.49)


# ---------------------------------------------------------------------------
# T037-F  KOROAD_SIDO_SHORT_REFERENCE sanity (inline table present in descriptions)
# ---------------------------------------------------------------------------


def test_sido_short_reference_inline_in_si_do_description() -> None:
    """KOROAD_SIDO_SHORT_REFERENCE must be embedded in si_do Field description."""
    from kosmos.tools.koroad.koroad_accident_search import KoroadAccidentSearchInput

    field_desc = KoroadAccidentSearchInput.model_fields["si_do"].description or ""
    assert KOROAD_SIDO_SHORT_REFERENCE in field_desc, (
        "KOROAD_SIDO_SHORT_REFERENCE not found in si_do field description. "
        f"Current description snippet: {field_desc[:200]!r}"
    )


def test_gu_gun_description_contains_wire_format_note() -> None:
    """gu_gun Field description must mention the 2+3-digit wire format and reject 4-digit."""
    from kosmos.tools.koroad.koroad_accident_search import KoroadAccidentSearchInput

    field_desc = KoroadAccidentSearchInput.model_fields["gu_gun"].description or ""
    assert "3-digit" in field_desc, "gu_gun description must mention '3-digit'"
    assert "4-digit" in field_desc or "4 digit" in field_desc, (
        "gu_gun description must warn against 4-digit 행정구역코드"
    )
