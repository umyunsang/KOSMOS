# SPDX-License-Identifier: Apache-2.0
"""KOSAX CLI package — Python rapid-prototype CLI for the citizen conversation loop."""

from __future__ import annotations

from kosax.cli.app import main
from kosax.cli.config import CLIConfig
from kosax.cli.models import COMMANDS, SlashCommand
from kosax.cli.permissions import ConsentPromptHandler
from kosax.cli.renderer import EventRenderer
from kosax.cli.repl import REPLLoop

__all__ = [
    "main",
    "CLIConfig",
    "COMMANDS",
    "SlashCommand",
    "ConsentPromptHandler",
    "EventRenderer",
    "REPLLoop",
]
