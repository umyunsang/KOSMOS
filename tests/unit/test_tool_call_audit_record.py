# SPDX-License-Identifier: Apache-2.0
"""Unit tests for ToolCallAuditRecord — schema, invariants, and performance.

Covers:
- (a) Minimum-valid record round-trip via model_dump / model_validate.
- (b) Invariant I1: sanitized_output_hash ↔ merkle_covered_hash consistency.
- (c) Invariant I2: public_path_marker → check_eligibility + AAL1 + non_personal.
- (d) Invariant I3: pipa_class != non_personal → dpa_reference non-null.
- (e) Invariant I4: naive datetime rejected; timezone-aware accepted.
- (f) Hex SHA-256 shape validation (64-char lowercase hex).
- (g) Field-shape constraints (empty strings, negative cost_tokens, bad tool_id).
- (h) JSON Schema validation of the three worked examples from §6 of the normative spec.
- (perf) model_validate < 5 ms per call, averaged over 1000 iterations.
"""

from __future__ import annotations

import json
import os
import time
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from kosmos.security.audit import ToolCallAuditRecord

# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

_VALID_HASH_A = "a" * 64  # lowercase hex, 64 chars — valid SHA-256 placeholder
_VALID_HASH_B = "b" * 64
_VALID_HASH_C = "c" * 64
_VALID_TS = datetime(2026, 4, 17, 10, 30, 0, tzinfo=UTC)

_SCHEMA_PATH = (
    __file__.replace("tests/unit/test_tool_call_audit_record.py", "")
    + "docs/security/tool-call-audit-record.schema.json"
)


def _abs_schema_path() -> str:
    """Return the absolute path to the JSON Schema artifact."""
    import pathlib

    repo_root = pathlib.Path(__file__).parent.parent.parent
    return str(repo_root / "docs" / "security" / "tool-call-audit-record.schema.json")


