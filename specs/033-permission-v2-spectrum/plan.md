# Implementation Plan: Permission v2 — Mode Spectrum · Persistent Rule Store · PIPA Consent Ledger

**Branch**: `033-permission-v2-spectrum` | **Date**: 2026-04-20 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/033-permission-v2-spectrum/spec.md`
**Parent Epic**: #1297 · Epic B (Claude Code 5-mode + PIPA 동의 원장)

## Summary

Port Claude Code 2.1.88's external PermissionMode spectrum (`default` / `plan` / `acceptEdits` / `bypassPermissions` / `dontAsk`) to KOSMOS's citizen-API harness, layer a persistent tri-state (`allow | ask | deny`) per-adapter rule store (Continue.dev-style `~/.kosmos/permissions.json`) on top, and anchor every data-access session to a hash-chained + HMAC-sealed PIPA consent ledger (`~/.kosmos/consent_ledger.jsonl`) whose record schema is Kantara Consent Receipt v1.1.0 + ISO/IEC 29184 notice-binding + KOSMOS scope extensions. Preserves Spec 024 `ToolCallAuditRecord` coupling via `consent_receipt_id` and Spec 025 V6 AAL backstop invariants — Permission v2 is a **layer on top** of those, never a replacement. Killswitch (FR-B01..B04) is NON-NEGOTIABLE per Constitution §II: `is_irreversible=True` adapters are never silent under any mode or rule, and `is_personal_data=True` + AAL≥2 calls are never allowed without a valid ledger receipt. Delivery factored into five parallel-safe workstreams (WS1 Mode engine + TUI keychord, WS2 Rule store + atomic write, WS3 Consent ledger + hash-chain, WS4 Killswitch + LLM synthesis guard, WS5 Integration with Spec 024/025/021) for Agent Teams dispatch at `/speckit-implement`. **Zero new runtime dependencies** (AGENTS.md hard rule) — stdlib `hashlib` / `hmac` / `secrets` / `json` / `pathlib` / `os.rename` only.

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing project baseline); TypeScript 5.6+ with Bun v1.2.x (TUI layer, existing Spec 287 runtime — Shift+Tab + slash commands already routed).
**Primary Dependencies**: `pydantic >= 2.13` (PermissionRule / ConsentDecision / ToolPermissionContext frozen models + discriminated unions, existing), `pydantic-settings >= 2.0` (env catalog — `KOSMOS_PERMISSION_*` knobs for timeout/TTL/key-path, existing), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (span attributes `kosmos.permission.mode` / `kosmos.permission.decision` / `kosmos.consent.receipt_id` from Spec 021, existing), `pytest` + `pytest-asyncio` (existing test stack). Stdlib `hashlib` (SHA-256 chain), `hmac` (HMAC-SHA-256 seal), `secrets` (key generation), `json` + `orjson`-free canonical JSON via **RFC 8785 JCS** (custom `kosmos.permissions.canonical_json` module, no external dep), `pathlib` + `os.rename` (atomic rule-store writes), `fcntl` (POSIX advisory lock on ledger append). **Zero new runtime dependencies** (AGENTS.md hard rule; SC-008 companion lint).
**Storage**:
- `~/.kosmos/permissions.json` — Continue.dev-style tri-state rule store, JSON object, schema-validated at boot, atomic writes via `tmpfile + os.rename`.
- `~/.kosmos/consent_ledger.jsonl` — append-only NDJSON, SHA-256 hash chain + HMAC-SHA-256 seal, WORM enforced in software (no update/delete API), POSIX advisory lock on append.
- `~/.kosmos/keys/ledger.key` — 32-byte HMAC secret, mode 0400, generated via `secrets.token_bytes(32)` on first boot, fail-closed on missing/wrong-mode.
- All three lives under user home (single-user MVP). Multi-device sync explicitly deferred (spec.md Deferred item #2).
**Testing**: `uv run pytest` — unit (PermissionMode transitions, rule-store schema violations, hash-chain canonicalization round-trip, HMAC seal verification), contract (JSON Schema Draft 2020-12 for permissions.json + consent_ledger.jsonl record + CLI schemas), integration (5 user stories via `pytest-asyncio` fixtures with mock HIRA/민원24 adapters), property (4-tuple-completeness via Hypothesis, chain-break detection on single-byte fuzz × 20), lint (SC-008 `pyproject.toml` diff guard — no new deps). No live `data.go.kr` calls (AGENTS.md Hard Rule).
**Target Platform**: macOS / Linux (POSIX advisory locks + 0400 file modes). Windows support explicitly deferred (same mechanism gap as Spec 032 Deferred #5; cross-referenced — not a new deferral here).
**Project Type**: Library — new `src/kosmos/permissions/` package + new TUI `tui/src/permissions/` component tree. No net-new top-level packages outside these two.
**Performance Goals**: Permission evaluation overhead p50 ≤ 5 ms, p99 ≤ 20 ms including rule-store lookup + ledger append (SC-008). Ledger chain verification ≥ 1000 records/sec (property test). Shift+Tab mode cycle render ≤ 16 ms (1 animation frame).
**Constraints**: Append-only ledger invariant enforced in software (no update/delete API surface). HMAC key rotation is yearly, manual, single-key (single-user MVP; policy table encoded as module constant, change requires ADR). 4-tuple (PIPA §15(2)) completeness is a property-test invariant — UI cannot render a prompt missing any of {목적·항목·보유기간·거부권}. Killswitch checks (Constitution §II) execute **before** mode/rule evaluation and cannot be short-circuited by any config surface.
**Scale/Scope**: Single-user local hness — rule-store expected O(10²) rules, ledger expected O(10⁴) records per year. Hash-chain verification is O(n) linear scan; acceptable for this cardinality. Ledger file rotation (size-based archival) deferred (spec.md Deferred #3 — Audit Archive Epic).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Check | Status |
|---|-----------|-------|--------|
| I | Reference-Driven | Every FR maps to a concrete reference (research.md § 1): FR-A* → Claude Code `PermissionMode.ts` + `permissionSetup.ts`; FR-B* → Claude Code bypass killswitch + OpenAI Agents SDK guardrails; FR-C* → Continue.dev `permissions.yaml`; FR-D* → Kantara CR v1.1.0 + ISO/IEC 29184 + NIST SP 800-92 hash-chain pattern; FR-E* → MEMORY `project_pipa_role` + AI 기본법 §27; FR-F* → Specs 024 / 025 / 021. Permission Pipeline primary ref = OpenAI Agents SDK per Constitution §I mapping table; secondary = Claude Code reconstructed. No orphan decisions. | PASS |
| II | Fail-Closed Security (NON-NEGOTIABLE) | Killswitch (FR-B01..B04) runs **before** mode evaluation — cannot be overridden by any config. HMAC key missing / wrong mode → ledger append refused, tool call blocked (FR-D04 + US2 Scenario 3). Rule-store schema violation → rule store disabled + fallback to `default` + prompt-always (FR-C02). 4-tuple incomplete → UI blocks prompt render (FR-D03 + SC-006). Automation on irreversible tool → `RequireHumanOversight` (FR-B03). No silent defaults — all failure modes explicit. | PASS |
| III | Pydantic v2 Strict Typing | `PermissionMode`, `PermissionRule`, `ConsentDecision`, `ToolPermissionContext`, `AdapterPermissionMetadata` all frozen Pydantic v2 `BaseModel` with `extra="forbid"` and concrete `Literal[...]` / `int ge=0` / `str min_length=1` fields (data-model.md § 1). No `Any`. JSON Schemas derived via `TypeAdapter.json_schema()`. Canonical JSON (RFC 8785 JCS) is a sort+escape-normalization helper, not a schema bypass. | PASS |
| IV | Gov API Compliance | No live `data.go.kr` calls (integration tests use mock HIRA + mock 민원24 adapters). Per-adapter `purpose_categories` + `consent_validity_period` metadata (FR-D07 + FR-D09) couples to Spec 024 `GovAPITool` extension surface. Recorded-fixture test pattern unchanged. | PASS |
| V | Policy Alignment | PIPA §15(2) 4-tuple enforced at prompt UI (FR-D03 + SC-006); §18(2) purpose-limitation enforced via FR-D08 re-prompt trigger; §22(1) individual-consent enforced via FR-D07; §26 controller/processor role per MEMORY `project_pipa_role` — KOSMOS = 수탁자 default, LLM synthesis = controller-level carve-out (FR-E01). AI 기본법 §27 high-impact AI safeguards via FR-E02 (banner + `/escalate` + explainability). Korea AI Action Plan Principle 5/8/9 preserved. ISMS-P 2.9.4 + 안전성 확보조치 §8 two-year retention encoded in FR-D10. | PASS |
| VI | Deferred Work Accountability | 7 items in `Deferred to Future Work` table, all with `NEEDS TRACKING` pending `/speckit-taskstoissues`. 4 items in `Out of Scope (Permanent)`. Spec scans clean — no "separate epic" / "future phase" free-text without table entry. Phase 0 research.md § 2 re-validates each deferred entry. | PASS |

**Gate outcome**: PASS — proceed to Phase 0 research. No complexity tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/033-permission-v2-spectrum/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 — reference mapping + 5 open-question resolutions + deferred-item validation
├── data-model.md        # Phase 1 — Pydantic v2 entities + invariants + state transitions
├── quickstart.md        # Phase 1 — 5 citizen-scenario walkthroughs (US1..US5)
├── contracts/           # Phase 1 — JSON Schema + CLI + file-format contracts
│   ├── permissions-store.schema.json     # JSON Schema 2020-12 for ~/.kosmos/permissions.json
│   ├── consent-ledger-record.schema.json # JSON Schema 2020-12 for single ledger record
│   ├── consent-prompt.contract.md        # PIPA §15(2) 4-tuple UI contract
│   ├── ledger-verify.cli.md              # `kosmos permissions verify` CLI contract
│   └── mode-transition.contract.md       # Mode spectrum + killswitch invariants
└── checklists/
    └── requirements.md  # PASS — 7/7 sections (committed earlier)
```

