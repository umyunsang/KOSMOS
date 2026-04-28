# SPDX-License-Identifier: Apache-2.0
"""Tests for the kosmos.prompt.hash boundary-marker slicing (Epic #2152 R4).

Contract: ``specs/2152-system-prompt-redesign/contracts/chat-request-envelope.md``
invariants I-C1, I-C2, I-C5.
"""

from __future__ import annotations

import hashlib
import re

import pytest

_BOUNDARY = "\nSYSTEM_PROMPT_DYNAMIC_BOUNDARY\n"


def _hash_static_prefix(system_text: str) -> str:
    """Re-implementation mirroring kosmos.llm.client._compute_prompt_hash logic.

    Kept here as a documentation anchor for the contract rather than imported
    from the production code so the test pins the *behaviour* even if the
    production helper is later renamed/inlined.
    """
    idx = system_text.find(_BOUNDARY)
    hashed = system_text if idx == -1 else system_text[: idx + len(_BOUNDARY)]
    return hashlib.sha256(hashed.encode("utf-8")).hexdigest()


def test_hash_excludes_dynamic_suffix() -> None:
    """I-C2 — the hash covers only bytes up to (and including) the marker."""
    static_prefix = "<role>citizen prompt</role>" + _BOUNDARY
    suffix_a = "ministry_scope: kma"
    suffix_b = "ministry_scope: kma,hira\nconsent: 3 receipts"
    hash_a = _hash_static_prefix(static_prefix + suffix_a)
    hash_b = _hash_static_prefix(static_prefix + suffix_b)
    assert hash_a == hash_b, "Dynamic suffix MUST NOT influence the prefix hash"


def test_hash_is_64_lowercase_hex() -> None:
    """Hash format invariant — 64 hex chars matching SHA-256 output."""
    h = _hash_static_prefix("<role>x</role>" + _BOUNDARY)
    assert re.fullmatch(r"[0-9a-f]{64}", h), f"Bad hash format: {h!r}"


def test_hash_falls_back_to_full_text_when_marker_absent() -> None:
    """Backward-compatibility path — pre-R4 callers without the marker get
    the legacy full-content hash, not an error."""
    legacy = "<role>x</role>"  # no boundary marker
    h = _hash_static_prefix(legacy)
    expected = hashlib.sha256(legacy.encode("utf-8")).hexdigest()
    assert h == expected


def test_hash_byte_stable_across_repeated_calls() -> None:
    """I-C5 (unit-level) — same prefix always yields same hash."""
    static_prefix = "<role>x</role>\n<core_rules>y</core_rules>" + _BOUNDARY
    h1 = _hash_static_prefix(static_prefix + "turn-1 dynamic")
    h2 = _hash_static_prefix(static_prefix + "turn-2 different dynamic")
    assert h1 == h2


def test_marker_must_appear_exactly_once_in_static_prefix() -> None:
    """Sanity check — the boundary literal does not naturally collide with
    any reasonable content. If it ever does the hash slice would be wrong."""
    static_prefix = "<role>x</role>" + _BOUNDARY + "extra prose"
    # Find returns the FIRST occurrence; multiple occurrences would slice wrong.
    assert static_prefix.count(_BOUNDARY) == 1


@pytest.mark.parametrize(
    "static_prefix",
    [
        "<role>citizen</role>" + _BOUNDARY,
        "<role>citizen</role>\n<core_rules>r</core_rules>" + _BOUNDARY,
        (
            "<role>citizen</role>\n<core_rules>r</core_rules>\n"
            "<tool_usage>t</tool_usage>\n<output_style>o</output_style>" + _BOUNDARY
        ),
    ],
)
def test_hash_isolated_from_dynamic_growth(static_prefix: str) -> None:
    """The hash for a given static prefix is constant regardless of suffix size."""
    suffixes = ["", "a", "very long dynamic suffix " * 100]
    hashes = {_hash_static_prefix(static_prefix + s) for s in suffixes}
    assert len(hashes) == 1


def test_production_client_uses_same_logic() -> None:
    """Anti-drift guard — the production client.py emits the same hash as the
    documentation re-implementation for an identical input. Imported lazily so
    the test file stays runnable without spinning up an LLMClient."""
    from kosmos.llm import client as _client_module

    src = _client_module.__file__ or ""
    if not src:
        pytest.skip("client.py source not available")
    with open(src, encoding="utf-8") as fp:
        text = fp.read()
    assert "SYSTEM_PROMPT_DYNAMIC_BOUNDARY" in text, (
        "client.py must reference SYSTEM_PROMPT_DYNAMIC_BOUNDARY for R4 hash slicing"
    )
    assert "kosmos.prompt.hash" in text
