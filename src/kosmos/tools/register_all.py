# SPDX-License-Identifier: Apache-2.0
"""Central registration entry point for all KOSMOS government API tools.

Call ``register_all_tools(registry, executor)`` once at application startup
to register every available tool adapter and its executor binding.
"""

from __future__ import annotations

import logging

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_all_tools(registry: ToolRegistry, executor: ToolExecutor) -> None:
    """Register all available government API tool adapters.

    Registers the following tools in order:
      1. koroad_accident_search — KOROAD accident hotspot search
      2. kma_weather_alert_status — KMA weather alert status
      3. kma_current_observation — KMA ultra-short-term current observation
      4. kma_short_term_forecast — KMA short-term forecast (단기예보)
      5. kma_ultra_short_term_forecast — KMA ultra-short-term forecast (초단기예보)
      6. kma_pre_warning — KMA weather pre-warning list (기상예비특보목록)
      7. road_risk_score — composite road risk score (fans out to all three)
      8. address_to_region — Kakao geocoding → KOROAD region codes (시도/구군)
      9. address_to_grid — Kakao geocoding → KMA grid coordinates (nx/ny)

    Args:
        registry: The central ToolRegistry to add tools to.
        executor: The ToolExecutor to bind adapter functions to.

    Raises:
        DuplicateToolError: If any tool id is already registered (i.e., this
            function is called a second time on the same registry).
    """
    from kosmos.tools.composite.road_risk_score import register as reg_risk
    from kosmos.tools.geocoding.address_to_grid import register as reg_addr_grid
    from kosmos.tools.geocoding.address_to_region import register as reg_addr_region
    from kosmos.tools.kma.kma_current_observation import register as reg_kma_obs
    from kosmos.tools.kma.kma_pre_warning import register as reg_kma_pre_warning
    from kosmos.tools.kma.kma_short_term_forecast import register as reg_kma_stf
    from kosmos.tools.kma.kma_ultra_short_term_forecast import register as reg_kma_ustf
    from kosmos.tools.kma.kma_weather_alert_status import register as reg_kma_alert
    from kosmos.tools.koroad.koroad_accident_search import register as reg_koroad

    reg_koroad(registry, executor)
    reg_kma_alert(registry, executor)
    reg_kma_obs(registry, executor)
    reg_kma_stf(registry, executor)
    reg_kma_ustf(registry, executor)
    reg_kma_pre_warning(registry, executor)
    reg_risk(registry, executor)
    reg_addr_region(registry, executor)
    reg_addr_grid(registry, executor)

    logger.info("All %d tools registered successfully", len(registry))
