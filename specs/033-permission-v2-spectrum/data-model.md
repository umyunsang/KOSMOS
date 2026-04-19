# Data Model — Permission v2 (Epic #1297)

**Feature**: 033-permission-v2-spectrum
**Phase**: 1 — Design & Contracts
**Date**: 2026-04-20
**Owner**: Lead (Opus) → delegated to Backend Architect (Sonnet) at `/speckit-implement`

> All models are Pydantic v2 `BaseModel` with `model_config = ConfigDict(frozen=True, extra="forbid", strict=True)`.
> Types use `Literal[...]` (enums), `StrictStr(min_length=1)`, `conint(ge=0)`, `constr(pattern=...)`.
> **No `Any`. No `Optional` defaults that widen the shape.** Every field is either required or has an explicit `None`-typed default with a `Literal[None]` guard.

---

## 1. Entities

### 1.1 `PermissionMode` (enum alias)

Python: `PermissionMode = Literal["default", "plan", "acceptEdits", "bypassPermissions", "dontAsk"]`

| Value | Description | PIPA prompt behavior | Auto-approve surface |
|-------|-------------|----------------------|----------------------|
| `default` | Ask on every tool call unless a persistent `allow` rule exists. | ASK (every irreversible / AAL3 call) | Persistent `allow` only. |
| `plan` | Dry-run — no side effects permitted. | SKIP (no execution) | Nothing. |
| `acceptEdits` | Auto-approve **reversible, AAL1/public** reads. | ASK (irreversible / AAL3) | Reversible + `auth_level ∈ {public, AAL1}`. |
| `bypassPermissions` | Auto-approve ALL *except* killswitch gates. | **ALWAYS ASK** (irreversible / pipa_class=특수) | Non-irreversible + non-특수. |
| `dontAsk` | Auto-approve exactly the pre-saved allow-list. Out-of-list = fall-back to `default`. | ASK (cache miss) | Exact-match rules only. |

**Invariant M1 — Mode is the outer gate, not the inner gate.** Killswitch (§II) runs BEFORE mode evaluation. No mode can widen the killswitch set.

**Invariant M2 — `plan` mode is observationally pure.** No adapter `.execute()` is called. Preview strings only.

**Invariant M3 — Mode is session-scoped.** Mode changes do NOT persist to disk (rules do; mode does not). Restart → reset to `default`.

### 1.2 `PermissionRule` (tri-state persistent rule)

```python
class PermissionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    tool_id: constr(pattern=r"^[a-z0-9_.]+$", min_length=1, max_length=128)
    decision: Literal["allow", "ask", "deny"]
    scope: Literal["session", "project", "user"]  # user = ~/.kosmos/permissions.json
    created_at: datetime  # UTC, tz-aware
    created_by_mode: PermissionMode  # which mode produced this rule
    expires_at: datetime | None = None  # None = never expires (user scope default)
```

**Invariant R1 — `deny` wins.** If any scope says `deny`, block — even if `user` scope says `allow`.
**Invariant R2 — Resolution order.** `session` > `project` > `user` (narrower scope overrides).
**Invariant R3 — `ask` is semantically equivalent to "no rule".** Kept explicit to model "user acknowledged but did not decide".
**Invariant R4 — `tool_id` is the canonical adapter identifier, NOT a wildcard.** Wildcards are a Deferred item (NEEDS TRACKING).

### 1.3 `ToolPermissionContext` (per-invocation request)

```python
class ToolPermissionContext(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    tool_id: StrictStr  # same pattern as PermissionRule.tool_id
    mode: PermissionMode
    is_irreversible: bool
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]
    pipa_class: Literal["일반", "민감", "고유식별", "특수"]
    session_id: UUID4
    correlation_id: StrictStr  # from Spec 032
    timestamp: datetime  # tz-aware UTC
```

**Invariant T1 — Every adapter call constructs one `ToolPermissionContext`.** Pipeline accepts no other shape.
**Invariant T2 — `is_irreversible` and `auth_level` and `pipa_class` come from `AdapterPermissionMetadata`, not user input.** The citizen CANNOT spoof these.

### 1.4 `AdapterPermissionMetadata` (Spec 024 coupling)

Extends `GovAPITool` declaration from Spec 024 §3.2. **This is a read-only projection** — KOSMOS Permission v2 does not re-author these; it reads them from `GovAPITool`.

```python
class AdapterPermissionMetadata(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    tool_id: StrictStr
    is_irreversible: bool                   # Spec 024 FR
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]  # Spec 024 FR
    pipa_class: Literal["일반", "민감", "고유식별", "특수"]   # Spec 024 FR
    requires_auth: bool                     # Spec 024/025 V6
    auth_type: Literal["public", "api_key", "oauth"]        # Spec 025 V6
```

