# SPDX-License-Identifier: Apache-2.0
"""Tests for AttachmentCollector (US2 / FR-002, FR-008, FR-010).

Covers:
- Empty session returns None
- Resolved tasks section present in output
- API health warnings included when provided
- Empty / None api_health ignored
- Reminder fires at cadence turn
- Reminder skips turn 0 (even when cadence=1)
- Reminder skips non-cadence turns
- Auth expiry warning via backdoor _auth_expiry_at attribute
- Multiple sections combined in a single attachment string
- SC-005: 50-turn session with cadence=5 produces exactly 10 reminder blocks (T029)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kosmos.context.attachments import AttachmentCollector
from kosmos.context.models import SystemPromptConfig
from kosmos.engine.config import QueryEngineConfig
from kosmos.engine.models import QueryState
from kosmos.llm.usage import UsageTracker


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(**kwargs) -> QueryState:
    """Create a QueryState with default UsageTracker for testing."""
    config = QueryEngineConfig()
    usage = UsageTracker(budget=config.context_window)
    return QueryState(usage=usage, **kwargs)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestAttachmentCollector:
    """AttachmentCollector.collect() produces per-turn dynamic attachment."""

    def test_empty_session_returns_none(self) -> None:
        """turn_count=0, no tasks → collect() returns None."""
        state = _make_state(turn_count=0)
        collector = AttachmentCollector()
        result = collector.collect(state=state)
        assert result is None

    def test_resolved_tasks_section(self) -> None:
        """Resolved tasks in state appear in the attachment content."""
        state = _make_state(turn_count=0, resolved_tasks=["Look up weather", "Find hospital"])
        collector = AttachmentCollector()
        result = collector.collect(state=state)
        assert result is not None
        assert "Look up weather" in result
        assert "Find hospital" in result
        assert "Resolved tasks" in result

    def test_api_health_section(self) -> None:
        """api_health dict with non-empty values appears as warnings."""
        state = _make_state(turn_count=0)
        api_health = {"kma_weather": "degraded", "koroad_traffic": "timeout"}
        collector = AttachmentCollector()
        result = collector.collect(state=state, api_health=api_health)
        assert result is not None
        assert "kma_weather" in result
        assert "koroad_traffic" in result
        assert "health" in result.lower() or "warning" in result.lower()

    def test_api_health_empty_dict_ignored(self) -> None:
        """Empty api_health dict is ignored → no health section."""
        state = _make_state(turn_count=0)
        collector = AttachmentCollector()
        result = collector.collect(state=state, api_health={})
        # With no tasks/reminder/auth/health, expect None
        assert result is None

    def test_api_health_none_ignored(self) -> None:
        """None api_health produces no health section."""
        state = _make_state(turn_count=0)
        collector = AttachmentCollector()
        result = collector.collect(state=state, api_health=None)
        assert result is None

    def test_reminder_fires_at_cadence(self) -> None:
        """turn_count=5, cadence=5 → attachment includes '[Reminder' block."""
        config = SystemPromptConfig(reminder_cadence=5)
        state = _make_state(turn_count=5)
        collector = AttachmentCollector(config=config)
        result = collector.collect(state=state)
        assert result is not None
        assert "[Reminder" in result

    def test_reminder_skips_turn_0(self) -> None:
        """turn_count=0 with cadence=1 → no reminder (turn 0 always excluded)."""
        config = SystemPromptConfig(reminder_cadence=1)
        state = _make_state(turn_count=0)
        collector = AttachmentCollector(config=config)
        result = collector.collect(state=state)
        # turn_count=0, no tasks, no health → None
        assert result is None

    def test_reminder_skips_non_cadence(self) -> None:
        """turn_count=3, cadence=5 → no reminder fires."""
        config = SystemPromptConfig(reminder_cadence=5)
        state = _make_state(turn_count=3)
        collector = AttachmentCollector(config=config)
        result = collector.collect(state=state)
        # No tasks, no health, no reminder → None
        assert result is None

    def test_auth_expiry_warning(self) -> None:
        """Auth expiry set to near-future generates a warning in attachment."""
        state = _make_state(turn_count=0)
        # Backdoor: set _auth_expiry_at to 30 seconds from now
        state._auth_expiry_at = datetime.now(tz=timezone.utc) + timedelta(seconds=30)  # noqa: SLF001
        collector = AttachmentCollector()
        result = collector.collect(state=state)
        assert result is not None
        assert "auth" in result.lower() or "expir" in result.lower()

    def test_multiple_sections_combined(self) -> None:
        """Tasks + health + reminder all present → all appear in output."""
        config = SystemPromptConfig(reminder_cadence=5)
        state = _make_state(
            turn_count=5,
            resolved_tasks=["Task one completed"],
        )
        api_health = {"some_api": "slow response"}
        collector = AttachmentCollector(config=config)
        result = collector.collect(state=state, api_health=api_health)
        assert result is not None
        assert "Task one completed" in result
        assert "some_api" in result
        assert "[Reminder" in result


# ---------------------------------------------------------------------------
# T029: SC-005 Reminder count — 50-turn session with cadence=5
# ---------------------------------------------------------------------------


class TestAttachmentReminderCadenceStress:
    """SC-005: 50-turn session with cadence=5 produces exactly 10 reminder blocks."""

    def test_reminder_count_50_turns_cadence_5(self) -> None:
        """SC-005: 50 turns, cadence=5 → exactly 10 reminder blocks emitted."""
        config = SystemPromptConfig(reminder_cadence=5)
        collector = AttachmentCollector(config=config)

        reminder_count = 0
        for turn in range(1, 51):  # turns 1-50
            state = _make_state(
                turn_count=turn,
                resolved_tasks=["task done"] if turn > 1 else [],
            )
            result = collector.collect(state=state)
            if result is not None and "[Reminder" in result:
                reminder_count += 1

        assert reminder_count == 10, (
            f"Expected 10 reminders in 50 turns with cadence=5, got {reminder_count}"
        )
