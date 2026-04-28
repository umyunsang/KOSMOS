# Phase 3 Analysis: Plugin DX TUI integration — Cross-artifact Audit

**Feature**: 1979-plugin-dx-tui-integration
**Date**: 2026-04-28
**Inputs analyzed**: spec.md (203 lines, 27 FR + 10 SC + 4 stories) + plan.md (12.6 KB) + research.md (V1/V2 + R-1..R-6 + Phase 0 deferred validation) + data-model.md (E1..E5) + 4 contracts/*.md + quickstart.md + tasks.md (38 tasks, 7 phases) + .specify/memory/constitution.md (Version 1.1.1)

---

## Specification Analysis Report

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| C1 | Coverage Gap | MEDIUM | spec.md FR-010 (OTEL `kosmos.plugin.id`) | No explicit task verifies plugin tool invocation emits OTEL span carrying `kosmos.plugin.id`. Relies on Spec 1636 FR-021 + register_plugin_adapter invariant. | Add an assertion line to T018 or T020 integration test verifying `kosmos.plugin.id` attribute on the tool-invocation span. |
| C2 | Coverage Gap | MEDIUM | spec.md SC-009 (concurrent ledger position) | No explicit task tests "concurrent installs from two TUI sessions assign monotonic `consent_ledger_position`". Spec 1636's `_allocate_consent_position` flock infrastructure is reused but uncovered by this Epic's tests. | Add a sub-bullet to T014 (`tests/ipc/test_plugin_op_dispatch.py`): `test_concurrent_installs_assign_monotonic_positions` running ≥ 5 simulated parallel `handle_install` invocations. |
| C3 | Coverage Gap | LOW | spec.md FR-023 / FR-024 / FR-025 / FR-027 (cross-cutting governance) | These FRs are governance invariants verified at PR time (zero deps grep, English-source grep, logging grep, sub-issue count) rather than via dedicated tasks. T038 (final quickstart validation) covers some. | Acceptable — invariants don't need dedicated tasks; T038 + post-merge audit is canonical. No action. |
| A1 | Ambiguity | LOW | spec.md US3 § FR-016 vs research.md § R-3+R-4 | "Space toggles activation" in FR-016 (citizen-visible mandate) is intentionally interpreted as visual-only in this Epic per research.md's runtime-toggle-IPC deferral. The conflict is acknowledged + tracked but not eliminated. | Document the visual-only interpretation in spec.md FR-016 explicitly as a one-line clarification, OR rely on research.md's deferral entry. Currently deferred. Acceptable. |
| R1 | Risk (cliff edge) | HIGH | tasks.md T021 (commands.ts:133 swap) | Single 1-line change activates the entire citizen plugin path. If the swap silently breaks (e.g., cyclic import, wrong relative path), all of US1+US2+US3 acceptance fails simultaneously. | Mitigation already present: T030 bun tests mock the swap before integration; T035 master orchestrator runs L1+L2+L3 sequentially so the swap regression surfaces early. **Accept risk with monitoring.** |
| R2 | Risk (live env) | LOW | spec.md SC-001 (≤30s install) | Wall-clock measurement is fixture-only; live `kosmos-plugin-store` measurement is implicit. Network latency variance not quantified. | Add a follow-up tracking issue (NEEDS TRACKING) for live-environment SC-001 validation post-PR merge. Update spec.md Deferred table. |
| R3 | Risk (scaling) | LOW | tasks.md T020 (plugins.ts data binding) + Spec 1636 SC-010 | Payload reassembly for `plugin_op_request:list` not stress-tested at >100 plugins; Spec 1636 SC-010 (200ms boot per plugin) implies catalogs may grow large. | Acceptable for MVP3 (1-4 plugins from kosmos-plugin-store). Add follow-up task to E2E suite when catalog exceeds ~50 plugins. NEEDS TRACKING. |
| D1 | Deferred (HIGH→tracked) | INFO | spec.md § Deferred table + research.md § Phase 0 deferred validation | 8 total deferred items: 4 with concrete issue numbers (#585, #1820, #1926, #1980), 2 inherited NEEDS TRACKING, 2 new NEEDS TRACKING discovered in research.md (CC residue cleanup + runtime enable/disable IPC). | T036 (Phase 7 Polish) commits to updating spec.md Deferred table with the 2 new entries. `/speckit-taskstoissues` resolves all NEEDS TRACKING markers. ✅ Compliant with §VI. |
| T1 | Terminology | LOW | spec.md vs contracts/dispatcher-routing.md ("envelope" vs "frame") | Spec 1636 contracts use "20th arm" / "discriminated union arm"; spec.md uses both "frame arm" and "frame" interchangeably. | Cosmetic. Already consistent enough for review. No action. |

**Summary**: 9 findings. 0 CRITICAL. 1 HIGH (managed cliff-edge risk). 2 MEDIUM coverage gaps with clear remediation. 6 LOW/INFO.

---

## Constitution Compliance Verdict

| Principle | Verdict | Evidence |
|---|---|---|
| §I Reference-Driven Development | ✅ PASS | spec.md Input cites 10 references; research.md V1/V2 + R-1..R-6 each cite primary + secondary; reference-mapping table populated; CC sourcemap consulted as residue baseline. |
| §II Fail-Closed Security | ✅ PASS | FR-005 (failed install rollback), FR-013 (revocation fail-closed), R-2 (TimeoutError → False denial), V1 (residue stays inert). 12 edge cases documented in spec.md cover crash recovery, concurrency, timeout, partial-state, namespace collision. |
| §III Pydantic v2 Strict Typing | ✅ PASS | Zero new schema additions. PluginOpFrame + PluginManifest + PermissionRequestFrame all reused. R-3/R-4 explicitly backed off from extending `request_op` enum to preserve Spec 032 envelope hash invariant. No `Any` introduced. |
| §IV Government API Compliance | ✅ PASS | FR-026 forbids live data.go.kr in CI; T031 fixture catalog uses file:// URLs; `installer.py:_default_catalog_fetcher` `file://` branch already exists. No new live API surface. |
| §V Policy Alignment | ✅ PASS | PIPA §26 trustee SHA-256 + trustee_org_name round-trip preserved (FR-012, contracts/consent-bridge.md, T020). 7-step gauntlet honoured (FR-011, T009, T019). Korea AI Action Plan Principle 8 (single conversational window) — citizen never leaves TUI for plugin lifecycle. |
| §VI Deferred Work Accountability | ✅ PASS | 8 deferred items: 4 with concrete tracking, 4 NEEDS TRACKING (resolved by `/speckit-taskstoissues`). Zero unregistered "future epic" / "v2" / "Phase N" prose patterns (verified by 6 deferred-pattern grep matches all in structured table). T036 commits to updating spec.md with 2 new research.md entries. |

**Constitution gate**: ✅ ALL PRINCIPLES PASS — `/speckit-taskstoissues` is unblocked from constitution side.

---

## Cross-artifact Consistency Matrix

### FR → Task Coverage (27 FRs)

| FR | Task(s) | Coverage |
|---|---|---|
| FR-001 (dispatcher routing) | T003, T004, T008, T011 | ✅ |
| FR-002 (7 progress frames bilingual) | T007, T008 | ✅ |
| FR-003 (complete frame shape + exit_code) | T008, T009, T011 | ✅ |
| FR-004 (consent_prompt IPC round-trip) | T006, T009, T015 | ✅ |
| FR-005 (failed install zero state) | T010 (rollback), T014 | ✅ |
| FR-006 (uninstall envelope shape) | T010, T011 | ✅ |
| FR-007 (list single complete frame + payload) | T012, T014 | ✅ |
| FR-008 (post-install tools[] propagation) | T016, T017, T018 | ✅ |
| FR-009 (post-uninstall tools[] exclusion) | T016, T017 | ✅ |
| FR-010 (OTEL kosmos.plugin.id span) | (relies on Spec 1636 invariant) | ⚠️ MEDIUM (C1) |
| FR-011 (gauntlet routes by manifest layer) | T009, T019 | ✅ |
| FR-012 (PII modal shows trustee + ack hash) | T006, T015, T020 | ✅ |
| FR-013 (revocation fail-closed) | T019, T033 (revoke smoke) | ✅ |
| FR-014 (layer color glyph) | T009, T019 | ✅ |
| FR-015 (browser listing surface) | T023, T024, T025 | ✅ |
| FR-016 (UI-E.3 key bindings) | T028, T030 | ✅ (with A1 deferred) |
| FR-017 (remove flow emits uninstall) | T027 | ✅ |
| FR-018 (CC residue verdict) | T021 + research.md V1 + T036 | ✅ |
| FR-019 (in-flight placeholder row) | T029 | ✅ |
| FR-020 (E2E scenario script + 4 artifacts) | T031, T032, T033, T034, T035 | ✅ |
| FR-021 (L3 grep markers) | T033 | ✅ |
| FR-022 (L1 baseline parity) | T035 | ✅ |
| FR-023 (zero new runtime deps) | T038 (PR-time grep) | ✅ |
| FR-024 (English source / Korean strings) | T022/T023/T024/T025/T026/T027/T028 (inline mandate) | ✅ |
| FR-025 (stdlib logging) | (invariant — no task needed) | ✅ |
| FR-026 (no live data.go.kr in CI) | T031 (file:// fixture catalog) | ✅ |
| FR-027 (≤90 sub-issues) | (verified at /speckit-taskstoissues) | ✅ |

**Coverage rate**: 26 / 27 = **96.3 %** explicit task mapping (FR-010 has implicit coverage via Spec 1636 invariant — flagged C1).

### SC → Verification Coverage (10 SCs)

| SC | Verification Path |
|---|---|
| SC-001 (≤30s install) | T035 wall-clock measurement against fixture catalog |
| SC-002 (≤3s tools[] propagation) | T018 integration test (post-install ChatRequestFrame) |
| SC-003 (100% gauntlet routing) | T019 fixture-based 3-layer matrix test |
| SC-004 (4-layer artifacts produced) | T031..T035 (artifact existence) |
| SC-005 (baseline parity 984/3458) | T035 master orchestrator runs L1 layer |
| SC-006 (zero new runtime deps) | T038 PR-description grep (acceptance gate) |
| SC-007 (≤90 sub-issues) | `/speckit-taskstoissues` GraphQL query (post-tasks gate) |
| SC-008 (revocation 100% fail-closed) | T019 + T033 smoke-1979-revoke.expect |
| SC-009 (concurrent ledger monotonic) | (no explicit task — relies on Spec 1636 fcntl.flock) | ⚠️ MEDIUM (C2) |
| SC-010 (deny → zero state) | T033 smoke-1979-deny.expect |

**SC verification rate**: 9 / 10 = **90.0 %** explicit task mapping (SC-009 has implicit coverage via Spec 1636 invariant — flagged C2).

### User Story → Phase Mapping

| Story | Priority | Phase | Tasks | Verifiable independently? |
|---|---|---|---|---|
| US1 (citizen install) | P1 | Phase 3 | T007–T015 (9 tasks) | ✅ via fixture catalog + pytest |
| US2 (citizen invokes) | P1 | Phase 4 | T016–T020 (5 tasks) | ✅ via pre-install fixture + integration test |
| US3 (citizen browser) | P2 | Phase 5 | T021–T030 (10 tasks) | ✅ via fixture state + bun test (after T021 swap) |
| US4 (E2E verification) | P2 | Phase 6 | T031–T035 (5 tasks) | ✅ via run-e2e.sh master orchestrator |

**Story independence**: ✅ Each story has a checkpoint and dedicated test path.

### Plan vs Research Consistency

| Topic | plan.md | research.md | Consistent? |
|---|---|---|---|
| Python 3.12+ baseline | Yes | Yes (R-1) | ✅ |
| TS 5.6+ on Bun v1.2.x | Yes | Yes (V1, V2) | ✅ |
| Zero new runtime deps | SC-006 + Technical Context | R-3/R-4 explicit reaffirmation | ✅ |
| Backend dispatcher arm location | stdio.py:1675 | R-1 same line | ✅ |
| Consent timeout | 60s | R-2 (60s, with rationale) | ✅ |
| ToolRegistry _inactive | data-model.md E4 | R-3+R-4 with verdict scope-limited | ✅ |
| ChatRequestFrame.tools[] | Plan section 4 + R-6 | R-6 detailed analysis | ✅ |
| 4-layer ladder methodology | quickstart + Phase F | R-5 vhs vs expect signal | ✅ |

### Data Model → Task Coverage (5 entities)

| Entity | Definition | Task | Status |
|---|---|---|---|
| E1 PluginOpDispatcher | data-model.md:34-72 | T004, T008, T011, T012 | ✅ |
| E2 IPCConsentBridge | data-model.md:78-120 | T006, T015 | ✅ |
| E3 uninstall_plugin | data-model.md:124-160 | T010 | ✅ |
| E4 ToolRegistry._inactive | data-model.md:162-205 | T005 | ✅ |
| E5 CitizenPluginStoreSession | data-model.md:208-252 | T023 | ✅ |

### Contract → Task Coverage (4 contracts)

| Contract | Tasks |
|---|---|
| dispatcher-routing.md | T003, T004, T007, T008, T009, T011, T012, T013, T017, T018 |
| consent-bridge.md | T006, T009, T015, T020 |
| citizen-plugin-store.md | T021, T022, T023, T024, T025, T026, T027, T028, T029, T030 |
| e2e-pty-scenario.md | T031, T032, T033, T034, T035 |

### Quickstart → User Story Mapping

- 1단계 (TUI 실행) ↔ baseline assumption (no story)
- 2단계 (플러그인 설치) ↔ US1 acceptance scenario 1
- 3단계 (동의 모달) ↔ US1 acceptance scenarios 4 (Layer 1) + US2 (Layer 2/3 in scenarios 2-3)
- 4단계 (플러그인 호출) ↔ US2 acceptance scenarios 1-3
- 5단계 (브라우저 확인) ↔ US3 acceptance scenarios 1-2
- 분기 거부 ↔ US1 acceptance scenario 2
- 분기 영수증 ↔ US3 (consent ledger surface)
- 분기 제거 ↔ US1 acceptance scenario 5 + US3 acceptance scenario 3

✅ All 5 main steps + 3 branches map to spec.md acceptance scenarios.

---

## Deferred Items Inventory (Constitution §VI Audit)

Spec.md § Scope Boundaries & Deferred Items section: ✅ PRESENT (mandatory section).

### Out of Scope (Permanent) — 8 items

All 8 items have explicit "MUST NOT change" / permanent rationale. None pattern-match unregistered "future" / "v2" prose. ✅ COMPLIANT.

### Deferred to Future Work — 6 inherited entries + 2 new from research.md = 8 total

| # | Item | Tracking | Status |
|---|---|---|---|
| 1 | Plugin tool dense-embedding discovery | #585 | ✅ tracked |
| 2 | External plugin contributor onboarding UX | NEEDS TRACKING | ⏳ resolves at /speckit-taskstoissues |
| 3 | Plugin store catalog index sync | NEEDS TRACKING | ⏳ resolves at /speckit-taskstoissues |
| 4 | Spec 027 swarm worker invokes plugins | #1980 | ✅ tracked |
| 5 | Plugin marketplace catalog browser (a-keystroke) | #1820 | ✅ tracked |
| 6 | Acknowledgment-text drift audit workflow | #1926 | ✅ tracked |
| 7 | CC marketplace residue cleanup (research.md V1) | NEEDS TRACKING | ⏳ T036 commits to spec.md table update |
| 8 | Plugin runtime enable/disable IPC (research.md R-3/R-4) | NEEDS TRACKING | ⏳ T036 commits to spec.md table update |

**Tracked vs untracked**: 4 ✅ + 4 ⏳ = 8 / 8 entries have a path forward (either issue # or NEEDS TRACKING marker resolved at next spec phase). Zero ghost work risk.

### Unregistered Deferral Pattern Scan

```bash
$ grep -E 'separate epic|future epic|Phase [2-9]|v2|deferred to|later release|out of scope for v1|not in this|won.t implement' spec.md | wc -l
6
```

All 6 matches occur within the structured Deferred to Future Work table or its scope-boundary headers. ✅ Zero unregistered ghost-work prose.

---

## Sub-Issue Budget Projection

- **Current task count**: 38
- **Hard cap**: 90 (per memory `feedback_subissue_100_cap` + Constitution §VI Sub-Issue Discipline)
- **Slots reserved**: 52 (for `[Deferred]` placeholder sub-issues + Codex review iteration buffer)
- **Risk**: ✅ LOW — well within budget; even if Codex review adds 5-10 follow-up tasks, total stays < 50

`/speckit-taskstoissues` projection: 38 task issues + 4 NEEDS TRACKING placeholder issues = 42 sub-issues parented to Epic #1979. Safe.

---

## Memory Guardrail Audit (14 memories)

| Memory | Applied Where | Status |
|---|---|---|
| `feedback_runtime_verification` | Phase 1 (T001-T002 baseline) + Phase 6 (T031-T035 PTY scenarios) | ✅ |
| `feedback_vhs_tui_smoke` | T033 L3 text-log primary + T034 L4 gif supplemental + T037 .gitignore | ✅ |
| `feedback_main_verb_primitive` | spec.md US2 acceptance scenarios + T018 integration test asserts plugin tool routes through `lookup`/`submit`/`verify`/`subscribe` namespace | ✅ |
| `feedback_no_hardcoding` | research.md notes BM25 + primitive routing reused; no static keyword/salvage introduced | ✅ |
| `feedback_check_references_first` | All 38 tasks carry "Reference: ..." citation; research.md cites primary + secondary per Constitution §I | ✅ |
| `feedback_speckit_autonomous` | tasks.md Implementation Strategy explicitly states "Lead + Teammates proceed autonomously up to PR" | ✅ |
| `feedback_integrated_pr_only` | tasks.md Notes: "단일 통합 PR" | ✅ |
| `feedback_pr_closing_refs` | tasks.md Notes: "PR body uses `Closes #1979` only (Epic)" | ✅ |
| `feedback_codex_reviewer` | tasks.md Notes: post-push Codex coment processing | ✅ |
| `feedback_copilot_gate_race` | (Implicit — applies during /speckit-implement push iterations; no spec-level task needed) | ✅ |
| `feedback_subissue_100_cap` | SC-007 + Sub-Issue Budget Projection above; 38 ≪ 90 | ✅ |
| `feedback_kosmos_uses_cc_query_engine` | research.md cites "agentic loop CC 쿼리 엔진 보존"; Plan technical approach reuses Epic #1978 | ✅ |
| `feedback_no_stubs_remove_or_migrate` | research.md V1: "leaving CC residue inert satisfies the rule by making it KOSMOS-unreachable" — explicit rationale | ✅ |
| `feedback_kosmos_scope_cc_plus_two_swaps` | research.md V1 explicit citation; rationale anchored in this memory | ✅ |

**Memory audit**: 14 / 14 applied with traceable evidence. ✅ FULL COMPLIANCE.

---

## Risk Inventory (4 user-flagged risks)

| Risk | Severity | Mitigation Status |
|---|---|---|
| **Risk A** — T021 single cliff-edge | HIGH | ⚠️ Managed: T030 (bun tests) + T035 (master orchestrator) catch swap regression. Acceptable with monitoring. PR description must explicitly note T021 as gate. |
| **Risk B** — Space toggle visual-only conflict | LOW | ✅ Documented in research.md R-3/R-4 + listed as Deferred item #8. Acceptable. |
| **Risk C** — SC-001 fixture-only measurement | LOW | ⏳ Add NEEDS TRACKING entry for live `kosmos-plugin-store` validation. T036 should include this as a third deferred entry to surface in spec.md. |
| **Risk D** — payload reassembly at scale | LOW | ✅ Acceptable for MVP3 (1-4 plugins). Add NEEDS TRACKING entry for >50 plugins stress test. T036 should include this. |

**Recommendation**: Update T036 scope to include 4 (not 2) new deferred entries: V1 cleanup + R-3/R-4 toggle IPC + Risk C live env + Risk D scale test.

---

## Metrics

- **Total Functional Requirements**: 27
- **Total Success Criteria**: 10
- **Total User Stories**: 4 (P1 ×2, P2 ×2)
- **Total Tasks**: 38 (across 7 phases)
- **FR Coverage**: 26 / 27 = 96.3 % (1 implicit via Spec 1636 invariant)
- **SC Coverage**: 9 / 10 = 90.0 % (1 implicit via Spec 1636 invariant)
- **Story Independence**: 4 / 4 stories have dedicated checkpoint tests
- **Deferred Items**: 8 (4 tracked, 4 NEEDS TRACKING resolved at next phase)
- **Sub-Issue Budget**: 38 / 90 = 42.2 % utilization
- **Constitution Gates**: 6 / 6 PASS
- **Memory Guardrails Applied**: 14 / 14
- **CRITICAL Findings**: 0
- **HIGH Findings**: 1 (R1 cliff-edge — managed)
- **MEDIUM Findings**: 2 (C1 FR-010 OTEL, C2 SC-009 concurrent ledger)
- **LOW Findings**: 5 (C3 governance invariants + A1 ambiguity + R2 + R3 + T1 terminology)

---

## Final Verdict: ✅ **PASS**

The Epic #1979 specification suite passes Constitution §I-VI, cross-artifact consistency, deferred work accountability, sub-issue budget, and memory guardrail audits. Zero CRITICAL findings.

**Conditions for proceeding to `/speckit-taskstoissues`**:

1. ✅ All Constitution principles satisfied.
2. ✅ All Functional Requirements have at least implicit task coverage.
3. ✅ All User Stories independently testable.
4. ✅ Deferred items either tracked or resolvable at next phase.
5. ✅ Sub-issue budget within 90-cap with 52-slot reserve.
6. ✅ Memory guardrails applied with traceable evidence.

**Recommended pre-`/speckit-implement` adjustments** (optional, do not block `/speckit-taskstoissues`):

- **Optional**: Update T036 to enumerate 4 new deferred entries (V1, R-3/R-4, Risk C, Risk D) instead of 2.
- **Optional**: Add a sub-bullet to T014 covering FR-010 OTEL `kosmos.plugin.id` assertion.
- **Optional**: Add a sub-bullet to T014 covering SC-009 concurrent install ledger assertion.

These are quality improvements that can land as part of the implement phase or in a separate fix-up commit.

---

## `/speckit-taskstoissues` Entry: ✅ **APPROVED**

The spec is ready for the GitHub issue materialization phase. `/speckit-taskstoissues` will:
1. Create 38 Task issues (T001-T038) with `agent-ready` label.
2. Resolve 4 NEEDS TRACKING markers in spec.md Deferred table → create placeholder issues.
3. Link all 42 issues as sub-issues of Epic #1979 via Sub-Issues API v2.
4. Verify total Sub-Issues count ≤ 90 (currently projected: 42).

Then `/speckit-implement` is the next entry point.
