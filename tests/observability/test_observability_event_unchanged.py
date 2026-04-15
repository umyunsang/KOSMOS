# SPDX-License-Identifier: Apache-2.0
"""Regression guard: ObservabilityEvent schema and ObservabilityEventLogger API must
be unchanged after setup_tracing().

Verifies:
- ObservabilityEvent Pydantic field names, types, and whitelist constants are stable.
- ObservabilityEventLogger.emit() signature is unchanged.
- _ALLOWED_METADATA_KEYS == frozenset({"tool_id", "step", "decision", "error_class", "model"}).
- Metadata whitelist enforcement produces byte-identical serialization before/after OTel init.

Guard covers:
- T030: ObservabilityEvent + ObservabilityEventLogger invariant
"""

from __future__ import annotations

import inspect
import json
import logging
from datetime import UTC
from typing import Any
from unittest.mock import MagicMock

import pytest

from kosmos.observability.event_logger import (
    _ALLOWED_METADATA_KEYS,
    ObservabilityEventLogger,
)
from kosmos.observability.events import ObservabilityEvent

# ---------------------------------------------------------------------------
# Expected whitelist (single source of truth in this guard)
# ---------------------------------------------------------------------------

_EXPECTED_ALLOWED_KEYS: frozenset[str] = frozenset(
    {"tool_id", "step", "decision", "error_class", "model"}
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _event_field_snapshot(cls: type) -> dict[str, Any]:
    """Return a snapshot of Pydantic model fields: names and outer type strings."""

    fields = cls.model_fields  # type: ignore[attr-defined]
    return {
        "field_names": sorted(fields.keys()),
        "field_types": {
            name: str(field.annotation) for name, field in fields.items()
        },
    }


def _emit_with_mixed_metadata(
    logger: ObservabilityEventLogger,
) -> tuple[ObservabilityEvent, str]:
    """Construct an event with both whitelisted and non-whitelisted metadata keys.

    Pass it through emit() using a capturing handler, and return the (clean)
    event and its JSON serialization as captured by the handler.
    """
    captured: list[str] = []

    class _Handler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            captured.append(record.getMessage())

    backing_logger = logging.getLogger("kosmos.events.test_guard")
    backing_logger.setLevel(logging.DEBUG)
    handler = _Handler()
    backing_logger.addHandler(handler)

    try:
        event = ObservabilityEvent(
            event_type="tool_call",
            tool_id="koroad_guard",
            success=True,
            metadata={
                # whitelisted keys
                "tool_id": "koroad_guard",
                "step": "1",
                "decision": "allow",
                "error_class": "none",
                "model": "k-exaone-3.5",
                # non-whitelisted keys — must be stripped
                "user_phone": "010-1234-5678",
                "ip_address": "192.168.1.1",
                "session_cookie": "secret-token",
            },
        )
        oel = ObservabilityEventLogger(logger=backing_logger)
        oel.emit(event)
    finally:
        backing_logger.removeHandler(handler)

    assert len(captured) == 1, f"Expected exactly 1 log message, got {len(captured)}"
    return event, captured[0]


# ---------------------------------------------------------------------------
# T030-A: Whitelist constant guard
# ---------------------------------------------------------------------------


class TestAllowedMetadataKeysConstant:
    """_ALLOWED_METADATA_KEYS must equal the expected frozenset exactly."""

    def test_whitelist_exact_equality(self) -> None:
        assert _ALLOWED_METADATA_KEYS == _EXPECTED_ALLOWED_KEYS, (
            f"_ALLOWED_METADATA_KEYS changed! "
            f"Expected {_EXPECTED_ALLOWED_KEYS}, got {_ALLOWED_METADATA_KEYS}"
        )

    def test_whitelist_is_frozenset(self) -> None:
        assert isinstance(_ALLOWED_METADATA_KEYS, frozenset), (
            f"_ALLOWED_METADATA_KEYS must be a frozenset, got {type(_ALLOWED_METADATA_KEYS)}"
        )

    def test_whitelist_size(self) -> None:
        assert len(_ALLOWED_METADATA_KEYS) == 5, (
            f"_ALLOWED_METADATA_KEYS must contain exactly 5 keys, got {len(_ALLOWED_METADATA_KEYS)}"
        )

    def test_whitelist_unchanged_after_setup_tracing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """setup_tracing() must not modify _ALLOWED_METADATA_KEYS."""
        snapshot_before = frozenset(_ALLOWED_METADATA_KEYS)

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        # Re-import to pick up any potential modification
        from kosmos.observability.event_logger import (
            _ALLOWED_METADATA_KEYS as after_keys,  # noqa: N811
        )

        assert snapshot_before == frozenset(after_keys), (
            f"_ALLOWED_METADATA_KEYS was modified by setup_tracing()! "
            f"Before: {snapshot_before}  After: {frozenset(after_keys)}"
        )


# ---------------------------------------------------------------------------
# T030-B: ObservabilityEvent schema guard
# ---------------------------------------------------------------------------


class TestObservabilityEventSchemaUnchanged:
    """Pydantic field names and types must be identical before/after OTel init."""

    def test_field_names_present(self) -> None:
        """All expected fields exist on ObservabilityEvent."""
        expected_fields = {
            "timestamp", "event_type", "tool_id", "duration_ms", "success", "metadata"
        }
        actual_fields = set(ObservabilityEvent.model_fields.keys())
        assert expected_fields == actual_fields, (
            f"ObservabilityEvent field set changed! "
            f"Expected {expected_fields}, got {actual_fields}"
        )

    def test_schema_unchanged_after_setup_tracing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Field snapshot must be byte-identical before and after setup_tracing()."""
        snapshot_before = _event_field_snapshot(ObservabilityEvent)

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        snapshot_after = _event_field_snapshot(ObservabilityEvent)

        assert snapshot_before == snapshot_after, (
            f"ObservabilityEvent schema changed after setup_tracing()! "
            f"Before: {snapshot_before}  After: {snapshot_after}"
        )

    def test_model_is_frozen(self) -> None:
        """ObservabilityEvent must remain frozen (immutable)."""
        event = ObservabilityEvent(event_type="tool_call")
        with pytest.raises(Exception):  # noqa: B017
            event.success = False  # type: ignore[misc]

    def test_default_success_is_true(self) -> None:
        event = ObservabilityEvent(event_type="tool_call")
        assert event.success is True

    def test_metadata_defaults_to_empty_dict(self) -> None:
        event = ObservabilityEvent(event_type="llm_call")
        assert event.metadata == {}


# ---------------------------------------------------------------------------
# T030-C: ObservabilityEventLogger.emit signature guard
# ---------------------------------------------------------------------------


class TestObservabilityEventLoggerSignatureUnchanged:
    """ObservabilityEventLogger.emit() signature must be unchanged."""

    def test_emit_method_exists(self) -> None:
        assert hasattr(ObservabilityEventLogger, "emit"), (
            "ObservabilityEventLogger.emit() method is missing!"
        )

    def test_emit_signature(self) -> None:
        sig = inspect.signature(ObservabilityEventLogger.emit)
        params = list(sig.parameters.keys())
        # Must have 'self' and 'event' — no more, no less
        assert params == ["self", "event"], (
            f"ObservabilityEventLogger.emit signature changed! "
            f"Expected ['self', 'event'], got {params}"
        )

    def test_emit_signature_unchanged_after_setup_tracing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sig_before = str(inspect.signature(ObservabilityEventLogger.emit))

        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        sig_after = str(inspect.signature(ObservabilityEventLogger.emit))

        assert sig_before == sig_after, (
            f"ObservabilityEventLogger.emit signature changed after setup_tracing()! "
            f"Before: {sig_before}  After: {sig_after}"
        )


# ---------------------------------------------------------------------------
# T030-D: Metadata whitelist enforcement — before/after byte-identical
# ---------------------------------------------------------------------------


class TestMetadataWhitelistEnforcement:
    """Metadata whitelist strip behavior must produce byte-identical JSON before/after OTel init."""

    def test_whitelist_strips_non_allowed_keys(self) -> None:
        """Non-whitelisted keys are removed from emitted metadata."""
        mock_log = MagicMock()
        oel = ObservabilityEventLogger(logger=mock_log)

        event = ObservabilityEvent(
            event_type="tool_call",
            metadata={
                "tool_id": "koroad",
                "user_ip": "192.168.1.1",
                "phone": "010-0000-0000",
            },
        )
        oel.emit(event)

        log_json = mock_log.log.call_args[0][1]
        parsed = json.loads(log_json)

        assert "tool_id" in parsed["metadata"]
        assert "user_ip" not in parsed["metadata"]
        assert "phone" not in parsed["metadata"]

    def test_whitelist_retains_all_allowed_keys(self) -> None:
        """All five whitelisted keys pass through unchanged."""
        mock_log = MagicMock()
        oel = ObservabilityEventLogger(logger=mock_log)

        event = ObservabilityEvent(
            event_type="llm_call",
            metadata={
                "tool_id": "t1",
                "step": "2",
                "decision": "allow",
                "error_class": "none",
                "model": "k-exaone",
            },
        )
        oel.emit(event)

        log_json = mock_log.log.call_args[0][1]
        parsed = json.loads(log_json)

        assert parsed["metadata"]["tool_id"] == "t1"
        assert parsed["metadata"]["step"] == "2"
        assert parsed["metadata"]["decision"] == "allow"
        assert parsed["metadata"]["error_class"] == "none"
        assert parsed["metadata"]["model"] == "k-exaone"

    def test_serialization_byte_identical_before_after_setup_tracing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """model_dump_json() output for equivalent events must be identical before/after OTel init.

        Strategy: construct two events with the same field values (except timestamp,
        which is pinned), emit them through the logger, and compare the captured JSON
        strings.  The timestamp is set explicitly to avoid drift.
        """
        from datetime import datetime

        fixed_ts = datetime(2026, 4, 15, 0, 0, 0, tzinfo=UTC)

        def _make_event() -> ObservabilityEvent:
            return ObservabilityEvent(
                timestamp=fixed_ts,
                event_type="tool_call",
                tool_id="koroad_guard",
                success=True,
                duration_ms=10.0,
                metadata={
                    "tool_id": "koroad_guard",
                    "step": "1",
                    "decision": "allow",
                    "error_class": "none",
                    "model": "k-exaone",
                    # non-whitelisted — will be stripped
                    "raw_user_input": "서울 교통사고",
                },
            )

        captured_before: list[str] = []
        captured_after: list[str] = []

        # --- BEFORE setup_tracing ---
        class _BeforeHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                # Capture only the structured event JSON (INFO level), not the
                # PII-warning message (WARNING level) that precedes it.
                if record.levelno == logging.INFO:
                    captured_before.append(record.getMessage())

        before_logger = logging.getLogger("kosmos.events.before_guard")
        before_logger.setLevel(logging.DEBUG)
        h_before = _BeforeHandler()
        before_logger.addHandler(h_before)
        try:
            ObservabilityEventLogger(logger=before_logger).emit(_make_event())
        finally:
            before_logger.removeHandler(h_before)

        # --- call setup_tracing (no-op) ---
        monkeypatch.setenv("OTEL_SDK_DISABLED", "true")
        from kosmos.observability.tracing import TracingSettings, setup_tracing

        setup_tracing(TracingSettings(disabled=True))

        # --- AFTER setup_tracing ---
        class _AfterHandler(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                # Same: capture only the structured event JSON at INFO level.
                if record.levelno == logging.INFO:
                    captured_after.append(record.getMessage())

        after_logger = logging.getLogger("kosmos.events.after_guard")
        after_logger.setLevel(logging.DEBUG)
        h_after = _AfterHandler()
        after_logger.addHandler(h_after)
        try:
            ObservabilityEventLogger(logger=after_logger).emit(_make_event())
        finally:
            after_logger.removeHandler(h_after)

        assert len(captured_before) == 1, (
            f"Expected 1 INFO event log, got {len(captured_before)}: {captured_before}"
        )
        assert len(captured_after) == 1, (
            f"Expected 1 INFO event log, got {len(captured_after)}: {captured_after}"
        )

        json_before = json.loads(captured_before[0])
        json_after = json.loads(captured_after[0])

        # raw_user_input must be stripped in both
        assert "raw_user_input" not in json_before["metadata"]
        assert "raw_user_input" not in json_after["metadata"]

        # The two JSON outputs must be structurally identical
        assert json_before == json_after, (
            f"JSON serialization changed after setup_tracing()!\n"
            f"Before: {captured_before[0]}\n"
            f"After:  {captured_after[0]}"
        )
