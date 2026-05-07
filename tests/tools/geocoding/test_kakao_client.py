# SPDX-License-Identifier: Apache-2.0
"""Tests for ummaya.tools.geocoding.kakao_client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from ummaya.tools.errors import ConfigurationError
from ummaya.tools.geocoding.kakao_client import (
    KakaoAddressDocument,
    KakaoCoord2RegionResult,
    KakaoRegionDocument,
    KakaoSearchMeta,
    KakaoSearchResult,
    coord_to_region_code,
    search_address,
)

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text())


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
# TestKakaoSearchMeta
# ---------------------------------------------------------------------------


class TestKakaoSearchMeta:
    def test_default_values(self):
        meta = KakaoSearchMeta()
        assert meta.total_count == 0
        assert meta.pageable_count == 0
        assert meta.is_end is True

    def test_populated(self):
        meta = KakaoSearchMeta(total_count=3, pageable_count=3, is_end=False)
        assert meta.total_count == 3
        assert meta.is_end is False


# ---------------------------------------------------------------------------
# TestKakaoSearchResult
# ---------------------------------------------------------------------------


class TestKakaoSearchResult:
    def test_empty_documents(self):
        result = KakaoSearchResult(meta=KakaoSearchMeta(), documents=[])
        assert result.documents == []
        assert result.meta.total_count == 0

    def test_gangnam_fixture(self):
        data = _load_fixture("address_to_region_gangnam.json")
        result = KakaoSearchResult(**data)
        assert result.meta.total_count == 1
        assert len(result.documents) == 1
        doc = result.documents[0]
        assert isinstance(doc, KakaoAddressDocument)
        assert doc.road_address is not None
        assert doc.road_address.region_1depth_name == "서울특별시"
        assert doc.road_address.region_2depth_name == "강남구"

    def test_busan_fixture(self):
        data = _load_fixture("address_to_region_busan.json")
        result = KakaoSearchResult(**data)
        assert result.meta.total_count == 1
        doc = result.documents[0]
        assert doc.road_address is not None
        assert doc.road_address.region_1depth_name == "부산광역시"
        assert doc.road_address.region_2depth_name == "해운대구"

    def test_no_results_fixture(self):
        data = _load_fixture("address_to_region_nonsense.json")
        result = KakaoSearchResult(**data)
        assert result.meta.total_count == 0
        assert result.documents == []


# ---------------------------------------------------------------------------
# TestKakaoCoord2RegionResult
# ---------------------------------------------------------------------------


class TestKakaoCoord2RegionResult:
    def test_hadan_region_payload_shape(self):
        payload = {
            "meta": {"total_count": 2},
            "documents": [
                {
                    "region_type": "B",
                    "address_name": "부산광역시 사하구 하단동",
                    "region_1depth_name": "부산광역시",
                    "region_2depth_name": "사하구",
                    "region_3depth_name": "하단동",
                    "region_4depth_name": "",
                    "code": "2638010300",
                    "x": 128.96044110450242,
                    "y": 35.11437276296668,
                }
            ],
        }

        result = KakaoCoord2RegionResult(**payload)

        assert result.meta.total_count == 2
        assert isinstance(result.documents[0], KakaoRegionDocument)
        assert result.documents[0].region_1depth_name == "부산광역시"
        assert result.documents[0].region_2depth_name == "사하구"


# ---------------------------------------------------------------------------
# TestSearchAddress
# ---------------------------------------------------------------------------


class TestSearchAddress:
    @pytest.mark.asyncio
    async def test_happy_path_gangnam(self, monkeypatch):
        monkeypatch.setenv("UMMAYA_KAKAO_API_KEY", "test-key-123")
        fixture = _load_fixture("address_to_region_gangnam.json")
        mock_client = _make_mock_client(fixture)

        result = await search_address("서울특별시 강남구 테헤란로 152", client=mock_client)

        assert result.meta.total_count == 1
        assert len(result.documents) == 1
        doc = result.documents[0]
        assert doc.road_address is not None
        assert doc.road_address.region_1depth_name == "서울특별시"

    @pytest.mark.asyncio
    async def test_no_results(self, monkeypatch):
        monkeypatch.setenv("UMMAYA_KAKAO_API_KEY", "test-key-123")
        fixture = _load_fixture("address_to_region_nonsense.json")
        mock_client = _make_mock_client(fixture)

        result = await search_address("nonsense xyz 12345", client=mock_client)
        assert result.documents == []

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("UMMAYA_KAKAO_API_KEY", raising=False)
        with pytest.raises(ConfigurationError):
            await search_address("서울 강남구")

    @pytest.mark.asyncio
    async def test_http_401_propagates_as_http_status_error(self, monkeypatch):
        monkeypatch.setenv("UMMAYA_KAKAO_API_KEY", "bad-key")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "401 Unauthorized", request=MagicMock(), response=mock_response
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await search_address("서울 강남구", client=mock_client)

    @pytest.mark.asyncio
    async def test_http_429_propagates_as_http_status_error(self, monkeypatch):
        monkeypatch.setenv("UMMAYA_KAKAO_API_KEY", "test-key")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "429 Too Many Requests", request=MagicMock(), response=mock_response
        )
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        with pytest.raises(httpx.HTTPStatusError):
            await search_address("서울 강남구", client=mock_client)

    @pytest.mark.asyncio
    async def test_timeout_propagates_as_httpx_exception(self, monkeypatch):
        monkeypatch.setenv("UMMAYA_KAKAO_API_KEY", "test-key")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(httpx.TimeoutException):
            await search_address("서울 강남구", client=mock_client)


class TestCoordToRegionCode:
    @pytest.mark.asyncio
    async def test_coord_to_region_code_uses_xy_params(self, monkeypatch):
        monkeypatch.setenv("UMMAYA_KAKAO_API_KEY", "test-key-123")
        fixture = {
            "meta": {"total_count": 1},
            "documents": [
                {
                    "region_type": "B",
                    "address_name": "부산광역시 사하구 하단동",
                    "region_1depth_name": "부산광역시",
                    "region_2depth_name": "사하구",
                    "region_3depth_name": "하단동",
                    "region_4depth_name": "",
                    "code": "2638010300",
                    "x": 128.96044110450242,
                    "y": 35.11437276296668,
                }
            ],
        }
        mock_client = _make_mock_client(fixture)

        result = await coord_to_region_code(
            lon=128.966786546793,
            lat=35.1062385683347,
            client=mock_client,
        )

        assert result.documents[0].region_2depth_name == "사하구"
        _, kwargs = mock_client.get.call_args
        assert kwargs["params"]["x"] == 128.966786546793
        assert kwargs["params"]["y"] == 35.1062385683347
        assert kwargs["params"]["input_coord"] == "WGS84"
