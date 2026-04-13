# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.tools.geocoding.address_to_grid."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from kosmos.tools.errors import ConfigurationError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.geocoding.address_to_grid import (
    ADDRESS_TO_GRID_TOOL,
    AddressToGridInput,
    _call,
    _fallback_local_lookup,
    _resolve_from_kakao,
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
# TestAddressToGridInput
# ---------------------------------------------------------------------------


class TestAddressToGridInput:
    def test_valid_address(self):
        inp = AddressToGridInput(address="서울특별시 서초구 반포대로 201")
        assert inp.address == "서울특별시 서초구 반포대로 201"

    def test_empty_address_raises(self):
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            AddressToGridInput(address="")


# ---------------------------------------------------------------------------
# TestResolveFromKakao
# ---------------------------------------------------------------------------


class TestResolveFromKakao:
    @pytest.mark.asyncio
    async def test_seocho_resolves_grid(self, monkeypatch):
        """Seocho address resolves to a valid KMA grid with source=kakao_latlon."""
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_grid_seocho.json")
        mock_client = _make_mock_client(fixture)

        output = await _resolve_from_kakao("서울특별시 서초구 반포대로 201", client=mock_client)

        assert output.source == "kakao_latlon"
        assert output.nx is not None
        assert output.ny is not None
        assert output.latitude is not None
        assert output.longitude is not None
        # Seocho should map to grid near (61, 124)
        assert isinstance(output.nx, int)
        assert isinstance(output.ny, int)

    @pytest.mark.asyncio
    async def test_haeundae_resolves_grid(self, monkeypatch):
        """Haeundae address resolves to a valid KMA grid with source=kakao_latlon."""
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_grid_haeundae.json")
        mock_client = _make_mock_client(fixture)

        output = await _resolve_from_kakao("부산광역시 해운대구 중동", client=mock_client)

        assert output.source == "kakao_latlon"
        assert output.nx is not None and output.nx > 0
        assert output.ny is not None and output.ny > 0

    @pytest.mark.asyncio
    async def test_no_results_returns_not_found(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_region_nonsense.json")
        mock_client = _make_mock_client(fixture)

        output = await _resolve_from_kakao("nonsense xyz", client=mock_client)

        assert output.source == "not_found"
        assert output.nx is None
        assert output.ny is None


# ---------------------------------------------------------------------------
# TestFallbackLocalLookup
# ---------------------------------------------------------------------------


class TestFallbackLocalLookup:
    def test_seoul_fallback(self):
        """'서울' appears in the static table."""
        output = _fallback_local_lookup("서울")
        assert output.source == "table_fallback"
        assert output.nx == 61
        assert output.ny == 126

    def test_partial_match_by_first_token(self):
        """'서울특별시 강남구 ...' — first token '서울특별시' should match."""
        output = _fallback_local_lookup("서울특별시 강남구 테헤란로 152")
        assert output.source == "table_fallback"
        assert output.nx is not None

    def test_unknown_returns_not_found(self):
        output = _fallback_local_lookup("알수없는지역 알수없는구")
        assert output.source == "not_found"
        assert output.nx is None
        assert output.ny is None


# ---------------------------------------------------------------------------
# TestCall
# ---------------------------------------------------------------------------


class TestCall:
    @pytest.mark.asyncio
    async def test_kakao_success_returns_dict(self, monkeypatch):
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_grid_seocho.json")
        mock_client = _make_mock_client(fixture)

        params = AddressToGridInput(address="서울특별시 서초구 반포대로 201")
        result = await _call(params, client=mock_client)

        assert isinstance(result, dict)
        assert result["source"] == "kakao_latlon"
        assert result["nx"] is not None
        assert result["ny"] is not None

    @pytest.mark.asyncio
    async def test_kakao_timeout_falls_back_to_table(self, monkeypatch):
        """On Kakao timeout, falls back to static table lookup."""
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.side_effect = httpx.TimeoutException("timed out")

        params = AddressToGridInput(address="서울 강남구")
        result = await _call(params, client=mock_client)

        # Should use table fallback for "서울" prefix
        assert result["source"] == "table_fallback"
        assert result["nx"] is not None

    @pytest.mark.asyncio
    async def test_missing_api_key_raises(self, monkeypatch):
        monkeypatch.delenv("KOSMOS_KAKAO_API_KEY", raising=False)
        params = AddressToGridInput(address="서울특별시 강남구")
        with pytest.raises(ConfigurationError):
            await _call(params)

    @pytest.mark.asyncio
    async def test_no_results_tries_fallback(self, monkeypatch):
        """When Kakao returns no results, fallback table is consulted."""
        monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", "test-key")
        fixture = _load_fixture("address_to_region_nonsense.json")
        mock_client = _make_mock_client(fixture)

        params = AddressToGridInput(address="서울")
        result = await _call(params, client=mock_client)

        # Static table has "서울", so fallback should succeed
        assert result["nx"] is not None
        assert result["ny"] is not None


# ---------------------------------------------------------------------------
# TestToolDefinition
# ---------------------------------------------------------------------------


class TestToolDefinition:
    def test_tool_id(self):
        assert ADDRESS_TO_GRID_TOOL.id == "address_to_grid"

    def test_requires_auth_false(self):
        assert ADDRESS_TO_GRID_TOOL.requires_auth is False

    def test_is_personal_data_false(self):
        assert ADDRESS_TO_GRID_TOOL.is_personal_data is False

    def test_is_concurrency_safe_true(self):
        assert ADDRESS_TO_GRID_TOOL.is_concurrency_safe is True

    def test_is_core_false(self):
        assert ADDRESS_TO_GRID_TOOL.is_core is False

    def test_cache_ttl_positive(self):
        assert ADDRESS_TO_GRID_TOOL.cache_ttl_seconds > 0


# ---------------------------------------------------------------------------
# TestRegister
# ---------------------------------------------------------------------------


class TestRegister:
    def test_register_adds_to_registry_and_executor(self):
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register(registry, executor)
        assert "address_to_grid" in registry
        assert "address_to_grid" in executor._adapters
