# SPDX-License-Identifier: Apache-2.0
"""PII redactor — upstream ingress layer for LLM context sanitisation.

This module is the *new* upstream redaction layer introduced by
spec/026-safety-rails (commit 50e2c17 added per-file redactions inside
``llm/client.py`` and ``tools/executor.py``).  Those per-file redactions are
intentionally preserved as defense-in-depth; ``_redactor.py`` provides an
earlier, centralised pass before tool output ever reaches the normalisation
step.  The two layers are complementary, not redundant.

Public API
----------
``run_redactor(text: str) -> RedactionResult``
    Scan *text* for the five Korean PII categories (RRN, phone, email,
    passport, Luhn-valid credit card), replace each match with a placeholder
    token, and return an immutable ``RedactionResult``.

Presidio path (optional)
------------------------
If ``presidio_analyzer`` is importable the function builds an
``AnalyzerEngine`` with one ``PatternRecognizer`` per category and a stub
NLP engine so that only regex-level matching is used (no spaCy model is
required).  This path is active once T039 adds the dependency to
``pyproject.toml``.

Fallback path (current)
-----------------------
When Presidio is not installed the function falls back to iterating directly
over ``_PII_PATTERNS`` using ``re.Pattern.finditer``.  Both paths produce
identical ``RedactionMatch`` values.

Luhn gate
---------
After collecting ``credit_card`` regex matches the function applies
``luhn_valid()`` to strip false positives.  Only digit sequences that pass
the ISO/IEC 7812 checksum are redacted.  Luhn-invalid sequences survive in
``redacted_text`` unchanged and produce no ``RedactionMatch``.
"""

from __future__ import annotations

import logging
import re

from kosmos.safety._models import RedactionMatch, RedactionResult
from kosmos.safety._patterns import _PII_PATTERNS, luhn_valid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Category → placeholder token
# Keys match the exact dict keys used in ``_PII_PATTERNS``.
# ---------------------------------------------------------------------------

_PLACEHOLDER: dict[str, str] = {
    "rrn": "<RRN>",
    "phone_kr": "<PHONE_KR>",
    "email": "<EMAIL>",
    "passport_kr": "<PASSPORT_KR>",
    "credit_card": "<CREDIT_CARD>",
}

# ---------------------------------------------------------------------------
# Presidio optional import
# ---------------------------------------------------------------------------

try:
    from presidio_analyzer import (  # type: ignore[import-untyped]
        Pattern as PresidioPattern,
    )
    from presidio_analyzer import (
        PatternRecognizer,
    )

    _PRESIDIO_AVAILABLE = True
except ImportError:
    _PRESIDIO_AVAILABLE = False

# ---------------------------------------------------------------------------
# Presidio recognisers (built once, lazily)
#
# The spec requires Presidio ``PatternRecognizer`` as the enforcement class,
# but NOT the full ``AnalyzerEngine`` pipeline — ``AnalyzerEngine`` mandates a
# spaCy NlpEngine whose cold-start and per-call overhead blow past SC-003
# (p95 ≤ 50 ms on 100 kB).  ``PatternRecognizer.analyze()`` takes
# ``nlp_artifacts=None`` without complaint for pure-regex recognisers, so we
# instantiate the recognisers directly and invoke them without an NLP lane.
# ---------------------------------------------------------------------------

_recognizers: list[object] | None = None  # list[PatternRecognizer] | None


def _build_presidio_recognizers() -> list[object]:
    """Build one ``PatternRecognizer`` per PII category (no NLP engine).

    The registered patterns are all language-agnostic regexes (RRN digits,
    Korean phone in ``010-xxxx-xxxx`` form, email, passport, credit card).
    Language metadata is bookkeeping only.
    """
    recognizers: list[object] = []
    for category, pattern in _PII_PATTERNS.items():
        recognizers.append(
            PatternRecognizer(
                supported_entity=category,
                patterns=[
                    PresidioPattern(
                        name=f"{category}_pattern",
                        regex=pattern.pattern,
                        score=1.0,
                    )
                ],
                supported_language="en",
            )
        )
    return recognizers


