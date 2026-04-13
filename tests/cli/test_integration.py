# SPDX-License-Identifier: Apache-2.0
"""Integration tests for the CLI with a mock LLM."""

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
from kosmos.tools.models import ToolResult
from kosmos.tools.registry import ToolRegistry


def _make_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=True, width=120)


class _MockEngine:
    def __init__(self, turn_responses: list[list[QueryEvent]]) -> None:
        self._responses = turn_responses
        self._call_count = 0

    async def run(self, user_message: str) -> AsyncIterator[QueryEvent]:  # noqa: ARG002
        events = self._responses[min(self._call_count, len(self._responses) - 1)]
        self._call_count += 1
        for event in events:
            yield event


def _make_repl_with_engine(engine: Any) -> tuple[REPLLoop, Console]:
    console = _make_console()
    registry = MagicMock(spec=ToolRegistry)
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


class TestEndToEndTurn:
    async def test_text_response_displayed(self) -> None:
        """Full turn: user input → text_delta → usage_update → stop."""
        events = [
            QueryEvent(type="text_delta", content="안녕하세요! 무엇을 도와드릴까요?"),
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=20, output_tokens=10)),
            QueryEvent(type="stop", stop_reason=StopReason.task_complete),
        ]
        engine = _MockEngine([events])
        repl, console = _make_repl_with_engine(engine)

        inputs = ["안녕하세요", "/exit"]
        idx = 0

        async def mock_prompt(prompt_str: str) -> str:
            nonlocal idx
            val = inputs[idx]
            idx += 1
            return val

        mock_session = MagicMock()
        mock_session.prompt_async = mock_prompt
        with patch("kosmos.cli.repl.PromptSession", return_value=mock_session):
            await repl.run()

        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "안녕하세요" in output
        assert "작업이 완료되었습니다" in output

    async def test_usage_tracked_across_turns(self) -> None:
        """Token usage accumulates across multiple turns."""
        events_turn1 = [
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=10, output_tokens=5)),
            QueryEvent(type="stop", stop_reason=StopReason.end_turn),
        ]
        events_turn2 = [
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=15, output_tokens=8)),
            QueryEvent(type="stop", stop_reason=StopReason.end_turn),
        ]
        engine = _MockEngine([events_turn1, events_turn2])
        repl, console = _make_repl_with_engine(engine)

        inputs = ["질문 1", "질문 2", "/exit"]
        idx = 0

        async def mock_prompt(prompt_str: str) -> str:
            nonlocal idx
            val = inputs[idx]
            idx += 1
            return val

        mock_session = MagicMock()
        mock_session.prompt_async = mock_prompt
        with patch("kosmos.cli.repl.PromptSession", return_value=mock_session):
            await repl.run()

        assert repl._total_input_tokens == 25
        assert repl._total_output_tokens == 13

    async def test_tool_use_and_result_rendered(self) -> None:
        """Turn with tool_use + tool_result events displays tool feedback."""
        events = [
            QueryEvent(type="tool_use", tool_name="test_tool", tool_call_id="call-1"),
            QueryEvent(
                type="tool_result",
                tool_result=ToolResult(
                    tool_id="test_tool",
                    success=True,
                    data={"result": "data"},
                ),
            ),
            QueryEvent(type="text_delta", content="결과를 찾았습니다."),
            QueryEvent(type="stop", stop_reason=StopReason.task_complete),
        ]
        engine = _MockEngine([events])
        repl, console = _make_repl_with_engine(engine)

        inputs = ["도로 정보 조회", "/exit"]
        idx = 0

        async def mock_prompt(prompt_str: str) -> str:
            nonlocal idx
            val = inputs[idx]
            idx += 1
            return val

        mock_session = MagicMock()
        mock_session.prompt_async = mock_prompt
        with patch("kosmos.cli.repl.PromptSession", return_value=mock_session):
            await repl.run()

        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "성공" in output
        assert "결과를 찾았습니다" in output

    async def test_welcome_banner_with_session_id(self) -> None:
        """Welcome banner is shown when welcome_banner=True."""
        console = _make_console()
        registry = MagicMock(spec=ToolRegistry)
        config = CLIConfig(welcome_banner=True)
        renderer = EventRenderer(console, registry=registry)
        engine = _MockEngine([[]])
        repl = REPLLoop(
            engine=engine,
            registry=registry,
            console=console,
            config=config,
            renderer=renderer,
        )

        inputs = ["/exit"]
        idx = 0

        async def mock_prompt(prompt_str: str) -> str:
            nonlocal idx
            val = inputs[idx]
            idx += 1
            return val

        mock_session = MagicMock()
        mock_session.prompt_async = mock_prompt
        with patch("kosmos.cli.repl.PromptSession", return_value=mock_session):
            await repl.run()

        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "KOSMOS" in output
        assert repl._session_id in output
