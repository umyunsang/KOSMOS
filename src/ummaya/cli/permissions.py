# SPDX-License-Identifier: Apache-2.0
"""CLI consent prompt handler for tool-execution permission flow."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.markup import escape
from rich.prompt import Confirm

logger = logging.getLogger(__name__)


class ConsentPromptHandler:
    """Interactively prompt the citizen for tool-execution consent.

    Uses ``rich.prompt.Confirm`` for Y/n confirmation so that the prompt
    integrates naturally with the rest of the Rich output.

    Args:
        console: Rich console to write prompts and messages to.
    """

    def __init__(self, console: Console) -> None:
        self._console = console

    def prompt(self, tool_name: str, provider: str, description: str) -> bool:
        """Display a Y/n consent prompt and return the user's choice.

        Args:
            tool_name: Korean display name of the tool.
            provider: Ministry or agency that owns the API.
            description: Brief description of what the tool does.

        Returns:
            ``True`` if the user consented, ``False`` otherwise.
        """
        self._console.print(
            f"\n[bold yellow]도구 실행 요청[/bold yellow]\n"
            f"  도구: [cyan]{escape(tool_name)}[/cyan]\n"
            f"  제공: [cyan]{escape(provider)}[/cyan]\n"
            f"  설명: {escape(description)}"
        )
        try:
            return Confirm.ask("실행을 허용하시겠습니까?", console=self._console, default=False)
        except (EOFError, KeyboardInterrupt):
            logger.debug("ConsentPromptHandler: prompt interrupted")
            return False

    def display_denial(self, tool_name: str, reason: str) -> None:
        """Show a denial message without offering an override option.

        Args:
            tool_name: Korean display name of the tool that was denied.
            reason: Human-readable reason for the denial.
        """
        self._console.print(
            f"\n[red]도구 실행이 거부되었습니다.[/red]\n"
            f"  도구: [cyan]{escape(tool_name)}[/cyan]\n"
            f"  사유: {escape(reason)}"
        )
