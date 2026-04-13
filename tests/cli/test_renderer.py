# SPDX-License-Identifier: Apache-2.0
"""Tests for EventRenderer."""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import MagicMock

from rich.console import Console

from kosmos.cli.renderer import EventRenderer
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.models import TokenUsage
from kosmos.tools.models import ToolResult


def _make_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=True, width=120)


class TestTextDeltaRendering:
    def test_buffer_accumulates(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(QueryEvent(type="text_delta", content="Hello"))
        renderer.render(QueryEvent(type="text_delta", content=" World"))
        assert renderer._text_buffer == "Hello World"

    def test_output_contains_text(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(QueryEvent(type="text_delta", content="테스트"))
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "테스트" in output


class TestUsageUpdateRendering:
    def test_usage_buffered(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        usage = TokenUsage(input_tokens=10, output_tokens=5)
        renderer.render(QueryEvent(type="usage_update", usage=usage))
        assert renderer._usage == usage

    def test_usage_overwritten_on_multiple_updates(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=10, output_tokens=5))
        )
        renderer.render(
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=20, output_tokens=10))
        )
        assert renderer._usage is not None
        assert renderer._usage.input_tokens == 20


class TestStopRendering:
    def test_stop_resets_buffer(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(QueryEvent(type="text_delta", content="some text"))
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.task_complete))
        assert renderer._text_buffer == ""

    def test_stop_shows_korean_message_task_complete(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.task_complete))
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "작업이 완료되었습니다" in output

    def test_stop_shows_korean_message_error(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.error_unrecoverable))
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "처리 중 오류가 발생했습니다" in output

    def test_stop_end_turn_no_extra_message(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(QueryEvent(type="text_delta", content="hi"))
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.end_turn))
        output = console.file.getvalue()  # type: ignore[union-attr]
        # "end_turn" stop reason should not produce a Korean stop message
        assert "end_turn" not in output

    def test_stop_shows_usage_summary(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer.render(
            QueryEvent(type="usage_update", usage=TokenUsage(input_tokens=10, output_tokens=5))
        )
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.task_complete))
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "10" in output
        assert "5" in output


class TestToolUseRendering:
    def test_tool_use_with_registry(self, mock_tool_registry: Any) -> None:
        console = _make_console()
        renderer = EventRenderer(console, registry=mock_tool_registry)
        renderer.render(QueryEvent(type="tool_use", tool_name="test_tool", tool_call_id="call-123"))
        # Korean name should have been looked up
        mock_tool_registry.lookup.assert_called_once_with("test_tool")
        # Stop the spinner to avoid console state issues
        renderer._stop_active_status()

    def test_tool_use_fallback_on_registry_error(self) -> None:
        console = _make_console()
        bad_registry = MagicMock()
        bad_registry.lookup.side_effect = KeyError("not found")
        renderer = EventRenderer(console, registry=bad_registry)
        # Should not raise; falls back to tool_name
        renderer.render(
            QueryEvent(type="tool_use", tool_name="unknown_tool", tool_call_id="call-456")
        )
        renderer._stop_active_status()


class TestToolResultRendering:
    def test_success_result(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        result = ToolResult(
            tool_id="test_tool",
            success=True,
            data={"key": "value"},
        )
        renderer.render(QueryEvent(type="tool_result", tool_result=result))
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "성공" in output

    def test_error_result(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        result = ToolResult(
            tool_id="test_tool",
            success=False,
            error="API error",
            error_type="execution",
        )
        renderer.render(QueryEvent(type="tool_result", tool_result=result))
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "오류" in output
        assert "API error" in output


class TestReset:
    def test_reset_clears_state(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console)
        renderer._text_buffer = "some text"
        renderer._usage = TokenUsage(input_tokens=5, output_tokens=3)
        renderer.reset()
        assert renderer._text_buffer == ""
        assert renderer._usage is None
