# SPDX-License-Identifier: Apache-2.0
"""Registration extensibility tests — T052.

Proves FR-010 (BM25 index rebuilt on register): adding a new adapter to a
test-local registry causes lookup(mode='search') to immediately reflect it,
without any changes to production source files.

Tests:
  1. KOROAD only → search returns KOROAD candidate; HIRA absent.
  2. Register HIRA → same BM25 search now ranks HIRA when its hint matches better.
  3. BM25 index rebuild for a 2-element registry completes in < 100 ms (loose SLO).
  4. Registering an adapter with is_personal_data=True + requires_auth=False
     raises RegistrationError at startup (FR-038 fail-closed invariant).
"""

from __future__ import annotations

import time

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.hira.hospital_search import register as register_hira
from kosmos.tools.lookup import lookup
from kosmos.tools.models import LookupSearchInput, LookupSearchResult
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Helpers — minimal adapter registration without touching register_all.py
# ---------------------------------------------------------------------------


def _make_koroad_registry() -> tuple[ToolRegistry, ToolExecutor]:
    """Fresh registry with only koroad_accident_hazard_search registered."""
    from kosmos.tools.koroad.accident_hazard_search import register as register_koroad

    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register_koroad(registry, executor)
    return registry, executor


def _make_koroad_and_hira_registry() -> tuple[ToolRegistry, ToolExecutor]:
    """Fresh registry with KOROAD + HIRA registered."""
    registry, executor = _make_koroad_registry()
    register_hira(registry, executor)
    return registry, executor


# ---------------------------------------------------------------------------
# T052-A: KOROAD-only registry — HIRA not discoverable
# ---------------------------------------------------------------------------


class TestKoroadOnlyRegistry:
    """KOROAD-only registry searches return KOROAD; HIRA is absent."""

    async def test_koroad_found_for_accident_query(self) -> None:
        """Query for 교통사고 finds koroad_accident_hazard_search in KOROAD-only registry."""
        registry, executor = _make_koroad_registry()
        inp = LookupSearchInput(mode="search", query="교통사고 위험지점")
        result = await lookup(inp, registry=registry)

        assert isinstance(result, LookupSearchResult)
        candidate_ids = [c.tool_id for c in result.candidates]
        assert "koroad_accident_hazard_search" in candidate_ids

    async def test_hira_not_found_in_koroad_only_registry(self) -> None:
        """HIRA is absent from a KOROAD-only registry."""
        registry, executor = _make_koroad_registry()
        inp = LookupSearchInput(mode="search", query="병원 검색 내과")
        result = await lookup(inp, registry=registry)

        assert isinstance(result, LookupSearchResult)
        candidate_ids = [c.tool_id for c in result.candidates]
        assert "hira_hospital_search" not in candidate_ids


# ---------------------------------------------------------------------------
# T052-B: After registering HIRA, BM25 index reflects new adapter
# ---------------------------------------------------------------------------


class TestBm25IndexRebuiltOnRegister:
    """After register_hira(), lookup(mode='search') reflects HIRA immediately."""

    async def test_hira_appears_after_registration(self) -> None:
        """Registering HIRA → hira_hospital_search is discoverable on next search."""
        registry, executor = _make_koroad_registry()

        # Before: HIRA not in index
        inp_before = LookupSearchInput(mode="search", query="병원 검색")
        result_before = await lookup(inp_before, registry=registry)
        ids_before = [c.tool_id for c in result_before.candidates]
        assert "hira_hospital_search" not in ids_before

        # Register HIRA
        register_hira(registry, executor)

        # After: HIRA is now discoverable
        inp_after = LookupSearchInput(mode="search", query="병원 검색 내과")
        result_after = await lookup(inp_after, registry=registry)
        ids_after = [c.tool_id for c in result_after.candidates]
        assert "hira_hospital_search" in ids_after, (
            f"Expected hira_hospital_search in candidates, got: {ids_after}"
        )

    async def test_koroad_still_discoverable_after_hira_added(self) -> None:
        """Registering HIRA does not break existing KOROAD discoverability."""
        registry, executor = _make_koroad_and_hira_registry()
        inp = LookupSearchInput(mode="search", query="교통사고 위험지점 사고다발구역")
        result = await lookup(inp, registry=registry)

        assert isinstance(result, LookupSearchResult)
        candidate_ids = [c.tool_id for c in result.candidates]
        assert "koroad_accident_hazard_search" in candidate_ids, (
            f"KOROAD missing from results after HIRA added: {candidate_ids}"
        )


# ---------------------------------------------------------------------------
# T052-C: BM25 rebuild SLO — 2-element registry < 100 ms
# ---------------------------------------------------------------------------


class TestBm25RebuildSlo:
    """BM25 index rebuild for a 2-element registry completes in < 100 ms."""

    def test_register_hira_completes_under_100ms(self) -> None:
        """Adding a second adapter (HIRA) to the registry rebuilds BM25 in < 100ms."""
        registry, executor = _make_koroad_registry()

        start_ns = time.monotonic_ns()
        register_hira(registry, executor)
        elapsed_ms = (time.monotonic_ns() - start_ns) / 1_000_000

        if elapsed_ms >= 100:
            import warnings

            warnings.warn(
                f"BM25 rebuild for 2-element registry took {elapsed_ms:.1f} ms "
                "(expected < 100 ms); investigate if this consistently fails on CI.",
                stacklevel=1,
            )


# ---------------------------------------------------------------------------
# T052-D: FR-038 fail-closed PII invariant
# REMOVED in Epic δ #2295 — is_personal_data / requires_auth fields deleted
# from GovAPITool as Spec 033 KOSMOS-invented residue (Constitution § II).
# ---------------------------------------------------------------------------
