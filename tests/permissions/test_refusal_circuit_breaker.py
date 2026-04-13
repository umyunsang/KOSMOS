# SPDX-License-Identifier: Apache-2.0
"""Tests for the Refusal Circuit Breaker."""

from __future__ import annotations

import logging

import pytest

from kosmos.permissions.steps.refusal_circuit_breaker import (
    CONSECUTIVE_DENIAL_THRESHOLD,
    get_denial_count,
    record_denial,
    record_success,
    reset_all,
)


@pytest.fixture(autouse=True)
def clean_state():
    """Reset circuit breaker state before and after each test."""
    reset_all()
    yield
    reset_all()


class TestRecordDenial:
    """record_denial() increments consecutive denial counter."""

    def test_first_denial_returns_1(self):
        count = record_denial("session-1", "tool_a")
        assert count == 1

    def test_consecutive_denials_increment(self):
        for expected in range(1, 5):
            count = record_denial("session-1", "tool_a")
            assert count == expected

    def test_denial_count_getter_matches(self):
        for _ in range(3):
            record_denial("session-1", "tool_a")
        assert get_denial_count("session-1", "tool_a") == 3

    def test_different_tools_independent(self):
        record_denial("session-1", "tool_a")
        record_denial("session-1", "tool_a")
        record_denial("session-1", "tool_b")

        assert get_denial_count("session-1", "tool_a") == 2
        assert get_denial_count("session-1", "tool_b") == 1

    def test_different_sessions_independent(self):
        record_denial("session-a", "tool_x")
        record_denial("session-b", "tool_x")
        record_denial("session-b", "tool_x")

        assert get_denial_count("session-a", "tool_x") == 1
        assert get_denial_count("session-b", "tool_x") == 2


class TestRecordSuccess:
    """record_success() resets the consecutive denial counter."""

    def test_success_resets_counter(self):
        record_denial("session-1", "tool_a")
        record_denial("session-1", "tool_a")
        record_success("session-1", "tool_a")
        assert get_denial_count("session-1", "tool_a") == 0

    def test_success_before_any_denial_is_noop(self):
        record_success("session-1", "tool_a")  # must not raise
        assert get_denial_count("session-1", "tool_a") == 0

    def test_success_only_resets_specified_tool(self):
        record_denial("session-1", "tool_a")
        record_denial("session-1", "tool_b")
        record_success("session-1", "tool_a")

        assert get_denial_count("session-1", "tool_a") == 0
        assert get_denial_count("session-1", "tool_b") == 1

    def test_denials_accumulate_after_reset(self):
        record_denial("session-1", "tool_a")
        record_success("session-1", "tool_a")
        record_denial("session-1", "tool_a")
        assert get_denial_count("session-1", "tool_a") == 1


class TestThresholdWarning:
    """A WARNING is logged when the threshold is reached."""

    def test_warning_logged_at_threshold(self, caplog):
        with caplog.at_level(logging.WARNING):
            for _ in range(CONSECUTIVE_DENIAL_THRESHOLD):
                record_denial("warn-session", "warn_tool")

        assert any(
            "warn_tool" in record.message and record.levelno == logging.WARNING
            for record in caplog.records
        ), "Expected a WARNING log message mentioning the tool name at threshold"

    def test_warning_logged_above_threshold(self, caplog):
        """Warnings should also appear when count exceeds the threshold."""
        with caplog.at_level(logging.WARNING):
            for _ in range(CONSECUTIVE_DENIAL_THRESHOLD + 2):
                record_denial("over-session", "over_tool")

        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING and "over_tool" in r.message
        ]
        assert len(warning_records) >= 3  # at threshold and each subsequent call

    def test_no_warning_below_threshold(self, caplog):
        """No WARNING should be emitted before reaching the threshold."""
        with caplog.at_level(logging.WARNING):
            for _ in range(CONSECUTIVE_DENIAL_THRESHOLD - 1):
                record_denial("quiet-session", "quiet_tool")

        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING and "quiet_tool" in r.message
        ]
        assert len(warning_records) == 0

    def test_no_warning_after_reset(self, caplog):
        """After record_success, the counter resets so no warning on next denial."""
        for _ in range(CONSECUTIVE_DENIAL_THRESHOLD):
            record_denial("reset-warn-session", "reset_tool")

        record_success("reset-warn-session", "reset_tool")

        with caplog.at_level(logging.WARNING):
            caplog.clear()
            record_denial("reset-warn-session", "reset_tool")  # count = 1 again

        warning_records = [
            r for r in caplog.records if r.levelno == logging.WARNING and "reset_tool" in r.message
        ]
        assert len(warning_records) == 0


class TestGetDenialCount:
    """get_denial_count() returns the current counter value."""

    def test_zero_for_unknown_key(self):
        assert get_denial_count("nonexistent-session", "nonexistent_tool") == 0

    def test_correct_count_after_denials(self):
        record_denial("s", "t")
        record_denial("s", "t")
        assert get_denial_count("s", "t") == 2

    def test_zero_after_success(self):
        record_denial("s", "t")
        record_success("s", "t")
        assert get_denial_count("s", "t") == 0


class TestResetAll:
    """reset_all() clears all state."""

    def test_reset_clears_all_state(self):
        record_denial("s1", "t1")
        record_denial("s2", "t2")
        reset_all()
        assert get_denial_count("s1", "t1") == 0
        assert get_denial_count("s2", "t2") == 0
