# SPDX-License-Identifier: Apache-2.0
"""EventRenderer — converts QueryEvent stream into Rich-formatted terminal output."""

from __future__ import annotations

import logging

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.status import Status

from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.models import TokenUsage
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Stop reason → citizen-facing Korean message
# ---------------------------------------------------------------------------

_STOP_REASON_MESSAGES: dict[StopReason, str] = {
    StopReason.task_complete: "작업이 완료되었습니다.",
    StopReason.end_turn: "",  # no extra message; just show the response
    StopReason.needs_citizen_input: "추가 정보가 필요합니다.",
    StopReason.needs_authentication: "인증이 필요합니다.",
    StopReason.api_budget_exceeded: "API 사용량 한도에 도달했습니다.",
    StopReason.max_iterations_reached: "최대 처리 횟수에 도달했습니다.",
    StopReason.error_unrecoverable: "처리 중 오류가 발생했습니다.",
    StopReason.cancelled: "요청이 취소되었습니다.",
}


class EventRenderer:
    """Render a stream of ``QueryEvent`` objects to a Rich ``Console``.

    The renderer maintains internal state across events within a single turn:
    - ``_text_buffer`` accumulates all ``text_delta`` content (for internal
      tracking only; text is printed incrementally as it arrives).
    - ``_usage`` accumulates the latest token usage snapshot.
    - ``_active_status`` holds the currently displayed spinner (if any).

    After each turn (``stop`` event), the renderer resets its state so it is
    ready for the next turn.

    Args:
        console: Rich console to write output to.
        registry: Optional tool registry for resolving Korean tool names.
        show_usage: Whether to display per-turn token usage after each
            response.  Totals are always tracked internally regardless of
            this flag (so that the ``/usage`` command can report them).
    """

    def __init__(
        self,
        console: Console,
        registry: ToolRegistry | None = None,
        show_usage: bool = True,
    ) -> None:
        self._console = console
        self._registry = registry
        self._show_usage = show_usage
        self._text_buffer: str = ""
        self._usage: TokenUsage | None = None
        self._active_status: Status | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def render(self, event: QueryEvent) -> None:
        """Dispatch a single ``QueryEvent`` to the appropriate render method."""
        if event.type == "text_delta":
            self._render_text_delta(event)
        elif event.type == "tool_use":
            self._render_tool_use(event)
        elif event.type == "tool_result":
            self._render_tool_result(event)
        elif event.type == "usage_update":
            self._render_usage_update(event)
        elif event.type == "stop":
            self._render_stop(event)

    def reset(self) -> None:
        """Reset per-turn state.  Called automatically by ``_render_stop``."""
        self._text_buffer = ""
        self._usage = None
        self._stop_active_status()

    # ------------------------------------------------------------------
    # Private render methods
    # ------------------------------------------------------------------

    def _render_text_delta(self, event: QueryEvent) -> None:
        """Append incremental text to the internal buffer and print it."""
        chunk = event.content or ""
        self._text_buffer += chunk
        self._console.print(chunk, end="", highlight=False, markup=False)

    def _render_tool_use(self, event: QueryEvent) -> None:
        """Show a spinner with the tool's Korean name while it executes."""
        # Stop any previously active status first
        self._stop_active_status()

        # Resolve Korean name via registry
        tool_id = event.tool_name or ""
        korean_name = tool_id
        if self._registry is not None:
            try:
                tool = self._registry.lookup(tool_id)
                korean_name = tool.name_ko
            except Exception:  # noqa: BLE001
                logger.debug("Could not resolve Korean name for tool %r", tool_id)

        label = f"[bold cyan]{escape(str(korean_name))}[/bold cyan] 조회 중..."
        status = Status(label, console=self._console)
        status.start()
        self._active_status = status

    def _render_tool_result(self, event: QueryEvent) -> None:
        """Replace the spinner with a panel summarising the tool result."""
        self._stop_active_status()

        result = event.tool_result
        if result is None:
            return

        if result.success:
            panel = Panel(
                f"[green]성공[/green]  tool_id={escape(repr(result.tool_id))}",
                title="[green]도구 결과[/green]",
                border_style="green",
            )
        else:
            panel = Panel(
                f"[red]오류[/red]  {escape(str(result.error or ''))}\n"
                f"error_type={escape(repr(result.error_type))}  "
                f"tool_id={escape(repr(result.tool_id))}",
                title="[red]도구 오류[/red]",
                border_style="red",
            )
        self._console.print(panel)

    def _render_usage_update(self, event: QueryEvent) -> None:
        """Buffer the latest token usage snapshot."""
        if event.usage is not None:
            self._usage = event.usage

    def _render_stop(self, event: QueryEvent) -> None:
        """Finalise a turn: print stop reason and (optionally) usage summary.

        Text was already printed incrementally via ``_render_text_delta``; we
        do NOT re-render the buffer here to avoid duplicating assistant text in
        the terminal.  The buffer is cleared as part of :meth:`reset`.
        """
        self._stop_active_status()

        # Print a trailing newline after the streamed text block (if any)
        if self._text_buffer:
            self._console.print()  # newline after streaming deltas

        # Show stop reason message (Korean)
        reason = event.stop_reason
        if reason is not None:
            msg = _STOP_REASON_MESSAGES.get(reason, "")
            if msg:
                self._console.print(f"[dim]{msg}[/dim]")

        # Show per-turn usage summary only when the flag is enabled
        if self._show_usage and self._usage is not None:
            self._console.print(
                f"[dim]토큰 사용: 입력 {self._usage.input_tokens} "
                f"/ 출력 {self._usage.output_tokens} "
                f"/ 합계 {self._usage.total_tokens}[/dim]"
            )

        # Reset state for next turn
        self.reset()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _stop_active_status(self) -> None:
        """Stop the active spinner if one is running."""
        if self._active_status is not None:
            self._active_status.stop()
            self._active_status = None
