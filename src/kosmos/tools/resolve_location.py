# SPDX-License-Identifier: Apache-2.0
"""resolve_location facade coroutine — T023.

Single entry point for converting a natural-language place reference into
structured location data (coordinates, 10-digit 행정동 code, address, POI).

Deterministic resolver chain: kakao → juso → sgis.
Short-circuits on the first non-error result for the requested ``want`` type.

FR-002: Accepts ``query``, ``want``, and optional ``near`` anchor.
FR-003: Kakao / JUSO / SGIS are backend-only; never exposed as LLM tools.
FR-035: ``source`` field populated on every successful result.
FR-036: ``ResolveBundle`` carries per-backend provenance.
"""

from __future__ import annotations

import logging
import re

import httpx

from kosmos.tools.models import (
    AdmCodeResult,
    AddressResult,
    CoordResult,
    POIResult,
    ResolveBundle,
    ResolveError,
    ResolveLocationInput,
)

logger = logging.getLogger(__name__)

# Regex patterns for input classification (FR-004 dispatch rules §4.4)
_COORD_RE = re.compile(r"^-?\d+\.?\d*\s*,\s*-?\d+\.?\d*$")
_ROAD_ADDR_RE = re.compile(r"[로길]\s*\d+")


def _classify_query(query: str) -> str:
    """Classify a query as 'coord', 'address', or 'place'."""
    stripped = query.strip()
    if _COORD_RE.match(stripped):
        return "coord"
    if _ROAD_ADDR_RE.search(stripped):
        return "address"
    return "place"


