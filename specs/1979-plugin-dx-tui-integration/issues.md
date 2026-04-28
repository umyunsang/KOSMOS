# Phase 4: Issue Materialization Summary

**Feature**: 1979-plugin-dx-tui-integration
**Date**: 2026-04-28
**Epic**: [#1979 — Plugin DX TUI integration (1636 closure)](https://github.com/umyunsang/KOSMOS/issues/1979)
**GraphQL Epic ID**: `I_kwDOR_3evs8AAAABAi8QPQ`

---

## Sub-issue inventory (42 / 90 budget)

Final Epic #1979 sub-issue count: **42** ✅ (verified via GraphQL `subIssues.totalCount`)

### Phase 1: Setup (2 issues)

| Task | Issue | Title |
|---|---|---|
| T001 | [#2204](https://github.com/umyunsang/KOSMOS/issues/2204) | Capture today's broken /plugin install UX as L3 text-log + L2 JSONL |
| T002 | [#2205](https://github.com/umyunsang/KOSMOS/issues/2205) | Document gap analysis to notes-baseline.md |

### Phase 2: Foundational (4 issues)

| Task | Issue | Title |
|---|---|---|
| T003 | [#2206](https://github.com/umyunsang/KOSMOS/issues/2206) | Add plugin_op arm to stdio.py:1675 if-elif dispatch chain |
| T004 | [#2207](https://github.com/umyunsang/KOSMOS/issues/2207) | [P] Create plugin_op_dispatcher.py module skeleton |
| T005 | [#2208](https://github.com/umyunsang/KOSMOS/issues/2208) | [P] Extend ToolRegistry with _inactive set + lifecycle methods |
| T006 | [#2209](https://github.com/umyunsang/KOSMOS/issues/2209) | [P] Create IPCConsentBridge module (consent_bridge.py) |

### Phase 3: User Story 1 — citizen install (9 issues)

| Task | Issue | Title |
|---|---|---|
| T007 | [#2210](https://github.com/umyunsang/KOSMOS/issues/2210) | [US1] Add progress_emitter param to install_plugin() |
| T008 | [#2211](https://github.com/umyunsang/KOSMOS/issues/2211) | [US1] Implement handle_install in plugin_op_dispatcher.py |
| T009 | [#2212](https://github.com/umyunsang/KOSMOS/issues/2212) | [US1] Inject IPCConsentBridge into installer's consent_prompt seam |
| T010 | [#2213](https://github.com/umyunsang/KOSMOS/issues/2213) | [P] [US1] Create uninstall_plugin module |
| T011 | [#2214](https://github.com/umyunsang/KOSMOS/issues/2214) | [US1] Implement handle_uninstall mirroring handle_install pattern |
| T012 | [#2215](https://github.com/umyunsang/KOSMOS/issues/2215) | [US1] Implement handle_list with payload_delta enumeration |
| T013 | [#2216](https://github.com/umyunsang/KOSMOS/issues/2216) | [US1] Wire dispatcher boot params into stdio.py |
| T014 | [#2217](https://github.com/umyunsang/KOSMOS/issues/2217) | [P] [US1] Author unit tests test_plugin_op_dispatch.py |
| T015 | [#2218](https://github.com/umyunsang/KOSMOS/issues/2218) | [P] [US1] Author unit tests test_consent_bridge.py |

### Phase 4: User Story 2 — citizen invokes plugin (5 issues)

| Task | Issue | Title |
|---|---|---|
| T016 | [#2219](https://github.com/umyunsang/KOSMOS/issues/2219) | [US2] Add pluginsModifiedThisSession session-scoped flag in TUI |
| T017 | [#2220](https://github.com/umyunsang/KOSMOS/issues/2220) | [US2] Empty frame.tools when pluginsModifiedThisSession is true |
| T018 | [#2221](https://github.com/umyunsang/KOSMOS/issues/2221) | [P] [US2] Author test_plugin_install_to_invoke.py integration test |
| T019 | [#2222](https://github.com/umyunsang/KOSMOS/issues/2222) | [P] [US2] Author test_plugin_layer_routing.py 3-layer test |
| T020 | [#2223](https://github.com/umyunsang/KOSMOS/issues/2223) | [P] [US2] Author test_plugin_pii_acknowledgment.py PIPA round-trip test |

### Phase 5: User Story 3 — citizen plugin browser (10 issues)

| Task | Issue | Title |
|---|---|---|
| T021 | [#2224](https://github.com/umyunsang/KOSMOS/issues/2224) | [US3] CRITICAL: Swap commands.ts:133 import to KOSMOS plugin.ts |
| T022 | [#2225](https://github.com/umyunsang/KOSMOS/issues/2225) | [P] [US3] Remove H7 deferred suffix from plugin.ts acknowledgements |
| T023 | [#2226](https://github.com/umyunsang/KOSMOS/issues/2226) | [US3] Replace KOSMOS_PLUGIN_REGISTRY env-var stub with IPC round-trip |
| T024 | [#2227](https://github.com/umyunsang/KOSMOS/issues/2227) | [P] [US3] Extend PluginEntry shape with 6 additive fields |
| T025 | [#2228](https://github.com/umyunsang/KOSMOS/issues/2228) | [US3] Render 6 new columns in PluginBrowser layout |
| T026 | [#2229](https://github.com/umyunsang/KOSMOS/issues/2229) | [P] [US3] Implement detail modal sub-component (i keystroke) |
| T027 | [#2230](https://github.com/umyunsang/KOSMOS/issues/2230) | [P] [US3] Implement remove confirmation modal (r keystroke) |
| T028 | [#2231](https://github.com/umyunsang/KOSMOS/issues/2231) | [P] [US3] Wire `a` keystroke deferred message |
| T029 | [#2232](https://github.com/umyunsang/KOSMOS/issues/2232) | [P] [US3] Implement in-flight install placeholder row |
| T030 | [#2233](https://github.com/umyunsang/KOSMOS/issues/2233) | [P] [US3] Author bun tests for PluginBrowser + plugins commands |

### Phase 6: User Story 4 — E2E PTY verification (5 issues)

| Task | Issue | Title |
|---|---|---|
| T031 | [#2234](https://github.com/umyunsang/KOSMOS/issues/2234) | [P] [US4] Author fixture catalog + bundle + provenance under scripts/fixtures/ |
| T032 | [#2235](https://github.com/umyunsang/KOSMOS/issues/2235) | [P] [US4] L2 stdio JSONL probe script smoke-stdio.sh |
| T033 | [#2236](https://github.com/umyunsang/KOSMOS/issues/2236) | [P] [US4] L3 expect script smoke-1979.expect + 3 negatives |
| T034 | [#2237](https://github.com/umyunsang/KOSMOS/issues/2237) | [P] [US4] L4 vhs .tape script for visual demonstration |
| T035 | [#2238](https://github.com/umyunsang/KOSMOS/issues/2238) | [US4] Master orchestrator run-e2e.sh runs L1+L2+L3 |

### Phase 7: Polish (3 issues)

| Task | Issue | Title |
|---|---|---|
| T036 | [#2239](https://github.com/umyunsang/KOSMOS/issues/2239) | [P] Update spec.md Deferred table with 4 new entries |
| T037 | [#2240](https://github.com/umyunsang/KOSMOS/issues/2240) | [P] Add .gitignore entry for smoke-1979.gif |
| T038 | [#2241](https://github.com/umyunsang/KOSMOS/issues/2241) | Run final quickstart.md validation |

### Deferred placeholder issues (4)

These materialize follow-up work surfaced during Phase 0 research (V1, R-3+R-4) and Phase 3 analysis (Risks C, D). Each is a `[Deferred]` issue parented to Epic #1979 — close-skipped per memory `feedback_deferred_sub_issues`.

| Topic | Issue | Reason for Deferral |
|---|---|---|
| CC marketplace residue cleanup | [#2242](https://github.com/umyunsang/KOSMOS/issues/2242) | Spec 1633-style dead-code-elimination Epic; preserves SC-005 baseline parity |
| Plugin runtime enable/disable IPC | [#2243](https://github.com/umyunsang/KOSMOS/issues/2243) | Requires Spec 032 envelope schema bump; out of scope |
| SC-001 live environment validation | [#2244](https://github.com/umyunsang/KOSMOS/issues/2244) | Fixture catalog only; live network calibration deferred |
| Plugin list payload reassembly stress | [#2245](https://github.com/umyunsang/KOSMOS/issues/2245) | MVP3 targets 1-4 plugins; >50-plugin scale test deferred |

### Pre-existing NEEDS TRACKING (2 — handled in T036 follow-up)

| Topic | Status | Reason |
|---|---|---|
| External plugin contributor onboarding UX | NEEDS TRACKING | Out of this Epic's scope (consume-side only); placeholder creation deferred to T036 phase |
| Plugin store catalog index sync mechanism | NEEDS TRACKING | Registry-side concern; placeholder creation deferred to T036 phase |

---

## Cleanup record

During the issue materialization phase, an accidental second invocation of `create_issues.py` produced 42 duplicate issues #2246-#2287. These were identified within minutes and remediated via `scripts/cleanup_duplicates.py`:

- **Detached** all 42 duplicates from Epic #1979 via GraphQL `removeSubIssue` mutation.
- **Closed** with `--reason "not planned"` plus a comment pointing at the canonical issue (#2204-#2245 1:1 mapping).
- **Verified** Epic #1979 sub-issue count returned to 42 (= 38 tasks + 4 deferred).

The cleanup operation is idempotent and reversible — closed duplicates can be reopened if needed; sub-issue links can be restored.

---

## Sub-Issues API verification

```bash
gh api graphql -f query='query { repository(owner: "umyunsang", name: "KOSMOS") { issue(number: 1979) { subIssues { totalCount } } } }' --jq '.data.repository.issue.subIssues.totalCount'
# Output: 42
```

Per memory `feedback_graphql_issue_tracking`, ALL sub-issue tracking henceforth uses GraphQL Sub-Issues API v2 (`subIssues` / `addSubIssue` / `removeSubIssue`) — never the legacy `trackedIssues` field, never REST `repos/.../issues` enumeration as the basis for tracking claims.

---

## Labels applied (consistent across all 42 issues)

- `agent-ready` — Lead/Teammate may pick up autonomously per memory `feedback_speckit_autonomous`
- `epic-1979` — sub-issue lineage tag
- `phase-1` through `phase-7` — phase grouping
- `P1` (US1, US2) / `P2` (US3, US4) — priority
- `parallel-safe` — only on [P] tasks
- `size/S` (≤2hr) / `size/M` (2-8hr) / `size/L` (>8hr) — effort heuristic
- `deferred` + `deferred-from-1979` + `needs-spec` — only on the 4 placeholder issues

---

## spec.md update

The spec's `Deferred to Future Work` table was updated with 4 new rows pointing at the placeholder issues (#2242-#2245). The 2 pre-existing NEEDS TRACKING markers (External contributor UX, Catalog sync) remain — to be materialized as part of T036 follow-up or a separate `/speckit-taskstoissues` invocation if ever surfaced as in-scope.

---

## Next step: `/speckit-implement`

The Epic is now ready for implementation. Per spec.md MVP scoping:

1. **MVP1** — Phases 1+2+3 (Setup + Foundational + US1) → citizen install loop via shell entry-point works.
2. **MVP2** — +Phase 4 (US2) → citizen invokes plugin tool through 5-primitive surface.
3. **MVP3** — +Phase 5 (US3) → critical T021 swap activates citizen `/plugin install` slash command.
4. **MVP4** — +Phase 6+7 (US4 + Polish) → E2E verified, ready for PR.

Per AGENTS.md § Agent Teams, `/speckit-implement` may spawn:
- **Lead (Opus)** — owns critical-path tasks (T003, T021, integration synthesis).
- **Teammate A (Sonnet, Backend Architect)** — Phase 2/3 backend (T004, T005, T006, T007, T008, T010, T011, T012, T013).
- **Teammate B (Sonnet, API Tester)** — Phase 3/4/5 tests (T014, T015, T018, T019, T020, T030).
- **Teammate C (Sonnet, Frontend Developer)** — Phase 5 TUI (T021-T029).
- **Teammate D (Sonnet, API Tester)** — Phase 6 E2E (T031-T035).

Per memory `feedback_integrated_pr_only`, the final PR is single-integrated. Per memory `feedback_pr_closing_refs`, body uses `Closes #1979` only (Epic). Task sub-issues (#2204-#2241) close post-merge via `gh issue close`. Deferred placeholders (#2242-#2245) skip close per memory `feedback_deferred_sub_issues`.
