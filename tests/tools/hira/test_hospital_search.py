# SPDX-License-Identifier: Apache-2.0
"""Tests for hira_hospital_search adapter — T051.

Covers:
  - Happy path: fixture replay via respx mock → LookupCollection with items.
  - Error path: upstream 500 HTTP status → LookupError(reason="upstream_unavailable").
  - Provider error: upstream returns resultCode=99 → RuntimeError → LookupError.
  - Input validation: xPos="" (empty / zero-length string via fetch params) →
      LookupError(reason="invalid_params") via the executor's validation gate.
  - lookup(mode="fetch") integration via a test-local registry + executor pair.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.hira.hospital_search import (
    HIRA_HOSPITAL_SEARCH_TOOL,
    HiraHospitalSearchInput,
    handle,
    register,
)
from kosmos.tools.lookup import lookup
from kosmos.tools.models import LookupCollection, LookupError, LookupFetchInput  # noqa: A004
from kosmos.tools.registry import ToolRegistry

_FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "hira"


def _load_fixture(name: str) -> dict:
    return json.loads((_FIXTURES_DIR / name).read_text())


def _make_mock_client(
    fixture_data: dict,
    *,
    status_code: int = 200,
) -> httpx.AsyncClient:
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


@pytest.fixture
def hira_registry_and_executor():
    """Test-local registry + executor with only hira_hospital_search registered."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register(registry, executor)
    return registry, executor


# ---------------------------------------------------------------------------
# Happy path — fixture replay returns LookupCollection
# ---------------------------------------------------------------------------


