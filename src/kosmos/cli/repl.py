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
    - Session persistence via :class:`~kosmos.session.manager.SessionManager`
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
        resume_session_id: Optional session UUID to resume on startup.
        session_manager: Optional pre-built session manager (used in tests).
    """

    def __init__(
        self,
        engine: QueryEngine,
        registry: ToolRegistry,
        console: Console,
        config: CLIConfig,
        renderer: EventRenderer,
        resume_session_id: str | None = None,
        session_manager: object | None = None,
    ) -> None:
        self._engine = engine
        self._registry = registry
        self._console = console
        self._config = config
        self._renderer = renderer
        self._resume_session_id = resume_session_id
        self._session_id = str(uuid.uuid4())
        self._total_input_tokens = 0
        self._total_output_tokens = 0
        self._last_ctrl_c: float = 0.0
        # Lazy-initialised session manager (avoids import at module level for
        # callers that don't need persistence)
        self._session_manager = session_manager

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self) -> None:
        """Start the REPL loop.

        Returns when the user exits normally (``/exit``, ``/quit``, or EOF).
        Calls ``sys.exit(130)`` on double Ctrl+C within 1 second at the
        idle prompt.
        """
        await self._init_session()

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
    # Private session initialisation
    # ------------------------------------------------------------------

    async def _init_session(self) -> None:
        """Create a new session or resume an existing one."""
        from kosmos.session.manager import SessionManager  # noqa: PLC0415

        if self._session_manager is None:
            self._session_manager = SessionManager()

        manager: SessionManager = self._session_manager  # type: ignore[assignment]

        if self._resume_session_id:
            try:
                messages = await manager.resume_session(self._resume_session_id)
                # Replay history into the engine state (guard against mock engines)
                engine_state = getattr(self._engine, "state", None)
                if messages and engine_state is not None:
                    engine_state.messages.extend(messages)
                self._session_id = self._resume_session_id
                self._console.print(f"[dim]세션 재개: {self._resume_session_id}[/dim]")
            except (FileNotFoundError, ValueError) as exc:
                self._console.print(
                    f"[yellow]세션을 재개할 수 없습니다:[/yellow] {escape(str(exc))}\n"
                    "[dim]새 세션을 시작합니다.[/dim]"
                )
                meta = await manager.new_session()
                self._session_id = meta.session_id
        else:
            meta = await manager.new_session()
            self._session_id = meta.session_id

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
            return

        # --- Persist the completed turn ---
        await self._persist_turn(user_message)

    async def _persist_turn(self, user_message: str) -> None:
        """Save the latest user/assistant exchange to the session store."""
        from kosmos.llm.models import ChatMessage  # noqa: PLC0415
        from kosmos.session.manager import SessionManager  # noqa: PLC0415

        manager: SessionManager | None = self._session_manager  # type: ignore[assignment]
        if manager is None or not self._session_id:
            return

        # The engine's message history contains the full conversation.
        # Guard against mock engines that don't expose a .state attribute.
        state = getattr(self._engine, "state", None)
        if state is None:
            return
        messages = state.messages
        user_msg: ChatMessage | None = None
        assistant_msg: ChatMessage | None = None
        tool_calls_list = []

        # Walk from the end to find the latest assistant then user message
        for msg in reversed(messages):
            if assistant_msg is None and msg.role == "assistant":
                assistant_msg = msg
                if msg.tool_calls:
                    tool_calls_list = list(msg.tool_calls)
            elif user_msg is None and msg.role == "user":
                user_msg = msg
                break

        if user_msg is None or assistant_msg is None:
            return

        try:
            await manager.save_turn(
                user_msg=user_msg,
                assistant_msg=assistant_msg,
                tool_calls=tool_calls_list or None,
            )
            # Auto-generate title from the first user message
            await manager.set_title(messages)
        except Exception:  # noqa: BLE001
            import logging  # noqa: PLC0415

            logging.getLogger(__name__).warning("Failed to persist session turn", exc_info=True)

    async def _handle_slash_command(self, cmd: str) -> bool:
        """Route a slash command via the COMMANDS registry.

        Returns ``True`` if the REPL should exit.
        """
        # Normalise: strip leading slash and lower-case; split off arguments
        raw = cmd.lstrip("/").strip()
        parts = raw.split(None, 1)
        name_raw = parts[0].lower() if parts else ""
        args = parts[1].strip() if len(parts) > 1 else ""

        # Resolve name through the COMMANDS registry (check primary name and
        # aliases so that e.g. "quit" routes to the "exit" handler)
        resolved: str | None = None
        if name_raw in COMMANDS:
            resolved = name_raw
        else:
            for cmd_name, cmd_def in COMMANDS.items():
                if name_raw in cmd_def.aliases:
                    resolved = cmd_name
                    break

        if resolved is None:
            self._console.print(
                "[yellow]알 수 없는 명령어:[/yellow] "
                f"{escape(repr(cmd))}. "
                "/help를 입력해 도움말을 확인하세요."
            )
            return False

        return await self._dispatch_command(resolved, args)

    async def _dispatch_command(self, name: str, args: str = "") -> bool:
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
            self._total_input_tokens = 0
            self._total_output_tokens = 0
            self._renderer.reset()
            self._console.print(
                Rule("[dim]새 대화 시작[/dim]", style="dim"),
            )
            # Create a fresh session for the new conversation
            await self._start_new_session()

        elif name == "usage":
            total = self._total_input_tokens + self._total_output_tokens
            self._console.print(
                f"[bold]세션 토큰 사용량[/bold]\n"
                f"  입력: {self._total_input_tokens}\n"
                f"  출력: {self._total_output_tokens}\n"
                f"  합계: {total}"
            )

        elif name == "save":
            await self._cmd_save()

        elif name == "sessions":
            await self._cmd_sessions()

        elif name == "resume":
            await self._cmd_resume(args)

        return False

    async def _start_new_session(self) -> None:
        """Create a new session and display the session ID."""
        from kosmos.session.manager import SessionManager  # noqa: PLC0415

        manager: SessionManager | None = self._session_manager  # type: ignore[assignment]
        if manager is not None:
            try:
                meta = await manager.new_session()
                self._session_id = meta.session_id
            except Exception:  # noqa: BLE001
                import logging  # noqa: PLC0415

                logging.getLogger(__name__).warning("Failed to create new session", exc_info=True)
                self._session_id = str(uuid.uuid4())
        else:
            self._session_id = str(uuid.uuid4())
        self._console.print(f"[dim]새 대화가 시작되었습니다. 세션 ID: {self._session_id}[/dim]")

    async def _cmd_save(self) -> None:
        """Force-save the current session title (no-op if already persisted)."""
        from kosmos.session.manager import SessionManager  # noqa: PLC0415

        manager: SessionManager | None = self._session_manager  # type: ignore[assignment]
        if manager is None:
            self._console.print("[dim]세션 저장 기능이 비활성화되어 있습니다.[/dim]")
            return
        try:
            await manager.set_title(self._engine._state.messages)
            self._console.print(f"[dim]세션이 저장되었습니다. ID: {self._session_id}[/dim]")
        except Exception as exc:  # noqa: BLE001
            self._console.print(f"[yellow]저장 중 오류가 발생했습니다:[/yellow] {escape(str(exc))}")

    async def _cmd_sessions(self) -> None:
        """List recent sessions from the store."""
        from kosmos.session.manager import SessionManager  # noqa: PLC0415
        from kosmos.session.store import list_sessions  # noqa: PLC0415

        manager: SessionManager | None = self._session_manager  # type: ignore[assignment]
        session_dir = manager._session_dir if manager is not None else None
        try:
            sessions = await list_sessions(session_dir=session_dir)
        except Exception as exc:  # noqa: BLE001
            self._console.print(
                f"[yellow]세션 목록을 불러오지 못했습니다:[/yellow] {escape(str(exc))}"
            )
            return

        if not sessions:
            self._console.print("[dim]저장된 세션이 없습니다.[/dim]")
            return

        self._console.print("[bold]최근 세션 목록:[/bold]")
        for meta in sessions[:20]:  # limit display
            marker = " ← 현재" if meta.session_id == self._session_id else ""
            title = meta.title or "(제목 없음)"
            updated = meta.updated_at.strftime("%Y-%m-%d %H:%M")
            self._console.print(
                f"  [cyan]{meta.session_id[:8]}…[/cyan]  "
                f"{escape(title)}  "
                f"[dim]{updated}  메시지 {meta.message_count}개{marker}[/dim]"
            )
        self._console.print("[dim]/resume <session-id> 로 세션을 재개할 수 있습니다.[/dim]")

    async def _cmd_resume(self, session_id: str) -> None:
        """Resume a session by ID within the running REPL."""
        from kosmos.session.manager import SessionManager  # noqa: PLC0415

        if not session_id:
            self._console.print("[yellow]사용법:[/yellow] /resume <session-id>")
            return

        manager: SessionManager | None = self._session_manager  # type: ignore[assignment]
        if manager is None:
            self._console.print("[dim]세션 기능이 비활성화되어 있습니다.[/dim]")
            return

        try:
            messages = await manager.resume_session(session_id)
            # Reset engine and reload history (guard against mock engines)
            self._engine.reset()
            engine_state = getattr(self._engine, "state", None)
            if messages and engine_state is not None:
                engine_state.messages.extend(messages)
            self._session_id = session_id
            self._total_input_tokens = 0
            self._total_output_tokens = 0
            self._renderer.reset()
            self._console.print(
                Rule("[dim]세션 재개[/dim]", style="dim"),
            )
            self._console.print(
                f"[dim]세션 재개됨: {session_id}  (메시지 {len(messages)}개 복원)[/dim]"
            )
        except (FileNotFoundError, ValueError) as exc:
            self._console.print(f"[yellow]세션을 재개할 수 없습니다:[/yellow] {escape(str(exc))}")

    def _show_welcome(self) -> None:
        """Display the welcome banner with session ID."""
        self._console.print(_WELCOME_BANNER)
        self._console.print(f"[dim]세션 ID: {self._session_id}[/dim]")
        self._console.print(
            "[dim]/help 를 입력하면 사용 가능한 명령어를 확인할 수 있습니다.[/dim]\n"
        )
