# SPDX-License-Identifier: Apache-2.0
"""Tests for SystemPromptAssembler (T010, T028).

Covers:
- All four mandatory sections present (FR-009)
- Determinism: same config → identical output
- Determinism stress test: 1000 consecutive calls (SC-001, T028)
- personal_data_warning=False omits section 4
"""

from __future__ import annotations

from kosmos.context.models import SystemPromptConfig
from kosmos.context.system_prompt import SystemPromptAssembler


class TestSystemPromptAssembler:
    def _assembler(self) -> SystemPromptAssembler:
        return SystemPromptAssembler()

    def test_contains_platform_identity(self) -> None:
        cfg = SystemPromptConfig(platform_name="KOSMOS")
        result = self._assembler().assemble(cfg)
        assert "KOSMOS" in result
        assert "Korean public service AI assistant" in result

    def test_contains_language_policy(self) -> None:
        cfg = SystemPromptConfig(language="ko")
        result = self._assembler().assemble(cfg)
        assert "ko" in result
        assert "language" in result.lower() or "respond" in result.lower()

    def test_contains_tool_use_policy(self) -> None:
        result = self._assembler().assemble(SystemPromptConfig())
        assert "tools" in result.lower()
        assert "fabricate" in result.lower()

    def test_contains_personal_data_reminder_when_enabled(self) -> None:
        cfg = SystemPromptConfig(personal_data_warning=True)
        result = self._assembler().assemble(cfg)
        assert "personal data" in result.lower()

    def test_omits_personal_data_reminder_when_disabled(self) -> None:
        cfg = SystemPromptConfig(personal_data_warning=False)
        result = self._assembler().assemble(cfg)
        assert "personal data" not in result.lower()

    def test_deterministic_same_instance(self) -> None:
        cfg = SystemPromptConfig()
        assembler = self._assembler()
        first = assembler.assemble(cfg)
        second = assembler.assemble(cfg)
        assert first == second

    def test_deterministic_different_instances(self) -> None:
        cfg = SystemPromptConfig()
        first = SystemPromptAssembler().assemble(cfg)
        second = SystemPromptAssembler().assemble(cfg)
        assert first == second

    def test_sections_separated_by_double_newline(self) -> None:
        result = self._assembler().assemble(SystemPromptConfig())
        assert "\n\n" in result

    def test_custom_platform_name(self) -> None:
        cfg = SystemPromptConfig(platform_name="TESTBOT")
        result = self._assembler().assemble(cfg)
        assert "TESTBOT" in result

    def test_custom_language(self) -> None:
        cfg = SystemPromptConfig(language="en")
        result = self._assembler().assemble(cfg)
        assert "en" in result

    def test_nonempty_output(self) -> None:
        result = self._assembler().assemble(SystemPromptConfig())
        assert len(result.strip()) > 0


class TestSystemPromptDeterminismStress:
    """SC-001: 1000 consecutive calls return identical content (T028)."""

    def test_1000_calls_deterministic(self) -> None:
        cfg = SystemPromptConfig()
        assembler = SystemPromptAssembler()
        baseline = assembler.assemble(cfg)
        for _ in range(999):
            result = assembler.assemble(cfg)
            assert result == baseline, "Assemble output changed between calls"
