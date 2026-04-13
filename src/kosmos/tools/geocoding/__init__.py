# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Geocoding adapter package.

Provides two tools that convert Korean addresses into structured location data:

  * ``address_to_region`` — resolves a free-form Korean address string to
    province (시도) and district (구군) codes used by KOROAD and other APIs.
  * ``address_to_grid`` — resolves a free-form Korean address string to the
    KMA 5 km grid (nx, ny) coordinates used by weather APIs.

Both tools use the Kakao Local API (``dapi.kakao.com``) for geocoding and fall
back to the built-in KMA region lookup table when the Kakao API is unavailable.

Public re-exports
-----------------
- :class:`AddressToRegionInput`
- :class:`AddressToRegionOutput`
- :class:`ADDRESS_TO_REGION_TOOL`
- :func:`register_address_to_region`
- :class:`AddressToGridInput`
- :class:`AddressToGridOutput`
- :class:`ADDRESS_TO_GRID_TOOL`
- :func:`register_address_to_grid`
"""

from __future__ import annotations

from kosmos.tools.geocoding.address_to_grid import (
    ADDRESS_TO_GRID_TOOL,
    AddressToGridInput,
    AddressToGridOutput,
)
from kosmos.tools.geocoding.address_to_grid import (
    register as register_address_to_grid,
)
from kosmos.tools.geocoding.address_to_region import (
    ADDRESS_TO_REGION_TOOL,
    AddressToRegionInput,
    AddressToRegionOutput,
)
from kosmos.tools.geocoding.address_to_region import (
    register as register_address_to_region,
)

__all__ = [
    "AddressToRegionInput",
    "AddressToRegionOutput",
    "ADDRESS_TO_REGION_TOOL",
    "register_address_to_region",
    "AddressToGridInput",
    "AddressToGridOutput",
    "ADDRESS_TO_GRID_TOOL",
    "register_address_to_grid",
]
