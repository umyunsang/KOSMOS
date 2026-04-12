# SPDX-License-Identifier: Apache-2.0
"""Road risk composite adapter.

Fans out to three inner adapters (koroad_accident_search, kma_weather_alert_status,
kma_current_observation) in parallel using ``asyncio.gather(return_exceptions=True)``,
computes a normalized risk score, and returns a citizen-facing summary.

Partial failures are tolerated: if one or two inner adapters fail, the composite
adapter uses default fallback values for the failed source and records the gap in
``data_gaps``.  If all three adapters fail, a ``ToolExecutionError`` is raised.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, model_validator

from kosmos.tools.errors import ToolExecutionError
from kosmos.tools.kma.kma_current_observation import (
    KmaCurrentObservationInput,
)
from kosmos.tools.kma.kma_current_observation import (
    _call as _kma_obs_call,
)
from kosmos.tools.kma.kma_weather_alert_status import (
    KmaWeatherAlertStatusInput,
)
from kosmos.tools.kma.kma_weather_alert_status import (
    _call as _kma_alert_call,
)
from kosmos.tools.koroad.code_tables import GugunCode, SearchYearCd, SidoCode
from kosmos.tools.koroad.koroad_accident_search import (
    KoroadAccidentSearchInput,
)
from kosmos.tools.koroad.koroad_accident_search import (
    _call as _koroad_call,
)
from kosmos.tools.models import GovAPITool

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Risk level constants
# ---------------------------------------------------------------------------

_RISK_LEVEL_KO: dict[str, str] = {
    "low": "낮음",
    "moderate": "보통",
    "high": "높음",
    "severe": "매우 높음",
}


# ---------------------------------------------------------------------------
# Pydantic v2 I/O Models (T034)
# ---------------------------------------------------------------------------


class RoadRiskScoreInput(BaseModel):
    """Input parameters for the road_risk_score composite tool."""

    model_config = ConfigDict(frozen=True)

    si_do: SidoCode
    """Province/city code for KOROAD query."""

    gu_gun: GugunCode | None = None
    """Optional district code."""

    search_year_cd: SearchYearCd | None = None
    """Dataset year code; defaults to GENERAL_2024 when None."""

    nx: int = Field(..., ge=1, le=149)
    """KMA grid X coordinate."""

    ny: int = Field(..., ge=1, le=253)
    """KMA grid Y coordinate."""

    @model_validator(mode="after")
    def _default_search_year(self) -> "RoadRiskScoreInput":
        """Set search_year_cd to GENERAL_2024 if not provided."""
        if self.search_year_cd is None:
            object.__setattr__(self, "search_year_cd", SearchYearCd.GENERAL_2024)
        return self


class RoadRiskScoreOutput(BaseModel):
    """Output from the road_risk_score composite tool."""

    model_config = ConfigDict(frozen=True)

    risk_score: float
    """Normalized risk score 0.0–1.0."""

    risk_level: Literal["low", "moderate", "high", "severe"]
    """Human-readable risk level."""

    hotspot_count: int
    """Number of accident hotspots found."""

    active_warnings: int
    """Number of active weather warnings."""

    precipitation_mm: float
    """Current precipitation in mm."""

    temperature_c: float | None
    """Current temperature in Celsius, None if observation failed."""

    data_gaps: list[str]
    """List of data sources that failed (e.g., ["kma_current_observation"])."""

    summary: str
    """Korean-language summary string for the citizen."""


# ---------------------------------------------------------------------------
# Scoring helpers (T035)
# ---------------------------------------------------------------------------


def _compute_risk_score(
    hotspot_count: int,
    active_warnings: int,
    precipitation_mm: float,
) -> float:
    """Compute a normalized road risk score in [0.0, 1.0].

    Weights:
      - hotspot_score = min(1.0, hotspot_count / 10.0)  (weight 0.5)
      - weather_score = min(1.0, active_warnings * 0.3 + precipitation_mm / 50.0)  (weight 0.5)

    Args:
        hotspot_count: Number of accident hotspots from KOROAD.
        active_warnings: Number of active weather warnings from KMA.
        precipitation_mm: Current 1-hour precipitation in mm from KMA.

    Returns:
        Risk score clamped to [0.0, 1.0].
    """
    hotspot_score = min(1.0, hotspot_count / 10.0)
    weather_score = min(1.0, active_warnings * 0.3 + precipitation_mm / 50.0)
    base_score = hotspot_score * 0.5 + weather_score * 0.5
    return min(1.0, base_score)


def _risk_level(score: float) -> Literal["low", "moderate", "high", "severe"]:
    """Map a normalized risk score to a human-readable level.

    Thresholds:
      [0.0, 0.3)  → "low"
      [0.3, 0.6)  → "moderate"
      [0.6, 0.8)  → "high"
      [0.8, 1.0]  → "severe"

    Args:
        score: Normalized risk score in [0.0, 1.0].

    Returns:
        Risk level string.
    """
    if score < 0.3:
        return "low"
    if score < 0.6:
        return "moderate"
    if score < 0.8:
        return "high"
    return "severe"


# ---------------------------------------------------------------------------
# Async composite adapter (T036)
# ---------------------------------------------------------------------------


async def _call(
    inp: RoadRiskScoreInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, object]:
    """Fan-out to three inner adapters and compute a road risk score.

    Uses ``asyncio.gather(return_exceptions=True)`` for concurrency.
    Partial failures are tolerated; total failure raises ``ToolExecutionError``.

    Args:
        inp: Validated composite input parameters.
        client: Optional httpx.AsyncClient for test injection; forwarded to
                all three inner adapters unchanged.

    Returns:
        A plain dict matching ``RoadRiskScoreOutput`` schema.

    Raises:
        ToolExecutionError: If all three inner adapters fail.
    """
    now = datetime.now(UTC)
    base_date = now.strftime("%Y%m%d")
    base_time = now.strftime("%H") + "00"

    # Build inner inputs
    koroad_inp = KoroadAccidentSearchInput(
        search_year_cd=inp.search_year_cd,  # type: ignore[arg-type]  # guaranteed by validator
        si_do=inp.si_do,
        gu_gun=inp.gu_gun,
        num_of_rows=100,
    )
    kma_alert_inp = KmaWeatherAlertStatusInput()
    kma_obs_inp = KmaCurrentObservationInput(
        base_date=base_date,
        base_time=base_time,
        nx=inp.nx,
        ny=inp.ny,
    )

    logger.debug(
        "road_risk_score fan-out: si_do=%s nx=%d ny=%d base_date=%s base_time=%s",
        inp.si_do.value,
        inp.nx,
        inp.ny,
        base_date,
        base_time,
    )

    # Parallel fan-out — exceptions are returned, not raised
    koroad_result, kma_alert_result, kma_obs_result = await asyncio.gather(
        _koroad_call(koroad_inp, client=client),
        _kma_alert_call(kma_alert_inp, client=client),
        _kma_obs_call(kma_obs_inp, client=client),
        return_exceptions=True,
    )

    # Check total failure
    all_failed = (
        isinstance(koroad_result, BaseException)
        and isinstance(kma_alert_result, BaseException)
        and isinstance(kma_obs_result, BaseException)
    )
    if all_failed:
        raise ToolExecutionError(
            "road_risk_score",
            "All three inner adapters failed: "
            f"koroad={koroad_result!r} "
            f"kma_alert={kma_alert_result!r} "
            f"kma_obs={kma_obs_result!r}",
        )

    # Extract values with fallbacks for partial failures
    data_gaps: list[str] = []

    if isinstance(koroad_result, BaseException):
        logger.warning("koroad_accident_search failed in road_risk_score: %s", koroad_result)
        data_gaps.append("koroad_accident_search")
        hotspot_count = 0
    else:
        hotspot_count = int(koroad_result.get("total_count", 0))

    if isinstance(kma_alert_result, BaseException):
        logger.warning("kma_weather_alert_status failed in road_risk_score: %s", kma_alert_result)
        data_gaps.append("kma_weather_alert_status")
        active_warnings = 0
    else:
        active_warnings = int(kma_alert_result.get("total_count", 0))

    temperature_c: float | None
    if isinstance(kma_obs_result, BaseException):
        logger.warning("kma_current_observation failed in road_risk_score: %s", kma_obs_result)
        data_gaps.append("kma_current_observation")
        precipitation_mm = 0.0
        temperature_c = None
    else:
        precipitation_mm = float(kma_obs_result.get("rn1", 0.0))
        raw_t1h = kma_obs_result.get("t1h")
        temperature_c = float(raw_t1h) if raw_t1h is not None else None

    # Compute score and level
    score = _compute_risk_score(hotspot_count, active_warnings, precipitation_mm)
    level = _risk_level(score)
    level_ko = _RISK_LEVEL_KO[level]

    summary = (
        f"위험도 {level_ko}: 사고다발지역 {hotspot_count}건, "
        f"기상특보 {active_warnings}건, 강수량 {precipitation_mm}mm"
    )

    output = RoadRiskScoreOutput(
        risk_score=score,
        risk_level=level,
        hotspot_count=hotspot_count,
        active_warnings=active_warnings,
        precipitation_mm=precipitation_mm,
        temperature_c=temperature_c,
        data_gaps=data_gaps,
        summary=summary,
    )

    logger.info(
        "road_risk_score: score=%.3f level=%s hotspots=%d warnings=%d precip=%.1fmm gaps=%s",
        score,
        level,
        hotspot_count,
        active_warnings,
        precipitation_mm,
        data_gaps,
    )

    return output.model_dump()


# ---------------------------------------------------------------------------
# Tool definition and registration helper (T037)
# ---------------------------------------------------------------------------

ROAD_RISK_SCORE_TOOL = GovAPITool(
    id="road_risk_score",
    name_ko="도로 위험도 종합 평가",
    provider="KOSMOS (종합)",
    category=["교통안전", "기상", "종합평가"],
    endpoint="",  # composite — no single endpoint
    auth_type="public",  # composite manages inner auth
    input_schema=RoadRiskScoreInput,
    output_schema=RoadRiskScoreOutput,
    search_hint=(
        "도로 위험도 종합 평가 교통사고 기상 날씨 안전 "
        "road risk score composite accident weather safety"
    ),
    requires_auth=False,
    is_concurrency_safe=True,
    is_personal_data=False,
    cache_ttl_seconds=300,
    rate_limit_per_minute=10,
    is_core=True,
)


def register(registry: object, executor: object) -> None:
    """Register road_risk_score composite tool and its adapter.

    Args:
        registry: A ToolRegistry instance.
        executor: A ToolExecutor instance.
    """
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.registry import ToolRegistry

    assert isinstance(registry, ToolRegistry)
    assert isinstance(executor, ToolExecutor)

    registry.register(ROAD_RISK_SCORE_TOOL)
    executor.register_adapter("road_risk_score", _call)
    logger.info("Registered tool: road_risk_score")
