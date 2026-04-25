# SPDX-License-Identifier: Apache-2.0
"""Canonical PIPA §26 trustee acknowledgment text extraction + SHA-256.

Source-of-truth file: ``docs/plugins/security-review.md``.

Pattern (per Spec 026 prompt-registry precedent):

1. The Markdown file holds the canonical text between
   ``<!-- CANONICAL-PIPA-ACK-START -->`` and
   ``<!-- CANONICAL-PIPA-ACK-END -->`` HTML-comment markers.
2. This module extracts the text, normalizes whitespace, computes
   SHA-256, and exposes ``CANONICAL_ACKNOWLEDGMENT_SHA256`` as a
   module-level constant computed at import time.
3. ``PluginManifest`` (in ``manifest_schema``) compares each plugin's
   ``acknowledgment_sha256`` against this constant; mismatch raises
   :class:`AcknowledgmentMismatchError`.

When the legal team approves a new acknowledgment text, the markers
move and this constant naturally changes; previously-merged plugins
report stale hashes (caught by the deferred drift-audit workflow,
issue #1926).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

_SECURITY_REVIEW_PATH: Final[Path] = (
    Path(__file__).resolve().parents[3] / "docs" / "plugins" / "security-review.md"
)
_START_MARKER: Final[str] = "<!-- CANONICAL-PIPA-ACK-START -->"
_END_MARKER: Final[str] = "<!-- CANONICAL-PIPA-ACK-END -->"


class CanonicalAcknowledgmentLoadError(RuntimeError):
    """Raised when the canonical text cannot be loaded.

    Indicates a misconfigured repo (missing markers, missing file) — should
    fail at import time so the platform never starts with an unknown
    acknowledgment surface.
    """


def _load_security_review_md(path: Path = _SECURITY_REVIEW_PATH) -> str:
    if not path.is_file():
        raise CanonicalAcknowledgmentLoadError(
            f"docs/plugins/security-review.md not found at {path}"
        )
    return path.read_text(encoding="utf-8")


def _extract_canonical_text(md: str) -> str:
    """Extract the canonical PIPA §26 text from the security-review markdown.

    The markdown legitimately mentions the marker token several times in
    prose (table cells, step procedure text) — those mentions are always
    wrapped in inline-code backticks so they sit mid-line. The ACTUAL
    canonical block places the markers on their own lines. We require
    the standalone-line form (newline boundaries on both sides) so prose
    mentions cannot contaminate extraction.

    Whitespace normalisation: strip leading/trailing whitespace and
    convert CRLF to LF so the SHA-256 is platform-stable.
    """
    normalized = md.replace("\r\n", "\n")
    # Markers must be on their own line — i.e. preceded by '\n' and
    # followed by '\n'. Search those exact byte sequences.
    start_token = "\n" + _START_MARKER + "\n"
    end_token = "\n" + _END_MARKER + "\n"
    start = normalized.find(start_token)
    end = normalized.find(end_token)
    if start == -1 or end == -1 or end <= start:
        raise CanonicalAcknowledgmentLoadError(
            "Canonical PIPA acknowledgment markers not found in "
            "docs/plugins/security-review.md. Both "
            f"{_START_MARKER!r} and {_END_MARKER!r} must appear on "
            "their own line — prose mentions inside backticks are "
            "intentionally ignored."
        )
    raw = normalized[start + len(start_token) : end]
    return raw.strip()


def _compute_canonical_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


CANONICAL_ACKNOWLEDGMENT_TEXT: Final[str] = _extract_canonical_text(
    _load_security_review_md()
)
"""Frozen canonical PIPA §26 trustee acknowledgment text.

Loaded from ``docs/plugins/security-review.md`` at import time.
"""

CANONICAL_ACKNOWLEDGMENT_SHA256: Final[str] = _compute_canonical_hash(
    CANONICAL_ACKNOWLEDGMENT_TEXT
)
"""SHA-256 hash of the canonical acknowledgment text.

Plugin manifests' ``acknowledgment_sha256`` field MUST equal this value.
"""


__all__ = [
    "CANONICAL_ACKNOWLEDGMENT_SHA256",
    "CANONICAL_ACKNOWLEDGMENT_TEXT",
    "CanonicalAcknowledgmentLoadError",
]
