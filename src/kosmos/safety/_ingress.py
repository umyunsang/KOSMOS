# SPDX-License-Identifier: Apache-2.0
"""Ingress safety adaptor — glue between the Tool System and Layers A + C.

Called from ``kosmos.tools.executor`` immediately after the adapter returns its
raw output and immediately before ``normalize()`` (FR-006, FR-013).

Ordering (FR-013):
  1. Run :func:`kosmos.safety._injection.run_detector` on the serialised
     adapter output.  If the combined score meets the block threshold, return
     an ``InjectionBlockedEvent`` — the caller MUST short-circuit with
     ``make_error_envelope(reason=LookupErrorReason.injection_detected, ...)``.
  2. Else, if ``SafetySettings.redact_tool_output`` is true, walk the dict
     leaves and pass each string through :func:`kosmos.safety._redactor.run_redactor`.
     Return a ``(redacted_dict, RedactedEvent)`` tuple when at least one match
     was redacted; otherwise the event is ``None`` and the dict is returned
     unchanged.

FR-020: the returned event carries only bounded metadata (match count /
signal summary).  Raw PII and raw tool output never leave this function.

Defense-in-depth note (T037, commit 50e2c17):
  The per-file log redactions in ``kosmos.llm.client`` (``reasoning_content``
  length-only logging; ``tool_call_delta.arguments`` metadata-only logging)
  and ``kosmos.tools.executor`` (``raw_args_len``-only logging on validation
  failure) remain in force *independently* of this ingress layer.  Layer A
  here redacts the payload that flows INTO the LLM context window; the 50e2c17
  logging redactions prevent the same payload from leaking into log
  aggregators via debug/warning lines.  The two layers intentionally overlap
  — removing either one regresses PII exposure.  Do not delete or weaken the
  50e2c17 log redactions when modifying this module.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from kosmos.safety._injection import run_detector
from kosmos.safety._models import (
    InjectionBlockedEvent,
    RedactedEvent,
)
from kosmos.safety._redactor import run_redactor
from kosmos.safety._settings import SafetySettings

logger = logging.getLogger(__name__)


def _redact_leaves(value: Any, total_matches: list[int]) -> Any:
    """Recursively redact string leaves in a dict / list structure.

    ``total_matches`` is a single-element list used as an out-parameter so the
    caller can aggregate match counts without threading tuples through every
    recursion level.
    """
    if isinstance(value, str):
        result = run_redactor(value)
        total_matches[0] += len(result.matches)
        return result.redacted_text
    if isinstance(value, dict):
        return {k: _redact_leaves(v, total_matches) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_leaves(item, total_matches) for item in value]
    return value


def apply_ingress_safety(
    raw_output: dict[str, Any],
    settings: SafetySettings,
) -> tuple[dict[str, Any] | None, InjectionBlockedEvent | RedactedEvent | None]:
    """Apply detector + redactor to *raw_output*.

    Args:
        raw_output: The dict returned by the adapter handler.
        settings: The resolved ``SafetySettings`` instance controlling
            ``injection_detector_enabled`` and ``redact_tool_output``.

    Returns:
        ``(None, InjectionBlockedEvent)`` when the detector blocks — the
        caller MUST abort normalisation and emit an ``injection_detected``
        error envelope.
        ``(redacted_dict, RedactedEvent)`` when at least one PII match was
        redacted.
        ``(raw_output, None)`` when the output is clean and no redaction
        applied.
    """
    # Layer C — injection detection (FR-013 ordering: detector runs first).
    if settings.injection_detector_enabled:
        try:
            probe = json.dumps(raw_output, ensure_ascii=False, default=str)
        except (TypeError, ValueError):
            # Fall back to repr for non-JSON-serialisable payloads.  Detection
            # still runs; the raw value never leaves the function body.
            probe = repr(raw_output)
        signals = run_detector(probe)
        if signals.decision == "block":
            logger.warning(
                "safety.ingress: injection detector blocked output "
                "(structural=%.3f entropy=%.3f length_dev=%.3f)",
                signals.structural_score,
                signals.entropy_score,
                signals.length_deviation,
            )
            return (None, InjectionBlockedEvent(signal_summary=signals))

    # Layer A — PII redaction on string leaves (FR-006, FR-007).
    if settings.redact_tool_output:
        counter: list[int] = [0]
        redacted = _redact_leaves(raw_output, counter)
        if counter[0] > 0:
            logger.info("safety.ingress: redactor replaced %d PII match(es)", counter[0])
            return (redacted, RedactedEvent(match_count=counter[0]))
        return (redacted, None)

    return (raw_output, None)
