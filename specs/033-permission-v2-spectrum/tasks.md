---
description: "Task list for 033-permission-v2-spectrum (Epic #1297)"
---

# Tasks: Permission v2 — 5-Mode Spectrum + PIPA Consent Ledger

**Input**: Design documents from `/specs/033-permission-v2-spectrum/`
**Prerequisites**: plan.md ✅, spec.md ✅, data-model.md ✅, contracts/ ✅, research.md ✅, quickstart.md ✅
**Epic**: #1297
**Budget**: 55 tasks (target ≤ 90 per Sub-Issues API cap + `feedback_subissue_100_cap`)

**Tests**: Tests ARE included — Constitution §II (fail-closed, NON-NEGOTIABLE) + SC-004 (byte-level tamper detection) + SC-007 (bypass killswitch re-prompt) require executable regression gates. All test tasks are labeled per story.

**Organization**: Tasks grouped by user story (US1–US5) + foundational + integration + polish. Each story is independently completable and testable per spec.md acceptance criteria.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no dependencies on incomplete tasks)
- **[Story]**: maps to spec.md US1..US5; setup/foundational/polish/integration carry no story label

## Path Conventions

- Backend: `src/kosmos/permissions/` (new package)
- TUI: `tui/src/permissions/` (new component tree, Ink + Bun + TypeScript 5.6)
- Tests: `tests/permissions/`
- Docs: `docs/security/permission-v2-*.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: scaffold package tree, test harness, env knobs — no behavioral code.

- [ ] T001 Create `src/kosmos/permissions/__init__.py` with `__version__ = "1.0.0"` and public re-exports (`PermissionMode`, `ToolPermissionContext`, `PermissionRule`, `ConsentLedgerRecord`)
- [ ] T002 [P] Create `tests/permissions/` directory + `conftest.py` with tmp-path fixtures for `permissions.json` / `consent_ledger.jsonl` / `keys/ledger.key` (mode 0400)
- [ ] T003 [P] Create `tui/src/permissions/` TypeScript component tree skeleton (`index.ts`, `types.ts` stubs) following Spec 287 conventions
- [ ] T004 [P] Register `KOSMOS_PERMISSION_*` env knobs (`TIMEOUT_SEC`, `TTL_SESSION_SEC`, `KEY_PATH`, `LEDGER_PATH`, `RULE_STORE_PATH`) in `src/kosmos/settings.py` pydantic-settings catalog

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: canonical JSON + HMAC key loader + core pydantic models + pipeline skeleton. Everything user-story-specific depends on this phase.

**⚠️ CRITICAL**: no US-tagged task may start until Phase 2 is complete.

- [ ] T005 Implement `src/kosmos/permissions/canonical_json.py` — RFC 8785 JCS encoder (stdlib-only, ~50 lines, sort keys, number canonicalization, UTF-8 NFC)
- [ ] T006 Add RFC 8785 Appendix A test vectors in `tests/permissions/test_canonical_json.py` (all 13 vectors must pass byte-identical)
- [ ] T007 [P] Implement `src/kosmos/permissions/modes.py` — `PermissionMode` Literal alias + mode adjacency table + `next_mode_shift_tab()` (default→plan→acceptEdits→default, escape hatch from bypass/dontAsk to default)
- [ ] T008 [P] Implement `src/kosmos/permissions/models.py` — pydantic v2 frozen models: `PermissionRule`, `ToolPermissionContext`, `AdapterPermissionMetadata`, `ConsentDecision`, `ConsentLedgerRecord`, `LedgerVerifyReport` (all `extra="forbid"`, `strict=True`, concrete Literals/StrictStr/constr)
- [ ] T009 Implement `src/kosmos/permissions/hmac_key.py` — load/generate `~/.kosmos/keys/ledger.key` (mode 0400 enforcement via `os.stat()`, `secrets.token_bytes(32)` on first boot, fail-closed refusal on mode drift)
- [ ] T010 [P] Implement `src/kosmos/permissions/adapter_metadata.py` — read-only projection from Spec 024 `GovAPITool` (fails closed if `is_irreversible` / `auth_level` / `pipa_class` missing — Invariant A1)
- [ ] T011 Implement permission pipeline skeleton `src/kosmos/permissions/pipeline.py` — ordered `killswitch.pre_evaluate() → mode.evaluate() → rule.resolve() → prompt.ask()` stubs that raise `NotImplementedError` (to be filled per story)
- [ ] T012 [P] Create CLI skeleton `src/kosmos/permissions/cli.py` with argparse + `pyproject.toml` entry point `kosmos-permissions = kosmos.permissions.cli:main`

**Checkpoint**: foundational package importable; `pytest tests/permissions/test_canonical_json.py` passes 13 JCS vectors.

---

## Phase 3: User Story 1 — 기본 모드 · 첫 HIRA 동의 (Priority: P1) 🎯 MVP

**Goal**: citizen runs `default` mode, first HIRA call shows PIPA 4-tuple prompt, `allow` persists for session, ledger gets 1 record.

**Independent Test**: mock HIRA adapter + `default` mode → 1 prompt + 2 silent executions + 1 ledger record chained to genesis.

- [ ] T013 [P] [US1] Implement `src/kosmos/permissions/rules.py` — tri-state rule store with session/project/user scope resolver (R1 deny-wins, R2 narrower-wins, R3 ask≡no-rule)
- [ ] T014 [US1] Extend `src/kosmos/permissions/rules.py` with atomic-write via `os.rename()` + JSON schema validation against `contracts/permissions-store.schema.json` on load (fail-closed on violation)
- [ ] T015 [P] [US1] Implement `src/kosmos/permissions/prompt.py::PIPAConsentPrompt` — 4-tuple builder (Invariant C1: all fields `StrictStr(min_length=1)`), individual-consent rule (Invariant C2: bundling 민감/고유식별/특수 raises `ValidationError`)
- [ ] T016 [US1] Implement `src/kosmos/permissions/ledger.py` — append path with fsync + `O_WRONLY|O_APPEND|O_CREAT` + `fcntl.LOCK_EX`, computes `prev_hash`/`record_hash`/`hmac_seal` via canonical JSON (Invariants L1–L5, C4)
- [ ] T017 [US1] Wire `default` mode behavior into `pipeline.py` — ASK every call unless persistent `allow` rule; persist user-approved rules to `~/.kosmos/permissions.json`
- [ ] T018 [US1] TUI: implement `tui/src/permissions/ConsentPrompt.tsx` — Ink component rendering 5-section prompt (title/목적/항목/보유기간/거부권+불이익), default focus on 거부, Y/N/ESC keyboard
- [ ] T019 [US1] TUI: wire `tui/src/permissions/consentBridge.ts` — round-trip consent request/decision over Spec 032 IPC envelope (uses `correlation_id` from `ToolPermissionContext`)
- [ ] T020 [US1] Emit OTEL spans `consent.prompt.shown` / `consent.prompt.decided` with attrs per contracts/consent-prompt §6
- [ ] T021 [P] [US1] Contract test `tests/permissions/test_prompt_contract.py` covering 16 T-matrix rows from contracts/consent-prompt.contract.md §4
- [ ] T022 [US1] Integration test `tests/permissions/test_us1_first_prompt.py` — mock HIRA adapter + default mode + 3 calls → 1 prompt + 2 silent + 1 ledger record (SC-001)

**Checkpoint**: MVP — US1 fully functional and testable independently. Stop here for first demo.

---

## Phase 4: User Story 2 — 외부 변조 탐지 (Priority: P1)

**Goal**: auditor flips a single byte in ledger; `kosmos permissions verify` exits non-zero with distinguishable reason.

**Independent Test**: 5-record ledger → flip 1 byte → verify exits 1 with `CHAIN_RECORD_HASH_MISMATCH` + points to first broken index.

- [ ] T023 [P] [US2] Implement `src/kosmos/permissions/ledger_verify.py` — streaming JSONL read, chain-walk with `prev_hash`↔`record_hash` check + HMAC-SHA-256 seal verification per record using key-ID registry (Invariants L2, L3, L4)
- [ ] T024 [US2] Wire `kosmos-permissions verify` subcommand in `cli.py` — implements contracts/ledger-verify.cli.md exit-code taxonomy (0/1/2/3/4/5/6/64), supports `--path`, `--hash-only`, `--acknowledge-key-loss`, `--json`
- [ ] T025 [US2] Implement `kosmos-permissions rotate-key` subcommand — archives `keys/ledger.key` → `keys/ledger.key.k0001`, generates new key at next sequence, records key-ID in registry
- [ ] T026 [P] [US2] Contract test `tests/permissions/test_ledger_verify_cli.py` covering 12 V-matrix scenarios from contracts/ledger-verify.cli.md §7 (exit codes + `broken_reason` mapping)
- [ ] T027 [US2] Integration test `tests/permissions/test_us2_tamper_detect.py` — quickstart scenario 2 end-to-end: write 5 records → single-byte flip → verify exit 1 (SC-004)

**Checkpoint**: US2 independently verified. External auditor workflow confirmed.

---

## Phase 5: User Story 3 — bypassPermissions · 되돌릴 수 없는 호출 킬스위치 (Priority: P1, NON-NEGOTIABLE)

**Goal**: Constitution §II — `bypassPermissions` mode NEVER silently executes irreversible / pipa_class=특수 / auth_level=AAL3 tools. Every such call re-prompts with distinct `action_digest`.

**Independent Test**: `is_irreversible=True` adapter + `bypassPermissions` mode + 2 calls → 2 prompts + 2 independent ledger records (K5, K6).

- [ ] T028 [P] [US3] Implement `src/kosmos/permissions/killswitch.py::pre_evaluate()` — returns `Decision.ASK` when mode=`bypassPermissions` AND (`is_irreversible` OR `pipa_class=특수` OR `auth_level=AAL3`); returns `None` otherwise (K2/K3/K4)
- [ ] T029 [US3] Wire killswitch as step 1 in `pipeline.py` BEFORE mode evaluation (Invariant K1/P1); add mutation test to assert order
- [ ] T030 [US3] Implement `bypassPermissions` mode behavior in `modes.py` / `pipeline.py` — silent-allow for non-killswitch calls; REJECT any attempt to cache killswitch-triggered prompts (K5)
- [ ] T031 [US3] Implement `action_digest` computation in `ledger.py` — SHA-256 over `(tool_id, canonical(arguments), uuid7_nonce)` so two identical bypass-mode irreversible calls get distinct digests (K6, FR-B04)
- [ ] T032 [P] [US3] TUI: implement `tui/src/permissions/BypassConfirmDialog.tsx` — warning dialog with 3-bullet killswitch reminder, default focus on "N" (Invariant UI2)
- [ ] T033 [US3] TUI: implement `tui/src/permissions/StatusBar.tsx` red/yellow flashing indicator when mode=`bypassPermissions` (Invariant UI1)
- [ ] T034 [US3] Emit OTEL span `permission.killswitch.triggered` with attrs `reason ∈ {irreversible, pipa_class_특수, aal3}` + `tool_id` + `mode`
- [ ] T035 [US3] Contract test `tests/permissions/test_killswitch_priority_order.py` — mutation asserting killswitch runs BEFORE mode/rule (Invariant K1); any re-ordering MUST fail the test
- [ ] T036 [US3] Integration test `tests/permissions/test_us3_bypass_killswitch.py` — bypassPermissions + irreversible adapter × 2 calls → 2 prompts + 2 distinct action_digests in ledger (SC-007)

**Checkpoint**: US3 Constitution §II compliance verified. Bypass-immunity property established.

---

## Phase 6: User Story 4 — Tri-state 영속화 · 세션 재시작 (Priority: P2)

**Goal**: persistent allow/deny/ask across process restarts; fail-closed on schema violation after external edit.

**Independent Test**: 3 rules (allow/deny/ask) → restart → each tool call produces expected behavior.

- [ ] T037 [US4] Implement session-restart behavior — process boot reloads `permissions.json`, resets `mode` to `default` (Invariant M3/PR1), retains `user` scope rules
- [ ] T038 [P] [US4] CLI: implement `/permissions allow|deny|ask|revoke <tool_id>` slash-command handlers in `src/kosmos/permissions/cli.py::rule_commands` (writes `user` scope rules via rules.py atomic write)
- [ ] T039 [US4] TUI: implement `tui/src/permissions/RuleListView.tsx` — `/permissions list` command renders current rules with scope + decision + created_at
- [ ] T040 [US4] Integration test `tests/permissions/test_us4_tri_state_persistence.py` — quickstart scenario 4 end-to-end: 3 rules → restart → 3 expected behaviors (SC-002)
- [ ] T041 [US4] Integration test `tests/permissions/test_us4_fail_closed_edit.py` — externally corrupt `permissions.json` → boot refuses to load, falls back to `default` mode with all rules cleared (FR-C02)

**Checkpoint**: US4 persistence + fail-closed on external tamper verified.

---

## Phase 7: User Story 5 — Shift+Tab 사이클 · 슬래시 명령 · 상태바 (Priority: P2)

**Goal**: Shift+Tab cycles default↔plan↔acceptEdits; `/permissions bypass|dontAsk` require confirmation; status bar color reflects current mode; bypass/dontAsk are reachable only via slash commands.

**Independent Test**: 4× Shift+Tab (full cycle) + `/permissions bypass` confirm + status color assertions per mode-transition.contract.md.

- [ ] T042 [P] [US5] TUI: implement Shift+Tab key handler in `tui/src/permissions/ModeCycle.tsx` — cycles default→plan→acceptEdits→default; from bypass/dontAsk returns directly to default (Invariant S1)
- [ ] T043 [US5] TUI: implement `/permissions bypass|dontAsk|default|list|edit|verify` slash-command routing in `tui/src/permissions/commandRouter.ts`
- [ ] T044 [US5] TUI: wire `tui/src/permissions/StatusBar.tsx` mode→color mapping (neutral/cyan/green/red-yellow-flash/blue) per mode-transition.contract.md §4
- [ ] T045 [US5] TUI: implement `/permissions dontAsk` confirmation dialog (mirrors BypassConfirmDialog, default focus N)
- [ ] T046 [US5] Emit OTEL span `permission.mode.changed` with attrs `from_mode`, `to_mode`, `trigger ∈ {shift_tab, slash_command}`, `confirmed: bool`
- [ ] T047 [US5] Integration test `tests/permissions/test_us5_mode_cycle.py` — quickstart scenario 5 end-to-end: 4× Shift+Tab + bypass confirm + status assertions covering all 17 M-matrix rows (SC-005, SC-006)

**Checkpoint**: US5 full mode spectrum + TUI keychord + slash commands verified.

---

## Phase 8: Integration & Cross-Cutting (FR-E + FR-F)

**Purpose**: couple Permission v2 to existing Specs 024 / 025 V6 / 021 without modifying their invariants; enforce LLM synthesis PII boundary.

- [ ] T048 [P] Implement `src/kosmos/permissions/audit_coupling.py` — populates Spec 024 `ToolCallAuditRecord.consent_receipt_id` + `correlation_id` (from Spec 032) on every tool call that required consent (FR-F01)
- [ ] T049 [P] Implement `src/kosmos/permissions/aal_backstop.py` — detects Spec 025 V6 AAL downgrade attempts (e.g., `auth_level=AAL3` at prompt time but `AAL1` at execution) → raises `AALDowngradeBlocked` (FR-F02 + edge case)
- [ ] T050 [P] Implement `src/kosmos/permissions/synthesis_guard.py::redact()` — scans adapter output schemas, drops fields tagged `pipa_class ∈ {민감, 고유식별}` before LLM prompt assembly (Invariant C5, FR-E02, MEMORY `project_pipa_role` LLM controller carve-out)
- [ ] T051 Wire permission-layer OTEL attrs (`kosmos.permission.mode`, `kosmos.permission.decision`, `kosmos.consent.receipt_id`) onto existing tool-call spans (FR-F03, Spec 021 coupling)
- [ ] T052 Integration test `tests/permissions/test_integration_spec_024_025_021.py` — end-to-end: consent prompt → decision → audit record has `consent_receipt_id` + AAL backstop + OTEL attrs present + synthesis_guard redacts 민감 fields

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T053 [P] Write `docs/security/permission-v2-threat-model.md` — documents R1–R8 risk matrix from research.md §4 + mitigations
- [ ] T054 [P] Lint: assert zero new runtime dependencies via `uv run python -c "import tomllib; import pathlib; prev = tomllib.loads(pathlib.Path('pyproject.toml.main').read_text())['project']['dependencies']; cur = tomllib.loads(pathlib.Path('pyproject.toml').read_text())['project']['dependencies']; assert set(cur) == set(prev)"` (SC-008)
- [ ] T055 Run full quickstart.md — reproduce all 5 scenarios end-to-end, confirm exit codes + ledger states match expected (final SC gate SC-001..SC-007, SC-009)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup** → no deps; start immediately.
- **Phase 2 Foundational** → depends on Phase 1; BLOCKS every US-tagged phase.
- **Phase 3 US1 (P1 MVP)** → depends on Phase 2; independent of US2–US5.
- **Phase 4 US2 (P1)** → depends on Phase 2 + T016 (ledger.append) from Phase 3 (shared ledger surface).
- **Phase 5 US3 (P1, NON-NEGOTIABLE)** → depends on Phase 2 + T011 (pipeline skeleton). Independent of US1/US2/US4/US5 functionally, but shares `pipeline.py` edit surface with US1 → serialize pipeline edits.
- **Phase 6 US4 (P2)** → depends on Phase 2 + US1 rule-store (T013/T014).
- **Phase 7 US5 (P2)** → depends on Phase 2 + US3 bypass dialog (T032) + TUI foundation from Spec 287.
- **Phase 8 Integration** → depends on all US phases (reads Spec 024 audit record shape, observes pipeline outputs).
- **Phase 9 Polish** → depends on Phase 8.

### Parallel Opportunities

- **Phase 1**: T002, T003, T004 run in parallel after T001.
- **Phase 2**: T005+T006 (canonical_json + tests) serialize; T007, T008, T010, T012 run in parallel; T009, T011 serialize after models land.
- **Phase 3 (US1)**: T013, T015, T021 run in parallel; T016/T017/T018 serialize on file `ledger.py` / `pipeline.py` edits.
- **Phase 4 (US2)**: T023, T026 run in parallel; T024, T025, T027 serialize.
- **Phase 5 (US3)**: T028, T032, T035 run in parallel; T029/T030/T031 serialize on `pipeline.py`.
- **Phase 6 (US4)**: T038 runs in parallel with T037; T039, T040, T041 serialize.
- **Phase 7 (US5)**: T042 runs in parallel with T043; T044/T045/T046/T047 serialize.
- **Phase 8**: T048, T049, T050 run in parallel; T051, T052 serialize.
- **Phase 9**: T053, T054 run in parallel; T055 final gate.

---

## Parallel Example — US1 Implementation Kickoff

```bash
# After Phase 2 completes, launch US1 parallel tracks:
Task: "[US1] Implement rules.py tri-state rule store — T013"
Task: "[US1] Implement PIPAConsentPrompt builder — T015"
Task: "[US1] Contract test test_prompt_contract.py (16 T-matrix rows) — T021"
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 (T001–T004) → Phase 2 (T005–T012) → Phase 3 (T013–T022).
2. Validate `quickstart.md` Scenario 1 end-to-end.
3. Demo → freeze MVP → proceed to P1 stories US2 + US3.

