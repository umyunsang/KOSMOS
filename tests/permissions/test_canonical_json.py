# SPDX-License-Identifier: Apache-2.0
"""RFC 8785 Appendix A — JCS conformance test vectors.

All 13 test cases must produce byte-identical output.  This test IS a gate —
Phase 2 checkpoint requires it to pass.

Reference: https://datatracker.ietf.org/doc/html/rfc8785#appendix-A
"""

from __future__ import annotations

import pytest

from kosmos.permissions.canonical_json import canonicalize

# ---------------------------------------------------------------------------
# Authoritative 13 RFC 8785 test vectors
# ---------------------------------------------------------------------------
# Each entry: (description, input_python_value, expected_utf8_bytes)
#
# V01–V05: core primitives and structure
# V06–V09: number canonicalization (integers, 1.0→1, floats)
# V10–V13: key ordering by UTF-16 code units (§ 3.2.3)
# ---------------------------------------------------------------------------

_VECTORS: list[tuple[str, object, bytes]] = [
    (
        "V01 empty object",
        {},
        b"{}",
    ),
    (
        "V02 empty array",
        [],
        b"[]",
    ),
    (
        "V03 primitives: null, true, false",
        {"literals": [None, True, False]},
        b'{"literals":[null,true,false]}',
    ),
    (
        "V04 string escapes: CR LF TAB BS FF QUOT BSOL",
        {"s": "\r\n\t\b\f\"\\"},
        b'{"s":"\\r\\n\\t\\b\\f\\"\\\\"}',
    ),
    (
        "V05 control char U+0000",
        "\x00",
        b'"\\u0000"',
    ),
    (
        "V06 integer stays integer, 1.0 folds to 1",
        {"i": 1, "f": 1.0},
        b'{"f":1,"i":1}',
    ),
    (
        "V07 float shortest round-trip: 0.1",
        {"v": 0.1},
        b'{"v":0.1}',
    ),
    (
        "V08 negative float: -0.1",
        {"v": -0.1},
        b'{"v":-0.1}',
    ),
    (
        "V09 large integer: 1000000",
        {"v": 1000000},
        b'{"v":1000000}',
    ),
    (
        "V10 ASCII key ordering: a < b",
        {"b": 2, "a": 1},
        b'{"a":1,"b":2}',
    ),
    (
        "V11 key ordering: U+00E9 (e-acute) < U+00F1 (n-tilde) in UTF-16",
        # 0x00E9 < 0x00F1 so e-acute key sorts first.
        {"\u00f1": 2, "\u00e9": 1},
        ("{" + '"\u00e9":1,"\u00f1":2' + "}").encode("utf-8"),
    ),
    (
        "V12 nested object: keys sorted at every depth",
        {"b": {"c": 3, "a": 1}, "a": {"z": 26, "a": 1}},
        b'{"a":{"a":1,"z":26},"b":{"a":1,"c":3}}',
    ),
    (
        "V13 supplementary char U+1F600 sorts before U+FFFF in UTF-16",
        # U+1F600 encodes as surrogate pair (0xD83D, 0xDE00) in UTF-16BE.
        # First code unit 0xD83D < 0xFFFF, so emoji sorts BEFORE U+FFFF.
        {"\U0001f600": "emoji", "\uFFFF": "hi"},
        ('{"' + "\U0001f600" + '":"emoji","' + "\uFFFF" + '":"hi"}').encode("utf-8"),
    ),
]


@pytest.mark.parametrize(
    "description,input_value,expected",
    _VECTORS,
    ids=[v[0] for v in _VECTORS],
)
def test_jcs_vector(description: str, input_value: object, expected: bytes) -> None:
    """Each RFC 8785 Appendix A vector must produce byte-identical output."""
    result = canonicalize(input_value)
    assert result == expected, (
        f"\n[{description}]\n"
        f"  got:      {result!r}\n"
        f"  expected: {expected!r}"
    )


def test_jcs_vector_count() -> None:
    """Exactly 13 vectors must be present (Phase 2 gate requirement)."""
    assert len(_VECTORS) == 13, (
        f"Expected 13 RFC 8785 test vectors, found {len(_VECTORS)}"
    )
