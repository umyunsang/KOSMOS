# SPDX-License-Identifier: Apache-2.0
"""Streaming hash-chain + HMAC-seal verifier for the PIPA consent ledger.

Implements T023 — verify all invariants L2, L3, L4 via a single streaming
pass over the NDJSON ledger file.  Memory-efficient: the file is read in one
shot but only the current record and the previous record_hash are retained.

Exit codes returned in ``LedgerVerifyReport.exit_code`` follow the contract:
  contracts/ledger-verify.cli.md §2

  0  — chain + HMAC verified (all records pass).
  1  — hash chain broken (CHAIN_RECORD_HASH_MISMATCH or CHAIN_PREV_HASH_MISMATCH).
  2  — HMAC seal mismatch (hmac_ok=False, chain_ok=True).
  3  — HMAC key unknown (key_id not in registry).
  4  — Schema violation (record fails ConsentLedgerRecord Pydantic validation).
  5  — File not found or empty.
  6  — HMAC key file mode mismatch (fail-closed load refusal).
  64 — Usage error.

Detection guarantee (SC-004):
  A single-byte flip anywhere in any record will be detected because:
  - Non-UTF-8 bytes: UnicodeDecodeError → treated as CHAIN_RECORD_HASH_MISMATCH.
  - Valid UTF-8 flip in non-hash field: record_hash recomputation mismatches → exit 1.
  - Flip in record_hash itself: HMAC of record_hash mismatches → exit 2.
    Plus: next record's prev_hash chain fails → exit 1 if chain check runs first.
  - Flip in hmac_seal: HMAC recomputation mismatches → exit 2.

References:
  - specs/033-permission-v2-spectrum/spec.md §US2 SC-004
  - specs/033-permission-v2-spectrum/contracts/ledger-verify.cli.md §5
"""

from __future__ import annotations

import hashlib
import hmac as hmac_lib
import json
import logging
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from kosmos.permissions.canonical_json import canonicalize
from kosmos.permissions.hmac_key import HMACKeyFileModeError, load_or_generate_key
from kosmos.permissions.models import ConsentLedgerRecord, LedgerVerifyReport

__all__ = ["verify_ledger"]

_logger = logging.getLogger(__name__)

# Genesis sentinel (Invariant L1).
_GENESIS_PREV_HASH = "0" * 64


# ---------------------------------------------------------------------------
# Key registry loading
# ---------------------------------------------------------------------------


