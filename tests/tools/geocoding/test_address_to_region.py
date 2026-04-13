# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.tools.geocoding.address_to_region."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from kosmos.tools.errors import ConfigurationError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.geocoding.address_to_region import (
    ADDRESS_TO_REGION_TOOL,
    AddressToRegionInput,
    AddressToRegionOutput,
    _call,
    _resolve,
    register,
)
from kosmos.tools.registry import ToolRegistry

_FIXTURE_DIR = Path(__file__).parent / "fixtures"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURE_DIR / name).read_text())


def _make_mock_client(fixture_data: dict) -> httpx.AsyncClient:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = fixture_data
    mock_response.raise_for_status = MagicMock()
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.get.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# TestAddressToRegionInput
# ---------------------------------------------------------------------------


class TestAddressToRegionInput:
    def test_valid_address(self):
        inp = AddressToRegionInput(address="서울특별시 강남구 테헤란로 152")
        assert inp.address == "서울특별시 강남구 테헤란로 152"

    def test_empty_address_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AddressToRegionInput(address="")


# ---------------------------------------------------------------------------
# TestResolve
# ---------------------------------------------------------------------------


class TestResolve:
    @pytest.mark.asyncio
    async def test_gangnam_resolves_correctly(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_region_gangnam.json")
        mock_client = _make_mock_client(fixture)

        output = await _resolve("서울특별시 강남구 테헤란로 152", client=mock_client)

        assert isinstance(output, AddressToRegionOutput)
        assert output.region_1depth == "서울특별시"
        assert output.region_2depth == "강남구"
        assert output.sido_code == 11  # SidoCode.SEOUL
        assert output.gugun_code == 680  # GugunCode.SEOUL_GANGNAM
        assert output.latitude is not None
        assert output.longitude is not None

    @pytest.mark.asyncio
    async def test_busan_haeundae_resolves_correctly(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_region_busan.json")
        mock_client = _make_mock_client(fixture)

        output = await _resolve("부산광역시 해운대구 해운대해변로 264", client=mock_client)

        assert output.sido_code == 26  # SidoCode.BUSAN
        assert output.gugun_code == 350  # GugunCode.BUSAN_HAEUNDAE
        assert output.region_1depth == "부산광역시"
        assert output.region_2depth == "해운대구"

    @pytest.mark.asyncio
    async def test_no_results_returns_empty_output(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_region_nonsense.json")
        mock_client = _make_mock_client(fixture)

        output = await _resolve("nonsense xyz 12345", client=mock_client)

        assert output.resolved_address == ""
        assert output.sido_code is None
        assert output.gugun_code is None
        assert output.latitude is None
        assert output.longitude is None


# ---------------------------------------------------------------------------
# TestCall
# ---------------------------------------------------------------------------


class TestCall:
    @pytest.mark.asyncio
    async def test_returns_dict(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_region_gangnam.json")
        mock_client = _make_mock_client(fixture)

        params = AddressToRegionInput(address="서울특별시 강남구 테헤란로 152")
        result = await _call(params, client=mock_client)

        assert isinstance(result, dict)
        assert result["sido_code"] == 11
        assert result["gugun_code"] == 680
        assert result["region_1depth"] == "서울특별시"

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("KOSMOS_KAKAO_API_KEY", raising=False)
        params = AddressToRegionInput(address="서울특별시 강남구")
        with pytest.raises(ConfigurationError):
            await _call(params)


# ---------------------------------------------------------------------------
# TestToolDefinition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    def test_tool_id(self):
        assert ADDRESS_TO_REGION_TOOL.id == "address_to_region"

    def test_requires_auth_true(self):
        assert ADDRESS_TO_REGION_TOOL.requires_auth is True

    def test_is_personal_data_false(self):
        assert ADDRESS_TO_REGION_TOOL.is_personal_data is False

    def test_is_concurrency_safe_true(self):
        assert ADDRESS_TO_REGION_TOOL.is_concurrency_safe is True

    def test_is_core_false(self):
        assert ADDRESS_TO_REGION_TOOL.is_core is False

    def test_cache_ttl_is_positive(self):
        assert ADDRESS_TO_REGION_TOOL.cache_ttl_seconds > 0


# ---------------------------------------------------------------------------
# TestRegister
# ---------------------------------------------------------------------------


class TestRegister:
    def test_register_adds_to_registry_and_executor(self):
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register(registry, executor)
        assert "address_to_region" in registry
        assert "address_to_region" in executor._adapters
