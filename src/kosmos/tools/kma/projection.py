# SPDX-License-Identifier: Apache-2.0
"""KMA Lambert Conformal Conic (LCC) projection — internal helper.

Converts WGS-84 (latitude, longitude) to KMA 5 km grid (nx, ny) using
the canonical constants published in the KMA VilageFcstInfoService_2.0
technical guide.

This module is *internal* to the KMA adapter package and is NOT exposed
as an LLM-visible tool. It was previously exposed as ``address_to_grid``
(tool #288); that exposure is removed in spec/022-mvp-main-tool US4 (T049).

Canonical constants (from KMA 단기예보 격자 기술 문서, 2021-12):
  RE    = 6371.00877  Earth radius [km]
  GRID  = 5.0         Grid resolution [km]
  SLAT1 = 30.0        Standard latitude 1 [degrees]
  SLAT2 = 60.0        Standard latitude 2 [degrees]
  OLON  = 126.0       Reference longitude [degrees]
  OLAT  = 38.0        Reference latitude [degrees]
  XO    = 43          Grid x-origin offset [grid cells]
  YO    = 136         Grid y-origin offset [grid cells]

Cross-check: 서울청사 (127.0495 E, 37.5665 N) → (nx=60, ny=127).
"""

from __future__ import annotations

import math


class KMADomainError(ValueError):
    """Raised when (lat, lon) is outside the KMA projection domain.

    The KMA short-term forecast grid covers the Korean peninsula and its
    surrounding maritime area.  Coordinates outside the range
    lat ∈ [22°, 46°] / lon ∈ [108°, 146°] are rejected because the
    LCC formula degenerates near the poles and produces nonsensical grid
    indices outside the service area.
    """

    def __init__(self, lat: float, lon: float) -> None:
        super().__init__(
            f"Coordinates ({lat}, {lon}) are outside the KMA forecast grid domain. "
            "Valid range: lat ∈ [22, 46], lon ∈ [108, 146]."
        )
        self.lat = lat
        self.lon = lon


# ---------------------------------------------------------------------------
# Domain bounds (KMA coverage area)
# ---------------------------------------------------------------------------

_LAT_MIN = 22.0
_LAT_MAX = 46.0
_LON_MIN = 108.0
_LON_MAX = 146.0

# ---------------------------------------------------------------------------
# KMA LCC constants
# ---------------------------------------------------------------------------

_RE = 6371.00877  # Earth radius [km]
_GRID = 5.0  # Grid resolution [km]
_SLAT1 = 30.0  # Standard latitude 1 [degrees]
_SLAT2 = 60.0  # Standard latitude 2 [degrees]
_OLON = 126.0  # Reference longitude [degrees]
_OLAT = 38.0  # Reference latitude [degrees]
_XO = 43.0  # Grid x-origin [cells]
_YO = 136.0  # Grid y-origin [cells]

# Pre-compute projection constants at module load time (no I/O)
_DEGRAD = math.pi / 180.0
_RE_GRID = _RE / _GRID  # re in grid units
_SLAT1_RAD = _SLAT1 * _DEGRAD
_SLAT2_RAD = _SLAT2 * _DEGRAD
_OLON_RAD = _OLON * _DEGRAD
_OLAT_RAD = _OLAT * _DEGRAD

_SN = math.log(math.cos(_SLAT1_RAD) / math.cos(_SLAT2_RAD)) / math.log(
    math.tan(math.pi * 0.25 + _SLAT2_RAD * 0.5) / math.tan(math.pi * 0.25 + _SLAT1_RAD * 0.5)
)
_SF = (math.tan(math.pi * 0.25 + _SLAT1_RAD * 0.5) ** _SN) * math.cos(_SLAT1_RAD) / _SN
_RO = _RE_GRID * _SF / (math.tan(math.pi * 0.25 + _OLAT_RAD * 0.5) ** _SN)


def latlon_to_lcc(lat: float, lon: float) -> tuple[int, int]:
    """Convert WGS-84 (lat, lon) to KMA grid (nx, ny) via Lambert Conformal Conic.

    Uses the official KMA VilageFcstInfoService_2.0 projection parameters.

    Args:
        lat: Latitude in decimal degrees (WGS-84).  Range [22, 46].
        lon: Longitude in decimal degrees (WGS-84).  Range [108, 146].

    Returns:
        ``(nx, ny)`` integer KMA grid coordinates.

    Raises:
        KMADomainError: If ``lat`` or ``lon`` is outside the KMA grid domain.
    """
    if not (_LAT_MIN <= lat <= _LAT_MAX) or not (_LON_MIN <= lon <= _LON_MAX):
        raise KMADomainError(lat, lon)

    lat_rad = lat * _DEGRAD
    ra = _RE_GRID * _SF / (math.tan(math.pi * 0.25 + lat_rad * 0.5) ** _SN)

    theta = lon * _DEGRAD - _OLON_RAD
    if theta > math.pi:
        theta -= 2.0 * math.pi
    if theta < -math.pi:
        theta += 2.0 * math.pi
    theta *= _SN

    nx = int(ra * math.sin(theta) + _XO + 1.5)
    ny = int(_RO - ra * math.cos(theta) + _YO + 1.5)
    return nx, ny