### Source Code (repository root)

One new backend package + one new TUI package tree. No modification of existing Spec 024/025/021/027/032 packages (Permission v2 is a layer that **consumes** their surfaces; it does not modify them).

```text
src/kosmos/permissions/                             # NEW package (WS1..WS5)
├── __init__.py                                     # public exports
├── modes.py                                        # WS1 — PermissionMode + transitions (FR-A01..A05)
├── context.py                                      # WS1 — ToolPermissionContext frozen model (FR-A04)
├── rules.py                                        # WS2 — PermissionRule + RuleStore + atomic write (FR-C01..C05)
├── canonical_json.py                               # WS3 — RFC 8785 JCS encoder (SC-003 dependency)
├── ledger.py                                       # WS3 — ConsentDecision + LedgerAppender + hash-chain (FR-D01..D10)
├── ledger_verify.py                                # WS3 — chain + HMAC verification (CLI backend, FR-D05)
├── hmac_key.py                                     # WS3 — key load / mode-check / yearly rotation (FR-D04)
├── prompt.py                                       # WS4 — 4-tuple prompt builder + render guard (FR-D03, SC-006)
├── killswitch.py                                   # WS4 — irreversible + AAL pre-evaluation (FR-B01..B04, NON-NEGOTIABLE)
├── synthesis_guard.py                              # WS4 — LLM pseudonymization boundary (FR-E01)
├── adapter_metadata.py                             # WS5 — AdapterPermissionMetadata (FR-F01 coupling w/ Spec 024)
├── audit_coupling.py                               # WS5 — consent_receipt_id ↔ ToolCallAuditRecord link (FR-F01)
├── aal_backstop.py                                 # WS5 — Spec 025 V6 invariant preservation (FR-F02)
├── otel_spans.py                                   # WS5 — Spec 021 attribute emission (FR-F03)
└── cli.py                                          # WS3 — `kosmos permissions verify` + `/permissions` backend

tui/src/permissions/                                # NEW package (WS1 + WS4 UI slice)
├── index.ts                                        # public exports
├── ModeStatusBar.tsx                               # WS1 — status bar + high-risk color (FR-A04)
├── ShiftTabCycler.ts                               # WS1 — Shift+Tab keychord cycling (FR-A02)
├── SlashCommands.ts                                # WS1 — /permissions bypass|dontAsk|list|edit (FR-A03, FR-C05)
├── ConsentPrompt.tsx                               # WS4 — PIPA §15(2) 4-tuple prompt UI (FR-D03)
├── HighRiskModeBanner.tsx                          # WS4 — visual warning for bypass/dontAsk (FR-A03)
├── PermissionsEditor.tsx                           # WS4 — /permissions TUI editor (FR-C05)
└── __tests__/
    ├── mode-cycle.test.ts                          # WS1 (SC-001)
    ├── consent-prompt.schema.test.ts               # WS4 (SC-006 4-tuple completeness)
    └── high-risk-timeout.test.ts                   # WS1 (SC-007)

tests/permissions/                                  # NEW test root
├── test_mode_spectrum.py                           # WS1 (SC-001, 5 modes × 1 acceptance each)
├── test_mode_transitions.py                        # WS1 (FR-A02, FR-A05)
├── test_rule_store_tri_state.py                    # WS2 (US4 Scenarios 1-3)
├── test_rule_store_atomic_write.py                 # WS2 (FR-C03, crash-inject via monkeypatch)
├── test_rule_store_schema_violation.py             # WS2 (FR-C02, fail-closed)
├── test_ledger_append_chain.py                     # WS3 (FR-D04, happy path)
├── test_ledger_hmac_seal.py                        # WS3 (FR-D04, key-missing fail-closed)
├── test_ledger_verify_cli.py                       # WS3 (FR-D05 + SC-003)
├── test_ledger_chain_fuzz.py                       # WS3 (SC-003, Hypothesis 20-run single-byte fuzz)
├── test_canonical_json_jcs.py                      # WS3 (RFC 8785 conformance — research.md § 3.3)
├── test_killswitch_irreversible.py                 # WS4 (FR-B01, SC-002 × 5 modes)
├── test_killswitch_personal_data_aal.py            # WS4 (FR-B02)
├── test_killswitch_automation_human_oversight.py   # WS4 (FR-B03)
├── test_prompt_4tuple_completeness.py              # WS4 (SC-006, Hypothesis property)
├── test_high_risk_mode_auto_expire.py              # WS1 (SC-007 ±1s precision)
├── test_audit_coupling_consent_receipt_id.py       # WS5 (SC-009, Spec 024 join integrity)
├── test_aal_backstop_preservation.py               # WS5 (FR-F02, Spec 025 V6 regression)
├── test_otel_permission_spans.py                   # WS5 (FR-F03)
├── test_synthesis_pseudonym_guard.py               # WS4 (FR-E01 fail-closed)
├── test_withdraw_consent_flow.py                   # WS3 (US2 Scenario 2)
├── test_reconciliation_rule_ledger_drift.py        # WS3 (Edge Case: rule-store vs ledger)
└── test_no_new_runtime_deps.py                     # SC-008 lint companion (pyproject.toml diff guard)
```