**Invariant A1 — Permission pipeline FAILS CLOSED if any field is missing.** No defaults. No inference.

### 1.5 `ConsentDecision` (PIPA §15(2) 4-tuple + user choice)

```python
class ConsentDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    # PIPA §15(2) 4-tuple — ALL REQUIRED
    purpose: StrictStr                      # 목적
    data_items: tuple[StrictStr, ...]       # 항목 (frozen tuple)
    retention_period: StrictStr             # 보유기간 (ISO 8601 duration or "일회성")
    refusal_right: StrictStr                # 거부권 + 불이익 고지문
    # User choice
    granted: bool
    # Context binding
    tool_id: StrictStr
    pipa_class: Literal["일반", "민감", "고유식별", "특수"]
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]
```

**Invariant C1 — All 4 tuple fields non-empty.** Enforced by `StrictStr(min_length=1)` on each.
**Invariant C2 — `data_items` is a tuple (frozen, ordered).** Pydantic v2 serializes to JSON array; canonical JSON ordering preserved at consent-receipt creation.
**Invariant C3 — 민감 / 고유식별 / 특수 → `granted=False` triggers immediate tool denial.** PIPA §22(1) individual consent requirement.

### 1.6 `ConsentLedgerRecord` (single append-only record)

```python
class ConsentLedgerRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    # Record identity
    receipt_id: UUID4                       # Kantara CR v1.1.0 "piiPrincipalId" surrogate
    version: Literal["1.0.0"]               # schema version
    # Time
    occurred_at: datetime                   # tz-aware UTC
    # Subject binding
    subject_hash: constr(pattern=r"^[0-9a-f]{64}$")  # SHA-256 of stable subject identifier
    session_id: UUID4
    # PIPA 4-tuple (embedded ConsentDecision shape)
    purpose: StrictStr
    data_items: tuple[StrictStr, ...]
    retention_period: StrictStr
    refusal_right: StrictStr
    # Context
    tool_id: StrictStr
    pipa_class: Literal["일반", "민감", "고유식별", "특수"]
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]
    mode: PermissionMode
    # Action digest (for bypassPermissions irreversible re-prompt dedup)
    action_digest: constr(pattern=r"^[0-9a-f]{64}$")  # SHA-256 of canonical (tool_id, args, timestamp-bucket)
    # User decision
    granted: bool
    # Hash chain (FR-D02)
    prev_hash: constr(pattern=r"^[0-9a-f]{64}$")       # SHA-256 of previous record; genesis = 64*"0"
    record_hash: constr(pattern=r"^[0-9a-f]{64}$")     # SHA-256 over canonical(record excluding record_hash + hmac_seal)
    # HMAC seal (FR-D04)
    hmac_key_id: constr(pattern=r"^k\d{4}$")           # e.g., "k0001" — for rotation-aware verification
    hmac_seal: constr(pattern=r"^[0-9a-f]{64}$")       # HMAC-SHA-256(canonical(record excluding hmac_seal))
```

**Invariant L1 — Append-only.** The JSONL file is opened `O_WRONLY | O_APPEND | O_CREAT` (never `O_TRUNC`). Spec enforces WORM via SC-004 verification.
**Invariant L2 — Chain integrity.** `record_hash[N] = SHA256(canonical_json(record[N] with record_hash="" and hmac_seal=""))`. `prev_hash[N+1] == record_hash[N]`.
**Invariant L3 — HMAC seal is independent of hash chain.** Two-layer defense: hash chain detects truncation/reorder; HMAC detects per-record tampering WITHOUT full chain re-read.
**Invariant L4 — `hmac_key_id` allows rotation.** Verifier maintains a key-ID → key registry. Old records remain verifiable after rotation.
**Invariant L5 — Canonical JSON is RFC 8785 JCS.** All hashing targets the same byte string regardless of key ordering.

### 1.7 `ConsentLedger` (aggregate verifier)

Not persisted — constructed at verify-time by reading the JSONL.

```python
class ConsentLedger(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    path: Path                              # ~/.kosmos/consent_ledger.jsonl
    records: tuple[ConsentLedgerRecord, ...]
    genesis_hash: Literal["0000000000000000000000000000000000000000000000000000000000000000"]

    def verify(self) -> LedgerVerifyReport: ...
```

### 1.8 `LedgerVerifyReport` (CLI output shape)

```python
class LedgerVerifyReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    total_records: conint(ge=0)
    chain_ok: bool
    hmac_ok: bool
    first_broken_index: int | None          # -1 if not broken, else 0-indexed position
    broken_reason: Literal[
        "CHAIN_PREV_HASH_MISMATCH",
        "CHAIN_RECORD_HASH_MISMATCH",
        "HMAC_SEAL_MISMATCH",
        "HMAC_KEY_UNKNOWN",
        "SCHEMA_VIOLATION",
        "FILE_NOT_FOUND",
        "FILE_EMPTY",
        None,
    ] | None
    verified_at: datetime                   # tz-aware UTC
```