def _minimal_record(**overrides) -> dict:
    """Return a dict that satisfies every required field with valid values."""
    base = {
        "record_version": "v1",
        "tool_id": "lookup",
        "adapter_mode": "mock",
        "session_id": "session-001",
        "caller_identity": "citizen:abc123",
        "permission_decision": "allow",
        "auth_level_presented": "AAL1",
        "pipa_class": "non_personal",
        "dpa_reference": None,
        "input_hash": _VALID_HASH_A,
        "output_hash": _VALID_HASH_B,
        "sanitized_output_hash": None,
        "merkle_covered_hash": "output_hash",
        "merkle_leaf_id": None,
        "timestamp": _VALID_TS,
        "cost_tokens": 0,
        "rate_limit_bucket": "per-session",
        "public_path_marker": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# (a) Minimum-valid record round-trip
# ---------------------------------------------------------------------------


class TestMinimalRoundTrip:
    def test_construct_and_round_trip(self):
        record = ToolCallAuditRecord(**_minimal_record())
        dumped = record.model_dump()
        rehydrated = ToolCallAuditRecord.model_validate(dumped)
        assert record == rehydrated

    def test_all_required_fields_present(self):
        record = ToolCallAuditRecord(**_minimal_record())
        dumped = record.model_dump()
        required = [
            "record_version",
            "tool_id",
            "adapter_mode",
            "session_id",
            "caller_identity",
            "permission_decision",
            "auth_level_presented",
            "pipa_class",
            "input_hash",
            "output_hash",
            "merkle_covered_hash",
            "timestamp",
            "cost_tokens",
            "rate_limit_bucket",
            "public_path_marker",
        ]
        for field in required:
            assert field in dumped, f"Missing required field: {field}"


# ---------------------------------------------------------------------------
# (b) Invariant I1 — sanitized_output_hash ↔ merkle_covered_hash
# ---------------------------------------------------------------------------


class TestInvariantI1:
    def test_i1_sanitized_set_and_covered_by_sanitized(self):
        """(i) sanitized_output_hash=<hex> + merkle_covered_hash=sanitized_output_hash succeeds."""
        record = ToolCallAuditRecord(
            **_minimal_record(
                sanitized_output_hash=_VALID_HASH_C,
                merkle_covered_hash="sanitized_output_hash",
            )
        )
        assert record.sanitized_output_hash == _VALID_HASH_C
        assert record.merkle_covered_hash == "sanitized_output_hash"

    def test_i1_sanitized_set_but_covered_by_output_raises(self):
        """(ii) sanitized_output_hash=<hex> + merkle_covered_hash='output_hash' raises."""
        with pytest.raises(ValidationError, match="I1"):
            ToolCallAuditRecord(
                **_minimal_record(
                    sanitized_output_hash=_VALID_HASH_C,
                    merkle_covered_hash="output_hash",
                )
            )

    def test_i1_sanitized_none_and_covered_by_output(self):
        """(iii) sanitized_output_hash=None + merkle_covered_hash='output_hash' succeeds."""
        record = ToolCallAuditRecord(
            **_minimal_record(
                sanitized_output_hash=None,
                merkle_covered_hash="output_hash",
            )
        )
        assert record.sanitized_output_hash is None
        assert record.merkle_covered_hash == "output_hash"

    def test_i1_sanitized_none_but_covered_by_sanitized_raises(self):
        """(iv) sanitized_output_hash=None + merkle_covered_hash='sanitized_output_hash' raises."""
        with pytest.raises(ValidationError, match="I1"):
            ToolCallAuditRecord(
                **_minimal_record(
                    sanitized_output_hash=None,
                    merkle_covered_hash="sanitized_output_hash",
                )
            )


# ---------------------------------------------------------------------------
# (c) Invariant I2 — public_path_marker conjuncts
# ---------------------------------------------------------------------------


def _public_path_record(**overrides) -> dict:
    """Return a valid public-path record base dict."""
    base = _minimal_record(
        tool_id="check_eligibility",
        auth_level_presented="AAL1",
        pipa_class="non_personal",
        public_path_marker=True,
        dpa_reference=None,
    )
    base.update(overrides)
    return base


class TestInvariantI2:
    def test_i2_success(self):
        """All three conjuncts satisfied — should succeed."""
        record = ToolCallAuditRecord(**_public_path_record())
        assert record.public_path_marker is True
        assert record.tool_id == "check_eligibility"
        assert record.auth_level_presented == "AAL1"
        assert record.pipa_class == "non_personal"

    def test_i2_wrong_tool_id_raises(self):
        """public_path_marker=True with tool_id != 'check_eligibility' fails."""
        with pytest.raises(ValidationError, match="I2"):
            ToolCallAuditRecord(**_public_path_record(tool_id="lookup"))

    def test_i2_wrong_auth_level_raises(self):
        """public_path_marker=True with auth_level_presented != 'AAL1' fails."""
        with pytest.raises(ValidationError, match="I2"):
            ToolCallAuditRecord(**_public_path_record(auth_level_presented="AAL2"))

    def test_i2_wrong_pipa_class_raises(self):
        """public_path_marker=True with pipa_class != 'non_personal' fails.

        Note: personal pipa_class also triggers I3 (dpa_reference required),
        so we expect ValidationError to fire. Match on I2 is the first trigger
        when public_path_marker=True with wrong pipa_class.
        """
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(
                **_public_path_record(
                    pipa_class="personal",
                    dpa_reference="DPA-TEST-001",
                )
            )


# ---------------------------------------------------------------------------
# (d) Invariant I3 — pipa_class != non_personal → dpa_reference non-null
# ---------------------------------------------------------------------------


class TestInvariantI3:
    def test_i3_personal_without_dpa_raises(self):
        with pytest.raises(ValidationError, match="I3"):
            ToolCallAuditRecord(
                **_minimal_record(
                    pipa_class="personal",
                    dpa_reference=None,
                    auth_level_presented="AAL2",
                )
            )

    def test_i3_sensitive_without_dpa_raises(self):
        with pytest.raises(ValidationError, match="I3"):
            ToolCallAuditRecord(
                **_minimal_record(
                    pipa_class="sensitive",
                    dpa_reference=None,
                    auth_level_presented="AAL2",
                )
            )

    def test_i3_identifier_without_dpa_raises(self):
        with pytest.raises(ValidationError, match="I3"):
            ToolCallAuditRecord(
                **_minimal_record(
                    pipa_class="identifier",
                    dpa_reference=None,
                    auth_level_presented="AAL3",
                )
            )

    def test_i3_non_personal_without_dpa_succeeds(self):
        record = ToolCallAuditRecord(
            **_minimal_record(
                pipa_class="non_personal",
                dpa_reference=None,
            )
        )
        assert record.dpa_reference is None

    def test_i3_personal_with_dpa_succeeds(self):
        record = ToolCallAuditRecord(
            **_minimal_record(
                pipa_class="personal",
                dpa_reference="DPA-TEST-001",
                auth_level_presented="AAL2",
            )
        )
        assert record.dpa_reference == "DPA-TEST-001"


# ---------------------------------------------------------------------------
# (e) Invariant I4 — naive datetime rejected
# ---------------------------------------------------------------------------


class TestInvariantI4:
    def test_i4_naive_datetime_rejected(self):
        naive_ts = datetime(2026, 4, 17, 10, 30, 0)  # no tzinfo
        with pytest.raises(ValidationError, match="I4"):
            ToolCallAuditRecord(**_minimal_record(timestamp=naive_ts))

    def test_i4_aware_datetime_accepted(self):
        aware_ts = datetime(2026, 4, 17, 10, 30, 0, tzinfo=UTC)
        record = ToolCallAuditRecord(**_minimal_record(timestamp=aware_ts))
        assert record.timestamp.tzinfo is not None


# ---------------------------------------------------------------------------
# (f) Hex SHA-256 shape validation
# ---------------------------------------------------------------------------


class TestHexSha256Shape:
    @pytest.mark.parametrize("field", ["input_hash", "output_hash"])
    def test_uppercase_hex_rejected(self, field: str):
        bad_hash = "A" * 64
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(**{field: bad_hash}))

    @pytest.mark.parametrize("field", ["input_hash", "output_hash"])
    def test_63_chars_rejected(self, field: str):
        short = "a" * 63
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(**{field: short}))

    @pytest.mark.parametrize("field", ["input_hash", "output_hash"])
    def test_65_chars_rejected(self, field: str):
        long_ = "a" * 65
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(**{field: long_}))

    @pytest.mark.parametrize("field", ["input_hash", "output_hash"])
    def test_non_hex_chars_rejected(self, field: str):
        non_hex = "g" + "a" * 63
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(**{field: non_hex}))

    def test_sanitized_output_hash_uppercase_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(
                **_minimal_record(
                    sanitized_output_hash="A" * 64,
                    merkle_covered_hash="sanitized_output_hash",
                )
            )

    def test_sanitized_output_hash_63_chars_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(
                **_minimal_record(
                    sanitized_output_hash="a" * 63,
                    merkle_covered_hash="sanitized_output_hash",
                )
            )

    def test_sanitized_output_hash_65_chars_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(
                **_minimal_record(
                    sanitized_output_hash="a" * 65,
                    merkle_covered_hash="sanitized_output_hash",
                )
            )

    def test_sanitized_output_hash_non_hex_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(
                **_minimal_record(
                    sanitized_output_hash="z" + "a" * 63,
                    merkle_covered_hash="sanitized_output_hash",
                )
            )


