# SPDX-License-Identifier: Apache-2.0
"""Address-to-KMA-grid geocoding adapter.

Resolves a free-form Korean address string to KMA 5 km grid (nx, ny) coordinates
used by KMA weather APIs (초단기실황, 단기예보, 초단기예보).

User Story 2 (US-2): "As a KOSMOS user, I want to look up weather data for an
address so that I can get weather conditions without manually finding grid codes."

Execution flow:
  1. Call Kakao ``search/address.json`` with the input address string.
  2. Extract ``(latitude, longitude)`` from the first document's ``y``/``x`` fields.
  3. Convert (lat, lon) to (nx, ny) using the KMA Lambert Conformal Conic
     projection via :func:`~kosmos.tools.kma.grid_coords.latlon_to_grid`.
  4. On Kakao API timeout or no results, fall back to
     :func:`~kosmos.tools.kma.grid_coords.lookup_grid` using progressively
     shorter prefix tokens of the raw address string.

If the Kakao API returns zero results and the fallback also fails, ``nx``/``ny``
are ``None`` and ``source`` is ``"not_found"``.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

from kosmos.tools.errors import ToolExecutionError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.geocoding.kakao_client import search_address
from kosmos.tools.kma.grid_coords import latlon_to_grid, lookup_grid
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# ---------------------------------------------------------------------------
# Input / Output models
# ---------------------------------------------------------------------------


class AddressToGridInput(BaseModel):
    """Input parameters for the address_to_grid geocoding tool."""

    model_config = ConfigDict(frozen=True)

    address: str = Field(..., min_length=1)
    """Free-form Korean address string to geocode (e.g. "서울특별시 서초구 반포대로 201")."""


class AddressToGridOutput(BaseModel):
    """Output from the address_to_grid geocoding tool."""

    model_config = ConfigDict(frozen=True)

    resolved_address: str
    """Canonical address as returned by the Kakao API.  Empty string when not found."""

    latitude: float | None = None
    """WGS-84 latitude of the resolved location; ``None`` when not found."""

    longitude: float | None = None
    """WGS-84 longitude of the resolved location; ``None`` when not found."""

    nx: int | None = None
    """KMA grid X coordinate; ``None`` when the address could not be resolved."""

    ny: int | None = None
    """KMA grid Y coordinate; ``None`` when the address could not be resolved."""

    source: str = "not_found"
    """Resolution method: ``"kakao_latlon"`` (Kakao + LCC projection), ``"table_fallback"``
    (static KMA region table), or ``"not_found"``."""


# ---------------------------------------------------------------------------
# Internal resolution helpers
# ---------------------------------------------------------------------------


async def _resolve_from_kakao(
    address: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> AddressToGridOutput:
    """Attempt to resolve *address* via Kakao and compute the KMA grid.

    Args:
        address: Free-form Korean address.
        client: Optional injected ``httpx.AsyncClient`` for testing.

    Returns:
        A populated :class:`AddressToGridOutput` with ``source="kakao_latlon"``
        on success, or a no-match output with ``source="not_found"`` when the
        Kakao API returns no documents.

    Raises:
        ConfigurationError: If ``KOSMOS_KAKAO_API_KEY`` is not set.
        ToolExecutionError: On non-timeout Kakao API errors.
    """
    result = await search_address(address, client=client)

    if not result.documents:
        logger.debug("address_to_grid: no Kakao results")
        return AddressToGridOutput(resolved_address="", source="not_found")

    if len(result.documents) > 1:
        raise ToolExecutionError(
            tool_id="address_to_grid",
            message=(
                f"Ambiguous address: Kakao returned {result.meta.total_count} matches. "
                "Please provide a more specific address."
            ),
        )

    doc = result.documents[0]

    try:
        lat = float(doc.y)
        lon = float(doc.x)
    except (ValueError, TypeError):
        logger.warning("address_to_grid: could not parse coordinates x=%r y=%r", doc.x, doc.y)
        return AddressToGridOutput(resolved_address=doc.address_name, source="not_found")

    nx, ny = latlon_to_grid(lat, lon)

    logger.debug(
        "address_to_grid: address=%r lat=%.5f lon=%.5f → nx=%d ny=%d",
        address,
        lat,
        lon,
        nx,
        ny,
    )

    return AddressToGridOutput(
        resolved_address=doc.address_name,
        latitude=lat,
        longitude=lon,
        nx=nx,
        ny=ny,
        source="kakao_latlon",
    )


def _fallback_local_lookup(address: str) -> AddressToGridOutput:
    """Fall back to the static KMA region table using the address string.

    Tries successive prefix tokens of *address* against the
    :func:`~kosmos.tools.kma.grid_coords.lookup_grid` table.

    Args:
        address: Address or region name string to try.

    Returns:
        A :class:`AddressToGridOutput` with ``source="table_fallback"`` if a match
        was found, or ``source="not_found"`` otherwise.
    """
    # Try the full string first, then progressively shorter leading tokens.
    tokens = address.strip().split()
    candidates = [address.strip()] + [" ".join(tokens[:i]) for i in range(len(tokens), 0, -1)]

    for candidate in candidates:
        try:
            nx, ny = lookup_grid(candidate)
            logger.debug(
                "address_to_grid: table fallback matched → nx=%d ny=%d",
                nx,
                ny,
            )
            return AddressToGridOutput(
                resolved_address=candidate,
                nx=nx,
                ny=ny,
                source="table_fallback",
            )
        except ValueError:
            continue

    logger.debug("address_to_grid: fallback lookup found no match")
    return AddressToGridOutput(resolved_address="", source="not_found")


# ---------------------------------------------------------------------------
# Adapter callable
# ---------------------------------------------------------------------------


async def _call(
    params: AddressToGridInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Adapter entry point for the address_to_grid tool.

    Attempts Kakao geocoding first; falls back to the static KMA table on
    :exc:`httpx.TimeoutException`.

    Args:
        params: Validated input parameters.
        client: Optional injected ``httpx.AsyncClient`` for testing.

    Returns:
        A plain dict matching :class:`AddressToGridOutput` field names.

    Raises:
        ConfigurationError: If ``KOSMOS_KAKAO_API_KEY`` is not set.
        ToolExecutionError: On non-timeout Kakao API errors.
    """
    logger.debug("address_to_grid: resolving address=%r", params.address)

    try:
        output = await _resolve_from_kakao(params.address, client=client)
    except httpx.TimeoutException:
        # On timeout, attempt static-table fallback.
        logger.debug("address_to_grid: Kakao timed out, using table fallback")
        output = _fallback_local_lookup(params.address)

    # If Kakao returned no results, also try static-table fallback.
    if output.source == "not_found":
        fallback = _fallback_local_lookup(params.address)
        if fallback.source != "not_found":
            output = fallback

    logger.debug(
        "address_to_grid: resolved nx=%s ny=%s source=%s",
        output.nx,
        output.ny,
        output.source,
    )
    return output.model_dump()


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

