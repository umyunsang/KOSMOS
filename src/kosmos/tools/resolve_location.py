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

import httpx

from kosmos.tools.models import (
    AddressResult,
    AdmCodeResult,
    CoordResult,
    POIResult,
    ResolveBundle,
    ResolveError,
    ResolveLocationInput,
)

logger = logging.getLogger(__name__)


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

    Delegates to the shared ``geocoding.juso.lookup_adm_cd`` backend helper.
    Returns AdmCodeResult on success, None on failure/no result.
    """
    from kosmos.settings import settings  # noqa: PLC0415
    from kosmos.tools.geocoding.juso import lookup_adm_cd  # noqa: PLC0415

    confm_key = settings.juso_confm_key
    if not confm_key:
        logger.debug("juso: KOSMOS_JUSO_CONFM_KEY not set, skipping")
        return None

    result = await lookup_adm_cd(query, confm_key=confm_key, client=client)
    if result is None:
        return None

    return AdmCodeResult(
        kind="adm_cd",
        code=result["adm_cd"],
        name=result["name"],
        level=result["level"],  # type: ignore[arg-type]
        source="juso",
    )


async def _sgis_adm_cd(
    query: str,
    coords: CoordResult | None = None,
    *,
    client: httpx.AsyncClient | None = None,
) -> AdmCodeResult | None:
    """Try to resolve 10-digit adm_cd via SGIS API.

    Delegates to the shared ``geocoding.sgis.lookup_adm_cd_by_coords`` backend
    helper.  Requires coordinates — returns None if not available.
    """
    if coords is None:
        logger.debug("sgis adm_cd: no coords available, skipping")
        return None

    from kosmos.settings import settings  # noqa: PLC0415
    from kosmos.tools.geocoding.sgis import lookup_adm_cd_by_coords  # noqa: PLC0415

    consumer_key = settings.sgis_key
    consumer_secret = settings.sgis_secret
    if not consumer_key or not consumer_secret:
        logger.debug("sgis: KOSMOS_SGIS_KEY/SECRET not set, skipping")
        return None

    result = await lookup_adm_cd_by_coords(
        lat=coords.lat,
        lon=coords.lon,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        client=client,
    )
    if result is None:
        return None

    return AdmCodeResult(
        kind="adm_cd",
        code=result["adm_cd"],
        name=result["name"],
        level=result["level"],  # type: ignore[arg-type]
        source="sgis",
    )


async def resolve_location(  # noqa: C901
    inp: ResolveLocationInput,
    *,
    client: httpx.AsyncClient | None = None,
) -> CoordResult | AdmCodeResult | AddressResult | POIResult | ResolveBundle | ResolveError:
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
        # adm.name is an administrative area name (e.g. "서울특별시 강남구"), not a
        # specific road or jibun address.  Returning it in road_address would
        # mislead callers, so we surface an honest not_found error instead.
        return ResolveError(
            kind="error",
            reason="not_found",
            message=(
                f"JUSO resolved only an administrative area ({adm.name!r}) for"
                f" query {query!r}, not a specific road or jibun address."
            ),
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
                    # address_type gives "REGION"|"ROAD"|"REGION_ADDR"|"ROAD_ADDR"
                    # which is a more meaningful category than the province name
                    # that region_1depth_name would return.
                    category = getattr(doc, "address_type", "")

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
        coords_bundle: CoordResult | None = None
        adm_bundle: AdmCodeResult | None = None
        address_result: AddressResult | None = None
        poi_result: POIResult | None = None

        # Resolve coordinates via kakao
        coords_bundle = await _kakao_coords(query, client=client)

        # Resolve adm_cd via juso (preferred) or sgis (fallback)
        adm_bundle = await _juso_adm_cd(query, client=client)
        if adm_bundle is None:
            adm_bundle = await _sgis_adm_cd(query, coords=coords_bundle, client=client)

        if want == "all":
            # Single Kakao call to extract address, coords, and POI together,
            # avoiding the three separate calls (_kakao_geocode, _kakao_coords,
            # search_address) that would hit the same endpoint with the same query.
            try:
                from kosmos.tools.geocoding.kakao_client import search_address

                kakao_result = await search_address(query, client=client)
                if kakao_result.documents:
                    doc = kakao_result.documents[0]
                    try:
                        lat = float(doc.y)
                        lon = float(doc.x)
                    except (ValueError, TypeError):
                        lat = lon = None  # type: ignore[assignment]

                    if lat is not None and lon is not None:
                        # Overwrite coords_bundle with fresh values from this call
                        # so all "all"-mode data shares the same source response.
                        total = kakao_result.meta.total_count
                        confidence = (
                            "high" if total == 1 else ("medium" if total <= 3 else "low")
                        )
                        coords_bundle = CoordResult(
                            kind="coords",
                            lat=lat,
                            lon=lon,
                            confidence=confidence,  # type: ignore[arg-type]
                            source="kakao",
                        )

                        poi_result = POIResult(
                            kind="poi",
                            name=doc.address_name,
                            category=getattr(doc, "address_type", ""),
                            lat=lat,
                            lon=lon,
                            source="kakao",
                        )

                    if doc.road_address or doc.address:
                        address_result = AddressResult(
                            kind="address",
                            road_address=(
                                doc.road_address.address_name if doc.road_address else None
                            ),
                            jibun_address=(
                                doc.address.address_name if doc.address else None
                            ),
                            postal_code=(
                                doc.road_address.zone_no if doc.road_address else None
                            ),
                            source="kakao",
                        )
            except Exception:
                logger.debug(
                    "Kakao resolution failed for %r; continuing without address/POI",
                    query,
                    exc_info=True,
                )

        if coords_bundle is None and adm_bundle is None:
            return ResolveError(
                kind="error",
                reason="not_found",
                message=f"Could not resolve location for query {query!r}.",
            )

        return ResolveBundle(
            kind="bundle",
            source="bundle",
            coords=coords_bundle,
            adm_cd=adm_bundle,
            address=address_result if want == "all" else None,
            poi=poi_result if want == "all" else None,
        )

    # Fallback for unrecognized want values (shouldn't reach here due to Pydantic)
    return ResolveError(
        kind="error",
        reason="invalid_query",
        message=f"Unsupported want={want!r}.",
    )
