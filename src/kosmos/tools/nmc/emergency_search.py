# SPDX-License-Identifier: Apache-2.0
"""NMC emergency room search adapter — T032.

Interface-only adapter. The Layer 3 auth-gate in ``executor.invoke()`` unconditionally
short-circuits every fetch call to ``LookupError(reason="auth_required")`` before the
handler body is reached (FR-025, FR-026, SC-006). The handler body is therefore
unreachable in practice and raises ``Layer3GateViolation`` as a defence-in-depth
guard against programming errors.

FR-034: Freshness check via ``KOSMOS_NMC_FRESHNESS_MINUTES`` env var is deferred to a
future epic. No freshness check is implemented here.

auth contract: ``requires_auth=True``, ``is_personal_data=True``.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, RootModel

from kosmos.tools.errors import Layer3GateViolation
from kosmos.tools.models import GovAPITool

logger = logging.getLogger(__name__)

# NMC real-time bed availability endpoint (not called from CI — auth required).
_BASE_URL = "https://api1.odcloud.kr/api/nmc/v1/realtime-beds"

# ---------------------------------------------------------------------------
# Input schema (T032 — lat/lon/limit, Pydantic v2 strict)
# ---------------------------------------------------------------------------


class NmcEmergencySearchInput(BaseModel):
    """Input schema for nmc_emergency_search.

    Pydantic v2 strict model (extra='forbid', frozen=True).
    All three fields are required; no defaults are provided so that the LLM
    must explicitly supply values rather than silently relying on fallbacks.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    lat: float = Field(
        ge=-90,
        le=90,
        description=(
            "Latitude of the search origin in decimal degrees (WGS-84). "
            "Obtain from resolve_location(want='coords'). "
            "Example: 37.5665 for central Seoul."
        ),
    )
    lon: float = Field(
        ge=-180,
        le=180,
        description=(
            "Longitude of the search origin in decimal degrees (WGS-84). "
            "Obtain from resolve_location(want='coords'). "
            "Example: 126.9780 for central Seoul."
        ),
    )
    limit: int = Field(
        ge=1,
        le=100,
        description=(
            "Maximum number of nearest emergency rooms to return. "
            "Capped at 100 per NMC API contract. "
            "Example: 5 for the five nearest ERs."
        ),
    )


# ---------------------------------------------------------------------------
# Placeholder output schema
# ---------------------------------------------------------------------------


class _NmcEmergencySearchOutput(RootModel[dict[str, Any]]):
    """Placeholder output schema for GovAPITool registration.

    Real output shape is deferred until NMC auth is provisioned.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# Handler — unreachable in practice due to Layer 3 auth-gate
# ---------------------------------------------------------------------------


async def handle(inp: NmcEmergencySearchInput) -> dict[str, Any]:
    """Handle an NMC emergency search request.

    Should never reach here — Layer 3 gate short-circuits on requires_auth=True.
    See ``executor.invoke()`` FR-025 / FR-026 / SC-006. If this body is ever
    reached it indicates a programming error (gate was bypassed), so we raise
    ``Layer3GateViolation`` as a hard fail rather than silently making an
    unauthenticated upstream call.

    FR-034: ``KOSMOS_NMC_FRESHNESS_MINUTES`` freshness check is intentionally
    omitted here and deferred to a future epic.

    Args:
        inp: Validated NmcEmergencySearchInput (lat, lon, limit).

    Raises:
        Layer3GateViolation: Always — this handler body must never be invoked.
    """
    raise Layer3GateViolation("nmc_emergency_search")


# ---------------------------------------------------------------------------
# Tool definition (T033 will call register() from register_all.py)
# ---------------------------------------------------------------------------

NMC_EMERGENCY_SEARCH_TOOL = GovAPITool(
    id="nmc_emergency_search",
    name_ko="응급실 실시간 병상 조회 (국립중앙의료원)",
    provider="국립중앙의료원 (NMC)",
    category=["응급의료", "실시간병상", "의료기관"],
    endpoint=_BASE_URL,
    auth_type="api_key",
    input_schema=NmcEmergencySearchInput,
    output_schema=_NmcEmergencySearchOutput,
    llm_description=(
        "Query the NMC (National Medical Center) real-time emergency room bed availability "
        "for the nearest ERs around a given coordinate. "
        "Obtain lat/lon first via resolve_location(want='coords'). "
        "Returns a ranked list of emergency rooms with available bed counts and distance. "
        "IMPORTANT: This tool requires citizen authentication (requires_auth=True). "
        "Calls without a valid session identity are rejected with auth_required. "
        "Use this when a user asks about nearby emergency rooms, ER bed availability, "
        "or the closest 응급실 in Korea."
    ),
    search_hint=(
        "응급실 실시간 병상 응급의료센터 국립중앙의료원 가까운 응급실 "
        "emergency room bed availability nearest ER NMC real-time Korea"
    ),
    # Metadata for T033 registration:
    requires_auth=True,
    is_personal_data=True,
    is_concurrency_safe=False,
    cache_ttl_seconds=0,
    rate_limit_per_minute=10,
    is_core=False,
    # search_hint_ko and search_hint_en are collapsed into search_hint above.
    # Canonical hint values (kept here as comments for T033 reference):
    #   search_hint_ko = "응급실 실시간 병상 · 응급의료센터"
    #   search_hint_en = "emergency room bed availability nearest ER"
)


def register(registry: object, executor: object) -> None:
    """Register the NMC emergency search tool and its stub adapter.

    Called by ``register_all.py`` in Stage 3 (T033). Do NOT call this
    function from Stage 2 — it is intentionally left unregistered until
    Stage 3 serial integration.

    The adapter is registered as a stub: it satisfies the executor's
    adapter contract but the handler body is never reachable because the
    Layer 3 auth-gate short-circuits every fetch on ``requires_auth=True``
    before invoking the adapter (FR-025, SC-006).

    Args:
        registry: A ToolRegistry instance.
        executor: A ToolExecutor instance.
    """
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.registry import ToolRegistry

    assert isinstance(registry, ToolRegistry)
    assert isinstance(executor, ToolExecutor)

    async def _adapter(inp: BaseModel) -> dict[str, Any]:
        assert isinstance(inp, NmcEmergencySearchInput)
        return await handle(inp)

    registry.register(NMC_EMERGENCY_SEARCH_TOOL)
    executor.register_adapter("nmc_emergency_search", _adapter)
    logger.info("Registered tool: nmc_emergency_search (stub — auth_required gate)")
