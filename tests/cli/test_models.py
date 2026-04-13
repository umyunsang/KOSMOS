# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI models and slash command registry."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.cli.models import COMMANDS, SlashCommand


class TestSlashCommand:
    def test_frozen(self) -> None:
        cmd = SlashCommand(name="test", description="A test command")
        with pytest.raises(ValidationError):
            cmd.name = "other"  # type: ignore[misc]

    def test_default_aliases(self) -> None:
        cmd = SlashCommand(name="foo", description="foo command")
        assert cmd.aliases == ()

    def test_aliases_stored(self) -> None:
        cmd = SlashCommand(name="exit", description="Exit", aliases=("exit", "quit"))
        assert "exit" in cmd.aliases
        assert "quit" in cmd.aliases


class TestCommandsRegistry:
    def test_help_present(self) -> None:
        assert "help" in COMMANDS

    def test_new_present(self) -> None:
        assert "new" in COMMANDS

    def test_exit_present(self) -> None:
        assert "exit" in COMMANDS

    def test_usage_present(self) -> None:
        assert "usage" in COMMANDS

    def test_exit_has_aliases(self) -> None:
        cmd = COMMANDS["exit"]
        assert "exit" in cmd.aliases
        assert "quit" in cmd.aliases

    def test_new_has_alias(self) -> None:
        cmd = COMMANDS["new"]
        assert "new" in cmd.aliases

    def test_all_commands_have_descriptions(self) -> None:
        for name, cmd in COMMANDS.items():
            assert cmd.description, f"Command '{name}' has empty description"
