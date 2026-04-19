# Contract — `kosmos permissions verify` CLI

**Feature**: 033-permission-v2-spectrum
**Artifact**: Behavioral contract for `src/kosmos/permissions/cli.py::verify` command
**Date**: 2026-04-20

> Verifies the hash chain + HMAC seal of `~/.kosmos/consent_ledger.jsonl`. Fail-closed on any integrity error. Designed so an external auditor can run it without KOSMOS runtime dependencies beyond the Python stdlib + HMAC key file.

## 1. Invocation

```
kosmos permissions verify [--path PATH] [--hash-only] [--acknowledge-key-loss] [--json]
```

| Flag | Default | Purpose |
|------|---------|---------|
| `--path PATH` | `~/.kosmos/consent_ledger.jsonl` | Override ledger location (test / audit). |
| `--hash-only` | `false` | Skip HMAC verification. Use only when HMAC key is lost (requires `--acknowledge-key-loss`). |
| `--acknowledge-key-loss` | `false` | Required alongside `--hash-only` — documents the skipped HMAC step in the output report. |
| `--json` | `false` | Emit `LedgerVerifyReport` as JSON (for CI / audit pipelines). Default = human-readable Korean text. |

## 2. Exit Codes

| Code | Meaning | Trigger |
|------|---------|---------|
| `0` | OK — chain + HMAC verified. | `chain_ok=True AND hmac_ok=True`. |
| `1` | Chain broken. | `chain_ok=False`. Any record `prev_hash` mismatch or `record_hash` recomputation mismatch. |
| `2` | HMAC broken. | `chain_ok=True AND hmac_ok=False`. At least one record failed HMAC-SHA-256 verification. |
| `3` | HMAC key unknown. | Record `hmac_key_id` not in key registry at `~/.kosmos/keys/`. |
| `4` | Schema violation. | Record fails Pydantic validation against `ConsentLedgerRecord`. |
| `5` | File not found or empty. | `~/.kosmos/consent_ledger.jsonl` missing or 0 bytes. |
| `6` | HMAC key file mode mismatch. | `~/.kosmos/keys/ledger.key` mode != `0400`. Fail-closed load refusal (Invariant C3). |
| `64` | Usage error. | Missing required flag combination (e.g., `--hash-only` without `--acknowledge-key-loss`). |

**Invariant E1 — Non-zero exit codes NEVER collapse into `1`.** Each failure class is distinguishable for CI / audit tooling.

## 3. Standard Output (human mode)

On success:
```
✓ Ledger verification PASSED
  Path: /Users/alice/.kosmos/consent_ledger.jsonl
  Records: 42
  Chain: OK
  HMAC: OK (key registry: k0001, k0002)
  Verified at: 2026-04-20T11:30:00Z
```

On failure (chain):
```
✗ Ledger verification FAILED — CHAIN_PREV_HASH_MISMATCH
  Path: /Users/alice/.kosmos/consent_ledger.jsonl
  Records: 42
  First broken index: 17 (receipt_id: 01970b0c-7a6d-...-8abc)
  Reason: prev_hash at record 17 does not match record_hash of record 16.
  Expected: aaaabbbbccccddddeeeeffff0000111122223333444455556666777788889999
  Got:      0000111122223333444455556666777788889999aaaabbbbccccddddeeeeffff
  Verified at: 2026-04-20T11:30:00Z
```

On failure (HMAC):
```
✗ Ledger verification FAILED — HMAC_SEAL_MISMATCH
  Path: /Users/alice/.kosmos/consent_ledger.jsonl
  Records: 42
  First broken index: 17 (receipt_id: 01970b0c-7a6d-...-8abc)
  Reason: HMAC-SHA-256 recomputed from key k0001 does not match stored seal.
  Verified at: 2026-04-20T11:30:00Z
```

## 4. Standard Output (JSON mode)

