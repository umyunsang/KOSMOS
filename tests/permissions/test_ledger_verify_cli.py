# SPDX-License-Identifier: Apache-2.0
"""Contract tests for ``kosmos-permissions verify`` — V-matrix scenarios.

Covers all 12 scenarios from contracts/ledger-verify.cli.md §7:

  V01: 5 records, all valid → exit 0
  V02: 0 records (empty file) → exit 5
  V03: Missing file → exit 5
  V04: 5 records, flip byte in record 2 purpose → exit 1 (CHAIN_RECORD_HASH_MISMATCH)
  V05: 5 records, flip byte in record 2 hmac_seal → exit 2 (HMAC_SEAL_MISMATCH)
  V06: 5 records, delete record 3 → exit 1 (CHAIN_PREV_HASH_MISMATCH)
  V07: 5 records, swap records 2 and 3 → exit 1 (CHAIN_PREV_HASH_MISMATCH)
  V08: 5 records, record 3 references key k9999 → exit 3 (HMAC_KEY_UNKNOWN)
  V09: 5 records, record 2 has invalid schema → exit 4 (SCHEMA_VIOLATION)
  V10: HMAC key file mode = 0644 → exit 6
  V11: 5 records, --hash-only --acknowledge-key-loss → exit 0 or 1
  V12: Usage error: --hash-only without --acknowledge-key-loss → exit 64

Reference: specs/033-permission-v2-spectrum/contracts/ledger-verify.cli.md §7
"""

from __future__ import annotations

import hashlib
import hmac as hmac_lib
import json
import os
from datetime import UTC
from pathlib import Path

import pytest

from kosmos.permissions.canonical_json import canonicalize
from kosmos.permissions.ledger_verify import verify_ledger

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GENESIS = "0" * 64


def _make_valid_records(
    n: int,
    key: bytes,
    key_id: str = "k0001",
) -> list[dict]:
    """Build a list of n valid, properly chained, HMAC-sealed ledger records."""
    from datetime import datetime

    records = []
    prev_hash = _GENESIS
    for i in range(n):
        record: dict = {
            "version": "1.0.0",
            "sequence": i,
            "recorded_at": datetime.now(tz=UTC).isoformat(),
            "tool_id": "test_tool",
            "mode": "default",
            "granted": True,
            "action_digest": hashlib.sha256(f"action_{i}".encode()).hexdigest(),
            "prev_hash": prev_hash,
            "record_hash": _GENESIS,  # placeholder
            "hmac_seal": _GENESIS,  # placeholder
            "key_id": key_id,
        }
        # Compute record_hash (excluding record_hash and hmac_seal).
        hashable = {k: v for k, v in record.items() if k not in ("record_hash", "hmac_seal")}
        record_hash = hashlib.sha256(canonicalize(hashable)).hexdigest()
        # Compute HMAC seal.
        hmac_seal = hmac_lib.new(key, record_hash.encode("ascii"), "sha256").hexdigest()
        record["record_hash"] = record_hash
        record["hmac_seal"] = hmac_seal
        prev_hash = record_hash
        records.append(record)
    return records


def _write_records(path: Path, records: list[dict]) -> None:
    """Write records as NDJSON to path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")


def _make_key_and_registry(tmp_dir: Path, key_id: str = "k0001") -> tuple[Path, Path]:
    """Create a 32-byte HMAC key with mode 0400 and a registry file."""
    keys_dir = tmp_dir / "keys"
    keys_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    key_path = keys_dir / "ledger.key"
    key_bytes = b"\xab" * 32  # deterministic test key
    fd = os.open(str(key_path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o400)
    try:
        os.write(fd, key_bytes)
    finally:
        os.close(fd)

    registry_path = keys_dir / "registry.json"
    registry = [{"key_id": key_id, "retired_at": None, "file_path": "ledger.key"}]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    return key_path, registry_path


def _test_key_bytes() -> bytes:
    return b"\xab" * 32


# ---------------------------------------------------------------------------
# V01 — 5 valid records → exit 0
# ---------------------------------------------------------------------------


def test_v01_five_valid_records(tmp_path: Path) -> None:
    """V01: 5 records, all valid. Expected exit code 0."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())
    _write_records(ledger_path, records)

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 0
    assert report.passed is True
    assert report.total_records == 5
    assert report.first_broken_index is None
    assert report.broken_reason is None


# ---------------------------------------------------------------------------
# V02 — Empty file → exit 5
# ---------------------------------------------------------------------------


def test_v02_empty_file(tmp_path: Path) -> None:
    """V02: Empty ledger file. Expected exit code 5 (FILE_EMPTY)."""
    _, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    ledger_path.touch()  # 0 bytes

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 5
    assert report.passed is False
    assert report.total_records == 0


# ---------------------------------------------------------------------------
# V03 — Missing file → exit 5
# ---------------------------------------------------------------------------


