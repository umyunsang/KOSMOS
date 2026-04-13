# SPDX-License-Identifier: Apache-2.0
"""Tests for EventRenderer streaming markdown mode and theme integration."""

from __future__ import annotations

import io

import pytest
from rich.console import Console

from kosmos.cli.renderer import EventRenderer
from kosmos.cli.themes import get_theme
from kosmos.engine.events import QueryEvent, StopReason
from kosmos.llm.models import TokenUsage


def _make_console() -> Console:
    """Return a Rich console that captures output to a StringIO buffer."""
    return Console(file=io.StringIO(), force_terminal=True, width=120)


def _get_output(console: Console) -> str:
    return console.file.getvalue()  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# Plain (non-streaming-markdown) mode
# ---------------------------------------------------------------------------


class TestPlainStreamingMode:
    def test_text_delta_printed_incrementally(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False)
        renderer.render(QueryEvent(type="text_delta", content="Hello"))
        renderer.render(QueryEvent(type="text_delta", content=" World"))
        assert renderer._text_buffer == "Hello World"

    def test_output_contains_text_after_delta(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False)
        renderer.render(QueryEvent(type="text_delta", content="테스트"))
        assert "테스트" in _get_output(console)

    def test_no_live_context_in_plain_mode(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False)
        renderer.render(QueryEvent(type="text_delta", content="chunk"))
        assert renderer._live is None

    def test_stop_event_resets_buffer(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False)
        renderer.render(QueryEvent(type="text_delta", content="text"))
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.end_turn))
        assert renderer._text_buffer == ""


# ---------------------------------------------------------------------------
# Streaming markdown mode
# ---------------------------------------------------------------------------


class TestStreamingMarkdownMode:
    def test_buffer_accumulates_in_streaming_mode(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=True)
        renderer.render(QueryEvent(type="text_delta", content="# Hello"))
        renderer.render(QueryEvent(type="text_delta", content="\n\nWorld"))
        assert renderer._text_buffer == "# Hello\n\nWorld"

    def test_stop_event_closes_live_and_resets(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=True)
        # Feed enough chars to trigger Live creation
        renderer.render(
            QueryEvent(
                type="text_delta",
                content="A" * 20,
            )
        )
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.task_complete))
        assert renderer._live is None
        assert renderer._text_buffer == ""

    def test_small_delta_does_not_open_live_immediately(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=True)
        # Under the minimum threshold
        renderer.render(QueryEvent(type="text_delta", content="Hi"))
        assert renderer._live is None

    def test_live_opens_after_threshold(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=True)
        # Over the minimum threshold of 10 chars
        renderer.render(QueryEvent(type="text_delta", content="A" * 15))
        assert renderer._live is not None
        # Cleanup
        renderer.reset()

    def test_reset_stops_live(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=True)
        renderer.render(QueryEvent(type="text_delta", content="A" * 15))
        assert renderer._live is not None
        renderer.reset()
        assert renderer._live is None


# ---------------------------------------------------------------------------
# Theme integration
# ---------------------------------------------------------------------------


class TestThemeIntegration:
    def test_custom_theme_applied_to_renderer(self) -> None:
        console = _make_console()
        dark = get_theme("dark")
        renderer = EventRenderer(console, streaming_markdown=False, theme=dark)
        assert renderer._theme is dark

    def test_default_theme_loaded_when_not_specified(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("KOSMOS_THEME", raising=False)
        monkeypatch.delenv("KOSMOS_CLI_THEME", raising=False)
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False)
        assert renderer._theme == get_theme("default")

    def test_tool_use_uses_theme_colour(self) -> None:
        """Smoke test: tool_use renders without error when theme is dark."""
        from unittest.mock import MagicMock  # noqa: PLC0415

        console = _make_console()
        dark = get_theme("dark")
        registry = MagicMock()
        registry.lookup.side_effect = Exception("not found")
        renderer = EventRenderer(console, registry=registry, streaming_markdown=False, theme=dark)
        # Should not raise
        renderer.render(
            QueryEvent(type="tool_use", tool_name="weather_tool", tool_call_id="call_001")
        )
        renderer._stop_active_status()


# ---------------------------------------------------------------------------
# Usage rendering with theme
# ---------------------------------------------------------------------------


class TestUsageRendering:
    def test_usage_shown_in_stop_event(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False, show_usage=True)
        renderer.render(
            QueryEvent(
                type="usage_update",
                usage=TokenUsage(input_tokens=42, output_tokens=7),
            )
        )
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.end_turn))
        output = _get_output(console)
        assert "42" in output
        assert "7" in output

    def test_usage_hidden_when_show_usage_false(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False, show_usage=False)
        renderer.render(
            QueryEvent(
                type="usage_update",
                usage=TokenUsage(input_tokens=42, output_tokens=7),
            )
        )
        renderer.render(QueryEvent(type="stop", stop_reason=StopReason.end_turn))
        output = _get_output(console)
        # Usage numbers should not appear
        assert "42" not in output


# ---------------------------------------------------------------------------
# Korean text safety
# ---------------------------------------------------------------------------


class TestKoreanText:
    def test_korean_text_rendered_without_error(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=False)
        korean = "안녕하세요. 오늘 서울의 날씨는 맑습니다."
        renderer.render(QueryEvent(type="text_delta", content=korean))
        assert renderer._text_buffer == korean

    def test_korean_text_in_streaming_markdown(self) -> None:
        console = _make_console()
        renderer = EventRenderer(console, streaming_markdown=True)
        korean = "## 오늘의 날씨\n\n서울: 맑음, 22°C"
        renderer.render(QueryEvent(type="text_delta", content=korean))
        assert renderer._text_buffer == korean
        renderer.reset()