**Structure Decision**: Brand-new `src/kosmos/permissions/` backend package and `tui/src/permissions/` TUI package — Permission v2 is a cross-cutting concern and gets its own namespace rather than sprawling across `ipc/` / `tools/` / `services/`. The package boundary mirrors the Constitution §I layer mapping: Permission Pipeline is its own layer. Five workstream boundaries map cleanly: WS1 owns `modes.py` + `context.py` + TUI `ModeStatusBar`/`ShiftTabCycler`/`SlashCommands`; WS2 owns `rules.py` + rule-store tests; WS3 owns `ledger.py` + `ledger_verify.py` + `hmac_key.py` + `canonical_json.py` + `cli.py` + ledger tests; WS4 owns `killswitch.py` + `prompt.py` + `synthesis_guard.py` + TUI `ConsentPrompt`/`HighRiskModeBanner`/`PermissionsEditor` + killswitch tests; WS5 owns `adapter_metadata.py` + `audit_coupling.py` + `aal_backstop.py` + `otel_spans.py` + integration tests with Specs 024/025/021. Cross-workstream contracts are expressed via Pydantic class imports from `modes.py` + `ledger.py` — those two modules land first (WS1 + WS3 core), WS2/4/5 extend behaviorally.

## Parallel-Safe Workstream Factoring (for Agent Teams at `/speckit-implement`)

