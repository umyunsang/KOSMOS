# SPDX-License-Identifier: Apache-2.0
"""Central registration entry point for all KOSMOS government API tools.

Call ``register_all_tools(registry, executor)`` once at application startup
to register every available tool adapter and its executor binding.

NOTE (T049 / Epic #507): ``address_to_region`` and ``address_to_grid`` were
removed in User Story 4.  Administrative code resolution is now handled by
``resolve_location(want='adm_cd')`` via the backend-only ``juso`` and ``sgis``
helpers.  Grid coordinate resolution is handled internally by
``kma_forecast_fetch`` via ``latlon_to_lcc()``.

NOTE (T048 / Stage 3): ``kma_forecast_fetch`` registration will be added here
in Stage 3 when it is wired into the MVP tool surface.
"""

from __future__ import annotations

import logging

from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def register_all_tools(registry: ToolRegistry, executor: ToolExecutor) -> None:
    """Register all available government API tool adapters.

    Registers the following tools in order:
      1. resolve_location — MVP LLM core surface: location resolution (is_core=True)
      2. lookup — MVP LLM core surface: adapter discovery + invocation (is_core=True)
      3. koroad_accident_search — KOROAD accident hotspot search (by enum codes)
      4. koroad_accident_hazard_search — KOROAD accident hazard search (by adm_cd)
      5. kma_weather_alert_status — KMA weather alert status
      6. kma_current_observation — KMA ultra-short-term current observation
      7. kma_short_term_forecast — KMA short-term forecast (단기예보)
      8. kma_ultra_short_term_forecast — KMA ultra-short-term forecast (초단기예보)
      9. kma_pre_warning — KMA weather pre-warning list (기상예비특보목록)
     10. road_risk_score — composite road risk score (fans out to all three)

    Args:
        registry: The central ToolRegistry to add tools to.
        executor: The ToolExecutor to bind adapter functions to.

    Raises:
        DuplicateToolError: If any tool id is already registered (i.e., this
            function is called a second time on the same registry).
    """
    from kosmos.tools.composite.road_risk_score import register as reg_risk
    from kosmos.tools.kma.kma_current_observation import register as reg_kma_obs
    from kosmos.tools.kma.kma_pre_warning import register as reg_kma_pre_warning
    from kosmos.tools.kma.kma_short_term_forecast import register as reg_kma_stf
    from kosmos.tools.kma.kma_ultra_short_term_forecast import register as reg_kma_ustf
    from kosmos.tools.kma.kma_weather_alert_status import register as reg_kma_alert
    from kosmos.tools.koroad.accident_hazard_search import register as reg_koroad_hazard
    from kosmos.tools.koroad.koroad_accident_search import register as reg_koroad
    from kosmos.tools.mvp_surface import register_mvp_surface

    # Register MVP LLM-visible core surface first (FR-001, SC-003)
    register_mvp_surface(registry)

    reg_koroad(registry, executor)
    reg_koroad_hazard(registry, executor)
    reg_kma_alert(registry, executor)
    reg_kma_obs(registry, executor)
    reg_kma_stf(registry, executor)
    reg_kma_ustf(registry, executor)
    reg_kma_pre_warning(registry, executor)
    reg_risk(registry, executor)

    logger.info("All %d tools registered successfully", len(registry))
