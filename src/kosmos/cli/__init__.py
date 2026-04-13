# SPDX-License-Identifier: Apache-2.0
"""KOSMOS CLI package — Python rapid-prototype CLI for the citizen conversation loop."""

from __future__ import annotations

from kosmos.cli.app import main
from kosmos.cli.config import CLIConfig
from kosmos.cli.models import COMMANDS, SlashCommand
from kosmos.cli.permissions import ConsentPromptHandler
from kosmos.cli.renderer import EventRenderer
from kosmos.cli.repl import REPLLoop

__all__ = [
    "main",
    "CLIConfig",
    "COMMANDS",
    "SlashCommand",
    "ConsentPromptHandler",
    "EventRenderer",
    "REPLLoop",
]
