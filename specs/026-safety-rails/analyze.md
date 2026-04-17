# /speckit-analyze Report — Epic #466 Safety Rails

**Date**: 2026-04-17
**Inputs analyzed**: `spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`
**Constitution version**: v1.1.0 (`.specify/memory/constitution.md`)
**Verdict**: **PASS** — ready for `/speckit-taskstoissues`.

---

## 1. Constitution Compliance (post-tasks re-check)

| Principle | Status | Evidence | Risk |
|---|---|---|---|
| I. Reference-Driven Development | ✅ PASS | plan.md § Phase 0 maps 14 design decisions to primary + secondary references; tasks.md § T018 and T023 carry forward the same reference anchors (Presidio docs, arXiv 2504.11168) into implementation. | None. |
| II. Fail-Closed Security | ✅ PASS | T008 makes `SafetySettings` raise `ConfigurationError` when moderation is enabled without an API key; T029 test enforces this. T035 wires the detector in a *blocking-first* order (detector → redactor → normalize). | Moderation outage is an intentional fail-open (FR-011); documented both in spec § Edge Cases and tasks.md T030 with a justification comment. Not a violation — the fail-open posture is scoped to a named edge case. |
| III. Pydantic v2 Strict Typing | ✅ PASS | T007 mandates `ConfigDict(frozen=True, strict=True)` on all 5 Key Entities; SafetyEvent is a discriminated union on `kind`. No `Any` anywhere in plan.md § Data Model or tasks.md. | None. |
| IV. Government API Compliance | ✅ PASS | No new tool adapters. `@pytest.mark.live` is **not** added — moderation tests use `respx`-mocked OpenAI calls (T028). | None. |
| V. Policy Alignment | ✅ PASS | T030 substitutes 1393/1366 Korean crisis hotlines for self-harm blocks (PIPA §26 + AI Action Plan 원칙9 citizen-protection mapping). Step 3 regression-gated byte-unchanged (T010+T012) so PIPA processor-role posture is preserved. | None. |
| VI. Deferred Work Accountability | ⚠️ PASS with follow-up | spec.md § Scope Boundaries lists 6 deferred items; 5 already cite target Epic numbers. One item — **post-MVP Llama Guard ADR** — is marked `NEEDS TRACKING`. `/speckit-taskstoissues` must open a tracking issue and back-fill the marker. | Tracked as a Task-issue deliverable (see § 6 below). |

**Gate**: PASS. No principle violated.

---

## 2. Spec ↔ Plan ↔ Tasks Coherence

### Coverage matrix (every FR in spec.md maps to ≥1 task)

| FR cluster | Spec FRs | Plan.md section | Tasks.md task(s) | Status |
|---|---|---|---|---|
| Layer A — PII redactor | FR-001..FR-005 | § Project Structure (safety/_redactor.py); § Data Model (RedactionResult/Match) | T007, T009, T017, T018, T019, T020 | ✅ |
| Layer B — Moderation | FR-006..FR-011 | § Technical Context (openai SDK); § Data Model (SafetyDecision + ModerationBlocked/Warned events) | T008, T026–T032 | ✅ |
| Layer C — Injection detector | FR-012..FR-017 | § Phase 0 (arXiv 2504.11168 ref); § Data Model (InjectionSignalSet) | T021, T022, T023, T024, T025 | ✅ |
| Layer D — Trust hierarchy | FR-018..FR-019 | § Phase 0 (NFR-003 cache stability ref) | T033, T034, T042 | ✅ |
| Observability | FR-020 | § Project Structure (_span.py); § Data Model (SafetyEvent discriminated union) | T014, T015, T032, T036 | ✅ |
| Configuration | FR-021..FR-023 | § Data Model (SafetySettings) | T008, T013, T029, T044 | ✅ |
| Enum extension | FR-024 | § Agent / Task Breakdown (PR-A) | T004, T005, T006 | ✅ |

