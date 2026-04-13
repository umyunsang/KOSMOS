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
      4. road_risk_score — composite road risk score (fans out to all three)

    Args:
        registry: The central ToolRegistry to add tools to.
        executor: The ToolExecutor to bind adapter functions to.

    Raises:
        DuplicateToolError: If any tool id is already registered (i.e., this
            function is called a second time on the same registry).
    """
    from kosmos.tools.composite.road_risk_score import register as reg_risk
    from kosmos.tools.kma.kma_current_observation import register as reg_kma_obs
    from kosmos.tools.kma.kma_weather_alert_status import register as reg_kma_alert
    from kosmos.tools.koroad.koroad_accident_search import register as reg_koroad

    reg_koroad(registry, executor)
    reg_kma_alert(registry, executor)
    reg_kma_obs(registry, executor)
    reg_risk(registry, executor)

    logger.info("All %d tools registered successfully", len(registry))
