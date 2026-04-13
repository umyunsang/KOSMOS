# SPDX-License-Identifier: Apache-2.0
"""REPL loop for the KOSMOS CLI — citizen conversation interface."""

from __future__ import annotations

import sys
import time
import uuid
from collections.abc import AsyncGenerator, Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markup import escape
from rich.rule import Rule

from kosmos.cli.config import CLIConfig
from kosmos.cli.models import COMMANDS
from kosmos.cli.renderer import EventRenderer
from kosmos.engine.engine import QueryEngine
from kosmos.engine.events import QueryEvent
from kosmos.tools.registry import ToolRegistry

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


def _build_help_text() -> str:
    """Generate /help output dynamically from the COMMANDS registry."""
    lines = ["[bold]사용 가능한 명령어:[/bold]\n"]
    for cmd in COMMANDS.values():
        aliases = ""
        if cmd.aliases:
            # Show any aliases that differ from the primary name
            extra = [a for a in cmd.aliases if a != cmd.name]
            if extra:
                aliases = " (또는 " + ", ".join(f"/{a}" for a in extra) + ")"
        lines.append(f"  [cyan]/{cmd.name}[/cyan]{aliases}  — {cmd.description}")
    lines.append(
        "\n[dim]질문을 입력하고 Enter를 누르세요. Ctrl+C를 두 번 누르면 강제 종료됩니다.[/dim]"
    )
    return "\n".join(lines)


class _LimitedInMemoryHistory(InMemoryHistory):
    """InMemoryHistory capped at *max_entries* most-recent entries.

    prompt_toolkit's InMemoryHistory grows unbounded.  This subclass overrides
    ``store_string`` (called by the base class's ``append_string``) to keep
    only the ``max_entries`` most-recent entries in ``_loaded_strings``.

    Note: ``_loaded_strings`` is stored newest-first by the base class, so we
    truncate from the end after inserting.
    """

    def __init__(self, max_entries: int) -> None:
        super().__init__()
        self._max_entries = max_entries

    def load_history_strings(self) -> Iterable[str]:
        return []

    def store_string(self, string: str) -> None:
        # Base class already inserted string at index 0 before calling us;
        # nothing extra to do for persisting.  Just enforce the size cap.
        if len(self._loaded_strings) > self._max_entries:
            # Drop the oldest entry (last element — it's stored newest-first)
            del self._loaded_strings[self._max_entries :]


class REPLLoop:
    """Async REPL loop for citizen conversation with the KOSMOS engine.

    Handles:
    - Slash command routing via the ``COMMANDS`` registry
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
        """Start the REPL loop.

        Returns when the user exits normally (``/exit``, ``/quit``, or EOF).
        Calls ``sys.exit(130)`` on double Ctrl+C within 1 second at the
        idle prompt.
        """
        if self._config.welcome_banner:
            self._show_welcome()

        prompt_session: PromptSession[str] = PromptSession(
            history=_LimitedInMemoryHistory(self._config.history_size),
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
                # Track usage totals for /usage command (always, regardless of
                # show_usage flag — the renderer controls per-turn display)
                if event.type == "usage_update" and event.usage is not None:
                    self._total_input_tokens += event.usage.input_tokens
                    self._total_output_tokens += event.usage.output_tokens
                self._renderer.render(event)
        except KeyboardInterrupt:
            # Ctrl+C during streaming: cancel the generator.
            # Update _last_ctrl_c so a second Ctrl+C at the next idle
            # prompt within 1 second triggers the forced-exit path.
            now = time.monotonic()
            if now - self._last_ctrl_c < 1.0:
                await gen.aclose()
                self._console.print("\n[dim]종료합니다.[/dim]")
                sys.exit(130)
            self._last_ctrl_c = now
            await gen.aclose()
            self._console.print("\n[dim]\\[cancelled][/dim]")
            self._renderer.reset()

    async def _handle_slash_command(self, cmd: str) -> bool:
        """Route a slash command via the COMMANDS registry.

        Returns ``True`` if the REPL should exit.
        """
        # Normalise: strip leading slash and lower-case
        name = cmd.lstrip("/").lower()

        # Resolve name through the COMMANDS registry (check primary name and
        # aliases so that e.g. "quit" routes to the "exit" handler)
        resolved: str | None = None
        if name in COMMANDS:
            resolved = name
        else:
            for cmd_name, cmd_def in COMMANDS.items():
                if name in cmd_def.aliases:
                    resolved = cmd_name
                    break

        if resolved is None:
            self._console.print(
                "[yellow]알 수 없는 명령어:[/yellow] "
                f"{escape(repr(cmd))}. "
                "/help를 입력해 도움말을 확인하세요."
            )
            return False

        return await self._dispatch_command(resolved)

    async def _dispatch_command(self, name: str) -> bool:
        """Execute the handler for a resolved command name.

        Returns ``True`` if the REPL should exit.
        """
        if name == "exit":
            self._console.print("[dim]종료합니다.[/dim]")
            return True

        if name == "help":
            self._console.print(_build_help_text())
        elif name == "new":
            self._engine.reset()
            self._session_id = str(uuid.uuid4())
            # Reset display-level token counters for the new conversation.
            # Note: the engine's UsageTracker budget is preserved across /new
            # resets to enforce a per-session spending cap.  These counters
            # only track display totals shown by /usage.
            self._total_input_tokens = 0
            self._total_output_tokens = 0
            self._renderer.reset()
            self._console.print(
                Rule("[dim]새 대화 시작[/dim]", style="dim"),
            )
            self._console.print(f"[dim]새 대화가 시작되었습니다. 세션 ID: {self._session_id}[/dim]")
        elif name == "usage":
            total = self._total_input_tokens + self._total_output_tokens
            self._console.print(
                f"[bold]세션 토큰 사용량[/bold]\n"
                f"  입력: {self._total_input_tokens}\n"
                f"  출력: {self._total_output_tokens}\n"
                f"  합계: {total}"
            )

        return False

    def _show_welcome(self) -> None:
        """Display the welcome banner with session ID."""
        self._console.print(_WELCOME_BANNER)
        self._console.print(f"[dim]세션 ID: {self._session_id}[/dim]")
        self._console.print(
            "[dim]/help 를 입력하면 사용 가능한 명령어를 확인할 수 있습니다.[/dim]\n"
        )
