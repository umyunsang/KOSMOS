# SPDX-License-Identifier: Apache-2.0
"""Tests for kosmos.cli.themes — theme loading and default fallback."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.cli.themes import Theme, get_theme, load_theme


class TestThemeModel:
    def test_default_theme_has_all_fields(self) -> None:
        theme = get_theme("default")
        assert theme.user_input
        assert theme.assistant_output
        assert theme.tool_call
        assert theme.tool_result_ok
        assert theme.tool_result_err
        assert theme.error
        assert theme.info
        assert theme.system
        assert theme.rule

    def test_theme_is_immutable(self) -> None:
        theme = get_theme("default")
        with pytest.raises(ValidationError):
            theme.user_input = "red"  # type: ignore[misc]


class TestGetTheme:
    def test_default_theme(self) -> None:
        theme = get_theme("default")
        assert isinstance(theme, Theme)

    def test_dark_theme(self) -> None:
        theme = get_theme("dark")
        assert isinstance(theme, Theme)

    def test_light_theme(self) -> None:
        theme = get_theme("light")
        assert isinstance(theme, Theme)

    def test_unknown_theme_raises(self) -> None:
        with pytest.raises(KeyError, match="Unknown theme"):
            get_theme("neon")


class TestLoadTheme:
    def test_returns_default_when_no_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KOSMOS_THEME", raising=False)
        monkeypatch.delenv("KOSMOS_CLI_THEME", raising=False)
        theme = load_theme()
        assert theme == get_theme("default")

    def test_respects_kosmos_theme_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_THEME", "dark")
        monkeypatch.delenv("KOSMOS_CLI_THEME", raising=False)
        theme = load_theme()
        assert theme == get_theme("dark")

    def test_respects_kosmos_cli_theme_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KOSMOS_THEME", raising=False)
        monkeypatch.setenv("KOSMOS_CLI_THEME", "light")
        theme = load_theme()
        assert theme == get_theme("light")

    def test_kosmos_theme_takes_precedence(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_THEME", "dark")
        monkeypatch.setenv("KOSMOS_CLI_THEME", "light")
        theme = load_theme()
        assert theme == get_theme("dark")

    def test_unknown_env_falls_back_to_default_with_warning(
        self, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
    ) -> None:
        import logging  # noqa: PLC0415

        monkeypatch.setenv("KOSMOS_THEME", "ultraviolet")
        monkeypatch.delenv("KOSMOS_CLI_THEME", raising=False)
        with caplog.at_level(logging.WARNING):
            theme = load_theme()
        assert theme == get_theme("default")
        assert any("ultraviolet" in rec.message for rec in caplog.records)

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_THEME", "DARK")
        monkeypatch.delenv("KOSMOS_CLI_THEME", raising=False)
        theme = load_theme()
        assert theme == get_theme("dark")

    def test_whitespace_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("KOSMOS_THEME", "  light  ")
        monkeypatch.delenv("KOSMOS_CLI_THEME", raising=False)
        theme = load_theme()
        assert theme == get_theme("light")