async def _kakao_geocode(
    query: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> CoordResult | AddressResult | POIResult | None:
    """Try to resolve via Kakao Local API.

    Returns a CoordResult, AddressResult, or POIResult on success.
    Returns None on no-result or config/network error.
    """
    try:
        from kosmos.tools.geocoding.kakao_client import search_address

        result = await search_address(query, client=client)
        if not result.documents:
            return None

        doc = result.documents[0]
        try:
            lat = float(doc.y) if doc.y else None
            lon = float(doc.x) if doc.x else None
        except (ValueError, TypeError):
            lat = lon = None

        if lat is None or lon is None:
            return None

        # Extract address info from road_address or address block
        addr_block = doc.road_address or doc.address
        road = doc.road_address.address_name if doc.road_address else None
        jibun = doc.address.address_name if doc.address else None

        # Build AddressResult if we have address info
        if addr_block:
            return AddressResult(
                kind="address",
                road_address=road,
                jibun_address=jibun,
                postal_code=doc.road_address.zone_no if doc.road_address else None,
                source="kakao",
            )

        # Fallback: CoordResult only
        return CoordResult(
            kind="coords",
            lat=lat,
            lon=lon,
            confidence="high" if result.meta.total_count == 1 else "medium",
            source="kakao",
        )
    except Exception as exc:
        logger.debug("kakao geocode failed for %r: %s", query, exc)
        return None


async def _kakao_coords(
    query: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> CoordResult | None:
    """Try to resolve coordinates via Kakao Local API."""
    try:
        from kosmos.tools.geocoding.kakao_client import search_address

        result = await search_address(query, client=client)
        if not result.documents:
            return None

        doc = result.documents[0]
        try:
            lat = float(doc.y) if doc.y else None
            lon = float(doc.x) if doc.x else None
        except (ValueError, TypeError):
            lat = lon = None

        if lat is None or lon is None:
            return None

        confidence: str
        if result.meta.total_count == 1:
            confidence = "high"
        elif result.meta.total_count <= 3:
            confidence = "medium"
        else:
            confidence = "low"

        return CoordResult(
            kind="coords",
            lat=lat,
            lon=lon,
            confidence=confidence,  # type: ignore[arg-type]
            source="kakao",
        )
    except Exception as exc:
        logger.debug("kakao coords failed for %r: %s", query, exc)
        return None


async def _juso_adm_cd(
    query: str,
    *,
    client: httpx.AsyncClient | None = None,
) -> AdmCodeResult | None:
    """Try to resolve 10-digit adm_cd via juso.go.kr API.

    Returns AdmCodeResult on success, None on failure/no result.
    """
    try:
        from kosmos.settings import settings

        confm_key = settings.juso_confm_key
        if not confm_key:
            logger.debug("juso: KOSMOS_JUSO_CONFM_KEY not set, skipping")
            return None

        params = {
            "confmKey": confm_key,
            "currentPage": "1",
            "countPerPage": "1",
            "keyword": query,
            "resultType": "json",
        }

        own_client = client is None
        _client = httpx.AsyncClient(timeout=10.0) if own_client else client
        assert _client is not None

        try:
            resp = await _client.get(
                "https://business.juso.go.kr/addrlink/addrLinkApi.do",
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", {})
            juso_list = results.get("juso", [])
            common = results.get("common", {})

            if not juso_list:
                return None

            item = juso_list[0]
            adm_cd = item.get("admCd", "")
            if not adm_cd or len(adm_cd) != 10:
                return None

            road_addr = item.get("roadAddr", "")
            sgg_nm = item.get("siNm", "") + " " + item.get("sggNm", "")

            # Determine level from admCd trailing digits
            # 10-digit: xxxx000000=sido, xxxxxx0000=sigungu, xxxxxxxxxx=emd
            if adm_cd.endswith("00000000"):
                level = "sido"
            elif adm_cd.endswith("0000"):
                level = "sigungu"
            else:
                level = "eupmyeondong"

            return AdmCodeResult(
                kind="adm_cd",
                code=adm_cd,
                name=sgg_nm.strip() or road_addr,
                level=level,  # type: ignore[arg-type]
                source="juso",
            )
        finally:
            if own_client and _client:
                await _client.aclose()

    except Exception as exc:
        logger.debug("juso adm_cd failed for %r: %s", query, exc)
        return None


async def _sgis_adm_cd(
    query: str,
    coords: CoordResult | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> AdmCodeResult | None:
    """Try to resolve 10-digit adm_cd via SGIS API.

    If coords are available, uses coord2region endpoint.
    Otherwise, returns None (SGIS needs coordinates for adm_cd lookup).
    """
    # SGIS adm_cd lookup requires coordinates; fall through if not available
    if coords is None:
        logger.debug("sgis adm_cd: no coords available, skipping")
        return None

    try:
        from kosmos.settings import settings

        consumer_key = settings.sgis_key
        consumer_secret = settings.sgis_secret
        if not consumer_key or not consumer_secret:
            logger.debug("sgis: KOSMOS_SGIS_KEY/SECRET not set, skipping")
            return None

        own_client = client is None
        _client = httpx.AsyncClient(timeout=10.0) if own_client else client
        assert _client is not None

        try:
            # Step 1: obtain access token
            token_resp = await _client.get(
                "https://sgisapi.kostat.go.kr/OpenAPI3/auth/authentication.json",
                params={
                    "consumer_key": consumer_key,
                    "consumer_secret": consumer_secret,
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            access_token = token_data.get("result", {}).get("accessToken", "")
            if not access_token:
                return None

            # Step 2: coord2region
            coord_resp = await _client.get(
                "https://sgisapi.kostat.go.kr/OpenAPI3/addr/rgeocode.json",
                params={
                    "accessToken": access_token,
                    "x_coor": str(coords.lon),
                    "y_coor": str(coords.lat),
                    "addr_type": "20",  # 행정동
                },
            )
            coord_resp.raise_for_status()
            coord_data = coord_resp.json()

            result_list = coord_data.get("result", [])
            if not result_list:
                return None

            item = result_list[0]
            adm_cd_raw = str(item.get("adm_cd", ""))
            if not adm_cd_raw or len(adm_cd_raw) < 8:
                return None

            # SGIS returns 8-digit code; pad to 10
            adm_cd = adm_cd_raw.ljust(10, "0")[:10]
            adm_nm = item.get("adm_nm", "")

            if adm_cd.endswith("00000000"):
                level = "sido"
            elif adm_cd.endswith("0000"):
                level = "sigungu"
            else:
                level = "eupmyeondong"

            return AdmCodeResult(
                kind="adm_cd",
                code=adm_cd,
                name=adm_nm,
                level=level,  # type: ignore[arg-type]
                source="sgis",
            )
        finally:
            if own_client and _client:
                await _client.aclose()

    except Exception as exc:
        logger.debug("sgis adm_cd failed for %r: %s", query, exc)
        return None


async def resolve_location(
    inp: ResolveLocationInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> (
    CoordResult
    | AdmCodeResult
    | AddressResult
    | POIResult
    | ResolveBundle
    | ResolveError
):
    """Resolve a natural-language place reference to structured location data.

    Deterministic resolver chain: kakao → juso → sgis.
    Short-circuits on the first non-error result.

    Args:
        inp: Validated ResolveLocationInput.
        client: Optional httpx.AsyncClient for test injection.

    Returns:
        One of the 6 ResolveLocationOutput variants.
    """
    query = inp.query.strip()
    want = inp.want

    if not query:
        return ResolveError(
            kind="error",
            reason="empty_query",
            message="Query must not be empty.",
        )

    logger.debug("resolve_location: query=%r want=%s", query, want)

    # --- coords path ---
    if want == "coords":
        coords = await _kakao_coords(query, client=client)
        if coords:
            return coords
        return ResolveError(
            kind="error",
            reason="not_found",
            message=f"Could not resolve coordinates for query {query!r}.",
        )

    # --- adm_cd path ---
    if want == "adm_cd":
        # Chain: juso (has admCd directly) → sgis (coord2region) → kakao+sgis
        adm = await _juso_adm_cd(query, client=client)
        if adm:
            return adm

        # Try kakao for coords then sgis for adm_cd
        coords = await _kakao_coords(query, client=client)
        adm = await _sgis_adm_cd(query, coords=coords, client=client)
        if adm:
            return adm

        return ResolveError(
            kind="error",
            reason="not_found",
            message=f"Could not resolve administrative code for query {query!r}.",
        )

    # --- address path ---
    if want in ("road_address", "jibun_address"):
        geo = await _kakao_geocode(query, client=client)
        if geo and isinstance(geo, AddressResult):
            return geo
        # Try juso for canonical road address
        adm = await _juso_adm_cd(query, client=client)
        if adm is None:
            return ResolveError(
                kind="error",
                reason="not_found",
                message=f"Could not resolve address for query {query!r}.",
            )
        # Convert juso result to AddressResult (juso returns road address in admCd call)
        return AddressResult(
            kind="address",
            road_address=adm.name,
            jibun_address=None,
            postal_code=None,
            source="juso",
        )

    # --- poi path ---
    if want == "poi":
        try:
            from kosmos.tools.geocoding.kakao_client import search_address

            result = await search_address(query, client=client)
            if result.documents:
                doc = result.documents[0]
                try:
                    lat = float(doc.y)
                    lon = float(doc.x)
                except (ValueError, TypeError):
                    lat = lon = None  # type: ignore[assignment]

                if lat is not None and lon is not None:
                    addr_block = doc.road_address or doc.address
                    category = ""
                    if addr_block:
                        category = getattr(addr_block, "region_1depth_name", "")

                    return POIResult(
                        kind="poi",
                        name=doc.address_name,
                        category=category,
                        lat=lat,
                        lon=lon,
                        source="kakao",
                    )
        except Exception as exc:
            logger.debug("poi resolution failed for %r: %s", query, exc)

        return ResolveError(
            kind="error",
            reason="not_found",
            message=f"Could not resolve POI for query {query!r}.",
        )

    # --- coords_and_admcd (default MVP bundle) ---
    if want in ("coords_and_admcd", "all"):
        coords: CoordResult | None = None
        adm: AdmCodeResult | None = None
        address_result: AddressResult | None = None
        poi_result: POIResult | None = None

        # Resolve coordinates via kakao
        coords = await _kakao_coords(query, client=client)

        # Resolve adm_cd via juso (preferred) or sgis (fallback)
        adm = await _juso_adm_cd(query, client=client)
        if adm is None:
            adm = await _sgis_adm_cd(query, coords=coords, client=client)

        if want == "all":
            # Also resolve address and POI
            geo = await _kakao_geocode(query, client=client)
            if isinstance(geo, AddressResult):
                address_result = geo

            try:
                from kosmos.tools.geocoding.kakao_client import search_address

                result = await search_address(query, client=client)
                if result.documents:
                    doc = result.documents[0]
                    try:
                        lat = float(doc.y)
                        lon = float(doc.x)
                    except (ValueError, TypeError):
                        lat = lon = None  # type: ignore[assignment]

                    if lat is not None and lon is not None:
                        poi_result = POIResult(
                            kind="poi",
                            name=doc.address_name,
                            category="",
                            lat=lat,
                            lon=lon,
                            source="kakao",
                        )
            except Exception:
                pass

        if coords is None and adm is None:
            return ResolveError(
                kind="error",
                reason="not_found",
                message=f"Could not resolve location for query {query!r}.",
            )

        return ResolveBundle(
            kind="bundle",
            source="bundle",
            coords=coords,
            adm_cd=adm,
            address=address_result if want == "all" else None,
            poi=poi_result if want == "all" else None,
        )

    # Fallback for unrecognized want values (shouldn't reach here due to Pydantic)
    return ResolveError(
        kind="error",
        reason="invalid_query",
        message=f"Unsupported want={want!r}.",
    )