def test_v03_missing_file(tmp_path: Path) -> None:
    """V03: Missing ledger file. Expected exit code 5 (FILE_NOT_FOUND)."""
    _, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "nonexistent.jsonl"

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 5
    assert report.passed is False


# ---------------------------------------------------------------------------
# V04 — Flip byte in record 2 purpose → exit 1 (CHAIN_RECORD_HASH_MISMATCH)
# ---------------------------------------------------------------------------


def test_v04_flip_byte_in_purpose(tmp_path: Path) -> None:
    """V04: Flip byte in record 2's purpose field. Expected exit 1."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())
    _write_records(ledger_path, records)

    # Read the NDJSON, tamper record at index 2 (0-based).
    lines = ledger_path.read_text("utf-8").splitlines()
    rec2 = json.loads(lines[2])
    # Flip a character in tool_id (simulating purpose field tamper).
    original_tool = rec2["tool_id"]
    rec2["tool_id"] = original_tool[:-1] + ("X" if original_tool[-1] != "X" else "Y")
    lines[2] = json.dumps(rec2, ensure_ascii=False, separators=(",", ":"))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 1
    assert report.passed is False
    assert report.broken_reason == "CHAIN_RECORD_HASH_MISMATCH"
    assert report.first_broken_index == 2


# ---------------------------------------------------------------------------
# V05 — Flip byte in record 2 hmac_seal → exit 2 (HMAC_SEAL_MISMATCH)
# ---------------------------------------------------------------------------


def test_v05_flip_hmac_seal(tmp_path: Path) -> None:
    """V05: Flip a byte in record 2's hmac_seal. Expected exit 2."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())
    _write_records(ledger_path, records)

    # Tamper only the hmac_seal of record 2; leave all other fields intact.
    lines = ledger_path.read_text("utf-8").splitlines()
    rec2 = json.loads(lines[2])
    original_seal = rec2["hmac_seal"]
    # Flip the first hex char.
    flipped = ("1" if original_seal[0] != "1" else "2") + original_seal[1:]
    rec2["hmac_seal"] = flipped
    lines[2] = json.dumps(rec2, ensure_ascii=False, separators=(",", ":"))
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 2
    assert report.passed is False
    assert report.broken_reason == "HMAC_SEAL_MISMATCH"
    assert report.first_broken_index == 2


# ---------------------------------------------------------------------------
# V06 — Delete record 3 → exit 1 (CHAIN_PREV_HASH_MISMATCH)
# ---------------------------------------------------------------------------


def test_v06_delete_record_3(tmp_path: Path) -> None:
    """V06: Delete record 3 (0-based). Expected exit 1 (CHAIN_PREV_HASH_MISMATCH)."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())
    _write_records(ledger_path, records)

    # Remove record at index 3.
    lines = ledger_path.read_text("utf-8").splitlines(keepends=False)
    del lines[3]
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 1
    assert report.passed is False
    assert report.broken_reason == "CHAIN_PREV_HASH_MISMATCH"


# ---------------------------------------------------------------------------
# V07 — Swap records 2 and 3 → exit 1 (CHAIN_PREV_HASH_MISMATCH)
# ---------------------------------------------------------------------------


def test_v07_swap_records_2_and_3(tmp_path: Path) -> None:
    """V07: Swap records 2 and 3. Expected exit 1 (CHAIN_PREV_HASH_MISMATCH)."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())
    _write_records(ledger_path, records)

    lines = ledger_path.read_text("utf-8").splitlines(keepends=False)
    # Swap lines 2 and 3.
    lines[2], lines[3] = lines[3], lines[2]
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 1
    assert report.passed is False
    assert report.broken_reason in ("CHAIN_PREV_HASH_MISMATCH", "CHAIN_RECORD_HASH_MISMATCH")


# ---------------------------------------------------------------------------
# V08 — Record 3 references unknown key k9999 → exit 3 (HMAC_KEY_UNKNOWN)
# ---------------------------------------------------------------------------


