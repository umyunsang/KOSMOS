# SPDX-License-Identifier: Apache-2.0
"""Tests for ConsentPromptHandler."""

from __future__ import annotations

import io
from unittest.mock import patch

from rich.console import Console

from kosmos.cli.permissions import ConsentPromptHandler


def _make_console() -> Console:
    return Console(file=io.StringIO(), force_terminal=True, width=120)


class TestConsentPromptHandler:
    def test_prompt_true_when_confirmed(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        with patch("kosmos.cli.permissions.Confirm.ask", return_value=True):
            result = handler.prompt("테스트 도구", "테스트 기관", "테스트 설명")
        assert result is True

    def test_prompt_false_when_denied(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        with patch("kosmos.cli.permissions.Confirm.ask", return_value=False):
            result = handler.prompt("테스트 도구", "테스트 기관", "테스트 설명")
        assert result is False

    def test_prompt_false_on_eof(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        with patch("kosmos.cli.permissions.Confirm.ask", side_effect=EOFError):
            result = handler.prompt("테스트 도구", "테스트 기관", "테스트 설명")
        assert result is False

    def test_prompt_false_on_keyboard_interrupt(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        with patch("kosmos.cli.permissions.Confirm.ask", side_effect=KeyboardInterrupt):
            result = handler.prompt("테스트 도구", "테스트 기관", "테스트 설명")
        assert result is False

    def test_prompt_shows_tool_info(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        with patch("kosmos.cli.permissions.Confirm.ask", return_value=False):
            handler.prompt("도로 검색", "국토부", "도로 정보 조회")
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "도로 검색" in output
        assert "국토부" in output

    def test_display_denial_shows_reason(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        handler.display_denial("테스트 도구", "권한이 없습니다")
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "거부" in output
        assert "권한이 없습니다" in output

    def test_display_denial_shows_tool_name(self) -> None:
        console = _make_console()
        handler = ConsentPromptHandler(console)
        handler.display_denial("날씨 조회", "인증 실패")
        output = console.file.getvalue()  # type: ignore[union-attr]
        assert "날씨 조회" in output
