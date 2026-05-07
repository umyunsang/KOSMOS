# SPDX-License-Identifier: Apache-2.0
"""v4 tests for hira_hospital_search — T020 (Spec 2522 US2).

Covers:
  - _type=json response schema validation (JSON envelope structure).
  - Gangnam-gu coordinate live query: xPos=127.047, yPos=37.517, radius=2000
    → ≥ 3 hospitals returned (@pytest.mark.live, skipped in CI).
  - llm_description 5-section structure assertions (purpose, input_quirk,
    domain_quirk, self_contained_decl present; xPos/yPos agency naming note).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from kosax.tools.hira.hospital_search import (
    _HIRA_DESCRIPTION,
    HIRA_HOSPITAL_SEARCH_TOOL,
    HiraHospitalSearchInput,
    handle,
)

_FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "hira"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES_DIR / name).read_text())


def _make_mock_client(fixture_data: dict, *, status_code: int = 200) -> httpx.AsyncClient:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = status_code
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = fixture_data
    if status_code >= 400:
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=mock_response,
        )
    else:
        mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# JSON response schema validation (_type=json returns correct envelope)
# ---------------------------------------------------------------------------


class TestHiraV4JsonResponseSchema:
    """_type=json response envelope structure tests."""

    async def test_json_response_envelope_kind_collection(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """JSON response returns kind='collection' envelope."""
        monkeypatch.setenv("KOSAX_DATA_GO_KR_API_KEY", "test-key-v4")
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        inp = HiraHospitalSearchInput(xPos=127.047, yPos=37.517, radius=2000)
        result = await handle(inp, client=mock_client)

        assert result["kind"] == "collection"
        assert "items" in result
        assert "total_count" in result
        assert isinstance(result["items"], list)
        assert isinstance(result["total_count"], int)

    async def test_json_response_items_have_required_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Each item in JSON response contains yadmNm, addr, ykiho, clCd, clCdNm."""
        monkeypatch.setenv("KOSAX_DATA_GO_KR_API_KEY", "test-key-v4")
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        inp = HiraHospitalSearchInput(xPos=127.047, yPos=37.517, radius=2000)
        result = await handle(inp, client=mock_client)

        for item in result["items"]:
            assert "yadmNm" in item, f"Missing yadmNm in item: {item}"
            assert "addr" in item, f"Missing addr in item: {item}"
            assert "ykiho" in item, f"Missing ykiho in item: {item}"
            assert "clCd" in item, f"Missing clCd in item: {item}"
            assert "clCdNm" in item, f"Missing clCdNm in item: {item}"

    async def test_json_response_distance_field_parseable_as_float(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """distance field in JSON response (high-precision decimal string) is float-parseable."""
        monkeypatch.setenv("KOSAX_DATA_GO_KR_API_KEY", "test-key-v4")
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        inp = HiraHospitalSearchInput(xPos=127.047, yPos=37.517, radius=2000)
        result = await handle(inp, client=mock_client)

        for item in result["items"]:
            dist = item.get("distance")
            if dist is not None:
                # distance may be string or numeric; must be float-parseable
                assert float(dist) >= 0.0, f"distance not parseable as float: {dist!r}"

    async def test_request_uses_underscore_type_param(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """handle() passes '_type'='json' (not 'type'='json') to the HTTP client."""
        monkeypatch.setenv("KOSAX_DATA_GO_KR_API_KEY", "test-key-v4")
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        inp = HiraHospitalSearchInput(xPos=127.047, yPos=37.517, radius=2000)
        await handle(inp, client=mock_client)

        call_kwargs = mock_client.get.call_args
        params = call_kwargs[1].get("params", call_kwargs[0][1] if len(call_kwargs[0]) > 1 else {})
        assert "_type" in params, (
            f"Expected '_type' in HTTP params, got keys: {list(params.keys())}"
        )
        assert params["_type"] == "json", f"Expected '_type'='json', got: {params['_type']!r}"
        assert "type" not in params or params.get("type") != "json", (
            "Deprecated 'type' param must not be used (use '_type')"
        )


# ---------------------------------------------------------------------------
# Live query: Gangnam-gu coordinates → ≥ 3 hospitals
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestHiraV4GangnamLive:
    """Live query: Gangnam-gu (xPos=127.047, yPos=37.517, radius=2000) → ≥ 3 hospitals.

    Skipped in CI by default. Run with: uv run pytest -m live tests/tools/hira/test_v4.py
    Requires KOSAX_DATA_GO_KR_API_KEY to be set.
    """

    async def test_gangnam_live_returns_at_least_three_hospitals(self) -> None:
        """Live HIRA call at Gangnam-gu returns ≥ 3 hospital records."""
        inp = HiraHospitalSearchInput(xPos=127.047, yPos=37.517, radius=2000)
        result = await handle(inp)

        assert result["kind"] == "collection", f"Unexpected kind: {result['kind']}"
        items = result["items"]
        assert len(items) >= 3, (
            f"Expected ≥ 3 hospitals at Gangnam-gu (xPos=127.047, yPos=37.517, radius=2000), "
            f"got {len(items)}. total_count={result['total_count']}"
        )
        for item in items:
            assert item.get("yadmNm"), f"Hospital missing name: {item}"


# ---------------------------------------------------------------------------
# llm_description 5-section structure assertions
# ---------------------------------------------------------------------------


class TestHiraV4Description:
    """llm_description 5-section structural assertions (Spec 2522 T019 description schema)."""

    def test_description_non_empty(self) -> None:
        """_HIRA_DESCRIPTION is a non-empty string."""
        assert isinstance(_HIRA_DESCRIPTION, str)
        assert len(_HIRA_DESCRIPTION) > 50

    def test_description_mentions_purpose_hira(self) -> None:
        """Section 1 purpose: mentions HIRA and hospital registry."""
        desc = _HIRA_DESCRIPTION.lower()
        assert "hira" in desc
        assert "hospital" in desc or "의료" in _HIRA_DESCRIPTION

    def test_description_mentions_xpos_longitude_quirk(self) -> None:
        """Section 2 input_quirk: xPos = longitude (lon) agency naming noted."""
        assert "xPos" in _HIRA_DESCRIPTION or "xpos" in _HIRA_DESCRIPTION.lower()
        assert "lon" in _HIRA_DESCRIPTION.lower() or "longitude" in _HIRA_DESCRIPTION.lower()

    def test_description_mentions_ypos_latitude_quirk(self) -> None:
        """Section 2 input_quirk: yPos = latitude (lat) agency naming noted."""
        assert "yPos" in _HIRA_DESCRIPTION or "ypos" in _HIRA_DESCRIPTION.lower()
        assert "lat" in _HIRA_DESCRIPTION.lower() or "latitude" in _HIRA_DESCRIPTION.lower()

    def test_description_mentions_underscore_type_domain_quirk(self) -> None:
        """Section 4 domain_quirk: '_type=json' (underscore prefix) noted."""
        assert "_type=json" in _HIRA_DESCRIPTION or "_type" in _HIRA_DESCRIPTION

    def test_description_mentions_resolve_location(self) -> None:
        """Section 5 self_contained_decl: resolve_location chain guidance present."""
        assert "resolve_location" in _HIRA_DESCRIPTION

    def test_tool_llm_description_matches_built_description(self) -> None:
        """HIRA_HOSPITAL_SEARCH_TOOL.llm_description equals _HIRA_DESCRIPTION."""
        assert HIRA_HOSPITAL_SEARCH_TOOL.llm_description == _HIRA_DESCRIPTION

    def test_description_five_sections_separated_by_blank_lines(self) -> None:
        """build_description_v4 joins sections with double newline — at least 4 separators."""
        sections = _HIRA_DESCRIPTION.split("\n\n")
        assert len(sections) >= 5, (
            f"Expected ≥ 5 sections (double-newline separated), got {len(sections)}: "
            f"{[s[:40] for s in sections]}"
        )