ADDRESS_TO_GRID_TOOL = GovAPITool(
    id="address_to_grid",
    name_ko="주소→기상청 격자좌표 변환 (nx/ny)",
    provider="카카오 (Kakao) + 기상청 (KMA)",
    category=["지오코딩", "주소변환", "기상격자"],
    endpoint=_BASE_URL,
    auth_type="api_key",
    input_schema=AddressToGridInput,
    output_schema=AddressToGridOutput,
    search_hint=(
        "주소 기상격자 좌표 변환 nx ny 날씨 위치 기상청 격자 "
        "address kma grid nx ny weather location geocoding"
    ),
    requires_auth=False,
    is_concurrency_safe=True,
    is_personal_data=False,
    cache_ttl_seconds=86400,
    rate_limit_per_minute=30,
    is_core=False,
)


# ---------------------------------------------------------------------------
# Registration helper
# ---------------------------------------------------------------------------


def register(registry: ToolRegistry, executor: ToolExecutor) -> None:
    """Register the address_to_grid tool and its adapter.

    Args:
        registry: The central :class:`~kosmos.tools.registry.ToolRegistry`.
        executor: The :class:`~kosmos.tools.executor.ToolExecutor` to bind to.
    """
    from kosmos.tools.executor import AdapterFn

    registry.register(ADDRESS_TO_GRID_TOOL)
    executor.register_adapter("address_to_grid", cast(AdapterFn, _call))
    logger.debug("Registered tool: address_to_grid")