All 24 FRs trace to at least one task. No orphan requirements; no orphan tasks.

### Success Criteria traceability

| SC | Assertion | Task(s) validating |
|---|---|---|
| SC-001 | 100% detection on 10 PII fixtures | T017, T019 |
| SC-002 | 100% block on 10 injection fixtures | T022, T024 |
| SC-003 | p95 redaction latency < 50ms at 100KB | T020 |
| SC-004 | Zero false positives on 500-turn clean corpus | T025, T041 |
| SC-005 | 5/5 moderation block + 5/5 pass on fixtures | T028, T031 |
| SC-006 | Cache-prefix stability (Section 5 last) | T034, T042 |
| SC-007 | Zero raw PII in spans (only `gen_ai.safety.event` bounded enum) | T014, T015, T032 |

All 7 SCs have concrete validating tasks.

### User-story ↔ phase alignment

| Spec US | Priority | Spec FRs | Tasks phase | Independent test |
|---|---|---|---|---|
| US1 — PII redaction | P1 | FR-001..FR-005 | Phase 3 (T016–T020) | ✅ `pii_samples.json` standalone |
| US2 — Injection defense | P2 | FR-012..FR-017 | Phase 4 (T021–T025) | ✅ `injection_samples.json` standalone |
| US3 — Moderation | P3 | FR-006..FR-011 | Phase 5 (T026–T032) | ✅ `respx`-mocked callbacks standalone |

Each user story is independently implementable and testable — MVP-shippable path documented in tasks.md § Implementation Strategy.

---

## 3. Cross-Epic Contract Compliance

