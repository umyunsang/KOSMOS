# SPDX-License-Identifier: Apache-2.0
"""CLI configuration loaded from environment variables with ``KOSMOS_CLI_`` prefix."""

from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CLIConfig(BaseSettings):
    """Runtime configuration for the KOSMOS CLI.

    All fields are configurable via environment variables prefixed with
    ``KOSMOS_CLI_``.  For example, ``KOSMOS_CLI_SHOW_USAGE=false`` disables
    the per-turn usage summary.
    """

    model_config = SettingsConfigDict(env_prefix="KOSMOS_CLI_")

    history_size: int = Field(default=1000, ge=0)
    """Maximum number of REPL history entries to persist."""

    show_usage: bool = True
    """Whether to display token usage after each response."""

    welcome_banner: bool = True
    """Whether to show the welcome banner on startup."""