def test_v08_unknown_key_id(tmp_path: Path) -> None:
    """V08: Record 3 uses key k9999 not in registry. Expected exit 3."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())

    # Manually set key_id of record 3 to unknown value.
    # We must recompute record_hash / hmac_seal with the new key_id so that
    # the chain and record_hash checks pass — only the key lookup should fail.
    rec = dict(records[3])
    rec["key_id"] = "k9999"
    # Recompute record_hash with new key_id included.
    hashable = {k: v for k, v in rec.items() if k not in ("record_hash", "hmac_seal")}
    new_record_hash = hashlib.sha256(canonicalize(hashable)).hexdigest()
    # Sign with the unknown key (verifier won't have it, so exit 3).
    unknown_key = b"\xff" * 32
    new_hmac = hmac_lib.new(unknown_key, new_record_hash.encode("ascii"), "sha256").hexdigest()
    rec["record_hash"] = new_record_hash
    rec["hmac_seal"] = new_hmac
    records[3] = rec

    # Fix record 4's prev_hash to point to the new record 3 hash.
    rec4 = dict(records[4])
    rec4["prev_hash"] = new_record_hash
    # Recompute record 4's hashes.
    hashable4 = {k: v for k, v in rec4.items() if k not in ("record_hash", "hmac_seal")}
    new_hash4 = hashlib.sha256(canonicalize(hashable4)).hexdigest()
    new_hmac4 = hmac_lib.new(_test_key_bytes(), new_hash4.encode("ascii"), "sha256").hexdigest()
    rec4["record_hash"] = new_hash4
    rec4["hmac_seal"] = new_hmac4
    records[4] = rec4

    _write_records(ledger_path, records)

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 3
    assert report.passed is False
    assert report.broken_reason == "KEY_MISSING"
    assert report.first_broken_index == 3


# ---------------------------------------------------------------------------
# V09 — Record 2 has invalid schema → exit 4 (SCHEMA_VIOLATION)
# ---------------------------------------------------------------------------


def test_v09_schema_violation(tmp_path: Path) -> None:
    """V09: Record 2 has invalid schema. Expected exit 4."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(5, _test_key_bytes())
    _write_records(ledger_path, records)

    # Replace record 2 with an invalid JSON object (missing required fields).
    lines = ledger_path.read_text("utf-8").splitlines(keepends=False)
    invalid_record = {"version": "1.0.0", "sequence": 2, "invalid_field_only": True}
    lines[2] = json.dumps(invalid_record, ensure_ascii=False)
    ledger_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 4
    assert report.passed is False
    assert report.broken_reason == "SCHEMA_VIOLATION"
    assert report.first_broken_index == 2


# ---------------------------------------------------------------------------
# V10 — HMAC key file mode = 0644 → exit 6
# ---------------------------------------------------------------------------


def test_v10_key_file_mode_mismatch(tmp_path: Path) -> None:
    """V10: HMAC key file mode 0644 instead of 0400. Expected exit 6."""
    from kosmos.permissions.hmac_key import HMACKeyFileModeError

    keys_dir = tmp_path / "keys"
    keys_dir.mkdir(mode=0o700, parents=True)
    key_path = keys_dir / "ledger.key"

    # Write key with wrong mode (0644).
    key_path.write_bytes(b"\xab" * 32)
    os.chmod(key_path, 0o644)

    registry_path = keys_dir / "registry.json"
    registry = [{"key_id": "k0001", "retired_at": None, "file_path": "ledger.key"}]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")

    ledger_path = tmp_path / "ledger.jsonl"
    # Build records with a fresh properly-moded key for writing.
    records = _make_valid_records(5, b"\xab" * 32)
    _write_records(ledger_path, records)

    # verify_ledger will call load_or_generate_key which raises HMACKeyFileModeError.
    with pytest.raises(HMACKeyFileModeError):
        verify_ledger(
            ledger_path=ledger_path,
            key_registry_path=registry_path,
        )


# ---------------------------------------------------------------------------
# V11 — --hash-only --acknowledge-key-loss → exit 0 or 1 (HMAC skipped)
# ---------------------------------------------------------------------------


def test_v11_hash_only_acknowledge_key_loss(tmp_path: Path) -> None:
    """V11: --hash-only --acknowledge-key-loss. Expected exit 0 (valid chain)."""
    # No key needed at all — using hash_only mode.
    keys_dir = tmp_path / "keys"
    keys_dir.mkdir(mode=0o700, parents=True)
    registry_path = keys_dir / "registry.json"
    registry_path.write_text("[]", encoding="utf-8")

    ledger_path = tmp_path / "ledger.jsonl"
    # Use a key to build valid records (hash chain is intact).
    records = _make_valid_records(5, b"\xab" * 32)
    _write_records(ledger_path, records)

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
        hash_only=True,
        acknowledge_key_loss=True,
    )

    # Chain is intact → exit 0.
    assert report.exit_code == 0
    assert report.passed is True


# Note: V12 CLI test removed in Epic δ #2295 — kosmos.permissions.cli deleted as
# Spec 033 KOSMOS-invented residue. The CLI gate logic is not part of Spec 035
# receipt set.
# References: specs/2295-backend-permissions-cleanup/spec.md § FR-001

# ---------------------------------------------------------------------------
# Additional: single-record ledger (V01 variant with 1 record)
# ---------------------------------------------------------------------------


def test_single_record_valid(tmp_path: Path) -> None:
    """Single record ledger with genesis prev_hash → exit 0."""
    key_path, registry_path = _make_key_and_registry(tmp_path)
    ledger_path = tmp_path / "ledger.jsonl"
    records = _make_valid_records(1, _test_key_bytes())
    _write_records(ledger_path, records)

    report = verify_ledger(
        ledger_path=ledger_path,
        key_registry_path=registry_path,
    )

    assert report.exit_code == 0
    assert report.total_records == 1
    # Verify the genesis prev_hash is "0" * 64.
    lines = ledger_path.read_text("utf-8").splitlines()
    rec = json.loads(lines[0])
    assert rec["prev_hash"] == "0" * 64
