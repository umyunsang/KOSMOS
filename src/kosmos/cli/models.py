# SPDX-License-Identifier: Apache-2.0
"""Data models and constants for the KOSMOS CLI slash-command system."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class SlashCommand(BaseModel):
    """A CLI slash command definition.

    Attributes:
        name: Primary command name (e.g. ``"help"``).
        description: One-line description shown in ``/help`` output.
        aliases: Additional names that trigger this command.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    aliases: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Registry of available slash commands
# ---------------------------------------------------------------------------

COMMANDS: dict[str, SlashCommand] = {
    "help": SlashCommand(name="help", description="Show available commands"),
    "new": SlashCommand(name="new", description="Start a new conversation", aliases=("new",)),
    "exit": SlashCommand(
        name="exit",
        description="Exit KOSMOS",
        aliases=("exit", "quit"),
    ),
    "usage": SlashCommand(name="usage", description="Show token usage for current session"),
}