### Incremental Delivery Order

1. MVP = US1.
2. + US2 (tamper detection) — citizen + auditor confidence.
3. + US3 (killswitch) — Constitution §II compliance gate.
4. + US4 (persistence) — UX quality-of-life.
5. + US5 (mode cycle + status bar) — Claude Code parity.
6. Integration + Polish.

### Parallel Team Strategy (at `/speckit-implement`)

With 5 Teammates (Sonnet) + 1 Lead (Opus):

- Team completes Phase 1 + Phase 2 serially (foundational).
- Phase 3–7 (US1–US5) run in parallel per plan.md workstream factoring:
  - **WS1 Teammate**: Frontend Developer — TUI mode cycle + status bar (T018, T019, T032, T033, T040–T046)
  - **WS2 Teammate**: Backend Architect — Rule store + atomic write (T013, T014, T037–T041)
  - **WS3 Teammate**: Security Engineer — Ledger + hash chain + CLI verify (T016, T017, T023–T027)
  - **WS4 Teammate**: Backend Architect — Killswitch + prompt + synthesis guard (T015, T028–T031, T035, T050)
  - **WS5 Teammate**: Backend Architect — Integration with Specs 024/025/021 (T048, T049, T051, T052)
- Lead (Opus) cross-reviews at each checkpoint; final gate at T055.

