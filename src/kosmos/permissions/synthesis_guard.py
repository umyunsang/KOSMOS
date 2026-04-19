# SPDX-License-Identifier: Apache-2.0
"""LLM synthesis boundary — PII redaction guard — Spec 033 T050 (WS4).

Implements ``redact()`` — the synthesis boundary enforced BEFORE adapter output
is assembled into the LLM prompt.  Fields tagged ``pipa_class ∈ {민감, 고유식별}``
are dropped from the adapter output mapping.

Invariant C5 (LLM synthesis boundary):
    ``redact()`` MUST drop 민감/고유식별 fields BEFORE the LLM ever sees the
    adapter output.  This is the controller-level carve-out described in
    MEMORY ``project_pipa_role`` — KOSMOS acts as a PIPA §26 수탁자 (processor)
    by default, but the LLM synthesis step is the single controller-level
    decision point where the data controller determines what personal data
    can enter the AI's context window.

FR-E02 compliance:
    AI 기본법 §27 requires that high-impact AI systems are designed so that
    sensitive personal data is not inadvertently included in the AI's training
    or inference context.  Dropping 민감/고유식별 fields here enforces this
    at the code level.

Field classification:
    The adapter output schema encodes pipa_class per field via metadata attached
    to the ``AdapterPermissionMetadata``.  In the absence of per-field metadata
    (e.g. when the adapter returns a flat dict), the module falls back to a
    key-name heuristic scan defined in ``_SENSITIVE_KEY_PATTERNS``.

Preserved fields:
    - ``pipa_class ∈ {일반, 개인식별}`` — general + personal identifier fields
      that are safe to include in the LLM prompt context.

Dropped fields:
    - ``pipa_class ∈ {민감, 고유식별}`` — sensitive + unique identifier fields
      that MUST NOT enter the LLM context (FR-E02, Invariant C5).

Reference:
    specs/033-permission-v2-spectrum/spec.md §FR-E01, §FR-E02
    specs/033-permission-v2-spectrum/data-model.md § 1.7 (controller carve-out)
    MEMORY project_pipa_role — PIPA §26 수탁자 default + LLM carve-out
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping
from typing import Any

from kosmos.permissions.models import AdapterPermissionMetadata

__all__ = ["redact", "SynthesisRedactionLog"]

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# PIPA classes that must be redacted before LLM synthesis (Invariant C5)
# ---------------------------------------------------------------------------

_REDACT_CLASSES: frozenset[str] = frozenset({"민감", "고유식별"})
"""Fields tagged with these PIPA classes are dropped before LLM context assembly.

PIPA classifications:
    민감 (sensitive)    — PIPA §23 sensitive data (health, political views, etc.)
    고유식별 (unique ID) — PIPA §24 unique identifiers (RRN, passport, etc.)

These are NOT forwarded to the LLM (FR-E02, Invariant C5, MEMORY project_pipa_role).
The remaining classes (일반, 특수) are forwarded subject to other pipeline
controls (killswitch blocks 특수 at a higher layer — it does not reach synthesis).
"""

# ---------------------------------------------------------------------------
# Key-name heuristic patterns for field-level PIPA classification
# (fallback when adapter output has no per-field metadata)
# ---------------------------------------------------------------------------

_SENSITIVE_KEY_PATTERNS: list[re.Pattern[str]] = [
    # Health / medical data (민감 — PIPA §23)
    re.compile(r"(diagnosis|health|medical|disease|treatment|prescription)", re.IGNORECASE),
    re.compile(r"(진단|병명|의료|건강|처방|수술|입원|처방전)", re.IGNORECASE),
    # Unique identifiers (고유식별 — PIPA §24)
    re.compile(r"(resident|rrn|jumin|passport|passport_no|driver_license)", re.IGNORECASE),
    re.compile(r"(주민|여권|운전면허|외국인등록)", re.IGNORECASE),
    # Biometrics (민감)
    re.compile(r"(biometric|fingerprint|retina|face_id)", re.IGNORECASE),
    re.compile(r"(지문|홍채|안면)", re.IGNORECASE),
    # Financial sensitive (민감)
    re.compile(r"(credit_score|bankruptcy|loan_delinquency)", re.IGNORECASE),
    re.compile(r"(신용등급|파산|연체)", re.IGNORECASE),
]
"""Heuristic key-name patterns for fallback sensitive field detection.

Used when the adapter output dict has no per-field ``pipa_class`` annotation.
These patterns catch common Korean public-service field names that typically
contain PIPA §23/§24 data.

