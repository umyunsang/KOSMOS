# SPDX-License-Identifier: Apache-2.0
"""Live integration tests for resolve_location_v4 — Spec 2522 US7 T040.

Tests the 4 canonical scenarios documented in
/tmp/kosmos-evidence/geocoding-evidence.md using the Kakao Local API only.
JUSO / SGIS are NOT exercised (keys may not be set).

All tests are decorated with ``@pytest.mark.live`` and are skipped by default.
Run with ``uv run pytest -m live`` to execute against the real API.

Prerequisite: ``KOSMOS_KAKAO_API_KEY`` must be set in the environment.
"""

from __future__ import annotations

import os

import pytest

from kosmos.tools.models import ResolveError, ResolveLocationOutput
from kosmos.tools.resolve_location import resolve_location_v4

_KAKAO_KEY_PRESENT = bool(os.getenv("KOSMOS_KAKAO_API_KEY"))


def _require_kakao() -> None:
    """Skip test if KOSMOS_KAKAO_API_KEY is not configured."""
    if not _KAKAO_KEY_PRESENT:
        pytest.skip("KOSMOS_KAKAO_API_KEY not set — skipping live Kakao test")


# ---------------------------------------------------------------------------
# Scenario 1 — 서울 강남구 (urban administrative district)
# Evidence: b_code=1168000000, lat≈37.517, lon≈127.047
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_scenario_gangnam_gu() -> None:
    """서울 강남구 resolves to known coordinates and b_code via Kakao."""
    _require_kakao()
    result = await resolve_location_v4("서울 강남구")

    assert isinstance(result, ResolveLocationOutput), (
        f"Expected ResolveLocationOutput, got {type(result).__name__}: {result}"
    )

    # 4-field contract
    assert -90 <= result.lat <= 90, f"lat out of range: {result.lat}"
    assert -180 <= result.lon <= 180, f"lon out of range: {result.lon}"
    assert len(result.b_code) == 10 and result.b_code.isdigit(), (
        f"b_code must be 10 digits: {result.b_code!r}"
    )
    assert len(result.address_name) >= 1, "address_name must be non-empty"

    # Known-value assertions from evidence
    assert result.b_code == "1168000000", (
        f"강남구 b_code should be 1168000000, got {result.b_code!r}"
    )
    assert result.lat == pytest.approx(37.517, abs=0.01)
    assert result.lon == pytest.approx(127.047, abs=0.01)

    # Backend constraint
    assert result.source == "kakao", f"v4 path must always be source=kakao, got {result.source!r}"
    assert result.confidence in ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Scenario 2 — 부산 (metropolitan city alone)
# Evidence: b_code=2600000000, lat≈35.180, lon≈129.075
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_scenario_busan() -> None:
    """부산 resolves to known coordinates and b_code via Kakao."""
    _require_kakao()
    result = await resolve_location_v4("부산")

    assert isinstance(result, ResolveLocationOutput), (
        f"Expected ResolveLocationOutput, got {type(result).__name__}: {result}"
    )

    # 4-field contract
    assert -90 <= result.lat <= 90
    assert -180 <= result.lon <= 180
    assert len(result.b_code) == 10 and result.b_code.isdigit()
    assert len(result.address_name) >= 1

    # Known-value assertions from evidence
    assert result.b_code == "2600000000", f"부산 b_code should be 2600000000, got {result.b_code!r}"
    assert result.lat == pytest.approx(35.180, abs=0.01)
    assert result.lon == pytest.approx(129.075, abs=0.01)
    assert result.source == "kakao"


