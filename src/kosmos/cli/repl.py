# SPDX-License-Identifier: Apache-2.0
"""REPL loop for the KOSMOS CLI — citizen conversation interface."""

from __future__ import annotations

import logging
import sys
import time
import uuid
from collections.abc import AsyncGenerator

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.rule import Rule

from kosmos.cli.config import CLIConfig
from kosmos.cli.renderer import EventRenderer
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

_WELCOME_BANNER = """[bold cyan]
 ██╗  ██╗ ██████╗ ███████╗███╗   ███╗ ██████╗ ███████╗
 ██║ ██╔╝██╔═══██╗██╔════╝████╗ ████║██╔═══██╗██╔════╝
 █████╔╝ ██║   ██║███████╗██╔████╔██║██║   ██║███████╗
 ██╔═██╗ ██║   ██║╚════██║██║╚██╔╝██║██║   ██║╚════██║
 ██║  ██╗╚██████╔╝███████║██║ ╚═╝ ██║╚██████╔╝███████║
 ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝     ╚═╝ ╚═════╝ ╚══════╝

                        KOSMOS
[/bold cyan]
[dim]대한민국 공공 API 대화형 플랫폼 · Korean Public API Conversational Platform[/dim]"""

_HELP_TEXT = """[bold]사용 가능한 명령어:[/bold]

  [cyan]/help[/cyan]   — 도움말 표시
  [cyan]/new[/cyan]    — 새 대화 시작
  [cyan]/usage[/cyan]  — 세션 토큰 사용량 표시
  [cyan]/exit[/cyan]   — 종료 (또는 /quit)

[dim]질문을 입력하고 Enter를 누르세요. Ctrl+C를 두 번 누르면 강제 종료됩니다.[/dim]"""


class REPLLoop:
    """Async REPL loop for citizen conversation with the KOSMOS engine.

    Handles:
    - Slash command routing (``/help``, ``/new``, ``/exit``, ``/usage``)
    - Empty/whitespace input skipping
    - Streaming event rendering via ``EventRenderer``
    - Interrupt handling:
      - Single Ctrl+C during streaming → cancel and append ``[cancelled]``
      - Double Ctrl+C within 1 second → ``sys.exit(130)``
      - Ctrl+C at idle prompt → clear input and re-prompt

    Args:
        engine: Configured ``QueryEngine`` for the session.
        registry: Tool registry for Korean name resolution.
        console: Rich console for all output.
        config: CLI runtime configuration.
        renderer: Pre-built ``EventRenderer`` bound to ``console``.
    """

    def __init__(
        self,
        engine: QueryEngine,
        registry: ToolRegistry,
        console: Console,
        config: CLIConfig,
        renderer: EventRenderer,
    ) -> None:
        self._engine = engine
        self._registry = registry
        self._console = console
        self._config = config
        self._renderer = renderer
        self._session_id = str(uuid.uuid4())
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._last_ctrl_c: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the REPL loop.  Returns when the user exits."""
        if self._config.welcome_banner:
            self._show_welcome()

        prompt_session: PromptSession[str] = PromptSession(
            history=InMemoryHistory(),
        )

        while True:
            try:
                user_input = await prompt_session.prompt_async("KOSMOS › ")
            except KeyboardInterrupt:
                now = time.monotonic()
                if now - self._last_ctrl_c < 1.0:
                    self._console.print("\n[dim]종료합니다.[/dim]")
                    sys.exit(130)
                self._last_ctrl_c = now
                self._console.print("[dim]다시 Ctrl+C를 누르면 강제 종료됩니다.[/dim]")
                continue
            except EOFError:
                self._console.print("\n[dim]종료합니다.[/dim]")
                break

            stripped = user_input.strip()
            if not stripped:
                continue

            # --- Slash command routing ---
            if stripped.startswith("/") or stripped in ("exit", "quit", "new"):
                should_exit = await self._handle_slash_command(stripped)
                if should_exit:
                    break
                continue

            # --- Regular citizen message ---
            await self._run_turn(stripped)

    # ------------------------------------------------------------------
    # Private methods
    # ------------------------------------------------------------------

    async def _run_turn(self, user_message: str) -> None:
        """Execute one engine turn, streaming events to the renderer."""
        # engine.run() is typed as AsyncIterator but the actual object is an
        # async generator, which supports aclose().  We cast to AsyncGenerator
        # so mypy accepts the aclose() call.
        from typing import cast  # noqa: PLC0415

        gen: AsyncGenerator[QueryEvent, None] = cast(
            AsyncGenerator[QueryEvent, None], self._engine.run(user_message)
        )
        try:
            async for event in gen:
                # Track usage for /usage command
                if event.type == "usage_update" and event.usage is not None:
                    self._total_input_tokens += event.usage.input_tokens
                    self._total_output_tokens += event.usage.output_tokens
                self._renderer.render(event)
        except KeyboardInterrupt:
            # Single Ctrl+C during streaming: cancel the generator
            await gen.aclose()
            self._console.print("\n[dim][cancelled][/dim]")
            self._renderer.reset()

    async def _handle_slash_command(self, cmd: str) -> bool:
        """Route a slash command.  Returns ``True`` if the REPL should exit."""
        # Normalise: strip leading slash
        name = cmd.lstrip("/").lower()

        # Check aliases for exit
        if name in ("exit", "quit"):
            self._console.print("[dim]종료합니다.[/dim]")
            return True

        if name == "help":
            self._console.print(_HELP_TEXT)
        elif name == "new":
            self._console.print(
                Rule("[dim]새 대화 시작[/dim]", style="dim"),
            )
            self._console.print("[dim]새 대화가 시작되었습니다.[/dim]")
        elif name == "usage":
            total = self._total_input_tokens + self._total_output_tokens
            self._console.print(
                f"[bold]세션 토큰 사용량[/bold]\n"
                f"  입력: {self._total_input_tokens}\n"
                f"  출력: {self._total_output_tokens}\n"
                f"  합계: {total}"
            )
        else:
            self._console.print(
                f"[yellow]알 수 없는 명령어:[/yellow] {cmd!r}. /help를 입력해 도움말을 확인하세요."
            )

        return False

    def _show_welcome(self) -> None:
        """Display the welcome banner with session ID."""
        self._console.print(_WELCOME_BANNER)
        self._console.print(f"[dim]세션 ID: {self._session_id}[/dim]")
        self._console.print(
            "[dim]/help 를 입력하면 사용 가능한 명령어를 확인할 수 있습니다.[/dim]\n"
        )
