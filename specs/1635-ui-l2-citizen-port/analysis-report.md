# Specification Analysis Report — Epic #1635 P4 UI L2 Citizen Port

**Generated**: 2026-04-25
**Scope**: spec.md · plan.md · research.md · data-model.md · contracts/ · quickstart.md · tasks.md
**Constitution**: `.specify/memory/constitution.md` v1.1.1
**Verdict**: **PASS** — 0 CRITICAL · 0 HIGH · 2 MEDIUM · 2 LOW. `/speckit-taskstoissues` is unblocked.

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|---|---|---|---|---|---|
| C1 | Constitution VI Deferred | — (PASS) | spec.md L226–231 (table) + research.md §3 | Spec.md ships an 8-row "Deferred to Future Work" table; every prose `Phase P5` / `Phase P6` / `follow-up` / `separate epic` mention resolves to a row. research.md §3 cross-validates 1:1. | None — all 8 rows carry `NEEDS TRACKING`; resolved at `/speckit-taskstoissues`. |
| F1 | FR Coverage | — (PASS) | spec.md FR-001..038 vs tasks.md | 38/38 FRs cited at least once across 80 tasks (73 total `FR-NNN` references in tasks.md). | None. |
| F2 | SC Coverage (buildable) | MEDIUM | spec.md SC-003 / SC-006 / SC-011 vs tasks.md | Three buildable success criteria (Layer 2/3 modal coverage CI, PDF inline detect/fallback test, a11y toggle ≤500 ms persist) have implicit task coverage but no explicit `SC-NNN` citation in task bodies. The associated tests (T024 PdfInlineViewer test, T037 permission modal tests, T044/T048/T050 a11y suite) cover the behavior. | Add explicit `SC-003/SC-006/SC-011` mentions to T037, T024, T050 bodies for traceability. Non-blocking. |
| F3 | SC Coverage (post-launch) | — (PASS) | spec.md SC-001 / SC-002 / SC-004 / SC-010 | Four success criteria are usability / Likert metrics (post-launch assessment: 95% onboarding completion, ≥4/5 streaming smoothness, 90% layer identification within 2s, ≥4/5 confidence). Per `/speckit-analyze` skill rules, post-launch outcome metrics are excluded from buildable-coverage requirements. | None. |
| P1 | Plan ↔ Tasks file map | — (PASS) | plan.md project structure tree | Cross-reference of 51 task file paths against the plan structure tree shows 100% match. The 3 "filename not in tasks" results (`Context.tsx`, `Keybinding.ts`, `KeybindingContext.tsx`) are Spec 287-shipped TUI infrastructure already on disk — verified `EXISTS` at `tui/src/keybindings/KeybindingContext.tsx`, `tui/src/keybindings/useKeybinding.ts`, `tui/src/context/modalContext.tsx`, `tui/src/context/overlayContext.tsx`, `tui/src/context/notifications.tsx`. | None. |
| P2 | Plan PORT-label clarity | MEDIUM | plan.md project structure tree (lines under `keybindings/` and `context/`) | Plan tree marks `KeybindingContext.tsx`, `useKeybinding.ts`, `modalContext.tsx`, `overlayContext.tsx`, `notifications.tsx` as `PORT` without distinguishing "Spec 287 already ported" vs "this epic ports now". A reviewer could mistakenly expect tasks for the already-ported files. | Add a per-file annotation like `(already ported by Spec 287, no work in this epic)` to those five lines. Non-blocking. |
| D1 | Data-model ↔ Tasks | — (PASS) | data-model.md §1–§7 vs tasks.md | All 7 entities (OnboardingState · PermissionReceipt · AgentVisibilityEntry · SlashCommandCatalogEntry · AccessibilityPreference · ErrorEnvelope · UfoMascotPose) are referenced by Phase 2 schema tasks T003–T007. | None. |
| K1 | Contracts ↔ Tasks | — (PASS) | contracts/{slash-commands,keybindings,memdir-paths} vs tasks.md | Slash command catalog SSOT seeded by T010 (12 commands match data-model §4); 10 keybinding IDs from `keybindings.schema.json` covered by T011 (Ctrl-O / Shift+Tab / `/` / Y/A/N / Space/i/r/a); both new memdir paths owned by T008 + T048. | None. |
| Q1 | Quickstart reachability | — (PASS) | quickstart.md Steps 1–13 | All 13 steps map to FRs (FR-001..006, FR-003, FR-025..028, FR-015..018, FR-019..021, FR-022, FR-010/011, FR-009, FR-014, FR-029..031, FR-032, FR-033, FR-004), every FR is covered by at least one task. | None. |
| A1 | AGENTS.md hard rules | — (PASS) | plan.md tech context + research.md §4 | Zero new Python core runtime deps (backend untouched). Source text English (Korean only in i18n strings + auto-memory). Zero new live data.go.kr calls. Two TS deps (pdf-to-img Apache-2.0, pdf-lib MIT) explicitly authorised by Epic body and justified in research.md §4. | None. |
| B1 | Sub-issue budget | — (PASS) | tasks.md count vs `feedback_subissue_100_cap` | 80 / 90 tasks (89% of cap). Leaves 10 slots for `[Deferred]` placeholders + mid-cycle additions. | None. |
| L1 | Deferred-text false positives | LOW | plan.md L10/L32/L35 | "Pydantic v2" / "permission v2 spectrum" matched the deferred-pattern `v2` regex but are spec/product names, not deferral declarations. | None — ignore as semantic version annotation. |
| L2 | Constitution III TS scope | LOW | plan.md Constitution Check row III | Principle III mandates Pydantic v2 strict typing, but TS layer uses Zod (its TS-side analog). plan.md notes this explicitly with "no `any` in shipped TS code" guarantee. | None — Zod is the canonical TS counterpart; the rule is preserved in spirit. |

