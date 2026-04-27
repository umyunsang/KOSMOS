# Audit Contract: P1 Dead Anthropic Model Matrix Removal

**Branch**: `2112-dead-anthropic-models` | **Date**: 2026-04-28
**Purpose**: Provide the audit-grade verification contract for SC-001 through SC-006. This is the **machine-verifiable interface** of this epic — every reviewer (Codex automated, human, future maintainer) MUST be able to run these commands and observe the expected outputs without any other context.

> **Note**: This is a *deletion-driven* epic. There is no public API contract, no CLI surface change, no new endpoint. The "contract" exposed by this epic is the **audit chain** that proves the deletion succeeded.

---

## Contract C1 — Regex 0-hit audit (FR-001 / FR-007 / FR-008 / SC-001)

**Command**:

```bash
rg -n -i 'claude-3|claude-opus|claude-sonnet|claude-haiku|"sonnet"|"opus"|"haiku"|anthropic' \
   tui/src/utils/model/ \
   tui/src/services/mockRateLimits.ts \
   tui/src/services/rateLimitMocking.ts 2>/dev/null
```

**Expected output**: empty stdout (0 matches). After this epic ships, `mockRateLimits.ts` and `rateLimitMocking.ts` do not exist (so `rg` reports them as not found, exit 0); `tui/src/utils/model/` directory contains 0 case-insensitive matches.

**Pass condition**: stdout is empty AND exit code is 0 (or 1 if `rg` treats "no matches" as exit 1; either is acceptable).

---

## Contract C2 — File-deletion audit (FR-002 / FR-003)

**Commands**:

```bash
test ! -f tui/src/services/mockRateLimits.ts && echo "C2.1 PASS"
test ! -f tui/src/services/rateLimitMocking.ts && echo "C2.2 PASS"
```

**Expected output**:

```
C2.1 PASS
C2.2 PASS
```

**Pass condition**: both lines printed.

---

## Contract C3 — Single-source-of-truth audit (FR-004 / FR-012 / SC-002)

**Command**:

```bash
rg -n 'K-EXAONE-236B-A23B' --type ts --type py | sort -u
```

**Expected output**: matches confined to **at most three lines**:

```
src/kosmos/llm/config.py:37:    default="LGAI-EXAONE/K-EXAONE-236B-A23B",
tui/src/utils/model/model.ts:179:  return 'LGAI-EXAONE/K-EXAONE-236B-A23B'
tui/src/utils/model/model.ts:187:  return 'LGAI-EXAONE/K-EXAONE-236B-A23B' as ModelName
```

**Pass condition**: ≤ 3 lines of output, all in the two source-of-truth files (`config.py:37` and `model.ts:179,187`). Doc/spec files are excluded from this audit (they may legitimately contain the constant in prose).

---

## Contract C4 — Sampling defaults preservation audit (FR-013)

**Command**:

```bash
rg -n 'temperature: float = 1\.0|top_p: float = 0\.95|presence_penalty: float = 0\.0|max_tokens: int = 1024' \
   src/kosmos/llm/client.py
```

**Expected output**: at least 8 lines (4 parameters × 2 sites: non-streaming `:161-164` and streaming `:288-291`).

**Pass condition**: ≥ 8 matches at the expected line ranges.

---

## Contract C5 — Rate-limit retry preservation audit (FR-014)

**Command**:

```bash
rg -n 'class RetryPolicy|_compute_rate_limit_delay|_is_rate_limit_envelope|_complete_with_retry|_stream_with_retry' \
   src/kosmos/llm/client.py
```

**Expected output**: at least 5 declarations matching the five names listed (RetryPolicy class, two private methods for delay/envelope, two retry-loop methods).

**Pass condition**: all 5 names found at lines unchanged from baseline (exact line numbers may shift; presence is required).

---

## Contract C6 — `enable_thinking` toggle preservation audit (FR-015)

**Command**:

```bash
rg -n 'KOSMOS_K_EXAONE_THINKING|chat_template_kwargs' src/kosmos/llm/client.py
```

**Expected output**: at least 2 matches (env-var read at `:838-844`, payload field at `:854-858`).

**Pass condition**: ≥ 2 matches.

---

## Contract C7 — Dependency-set audit (FR-009 / SC-005)

**Commands**:

```bash
git diff main...HEAD -- tui/package.json | rg -c '^\+' | head -1
git diff main...HEAD -- pyproject.toml | rg -c '^\+' | head -1
```

A more precise command extracts just the dependencies sections:

```bash
git diff main...HEAD -- tui/package.json pyproject.toml | \
   awk '/^[+-]\s*"[^"]+"\s*:\s*"[^"]+"/ && /dependencies|devDependencies/ { print }' | \
   rg -E '^\+\s*"' | wc -l
```

