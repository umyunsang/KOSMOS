# SPDX-License-Identifier: Apache-2.0
"""T029 — lookup primitive end-to-end integration tests.

Verifies the Python-side lookup pipeline end-to-end:
  - mode='search': BM25 retrieval over the full registered adapter corpus.
  - mode='fetch': direct adapter invocation via executor (live-network tests
    skipped by default per AGENTS.md hard rule).

No TUI involved.  Registry + executor are instantiated directly.

Live-network gate
-----------------
Tests that invoke real data.go.kr adapters (hira_hospital_search) are marked
``@pytest.mark.live`` and skipped unless the caller explicitly enables them
with ``-m live``.  CI MUST NOT run live tests (AGENTS.md § Hard rules).

References
----------
- specs/1634-tool-system-wiring/contracts/primitive-envelope.md § 2
- src/kosmos/tools/lookup.py
- src/kosmos/tools/register_all.py
"""

from __future__ import annotations

import pytest

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.lookup import lookup
from kosmos.tools.models import (
    AdapterCandidate,
    LookupError,  # noqa: A004 — intentional: `LookupError` is KOSMOS domain model; shadowing is scoped.
    LookupFetchInput,
    LookupSearchInput,
    LookupSearchResult,
)
from kosmos.tools.register_all import register_all_tools
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Module-scoped registry + executor (built once, shared across all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def full_registry() -> ToolRegistry:
    """Full ToolRegistry with all 14 seed adapters registered."""
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register_all_tools(registry, executor)
    return registry


@pytest.fixture(scope="module")
def full_executor(full_registry: ToolRegistry) -> ToolExecutor:
    """ToolExecutor bound to the full registry."""
    return ToolExecutor(full_registry)


# ---------------------------------------------------------------------------
# T029-A: mode='search' — hospital/emergency query
# ---------------------------------------------------------------------------


class TestLookupSearchHospital:
    """BM25 search must surface hospital and emergency adapters for '응급실'."""

    @pytest.mark.asyncio
    async def test_emergency_query_surfaces_hospital_adapter(
        self, full_registry: ToolRegistry, full_executor: ToolExecutor
    ) -> None:
        """lookup(search, '응급실', top_k=3) must include hospital/emergency adapters."""
        inp = LookupSearchInput(mode="search", query="응급실", top_k=3)
        result = await lookup(inp, registry=full_registry, executor=full_executor)

        assert isinstance(result, LookupSearchResult)
        assert result.kind == "search"
        tool_ids = [c.tool_id for c in result.candidates]
        # At least one of the hospital/emergency adapters must rank in top-3
        hospital_adapters = {"hira_hospital_search", "nmc_emergency_search"}
        matching = hospital_adapters & set(tool_ids)
        assert matching, (
            f"Expected one of {hospital_adapters} in top-3; got {tool_ids}"
        )

    @pytest.mark.asyncio
    async def test_search_result_shape(
        self, full_registry: ToolRegistry, full_executor: ToolExecutor
    ) -> None:
        """LookupSearchResult must carry valid AdapterCandidate instances."""
        inp = LookupSearchInput(mode="search", query="응급실 병원", top_k=5)
        result = await lookup(inp, registry=full_registry, executor=full_executor)

        assert isinstance(result, LookupSearchResult)
        assert result.total_registry_size > 0
        assert result.effective_top_k >= 1
        for candidate in result.candidates:
            assert isinstance(candidate, AdapterCandidate)
            assert candidate.score >= 0.0
            assert isinstance(candidate.tool_id, str) and len(candidate.tool_id) > 0

    @pytest.mark.asyncio
    async def test_top_k_clamp(
        self, full_registry: ToolRegistry, full_executor: ToolExecutor
    ) -> None:
        """effective_top_k must not exceed 3 when top_k=3 is requested."""
        inp = LookupSearchInput(mode="search", query="병원", top_k=3)
        result = await lookup(inp, registry=full_registry, executor=full_executor)

        assert isinstance(result, LookupSearchResult)
        assert len(result.candidates) <= 3
        assert result.effective_top_k <= 3

    @pytest.mark.asyncio
    async def test_empty_registry_returns_empty_search(self) -> None:
        """An empty registry must return reason='empty_registry' gracefully."""
        empty_registry = ToolRegistry()
        inp = LookupSearchInput(mode="search", query="응급실")
        result = await lookup(inp, registry=empty_registry)

        assert isinstance(result, LookupSearchResult)
        assert result.candidates == []
        assert result.reason == "empty_registry"

    @pytest.mark.asyncio
    async def test_no_registry_returns_empty_search(self) -> None:
        """No registry provided must return gracefully with empty candidates."""
        inp = LookupSearchInput(mode="search", query="응급실")
        result = await lookup(inp, registry=None)

        assert isinstance(result, LookupSearchResult)
        assert result.candidates == []


# ---------------------------------------------------------------------------
# T029-B: mode='fetch' without executor → LookupError (no live call)
# ---------------------------------------------------------------------------


class TestLookupFetchNoExecutor:
    """Fetch mode without a valid executor must return a structured LookupError."""

    @pytest.mark.asyncio
    async def test_fetch_without_executor_returns_lookup_error(self) -> None:
        """lookup(fetch, no executor) must return LookupError, not raise."""
        inp = LookupFetchInput(
            mode="fetch",
            tool_id="hira_hospital_search",
            params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
        )
        result = await lookup(inp, executor=None)

        assert isinstance(result, LookupError)
        assert result.kind == "error"
        assert result.retryable is False


# ---------------------------------------------------------------------------
# T029-C: mode='fetch' via mocked adapter (no live network)
# ---------------------------------------------------------------------------


class TestLookupFetchMocked:
    """Fetch mode with a fixture-backed mock httpx client — no real network."""

    @pytest.mark.asyncio
    async def test_fetch_hira_with_fixture(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """lookup(fetch, hira_hospital_search) with a fixture returns LookupCollection."""
        import json
        from pathlib import Path
        from unittest.mock import AsyncMock, MagicMock, patch

        import httpx

        from kosmos.tools.hira.hospital_search import register
        from kosmos.tools.models import LookupCollection

        # Build a test-local registry + executor with only hira registered
        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        register(registry, executor)

        # Load the existing fixture (matches the pattern in tests/tools/hira/)
        fixture_path = (
            Path(__file__).resolve().parents[2]
            / "tests" / "fixtures" / "hira" / "hospital_search_happy.json"
        )
        fixture_data = json.loads(fixture_path.read_text())

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = fixture_data
        mock_response.raise_for_status = MagicMock()
        mock_client = AsyncMock(spec=httpx.AsyncClient)
        mock_client.get.return_value = mock_response

        monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", "test-key-e2e")

        with patch("httpx.AsyncClient", return_value=mock_client):
            inp = LookupFetchInput(
                mode="fetch",
                tool_id="hira_hospital_search",
                params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
            )
            result = await lookup(inp, executor=executor, session_identity="test-session")

        assert isinstance(result, LookupCollection), (
            f"Expected LookupCollection, got {type(result).__name__}: {result}"
        )
        assert result.kind == "collection"
        assert len(result.items) > 0


# ---------------------------------------------------------------------------
# T029-D: mode='fetch' against live data.go.kr (SKIPPED by default in CI)
# ---------------------------------------------------------------------------


@pytest.mark.live
class TestLookupFetchLive:
    """Live integration tests — skipped unless '-m live' is passed explicitly.

    These tests call the real data.go.kr HIRA API.  They MUST NOT run in CI.
    Requires KOSMOS_DATA_GO_KR_API_KEY to be set in the environment.

    CI contract (AGENTS.md § Hard rules):
        Never call live data.go.kr APIs from CI tests.
    """

    @pytest.mark.asyncio
    async def test_fetch_hira_live(
        self, full_registry: ToolRegistry, full_executor: ToolExecutor
    ) -> None:
        """Live: lookup(fetch, hira_hospital_search) against real HIRA API."""
        import os

        if not os.environ.get("KOSMOS_DATA_GO_KR_API_KEY"):
            pytest.skip("KOSMOS_DATA_GO_KR_API_KEY not set — skipping live fetch test")

        inp = LookupFetchInput(
            mode="fetch",
            tool_id="hira_hospital_search",
            params={"xPos": 127.028, "yPos": 37.498, "radius": 2000},
        )
        result = await lookup(inp, executor=full_executor, session_identity="live-test-session")
        # Live result may be LookupCollection or LookupError depending on quota
        assert hasattr(result, "kind"), f"Unexpected result type: {type(result)}"