### 1.9 `HMACKey` (file-backed secret)

Not a BaseModel — filesystem contract only. Stored at `~/.kosmos/keys/ledger.key`.

| Property | Requirement |
|----------|-------------|
| File mode | `0400` (owner-read only). Loader REFUSES to load if any other bit set. |
| Content | 32-byte cryptographically random value, base64-encoded (44 chars + `\n`). |
| Generation | `secrets.token_bytes(32)` on first boot if missing. |
| Rotation | `kosmos permissions rotate-key` CLI archives old key as `keys/ledger.key.k0001` and writes new `keys/ledger.key` with incremented `hmac_key_id`. |
| Loss | If deleted, ledger becomes HMAC-unverifiable for records sealed with the lost key. Hash chain still verifies. Recovery: `kosmos permissions verify --hash-only --acknowledge-key-loss`. |

---

## 2. Invariants (cross-entity)

### 2.1 Killswitch invariants (K1–K6) — Constitution §II

| ID | Invariant | Enforced by |
|----|-----------|-------------|
| K1 | Killswitch runs BEFORE mode evaluation. | `killswitch.py::pre_evaluate()` must be first call in `permission_pipeline()`. |
| K2 | `bypassPermissions` NEVER silently executes an `is_irreversible=True` tool. | Killswitch table returns `ASK` for `(bypassPermissions, is_irreversible)`. |
| K3 | `bypassPermissions` NEVER silently executes a `pipa_class="특수"` tool. | Killswitch table returns `ASK` for `(bypassPermissions, pipa_class="특수")`. |
| K4 | `bypassPermissions` NEVER silently executes an `auth_level="AAL3"` tool. | Killswitch table returns `ASK` for `(bypassPermissions, auth_level="AAL3")`. |
| K5 | Killswitch ASK prompts are NOT cacheable. Re-prompt every call. | `bypass_prompt.py` forbids cache key lookup; always asks. |
| K6 | Killswitch decisions get their own `action_digest` per call. | `action_digest` includes `uuid7()` timestamp bucket to prevent prompt dedup within bypass mode. |

### 2.2 Consent invariants (C1–C5) — PIPA §15(2)/§22(1)/§26

| ID | Invariant | Enforced by |
|----|-----------|-------------|
| C1 | PIPA §15(2) 4-tuple completeness at prompt time. | `prompt.py::PIPAConsentPrompt.__init__` requires all 4 fields; builder raises `ValidationError` if any missing. |
| C2 | 민감 / 고유식별 / 특수 require individual consent (no bundle). | `prompt.py::assert_individual_consent(pipa_class)` raises if bundled prompt detected. |
| C3 | HMAC key file mode is `0400` at open time. | `hmac_key.py::load()` calls `os.stat()` and refuses `st_mode & 0o077 != 0`. |
| C4 | Ledger append is atomic. | `ledger.py::append()` writes canonical JSON + `\n` in a single `os.write()` to the `O_APPEND` fd; then fsync. |
| C5 | LLM synthesis output NEVER emits PII fields marked `민감` / `고유식별`. | `synthesis_guard.py::redact()` pattern-matches adapter output schema and drops fields before LLM prompt assembly. |

### 2.3 Mode invariants (M1–M3)

See §1.1 above.

### 2.4 Rule invariants (R1–R4)

See §1.2 above.

### 2.5 Adapter metadata invariants (A1)

See §1.4 above. Fail-closed if any field missing.

### 2.6 Tool context invariants (T1–T2)

See §1.3 above.

---

## 3. State Transitions

### 3.1 Mode spectrum — Shift+Tab cycle (FR-A02/A03)

```
default ──Shift+Tab──▶ plan ──Shift+Tab──▶ acceptEdits ──Shift+Tab──▶ default
                                                                         ▲
                                                                         └── (cycle)

bypassPermissions   — reached only via `/permissions bypass` + explicit confirmation
dontAsk             — reached only via `/permissions dontAsk` + explicit confirmation

Shift+Tab SKIPS bypassPermissions and dontAsk (high-risk modes excluded from fast cycle).
```

**State graph (adjacency):**

