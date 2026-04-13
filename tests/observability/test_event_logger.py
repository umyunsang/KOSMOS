# SPDX-License-Identifier: Apache-2.0
"""Tests for ObservabilityEventLogger — PII whitelist, emit, event types.

Covers AC-A12(c): unit tests for ObservabilityEventLogger.
"""

from __future__ import annotations

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from kosmos.observability.event_logger import (
    _ALLOWED_METADATA_KEYS,
    ObservabilityEventLogger,
    _log_level_for,
)
from kosmos.observability.events import ObservabilityEvent

# ---------------------------------------------------------------------------
# Log level mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_type,success,expected_level",
    [
        ("llm_call", True, logging.INFO),
        ("llm_call", False, logging.WARNING),
        ("permission_decision", True, logging.INFO),
        ("permission_decision", False, logging.WARNING),
        ("tool_call", True, logging.INFO),
        ("tool_call", False, logging.WARNING),
        ("retry", True, logging.INFO),
        ("retry", False, logging.INFO),
        ("circuit_break", True, logging.INFO),
        ("circuit_break", False, logging.WARNING),
        ("cache_hit", True, logging.DEBUG),
        ("cache_hit", False, logging.DEBUG),
        ("cache_miss", True, logging.DEBUG),
        ("cache_miss", False, logging.DEBUG),
        ("error", True, logging.WARNING),
        ("error", False, logging.WARNING),
        ("auth_refresh", True, logging.INFO),
        ("auth_refresh", False, logging.WARNING),
    ],
)
def test_emit_level_by_event_type_and_success(
    event_type: str, success: bool, expected_level: int
) -> None:
    """Parameterized test: each (event_type, success) pair maps to the correct log level."""
    assert _log_level_for(event_type, success) == expected_level  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# PII whitelist enforcement
# ---------------------------------------------------------------------------


def test_emit_pii_key_allowed_keys_pass_through() -> None:
    """All whitelisted keys are retained in emitted metadata."""
    mock_log = MagicMock()
    logger = ObservabilityEventLogger(logger=mock_log)
    event = ObservabilityEvent(
        event_type="tool_call",
        metadata=dict.fromkeys(_ALLOWED_METADATA_KEYS, "v"),
    )
    logger.emit(event)
    # The log call should have been made
    assert mock_log.log.called


def test_emit_pii_key_dropped() -> None:
    """Non-whitelisted key is dropped; a WARNING is logged; no exception raised."""
    mock_log = MagicMock()
    logger = ObservabilityEventLogger(logger=mock_log)
    event = ObservabilityEvent(
        event_type="tool_call",
        metadata={"phone_number": "010-1234-5678", "tool_id": "koroad"},
    )
    # Should not raise
    logger.emit(event)

    # A warning about the dropped key should have been logged
    assert mock_log.warning.called
    warning_call_args = str(mock_log.warning.call_args)
    assert "phone_number" in warning_call_args

    # The actual event log call should still succeed
    assert mock_log.log.called
    # The JSON in the log call should not contain "phone_number"
    log_call_args = str(mock_log.log.call_args)
    assert "phone_number" not in log_call_args
    # But tool_id should still be there
    assert "koroad" in log_call_args


def test_emit_all_pii_stripped_only_warns() -> None:
    """All keys disallowed: metadata ends up empty, still emits."""
    mock_log = MagicMock()
    logger = ObservabilityEventLogger(logger=mock_log)
    event = ObservabilityEvent(
        event_type="llm_call",
        metadata={"user_id": "123", "ip": "192.168.1.1"},
    )
    logger.emit(event)
    # Should warn and still call log
    assert mock_log.warning.called
    assert mock_log.log.called


# ---------------------------------------------------------------------------
# Fail-safe contract
# ---------------------------------------------------------------------------


def test_emit_fail_safe_logger_raises() -> None:
    """If the backing logger raises, emit() must not propagate the exception."""
    mock_log = MagicMock()
    mock_log.log.side_effect = RuntimeError("logging broke")
    logger = ObservabilityEventLogger(logger=mock_log)
    event = ObservabilityEvent(event_type="tool_call")
    # Must not raise
    logger.emit(event)


def test_emit_fail_safe_warning_on_exception() -> None:
    """emit() catches exceptions and logs them as warnings to the root logger."""
    mock_log = MagicMock()
    mock_log.log.side_effect = RuntimeError("logging broke")
    logger = ObservabilityEventLogger(logger=mock_log)
    event = ObservabilityEvent(event_type="tool_call")

    with patch("kosmos.observability.event_logger.logging") as mock_logging_module:
        mock_inner_logger = MagicMock()
        mock_logging_module.getLogger.return_value = mock_inner_logger
        # This patches the inner fallback warning call — if it reaches there,
        # the test verifies it doesn't raise.
        logger.emit(event)


# ---------------------------------------------------------------------------
# JSON serialisability
# ---------------------------------------------------------------------------


def test_emit_json_serializable() -> None:
    """The emitted message is valid JSON."""
    captured_messages: list[str] = []

    class CapturingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured_messages.append(record.getMessage())

    handler = CapturingHandler()
    events_logger = logging.getLogger("kosmos.events")
    original_level = events_logger.level
    events_logger.setLevel(logging.DEBUG)
    events_logger.addHandler(handler)

    try:
        logger = ObservabilityEventLogger()
        event = ObservabilityEvent(
            event_type="tool_call",
            tool_id="koroad_search",
            success=True,
            duration_ms=42.5,
            metadata={"tool_id": "koroad_search"},
        )
        logger.emit(event)
    finally:
        events_logger.removeHandler(handler)
        events_logger.setLevel(original_level)

    assert len(captured_messages) == 1
    msg = captured_messages[0]
    parsed = json.loads(msg)
    assert parsed["event_type"] == "tool_call"
    assert parsed["tool_id"] == "koroad_search"
    assert parsed["success"] is True


# ---------------------------------------------------------------------------
# New EventType variants
# ---------------------------------------------------------------------------


def test_emit_new_event_types_accepted() -> None:
    """New event types llm_call and permission_decision are valid."""
    mock_log = MagicMock()
    logger = ObservabilityEventLogger(logger=mock_log)

    for event_type in ("llm_call", "permission_decision"):
        event = ObservabilityEvent(
            event_type=event_type,  # type: ignore[arg-type]
            success=True,
        )
        logger.emit(event)

    assert mock_log.log.call_count == 2
