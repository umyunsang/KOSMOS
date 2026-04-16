# SPDX-License-Identifier: Apache-2.0
"""KOSMOS Geocoding backend helper package.

Provides backend-only helpers for resolving Korean addresses to
administrative codes and geographic coordinates:

  * ``juso_lookup_adm_cd`` — queries Juso API for administrative codes (adm_cd)
  * ``sgis_lookup_adm_cd_by_coords`` — queries SGIS API to reverse-geocode
    coordinates to administrative codes

These helpers are NOT LLM-visible tools. They are available as public
re-exports for programmatic use by adapters and internal services.
The ``resolve_location`` tool currently uses ``kakao_client`` directly
for its geocoding chain.

Public re-exports
-----------------
- :func:`juso_lookup_adm_cd`
- :func:`sgis_lookup_adm_cd_by_coords`
"""

from __future__ import annotations

from kosmos.tools.geocoding.juso import lookup_adm_cd as juso_lookup_adm_cd
from kosmos.tools.geocoding.sgis import lookup_adm_cd_by_coords as sgis_lookup_adm_cd_by_coords

__all__ = [
    "juso_lookup_adm_cd",
    "sgis_lookup_adm_cd_by_coords",
]