| Contract | Owner | Plan.md commitment | Tasks.md enforcement | Status |
|---|---|---|---|---|
| `LookupErrorReason` enum extension | Code-owned (ex-#507) | PR-A isolated first | T004–T006 as PR-A; T005 round-trip test | ✅ |
| `gen_ai.safety.event` span attribute | #501 | Only attribute key, bounded enum, no raw data | T014 (helper), T015 (test), T045 (follow-up comment) | ✅ |
| `KOSMOS_SAFETY_*` env keys | #468 | Propose 4 keys + 1 OpenAI key; never touch docs/configuration.md | T008 (SafetySettings), T044 (follow-up comment on #468) | ✅ |
| LiteLLM callback slot | #465 | Code-only registration; never touch infra/litellm/config.yaml | T030 (callbacks), T043 (follow-up comment on #465) | ✅ |
| Permission gauntlet boundary | #16, #20 | Out of scope; Step 3 byte-unchanged | T010 (refactor), T012 (regression gate) | ✅ |

No cross-Epic contract violated. All boundary-crossing work reduced to comment-based follow-ups (T043–T045) per spec.

---

## 4. Hard Constraint Verification

| Constraint | Verification path |
|---|---|
| Apache-2.0 purity | T040 doc mentions Option A accepted / Option B deferred; no Llama Guard in deps (T039 adds `presidio-analyzer` + `openai` only). |
| 3x no-hardcoding rule | T018 delegates to Presidio PatternRecognizer; T023 decomposes into structural + entropy + length signals (no static keyword list); T009 centralizes patterns in `_patterns.py`. |
| Single source of truth for `_PII_PATTERNS` | T009 + T010 + T011 (SoT test explicitly greps `src/` and asserts exactly one definition site). |
| Pydantic v2 strict + discriminated union | T007 names `ConfigDict(frozen=True, strict=True)`; SafetyEvent uses `Annotated[..., Field(discriminator="kind")]`. |
| NFR-003 cache prefix stability | T033 inserts trust hierarchy between Sections 3 and 4 (verified via source read at line 47–57 of `context/system_prompt.py`); T034 asserts Section 5 stays last; T042 re-verifies at Polish time. |
| Defense-in-depth (commit 50e2c17) | T037 explicitly verifies the existing per-file redactions remain untouched. |
| Zero raw data in spans | T014 signature accepts only `SafetyEvent` (discriminated union with no raw-value variant); T015 smoke-tests the type-level guarantee. |

All hard constraints have a concrete verification task.

---

## 5. Anchor Point Verification (against live source)

| Anchor referenced in plan/tasks | Actual source state | Match |
|---|---|---|
| `step3_params._PII_PATTERNS` at `src/kosmos/permissions/steps/step3_params.py:50` | Present (verified via Read during session). Contains 5 categories as spec claims. | ✅ |
| `LookupErrorReason` enum in `src/kosmos/tools/errors.py:83` | Present with 8 members (auth_required, stale_data, timeout, upstream_unavailable, unknown_tool, invalid_params, out_of_domain, empty_registry). Tasks T004 adds 2 → 10 total. | ✅ |
| `ToolExecutor.invoke` in `src/kosmos/tools/executor.py:114` and `dispatch` at `executor.py:259` | Verified by Grep. Plan.md notes "~L222" and "~L394" as approximate lines inside each method; T035 requires locating the exact line by reading the current file, not by line number. Resilient to drift. | ✅ |
| `SystemPromptAssembler._session_guidance_section` last at `context/system_prompt.py:57` (append after optional Section 4) | Verified by Read. T033 insertion point is between `_tool_use_policy_section()` (line 49) and the conditional append of `_personal_data_reminder_section()` (lines 51–52). | ✅ |

No anchor drift. Plan and tasks align with the current source state.

---

## 6. Issues Flagged for `/speckit-taskstoissues`

1. **Llama Guard post-MVP ADR (`NEEDS TRACKING`)** — spec § Scope Boundaries deferred item needs a new tracking issue when sub-issues are created. Proposed title: `chore(safety): ADR — Llama Guard 3 opt-in path (post-MVP)`.
2. **Upstream follow-up comments T043–T045** — these are not Task sub-issues but free-text comments on Epics #465/#468/#501. `/speckit-taskstoissues` should list them in a "Follow-ups" section of the issue-creation report, not as separate issues.
3. **Tasks.md counts 46 tasks** (T001–T046). That exceeds GitHub's 50-sub-issue soft limit comfortably, but approaches it — if any task is later split, verify the ceiling.

No blocking analysis issues. All three flagged items are operational notes for the next command, not correctness problems.

---

## 7. Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| Presidio's pattern-only deployment (empty NlpEngine) may not be documented as officially supported. | Low | T018 requires implementation to verify exact shape against Presidio docs. If blocked, fallback is to subclass `AnalyzerEngine` and bypass NLP explicitly; plan.md already notes both options. |
| OpenAI Moderation Korean-language performance may differ from English. | Medium | T027 + T031 exercise 5 Korean-language pass fixtures including ambiguous public-service queries (자살 예방 상담 전화, etc.). If false-positive rate > 0, spec § Edge Cases permits a configuration-level adjustment (fail-open via `moderation_enabled=False`). |
| Injection detector weights (0.6 / 0.25 / 0.15) may over-trigger on certain KOROAD tool outputs (legal text quoting, etc.). | Medium | T025 false-positive audit against recorded corpus; tuning permitted **within the 3-signal framework** — no keyword additions. |
| `uv add openai` adds transitively-large dep graph. | Low | Student-portfolio single-node deployment; no production-size pressure. Documented in T039. |

No high-severity risks. All medium risks have named mitigation tasks.

---

## Recommendation

**PROCEED** to `/speckit-taskstoissues` with the current `tasks.md`. Create Task issues for T001–T046 plus one tracking issue for the Llama Guard post-MVP ADR. Link all as sub-issues of Epic #466 via the Sub-Issues API. After sub-issues are created, back-fill the `NEEDS TRACKING` marker in `spec.md` § Scope Boundaries with the new ADR tracking issue number.

Halt after `/speckit-taskstoissues` per the standing `/remote-control` directive — do **not** auto-advance to `/speckit-implement`.