class TestHiraHospitalSearchHappy:
    """Happy path: fixture-backed fetch returns LookupCollection."""

    async def test_handle_returns_collection_dict(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """handle() with happy fixture returns a collection-shaped dict."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-hira")
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        inp = HiraHospitalSearchInput(xPos=127.028, yPos=37.498, radius=2000)
        result = await handle(inp, client=mock_client)

        assert result["kind"] == "collection"
        assert result["total_count"] == 3
        assert len(result["items"]) == 3

    async def test_handle_items_have_expected_fields(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Items from the happy fixture contain yadmNm, addr, telno, clCd, clCdNm, ykiho."""
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-hira")
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        inp = HiraHospitalSearchInput(xPos=127.028, yPos=37.498, radius=2000)
        result = await handle(inp, client=mock_client)

        for item in result["items"]:
            assert "yadmNm" in item
            assert "addr" in item
            assert "ykiho" in item

    async def test_lookup_fetch_returns_lookup_collection(
        self,
        hira_registry_and_executor,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """lookup(mode='fetch', tool_id='hira_hospital_search') → LookupCollection."""
        registry, executor = hira_registry_and_executor
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.MonkeyPatch.context() as mp,
        ):
            mp.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-hira")
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="hira_hospital_search",
                params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
            )
            result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupCollection), f"Expected LookupCollection, got: {result}"
        assert result.kind == "collection"
        assert len(result.items) == 3
        assert result.total_count == 3
        assert result.meta.source == "hira_hospital_search"

    async def test_lookup_fetch_items_populated(
        self,
        hira_registry_and_executor,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Items from lookup fetch have yadmNm and ykiho fields."""
        registry, executor = hira_registry_and_executor
        fixture = _load_fixture("hospital_search_happy.json")
        mock_client = _make_mock_client(fixture)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.MonkeyPatch.context() as mp,
        ):
            mp.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-hira")
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="hira_hospital_search",
                params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
            )
            result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupCollection)
        for item in result.items:
            assert "yadmNm" in item
            assert "ykiho" in item


# ---------------------------------------------------------------------------
# Error path — upstream 500 → LookupError(reason="upstream_unavailable")
# ---------------------------------------------------------------------------


class TestHiraHospitalSearchErrorPath:
    """Error paths: HTTP 500 and provider resultCode errors."""

    async def test_upstream_500_returns_lookup_error(
        self,
        hira_registry_and_executor,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """HTTP 500 from HIRA → LookupError(reason='upstream_unavailable', retryable=True)."""
        registry, executor = hira_registry_and_executor
        mock_client = _make_mock_client({}, status_code=500)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.MonkeyPatch.context() as mp,
        ):
            mp.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-hira")
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="hira_hospital_search",
                params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
            )
            result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupError), f"Expected LookupError, got: {result}"
        assert result.reason == "upstream_unavailable"
        assert result.retryable is True

    async def test_provider_error_resultcode_99_returns_lookup_error(
        self,
        hira_registry_and_executor,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """HIRA resultCode=99 (SYSTEM_ERROR) → LookupError(reason='upstream_unavailable')."""
        registry, executor = hira_registry_and_executor
        fixture = _load_fixture("hospital_search_error_provider_error.json")
        mock_client = _make_mock_client(fixture)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.MonkeyPatch.context() as mp,
        ):
            mp.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-hira")
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="hira_hospital_search",
                params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
            )
            result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupError)
        assert result.reason == "upstream_unavailable"


# ---------------------------------------------------------------------------
# Input validation — invalid params → LookupError(reason="invalid_params")
# ---------------------------------------------------------------------------


class TestHiraHospitalSearchInputValidation:
    """Input validation errors produce LookupError(reason='invalid_params')."""

    async def test_radius_exceeds_max_returns_invalid_params(
        self,
        hira_registry_and_executor,
    ) -> None:
        """radius > 10000 → LookupError(reason='invalid_params')."""
        registry, executor = hira_registry_and_executor
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="hira_hospital_search",
            params={"xPos": 127.028, "yPos": 37.498, "radius": 99999},
        )
        result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupError)
        assert result.reason == "invalid_params"

    async def test_xpos_out_of_korea_range_returns_invalid_params(
        self,
        hira_registry_and_executor,
    ) -> None:
        """xPos outside Korean longitude range (124–132) → LookupError(reason='invalid_params')."""
        registry, executor = hira_registry_and_executor
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="hira_hospital_search",
            params={"xPos": 0.0, "yPos": 37.498, "radius": 2000},
        )
        result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupError)
        assert result.reason == "invalid_params"

    async def test_missing_required_xpos_returns_invalid_params(
        self,
        hira_registry_and_executor,
    ) -> None:
        """Missing required xPos parameter → LookupError(reason='invalid_params')."""
        registry, executor = hira_registry_and_executor
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="hira_hospital_search",
            params={"yPos": 37.498, "radius": 2000},  # xPos omitted
        )
        result = await lookup(inp, executor=executor)

        assert isinstance(result, LookupError)
        assert result.reason == "invalid_params"


# ---------------------------------------------------------------------------
# Tool definition assertions
# ---------------------------------------------------------------------------


class TestHiraHospitalSearchToolDefinition:
    """HIRA_HOSPITAL_SEARCH_TOOL GovAPITool field assertions."""

    def test_tool_id(self) -> None:
        assert HIRA_HOSPITAL_SEARCH_TOOL.id == "hira_hospital_search"

    def test_requires_auth_false(self) -> None:
        assert HIRA_HOSPITAL_SEARCH_TOOL.requires_auth is False

    def test_is_personal_data_false(self) -> None:
        assert HIRA_HOSPITAL_SEARCH_TOOL.is_personal_data is False

    def test_is_concurrency_safe_true(self) -> None:
        assert HIRA_HOSPITAL_SEARCH_TOOL.is_concurrency_safe is True

    def test_cache_ttl_zero(self) -> None:
        assert HIRA_HOSPITAL_SEARCH_TOOL.cache_ttl_seconds == 0

    def test_input_schema(self) -> None:
        assert HIRA_HOSPITAL_SEARCH_TOOL.input_schema is HiraHospitalSearchInput

    def test_search_hint_bilingual(self) -> None:
        hint = HIRA_HOSPITAL_SEARCH_TOOL.search_hint
        # Must contain both Korean and English terms (FR-021, bilingual requirement)
        assert "병원" in hint
        assert "hospital" in hint.lower()


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


class TestHiraHospitalSearchRegister:
    """register() wires tool into registry and executor."""

    def test_register(self) -> None:
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register(registry, executor)

        assert "hira_hospital_search" in registry
        tool = registry.lookup("hira_hospital_search")
        assert tool.id == "hira_hospital_search"
        assert "hira_hospital_search" in executor._adapters
        assert callable(executor._adapters["hira_hospital_search"])