**Expected output**: 0

**Pass condition**: zero added lines under any `dependencies` / `devDependencies` key.

---

## Contract C8 — Test baseline audit (FR-010 / SC-004)

**Commands**:

```bash
cd tui && bun test 2>&1 | tail -3
cd .. && uv run pytest 2>&1 | tail -3
```

**Expected output**: bun reports `≥ 984 pass`; pytest reports `≥ 437 passed`.

**Pass condition**: both counts ≥ baseline.

---

## Contract C9 — Citizen smoke audit via expect text-log (FR-011 / SC-003)

Per memory `feedback_vhs_tui_smoke` (TUI text-log smoke): smoke is automated via `expect` heredoc producing a plain-text log. LLM / Codex / human reviewers all grep the log directly. GIF/PNG are visual aids only (binary, not grep-able).

**Smoke recipe** (`specs/2112-dead-anthropic-models/smoke.expect`):

```expect
#!/usr/bin/env expect
set timeout 90
log_file -a specs/2112-dead-anthropic-models/smoke.txt

spawn bun run tui
expect ">"

send "Hi\r"
sleep 12

send "강남역 어디?\r"
sleep 45

send "/quit\r"
expect eof
```

**Run command**:

```bash
chmod +x specs/2112-dead-anthropic-models/smoke.expect
specs/2112-dead-anthropic-models/smoke.expect
```

**Audit commands** (run after the recording finishes):

```bash
echo "C9.1 Korean reply paint:" && grep -E '[가-힣]' specs/2112-dead-anthropic-models/smoke.txt | head -3
echo "C9.2 Lookup primitive call:" && grep -E 'lookup|resolve_location' specs/2112-dead-anthropic-models/smoke.txt | head -3
echo "C9.3 No legacy rate-limit headers:" && grep -F 'anthropic-ratelimit-unified' specs/2112-dead-anthropic-models/smoke.txt && echo FAIL || echo PASS
echo "C9.4 No model-selection prompt:" && grep -Ei 'pick a model|select a model|claude-3|claude-opus|claude-sonnet|claude-haiku' specs/2112-dead-anthropic-models/smoke.txt && echo FAIL || echo PASS
```

**Pass conditions** (text-log grep):
1. C9.1 — at least one Korean (Hangul) character appears in the assistant reply lines.
2. C9.2 — `lookup` (or `resolve_location`) tool-call appears in the transcript.
3. C9.3 — zero `anthropic-ratelimit-unified` matches.
4. C9.4 — zero model-selection prompt or legacy-Anthropic-name matches.

**Fallback** (no `expect` available): `script -q smoke.txt bun run tui < smoke-input.txt` where `smoke-input.txt` contains `Hi\n강남역 어디?\n/quit\n`. PR description must explicitly note fallback used.

---

## Contract C10 — LOC reduction audit (SC-006)

**Command**:

```bash
wc -l tui/src/utils/model/modelOptions.ts tui/src/utils/model/model.ts 2>/dev/null
```

**Expected output**: total LOC across the two surviving files ≤ 1 211 (40 % drop from baseline 2 019; mockRateLimits.ts deleted at 882 LOC).

**Pass condition**: total ≤ 1 211 LOC.

---

## Contract C11 — Helper alias annotations (FR-006)

**Command**:

```bash
rg -n -B1 -A2 'getDefaultSonnetModel|getDefaultOpusModel|getDefaultHaikuModel' \
   tui/src/utils/model/model.ts
```

**Expected output**: each helper body either:
(a) does not exist (file does not export the helper) — meaning all callers were prunable, OR
(b) contains the marker `[Deferred to P2 — issue #NNN]` (where `NNN` is resolved by `/speckit-taskstoissues`)

**Pass condition**: at least one of (a) or (b) holds for each of the three helpers.

---

## Audit run order (recommended)

1. C2 — file-deletion check (fastest, fails immediately if rebase is broken)
2. C1 — regex audit (the headline result)
3. C3 — single-source-of-truth (verifies no new K-EXAONE literals)
4. C7 — dependency-set audit (AGENTS.md hard-rule check)
5. C4 / C5 / C6 — Python preservation audits (FR-013/014/015)
6. C10 — LOC reduction audit (SC-006)
7. C11 — helper alias annotations (FR-006)
8. C8 — test baseline (slowest, blocking gate for merge)
9. C9 — citizen smoke (manual; required before merge)

A reviewer who runs C1–C7 and C10–C11 in sequence completes the static audit in ≤ 60 seconds. C8 takes 2–5 minutes. C9 is manual.