Note: These patterns are conservative — they may produce false positives.
False positives are acceptable (redacting a non-sensitive field is safe);
false negatives (missing a truly sensitive field) are not.
"""


class SynthesisRedactionLog:
    """Immutable record of what was redacted from an adapter output.

    Used for audit trail and debug logging.  Not persisted to disk.
    """

    __slots__ = ("tool_id", "redacted_keys", "total_keys", "pipa_class")

    def __init__(
        self,
        tool_id: str,
        redacted_keys: frozenset[str],
        total_keys: int,
        pipa_class: str,
    ) -> None:
        self.tool_id = tool_id
        self.redacted_keys = redacted_keys
        self.total_keys = total_keys
        self.pipa_class = pipa_class

    def __repr__(self) -> str:
        return (
            f"SynthesisRedactionLog(tool_id={self.tool_id!r}, "
            f"pipa_class={self.pipa_class!r}, "
            f"redacted={sorted(self.redacted_keys)!r}, "
            f"total={self.total_keys})"
        )


def redact(
    adapter_output: Mapping[str, Any],
    adapter_metadata: AdapterPermissionMetadata,
) -> dict[str, Any]:
    """Redact PII fields from adapter output before LLM prompt assembly.

    Drops all fields from ``adapter_output`` whose keys match either:
    1. Per-field ``pipa_class`` annotation (if embedded in the value as
       ``{"__pipa_class__": "민감", "value": ...}``), OR
    2. Key-name heuristic patterns in ``_SENSITIVE_KEY_PATTERNS`` (fallback).

    Additionally, if ``adapter_metadata.pipa_class ∈ {민감, 고유식별}``, the
    ENTIRE adapter output is redacted and an empty dict is returned.  This
    is the strictest interpretation of Invariant C5: if the adapter itself
    is classified as sensitive, nothing from its output should reach the LLM.

    Invariant C5 guarantee:
        The returned dict MUST NOT contain any key that maps to PIPA 민감 or
        고유식별 data.  This guarantee is enforced by this function and is
        audited at test time by ``tests/permissions/test_synthesis_guard.py``.

    Args:
        adapter_output: The raw dict-like output from the adapter.
        adapter_metadata: The frozen adapter permission metadata.  Used to
            determine the adapter-level pipa_class for bulk redaction.

    Returns:
        A new plain dict with sensitive fields removed.  Non-sensitive fields
        are passed through unchanged.  An empty dict is returned when the
        entire adapter is classified as sensitive/unique-identifier-bearing.

    Raises:
        TypeError: If ``adapter_output`` is not a ``Mapping``.
    """
    if not isinstance(adapter_output, Mapping):
        raise TypeError(f"adapter_output must be a Mapping, got {type(adapter_output).__name__!r}")

    tool_id = adapter_metadata.tool_id
    adapter_pipa_class = adapter_metadata.pipa_class

    # Fast path: if the adapter itself is classified as 민감 or 고유식별,
    # drop the entire output (Invariant C5 — controller carve-out).
    if adapter_pipa_class in _REDACT_CLASSES:
        _logger.warning(
            "synthesis_guard.redact: adapter %r has pipa_class=%r — "
            "entire output redacted before LLM context assembly (C5).",
            tool_id,
            adapter_pipa_class,
        )
        return {}

    # Field-level scan: drop any key that matches sensitive patterns.
    result: dict[str, Any] = {}
    redacted_keys: set[str] = set()

    for key, value in adapter_output.items():
        # Check for inline __pipa_class__ annotation in the value.
        if isinstance(value, dict) and "__pipa_class__" in value:
            field_class = value["__pipa_class__"]
            if field_class in _REDACT_CLASSES:
                _logger.info(
                    "synthesis_guard.redact: tool_id=%r dropping field %r "
                    "(inline pipa_class=%r, C5).",
                    tool_id,
                    key,
                    field_class,
                )
                redacted_keys.add(key)
                continue
            # Strip the annotation before forwarding to LLM.
            result[key] = value.get("value", value)
            continue

        # Heuristic key-name scan (fallback).
        if _is_sensitive_key(key):
            _logger.info(
                "synthesis_guard.redact: tool_id=%r dropping field %r "
                "(key-name heuristic match, C5).",
                tool_id,
                key,
            )
            redacted_keys.add(key)
            continue

        result[key] = value

    if redacted_keys:
        _logger.info(
            "synthesis_guard.redact: tool_id=%r redacted %d/%d fields: %r",
            tool_id,
            len(redacted_keys),
            len(adapter_output),
            sorted(redacted_keys),
        )
    else:
        _logger.debug(
            "synthesis_guard.redact: tool_id=%r no fields redacted (%d total).",
            tool_id,
            len(adapter_output),
        )

    return result


def _is_sensitive_key(key: str) -> bool:
    """Return True if ``key`` matches any of the sensitive key-name patterns."""
    return any(pattern.search(key) for pattern in _SENSITIVE_KEY_PATTERNS)
