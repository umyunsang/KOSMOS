# Quickstart — Permission v2 (Epic #1297)

**Feature**: 033-permission-v2-spectrum
**Audience**: KOSMOS citizen users + onboarding engineers + auditors
**Date**: 2026-04-20

> 5 citizen scenarios mapping directly to US1–US5. Each scenario is reproducible end-to-end with stdlib-only tooling. No new runtime dependencies.

---

## Prerequisites

```bash
# KOSMOS already installed via uv (see repo root README)
uv run python -c "from kosmos.permissions import modes; print(modes.__version__)"
# → 1.0.0

# Directories created on first boot (do NOT pre-create)
ls -la ~/.kosmos/
# drwx------  alice  staff   permissions.json          (mode 0600)
# drwx------  alice  staff   consent_ledger.jsonl      (mode 0600)
# drwx------  alice  staff   keys/
# -r--------  alice  staff   keys/ledger.key           (mode 0400)
```

If any file is missing, KOSMOS creates it on first call with the correct mode. **Do NOT pre-create with wrong modes** — loader will refuse (Invariant C3).

---

## Scenario 1 — US1 (P1): `default` mode, first HIRA call

**Citizen goal**: find nearest hospital without understanding permission internals.

```bash
uv run kosmos chat
# TUI opens at default mode (gray status bar).
```

Prompt the agent:

> "집 근처 내과 병원 찾아줘"

Expected behavior:

1. Agent calls `resolve_location` → silent (AAL public, reversible).
2. Agent calls `hira_hospital_search` → **first-time consent prompt appears**:
   - 목적: 병원 검색 결과 제공
   - 항목: 현재 위치 좌표
   - 보유기간: 일회성
   - 거부권: 거부 시 검색 불가
3. Citizen presses `Y`. Tool executes. Ledger appends 1 record.
4. Second call (`hira_hospital_search` with different params) in same session: **no prompt** (session-scope `allow` rule).
5. Verify ledger:
   ```bash
   uv run kosmos permissions verify
   # ✓ Ledger verification PASSED
   #   Records: 1
   ```

---

## Scenario 2 — US2 (P1): tamper detection

**Audit goal**: detect a single-byte modification in the ledger.

```bash
# Start with clean state
rm -rf ~/.kosmos/consent_ledger.jsonl

# Run Scenario 1 five times (different searches)
# ... 5 records in ledger

# Simulate external tamper
python3 -c "
with open('$HOME/.kosmos/consent_ledger.jsonl', 'r+b') as f:
    f.seek(100)  # flip a byte inside record 1
    byte = f.read(1)
    f.seek(100)
    f.write(bytes([byte[0] ^ 0x01]))
"

# Verify
uv run kosmos permissions verify
# ✗ Ledger verification FAILED — CHAIN_RECORD_HASH_MISMATCH
#   First broken index: 0
#   Reason: record_hash recomputation does not match stored record_hash at record 0.
# Exit code: 1
```

---

## Scenario 3 — US3 (P1): `bypassPermissions` + irreversible killswitch

**Citizen goal**: citizen enables bypass for speed but irreversible calls still prompt.

```bash
uv run kosmos chat
```

In TUI:
1. Type `/permissions bypass`.
2. Confirmation dialog appears with default focus on **N**. Type `y` + Enter.
3. Status bar flashes red/yellow: `⚠ 모드: 우회`.

Prompt agent:

> "국민신문고에 민원 제출해줘 주제는 X"

Expected behavior (assuming `gov24_complaint_submit` adapter has `is_irreversible=True`):

1. **Prompt appears** (Killswitch K2):
   - 목적: 민원 제출
   - 항목: 민원 본문, 연락처
   - 보유기간: 법정 보존기간
   - 거부권: 거부 시 민원 미제출
2. Citizen presses `Y`. Tool executes.
3. Citizen prompts "같은 민원 하나 더 제출해줘".
4. **Prompt appears AGAIN** (K5 — no caching, K6 — distinct `action_digest`).
5. Verify ledger: 2 records, both with `mode="bypassPermissions"`, `granted=true`, distinct `action_digest`.

```bash
uv run kosmos permissions verify --json | jq '.total_records'
# 2
```

