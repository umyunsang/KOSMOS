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

    Whitespace normalisation: strip leading/trailing whitespace and convert
    CRLF to LF so the SHA-256 is platform-stable.
    """
    start = md.find(_START_MARKER)
    end = md.find(_END_MARKER)
    if start == -1 or end == -1 or end <= start:
        raise CanonicalAcknowledgmentLoadError(
            "Canonical PIPA acknowledgment markers not found in "
            "docs/plugins/security-review.md. Expected "
            f"{_START_MARKER!r} ... {_END_MARKER!r}."
        )
    raw = md[start + len(_START_MARKER) : end]
    return raw.strip().replace("\r\n", "\n")


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
