# SPDX-License-Identifier: Apache-2.0
"""Address-to-region geocoding adapter.

Resolves a free-form Korean address string to KOROAD province (시도) and
district (구군) integer codes via the Kakao Local API.

User Story 1 (US-1): "As a KOSMOS user, I want to find accident hotspots near
an address so that I can assess road-safety risk without manually looking up
region codes."

Execution flow:
  1. Call Kakao ``search/address.json`` with the input address string.
  2. Extract ``region_1depth_name`` and ``region_2depth_name`` from the first
     document.
  3. Map both names to :class:`~kosmos.tools.koroad.code_tables.SidoCode` and
     :class:`~kosmos.tools.koroad.code_tables.GugunCode` via
     :mod:`~kosmos.tools.geocoding.region_mapping`.
  4. Return the codes together with the canonical address string and coordinates.

If the Kakao API returns zero results, ``sido_code`` and ``gugun_code`` are
``None`` and ``resolved_address`` is an empty string.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import httpx
from pydantic import BaseModel, ConfigDict, Field

from kosmos.tools.errors import ToolExecutionError
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.geocoding.kakao_client import search_address
from kosmos.tools.geocoding.region_mapping import region1_to_sido, region2_to_gugun
from kosmos.tools.models import GovAPITool
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"

# ---------------------------------------------------------------------------
# Input / Output models
# ---------------------------------------------------------------------------


class AddressToRegionInput(BaseModel):
    """Input parameters for the address_to_region geocoding tool."""

    model_config = ConfigDict(frozen=True)

    address: str = Field(..., min_length=1)
    """Free-form Korean address string to geocode (e.g. "서울특별시 강남구 테헤란로 152")."""


class AddressToRegionOutput(BaseModel):
    """Output from the address_to_region geocoding tool."""

    model_config = ConfigDict(frozen=True)

    resolved_address: str
    """Canonical address string as returned by the Kakao API.  Empty string when no match."""

    latitude: float | None = None
    """WGS-84 latitude of the resolved location; ``None`` when no match."""

    longitude: float | None = None
    """WGS-84 longitude of the resolved location; ``None`` when no match."""

    region_1depth: str = ""
    """Province/city name (시도) as returned by Kakao (e.g. "서울특별시")."""

    region_2depth: str = ""
    """District name (구군) as returned by Kakao (e.g. "강남구")."""

    sido_code: int | None = None
    """KOROAD SidoCode integer for the resolved province; ``None`` when no match or unmapped."""

    gugun_code: int | None = None
    """KOROAD GugunCode integer for the resolved district; ``None`` when unmapped."""


# ---------------------------------------------------------------------------
# Internal resolution helper
# ---------------------------------------------------------------------------


async def _resolve(
    address: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> AddressToRegionOutput:
    """Geocode *address* and map it to KOROAD region codes.

    Args:
        address: Free-form Korean address to geocode.
        client: Optional injected ``httpx.AsyncClient`` for testing.

    Returns:
        A populated :class:`AddressToRegionOutput`.  All code fields are
        ``None`` when the Kakao API returns no documents.

    Raises:
        ConfigurationError: If ``KOSMOS_KAKAO_API_KEY`` is not set.
        ToolExecutionError: On Kakao API HTTP errors.
    """
    result = await search_address(address, client=client)

    if not result.documents:
        logger.debug("address_to_region: no Kakao results")
        return AddressToRegionOutput(resolved_address="")

    if len(result.documents) > 1:
        raise ToolExecutionError(
            tool_id="address_to_region",
            message=(
                f"Ambiguous address: Kakao returned {result.meta.total_count} matches. "
                "Please provide a more specific address."
            ),
        )

    doc = result.documents[0]

    # Prefer road_address for region depth names; fall back to legacy address block.
    addr_block = doc.road_address or doc.address
    region1 = addr_block.region_1depth_name if addr_block else ""
    region2 = addr_block.region_2depth_name if addr_block else ""

    sido = region1_to_sido(region1) if region1 else None
    gugun = region2_to_gugun(region2) if region2 else None

    try:
        lat = float(doc.y) if doc.y else None
        lon = float(doc.x) if doc.x else None
    except (ValueError, TypeError):
        lat = lon = None

    return AddressToRegionOutput(
        resolved_address=doc.address_name,
        latitude=lat,
        longitude=lon,
        region_1depth=region1,
        region_2depth=region2,
        sido_code=int(sido) if sido is not None else None,
        gugun_code=int(gugun) if gugun is not None else None,
    )


# ---------------------------------------------------------------------------
# Adapter callable
# ---------------------------------------------------------------------------


async def _call(
    params: AddressToRegionInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Adapter entry point for the address_to_region tool.

    Args:
        params: Validated input parameters.
        client: Optional injected ``httpx.AsyncClient`` for testing.

    Returns:
        A plain dict matching :class:`AddressToRegionOutput` field names.

    Raises:
        ConfigurationError: If ``KOSMOS_KAKAO_API_KEY`` is not set.
        ToolExecutionError: On Kakao API HTTP errors.
    """
    logger.debug("address_to_region: resolving address=%r", params.address)

    output = await _resolve(params.address, client=client)

    logger.debug(
        "address_to_region: resolved sido_code=%s gugun_code=%s",
        output.sido_code,
        output.gugun_code,
    )
    return output.model_dump()


# ---------------------------------------------------------------------------
# Tool definition
# ---------------------------------------------------------------------------

ADDRESS_TO_REGION_TOOL = GovAPITool(
    id="address_to_region",
    name_ko="주소→지역코드 변환 (시도/구군)",
    provider="카카오 (Kakao)",
    category=["지오코딩", "주소변환", "지역코드"],
    endpoint=_BASE_URL,
    auth_type="api_key",
    input_schema=AddressToRegionInput,
    output_schema=AddressToRegionOutput,
    search_hint=(
        "주소 지역코드 변환 시도코드 구군코드 카카오 지오코딩 "
        "address region code geocoding sido gugun kakao location"
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
    """Register the address_to_region tool and its adapter.

    Args:
        registry: The central :class:`~kosmos.tools.registry.ToolRegistry`.
        executor: The :class:`~kosmos.tools.executor.ToolExecutor` to bind to.
    """
    from kosmos.tools.executor import AdapterFn

    registry.register(ADDRESS_TO_REGION_TOOL)
    executor.register_adapter("address_to_region", cast(AdapterFn, _call))
    logger.debug("Registered tool: address_to_region")