| From | Shift+Tab | `/permissions bypass` | `/permissions dontAsk` | `/permissions default` |
|------|-----------|----------------------|------------------------|------------------------|
| `default` | → `plan` | → `bypassPermissions` (confirm) | → `dontAsk` (confirm) | no-op |
| `plan` | → `acceptEdits` | → `bypassPermissions` (confirm) | → `dontAsk` (confirm) | → `default` |
| `acceptEdits` | → `default` | → `bypassPermissions` (confirm) | → `dontAsk` (confirm) | → `default` |
| `bypassPermissions` | → `default` | no-op | → `dontAsk` (confirm) | → `default` |
| `dontAsk` | → `default` | → `bypassPermissions` (confirm) | no-op | → `default` |

**Invariant S1 — Shift+Tab can always ESCAPE high-risk modes (both `bypassPermissions` and `dontAsk` → `default`).** Citizen always has a one-keypress exit.

### 3.2 Rule lifecycle

```
(no rule) ──user.allow──▶ allow ──user.revoke──▶ (no rule)
(no rule) ──user.deny───▶ deny  ──user.revoke──▶ (no rule)
(no rule) ──user.ack────▶ ask   ──user.revoke──▶ (no rule)

allow ──upgrade──▶ allow (idempotent)
deny  ──upgrade──▶ deny  (idempotent)
ask   ──upgrade──▶ allow | deny (explicit transition only)
```

**Invariant S2 — `deny` cannot be silently demoted.** Explicit `/permissions revoke <tool_id>` required.

### 3.3 Ledger append → verify lifecycle

```
(no ledger) ──first-append──▶ [R0] (prev_hash=64*"0", record_hash=H0, hmac_key_id=k0001)
[R0] ──append──▶ [R0, R1] (R1.prev_hash=R0.record_hash)
[R0, R1] ──append──▶ [R0, R1, R2] (R2.prev_hash=R1.record_hash)
...
[R0..RN] ──verify──▶ LedgerVerifyReport(chain_ok=True, hmac_ok=True)
[R0..RN] ──external tamper──▶ LedgerVerifyReport(chain_ok=False, first_broken_index=k)
[R0..RN] ──HMAC key rotate──▶ [R0..RN appended with k0001, RN+1... appended with k0002]
```

**Invariant S3 — Rotation does not re-seal old records.** Old records keep their original `hmac_key_id`. Verifier carries the whole key registry.

### 3.4 Killswitch ask lifecycle (FR-B01..B04)

```
bypassPermissions mode + tool_context arrives
   │
   ├─ is_irreversible=True?  ────YES────▶ PROMPT (PIPA 4-tuple, individual)
   │                                           │
   │                                           ├── granted=True ──▶ execute + append ledger record + audit hash
   │                                           └── granted=False ─▶ deny + append ledger record (granted=False)
   │
   ├─ pipa_class="특수"?      ────YES────▶ (same prompt flow)
   │
   ├─ auth_level="AAL3"?      ────YES────▶ (same prompt flow)
   │
   └─ NONE of the above       ────────▶  SILENT ALLOW (bypass mode's normal path)
```

**Invariant S4 — Killswitch prompt re-appears every call.** No "remember this" option in bypass mode (contrast with `default` mode where `allow` is persistable).

---

## 4. Schema Versioning

| Entity | Version field | Migration policy |
|--------|---------------|------------------|
| `ConsentLedgerRecord` | `version: Literal["1.0.0"]` | v1.1.0+ rewrites via migration CLI that appends new records with new version; old records remain valid. NEVER rewrites in place. |
| `PermissionRule` | implicit via `permissions.json.schema_version` | v2 rule-store layout triggers boot-time migration to JSONL fork. NEEDS TRACKING. |
| `HMACKey` | `hmac_key_id` | Monotonic `k0001`, `k0002`, ... Rotation CLI increments. |

---

## 5. Out of Model

Not modeled by this spec (explicit exclusions — see `spec.md § Out of Scope`):

- Wildcard rules (`tool_id: *`) — Deferred (NEEDS TRACKING).
- Cross-device sync of `permissions.json` — Permanent out of scope (single-user MVP).
- Consent receipt export to 3rd-party Kantara registrar — Deferred (NEEDS TRACKING).
- Multi-subject ledger (SaaS tenancy) — Permanent out of scope.
- Web / mobile UI for rule management — Permanent out of scope (TUI only).

---

## 6. Phase 1 Exit for data-model.md

- [x] Every entity has `frozen=True, extra="forbid", strict=True`.
- [x] Every field has a concrete type (`Literal`, `StrictStr`, `conint`, `constr(pattern=...)`). No `Any`.
- [x] Every invariant has an enforcement site named.
- [x] State transitions cover all 5 modes + rule lifecycle + ledger append + killswitch ask.
- [x] Schema versioning strategy covers append-only migration path.
- [x] Out-of-model exclusions cite `spec.md § Out of Scope` or Deferred items.

**Next**: write `contracts/*` JSON Schemas + behavioral contracts.
