# SPDX-License-Identifier: Apache-2.0
"""Live validation tests for KMA forecast and pre-warning adapter endpoints.

Tests hit the REAL KMA APIs via data.go.kr.  They hard-fail on any network or
API error — no silent skips on unavailability.  Assertions are limited to
response *structure*, not specific data values, because weather data changes
constantly.

Required environment variable: ``KOSMOS_DATA_GO_KR_API_KEY``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from kosmos.tools.kma.kma_pre_warning import (
    KmaPreWarningInput,
    KmaPreWarningOutput,
)
from kosmos.tools.kma.kma_pre_warning import (
    _call as _pre_warning_call,
)
from kosmos.tools.kma.kma_short_term_forecast import (
    KmaShortTermForecastInput,
    KmaShortTermForecastOutput,
)
from kosmos.tools.kma.kma_short_term_forecast import (
    _call as _short_term_call,
)
from kosmos.tools.kma.kma_ultra_short_term_forecast import (
    KmaUltraShortTermForecastInput,
    KmaUltraShortTermForecastOutput,
)
from kosmos.tools.kma.kma_ultra_short_term_forecast import (
    _call as _ultra_short_term_call,
)

# ---------------------------------------------------------------------------
# Datetime helpers
# ---------------------------------------------------------------------------


def _short_term_datetime() -> tuple[str, str]:
    """Return (base_date, base_time) using the most recent published short-term slot.

    The short-term forecast publishes at 0200, 0500, 0800, 1100, 1400, 1700,
    2000, 2300 KST (UTC+9).  We subtract one publish cycle (3 hours) from now
    to ensure the data is already available.

    Returns:
        A tuple of (YYYYMMDD, HHMM) strings.
    """
    now = datetime.now(UTC) + timedelta(hours=9)  # Convert to KST
    # Walk back to the most recent valid base_time
    publish_hours = [2, 5, 8, 11, 14, 17, 20, 23]
    # Subtract 3 hours to avoid data-not-ready edge cases
    adjusted = now - timedelta(hours=3)
    for h in reversed(publish_hours):
        if adjusted.hour >= h:
            base_time = f"{h:02d}00"
            base_date = adjusted.strftime("%Y%m%d")
            return base_date, base_time
    # Wrap to previous day at 2300
    prev_day = adjusted - timedelta(days=1)
    return prev_day.strftime("%Y%m%d"), "2300"


def _ultra_short_term_datetime() -> tuple[str, str]:
    """Return (base_date, base_time) using the previous half-hour slot.

    The ultra-short-term forecast publishes every hour at HH:30 KST.
    We subtract one hour to ensure data is available.

    Returns:
        A tuple of (YYYYMMDD, HHMM) strings.
    """
    now = datetime.now(UTC) + timedelta(hours=9)  # Convert to KST
    prev = now - timedelta(hours=1)
    base_date = prev.strftime("%Y%m%d")
    base_time = f"{prev.hour:02d}30"
    return base_date, base_time


# ---------------------------------------------------------------------------
# Short-term forecast tests
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_kma_short_term_forecast_basic(
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call the real KMA getVilageFcst endpoint for Seoul and verify response structure.

    Uses Seoul grid coordinates (nx=61, ny=126) and the most recently published
    base time.  Verifies that total_count is non-negative and items is a list.
    """
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    base_date, base_time = _short_term_datetime()
    inp = KmaShortTermForecastInput(
        base_date=base_date,
        base_time=base_time,
        nx=61,
        ny=126,
        num_of_rows=20,
    )
    result = await _short_term_call(inp)

    assert "total_count" in result, "Missing key 'total_count' in short-term forecast response"
    assert "items" in result, "Missing key 'items' in short-term forecast response"

    assert isinstance(result["total_count"], int), (
        f"'total_count' must be int, got {type(result['total_count'])!r}"
    )
    assert result["total_count"] >= 0, f"'total_count' must be >= 0, got {result['total_count']}"
    assert isinstance(result["items"], list), f"'items' must be list, got {type(result['items'])!r}"

    if result["items"]:
        first = result["items"][0]
        assert "category" in first, "Missing field 'category' in first forecast item"
        assert "fcst_value" in first, "Missing field 'fcst_value' in first forecast item"
        assert "fcst_date" in first, "Missing field 'fcst_date' in first forecast item"
        assert "fcst_time" in first, "Missing field 'fcst_time' in first forecast item"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_kma_short_term_forecast_parses_to_model(
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the raw _call() dict validates cleanly into KmaShortTermForecastOutput."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    base_date, base_time = _short_term_datetime()
    inp = KmaShortTermForecastInput(
        base_date=base_date,
        base_time=base_time,
        nx=61,
        ny=126,
        num_of_rows=20,
    )
    result = await _short_term_call(inp)

    output = KmaShortTermForecastOutput.model_validate(result)
    assert isinstance(output, KmaShortTermForecastOutput)
    assert output.total_count >= 0
    assert isinstance(output.items, list)


# ---------------------------------------------------------------------------
# Ultra-short-term forecast tests
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_kma_ultra_short_term_forecast_basic(
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call the real KMA getUltraSrtFcst endpoint for Seoul and verify response structure.

    Uses Seoul grid coordinates (nx=61, ny=126) and the previous half-hour slot.
    Verifies that total_count is non-negative and items is a list.
    """
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    base_date, base_time = _ultra_short_term_datetime()
    inp = KmaUltraShortTermForecastInput(
        base_date=base_date,
        base_time=base_time,
        nx=61,
        ny=126,
    )
    result = await _ultra_short_term_call(inp)

    assert "total_count" in result, (
        "Missing key 'total_count' in ultra-short-term forecast response"
    )
    assert "items" in result, "Missing key 'items' in ultra-short-term forecast response"

    assert isinstance(result["total_count"], int), (
        f"'total_count' must be int, got {type(result['total_count'])!r}"
    )
    assert result["total_count"] >= 0, f"'total_count' must be >= 0, got {result['total_count']}"
    assert isinstance(result["items"], list), f"'items' must be list, got {type(result['items'])!r}"

    if result["items"]:
        first = result["items"][0]
        assert "category" in first, "Missing field 'category' in first forecast item"
        assert "fcst_value" in first, "Missing field 'fcst_value' in first forecast item"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_kma_ultra_short_term_forecast_parses_to_model(
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the raw _call() dict validates cleanly into KmaUltraShortTermForecastOutput."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    base_date, base_time = _ultra_short_term_datetime()
    inp = KmaUltraShortTermForecastInput(
        base_date=base_date,
        base_time=base_time,
        nx=61,
        ny=126,
    )
    result = await _ultra_short_term_call(inp)

    output = KmaUltraShortTermForecastOutput.model_validate(result)
    assert isinstance(output, KmaUltraShortTermForecastOutput)
    assert output.total_count >= 0
    assert isinstance(output.items, list)


# ---------------------------------------------------------------------------
# Pre-warning tests
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_kma_pre_warning_basic(
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Call the real KMA getWthrPwnList endpoint and verify response structure.

    Verifies that the result contains ``total_count`` (int >= 0) and
    ``items`` (list).  Pre-warnings may not always be active; this test
    accepts an empty result as valid.
    """
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    inp = KmaPreWarningInput()
    result = await _pre_warning_call(inp)

    assert "total_count" in result, "Missing key 'total_count' in pre-warning response"
    assert "items" in result, "Missing key 'items' in pre-warning response"

    assert isinstance(result["total_count"], int), (
        f"'total_count' must be int, got {type(result['total_count'])!r}"
    )
    assert result["total_count"] >= 0, f"'total_count' must be >= 0, got {result['total_count']}"
    assert isinstance(result["items"], list), f"'items' must be list, got {type(result['items'])!r}"

    if result["items"]:
        first = result["items"][0]
        assert "stn_id" in first, "Missing field 'stn_id' in first pre-warning item"
        assert "title" in first, "Missing field 'title' in first pre-warning item"
        assert "tm_fc" in first, "Missing field 'tm_fc' in first pre-warning item"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_kma_pre_warning_parses_to_model(
    data_go_kr_api_key: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the raw _call() dict validates cleanly into KmaPreWarningOutput."""
    monkeypatch.setenv("KOSMOS_DATA_GO_KR_API_KEY", data_go_kr_api_key)

    inp = KmaPreWarningInput()
    result = await _pre_warning_call(inp)

    output = KmaPreWarningOutput.model_validate(result)
    assert isinstance(output, KmaPreWarningOutput)
    assert output.total_count >= 0
    assert isinstance(output.items, list)
