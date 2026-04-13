# SPDX-License-Identifier: Apache-2.0
"""Tests for REPLLoop."""

from __future__ import annotations

import io
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import MagicMock, patch

from rich.console import Console

from kosmos.cli.config import CLIConfig
from kosmos.cli.renderer import EventRenderer
from kosmos.cli.repl import REPLLoop
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.models import TokenUsage
from kosmos.tools.registry import ToolRegistry


def _make_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=True, width=120)


def _make_repl(
    engine: Any,
    registry: Any | None = None,
    config: CLIConfig | None = None,
) -> tuple[REPLLoop, Console]:
    console = _make_console()
    if registry is None:
        registry = MagicMock(spec=ToolRegistry)
    if config is None:
        config = CLIConfig(welcome_banner=False, show_usage=True)
    renderer = EventRenderer(console, registry=registry)
    repl = REPLLoop(
        engine=engine,
        registry=registry,
        console=console,
        config=config,
        renderer=renderer,
    )
    return repl, console


class _MockEngine:
    """Minimal async mock engine."""

    def __init__(self, events: list[QueryEvent]) -> None:
        self._events = events

    async def run(self, user_message: str) -> AsyncIterator[QueryEvent]:  # noqa: ARG002
        for event in self._events:
            yield event


class TestSlashCommands:
    async def test_exit_command_returns_true(self) -> None:
        engine = _MockEngine([])
        repl, _ = _make_repl(engine)
        result = await repl._handle_slash_command("/exit")
        assert result is True

    async def test_quit_command_returns_true(self) -> None:
        engine = _MockEngine([])
        repl, _ = _make_repl(engine)
        result = await repl._handle_slash_command("/quit")
        assert result is True

    async def test_help_command_returns_false(self) -> None:
        engine = _MockEngine([])
        repl, console = _make_repl(engine)
        result = await repl._handle_slash_command("/help")
        assert result is False
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "help" in output

    async def test_new_command_returns_false(self) -> None:
        engine = _MockEngine([])
        repl, console = _make_repl(engine)
        result = await repl._handle_slash_command("/new")
        assert result is False
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "새 대화" in output

    async def test_usage_command_shows_tokens(self) -> None:
        engine = _MockEngine([])
        repl, console = _make_repl(engine)
        repl._total_input_tokens = 100
        repl._total_output_tokens = 50
        result = await repl._handle_slash_command("/usage")
        assert result is False
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "100" in output
        assert "50" in output

    async def test_unknown_command_returns_false(self) -> None:
        engine = _MockEngine([])
        repl, console = _make_repl(engine)
        result = await repl._handle_slash_command("/unknown")
        assert result is False
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "알 수 없는" in output

    async def test_alias_exit_without_slash(self) -> None:
        engine = _MockEngine([])
        repl, _ = _make_repl(engine)
        result = await repl._handle_slash_command("exit")
        assert result is True

    async def test_alias_quit_without_slash(self) -> None:
        engine = _MockEngine([])
        repl, _ = _make_repl(engine)
        result = await repl._handle_slash_command("quit")
        assert result is True


class TestRunTurn:
    async def test_run_turn_renders_events(self) -> None:
        events = [
            QueryEvent(type="text_delta", content="응답"),
            QueryEvent(type="stop", stop_reason=StopReason.task_complete),
        ]
        engine = _MockEngine(events)
        repl, console = _make_repl(engine)
        await repl._run_turn("안녕하세요")
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "응답" in output

    async def test_run_turn_tracks_usage(self) -> None:
        events = [
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=10, output_tokens=5)),
            QueryEvent(type="stop", stop_reason=StopReason.end_turn),
        ]
        engine = _MockEngine(events)
        repl, _ = _make_repl(engine)
        await repl._run_turn("질문")
        assert repl._total_input_tokens == 10
        assert repl._total_output_tokens == 5

    async def test_run_turn_accumulates_usage(self) -> None:
        events = [
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=10, output_tokens=5)),
            QueryEvent(type="stop", stop_reason=StopReason.end_turn),
        ]
        engine = _MockEngine(events)
        repl, _ = _make_repl(engine)
        await repl._run_turn("질문1")
        await repl._run_turn("질문2")
        assert repl._total_input_tokens == 20
        assert repl._total_output_tokens == 10


class TestWelcomeBanner:
    def test_welcome_banner_shows_session_id(self) -> None:
        engine = _MockEngine([])
        console = _make_console()
        registry = MagicMock(spec=ToolRegistry)
        config = CLIConfig(welcome_banner=True)
        renderer = EventRenderer(console, registry=registry)
        repl = REPLLoop(
            engine=engine,
            registry=registry,
            console=console,
            config=config,
            renderer=renderer,
        )
        repl._show_welcome()
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert repl._session_id in output


class TestREPLRun:
    async def test_exit_command_stops_loop(self) -> None:
        engine = _MockEngine([])
        repl, console = _make_repl(engine)

        # Simulate: user types "/exit"
        call_count = 0

        async def mock_prompt_async(prompt_str: str) -> str:
            nonlocal call_count
            call_count += 1
            return "/exit"

        with patch.object(type(repl._engine), "__init__", return_value=None):
            mock_session = MagicMock()
            mock_session.prompt_async = mock_prompt_async
            with patch("kosmos.cli.repl.PromptSession", return_value=mock_session):
                await repl.run()

        assert call_count == 1

    async def test_empty_input_skipped(self) -> None:
        engine = _MockEngine([])
        repl, console = _make_repl(engine)
        inputs = ["   ", "", "/exit"]
        idx = 0

        async def mock_prompt_async(prompt_str: str) -> str:
            nonlocal idx
            val = inputs[idx]
            idx += 1
            return val

        mock_session = MagicMock()
        mock_session.prompt_async = mock_prompt_async
        with patch("kosmos.cli.repl.PromptSession", return_value=mock_session):
            await repl.run()

        # Should have called prompt 3 times (2 empty + 1 exit)
        assert idx == 3
