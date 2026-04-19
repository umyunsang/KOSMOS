# SPDX-License-Identifier: Apache-2.0
"""Integration test — fail-closed on external edit (T041).

Covers FR-C02: externally corrupt ``permissions.json`` → boot must refuse to
load, fall back to ``default`` mode with all rules cleared.

Test cases:
  1. Invalid JSON (cannot parse)
  2. Wrong schema_version (const "1.0.0" violated)
  3. Missing required field ``rules``
  4. Extra fields not allowed by ``additionalProperties: false``
  5. Rule with invalid ``decision`` value
  6. Rule with invalid ``tool_id`` pattern
  7. File with wrong permissions (not 0o600) — raises RuleStorePermissionsError
  8. Rule with extra properties (additionalProperties: false on rule object)
  9. Schema version mismatch (e.g. "2.0.0")
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest

from kosmos.permissions.rules import (
    RuleStore,
    RuleStorePermissionsError,
)
from kosmos.permissions.session_boot import SessionBootState, reset_session_state

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_store_mode_600(path: Path, content: bytes) -> None:
    """Write *content* to *path* with mode 0o600."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)


def _valid_store_bytes(rules: list[dict] | None = None) -> bytes:
    """Return a minimal valid permissions.json as UTF-8 bytes."""
    doc = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(tz=UTC).isoformat(),
        "rules": rules or [],
    }
    return json.dumps(doc, ensure_ascii=False).encode("utf-8")


def _write_valid_store(path: Path) -> None:
    _write_store_mode_600(path, _valid_store_bytes())


def _assert_fail_closed(boot_state: SessionBootState) -> None:
    """Assert the boot state reflects FR-C02 fail-closed behavior."""
    assert boot_state.rules_loaded is False
    assert boot_state.mode == "default", "M3/PR1: mode must be 'default' even on failure"
    assert boot_state.failed_reason is not None
    assert boot_state.user_rule_count == 0


# ---------------------------------------------------------------------------
# FR-C02: invalid JSON
# ---------------------------------------------------------------------------


