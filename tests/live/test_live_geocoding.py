# SPDX-License-Identifier: Apache-2.0
"""Live validation tests for the Kakao-backed geocoding adapters.

Coverage scope
--------------
This module exercises the ``search_address`` Kakao adapter against the **real**
Kakao Local API.  Mock-based unit tests under ``tests/tools/geocoding/`` verify
logic in isolation; only live traffic can detect Kakao response-schema drift,
quota/rate-limit contract changes, or real-world edge cases.

NOTE: ``address_to_grid`` and ``address_to_region`` were removed in T049
(Epic #507).  Grid resolution is now handled internally by ``kma_forecast_fetch``
via ``latlon_to_lcc()``.  Administrative code resolution is handled by
``resolve_location(want='adm_cd')`` via the backend-only ``juso`` and ``sgis``
helpers.

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

from kosmos.tools.geocoding.kakao_client import search_address

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
