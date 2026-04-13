# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.tools.geocoding.kakao_client."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from kosmos.tools.errors import ConfigurationError, ToolExecutionError
from kosmos.tools.geocoding.kakao_client import (
    KakaoAddressDocument,
    KakaoSearchMeta,
    KakaoSearchResult,
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
# TestSearchAddress
# ---------------------------------------------------------------------------


class TestSearchAddress:
    @pytest.mark.asyncio
    async def test_happy_path_gangnam(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key-123")
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
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key-123")
        fixture = _load_fixture("address_to_region_nonsense.json")
        mock_client = _make_mock_client(fixture)

        result = await search_address("nonsense xyz 12345", client=mock_client)
        assert result.documents == []

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_config_error(self, monkeypatch):
        monkeypatch.delenv("KOSMOS_KAKAO_API_KEY", raising=False)
        with pytest.raises(ConfigurationError):
            await search_address("서울 강남구")

    @pytest.mark.asyncio
    async def test_http_401_raises_tool_execution_error(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "bad-key")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 401
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        with pytest.raises(ToolExecutionError) as exc_info:
            await search_address("서울 강남구", client=mock_client)
        assert "401" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_http_429_raises_tool_execution_error(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.headers = {"content-type": "application/json"}
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        with pytest.raises(ToolExecutionError) as exc_info:
            await search_address("서울 강남구", client=mock_client)
        assert "429" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_raises_tool_execution_error(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")

        with pytest.raises(ToolExecutionError) as exc_info:
            await search_address("서울 강남구", client=mock_client)
        assert "timed out" in str(exc_info.value).lower()