class TestFailClosedInvalidJSON:
    """FR-C02: permissions.json is not parseable JSON → fail closed."""

    def test_truncated_json(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        _write_store_mode_600(store_path, b'{"schema_version": "1.0.0", "rules": [{')  # truncated

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_completely_invalid_json(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        _write_store_mode_600(store_path, b"NOT_JSON_AT_ALL")

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_empty_file(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        _write_store_mode_600(store_path, b"")

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_json_array_at_root(self, tmp_path: Path) -> None:
        """Root must be object, not array."""
        store_path = tmp_path / "permissions.json"
        _write_store_mode_600(store_path, b"[]")

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)


# ---------------------------------------------------------------------------
# FR-C02: schema version mismatch
# ---------------------------------------------------------------------------


class TestFailClosedSchemaVersion:
    """FR-C02: schema_version != '1.0.0' → fail closed."""

    def test_wrong_schema_version(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        doc = {"schema_version": "2.0.0", "rules": []}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_missing_schema_version(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        doc = {"rules": []}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_null_schema_version(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        doc = {"schema_version": None, "rules": []}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)


# ---------------------------------------------------------------------------
# FR-C02: missing required top-level fields
# ---------------------------------------------------------------------------


class TestFailClosedMissingRequiredFields:
    """FR-C02: required fields (schema_version, rules) missing → fail closed."""

    def test_missing_rules(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        doc = {"schema_version": "1.0.0"}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)


# ---------------------------------------------------------------------------
# FR-C02: extra fields (additionalProperties: false)
# ---------------------------------------------------------------------------


class TestFailClosedExtraFields:
    """FR-C02: additionalProperties: false — extra top-level fields → fail closed."""

    def test_extra_top_level_field(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        doc = {
            "schema_version": "1.0.0",
            "rules": [],
            "INJECTED_FIELD": "bad actor",  # not permitted
        }
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_extra_field_on_rule_object(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "kma_forecast_fetch",
            "decision": "allow",
            "scope": "user",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "default",
            "expires_at": None,
            "EVIL_EXTRA": "injected",  # not permitted
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)


# ---------------------------------------------------------------------------
# FR-C02: invalid rule field values
# ---------------------------------------------------------------------------


class TestFailClosedInvalidRuleValues:
    """FR-C02: invalid rule field values → fail closed."""

    def test_invalid_decision_value(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "kma_forecast_fetch",
            "decision": "maybe",  # invalid enum
            "scope": "user",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "default",
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_invalid_tool_id_pattern(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "INVALID-UPPER_CASE",  # uppercase not allowed
            "decision": "allow",
            "scope": "user",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "default",
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_invalid_scope_value(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "kma_forecast_fetch",
            "decision": "allow",
            "scope": "global",  # invalid
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "default",
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_invalid_mode_value(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "kma_forecast_fetch",
            "decision": "allow",
            "scope": "user",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "superPower",  # invalid
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_missing_required_rule_field(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "kma_forecast_fetch",
            # missing decision
            "scope": "user",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "default",
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_tool_id_too_long(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "a" * 129,  # exceeds 128-char limit
            "decision": "allow",
            "scope": "user",
            "created_at": datetime.now(tz=UTC).isoformat(),
            "created_by_mode": "default",
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)

    def test_invalid_created_at_format(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"
        rule = {
            "tool_id": "kma_forecast_fetch",
            "decision": "allow",
            "scope": "user",
            "created_at": "not-a-date",  # invalid
            "created_by_mode": "default",
        }
        doc = {"schema_version": "1.0.0", "rules": [rule]}
        _write_store_mode_600(store_path, json.dumps(doc).encode())

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)


# ---------------------------------------------------------------------------
# Invariant C3: wrong file permissions
# ---------------------------------------------------------------------------


class TestFailClosedWrongFileMode:
    """Invariant C3: file mode != 0o600 → RuleStorePermissionsError."""

    @pytest.mark.parametrize("bad_mode", [0o644, 0o666, 0o777, 0o400, 0o640])
    def test_wrong_mode_raises_permissions_error(
        self, tmp_path: Path, bad_mode: int
    ) -> None:
        store_path = tmp_path / "permissions.json"
        # Write valid content first
        store_path.write_bytes(_valid_store_bytes())
        # Then change to a bad mode
        os.chmod(str(store_path), bad_mode)

        store = RuleStore(store_path)
        with pytest.raises(RuleStorePermissionsError, match="0o600"):
            store.load()

    def test_wrong_mode_boot_fails_closed(self, tmp_path: Path) -> None:
        """reset_session_state fails closed and returns rules_loaded=False on mode error."""
        store_path = tmp_path / "permissions.json"
        store_path.write_bytes(_valid_store_bytes())
        os.chmod(str(store_path), 0o644)  # too permissive

        boot = reset_session_state(store_path)
        _assert_fail_closed(boot)
        assert "0o600" in boot.failed_reason  # type: ignore[operator]

    def test_correct_mode_loads_successfully(self, tmp_path: Path) -> None:
        """Correct mode 0o600 allows successful load (positive control)."""
        store_path = tmp_path / "permissions.json"
        _write_store_mode_600(store_path, _valid_store_bytes())

        boot = reset_session_state(store_path)
        assert boot.rules_loaded is True
        assert boot.mode == "default"


# ---------------------------------------------------------------------------
# Positive: valid store after corrupt boot
# ---------------------------------------------------------------------------


class TestRecoveryAfterCorruption:
    """After corruption, fixing the file allows a clean boot on next restart."""

    def test_corrupt_then_fix_then_boot(self, tmp_path: Path) -> None:
        store_path = tmp_path / "permissions.json"

        # 1. Write corrupted file
        _write_store_mode_600(store_path, b"CORRUPT_DATA")

        boot_bad = reset_session_state(store_path)
        assert boot_bad.rules_loaded is False

        # 2. Fix the file (simulates user repairing or harness resetting it)
        _write_store_mode_600(store_path, _valid_store_bytes())

        boot_good = reset_session_state(store_path)
        assert boot_good.rules_loaded is True
        assert boot_good.mode == "default"
        assert boot_good.user_rule_count == 0

    def test_absent_file_is_not_an_error(self, tmp_path: Path) -> None:
        """Absent permissions.json is valid (first-run): boot succeeds with 0 rules."""
        store_path = tmp_path / "permissions.json"
        assert not store_path.exists()

        boot = reset_session_state(store_path)
        assert boot.rules_loaded is True
        assert boot.mode == "default"
        assert boot.user_rule_count == 0
        assert boot.failed_reason is None