# ---------------------------------------------------------------------------
# Scenario 3 — 제주특별자치도 (provincial-level region)
# Evidence: b_code=5000000000, lat≈33.489, lon≈126.498
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_scenario_jeju() -> None:
    """제주특별자치도 resolves to known coordinates and b_code via Kakao."""
    _require_kakao()
    result = await resolve_location_v4("제주특별자치도")

    assert isinstance(result, ResolveLocationOutput), (
        f"Expected ResolveLocationOutput, got {type(result).__name__}: {result}"
    )

    # 4-field contract
    assert -90 <= result.lat <= 90
    assert -180 <= result.lon <= 180
    assert len(result.b_code) == 10 and result.b_code.isdigit()
    assert len(result.address_name) >= 1

    # Known-value assertions from evidence
    assert result.b_code == "5000000000", (
        f"제주특별자치도 b_code should be 5000000000, got {result.b_code!r}"
    )
    assert result.lat == pytest.approx(33.489, abs=0.01)
    assert result.lon == pytest.approx(126.498, abs=0.01)
    assert result.source == "kakao"


# ---------------------------------------------------------------------------
# Scenario 4 — 존재하지않는주소 (non-existent address → ResolveError)
# Evidence: Kakao returns 0 documents; expect not_found error.
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_scenario_nonexistent_address() -> None:
    """A non-existent address returns a ResolveError with reason not_found."""
    _require_kakao()
    result = await resolve_location_v4("존재하지않는주소")

    assert isinstance(result, ResolveError), (
        f"Expected ResolveError for non-existent address, got {type(result).__name__}: {result}"
    )
    assert result.reason == "not_found", f"Expected reason='not_found', got {result.reason!r}"
    assert "존재하지않는주소" in result.message


# ---------------------------------------------------------------------------
# Unit tests — no live API calls
# ---------------------------------------------------------------------------


class TestResolveLocationOutputModel:
    """Validate ResolveLocationOutput v4 model constraints (pure-unit, no network)."""

    def test_valid_construction(self) -> None:
        out = ResolveLocationOutput(
            lat=37.517,
            lon=127.047,
            b_code="1168000000",
            address_name="서울 강남구",
            confidence="high",
            source="kakao",
        )
        assert out.lat == pytest.approx(37.517)
        assert out.b_code == "1168000000"
        assert out.source == "kakao"

    def test_frozen_immutable(self) -> None:
        """Model must be immutable (frozen=True)."""
        from pydantic import ValidationError

        out = ResolveLocationOutput(
            lat=37.0,
            lon=127.0,
            b_code="1168000000",
            address_name="강남구",
            confidence="medium",
            source="kakao",
        )
        with pytest.raises((TypeError, ValidationError)):
            out.lat = 38.0  # type: ignore[misc]

    def test_extra_fields_forbidden(self) -> None:
        """extra='forbid' rejects unknown fields."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResolveLocationOutput(
                lat=37.0,
                lon=127.0,
                b_code="1168000000",
                address_name="강남구",
                confidence="high",
                source="kakao",
                unknown_field="x",  # type: ignore[call-arg]
            )

    def test_b_code_pattern_enforced(self) -> None:
        """b_code must match ^[0-9]{10}$."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResolveLocationOutput(
                lat=37.0,
                lon=127.0,
                b_code="SHORT",  # not 10 digits
                address_name="강남구",
                confidence="high",
                source="kakao",
            )

    def test_lat_range_enforced(self) -> None:
        """lat must be in [-90, 90]."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResolveLocationOutput(
                lat=91.0,  # out of range
                lon=127.0,
                b_code="1168000000",
                address_name="강남구",
                confidence="high",
                source="kakao",
            )

    def test_address_name_min_length(self) -> None:
        """address_name must be at least 1 character."""
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            ResolveLocationOutput(
                lat=37.0,
                lon=127.0,
                b_code="1168000000",
                address_name="",  # empty
                confidence="high",
                source="kakao",
            )

    def test_juso_source_accepted(self) -> None:
        """source field accepts 'juso' for potential future JUSO v4 path."""
        out = ResolveLocationOutput(
            lat=37.0,
            lon=127.0,
            b_code="1168000000",
            address_name="강남구",
            confidence="low",
            source="juso",
        )
        assert out.source == "juso"
