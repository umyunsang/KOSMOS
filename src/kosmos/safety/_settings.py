# SPDX-License-Identifier: Apache-2.0
"""Safety-pipeline runtime configuration for KOSMOS.

All fields are loaded from ``KOSMOS_SAFETY_*`` environment variables,
except ``openai_moderation_api_key`` which uses its own namespaced variable
``KOSMOS_OPENAI_MODERATION_API_KEY`` (no ``SAFETY_`` infix — deliberate).

Fail-closed per FR-022: enabling moderation without providing an
OpenAI Moderation API key raises ConfigurationError at construction.
"""

from __future__ import annotations

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from kosmos.tools.errors import ConfigurationError


class SafetySettings(BaseSettings):
    """KOSMOS safety-pipeline runtime configuration (KOSMOS_SAFETY_* env vars).

    Fail-closed per FR-022: enabling moderation without providing an
    OpenAI Moderation API key raises ConfigurationError at construction.
    """

    model_config = SettingsConfigDict(
        env_prefix="KOSMOS_SAFETY_",
        env_file=".env",
        extra="ignore",
        frozen=True,
    )

    redact_tool_output: bool = True
    injection_detector_enabled: bool = True
    moderation_enabled: bool = False
    openai_moderation_api_key: SecretStr | None = Field(
        default=None,
        alias="KOSMOS_OPENAI_MODERATION_API_KEY",
    )

    @model_validator(mode="after")
    def _fail_closed_on_missing_moderation_key(self) -> SafetySettings:
        if self.moderation_enabled and self.openai_moderation_api_key is None:
            raise ConfigurationError("KOSMOS_OPENAI_MODERATION_API_KEY")
        return self
