# SPDX-License-Identifier: Apache-2.0
"""Live validation tests for the Kakao-backed geocoding adapters (Epic #288).

Coverage scope
--------------
This module exercises the three geocoding adapters — ``search_address``,
``address_to_grid``, and ``address_to_region`` — against the **real** Kakao
Local API.  Mock-based unit tests under ``tests/tools/geocoding/`` verify
logic in isolation; only live traffic can detect Kakao response-schema drift,
quota/rate-limit contract changes, or real-world edge cases such as unmapped
remote regions.

Kakao Developers prerequisite
------------------------------
The operator must activate the Kakao Local API before running this suite:

    앱 설정 → 제품 설정 → 카카오맵 → 사용 설정 → 상태 ON

Platform registration is **not** required for server-side REST calls — only
the one-time service activation listed above.  The REST API key is supplied
via ``KOSMOS_KAKAO_API_KEY``.

Running these tests
-------------------
Tests are opt-in and never run in CI::

    uv run pytest tests/live/test_live_geocoding.py -m live -v

``KOSMOS_KAKAO_API_KEY`` must be set; the suite hard-fails immediately if the
variable is absent (FR-004 / Story 1 AS-8).
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Coroutine
from typing import Any

import pytest

from kosmos.tools.errors import ToolExecutionError
from kosmos.tools.geocoding.address_to_grid import AddressToGridInput
from kosmos.tools.geocoding.address_to_grid import _call as grid_call
from kosmos.tools.geocoding.address_to_region import _resolve
from kosmos.tools.geocoding.kakao_client import search_address
from kosmos.tools.koroad.code_tables import GugunCode, SidoCode

logger = logging.getLogger(__name__)

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

# Type alias matching the kakao_rate_limit_delay fixture yield type.
_DelayFn = Callable[[], Coroutine[Any, Any, None]]


# ---------------------------------------------------------------------------
# T005 — search_address happy path
# ---------------------------------------------------------------------------


async def test_live_kakao_search_address_happy(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live Kakao address search returns at least one document for a canonical Seoul address.

    Asserts:
    - At least one document is returned (non-empty results list).
    - Each of the always-present fields ``address_name``, ``x``, ``y`` is non-empty.
    - ``x`` (longitude) parses to a float in the Korea bounding box [124, 132].
    - ``y`` (latitude) parses to a float in the Korea bounding box [33, 39].
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    result = await search_address("서울특별시 강남구 테헤란로 152")
    await kakao_rate_limit_delay()

    assert len(result.documents) >= 1, (
        "Expected at least one document for a canonical Seoul address"
    )

    doc = result.documents[0]

    # Always-present fields per KakaoAddressDocument model
    assert doc.address_name, "address_name must be non-empty"
    assert doc.x, "x (longitude) must be non-empty"
    assert doc.y, "y (latitude) must be non-empty"

    # Korea geographic bounding box validation (structural, not exact)
    lon = float(doc.x)
    lat = float(doc.y)
    assert 124.0 <= lon <= 132.0, f"Longitude {lon} out of Korea bounding box [124, 132]"
    assert 33.0 <= lat <= 39.0, f"Latitude {lat} out of Korea bounding box [33, 39]"

    logger.debug(
        "test_live_kakao_search_address_happy: address_name=%r lon=%.5f lat=%.5f",
        doc.address_name,
        lon,
        lat,
    )


# ---------------------------------------------------------------------------
# T006 — search_address empty-result (nonsense query)
# ---------------------------------------------------------------------------


async def test_live_kakao_search_address_nonsense(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live Kakao address search returns empty documents for a nonsense query without raising.

    The adapter's empty-result contract must match real Kakao behavior: the
    function returns a ``KakaoSearchResult`` with an empty ``documents`` list
    rather than raising any exception.
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    result = await search_address("xyzzy_qwerty_무의미한쿼리_12345_!@#")
    await kakao_rate_limit_delay()

    assert result.documents == [], (
        "Expected empty documents list for a nonsense query; "
        f"got {len(result.documents)} document(s)"
    )


# ---------------------------------------------------------------------------
# T007 — address_to_grid Seoul landmark
# ---------------------------------------------------------------------------


async def test_live_address_to_grid_seoul_landmark(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live address_to_grid returns KMA grid in the Seoul band for a Seoul landmark.

    Seoul center grid (nx=60, ny=127) with ±3 tolerance for district-level variance.
    Asserts:
    - ``nx`` is in [57, 63].
    - ``ny`` is in [124, 130].
    - ``source`` is not ``"not_found"`` (grid was resolved).
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    params = AddressToGridInput(address="서울특별시 중구 세종대로 110")
    result = await grid_call(params)
    await kakao_rate_limit_delay()

    nx = result["nx"]
    ny = result["ny"]
    source = result["source"]

    assert source != "not_found", "address_to_grid returned source='not_found' for Seoul landmark"
    assert nx is not None, "nx must not be None for a resolved Seoul address"
    assert ny is not None, "ny must not be None for a resolved Seoul address"
    assert 57 <= nx <= 63, f"Seoul landmark nx={nx} outside expected range [57, 63]"
    assert 124 <= ny <= 130, f"Seoul landmark ny={ny} outside expected range [124, 130]"

    logger.debug("test_live_address_to_grid_seoul_landmark: nx=%d ny=%d source=%s", nx, ny, source)


# ---------------------------------------------------------------------------
# T008 — address_to_grid Busan landmark
# ---------------------------------------------------------------------------


async def test_live_address_to_grid_busan_landmark(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live address_to_grid returns KMA grid in the Busan band for a Busan landmark.

    Asserts:
    - ``nx`` is in [95, 100].
    - ``ny`` is in [73, 78].
    - ``source`` is not ``"not_found"`` (grid was resolved).
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    params = AddressToGridInput(address="부산광역시 해운대구 해운대해변로 264")
    result = await grid_call(params)
    await kakao_rate_limit_delay()

    nx = result["nx"]
    ny = result["ny"]
    source = result["source"]

    assert source != "not_found", "address_to_grid returned source='not_found' for Busan landmark"
    assert nx is not None, "nx must not be None for a resolved Busan address"
    assert ny is not None, "ny must not be None for a resolved Busan address"
    assert 95 <= nx <= 100, f"Busan landmark nx={nx} outside expected range [95, 100]"
    assert 73 <= ny <= 78, f"Busan landmark ny={ny} outside expected range [73, 78]"

    logger.debug("test_live_address_to_grid_busan_landmark: nx=%d ny=%d source=%s", nx, ny, source)


# ---------------------------------------------------------------------------
# T009 — address_to_region Gangnam
# ---------------------------------------------------------------------------


async def test_live_address_to_region_gangnam(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live address_to_region maps a Gangnam address to SEOUL / SEOUL_GANGNAM codes.

    Asserts:
    - ``sido_code`` equals ``SidoCode.SEOUL`` (integer 11).
    - ``gugun_code`` equals ``GugunCode.SEOUL_GANGNAM``.
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    output = await _resolve("서울특별시 강남구 테헤란로 152")
    await kakao_rate_limit_delay()

    assert output.sido_code == SidoCode.SEOUL, (
        f"Expected sido_code={int(SidoCode.SEOUL)} (SEOUL), got {output.sido_code}"
    )
    assert output.gugun_code == GugunCode.SEOUL_GANGNAM, (
        f"Expected gugun_code={int(GugunCode.SEOUL_GANGNAM)} (SEOUL_GANGNAM), "
        f"got {output.gugun_code}"
    )

    logger.debug(
        "test_live_address_to_region_gangnam: sido_code=%s gugun_code=%s",
        output.sido_code,
        output.gugun_code,
    )


# ---------------------------------------------------------------------------
# T010 — address_to_region Busan
# ---------------------------------------------------------------------------


async def test_live_address_to_region_busan(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live address_to_region maps a Busan address to BUSAN sido code.

    Asserts:
    - ``sido_code`` equals ``SidoCode.BUSAN`` (integer 26).
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    output = await _resolve("부산광역시 해운대구 해운대해변로 264")
    await kakao_rate_limit_delay()

    assert output.sido_code == SidoCode.BUSAN, (
        f"Expected sido_code={int(SidoCode.BUSAN)} (BUSAN), got {output.sido_code}"
    )

    logger.debug(
        "test_live_address_to_region_busan: sido_code=%s gugun_code=%s",
        output.sido_code,
        output.gugun_code,
    )


# ---------------------------------------------------------------------------
# T011 — address_to_region unmapped remote region
# ---------------------------------------------------------------------------


async def test_live_address_to_region_unmapped_region(
    kakao_api_key: str,
    kakao_rate_limit_delay: _DelayFn,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Live address_to_region handles a remote / unmapped area without crashing.

    "울릉도" is a real Korean island.  The adapter must either:

    (a) Return a structured ``AddressToRegionOutput`` — if Kakao returns a
        document, the output may have ``sido_code=None`` or ``gugun_code=None``
        for regions not covered by the mapping table, which is the documented
        fail-closed "unmapped" contract.
    (b) Raise ``ToolExecutionError`` — if Kakao returns no results for the
        query, the adapter raises its documented "Address not found" error,
        which is also a structured, expected failure path.

    In both cases the test asserts that no unexpected exception type escapes —
    the adapter never crashes silently or raises a bare ``Exception``.
    """
    monkeypatch.setenv("KOSMOS_KAKAO_API_KEY", kakao_api_key)

    try:
        output = await _resolve("울릉도")
        await kakao_rate_limit_delay()

        # Kakao returned a document — verify the output is structurally valid.
        # sido_code and/or gugun_code may be None for unmapped areas.
        from kosmos.tools.geocoding.address_to_region import AddressToRegionOutput

        assert isinstance(output, AddressToRegionOutput), (
            f"Expected AddressToRegionOutput, got {type(output)}"
        )
        # resolved_address must always be a string (never None)
        assert isinstance(output.resolved_address, str)

        logger.debug(
            "test_live_address_to_region_unmapped_region: resolved=%r sido_code=%s gugun_code=%s",
            output.resolved_address,
            output.sido_code,
            output.gugun_code,
        )

    except ToolExecutionError as exc:
        await kakao_rate_limit_delay()
        # ToolExecutionError is the adapter's documented fail-closed contract
        # for "address not found" — this is an expected, structured failure.
        logger.debug(
            "test_live_address_to_region_unmapped_region: ToolExecutionError raised "
            "(address not found path): %s",
            exc,
        )
        # Verify the error is correctly attributed to the address_to_region tool
        assert exc.tool_id == "address_to_region", (
            f"Expected tool_id='address_to_region', got {exc.tool_id!r}"
        )