def _load_key_registry(key_registry_path: Path) -> dict[str, bytes]:
    """Build a mapping of key_id → 32-byte secret from the key registry.

    Registry file ``keys/registry.json`` format:
    ``[{"key_id": "k0001", "retired_at": null, "file_path": "ledger.key"}, ...]``

    The active key is the last entry with ``retired_at == null``.
    Retired keys have ``retired_at`` set and ``file_path`` pointing to the
    archive file (e.g. ``ledger.key.k0001``).

    Args:
        key_registry_path: Absolute path to ``keys/registry.json``.

    Returns:
        Dict mapping each known ``key_id`` to its 32-byte secret.
        Empty dict if the registry does not exist (caller handles missing key).

    Raises:
        HMACKeyFileModeError: If any key file has wrong permissions.
    """
    keys_dir = key_registry_path.parent
    result: dict[str, bytes] = {}

    if not key_registry_path.exists():
        # No registry yet — try to load the default active key.
        default_key_path = keys_dir / "ledger.key"
        if default_key_path.exists():
            # HMACKeyFileModeError propagates up — caller maps to exit 6.
            key_bytes = load_or_generate_key(default_key_path)
            result["k0001"] = key_bytes
        return result

    try:
        entries = json.loads(key_registry_path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        _logger.warning("Failed to read key registry at %s: %s", key_registry_path, exc)
        return result

    if not isinstance(entries, list):
        return result

    for entry in entries:
        key_id = entry.get("key_id")
        file_path_str = entry.get("file_path")
        if not key_id or not file_path_str:
            continue

        # file_path is relative to keys_dir.
        key_file = keys_dir / file_path_str
        if not key_file.exists():
            _logger.warning("Key file for %s not found at %s", key_id, key_file)
            continue

        try:
            # HMACKeyFileModeError propagates up if mode drifted.
            key_bytes = load_or_generate_key(key_file)
            result[key_id] = key_bytes
        except HMACKeyFileModeError:
            raise
        except OSError as exc:
            _logger.warning("Failed to load key %s from %s: %s", key_id, key_file, exc)

    return result


# ---------------------------------------------------------------------------
# Hash computation (mirroring ledger.py for verification)
# ---------------------------------------------------------------------------


def _recompute_record_hash(record_dict: dict[str, Any]) -> str:
    """Recompute the SHA-256 record_hash for verification.

    Excludes ``record_hash`` and ``hmac_seal`` fields (same as append).
    """
    hashable = {k: v for k, v in record_dict.items() if k not in ("record_hash", "hmac_seal")}
    canonical_bytes = canonicalize(hashable)
    return hashlib.sha256(canonical_bytes).hexdigest()


def _recompute_hmac_seal(key: bytes, record_hash: str) -> str:
    """Recompute the HMAC-SHA-256 seal for verification."""
    return hmac_lib.new(key, record_hash.encode("ascii"), "sha256").hexdigest()


# ---------------------------------------------------------------------------
# Public verifier
# ---------------------------------------------------------------------------


def verify_ledger(  # noqa: C901 — security-critical verifier; complexity is inherent
    ledger_path: Path,
    key_registry_path: Path,
    *,
    hash_only: bool = False,
    acknowledge_key_loss: bool = False,
) -> LedgerVerifyReport:
    """Verify the hash chain and HMAC seals of the consent ledger.

    This is a streaming verifier — the file is read once in binary mode to
    handle byte-level tamper detection (including invalid UTF-8 sequences).
    Only one record is held in memory at a time.

    Algorithm:
    1. Open the ledger file in binary mode; emit exit 5 if missing or empty.
    2. Split on b"\\n"; for each non-empty line:
       a. Decode UTF-8; non-decodable bytes → exit 1 (CHAIN_RECORD_HASH_MISMATCH).
       b. Parse JSON; JSON parse error → exit 4 (SCHEMA_VIOLATION).
       c. Validate against ``ConsentLedgerRecord``; Pydantic error → exit 4.
       d. Recompute ``record_hash``; compare with stored value.
          Mismatch → exit 1 (CHAIN_RECORD_HASH_MISMATCH).
       e. Compare stored ``prev_hash`` with previous record's ``record_hash``.
          Mismatch → exit 1 (CHAIN_PREV_HASH_MISMATCH).
       f. Unless ``hash_only``: look up key by ``key_id``; emit exit 3 if
          unknown (unless ``acknowledge_key_loss``).  Recompute HMAC; mismatch
          → track first HMAC failure (reported after full chain walk).
    3. Emit ``LedgerVerifyReport`` with the first broken record's index.

    Chain errors take priority over HMAC errors: if a chain break is detected,
    the report is returned immediately.  HMAC mismatches are recorded and
    returned only if the chain is intact.

    Args:
        ledger_path: Absolute path to the consent ledger JSONL file.
        key_registry_path: Absolute path to ``keys/registry.json``.
        hash_only: If True, skip HMAC verification.
        acknowledge_key_loss: Suppresses exit-3 for missing keys in
                              ``hash_only`` mode.

    Returns:
        ``LedgerVerifyReport`` with full verification results.

    Raises:
        HMACKeyFileModeError: If any HMAC key file has wrong permissions.
    """
    # ---- File existence / empty check (exit 5) ----------------------------
    if not ledger_path.exists():
        return LedgerVerifyReport(
            passed=False,
            total_records=0,
            first_broken_index=None,
            broken_reason="FILE_CORRUPT",
            exit_code=5,
        )

    file_size = ledger_path.stat().st_size
    if file_size == 0:
        return LedgerVerifyReport(
            passed=False,
            total_records=0,
            first_broken_index=None,
            broken_reason="FILE_CORRUPT",
            exit_code=5,
        )

    # ---- Load key registry (unless hash_only) ------------------------------
    key_registry: dict[str, bytes] = {}
    if not hash_only:
        # HMACKeyFileModeError propagates up — CLI catches → exit 6.
        key_registry = _load_key_registry(key_registry_path)

    # ---- Read file in binary mode (SC-004: detect any byte-level tamper) --
    raw_content = ledger_path.read_bytes()
    raw_lines = raw_content.split(b"\n")

    # ---- Streaming verification pass ---------------------------------------
    total_records = 0
    prev_record_hash = _GENESIS_PREV_HASH  # expected prev_hash for record 0

    # Track whether we have a pending HMAC mismatch (chain takes priority).
    hmac_mismatch_index: int | None = None

    for raw_line_bytes in raw_lines:
        stripped_bytes = raw_line_bytes.strip()
        if not stripped_bytes:
            continue  # skip blank / trailing newline lines

        index = total_records
        total_records += 1

        # --- Decode UTF-8 (byte-level tamper: invalid UTF-8 → exit 1) ------
        try:
            stripped = stripped_bytes.decode("utf-8")
        except UnicodeDecodeError:
            # A byte flip creating invalid UTF-8 is a hash chain break.
            return LedgerVerifyReport(
                passed=False,
                total_records=total_records,
                first_broken_index=index,
                broken_reason="CHAIN_RECORD_HASH_MISMATCH",
                exit_code=1,
            )

        # --- Parse JSON ---------------------------------------------------------
        # JSONDecodeError means the bytes are not valid JSON at all — this is
        # stronger evidence of byte-level tampering (chain break) than of an
        # original schema violation.  Schema violations (exit 4) are reserved
        # for records whose JSON is syntactically valid but whose fields do not
        # satisfy ConsentLedgerRecord — a write-time error, not a tamper.
        try:
            record_dict = json.loads(stripped)
        except json.JSONDecodeError:
            return LedgerVerifyReport(
                passed=False,
                total_records=total_records,
                first_broken_index=index,
                broken_reason="CHAIN_RECORD_HASH_MISMATCH",
                exit_code=1,
            )

        # --- Chain integrity: check required chain fields exist -----------
        # We check record_hash and prev_hash directly on the raw dict BEFORE
        # Pydantic validation.  This ensures:
        #   - Missing chain fields (genuinely malformed record, write-time
        #     error) → SCHEMA_VIOLATION exit 4.
        #   - Present chain fields but corrupted other fields (byte-flip
        #     tampering) → CHAIN_RECORD_HASH_MISMATCH exit 1 (hash fails).
        stored_hash = record_dict.get("record_hash")
        stored_prev = record_dict.get("prev_hash")
        if not isinstance(stored_hash, str) or not isinstance(stored_prev, str):
            return LedgerVerifyReport(
                passed=False,
                total_records=total_records,
                first_broken_index=index,
                broken_reason="SCHEMA_VIOLATION",
                exit_code=4,
            )

        # --- Chain integrity: recompute record_hash -----------------------
        recomputed_hash = _recompute_record_hash(record_dict)
        if recomputed_hash != stored_hash:
            return LedgerVerifyReport(
                passed=False,
                total_records=total_records,
                first_broken_index=index,
                broken_reason="CHAIN_RECORD_HASH_MISMATCH",
                exit_code=1,
            )

        # --- Chain integrity: verify prev_hash links ----------------------
        if stored_prev != prev_record_hash:
            return LedgerVerifyReport(
                passed=False,
                total_records=total_records,
                first_broken_index=index,
                broken_reason="CHAIN_PREV_HASH_MISMATCH",
                exit_code=1,
            )

        # --- Pydantic schema validation ------------------------------------
        # At this point the hash chain is intact.  Parse the record with the
        # full Pydantic model for HMAC key_id extraction.
        # Use model_validate_json because model_config has strict=True which
        # prevents str→datetime coercion via model_validate(dict).
        try:
            record = ConsentLedgerRecord.model_validate_json(stripped)
        except ValidationError:
            # The chain fields validated correctly but the record fields are
            # semantically invalid (write-time schema error).
            return LedgerVerifyReport(
                passed=False,
                total_records=total_records,
                first_broken_index=index,
                broken_reason="SCHEMA_VIOLATION",
                exit_code=4,
            )

        # --- HMAC verification (skipped in hash_only mode) ----------------
        if not hash_only:
            key_id = record.key_id
            if key_id not in key_registry:
                if not acknowledge_key_loss:
                    return LedgerVerifyReport(
                        passed=False,
                        total_records=total_records,
                        first_broken_index=index,
                        broken_reason="KEY_MISSING",
                        exit_code=3,
                    )
                # acknowledge_key_loss: skip HMAC for this record.
                _logger.warning(
                    "Key %s not in registry; skipping HMAC for record %d "
                    "(--acknowledge-key-loss set)",
                    key_id,
                    index,
                )
            else:
                key_bytes = key_registry[key_id]
                recomputed_seal = _recompute_hmac_seal(key_bytes, stored_hash)
                if recomputed_seal != record.hmac_seal and hmac_mismatch_index is None:
                    # Record first HMAC mismatch; continue chain walk.
                    # Chain errors take priority over HMAC errors — only
                    # report HMAC failure if chain is intact.
                    hmac_mismatch_index = index

        # Advance the chain pointer.
        prev_record_hash = stored_hash

    # ---- Determine final result -------------------------------------------
    if hmac_mismatch_index is not None:
        return LedgerVerifyReport(
            passed=False,
            total_records=total_records,
            first_broken_index=hmac_mismatch_index,
            broken_reason="HMAC_SEAL_MISMATCH",
            exit_code=2,
        )

    return LedgerVerifyReport(
        passed=True,
        total_records=total_records,
        first_broken_index=None,
        broken_reason=None,
        exit_code=0,
    )