Five independent streams; WS1 + WS3 core models land first (≈1.5 hours, foundational), then WS2 / WS4 / WS5 concurrent. The 5-stream split is deliberately one more than Spec 032's 4-stream — the PIPA ledger (WS3) is heavy enough on canonical JSON + HMAC + CLI surface to deserve its own Teammate, and WS5 integration couples three existing specs (024/025/021) which benefits from a dedicated Teammate who only reads their contracts without modifying them.

| Stream | Scope | Files owned | Dependencies |
|--------|-------|-------------|--------------|
| **WS1** — Mode Engine + TUI Keychord | 5 external modes + transitions + Shift+Tab cycle + slash commands + auto-expiry; status bar; `ToolPermissionContext` injection | `modes.py`, `context.py`, `ModeStatusBar.tsx`, `ShiftTabCycler.ts`, `SlashCommands.ts`, `HighRiskModeBanner.tsx`, `test_mode_spectrum.py`, `test_mode_transitions.py`, `test_high_risk_mode_auto_expire.py`, `mode-cycle.test.ts`, `high-risk-timeout.test.ts` | none (foundational) |
| **WS2** — Rule Store + Atomic Write | Tri-state rule registry; schema validation at boot; atomic `tmpfile + rename` writes; `/permissions` editor TUI; fail-closed fallback on schema violation | `rules.py`, `PermissionsEditor.tsx`, `test_rule_store_tri_state.py`, `test_rule_store_atomic_write.py`, `test_rule_store_schema_violation.py` | WS1 model surface (`PermissionMode`, `ToolPermissionContext`) |
| **WS3** — Consent Ledger + Hash-Chain + CLI | RFC 8785 JCS encoder; SHA-256 chain + HMAC-SHA-256 seal; `LedgerAppender` + POSIX advisory lock; HMAC key load/rotation; `kosmos permissions verify` CLI; withdraw flow; reconciliation on drift | `canonical_json.py`, `ledger.py`, `ledger_verify.py`, `hmac_key.py`, `cli.py`, `test_ledger_append_chain.py`, `test_ledger_hmac_seal.py`, `test_ledger_verify_cli.py`, `test_ledger_chain_fuzz.py`, `test_canonical_json_jcs.py`, `test_withdraw_consent_flow.py`, `test_reconciliation_rule_ledger_drift.py` | Kantara CR v1.1.0 + ISO 29184 spec references (external); WS1 model surface |
| **WS4** — Killswitch + Prompt + Synthesis Guard | NON-NEGOTIABLE pre-evaluation of irreversible / personal-data+AAL / automation-on-irreversible; 4-tuple prompt builder + render guard; LLM pseudonymization boundary; `RequireHumanOversight` error type | `killswitch.py`, `prompt.py`, `synthesis_guard.py`, `ConsentPrompt.tsx`, `test_killswitch_irreversible.py`, `test_killswitch_personal_data_aal.py`, `test_killswitch_automation_human_oversight.py`, `test_prompt_4tuple_completeness.py`, `test_synthesis_pseudonym_guard.py`, `consent-prompt.schema.test.ts` | WS1 + WS3 model surfaces |
| **WS5** — Integration (Specs 024/025/021) | `AdapterPermissionMetadata` extension matrix; `consent_receipt_id` ↔ `ToolCallAuditRecord` join; Spec 025 V6 AAL backstop preservation; Spec 021 OTEL span attributes | `adapter_metadata.py`, `audit_coupling.py`, `aal_backstop.py`, `otel_spans.py`, `test_audit_coupling_consent_receipt_id.py`, `test_aal_backstop_preservation.py`, `test_otel_permission_spans.py` | WS1 + WS3 + WS4 model surfaces; Specs 024/025/021 schemas (read-only) |

