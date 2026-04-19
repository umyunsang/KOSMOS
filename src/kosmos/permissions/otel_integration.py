# SPDX-License-Identifier: Apache-2.0
"""Spec 021 OTEL span enrichment for Permission v2 — Spec 033 FR-F03.

Wires permission-layer OpenTelemetry attributes onto **already-active** tool-call
spans.  This module NEVER creates new spans — it only adds attributes to the
span that is currently recording when ``enrich_tool_call_span`` is called.

Attribute namespace (Spec 021 kosmos.* convention):
    ``kosmos.permission.mode``           — the PermissionMode string
    ``kosmos.permission.decision``       — "granted" or "denied"
    ``kosmos.consent.receipt_id``        — consent_receipt_id (when available)

Design constraints:
- NO new spans are created.  The caller (pipeline_v2.py) is responsible for
  opening a tool-call span before invoking ``enrich_tool_call_span``.
- When no span is recording (no-op tracer / CI with OTEL disabled), this
  function is a silent no-op — zero overhead on the hot path.
- ``consent`` may be ``None`` when the adapter did not require consent
  (e.g., public adapters in plan mode).  In that case ``decision`` is set
  to ``"not_required"`` and ``receipt_id`` is omitted.

Reference:
    specs/033-permission-v2-spectrum/spec.md §FR-F03
    specs/021-observability-otel-genai/spec.md §GenAI semconv v1.40
    src/kosmos/observability/semconv.py (KOSMOS attribute namespace)
    src/kosmos/permissions/models.py ConsentDecision, ToolPermissionContext
"""

from __future__ import annotations

import logging

from opentelemetry import trace

from kosmos.permissions.models import ConsentDecision, ToolPermissionContext

__all__ = [
    "KOSMOS_PERMISSION_MODE",
    "KOSMOS_PERMISSION_DECISION",
    "KOSMOS_CONSENT_RECEIPT_ID",
    "enrich_tool_call_span",
]

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Attribute-name constants (kosmos.permission.* namespace — Spec 033 FR-F03)
# ---------------------------------------------------------------------------

KOSMOS_PERMISSION_MODE: str = "kosmos.permission.mode"
"""Span attribute: current PermissionMode string at time of tool call.

Value: one of ``default``, ``plan``, ``acceptEdits``, ``bypassPermissions``,
``dontAsk`` (Spec 033 PermissionMode literals).
"""

KOSMOS_PERMISSION_DECISION: str = "kosmos.permission.decision"
"""Span attribute: the consent/permission decision for this call.

Values:
    ``"granted"``       — citizen granted consent (ConsentDecision.granted=True)
    ``"denied"``        — citizen refused consent (ConsentDecision.granted=False)
    ``"not_required"``  — adapter did not require explicit consent
"""

KOSMOS_CONSENT_RECEIPT_ID: str = "kosmos.consent.receipt_id"
"""Span attribute: Kantara Consent Receipt ID / action_digest.

Populated only when ``consent`` is non-null and ``granted=True``.
Value: 64-character hex SHA-256 action_digest from ConsentDecision.
"""


# ---------------------------------------------------------------------------
# Core enrichment function (T051)
# ---------------------------------------------------------------------------


def enrich_tool_call_span(
    span: trace.Span,
    ctx: ToolPermissionContext,
    consent: ConsentDecision | None,
) -> None:
    """Add permission-layer OTEL attributes to an already-active tool-call span.

    This function is a CONSUMER of Spec 021 OTEL infrastructure.  It calls
    ``span.set_attribute`` on the provided span object — it does NOT start,
    stop, or nest spans.

    The caller MUST pass the span that is currently recording for the tool call
    (typically obtained via ``trace.get_current_span()`` or the span handle
    from a ``tracer.start_as_current_span`` context manager).

    When ``span.is_recording()`` is False (no-op tracer, CI environment), all
    attribute-setting calls are no-ops — this function returns immediately with
    zero overhead.

    Attributes set:
    - ``kosmos.permission.mode``         — always set from ``ctx.mode``
    - ``kosmos.permission.decision``     — "granted" / "denied" / "not_required"
    - ``kosmos.consent.receipt_id``      — set only when consent is granted
      (action_digest from ConsentDecision)

    Args:
        span: The currently-recording OTEL span for the tool call.
            Must be non-None.  When ``is_recording()`` is False, the function
            exits immediately.
        ctx: The ToolPermissionContext for this invocation.  Provides the
            ``mode`` (PermissionMode) and ``tool_id`` for logging.
        consent: The ConsentDecision produced by the permission pipeline.
            Pass ``None`` when the adapter did not require explicit citizen
            consent (e.g., public/AAL1 adapters in plan mode).

    Returns:
        None.  Side effect: OTEL span attributes added when ``span.is_recording()``.
    """
    if not span.is_recording():
        return

    # FR-F03 — kosmos.permission.mode (always emitted)
    span.set_attribute(KOSMOS_PERMISSION_MODE, ctx.mode)

    # FR-F03 — kosmos.permission.decision
    if consent is None:
        decision_value = "not_required"
    elif consent.granted:
        decision_value = "granted"
    else:
        decision_value = "denied"

    span.set_attribute(KOSMOS_PERMISSION_DECISION, decision_value)

    # FR-F03 — kosmos.consent.receipt_id (only when consent was actively granted)
    if consent is not None and consent.granted:
        receipt_id = consent.action_digest
        if receipt_id:
            span.set_attribute(KOSMOS_CONSENT_RECEIPT_ID, receipt_id)
        else:
            _logger.warning(
                "otel_integration.missing_receipt_id: tool_id=%s "
                "consent.granted=True but action_digest is empty; "
                "kosmos.consent.receipt_id not set on span.",
                ctx.tool_id,
            )

    _logger.debug(
        "otel_integration.enriched: tool_id=%s mode=%s decision=%s",
        ctx.tool_id,
        ctx.mode,
        decision_value,
    )
