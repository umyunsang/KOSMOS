# SPDX-License-Identifier: Apache-2.0
"""Thin kiwipiepy wrapper for BM25 tokenization with deterministic output.

Korean text is tokenized using kiwipiepy morpheme analysis (POS-filtered:
NNG, NNP, VV, VA, SL). Non-Korean (ASCII-only) text falls back to
whitespace splitting.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Module-level lazy singleton — Kiwi startup is slow (~300 ms), load once.
_KIWI: object | None = None


def _get_kiwi() -> object:
    """Return (and lazily initialise) the module-level Kiwi singleton."""
    global _KIWI  # noqa: PLW0603
    if _KIWI is None:
        try:
            from kiwipiepy import Kiwi  # type: ignore[import-untyped]

            _KIWI = Kiwi()
            logger.debug("kiwipiepy Kiwi singleton initialised")
        except Exception as exc:  # pragma: no cover
            logger.warning("kiwipiepy unavailable — falling back to whitespace tokenizer: %s", exc)
            _KIWI = _FallbackTokenizer()
    return _KIWI


# POS tags to keep from kiwipiepy output (content-bearing tokens only).
_KEEP_POS: frozenset[str] = frozenset({"NNG", "NNP", "VV", "VA", "SL"})


def _is_ascii_only(text: str) -> bool:
    """Return True if every character in *text* is ASCII (code point < 128)."""
    return all(ord(c) < 128 for c in text)


class _FallbackTokenizer:
    """Minimal stand-in when kiwipiepy cannot be loaded."""

    def tokenize(self, text: str) -> list[object]:  # pragma: no cover
        return []  # callers check this only for Korean paths


def tokenize(text: str) -> list[str]:
    """Tokenize *text* for BM25 indexing.

    Behaviour:
    - If *text* contains only ASCII characters, lowercase and split on
      whitespace (English / numeric content, stable and cheap).
    - Otherwise, invoke kiwipiepy morpheme analysis and keep tokens whose
      POS tag is in ``_KEEP_POS`` (NNG, NNP, VV, VA, SL).

    The output is deterministic: same input always produces the same ordered
    list. Tokens are lowercased for case-insensitive BM25 matching.

    Args:
        text: Input string to tokenize.

    Returns:
        List of lowercase token strings.
    """
    stripped = text.strip()
    if not stripped:
        return []

    if _is_ascii_only(stripped):
        return stripped.lower().split()

    # Korean path — use kiwipiepy.
    kiwi = _get_kiwi()
    if isinstance(kiwi, _FallbackTokenizer):  # pragma: no cover
        # Degraded: fall back to whitespace split for Korean too.
        return stripped.lower().split()

    try:
        tokens: list[str] = []
        for token in kiwi.tokenize(stripped):
            if token.tag in _KEEP_POS:
                tokens.append(token.form.lower())
        return tokens
    except Exception as exc:  # pragma: no cover
        logger.warning("kiwipiepy.tokenize failed, falling back: %s", exc)
        return stripped.lower().split()