**Lead/Teammate assignment** (per AGENTS.md § Agent Teams):
- WS1 → Backend Architect (Sonnet, `modes.py` + `context.py`) + Frontend Developer (Sonnet, Ink components + keychord tests), parallel.
- WS2 → Backend Architect (Sonnet) — single-cluster scope, solo.
- WS3 → Backend Architect (Sonnet, ledger core + canonical JSON + HMAC) + Security Engineer (Sonnet, spot-review HMAC key handling + chain fuzz).
- WS4 → Backend Architect (Sonnet, killswitch + synthesis guard) + Frontend Developer (Sonnet, ConsentPrompt 4-tuple UI), parallel.
- WS5 → Backend Architect (Sonnet) — integration-only scope, reads Specs 024/025/021 without modifying; solo.
- Cross-cutting review → Code Reviewer (Opus) after each WS merge.
- Security spot-check → Security Engineer (Sonnet) on WS3 (ledger + HMAC) and WS4 (killswitch) specifically — these two are the Constitution §II surface.
- API Tester (Sonnet) owns the SC-001..SC-009 test coverage gate (runs final, after WS1..WS5 lands).

**Sub-Issue budget** (per MEMORY `feedback_subissue_100_cap`): 5 workstreams × typical 8–14 tasks each = target 50–70 Task sub-issues, well under the 90-task budget. `/speckit-tasks` will apply cohesion merging where single-cluster work is split across > 3 files.