---

## Deferred Items (NEEDS TRACKING → `/speckit-taskstoissues` placeholders)

Per research.md §2 + spec.md Scope Boundaries, these 7 items are out of scope for this Epic but must be tracked as placeholder sub-issues with `[Deferred]` prefix:

1. [Deferred] Wildcard rules (`tool_id: *`) support — target Epic: Permission v3
2. [Deferred] Consent receipt export to Kantara-registered 3rd-party registrar — target Epic: Consent Portability v1
3. [Deferred] Multi-key HMAC rotation with automatic time-based rollover — target Epic: Permission v2.1
4. [Deferred] `permissions.json` project-scope layer (repo-local) — target Epic: Permission v2.1
5. [Deferred] Consent prompt internationalization (EN/ZH/JA) — target Epic: I18N wave 1
6. [Deferred] Bypass-mode per-tool kill-switch override override (opt-out for non-destructive irreversible reads) — target Epic: Permission v3
7. [Deferred] AI 기본법 §31 고위험 사전고지 auto-banner — target Epic: AI 기본법 Compliance v1

---

## Budget Check

- Total `- [ ]` tasks emitted: **55** (T001–T055)
- Sub-Issues API cap: **90** (allowing 35-slot headroom per `feedback_subissue_100_cap`)
- Deferred placeholders (separate sub-issues): **7** (will be materialized at `/speckit-taskstoissues`)
- Projected Epic #1297 sub-issue total: **55 + 7 = 62** (under cap ✅)

---

## Notes

- [P] = different files + no open dependencies; run in parallel.
- [Story] label maps to spec.md US1..US5.
- Every US-tagged phase has an `Independent Test` criterion that maps 1:1 to spec.md US acceptance scenarios + at least one SC-NNN success criterion.
- Tests-first is NON-NEGOTIABLE for T021 (prompt contract), T026 (ledger verify CLI), T035 (killswitch priority order) — these gate Constitution §II.
- Zero new runtime dependencies (AGENTS.md hard rule + SC-008). T054 enforces.
- All file paths are concrete; no "[fill-in]" placeholders remain.
