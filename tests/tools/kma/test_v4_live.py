# SPDX-License-Identifier: Apache-2.0
"""KMA v4 live integration tests — @pytest.mark.live only.

Covers all 6 KMA tools with at least 1 live scenario each.
Key regression: test_busan_current_observation_no_invalid_params verifies
Spec 2521 regression fix — KMA call with Busan grid coords must not produce
invalid_params (nx/ny confusion with lat/lon).

Run:
    uv run pytest tests/tools/kma/test_v4_live.py -m live -v
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

# ---------------------------------------------------------------------------
# Skip all tests if env key is absent
# ---------------------------------------------------------------------------

pytestmark = pytest.mark.live

_DATA_GO_KR_KEY_PRESENT = bool(os.environ.get("UMMAYA_DATA_GO_KR_API_KEY"))
_KMA_API_HUB_KEY_PRESENT = bool(os.environ.get("UMMAYA_KMA_API_HUB_AUTH_KEY"))
_SEOUL_TZ = ZoneInfo("Asia/Seoul")


def _skip_if_no_data_go_kr_key() -> None:
    if not _DATA_GO_KR_KEY_PRESENT:
        pytest.skip("UMMAYA_DATA_GO_KR_API_KEY not set — skipping live test")


def _skip_if_no_kma_api_hub_key() -> None:
    if not _KMA_API_HUB_KEY_PRESENT:
        pytest.skip("UMMAYA_KMA_API_HUB_AUTH_KEY not set — skipping live test")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kst_now() -> datetime:
    """Return the current KST wall clock."""
    return datetime.now(_SEOUL_TZ)


def _now_obs_slot() -> tuple[str, str]:
    """Return base_date/base_time for getUltraSrtNcst in KST.

    Minutes >= 10: use current hour; else use previous hour.
    Always returns HH00 and keeps date rollover paired with the time.
    """
    kst = _kst_now()
    slot = kst if kst.minute >= 10 else kst - timedelta(hours=1)
    return slot.strftime("%Y%m%d"), f"{slot.hour:02d}00"


def _now_forecast_slot() -> tuple[str, str]:
    """Return base_date/base_time for getVilageFcst in KST.

    Valid times: 0200, 0500, 0800, 1100, 1400, 1700, 2000, 2300 (KST).
    KMA publishes each slot approximately 10 minutes after its base time.
    """
    _VALID_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]
    now = _kst_now() - timedelta(minutes=10)
    current_hour = now.hour
    past_hours = [h for h in _VALID_HOURS if h <= current_hour]
    if not past_hours:
        prev_day = now - timedelta(days=1)
        return prev_day.strftime("%Y%m%d"), "2300"
    hour = past_hours[-1]
    return now.strftime("%Y%m%d"), f"{hour:02d}00"


def _ultra_short_slot() -> tuple[str, str]:
    """Return base_date/base_time for getUltraSrtFcst latest HH30 in KST."""
    now = _kst_now()
    slot = now if now.minute >= 45 else now - timedelta(hours=1)
    return slot.strftime("%Y%m%d"), f"{slot.hour:02d}30"


# ---------------------------------------------------------------------------
# Tool 1: kma_current_observation
# ---------------------------------------------------------------------------


class TestKmaCurrentObservationLive:
    """Live tests for kma_current_observation (getUltraSrtNcst)."""

    @pytest.mark.asyncio
    async def test_seoul_current_observation(self) -> None:
        """Seoul (nx=61, ny=126) current observation returns valid temperature."""
        _skip_if_no_kma_api_hub_key()

        from ummaya.tools.kma.kma_current_observation import KmaCurrentObservationInput, _call

        base_date, base_time = _now_obs_slot()
        inp = KmaCurrentObservationInput(
            base_date=base_date,
            base_time=base_time,
            nx=61,
            ny=126,
        )
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "t1h" in result or result.get("base_date") is not None
        assert result.get("nx") == 61
        assert result.get("ny") == 126

    @pytest.mark.asyncio
    async def test_busan_current_observation_no_invalid_params(self) -> None:
        """Spec 2521 regression fix — Busan (nx=98, ny=76) must not produce invalid_params.

        This test verifies that the KMA adapter correctly uses KMA grid coords (nx, ny)
        NOT lat/lon.  Busan's grid is (98, 76) — passing lat(35.1)/lon(129.0) would
        fail with invalid range errors (nx 1-149, ny 1-253 check).
        """
        _skip_if_no_kma_api_hub_key()

        from ummaya.tools.kma.kma_current_observation import KmaCurrentObservationInput, _call

        # Busan KMA grid: nx=98, ny=76
        base_date, base_time = _now_obs_slot()
        inp = KmaCurrentObservationInput(
            base_date=base_date,
            base_time=base_time,
            nx=98,
            ny=76,
        )
        result = await _call(inp)

        assert isinstance(result, dict)
        # Must succeed with grid coords, not raise ValidationError or ToolExecutionError
        assert result.get("nx") == 98
        assert result.get("ny") == 76
        # Temperature should be a plausible float (−50 to +50 °C)
        if result.get("t1h") is not None:
            assert -50.0 <= float(result["t1h"]) <= 50.0


# ---------------------------------------------------------------------------
# Tool 2: kma_short_term_forecast
# ---------------------------------------------------------------------------


class TestKmaShortTermForecastLive:
    """Live tests for kma_short_term_forecast (getVilageFcst)."""

    @pytest.mark.asyncio
    async def test_seoul_short_term_forecast(self) -> None:
        """Seoul (nx=61, ny=126) short-term forecast returns ≥1 item."""
        _skip_if_no_kma_api_hub_key()

        from ummaya.tools.kma.kma_short_term_forecast import KmaShortTermForecastInput, _call

        base_date, base_time = _now_forecast_slot()
        inp = KmaShortTermForecastInput(
            base_date=base_date,
            base_time=base_time,
            nx=61,
            ny=126,
            num_of_rows=10,
        )
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "items" in result
        items = result["items"]
        assert isinstance(items, list)
        assert len(items) >= 1
        # Each item has required fields
        first = items[0]
        assert "fcst_date" in first
        assert "fcst_time" in first
        assert "category" in first


# ---------------------------------------------------------------------------
# Tool 3: kma_ultra_short_term_forecast
# ---------------------------------------------------------------------------


class TestKmaUltraShortTermForecastLive:
    """Live tests for kma_ultra_short_term_forecast (getUltraSrtFcst)."""

    @pytest.mark.asyncio
    async def test_seoul_ultra_short_forecast(self) -> None:
        """Seoul (nx=61, ny=126) ultra-short-term forecast returns ≥1 item."""
        _skip_if_no_kma_api_hub_key()

        from ummaya.tools.kma.kma_ultra_short_term_forecast import (
            KmaUltraShortTermForecastInput,
            _call,
        )

        base_date, base_time = _ultra_short_slot()
        inp = KmaUltraShortTermForecastInput(
            base_date=base_date,
            base_time=base_time,
            nx=61,
            ny=126,
            num_of_rows=10,
        )
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "items" in result
        assert isinstance(result["items"], list)
        assert len(result["items"]) >= 1


# ---------------------------------------------------------------------------
# Tool 4: kma_forecast_fetch
# ---------------------------------------------------------------------------


class TestKmaForecastFetchLive:
    """Live tests for kma_forecast_fetch (getVilageFcst, lat/lon variant)."""

    @pytest.mark.asyncio
    async def test_busan_forecast_fetch_by_latlon(self) -> None:
        """Busan by lat/lon — adapter internally converts to nx/ny."""
        _skip_if_no_kma_api_hub_key()

        from ummaya.tools.kma.forecast_fetch import KmaForecastFetchInput, _fetch
        from ummaya.tools.models import LookupTimeseries

        base_date, base_time = _now_forecast_slot()
        inp = KmaForecastFetchInput(
            lat=35.1796,
            lon=129.0756,
            base_date=base_date,
            base_time=base_time,
        )
        result = await _fetch(inp)

        assert isinstance(result, LookupTimeseries)
        assert len(result.points) >= 1


# ---------------------------------------------------------------------------
# Tool 5: kma_pre_warning
# ---------------------------------------------------------------------------


class TestKmaPreWarningLive:
    """Live tests for kma_pre_warning (getWthrWrnList — confirmed 200)."""

    @pytest.mark.asyncio
    async def test_nationwide_pre_warning(self) -> None:
        """Nationwide pre-warning list (no stn_id) returns valid output."""
        _skip_if_no_data_go_kr_key()

        from ummaya.tools.kma.kma_pre_warning import KmaPreWarningInput, _call

        inp = KmaPreWarningInput(num_of_rows=10)
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "total_count" in result
        assert "items" in result
        assert isinstance(result["items"], list)
        # Regardless of alert state (0 or N), structure is valid
        assert result["total_count"] >= 0

    @pytest.mark.asyncio
    async def test_seoul_pre_warning_with_stn_id(self) -> None:
        """Seoul (stn_id=108) pre-warning filtered list is valid."""
        _skip_if_no_data_go_kr_key()

        from ummaya.tools.kma.kma_pre_warning import KmaPreWarningInput, _call

        inp = KmaPreWarningInput(stn_id="108", num_of_rows=10)
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "total_count" in result
        assert isinstance(result["items"], list)


# ---------------------------------------------------------------------------
# Tool 6: kma_weather_alert_status
# ---------------------------------------------------------------------------


class TestKmaWeatherAlertStatusLive:
    """Live tests for kma_weather_alert_status (getWthrWrnList).

    Evidence: empty params perform nationwide active-warning lookup.
    stn_id and tmFc remain optional filters.
    """

    @pytest.mark.asyncio
    async def test_seoul_alert_status_by_stn_id(self) -> None:
        """Seoul (stn_id=108) alert status by stn_id returns valid output."""
        _skip_if_no_data_go_kr_key()

        from ummaya.tools.kma.kma_weather_alert_status import (
            KmaWeatherAlertStatusInput,
            _call,
        )

        inp = KmaWeatherAlertStatusInput(stn_id="108", num_of_rows=10)
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "total_count" in result
        assert "warnings" in result
        assert isinstance(result["warnings"], list)
        assert result["total_count"] >= 0

    @pytest.mark.asyncio
    async def test_jeju_alert_status_by_stn_id(self) -> None:
        """Jeju (stn_id=184) alert status returns valid output (active marine area)."""
        _skip_if_no_data_go_kr_key()

        from ummaya.tools.kma.kma_weather_alert_status import (
            KmaWeatherAlertStatusInput,
            _call,
        )

        inp = KmaWeatherAlertStatusInput(stn_id="184", num_of_rows=10)
        result = await _call(inp)

        assert isinstance(result, dict)
        assert "total_count" in result
        assert "warnings" in result

    @pytest.mark.asyncio
    async def test_missing_both_is_nationwide_lookup(self) -> None:
        """Both stn_id=None and tmFc=None is accepted for nationwide lookup."""
        from ummaya.tools.kma.kma_weather_alert_status import KmaWeatherAlertStatusInput

        inp = KmaWeatherAlertStatusInput()
        assert inp.stn_id is None
        assert inp.tmFc is None