## Complexity Tracking

No constitution violations detected. No complexity entries required.

## Post-Design Constitution Re-check (Phase 1 exit gate)

*Re-evaluated after generating `research.md`, `data-model.md`, `contracts/*`, `quickstart.md`.*

| # | Principle | Post-design check | Status |
|---|-----------|-------------------|--------|
| I | Reference-Driven | `research.md § 1` maps every FR group to a concrete reference (Claude Code `PermissionMode.ts` / `permissionSetup.ts` / `bypassPermissionsKillswitch.ts`; Kantara CR v1.1.0; ISO/IEC 29184:2020; RFC 8785 JCS; NIST SP 800-92; Continue.dev permissions.yaml; OpenAI Agents SDK guardrails; MEMORY `project_pipa_role`; Specs 024/025/021/027/287/032). `data-model.md § 1` cites reference per entity. `contracts/consent-prompt.contract.md` cites PIPA §15(2) verbatim. No orphan decisions. | PASS |
| II | Fail-Closed Security (NON-NEGOTIABLE) | `data-model.md § 1.*` pins `extra="forbid"` on every model; § 2 enumerates invariants K1–K6 (killswitch pre-evaluation + irreversible-never-silent + AAL-consent-coupling + HMAC-key-mode-0400 + 4-tuple-completeness + append-only-WORM). `contracts/mode-transition.contract.md § 3` enumerates explicit rejection paths. `contracts/ledger-verify.cli.md` declares exit-code ≠ 0 on any chain break, no silent tolerance. | PASS |
| III | Pydantic v2 Strict Typing | `data-model.md § 1.1..1.6` — every entity is `BaseModel(frozen=True, extra="forbid")` with concrete `Literal[...]`, `StrictStr(min_length=1)`, `conint(ge=0)` types. JSON Schema in `contracts/permissions-store.schema.json` + `contracts/consent-ledger-record.schema.json` mirror via `TypeAdapter.json_schema()` — round-trip test in `quickstart.md § 1.1`. Canonical JSON (RFC 8785) is deterministic encoder on top of validated models, not a typing bypass. | PASS |
| IV | Gov API Compliance | `quickstart.md § 0` forbids live `data.go.kr` calls in all 5 scenarios (mock HIRA + mock 민원24 adapters). `AdapterPermissionMetadata` (data-model.md § 1.6) couples to Spec 024 `GovAPITool` via `consent_receipt_id` — every adapter call emits a ledger-linked audit record. `contracts/consent-prompt.contract.md § 4` requires the `purpose_category` enum to match ministry-declared categories. | PASS |
| V | Policy Alignment | `contracts/consent-prompt.contract.md § 2` encodes PIPA §15(2) 4-tuple as a schema invariant — UI cannot render a prompt missing any field; `data-model.md § 1.3` invariant C3 encodes §18(2) purpose-limitation; `data-model.md § 1.3` invariant C5 encodes §22(1) individual-consent (no bundle). §26 수탁자 default + LLM synthesis controller-level carve-out encoded in `data-model.md § 1.7`. AI 기본법 §27 high-impact AI banner + `/escalate` + explainability in `quickstart.md § 6` (cross-scenario). ISMS-P 2.9.4 + 안전성 확보조치 §8 two-year retention encoded as a module constant in `ledger.py` (documented in data-model.md § 2). | PASS |
| VI | Deferred Work Accountability | `research.md § 2` deferred-item validation clean — 7 items, all NEEDS TRACKING, 4 permanent-out-of-scope items listed. `contracts/consent-prompt.contract.md § 6`, `contracts/ledger-verify.cli.md § 5`, `contracts/mode-transition.contract.md § 4` each end with "Out of scope" blocks pointing back to spec.md table. No new scope creep introduced during Phase 1. | PASS |

