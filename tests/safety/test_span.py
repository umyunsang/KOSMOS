# SPDX-License-Identifier: Apache-2.0
"""T015 — Unit tests for emit_safety_event() in kosmos.safety._span.

Tests:
1. test_emit_redacted_event_sets_attribute
   - A RedactedEvent emits exactly {"gen_ai.safety.event": "redacted"} on the span.
2. test_all_four_kinds_map_to_bounded_enum_values
   - All four SafetyEvent variants produce attribute values in the allowed set.
3. test_emit_on_non_recording_span_is_noop
   - Calling emit_safety_event on a non-recording span raises no exception and
     sets no attribute.
"""

from __future__ import annotations

import pytest
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from opentelemetry.trace import INVALID_SPAN

from kosmos.safety._models import (
    InjectionBlockedEvent,
    InjectionSignalSet,
    ModerationBlockedEvent,
    ModerationWarnedEvent,
    RedactedEvent,
)
from kosmos.safety._span import emit_safety_event

# ---------------------------------------------------------------------------
# Module-level TracerProvider + InMemorySpanExporter (shared across tests).
#
# The SDK's TracerProvider reads OTEL_SDK_DISABLED at construction time — when
# it's "true" (CI default, to suppress OTLP export), get_tracer() returns a
# NoOpTracer and spans are never recorded.  We temporarily remove that env var
# just long enough to build the in-memory provider, then restore it so the
# rest of the process sees the original value.
# ---------------------------------------------------------------------------

import os as _os

_prev_otel_disabled = _os.environ.pop("OTEL_SDK_DISABLED", None)
try:
    _EXPORTER = InMemorySpanExporter()
    _PROVIDER = TracerProvider()
    _PROVIDER.add_span_processor(SimpleSpanProcessor(_EXPORTER))
    _TRACER = _PROVIDER.get_tracer("kosmos.safety.test_span")
finally:
    if _prev_otel_disabled is not None:
        _os.environ["OTEL_SDK_DISABLED"] = _prev_otel_disabled

_ALLOWED_KINDS = {"redacted", "injection_blocked", "moderation_blocked", "moderation_warned"}


@pytest.fixture(autouse=True)
def _clear_exporter() -> None:
    """Clear exported spans before each test to ensure isolation."""
    _EXPORTER.clear()


# ---------------------------------------------------------------------------
# Test 1: RedactedEvent sets exactly one attribute with value "redacted"
# ---------------------------------------------------------------------------


def test_emit_redacted_event_sets_attribute() -> None:
    """emit_safety_event on a RedactedEvent sets gen_ai.safety.event=redacted only."""
    event = RedactedEvent(match_count=3)
    span = _TRACER.start_span("test_redacted")
    emit_safety_event(event, span=span)
    span.end()

    spans = _EXPORTER.get_finished_spans()
    assert len(spans) == 1, f"Expected 1 finished span, got {len(spans)}"

    attrs = dict(spans[0].attributes or {})
    assert attrs == {"gen_ai.safety.event": "redacted"}, (
        f"Expected exactly {{gen_ai.safety.event: redacted}}, got {attrs}"
    )


# ---------------------------------------------------------------------------
# Test 2: All four event variants produce a value in the bounded enum
# ---------------------------------------------------------------------------

_INJECTION_SIGNAL = InjectionSignalSet(
    structural_score=0.9,
    entropy_score=0.8,
    length_deviation=1.2,
    decision="block",
)

_EVENT_VARIANTS = [
    RedactedEvent(match_count=1),
    InjectionBlockedEvent(signal_summary=_INJECTION_SIGNAL),
    ModerationBlockedEvent(categories=("hate",)),
    ModerationWarnedEvent(detail="outage"),
]


@pytest.mark.parametrize("event", _EVENT_VARIANTS, ids=lambda e: e.kind)
def test_all_four_kinds_map_to_bounded_enum_values(event: object) -> None:
    """Every SafetyEvent variant produces an attribute value in the bounded set."""
    span = _TRACER.start_span(f"test_{event.kind}")  # type: ignore[union-attr]
    emit_safety_event(event, span=span)  # type: ignore[arg-type]
    span.end()

    spans = _EXPORTER.get_finished_spans()
    finished = [s for s in spans if s.name == f"test_{event.kind}"]  # type: ignore[union-attr]
    assert len(finished) == 1, f"Expected 1 span named test_{event.kind}, got {finished}"  # type: ignore[union-attr]

    attrs = dict(finished[0].attributes or {})
    value = attrs.get("gen_ai.safety.event")
    assert value in _ALLOWED_KINDS, (
        f"Attribute value {value!r} is not in the allowed set {_ALLOWED_KINDS}"
    )


# ---------------------------------------------------------------------------
# Test 3: Non-recording span → noop, no exception, no attribute set
# ---------------------------------------------------------------------------


def test_emit_on_non_recording_span_is_noop() -> None:
    """emit_safety_event on a non-recording span is a silent no-op."""
    # INVALID_SPAN is the canonical non-recording sentinel in the OTel SDK.
    assert not INVALID_SPAN.is_recording(), "Precondition: INVALID_SPAN must be non-recording"

    event = RedactedEvent(match_count=0)

    # Must not raise.
    emit_safety_event(event, span=INVALID_SPAN)  # type: ignore[arg-type]

    # INVALID_SPAN has no attributes; verify nothing was set.
    attrs = getattr(INVALID_SPAN, "attributes", None) or {}
    assert "gen_ai.safety.event" not in attrs, (
        "gen_ai.safety.event must not be set on a non-recording span"
    )
