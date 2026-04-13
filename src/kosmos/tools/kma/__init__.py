# SPDX-License-Identifier: Apache-2.0
"""KMA (Korea Meteorological Administration) API adapter package for KOSMOS Tool System."""

from kosmos.tools.kma.kma_current_observation import (
    KMA_CURRENT_OBSERVATION_TOOL,
    KmaCurrentObservationInput,
    KmaCurrentObservationOutput,
)
from kosmos.tools.kma.kma_pre_warning import (
    KMA_PRE_WARNING_TOOL,
    KmaPreWarningInput,
    KmaPreWarningOutput,
    PreWarningItem,
)
from kosmos.tools.kma.kma_short_term_forecast import (
    KMA_SHORT_TERM_FORECAST_TOOL,
    ForecastItem,
    KmaShortTermForecastInput,
    KmaShortTermForecastOutput,
)
from kosmos.tools.kma.kma_ultra_short_term_forecast import (
    KMA_ULTRA_SHORT_TERM_FORECAST_TOOL,
    KmaUltraShortTermForecastInput,
    KmaUltraShortTermForecastOutput,
)
from kosmos.tools.kma.kma_weather_alert_status import (
    KMA_WEATHER_ALERT_STATUS_TOOL,
    KmaWeatherAlertStatusInput,
    KmaWeatherAlertStatusOutput,
    WeatherWarning,
)

__all__ = [
    # Current observation
    "KMA_CURRENT_OBSERVATION_TOOL",
    "KmaCurrentObservationInput",
    "KmaCurrentObservationOutput",
    # Short-term forecast
    "KMA_SHORT_TERM_FORECAST_TOOL",
    "ForecastItem",
    "KmaShortTermForecastInput",
    "KmaShortTermForecastOutput",
    # Ultra-short-term forecast
    "KMA_ULTRA_SHORT_TERM_FORECAST_TOOL",
    "KmaUltraShortTermForecastInput",
    "KmaUltraShortTermForecastOutput",
    # Pre-warning
    "KMA_PRE_WARNING_TOOL",
    "KmaPreWarningInput",
    "KmaPreWarningOutput",
    "PreWarningItem",
    # Weather alert status
    "KMA_WEATHER_ALERT_STATUS_TOOL",
    "KmaWeatherAlertStatusInput",
    "KmaWeatherAlertStatusOutput",
    "WeatherWarning",
]