**Post-design gate**: PASS — no new violations, no new complexity entries. Ready for `/speckit-tasks`.

## Phase 1 Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Research | [`research.md`](./research.md) | Reference mapping per FR group · 5 open-question resolutions (Kantara license, Continue.dev adoption, RFC 8785, HMAC rotation, 7 deferred placeholders) · deferred-item validation · risk matrix |
| Data model | [`data-model.md`](./data-model.md) | Pydantic v2 entities (`PermissionMode`, `PermissionRule`, `ConsentDecision`, `ConsentLedger`, `ToolPermissionContext`, `AdapterPermissionMetadata`) · invariants K1–K6 + C1–C5 · state transitions |
| Rule-store schema | [`contracts/permissions-store.schema.json`](./contracts/permissions-store.schema.json) | JSON Schema 2020-12 for `~/.kosmos/permissions.json` |
| Ledger-record schema | [`contracts/consent-ledger-record.schema.json`](./contracts/consent-ledger-record.schema.json) | JSON Schema 2020-12 for single ledger JSONL line |
| Prompt contract | [`contracts/consent-prompt.contract.md`](./contracts/consent-prompt.contract.md) | PIPA §15(2) 4-tuple UI invariants + prompt-builder test matrix |
| Verify CLI contract | [`contracts/ledger-verify.cli.md`](./contracts/ledger-verify.cli.md) | `kosmos permissions verify` exit-code / output / failure-mode contract |
| Mode-transition contract | [`contracts/mode-transition.contract.md`](./contracts/mode-transition.contract.md) | 5-mode spectrum + Shift+Tab cycle + killswitch bypass-immunity invariants |
| Quickstart | [`quickstart.md`](./quickstart.md) | 5 citizen scenarios (US1..US5) + rollback + troubleshooting |
| Agent context | [`/CLAUDE.md`](../../CLAUDE.md) | Updated by `update-agent-context.sh claude` — added Python 3.12 / Pydantic v2 / stdlib hashlib-hmac / no-new-deps entry for 033 |
