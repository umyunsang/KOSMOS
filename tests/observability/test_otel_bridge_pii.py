# SPDX-License-Identifier: Apache-2.0
"""T015 — Unit tests for filter_metadata() PII prefilter in otel_bridge.py.

Verifies:
- Only whitelisted keys pass through.
- PII keys (user_input, pii_email, payload) are dropped.
- Values are preserved exactly for whitelisted keys.
- Non-primitive values (dict, object) are dropped even if key is whitelisted.
- Output keys == _ALLOWED_METADATA_KEYS ∩ raw.keys().
"""

from __future__ import annotations

from kosmos.observability.event_logger import _ALLOWED_METADATA_KEYS
from kosmos.observability.otel_bridge import filter_metadata

# ---------------------------------------------------------------------------
# Reference input from task spec
# ---------------------------------------------------------------------------

_RAW: dict[str, object] = {
    "tool_id": "koroad_accident_search",
    "step": 1,
    "decision": "call",
    "user_input": "홍길동 010-1234-5678",
    "pii_email": "a@b.com",
    "model": "K-EXAONE",
    "payload": {"deep": "nested"},
    "error_class": "TimeoutError",
}

_EXPECTED_KEYS = {"tool_id", "step", "decision", "model", "error_class"}
_EXPECTED_VALUES = {
    "tool_id": "koroad_accident_search",
    "step": 1,
    "decision": "call",
    "model": "K-EXAONE",
    "error_class": "TimeoutError",
}


# ---------------------------------------------------------------------------
# T015-A: Output keys == whitelist ∩ raw.keys()
# ---------------------------------------------------------------------------


def test_filter_metadata_output_keys_match_whitelist_intersection() -> None:
    """Output keys must equal _ALLOWED_METADATA_KEYS ∩ raw.keys()."""
    result = filter_metadata(_RAW)

    expected = _ALLOWED_METADATA_KEYS & _RAW.keys()
    assert set(result.keys()) == expected, (
        f"Expected keys {expected}, got {set(result.keys())}"
    )
    assert set(result.keys()) == _EXPECTED_KEYS


# ---------------------------------------------------------------------------
# T015-B: PII keys are dropped
# ---------------------------------------------------------------------------


def test_filter_metadata_drops_user_input() -> None:
    """'user_input' must be dropped (not in whitelist)."""
    result = filter_metadata(_RAW)
    assert "user_input" not in result, (
        f"'user_input' must not appear in filtered output. Got keys: {set(result.keys())}"
    )


def test_filter_metadata_drops_pii_email() -> None:
    """'pii_email' must be dropped (not in whitelist)."""
    result = filter_metadata(_RAW)
    assert "pii_email" not in result, (
        f"'pii_email' must not appear in filtered output. Got keys: {set(result.keys())}"
    )


def test_filter_metadata_drops_payload() -> None:
    """'payload' (nested dict) must be dropped (not in whitelist + non-primitive)."""
    result = filter_metadata(_RAW)
    assert "payload" not in result, (
        f"'payload' must not appear in filtered output. Got keys: {set(result.keys())}"
    )


# ---------------------------------------------------------------------------
# T015-C: Values preserved exactly for whitelisted keys
# ---------------------------------------------------------------------------


def test_filter_metadata_preserves_whitelisted_values() -> None:
    """Whitelisted primitive values must be preserved unchanged."""
    result = filter_metadata(_RAW)
    for key, expected_val in _EXPECTED_VALUES.items():
        assert key in result, f"Expected key {key!r} in result"
        assert result[key] == expected_val, (
            f"Value mismatch for {key!r}: expected {expected_val!r}, got {result[key]!r}"
        )


# ---------------------------------------------------------------------------
# T015-D: Non-primitive values are dropped even when key is whitelisted
# ---------------------------------------------------------------------------


def test_filter_metadata_drops_dict_value_for_whitelisted_key() -> None:
    """A whitelisted key with a dict value must be dropped (non-primitive)."""
    raw = {
        "tool_id": {"nested": "oops"},  # whitelisted key, non-primitive value
        "step": 2,
    }
    result = filter_metadata(raw)
    assert "tool_id" not in result, (
        "Dict value under whitelisted key must be dropped"
    )
    assert result.get("step") == 2


def test_filter_metadata_drops_object_value() -> None:
    """A whitelisted key with an arbitrary object value must be dropped."""

    class _Opaque:
        pass

    raw: dict[str, object] = {
        "tool_id": _Opaque(),  # non-primitive
        "model": "K-EXAONE",
    }
    result = filter_metadata(raw)
    assert "tool_id" not in result, (
        "Object value under whitelisted key must be dropped"
    )
    assert result.get("model") == "K-EXAONE"


def test_filter_metadata_drops_list_of_mixed_types() -> None:
    """A list containing non-primitives must be dropped."""
    raw: dict[str, object] = {
        "tool_id": ["koroad", {"bad": True}],  # mixed list → drop
        "step": 3,
    }
    result = filter_metadata(raw)
    assert "tool_id" not in result, (
        "Mixed-type list under whitelisted key must be dropped"
    )
    assert result.get("step") == 3


def test_filter_metadata_accepts_homogeneous_primitive_list() -> None:
    """A homogeneous list of primitives under a whitelisted key is accepted."""
    raw: dict[str, object] = {
        "tool_id": ["a", "b", "c"],  # homogeneous str list → allowed
        "step": 1,
    }
    result = filter_metadata(raw)
    assert result.get("tool_id") == ["a", "b", "c"], (
        "Homogeneous primitive list must pass through"
    )


# ---------------------------------------------------------------------------
# T015-E: Full reference input — exact equality check
# ---------------------------------------------------------------------------


def test_filter_metadata_full_reference_input() -> None:
    """Full reference input from spec: output matches expected exactly."""
    result = filter_metadata(_RAW)

    assert result == _EXPECTED_VALUES, (
        f"filter_metadata output mismatch.\n"
        f"Expected: {_EXPECTED_VALUES}\n"
        f"Got:      {result}"
    )


# ---------------------------------------------------------------------------
# T015-F: Empty input / all-PII input → empty output
# ---------------------------------------------------------------------------


def test_filter_metadata_empty_input() -> None:
    """Empty dict input must produce empty dict output."""
    assert filter_metadata({}) == {}


def test_filter_metadata_all_pii_input() -> None:
    """Dict with only non-whitelisted keys must produce empty output."""
    raw: dict[str, object] = {
        "user_name": "홍길동",
        "phone": "010-1234-5678",
        "email": "user@example.com",
        "ssn": "900101-1234567",
    }
    result = filter_metadata(raw)
    assert result == {}, (
        f"Expected empty output for all-PII input, got: {result}"
    )


# ---------------------------------------------------------------------------
# T015-G: All whitelisted primitives pass through
# ---------------------------------------------------------------------------


def test_filter_metadata_all_allowed_primitives() -> None:
    """All _ALLOWED_METADATA_KEYS with primitive values must pass through."""
    raw: dict[str, object] = {
        "tool_id": "koroad_accident",
        "step": 5,
        "decision": "allow",
        "error_class": "TimeoutError",
        "model": "K-EXAONE",
    }
    result = filter_metadata(raw)
    assert set(result.keys()) == _ALLOWED_METADATA_KEYS
    assert result["tool_id"] == "koroad_accident"
    assert result["step"] == 5
    assert result["decision"] == "allow"
    assert result["error_class"] == "TimeoutError"
    assert result["model"] == "K-EXAONE"
