# SPDX-License-Identifier: Apache-2.0
"""OTEL span emission helpers for the permission killswitch — Spec 033 T034 (WS4).

Provides ``emit_killswitch_span()`` which emits the
``permission.killswitch.triggered`` span using the OpenTelemetry SDK already
installed from Spec 021.

Span attributes follow the Spec 021 ``kosmos.*`` namespace convention:
    - ``kosmos.permission.killswitch.reason`` — the trigger reason
    - ``kosmos.permission.tool_id``           — the adapter that triggered the killswitch
    - ``kosmos.permission.mode``              — session mode at trigger time
    - ``kosmos.permission.correlation_id``   — Spec 032 IPC correlation id

All attributes are plain strings (no sensitive data).  This module uses
only ``opentelemetry.trace`` from the existing OTEL SDK installation.

Reference:
    specs/033-permission-v2-spectrum/spec.md FR-F03
    specs/033-permission-v2-spectrum/tasks.md T034
    Spec 021 — opentelemetry-sdk + opentelemetry-semantic-conventions
"""

from __future__ import annotations

import logging
from typing import Literal

from opentelemetry import trace

__all__ = ["emit_killswitch_span"]

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level tracer (Spec 021 convention: use __name__ as tracer name)
# ---------------------------------------------------------------------------

_tracer: trace.Tracer = trace.get_tracer(__name__)

# ---------------------------------------------------------------------------
# Span name constant (machine-readable, Spec 021 namespace)
# ---------------------------------------------------------------------------

_KILLSWITCH_SPAN_NAME: str = "permission.killswitch.triggered"
"""OpenTelemetry span name emitted whenever the killswitch fires."""


def emit_killswitch_span(
    reason: Literal["irreversible", "pipa_class_특수", "aal3"],
    tool_id: str,
    mode: str,
    correlation_id: str,
) -> None:
    """Emit a ``permission.killswitch.triggered`` OTEL span.

    Creates a new span (child of the current active span if one exists) with
    the provided killswitch context.  The span ends immediately after setting
    attributes — it is a point-in-time event, not a duration span.

    No PII is included in span attributes.  The ``reason`` encodes the
    structural trigger condition (invariant reference) rather than any
    citizen-identifying information.

    Args:
        reason: Machine-readable killswitch trigger reason:
            - ``"irreversible"``    — adapter.is_irreversible (K2)
            - ``"pipa_class_특수"`` — adapter.pipa_class == "특수" (K3)
            - ``"aal3"``            — adapter.auth_level == "AAL3" (K4)
        tool_id: The canonical adapter identifier that triggered the killswitch.
        mode: The session permission mode at the time of the trigger
            (e.g. ``"bypassPermissions"``).
        correlation_id: The Spec 032 IPC envelope correlation id for trace linkage.

    Returns:
        None.  Side effect: a completed OTEL span is exported via the
        configured exporter (if any — no-op tracer is fine for tests).
    """
    _logger.debug(
        "Emitting OTEL span %r: reason=%r tool_id=%r mode=%r correlation_id=%r",
        _KILLSWITCH_SPAN_NAME,
        reason,
        tool_id,
        mode,
        correlation_id,
    )

    with _tracer.start_as_current_span(_KILLSWITCH_SPAN_NAME) as span:
        span.set_attribute("kosmos.permission.killswitch.reason", reason)
        span.set_attribute("kosmos.permission.tool_id", tool_id)
        span.set_attribute("kosmos.permission.mode", mode)
        span.set_attribute("kosmos.permission.correlation_id", correlation_id)
        # Mark this span as an event (instantaneous) rather than a duration.
        span.add_event(
            "killswitch.fired",
            attributes={
                "reason": reason,
                "tool_id": tool_id,
            },
        )
