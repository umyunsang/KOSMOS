# SPDX-License-Identifier: Apache-2.0
"""Tests for lookup(mode='search') top_k adaptive clamping — T036.

Verifies the adaptive top_k clamp contract (FR-009):
    effective_top_k = max(1, min(top_k if top_k else default_k, len(registry), 20))

Test cases:
    1. top_k=None → effective 5 (default from KOSMOS_LOOKUP_TOPK, default=5).
    2. top_k=0     → LookupSearchInput clamps min to 1 (ge=1 validator).
       We test the boundary by using top_k=1 explicitly.
    3. top_k=99    → LookupSearchInput clamps max to 20 (le=20 validator),
       then effective = min(20, len(registry)).
    4. Registry size 4 → effective_top_k = 4 when requested > 4.

No live API calls are made.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from kosmos.tools.lookup import lookup
from kosmos.tools.models import (
    LookupSearchInput,
    LookupSearchResult,
)
from kosmos.tools.registry import ToolRegistry

# ---------------------------------------------------------------------------
# Minimal fixtures — build small test registries in-process
# ---------------------------------------------------------------------------


class _MinimalInput(BaseModel):
    """Stub input schema for test adapters."""

    q: str = ""


class _MinimalOutput(BaseModel):
    """Stub output schema for test adapters."""

    result: str = ""


def _make_tool(tool_id: str, search_hint: str) -> object:
    """Create a minimal GovAPITool for testing."""
    from kosmos.tools.models import GovAPITool

    return GovAPITool(
        id=tool_id,
        name_ko=f"{tool_id} 도구",
        provider="테스트",
        category=["테스트"],
        endpoint=f"https://example.com/{tool_id}",
        auth_type="public",
        input_schema=_MinimalInput,
        output_schema=_MinimalOutput,
        search_hint=search_hint,
        requires_auth=False,
        is_personal_data=False,
        is_concurrency_safe=True,
        cache_ttl_seconds=0,
        rate_limit_per_minute=10,
    )


def _make_registry(n: int) -> ToolRegistry:
    """Create a registry with exactly *n* tools."""
    registry = ToolRegistry()
    hints = [
        "교통사고 위험지점 accident hazard",
        "날씨 기온 weather forecast temperature",
        "병원 의원 hospital clinic",
        "응급실 병상 emergency room bed",
        "사업자 등록 business registration",
        "환율 외환 exchange rate",
    ]
    for i in range(n):
        tool_id = f"test_tool_{i:02d}"
        hint = hints[i % len(hints)]
        registry.register(_make_tool(tool_id, hint))  # type: ignore[arg-type]
    return registry


# ---------------------------------------------------------------------------
# T036-A: top_k=None → effective 5 (default)
# ---------------------------------------------------------------------------


class TestTopKDefault:
    @pytest.mark.asyncio
    async def test_none_top_k_uses_default_5(self) -> None:
        """When top_k is None, effective_top_k must equal min(5, registry_size)."""
        # Registry size >= 5 so effective should be 5
        registry = _make_registry(6)
        inp = LookupSearchInput(mode="search", query="교통사고", top_k=None)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert result.effective_top_k == 5, (
            f"Expected effective_top_k=5 for top_k=None with 6-tool registry, "
            f"got {result.effective_top_k}"
        )

    @pytest.mark.asyncio
    async def test_none_top_k_clamped_to_registry_size_when_small(self) -> None:
        """When registry_size < 5, effective_top_k = registry_size (not 5)."""
        registry = _make_registry(3)
        inp = LookupSearchInput(mode="search", query="날씨", top_k=None)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert result.effective_top_k == 3, (
            f"Expected effective_top_k=3 for 3-tool registry, got {result.effective_top_k}"
        )

    @pytest.mark.asyncio
    async def test_default_k_result_length_is_at_most_effective_top_k(self) -> None:
        """Number of returned candidates must not exceed effective_top_k."""
        registry = _make_registry(6)
        inp = LookupSearchInput(mode="search", query="교통사고 위험", top_k=None)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert len(result.candidates) <= result.effective_top_k


# ---------------------------------------------------------------------------
# T036-B: top_k model validation (ge=1, le=20 enforced by LookupSearchInput)
# ---------------------------------------------------------------------------


class TestTopKModelValidation:
    def test_top_k_zero_is_rejected_by_model(self) -> None:
        """top_k=0 must be rejected at input validation (ge=1 constraint)."""
        with pytest.raises(ValidationError):
            LookupSearchInput(mode="search", query="test", top_k=0)

    def test_top_k_negative_is_rejected_by_model(self) -> None:
        """top_k=-1 must be rejected at input validation (ge=1 constraint)."""
        with pytest.raises(ValidationError):
            LookupSearchInput(mode="search", query="test", top_k=-1)

    def test_top_k_above_20_is_rejected_by_model(self) -> None:
        """top_k=99 must be rejected at input validation (le=20 constraint)."""
        with pytest.raises(ValidationError):
            LookupSearchInput(mode="search", query="test", top_k=99)

    def test_top_k_21_is_rejected_by_model(self) -> None:
        """top_k=21 must be rejected at input validation (le=20 constraint)."""
        with pytest.raises(ValidationError):
            LookupSearchInput(mode="search", query="test", top_k=21)

    def test_top_k_1_is_valid(self) -> None:
        """top_k=1 is the minimum valid value."""
        inp = LookupSearchInput(mode="search", query="test", top_k=1)
        assert inp.top_k == 1

    def test_top_k_20_is_valid(self) -> None:
        """top_k=20 is the maximum valid value."""
        inp = LookupSearchInput(mode="search", query="test", top_k=20)
        assert inp.top_k == 20


# ---------------------------------------------------------------------------
# T036-C: top_k=20 → effective = min(20, registry_size)
# ---------------------------------------------------------------------------


class TestTopKMaxClamp:
    @pytest.mark.asyncio
    async def test_top_k_20_with_large_registry_clamps_at_20(self) -> None:
        """top_k=20 with a 6-tool registry → effective = min(20, 6) = 6."""
        registry = _make_registry(6)
        inp = LookupSearchInput(mode="search", query="교통사고", top_k=20)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        # effective = min(20, 6) = 6
        assert result.effective_top_k == 6, (
            f"Expected effective_top_k=6 for 6-tool registry with top_k=20, "
            f"got {result.effective_top_k}"
        )

    @pytest.mark.asyncio
    async def test_result_count_does_not_exceed_registry_size(self) -> None:
        """Number of candidates must never exceed registry size."""
        registry = _make_registry(4)
        inp = LookupSearchInput(mode="search", query="병원", top_k=20)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert len(result.candidates) <= len(registry)


# ---------------------------------------------------------------------------
# T036-D: Registry size 4 → effective_top_k = 4 when requested > 4
# ---------------------------------------------------------------------------


class TestTopKRegistrySize4:
    @pytest.mark.asyncio
    async def test_registry_size_4_top_k_5_gives_effective_4(self) -> None:
        """With 4-tool registry, top_k=5 → effective = min(5, 4) = 4."""
        registry = _make_registry(4)
        inp = LookupSearchInput(mode="search", query="교통사고", top_k=5)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert result.effective_top_k == 4, (
            f"Expected effective_top_k=4 for 4-tool registry with top_k=5, "
            f"got {result.effective_top_k}"
        )

    @pytest.mark.asyncio
    async def test_registry_size_4_top_k_20_gives_effective_4(self) -> None:
        """With 4-tool registry, top_k=20 → effective = min(20, 4) = 4."""
        registry = _make_registry(4)
        inp = LookupSearchInput(mode="search", query="날씨", top_k=20)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert result.effective_top_k == 4, (
            f"Expected effective_top_k=4 for 4-tool registry with top_k=20, "
            f"got {result.effective_top_k}"
        )

    @pytest.mark.asyncio
    async def test_registry_size_4_top_k_none_gives_effective_4(self) -> None:
        """With 4-tool registry, top_k=None (default=5) → effective = min(5,4) = 4."""
        registry = _make_registry(4)
        inp = LookupSearchInput(mode="search", query="응급실", top_k=None)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert result.effective_top_k == 4, (
            f"Expected effective_top_k=4 for 4-tool registry with top_k=None, "
            f"got {result.effective_top_k}"
        )

    @pytest.mark.asyncio
    async def test_registry_size_4_candidates_at_most_4(self) -> None:
        """With a 4-tool registry, returned candidates must be <= 4."""
        registry = _make_registry(4)
        inp = LookupSearchInput(mode="search", query="교통사고", top_k=None)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        assert len(result.candidates) <= 4, (
            f"Expected at most 4 candidates for 4-tool registry, got {len(result.candidates)}"
        )

    @pytest.mark.asyncio
    async def test_effective_top_k_in_result_matches_actual_candidates(self) -> None:
        """effective_top_k from result matches number of candidates returned."""
        registry = _make_registry(4)
        inp = LookupSearchInput(mode="search", query="교통사고", top_k=None)
        result = await lookup(inp, registry=registry)
        assert isinstance(result, LookupSearchResult)
        # Candidates count can be less than or equal to effective_top_k
        assert len(result.candidates) <= result.effective_top_k
