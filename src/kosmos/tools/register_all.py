# SPDX-License-Identifier: Apache-2.0
"""Central registration entry point for all KOSMOS government API tools.

Call ``register_all_tools(registry, executor)`` once at application startup
to register every available tool adapter and its executor binding.

NOTE (T049 / Epic #507): ``address_to_region`` and ``address_to_grid`` were
removed in User Story 4.  Administrative code resolution is now handled by
``resolve_location(want='adm_cd')`` via the backend-only ``juso`` and ``sgis``
helpers.  Grid coordinate resolution is handled internally by
``kma_forecast_fetch`` via ``latlon_to_lcc()``.

NOTE (Stage 3 / T033, T048, T056): Three seed adapters added to the registry:
``nmc_emergency_search`` (Layer 3 gated stub), ``kma_forecast_fetch`` (short-term
forecast via LCC-projected grid), and ``hira_hospital_search`` (hospital search
by radius).  All three are discoverable via ``lookup(mode="search")`` and
invocable via ``lookup(mode="fetch")``.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel

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
     11. nmc_emergency_search — NMC emergency room bed availability (Layer 3 gated)
     12. kma_forecast_fetch — KMA short-term forecast by (lat, lon) → LCC grid
     13. hira_hospital_search — HIRA hospital search by coordinates + radius
     14. nfa_emergency_info_service — NFA EMS statistics (Phase 2, Layer 3 gated stub)
     15. mohw_welfare_eligibility_search — SSIS welfare service list (Phase 2, Layer 3 gated stub)

    Args:
        registry: The central ToolRegistry to add tools to.
        executor: The ToolExecutor to bind adapter functions to.

    Raises:
        DuplicateToolError: If any tool id is already registered (i.e., this
            function is called a second time on the same registry).
    """
    from kosmos.tools.composite.road_risk_score import register as reg_risk
    from kosmos.tools.hira.hospital_search import register as reg_hira
    from kosmos.tools.kma.forecast_fetch import (
        KMA_FORECAST_FETCH_TOOL,
        KmaForecastFetchInput,
    )
    from kosmos.tools.kma.forecast_fetch import (
        _fetch as kma_forecast_fetch_adapter,
    )
    from kosmos.tools.kma.kma_current_observation import register as reg_kma_obs
    from kosmos.tools.kma.kma_pre_warning import register as reg_kma_pre_warning
    from kosmos.tools.kma.kma_short_term_forecast import register as reg_kma_stf
    from kosmos.tools.kma.kma_ultra_short_term_forecast import register as reg_kma_ustf
    from kosmos.tools.kma.kma_weather_alert_status import register as reg_kma_alert
    from kosmos.tools.koroad.accident_hazard_search import register as reg_koroad_hazard
    from kosmos.tools.koroad.koroad_accident_search import register as reg_koroad
    from kosmos.tools.mvp_surface import register_mvp_surface
    from kosmos.tools.nfa119.emergency_info_service import register as reg_nfa
    from kosmos.tools.nmc.emergency_search import register as reg_nmc
    from kosmos.tools.ssis.welfare_eligibility_search import register as reg_mohw

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

    # Seed adapters for MVP Main-Tool (Epic #507, Stage 3)
    reg_nmc(registry, executor)  # T033 — NMC (Layer 3 gated stub)
    reg_hira(registry, executor)  # T056 — HIRA hospital search

    # T048 — KMA forecast_fetch: register tool + bind executor adapter.
    # The module's register(registry) only covers the registry; the executor
    # binding lives here so _fetch is reachable via lookup(mode="fetch").
    registry.register(KMA_FORECAST_FETCH_TOOL)

    async def _kma_forecast_fetch_adapter(inp: BaseModel) -> dict[str, Any]:
        assert isinstance(inp, KmaForecastFetchInput)
        result = await kma_forecast_fetch_adapter(inp)
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)

    executor.register_adapter("kma_forecast_fetch", _kma_forecast_fetch_adapter)
    logger.info("Registered tool: kma_forecast_fetch")

    # Phase 2 adapters (spec 029 — NFA 119 + MOHW SSIS, Layer 3 gated stubs)
    reg_nfa(registry, executor)  # T014 — NFA EMS statistics (interface-only)
    reg_mohw(registry, executor)  # T022 — MOHW welfare eligibility search (interface-only)

    logger.info("All %d tools registered successfully", len(registry))
