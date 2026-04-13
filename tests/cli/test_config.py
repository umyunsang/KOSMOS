# SPDX-License-Identifier: Apache-2.0
"""Tests for CLIConfig."""

from __future__ import annotations

import pytest

from kosmos.cli.config import CLIConfig


class TestCLIConfigDefaults:
    def test_default_history_size(self) -> None:
        cfg = CLIConfig()
        assert cfg.history_size == 1000

    def test_default_show_usage(self) -> None:
        cfg = CLIConfig()
        assert cfg.show_usage is True

    def test_default_welcome_banner(self) -> None:
        cfg = CLIConfig()
        assert cfg.welcome_banner is True


class TestCLIConfigEnvOverride:
    def test_history_size_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_CLI_HISTORY_SIZE", "500")
        cfg = CLIConfig()
        assert cfg.history_size == 500

    def test_show_usage_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_CLI_SHOW_USAGE", "false")
        cfg = CLIConfig()
        assert cfg.show_usage is False

    def test_welcome_banner_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_CLI_WELCOME_BANNER", "false")
        cfg = CLIConfig()
        assert cfg.welcome_banner is False