# ---------------------------------------------------------------------------
# (g) Field-shape constraints
# ---------------------------------------------------------------------------


class TestFieldShapeConstraints:
    def test_empty_session_id_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(session_id=""))

    def test_empty_caller_identity_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(caller_identity=""))

    def test_empty_rate_limit_bucket_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(rate_limit_bucket=""))

    def test_negative_cost_tokens_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(cost_tokens=-1))

    def test_tool_id_starting_with_uppercase_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(tool_id="Lookup"))

    def test_tool_id_starting_with_digit_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(tool_id="1lookup"))

    def test_tool_id_starting_with_hyphen_rejected(self):
        with pytest.raises(ValidationError):
            ToolCallAuditRecord(**_minimal_record(tool_id="-lookup"))


# ---------------------------------------------------------------------------
# (h) JSON Schema validation of the three worked examples
# ---------------------------------------------------------------------------

jsonschema = pytest.importorskip("jsonschema")

# The three worked examples from docs/security/tool-template-security-spec-v1.md §6.4
# Inline Python dicts (preferred over markdown extraction per task brief).

_EXAMPLE_1_ALLOW = {
    "record_version": "v1",
    "tool_id": "issue_certificate",
    "adapter_mode": "live",
    "session_id": "01jb8zk3v0000000deadbeefcafe0001",
    "caller_identity": "citizen:abc123",
    "permission_decision": "allow",
    "auth_level_presented": "AAL3",
    "pipa_class": "identifier",
    "dpa_reference": "DPA-MOIS-2026-01",
    "input_hash": "a3f1c2e4b5d6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2",
    "output_hash": "b4e2d3f5c6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3",
    "sanitized_output_hash": "c5f3e4a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4",
    "merkle_covered_hash": "sanitized_output_hash",
    "merkle_leaf_id": None,
    "timestamp": "2026-04-17T10:30:00+09:00",
    "cost_tokens": 0,
    "rate_limit_bucket": "per-session",
    "public_path_marker": False,
}

