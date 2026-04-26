# SPDX-License-Identifier: Apache-2.0
"""Token estimation utilities for KOSMOS Query Engine.

The FriendliAI EXAONE tokenizer is not publicly available, so this module
provides a character-based heuristic for pre-processing decisions.  Actual
token counts are obtained from the LLM API for budget accounting.
"""

from __future__ import annotations

import math


def estimate_tokens(text: str) -> int:
    """Estimate token count using character-based heuristic.

    Korean Hangul syllables (U+AC00-U+D7A3): ~2 characters per token.
    Other text (English, punctuation, numbers, etc.): ~4 characters per token.

    Args:
        text: Input text to estimate.

    Returns:
        Estimated token count (always >= 0).
    """
    if not text:
        return 0

    korean_count = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
    other_count = len(text) - korean_count
    return math.ceil(korean_count / 2 + other_count / 4)
