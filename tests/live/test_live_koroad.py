# SPDX-License-Identifier: Apache-2.0
"""Live validation tests for the KOROAD accident hotspot search adapter."""

from __future__ import annotations

import pytest

from kosmos.tools.koroad.code_tables import GugunCode, SearchYearCd, SidoCode
from kosmos.tools.koroad.koroad_accident_search import (
    KoroadAccidentSearchInput,
    KoroadAccidentSearchOutput,
    _call,
)


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_koroad_basic_search(
    koroad_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call the real KOROAD API with Seoul/GENERAL_2024 and verify response structure."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", koroad_api_key)

    inp = KoroadAccidentSearchInput(
        search_year_cd=SearchYearCd.GENERAL_2024,
        si_do=SidoCode.SEOUL,
        gu_gun=GugunCode.SEOUL_GANGNAM,
        num_of_rows=10,
        page_no=1,
    )
    result = await _call(inp)

    # Verify top-level keys are present
    assert "total_count" in result
    assert "page_no" in result
    assert "num_of_rows" in result
    assert "hotspots" in result

    # Verify types and basic constraints
    assert isinstance(result["total_count"], int)
    assert result["total_count"] >= 0
    assert isinstance(result["hotspots"], list)

    # If results were returned, verify first hotspot has required fields
    if result["hotspots"]:
        first = result["hotspots"][0]
        required_fields = {"spot_cd", "spot_nm", "la_crd", "lo_crd", "occrrnc_cnt"}
        for field in required_fields:
            assert field in first, f"Missing required field {field!r} in AccidentHotspot"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_koroad_response_parses_to_output_model(
    koroad_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify the raw _call() dict parses cleanly into KoroadAccidentSearchOutput."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", koroad_api_key)

    inp = KoroadAccidentSearchInput(
        search_year_cd=SearchYearCd.GENERAL_2024,
        si_do=SidoCode.SEOUL,
        gu_gun=GugunCode.SEOUL_GANGNAM,
        num_of_rows=10,
        page_no=1,
    )
    result = await _call(inp)

    # model_validate should succeed without raising a ValidationError
    output = KoroadAccidentSearchOutput.model_validate(result)
    assert isinstance(output, KoroadAccidentSearchOutput)
    assert output.total_count >= 0
    assert isinstance(output.hotspots, list)


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_koroad_pagination(
    koroad_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Request a single-row page and verify pagination fields are respected."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", koroad_api_key)

    inp = KoroadAccidentSearchInput(
        search_year_cd=SearchYearCd.GENERAL_2024,
        si_do=SidoCode.SEOUL,
        gu_gun=GugunCode.SEOUL_GANGNAM,
        num_of_rows=1,
        page_no=1,
    )
    result = await _call(inp)

    assert result["num_of_rows"] == 1
    assert len(result["hotspots"]) <= 1
