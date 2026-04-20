# SPDX-License-Identifier: Apache-2.0
"""Tests for the main-tool router ministry-scope guard.

Feature: Epic H #1302 (035-onboarding-brand-port), task T033.
Contract: specs/035-onboarding-brand-port/contracts/memdir-ministry-scope-schema.md § 5.
SC-009: refusal raised < 100 ms (pre-network).

Covers:
    I-X3 (fail-closed default when no scope record exists)
    I-13/14 (ministry-code enumeration fidelity)
    FR-016 + SC-009 timing
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

from kosmos.memdir.ministry_scope import (
    CURRENT_SCOPE_VERSION,
    MINISTRY_CODES,
    MinistryOptIn,
    MinistryScopeAcknowledgment,
    write_scope_atomic,
)
from kosmos.tools.main_router import (
    MinistryOptOutRefusal,
    check_ministry_scope,
    ministry_for_tool,
    ministry_korean_name,
    resolve_with_scope_guard,
)

FIXTURE_SESSION = UUID("018f8a72-d4c9-7a1e-9c8b-0b2c3d4e5f60")
UTC = timezone.utc


def _scope_record(
    overrides: dict[str, bool] | None = None,
) -> MinistryScopeAcknowledgment:
    """Build a scope record with the four ministries opted in, overriding
    any pair in `overrides` to the provided state."""
    defaults = {code: True for code in MINISTRY_CODES}
    if overrides:
        defaults.update(overrides)
    return MinistryScopeAcknowledgment(
        scope_version=CURRENT_SCOPE_VERSION,
        timestamp=datetime(2026, 4, 20, 14, 33, 17, tzinfo=UTC),
        session_id=FIXTURE_SESSION,
        ministries=frozenset(
            MinistryOptIn(ministry_code=code, opt_in=optin)
            for code, optin in defaults.items()
        ),
    )


async def _noop_resolver(_tool_id: str, _params: dict[str, Any]) -> str:
    return "resolved"


# ---------------------------------------------------------------------------
# FR-016 — ministry-for-tool prefix mapping
# ---------------------------------------------------------------------------


def test_ministry_for_tool_recognises_all_four_prefixes() -> None:
    assert ministry_for_tool("koroad_accident_hazard_search") == "KOROAD"
    assert ministry_for_tool("kma_forecast_fetch") == "KMA"
    assert ministry_for_tool("hira_hospital_search") == "HIRA"
    assert ministry_for_tool("nmc_emergency_search") == "NMC"


def test_ministry_for_tool_returns_none_for_non_ministry() -> None:
    assert ministry_for_tool("lookup") is None
    assert ministry_for_tool("resolve_location") is None


# ---------------------------------------------------------------------------
# Korean refusal copy
# ---------------------------------------------------------------------------


def test_ministry_korean_names_cover_all_four() -> None:
    assert ministry_korean_name("KOROAD") == "한국도로공사"
    assert ministry_korean_name("KMA") == "기상청"
    assert ministry_korean_name("HIRA") == "건강보험심사평가원"
    assert ministry_korean_name("NMC") == "국립중앙의료원"


# ---------------------------------------------------------------------------
# I-X3 — fail-closed default
# ---------------------------------------------------------------------------


def test_no_scope_record_refuses_all_ministry_tools(tmp_path: Path) -> None:
    """When no scope record exists, every ministry-bound tool must refuse."""
    for tool_id in [
        "koroad_accident_hazard_search",
        "kma_forecast_fetch",
        "hira_hospital_search",
        "nmc_emergency_search",
    ]:
        result = check_ministry_scope(tool_id, memdir_root=tmp_path)
        assert isinstance(result, MinistryOptOutRefusal)


def test_no_scope_record_passes_non_ministry_tools(tmp_path: Path) -> None:
    assert check_ministry_scope("lookup", memdir_root=tmp_path) == "pass"


# ---------------------------------------------------------------------------
# Opt-in success path
# ---------------------------------------------------------------------------


def test_opt_in_success() -> None:
    scope = _scope_record()
    result = check_ministry_scope(
        "hira_hospital_search", memdir_root=Path("/nonexistent"), scope_override=scope,
    )
    assert result == "pass"


# ---------------------------------------------------------------------------
# Opt-out refusal (Korean message + structure)
# ---------------------------------------------------------------------------


def test_opt_out_refusal_carries_korean_message() -> None:
    scope = _scope_record({"HIRA": False})
    result = check_ministry_scope(
        "hira_hospital_search",
        memdir_root=Path("/nonexistent"),
        scope_override=scope,
    )
    assert isinstance(result, MinistryOptOutRefusal)
    assert result.ministry == "HIRA"
    assert "건강보험심사평가원의 데이터 사용에 동의하지 않으셨습니다" in result.message
    assert "다시 온보딩을 실행하시려면" in result.message


# ---------------------------------------------------------------------------
# SC-009 — < 100 ms refusal latency (with filesystem read)
# ---------------------------------------------------------------------------


def test_refusal_latency_under_100ms(tmp_path: Path) -> None:
    """Writes a real declined-HIRA scope record, then times the refusal."""
    base = tmp_path
    scope_dir = base / "user" / "ministry-scope"
    write_scope_atomic(_scope_record({"HIRA": False}), scope_dir)

    # Warm filesystem cache (so first read is not unfairly slow).
    check_ministry_scope("hira_hospital_search", memdir_root=base)

    start = time.perf_counter()
    result = check_ministry_scope("hira_hospital_search", memdir_root=base)
    elapsed_ms = (time.perf_counter() - start) * 1000.0

    assert isinstance(result, MinistryOptOutRefusal)
    assert result.ministry == "HIRA"
    assert elapsed_ms < 100.0, f"refusal took {elapsed_ms:.2f} ms (limit 100)"


# ---------------------------------------------------------------------------
# resolve_with_scope_guard — integration wrapper
# ---------------------------------------------------------------------------


def test_resolve_with_scope_guard_raises_refusal(tmp_path: Path) -> None:
    scope_dir = tmp_path / "user" / "ministry-scope"
    write_scope_atomic(_scope_record({"KMA": False}), scope_dir)

    async def run() -> None:
        with pytest.raises(MinistryOptOutRefusal) as excinfo:
            await resolve_with_scope_guard(
                "kma_forecast_fetch", {}, memdir_root=tmp_path, resolver=_noop_resolver
            )
        assert excinfo.value.ministry == "KMA"

    asyncio.run(run())


def test_resolve_with_scope_guard_passes_through_on_opt_in(tmp_path: Path) -> None:
    scope_dir = tmp_path / "user" / "ministry-scope"
    write_scope_atomic(_scope_record(), scope_dir)

    async def run() -> str:
        return await resolve_with_scope_guard(
            "kma_forecast_fetch", {}, memdir_root=tmp_path, resolver=_noop_resolver,
        )

    result = asyncio.run(run())
    assert result == "resolved"


def test_resolve_with_scope_guard_bypasses_non_ministry(tmp_path: Path) -> None:
    """Non-ministry tool_id is allowed through even with no scope record."""

    async def run() -> str:
        return await resolve_with_scope_guard(
            "lookup", {}, memdir_root=tmp_path, resolver=_noop_resolver,
        )

    assert asyncio.run(run()) == "resolved"
