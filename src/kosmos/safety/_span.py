# SPDX-License-Identifier: Apache-2.0
"""Span-attribute helper for KOSMOS safety pipeline observability.

Emits the ``gen_ai.safety.event`` span attribute (FR-016) on behalf of all
three safety layers.  The attribute value is a bounded enum drawn from the
``SafetyEvent`` discriminated union — exactly the ``kind`` literal, never
any raw payload, PII, or moderation response body.

Contract reference:
  - specs/026-safety-rails/spec.md FR-019 (one attribute per safety decision)
  - specs/026-safety-rails/spec.md FR-020 (no raw PII in spans)
  - Upstream #501 contract: span attribute-only; no new exporter introduced here.
"""

from __future__ import annotations

from opentelemetry.trace import Span, get_current_span

from kosmos.safety._models import SafetyEvent

_ATTRIBUTE_NAME = "gen_ai.safety.event"


def emit_safety_event(event: SafetyEvent, span: Span | None = None) -> None:
    """Set ``gen_ai.safety.event`` on *span* (or the current active span).

    Args:
        event: A ``SafetyEvent`` discriminated-union instance.  Only its
            ``kind`` field is written to the span; no raw payload, PII, or
            vendor response body is ever attached.
        span: The target span.  When *None* the current active span is used
            via :func:`opentelemetry.trace.get_current_span`.

    Returns:
        ``None``.  If the resolved span is not recording, this function
        returns without side effect.
    """
    if span is None:
        span = get_current_span()

    if not span.is_recording():
        return

    # FR-019: exactly one attribute — the bounded enum kind, nothing else.
    span.set_attribute(_ATTRIBUTE_NAME, event.kind)
