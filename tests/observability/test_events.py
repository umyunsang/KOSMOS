# SPDX-License-Identifier: Apache-2.0
"""Tests for ObservabilityEvent model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from kosmos.observability.events import ObservabilityEvent

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_event_defaults_success_true() -> None:
    event = ObservabilityEvent(event_type="tool_call")
    assert event.success is True


def test_event_defaults_empty_metadata() -> None:
    event = ObservabilityEvent(event_type="tool_call")
    assert event.metadata == {}


def test_event_defaults_tool_id_none() -> None:
    event = ObservabilityEvent(event_type="tool_call")
    assert event.tool_id is None


def test_event_defaults_duration_none() -> None:
    event = ObservabilityEvent(event_type="retry")
    assert event.duration_ms is None


def test_event_auto_timestamp() -> None:
    """Timestamp is auto-populated with a UTC datetime."""
    event = ObservabilityEvent(event_type="cache_hit")
    assert isinstance(event.timestamp, datetime)
    assert event.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# Explicit field values
# ---------------------------------------------------------------------------


def test_event_explicit_fields() -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    event = ObservabilityEvent(
        timestamp=ts,
        event_type="error",
        tool_id="koroad_search",
        duration_ms=142.5,
        success=False,
        metadata={"error_class": "transient", "attempt": 2},
    )
    assert event.timestamp == ts
    assert event.event_type == "error"
    assert event.tool_id == "koroad_search"
    assert event.duration_ms == 142.5
    assert event.success is False
    assert event.metadata["error_class"] == "transient"
    assert event.metadata["attempt"] == 2


# ---------------------------------------------------------------------------
# All valid event_type values
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "event_type",
    ["tool_call", "retry", "circuit_break", "cache_hit", "cache_miss", "error", "auth_refresh"],
)
def test_all_valid_event_types(event_type: str) -> None:
    event = ObservabilityEvent(event_type=event_type)  # type: ignore[arg-type]
    assert event.event_type == event_type


# ---------------------------------------------------------------------------
# Invalid event_type
# ---------------------------------------------------------------------------


def test_invalid_event_type_raises() -> None:
    with pytest.raises(ValidationError):
        ObservabilityEvent(event_type="unknown_event_xyz")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Immutability
# ---------------------------------------------------------------------------


def test_event_is_frozen() -> None:
    event = ObservabilityEvent(event_type="tool_call")
    with pytest.raises(ValidationError):
        event.success = False  # type: ignore[misc]


# ---------------------------------------------------------------------------
# JSON serialization
# ---------------------------------------------------------------------------


def test_event_serializes_to_json() -> None:
    event = ObservabilityEvent(
        event_type="retry",
        tool_id="bus_route_search",
        duration_ms=50.0,
        metadata={"attempt": 1},
    )
    json_str = event.model_dump_json()
    assert "retry" in json_str
    assert "bus_route_search" in json_str
    assert "50.0" in json_str


def test_event_round_trips_via_dict() -> None:
    event = ObservabilityEvent(
        event_type="cache_miss",
        tool_id="weather_api",
        success=True,
    )
    data = event.model_dump()
    reconstructed = ObservabilityEvent.model_validate(data)
    assert reconstructed.event_type == event.event_type
    assert reconstructed.tool_id == event.tool_id
    assert reconstructed.success == event.success