```json
{
  "total_records": 42,
  "chain_ok": true,
  "hmac_ok": true,
  "first_broken_index": null,
  "broken_reason": null,
  "verified_at": "2026-04-20T11:30:00Z",
  "path": "/Users/alice/.kosmos/consent_ledger.jsonl",
  "key_registry": ["k0001", "k0002"]
}
```

## 5. Byte-Level Tamper Detection Contract

The verifier MUST detect a **single-byte modification** anywhere in any record (SC-004).

| Attack | Expected detection |
|--------|--------------------|
| Flip a byte inside `purpose` field. | Record `record_hash` recomputation fails → exit 1 (`CHAIN_RECORD_HASH_MISMATCH`). If record_hash is also flipped, `prev_hash` chain fails at next record → exit 1 (`CHAIN_PREV_HASH_MISMATCH`). HMAC also fails → exit 2 if chain is untouched. |
| Delete a record (truncate). | Chain verification detects missing link via `prev_hash` mismatch on next record → exit 1. If last record deleted, no immediate detection until next append (append CLI refuses on prev_hash miss). |
| Re-order two records. | `prev_hash` mismatch → exit 1. |
| Insert a forged record with valid HMAC (attacker has key). | Chain mismatch → exit 1. HMAC key compromise requires `kosmos permissions rotate-key` + forensic review (out-of-band). |
| Flip a byte in `hmac_seal` itself. | HMAC recomputation mismatch → exit 2. |
| Replace `hmac_key_id` with unknown key. | Key lookup fails → exit 3. |

## 6. Non-Functional Requirements

- Runtime: ≤ 200ms for 1,000 records (SC-003 indirectly; verified at CI).
- Memory: Streaming JSONL read, ≤ 8 MB resident for 10,000 records.
- Dependencies: Python stdlib only (`hashlib`, `hmac`, `json`, `pathlib`, `argparse`, `os`) + `pydantic v2` for schema validation.
- Portability: Runnable via `uv run python -m kosmos.permissions.cli verify` with ONLY the `kosmos/permissions/` package vendored.

## 7. Test Matrix (required)

| # | Scenario | Expected exit | Expected `broken_reason` |
|---|----------|---------------|--------------------------|
| V01 | 5 records, all valid. | 0 | null |
| V02 | 0 records (empty file). | 5 | `FILE_EMPTY` |
| V03 | Missing file. | 5 | `FILE_NOT_FOUND` |
| V04 | 5 records, flip byte in record 2 `purpose`. | 1 | `CHAIN_RECORD_HASH_MISMATCH` |
| V05 | 5 records, flip byte in record 2 `hmac_seal`. | 2 | `HMAC_SEAL_MISMATCH` |
| V06 | 5 records, delete record 3 (truncate + shift). | 1 | `CHAIN_PREV_HASH_MISMATCH` |
| V07 | 5 records, swap records 2 and 3. | 1 | `CHAIN_PREV_HASH_MISMATCH` |
| V08 | 5 records, record 3 references key k9999 (not in registry). | 3 | `HMAC_KEY_UNKNOWN` |
| V09 | 5 records, record 2 has invalid schema (pipa_class="invalid"). | 4 | `SCHEMA_VIOLATION` |
| V10 | HMAC key file mode = 0644. | 6 | HMAC load refusal |
| V11 | 5 records, `--hash-only --acknowledge-key-loss`. | 0 or 1 | HMAC skip recorded in report |
| V12 | Usage error: `--hash-only` without `--acknowledge-key-loss`. | 64 | Usage error |

## 8. Exit Criteria

- [ ] All 12 V-matrix scenarios implemented in `tests/permissions/test_ledger_verify_cli.py`.
- [ ] CLI wired via entry point `kosmos permissions verify` (no new dependency).
- [ ] Exit code taxonomy (§2) documented in `--help`.
- [ ] JSON output shape matches `LedgerVerifyReport` Pydantic model.
- [ ] Stdlib-only (no `PyYAML`, no `cryptography`, no `click`).