# ---------------------------------------------------------------------------
# Core implementation helpers
# ---------------------------------------------------------------------------


def _collect_matches_via_regex(text: str) -> list[tuple[str, int, int]]:
    """Direct regex fallback: return (category, start, end) tuples."""
    raw: list[tuple[str, int, int]] = []
    for category, pattern in _PII_PATTERNS.items():
        for m in pattern.finditer(text):
            raw.append((category, m.start(), m.end()))
    return raw


def _collect_matches_via_presidio(text: str) -> list[tuple[str, int, int]]:
    """Presidio path: run each ``PatternRecognizer`` directly (no NLP lane)."""
    global _recognizers  # noqa: PLW0603
    if _recognizers is None:
        _recognizers = _build_presidio_recognizers()

    raw: list[tuple[str, int, int]] = []
    for recognizer in _recognizers:
        results = recognizer.analyze(  # type: ignore[attr-defined]
            text=text,
            entities=None,
            nlp_artifacts=None,
        )
        for r in results:
            raw.append((r.entity_type, r.start, r.end))
    return raw


def _apply_luhn_gate(
    raw: list[tuple[str, int, int]], text: str
) -> list[tuple[str, int, int]]:
    """Filter credit_card matches: keep only those that pass luhn_valid()."""
    filtered: list[tuple[str, int, int]] = []
    for category, start, end in raw:
        if category == "credit_card":
            digits = re.sub(r"\D", "", text[start:end])
            if not luhn_valid(digits):
                logger.debug(
                    "Luhn gate rejected credit_card match at [%d:%d]", start, end
                )
                continue
        filtered.append((category, start, end))
    return filtered


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_redactor(text: str) -> RedactionResult:
    """Scan *text* for PII, redact matches, and return a ``RedactionResult``.

    The result contains:
    - ``original_length``: character length of the input text.
    - ``redacted_text``: text with each PII span replaced by its placeholder.
    - ``redacted_length``: character length of the redacted text.
    - ``matches``: immutable tuple of ``RedactionMatch`` (category + offsets in
      the *original* text; no raw values are stored — FR-017).

    Processing order
    ----------------
    1. Collect all regex matches (via Presidio if available, else direct).
    2. Apply the Luhn gate for ``credit_card`` category.
    3. Sort matches in *reverse* start-offset order to allow in-place string
       surgery without offset drift.
    4. Build the redacted string and ``RedactionMatch`` objects.
    """
    if _PRESIDIO_AVAILABLE:
        raw = _collect_matches_via_presidio(text)
    else:
        raw = _collect_matches_via_regex(text)

    # Apply Luhn gate (no-op for non-credit-card categories).
    raw = _apply_luhn_gate(raw, text)

    # Deduplicate overlapping spans: keep the leftmost/longest in case of ties.
    # Sort by start ascending, then end descending (longest first).
    raw.sort(key=lambda t: (t[1], -(t[2])))
    deduped: list[tuple[str, int, int]] = []
    last_end = -1
    for category, start, end in raw:
        if start >= last_end:
            deduped.append((category, start, end))
            last_end = end

    # Build RedactionMatch objects (offsets into original text, no raw values).
    matches: list[RedactionMatch] = [
        RedactionMatch(category=cat, start=s, end=e)  # type: ignore[arg-type]
        for cat, s, e in deduped
    ]

    # Apply placeholder substitutions in reverse offset order.
    redacted = text
    for category, start, end in sorted(deduped, key=lambda t: t[1], reverse=True):
        placeholder = _PLACEHOLDER[category]
        redacted = redacted[:start] + placeholder + redacted[end:]

    return RedactionResult(
        original_length=len(text),
        redacted_length=len(redacted),
        matches=tuple(matches),
        redacted_text=redacted,
    )
