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

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from kosmos.safety._settings import SafetySettings


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

    # --- Safety pipeline (Epic #466) ---
    safety: SafetySettings = Field(default_factory=SafetySettings)
    """Four-layer safety pipeline configuration (KOSMOS_SAFETY_* env vars)."""

    # --- Agent Swarm (Epic #13) ---
    agent_mailbox_root: Path = Field(
        default_factory=lambda: Path.home() / ".kosmos" / "mailbox",
    )
    """Root directory for FileMailbox (KOSMOS_AGENT_MAILBOX_ROOT).

    MUST be an absolute path. Relative paths are rejected at validation time.
    Default: ~/.kosmos/mailbox
    """

    agent_mailbox_max_messages: int = Field(default=1000, ge=100, le=10_000)
    """Per-session message cap (KOSMOS_AGENT_MAILBOX_MAX_MESSAGES).

    Clamped to [100, 10000]. Default: 1000.
    """

    agent_max_workers: int = Field(default=4, ge=1, le=16)
    """Max concurrent workers per coordinator session (KOSMOS_AGENT_MAX_WORKERS).

    Clamped to [1, 16]. Default: 4.
    """

    agent_worker_timeout_seconds: int = Field(default=120, ge=10, le=600)
    """Worker timeout before coordinator cancels (KOSMOS_AGENT_WORKER_TIMEOUT_SECONDS).

    A worker that does not post a result or error message within this timeout
    is cancelled by the coordinator and treated as an error.
    Clamped to [10, 600]. Default: 120.
    """

    @field_validator("agent_mailbox_root", mode="after")
    @classmethod
    def _agent_mailbox_root_must_be_absolute(cls, v: Path) -> Path:
        """Reject relative paths for agent_mailbox_root (FR-032)."""
        if not v.is_absolute():
            raise ValueError(
                f"agent_mailbox_root must be an absolute path, got: {v!r}"
            )
        return v


settings: KosmosSettings = KosmosSettings()
"""Module-level singleton.  Import this directly in production code."""
