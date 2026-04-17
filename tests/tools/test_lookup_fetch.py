# SPDX-License-Identifier: Apache-2.0
"""Tests for lookup(mode='fetch') — typed adapter invocation — T021.

Tests use the committed fixture tape and a mocked httpx client.
No live API calls are made.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.lookup import lookup
from kosmos.tools.models import (
    LookupCollection,
    LookupError,  # noqa: A004
    LookupFetchInput,
)
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

_FIXTURE_DIR = Path(__file__).parent.parent / "fixtures" / "koroad"


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


@pytest.fixture(scope="module")
def registry_and_executor():
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register_all_tools(registry, executor)
    return registry, executor


# ---------------------------------------------------------------------------
# T021: happy-path fetch via fixture
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("ignore::pytest.PytestUnraisableExceptionWarning")
class TestLookupFetchHappy:
    @pytest.mark.asyncio
    async def test_fetch_happy_fixture(self, registry_and_executor, monkeypatch):
        """Fetch koroad_accident_hazard_search with happy fixture returns LookupCollection."""
        registry, executor = registry_and_executor
        fixture = _load_fixture("accident_hazard_search_happy.json")
        mock_client = _make_mock_client(fixture)

        # Patch httpx.AsyncClient inside the handler
        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-12345")

        from unittest.mock import patch

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.MonkeyPatch.context() as mp2,
        ):
            mp2.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-12345")
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="koroad_accident_hazard_search",
                params={"adm_cd": "1168000000", "year": 2024},
            )
            # V6: koroad_accident_hazard_search now requires auth_level=AAL1 + requires_auth=True.
            # Provide a test session identity so the executor auth gate passes.
            result = await lookup(inp, executor=executor, session_identity="test-session")

        assert isinstance(result, LookupCollection), f"Expected LookupCollection, got: {result}"
        assert result.kind == "collection"
        assert len(result.items) == 2
        assert result.total_count == 2
        assert result.meta.source == "koroad_accident_hazard_search"

    @pytest.mark.asyncio
    async def test_fetch_items_have_expected_fields(self, registry_and_executor, monkeypatch):
        """Items in the happy fixture must contain spot_nm and occrrnc_cnt."""
        registry, executor = registry_and_executor
        fixture = _load_fixture("accident_hazard_search_happy.json")
        mock_client = _make_mock_client(fixture)

        from unittest.mock import patch

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            pytest.MonkeyPatch.context() as mp,
        ):
            mp.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-12345")
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="koroad_accident_hazard_search",
                params={"adm_cd": "1168000000", "year": 2024},
            )
            # V6: requires_auth=True; provide session identity to pass auth gate.
            result = await lookup(inp, executor=executor, session_identity="test-session")

        assert isinstance(result, LookupCollection)
        for item in result.items:
            assert "spot_nm" in item
            assert "occrrnc_cnt" in item


# ---------------------------------------------------------------------------
# T021: unknown_tool error path
# ---------------------------------------------------------------------------


class TestLookupFetchUnknownTool:
    @pytest.mark.asyncio
    async def test_unknown_tool_returns_lookup_error(self, registry_and_executor):
        """Fetching a non-existent tool_id must return LookupError(reason='unknown_tool')."""
        registry, executor = registry_and_executor
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="nonexistent_tool_abc",
            params={"key": "value"},
        )
        result = await lookup(inp, executor=executor)
        assert isinstance(result, LookupError)
        assert result.reason == "unknown_tool"

    @pytest.mark.asyncio
    async def test_no_executor_returns_lookup_error(self):
        """No executor provided returns LookupError(reason='unknown_tool')."""
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="koroad_accident_hazard_search",
            params={"adm_cd": "1168000000", "year": 2024},
        )
        result = await lookup(inp, executor=None)
        assert isinstance(result, LookupError)
        assert result.reason == "unknown_tool"


# ---------------------------------------------------------------------------
# T021: auth gate (requires_auth=True + no session → auth_required)
# ---------------------------------------------------------------------------


class TestLookupFetchAuthGate:
    @pytest.mark.asyncio
    async def test_auth_required_tool_returns_error_without_identity(self, registry_and_executor):
        """A tool with requires_auth=True + no session identity → LookupError(auth_required)."""
        registry, executor = registry_and_executor
        # kma_weather_alert_status uses requires_auth default (True per fail-closed)
        # Let's verify by checking the tool in registry
        alert_tool = registry.lookup("kma_weather_alert_status")
        if not alert_tool.requires_auth:
            pytest.skip("kma_weather_alert_status has requires_auth=False, skip auth gate test")

        inp = LookupFetchInput(
            mode="fetch",
            tool_id="kma_weather_alert_status",
            params={},
        )
        result = await lookup(inp, executor=executor)
        assert isinstance(result, LookupError)
        assert result.reason == "auth_required"


# ---------------------------------------------------------------------------
# T021: invalid params
# ---------------------------------------------------------------------------


class TestLookupFetchInvalidParams:
    @pytest.mark.asyncio
    async def test_invalid_adm_cd_pattern_returns_error(self, registry_and_executor, monkeypatch):
        """adm_cd not matching ^[0-9]{10}$ → LookupError(reason='invalid_params')."""
        registry, executor = registry_and_executor

        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-12345")
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="koroad_accident_hazard_search",
            params={"adm_cd": "INVALID", "year": 2024},
        )
        # V6: requires_auth=True; provide session identity so auth gate passes,
        # then the input validation gate returns invalid_params.
        result = await lookup(inp, executor=executor, session_identity="test-session")
        assert isinstance(result, LookupError)
        assert result.reason == "invalid_params"