---

## Scenario 4 — US4 (P2): tri-state persistence across sessions

**Citizen goal**: persistent allow/deny/ask decisions survive restart.

```bash
uv run kosmos chat
# Set 3 rules via slash commands
# /permissions allow hira_hospital_search
# /permissions deny gov24_complaint_submit
# /permissions ask nmc_emergency_search  (explicit "not decided")
```

Exit TUI (`Ctrl+D`).

```bash
cat ~/.kosmos/permissions.json | python3 -m json.tool
# {
#   "schema_version": "1.0.0",
#   "generated_at": "2026-04-20T...",
#   "rules": [
#     { "tool_id": "hira_hospital_search", "decision": "allow", ... },
#     { "tool_id": "gov24_complaint_submit", "decision": "deny", ... },
#     { "tool_id": "nmc_emergency_search", "decision": "ask", ... }
#   ]
# }
```

Restart TUI:
```bash
uv run kosmos chat
```

- Call `hira_hospital_search` → silent allow (rule loaded).
- Call `gov24_complaint_submit` → immediate denial without prompt.
- Call `nmc_emergency_search` → prompt appears (ask = no decision).

---

## Scenario 5 — US5 (P2): Shift+Tab + slash command cycle

```bash
uv run kosmos chat
```

1. Start at `default` (gray).
2. Press `Shift+Tab`. Status → `plan` (cyan).
3. Press `Shift+Tab`. Status → `acceptEdits` (green).
4. Press `Shift+Tab`. Status → `default` (gray).
5. Press `Shift+Tab`. Status → `plan` (cyan, full cycle verified).
6. Type `/permissions bypass`. Confirm `y`. Status → **flashing red/yellow**.
7. Press `Shift+Tab`. Status → `default` (escape hatch S1).

---

## Troubleshooting

### "HMAC key file mode mismatch" (exit code 6)

```bash
ls -la ~/.kosmos/keys/ledger.key
# -rw-------  alice  staff   ...  (mode 0600)  ← WRONG
```

Fix:
```bash
chmod 0400 ~/.kosmos/keys/ledger.key
```

If the file is missing, restart KOSMOS — it regenerates on first call.

### "permissions.json schema violation"

External editor broke the schema. Restore from backup or delete to reset (all rules lost):

```bash
rm ~/.kosmos/permissions.json
# KOSMOS recreates on next call. Rules must be re-added.
```

### Lost HMAC key

```bash
uv run kosmos permissions verify --hash-only --acknowledge-key-loss
# Hash chain remains verifiable. HMAC verification permanently waived for affected records.
```

Rotate going forward:
```bash
uv run kosmos permissions rotate-key
# New key id: k0002. Old records remain HMAC-unverifiable.
```

### Mode stuck at `bypassPermissions` after restart

Impossible by design (Invariant PR1). Every session starts at `default`. If you see bypass after restart, file a bug — this is a constitutional violation.

---

## Rollback

If Permission v2 behavior is undesirable:

```bash
# Option A: delete rule store (loses all rules)
rm ~/.kosmos/permissions.json

# Option B: set all rules to 'ask' (keep history)
uv run kosmos permissions reset-to-ask
```

**Consent ledger is NEVER rolled back.** PIPA §8 (2+ year retention). To archive:

```bash
mv ~/.kosmos/consent_ledger.jsonl ~/.kosmos/consent_ledger.archive.$(date +%Y%m%d).jsonl
# A fresh ledger starts from genesis on next consent event.
```

---

## CI smoke test (for maintainers)

```bash
uv run pytest tests/permissions/ -v --no-cov
# Expected: all tests PASS, <3s wall time
```

Verify zero new runtime deps:

```bash
git diff main -- pyproject.toml | grep -E "^\+[a-z]" | grep -vE "^\+\+\+"
# Expected: no output
```

---

## Exit Criteria

- [ ] All 5 scenarios documented with reproducible commands.
- [ ] Troubleshooting covers exit codes 1, 2, 3, 5, 6 and "lost HMAC key".
- [ ] Rollback preserves PIPA retention (ledger never deleted, only archived).
- [ ] CI smoke test invocation documented.
