# SPDX-License-Identifier: Apache-2.0
"""Unit tests for kosmos.engine.tokens.estimate_tokens."""

from __future__ import annotations

import pytest

from kosmos.engine.tokens import estimate_tokens

# ---------------------------------------------------------------------------
# Parametrized happy-path cases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected",
    [
        # Empty string must return 0 (fast-path guard)
        ("", 0),
        # Pure English: "hello" (5 chars) → ceil(0/2 + 5/4) = ceil(1.25) = 2
        ("hello", 2),
        # Pure Korean: "안녕하세요" (5 syllables) → ceil(5/2 + 0/4) = ceil(2.5) = 3
        ("안녕하세요", 3),
        # Mixed: "서울 Seoul" → korean=2, other=6(" Seoul") → ceil(2/2 + 6/4) = ceil(1+1.5) = 3
        ("서울 Seoul", 3),
        # Single Korean character: "가" → ceil(1/2) = 1
        ("가", 1),
        # Single English character: "a" → ceil(0/2 + 1/4) = ceil(0.25) = 1
        ("a", 1),
        # Numbers and punctuation: "123!@#" (6 non-Korean chars) → ceil(6/4) = 2
        ("123!@#", 2),
        # Whitespace only: "   " (3 spaces) → ceil(3/4) = 1
        ("   ", 1),
    ],
    ids=[
        "empty_string",
        "pure_english",
        "pure_korean",
        "mixed_korean_english",
        "single_korean_char",
        "single_english_char",
        "numbers_and_punctuation",
        "whitespace_only",
    ],
)
def test_estimate_tokens_parametrized(text: str, expected: int) -> None:
    """estimate_tokens returns the expected token count for basic inputs."""
    assert estimate_tokens(text) == expected


# ---------------------------------------------------------------------------
# Korean Unicode boundary tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "char, should_be_korean",
    [
        # U+AC00 — first Hangul syllable block character ("가")
        ("\uac00", True),
        # U+D7A3 — last Hangul syllable block character ("힣")
        ("\ud7a3", True),
        # U+ABFF — one code-point before the Hangul syllable block
        ("\uabff", False),
        # U+D7A4 — one code-point after the Hangul syllable block
        ("\ud7a4", False),
    ],
    ids=[
        "boundary_start_ac00",
        "boundary_end_d7a3",
        "just_before_korean_range",
        "just_after_korean_range",
    ],
)
def test_korean_boundary_classification(char: str, should_be_korean: bool) -> None:
    """Characters on and around the Hangul syllable block boundary are classified correctly.

    A Korean character contributes ceil(1/2) = 1 token.
    A non-Korean character contributes ceil(1/4) = 1 token.
    Both yield 1 for a single-character input, so we verify by testing a pair
    where the difference in count is observable.

    Strategy: pass two copies of the character.
    - Two Korean chars → ceil(2/2 + 0/4) = 1
    - Two non-Korean chars → ceil(0/2 + 2/4) = 1
    Because both branches give 1 for a two-char input we must check an
    odd-count scenario to distinguish:
    - Three Korean chars → ceil(3/2) = ceil(1.5) = 2
    - Three non-Korean chars → ceil(3/4) = ceil(0.75) = 1
    """
    triple = char * 3
    result = estimate_tokens(triple)
    if should_be_korean:
        # Three Korean syllables: ceil(3/2) = 2
        assert result == 2, f"Expected 2 for three Korean chars, got {result}"
    else:
        # Three non-Korean chars: ceil(3/4) = 1
        assert result == 1, f"Expected 1 for three non-Korean chars, got {result}"


# ---------------------------------------------------------------------------
# Realistic long mixed-text scenario
# ---------------------------------------------------------------------------


def test_estimate_tokens_long_mixed_text() -> None:
    """estimate_tokens returns a positive integer for a realistic mixed-language sentence."""
    # A realistic query a user might send to KOSMOS.
    text = "서울특별시 강남구 교통사고 현황을 조회해 주세요. (Seoul Gangnam traffic)"
    result = estimate_tokens(text)
    # We don't hardcode the exact number; we verify structural correctness.
    assert isinstance(result, int)
    assert result > 0
    # Sanity: result should be well below the raw character count (heuristic compresses)
    assert result < len(text)


# ---------------------------------------------------------------------------
# Return-type and non-negativity invariants
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "",
        "a",
        "가",
        "hello world",
        "안녕하세요 Hello 123!",
        "   \t\n",
    ],
    ids=[
        "empty",
        "single_ascii",
        "single_korean",
        "english_sentence",
        "full_mixed",
        "whitespace_variants",
    ],
)
def test_estimate_tokens_returns_non_negative_int(text: str) -> None:
    """estimate_tokens always returns a non-negative int for any input."""
    result = estimate_tokens(text)
    assert isinstance(result, int)
    assert result >= 0
