# SPDX-License-Identifier: Apache-2.0
"""Kakao Local API HTTP client for address geocoding.

Wraps the ``GET https://dapi.kakao.com/v2/local/search/address.json``
endpoint used to convert free-form Korean address strings into structured
coordinate and administrative region data.

Authentication: REST API key via ``Authorization: KakaoAK {key}`` header.
Key source: ``KOSMOS_KAKAO_API_KEY`` environment variable.

Error mapping:
  - HTTP 401  → :exc:`~kosmos.tools.errors.ToolExecutionError` (auth_expired)
  - HTTP 429  → :exc:`~kosmos.tools.errors.ToolExecutionError` (rate_limit)
  - timeout   → :exc:`httpx.TimeoutException` (propagated for recovery classifier)
  - other 4xx/5xx → :exc:`httpx.HTTPStatusError` (propagated for recovery classifier)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from kosmos.tools.errors import ConfigurationError, ToolExecutionError, _require_env

logger = logging.getLogger(__name__)

_BASE_URL = "https://dapi.kakao.com/v2/local/search/address.json"
_DEFAULT_TIMEOUT = 5.0  # seconds


# ---------------------------------------------------------------------------
# Pydantic v2 response models
# ---------------------------------------------------------------------------


class KakaoRoadAddressResult(BaseModel):
    """Road address (도로명주소) portion of a Kakao address document."""

    model_config = ConfigDict(frozen=True)

    address_name: str
    """Full road address string."""

    region_1depth_name: str
    """Province (시도) name, e.g. "서울특별시"."""

    region_2depth_name: str
    """District (구군) name, e.g. "강남구"."""

    region_3depth_name: str = ""
    """Sub-district (읍면동) name."""

    road_name: str = ""
    """Road name."""

    underground_yn: str = "N"
    """Whether underground (Y/N)."""

    main_building_no: str = ""
    """Main building number."""

    sub_building_no: str = ""
    """Sub building number."""

    building_name: str = ""
    """Building name."""

    zone_no: str = ""
    """Postal zone code."""

    x: str = ""
    """Longitude as string."""

    y: str = ""
    """Latitude as string."""


class KakaoAddressDocument(BaseModel):
    """A single address document returned by the Kakao search/address endpoint."""

    model_config = ConfigDict(frozen=True)

    address_name: str
    """Full resolved address string."""

    address_type: str = ""
    """Type of address: REGION, ROAD_ADDR, REGION_ADDR, etc."""

    x: str
    """Longitude (경도) as string."""

    y: str
    """Latitude (위도) as string."""

    address: KakaoAddressResult | None = None
    """Legacy address result block (구주소)."""

    road_address: KakaoRoadAddressResult | None = None
    """Road address block (도로명주소); preferred when available."""


class KakaoAddressResult(BaseModel):
    """Legacy address (구주소) portion of a Kakao address document."""

    model_config = ConfigDict(frozen=True)

    address_name: str
    """Full legacy address string."""

    region_1depth_name: str
    """Province (시도) name."""

    region_2depth_name: str
    """District (구군) name."""

    region_3depth_name: str = ""
    """Sub-district (읍면동) name."""

    mountain_yn: str = "N"
    """Whether mountain address (Y/N)."""

    main_address_no: str = ""
    """Main address number."""

    sub_address_no: str = ""
    """Sub address number."""

    x: str = ""
    """Longitude as string."""

    y: str = ""
    """Latitude as string."""


# Re-attach forward reference now that KakaoAddressResult is defined
KakaoAddressDocument.model_rebuild()


class KakaoSearchMeta(BaseModel):
    """Metadata returned alongside Kakao address search results."""

    model_config = ConfigDict(frozen=True)

    total_count: int = Field(default=0, ge=0)
    """Total number of documents matching the query."""

    pageable_count: int = Field(default=0, ge=0)
    """Number of results the API will paginate through."""

    is_end: bool = True
    """Whether this is the last page of results."""


class KakaoSearchResult(BaseModel):
    """Top-level response envelope from the Kakao address search API."""

    model_config = ConfigDict(frozen=True)

    meta: KakaoSearchMeta
    """Pagination metadata."""

    documents: list[KakaoAddressDocument]
    """Matched address documents (empty list when no match)."""


# ---------------------------------------------------------------------------
# HTTP client
# ---------------------------------------------------------------------------


async def search_address(
    query: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> KakaoSearchResult:
    """Search Kakao Local API for a Korean address string.

    Args:
        query: Free-form Korean address to geocode (e.g. "서울특별시 강남구 테헤란로").
        client: Optional injected ``httpx.AsyncClient`` for testing.

    Returns:
        A :class:`KakaoSearchResult` with matched documents (may be empty).

    Raises:
        ConfigurationError: If ``KOSMOS_KAKAO_API_KEY`` is not set.
        ToolExecutionError: On HTTP 401 (auth expired), 429 (rate limit),
            timeout, or other HTTP errors.
    """
    api_key = _require_env("KOSMOS_KAKAO_API_KEY")

    headers = {
        "Authorization": f"KakaoAK {api_key}",
        "Accept": "application/json",
    }
    request_params: dict[str, str | int] = {"query": query, "size": 2}

    logger.debug("Kakao address search: query=%r", query)

    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=_DEFAULT_TIMEOUT)

    try:
        assert client is not None
        response = await client.get(_BASE_URL, headers=headers, params=request_params)

        if response.status_code == 401:
            raise ToolExecutionError(
                tool_id="kakao_geocoding",
                message=(
                    "Kakao API authentication failed (HTTP 401). Check KOSMOS_KAKAO_API_KEY value."
                ),
            )
        if response.status_code == 429:
            raise ToolExecutionError(
                tool_id="kakao_geocoding",
                message="Kakao API rate limit exceeded (HTTP 429). Try again later.",
            )

        response.raise_for_status()

        payload: dict[str, Any] = response.json()
        result = KakaoSearchResult(**payload)

        logger.debug(
            "Kakao address search returned %d document(s) for query=%r",
            result.meta.total_count,
            query,
        )
        return result

    except (ToolExecutionError, ConfigurationError):
        raise
    # Let httpx exceptions (TimeoutException, HTTPStatusError, RequestError)
    # propagate directly so the recovery classifier can recognise them.
    finally:
        if own_client and client is not None:
            await client.aclose()