## Coverage Summary

### Functional Requirements (38/38 = 100%)

| Range | Tasks | Hit count |
|---|---|---|
| FR-001..007 (UI-A Onboarding) | T040–T052 | 14 |
| FR-008..014 (UI-B REPL) | T014–T026 | 14 |
| FR-015..024 (UI-C Permission) | T027–T039 | 14 |
| FR-025..028 (UI-D Agents) | T053–T059 | 8 |
| FR-029..033 (UI-E Auxiliary) | T060–T072 | 13 |
| FR-034..038 (Cross-cutting) | T009/T011/T022/T035/T049/T072/T074–T076 | 10 |
| **Total** | 80 tasks | 73 FR refs |

### Success Criteria (12 total)

| ID | Type | Coverage | Task IDs |
|---|---|---|---|
| SC-001 | post-launch (usability) | excluded | — |
| SC-002 | post-launch (usability) | excluded | — |
| SC-003 | buildable (CI assertion) | implicit | T037 (recommend explicit cite) |
| SC-004 | post-launch (usability) | excluded | — |
| SC-005 | buildable (perf budget) | explicit | T025 |
| SC-006 | buildable (test) | implicit | T024 (recommend explicit cite) |
| SC-007 | buildable (perf budget) | explicit | T057, T058 |
| SC-008 | buildable (verification) | explicit | T076 |
| SC-009 | buildable (manual scoring) | explicit | T075 |
| SC-010 | post-launch (usability) | excluded | — |
| SC-011 | buildable (perf budget) | implicit | T044, T048, T050 (recommend explicit cite) |
| SC-012 | buildable (content scan) | explicit | T071, T077 |

Buildable: 8 / 8 covered (5 explicit, 3 implicit). Post-launch: 4 (excluded per skill rule).

### Constitution Alignment

| Principle | Verdict | Source |
|---|---|---|
| I · Reference-Driven Development | PASS | research.md §1 maps every FR to CC restored-src or canonical KOSMOS spec |
| II · Fail-Closed Security | PASS | FR-022/023/024 enforce auto-deny on cancel/timeout + bypass reinforcement |
| III · Pydantic v2 Strict Typing | PASS (TS analog) | plan.md notes Zod with no `any`; backend untouched |
| IV · Government API Compliance | N/A | No new tool adapters |
| V · Policy Alignment | PASS | FR-006 PIPA §26 trustee; FR-007 right-of-revocation; principles 8/9 of AI Action Plan |
| VI · Deferred Work Accountability | PASS | 8-row table, 0 untracked prose deferrals |

### Deferred-Items Audit (Constitution VI)

| Row | Item | Tracking | Status |
|---|---|---|---|
| 1 | Plugin DX 5-tier | NEEDS TRACKING | OK — resolves at taskstoissues |
| 2 | docs/api + docs/plugins | NEEDS TRACKING | OK |
| 3 | Phase 2 auxiliary tools | NEEDS TRACKING | OK |
| 4 | Japanese localization | NEEDS TRACKING | OK |
| 5 | /agents advanced views | NEEDS TRACKING | OK |
| 6 | Plugin marketplace store UI | NEEDS TRACKING | OK |
| 7 | Spec 035 memdir restyling | NEEDS TRACKING | OK |
| 8 | Composite tools | NEEDS TRACKING | OK |

Total deferred items: **8** · Tracked: **8** · Ghost-work risk: **None**.

### Unmapped Tasks

None. Every task in tasks.md (T001–T080) cites at least one FR or anchors to a foundational/setup/polish purpose with explicit dependencies.

## Metrics

- Total Functional Requirements: **38**
- Total Success Criteria: **12** (8 buildable + 4 post-launch)
- Total Tasks: **80**
- Coverage % (FRs with ≥ 1 task): **100%**
- Coverage % (buildable SCs with ≥ 1 task): **100%** (5 explicit + 3 implicit)
- Ambiguity Count: **0**
- Duplication Count: **0**
- CRITICAL Issues: **0**
- HIGH Issues: **0**
- MEDIUM Issues: **2** (F2 SC explicit citation · P2 PORT label clarity)
- LOW Issues: **2** (L1 v2 false positive · L2 Zod-as-TS-analog)

## Next Actions

The spec / plan / tasks triad is internally consistent and constitution-compliant. **No CRITICAL or HIGH issue blocks `/speckit-taskstoissues`.**

Optional improvements (non-blocking):

1. **F2 — SC traceability**: append `(SC-003)` / `(SC-006)` / `(SC-011)` to T037, T024, and T050 bodies respectively for explicit success-criteria mapping. ~3 single-line edits in `tasks.md`.
2. **P2 — Plan label clarity**: in `plan.md` structure tree, annotate the five Spec 287-shipped files (`KeybindingContext.tsx`, `useKeybinding.ts`, `modalContext.tsx`, `overlayContext.tsx`, `notifications.tsx`) with `(already ported by Spec 287)`. ~5 single-line annotations.

Both are remediable in under 5 minutes and would strengthen reviewer confidence without changing scope.

Recommended next command: `/speckit-taskstoissues` to materialise the 80 tasks as GitHub Sub-Issues of Epic #1635 and resolve the 8 `NEEDS TRACKING` deferred-item rows.