_EXAMPLE_2_DENY_AAL = {
    "record_version": "v1",
    "tool_id": "issue_certificate",
    "adapter_mode": "live",
    "session_id": "01jb8zk3v0000000deadbeefcafe0002",
    "caller_identity": "citizen:def456",
    "permission_decision": "deny_aal",
    "auth_level_presented": "AAL1",
    "pipa_class": "identifier",
    "dpa_reference": "DPA-MOIS-2026-01",
    "input_hash": "d6e4f5a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5",
    "output_hash": "e7f5a6b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6",
    "sanitized_output_hash": None,
    "merkle_covered_hash": "output_hash",
    "merkle_leaf_id": None,
    "timestamp": "2026-04-17T10:31:00+09:00",
    "cost_tokens": 0,
    "rate_limit_bucket": "per-session",
    "public_path_marker": False,
}

_EXAMPLE_3_PUBLIC_PATH = {
    "record_version": "v1",
    "tool_id": "check_eligibility",
    "adapter_mode": "mock",
    "session_id": "01jb8zk3v0000000deadbeefcafe0003",
    "caller_identity": "citizen:ghi789",
    "permission_decision": "allow",
    "auth_level_presented": "AAL1",
    "pipa_class": "non_personal",
    "dpa_reference": None,
    "input_hash": "f8a6b7c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7",
    "output_hash": "a9b7c8d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8",
    "sanitized_output_hash": None,
    "merkle_covered_hash": "output_hash",
    "merkle_leaf_id": None,
    "timestamp": "2026-04-17T10:32:00+09:00",
    "cost_tokens": 0,
    "rate_limit_bucket": "per-session",
    "public_path_marker": True,
}


class TestJsonSchemaValidation:
    @pytest.fixture(scope="class")
    def schema(self):
        import pathlib

        schema_path = (
            pathlib.Path(__file__).parent.parent.parent
            / "docs"
            / "security"
            / "tool-call-audit-record.schema.json"
        )
        with open(schema_path) as f:
            return json.load(f)

    def test_example1_allow_validates(self, schema):
        jsonschema.validate(instance=_EXAMPLE_1_ALLOW, schema=schema)

    def test_example2_deny_aal_validates(self, schema):
        jsonschema.validate(instance=_EXAMPLE_2_DENY_AAL, schema=schema)

    def test_example3_public_path_validates(self, schema):
        jsonschema.validate(instance=_EXAMPLE_3_PUBLIC_PATH, schema=schema)


# ---------------------------------------------------------------------------
# (perf) T014 — model_validate < 5 ms per call, averaged over 1000 iterations
# Source: data-model.md §3 (performance target: < 5 ms average per record)
# ---------------------------------------------------------------------------


@pytest.mark.performance
def test_model_validate_under_5ms_p_avg():
    """Assert ToolCallAuditRecord.model_validate averages under 5 ms per call.

    Source: data-model.md §3 — "model_validate target < 5 ms per record
    (validated in unit test, not enforced in schema)".

    The test skips when KOSMOS_SKIP_PERF=1 to allow CI on constrained runners
    to opt out without failing the suite.
    """
    if os.environ.get("KOSMOS_SKIP_PERF") == "1":
        pytest.skip("KOSMOS_SKIP_PERF=1 — skipping performance assertion")

    canonical = {
        "record_version": "v1",
        "tool_id": "lookup",
        "adapter_mode": "mock",
        "session_id": "perf-session-001",
        "caller_identity": "citizen:perf-test",
        "permission_decision": "allow",
        "auth_level_presented": "AAL1",
        "pipa_class": "non_personal",
        "dpa_reference": None,
        "input_hash": "a" * 64,
        "output_hash": "b" * 64,
        "sanitized_output_hash": None,
        "merkle_covered_hash": "output_hash",
        "merkle_leaf_id": None,
        "timestamp": _VALID_TS,
        "cost_tokens": 0,
        "rate_limit_bucket": "per-session",
        "public_path_marker": False,
    }

    iterations = 1000
    # Warm up (excluded from measurement)
    ToolCallAuditRecord.model_validate(canonical)

    start_ns = time.perf_counter_ns()
    for _ in range(iterations):
        ToolCallAuditRecord.model_validate(canonical)
    elapsed_ns = time.perf_counter_ns() - start_ns

    avg_ns = elapsed_ns / iterations
    budget_ns = 5_000_000  # 5 ms = 5,000,000 ns — from data-model.md §3

    assert avg_ns < budget_ns, (
        f"model_validate average {avg_ns / 1_000_000:.3f} ms exceeds 5 ms budget (data-model.md §3)"
    )
