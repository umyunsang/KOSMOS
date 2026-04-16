# SPDX-License-Identifier: Apache-2.0
"""Centralised pydantic-settings configuration for KOSMOS.

All runtime configuration is read from ``KOSMOS_``-prefixed environment
variables (FR-032, FR-033, FR-034).  Defaults are fail-closed: empty strings
for secrets, conservative integers for rate/freshness windows.

Usage::

    from kosmos.settings import settings
    key = settings.kosmos_kakao_api_key
"""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class KosmosSettings(BaseSettings):
    """KOSMOS runtime configuration loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_prefix="KOSMOS_",
        env_file=".env",
        extra="ignore",
    )

    # --- Retrieval gate (FR-033) ---
    lookup_topk: int = Field(default=5, ge=1, le=20)
    """Default top-k for lookup(mode='search'). Clamped to [1, 20]."""

    # --- NMC freshness SLO (FR-034; enforcement deferred to follow-on epic) ---
    nmc_freshness_minutes: int = Field(default=30, ge=1, le=1440)
    """Max acceptable age of NMC hvidate field in minutes."""

    # --- External API keys (FR-032) ---
    kakao_api_key: str = Field(default="")
    """Kakao REST API key (KOSMOS_KAKAO_API_KEY)."""

    juso_confm_key: str = Field(default="")
    """행정안전부 도로명주소 확인키 (KOSMOS_JUSO_CONFM_KEY)."""

    sgis_key: str = Field(default="")
    """SGIS API consumer key (KOSMOS_SGIS_KEY)."""

    sgis_secret: str = Field(default="")
    """SGIS API consumer secret (KOSMOS_SGIS_SECRET)."""

    data_go_kr_api_key: str = Field(default="")
    """공공데이터포털 통합 API 키, shared by KOROAD / KMA / HIRA (KOSMOS_DATA_GO_KR_API_KEY)."""


settings: KosmosSettings = KosmosSettings()
"""Module-level singleton.  Import this directly in production code."""
