---

description: "Tasks for Epic γ #2294 — 5-primitive align with CC Tool.ts interface"

---

# Tasks: 5-Primitive Align with CC Tool.ts Interface

**Input**: Design documents from `/Users/um-yunsang/KOSMOS-w-2294/specs/2294-5-primitive-align/`
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, contracts/ (primitive-shape.md + registry-boot-guard.md), quickstart.md
**Worktree**: `/Users/um-yunsang/KOSMOS-w-2294`
**Branch**: `2294-5-primitive-align`
**Epic**: #2294 (Initiative #2290)

**Tests**: Three new test files are part of acceptance (FR-008/SC-002/SC-003/SC-007) — they are NOT optional for this Epic.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story. The four primitives map to two priority phases — US1 owns the LookupPrimitive happy-path (the Korean PTY smoke), US2 owns the boot-guard correctness across all 4 primitives.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Maps task to user story (US1, US2, US3, US4); Setup/Foundational/Polish phases carry no story label
- All file paths are absolute under the worktree

## Path Conventions

This is a TUI single-app project layered over a stable Python backend. All edits live under `tui/src/`; specs/docs live under `specs/2294-5-primitive-align/`. The Python backend (`src/kosmos/primitives/`) is **not** modified by this Epic.

## Dispatch Tree (per AGENTS.md § Agent Teams two-layer parallelism)

```text
Phase 1 Setup (T001-T002):                    Lead solo
Phase 2 Foundational (T003-T005):             Lead solo                    ┐ blocks
Phase 3 US1 LookupPrimitive (T006-T009):      sonnet-lookup                │ all
Phase 4 US2 Submit/Verify/Subscribe + guard   sonnet-submit       (T010-T012) ─┐ Sonnet [P]
            (T010-T020):                       sonnet-verify       (T013-T015) ─┤ all
                                               sonnet-subscribe    (T016-T018) ─┤ in
                                               sonnet-bootguard    (T019-T020)  │ parallel
Phase 5 US3 Citation tests (T021):            sonnet-citation                  ┘
Phase 6 US4 Span + resolve_loc (T022-T023):   sonnet-regress
Phase 7 PTY smoke (T024):                     Lead solo (cannot be teammate; PTY = Lead per memory)
Phase 8 Polish (T025-T027):                   Lead solo
```

Sonnet teammate budget per group: ≤ 5 tasks AND ≤ 10 files. Verified per group below.

---

## Phase 1: Setup

**Purpose**: Confirm the worktree is clean and reference materials are in place. CC source migration pattern (memory `feedback_cc_source_migration_pattern`) — Sonnet teammates copy from `.references/claude-code-sourcemap/` and adapt; do NOT write from scratch.

- [X] T001 Verify worktree state and dependencies — run `cd tui && bun install && bun typecheck` and `uv sync && uv run pytest -q` from `/Users/um-yunsang/KOSMOS-w-2294`; record baseline pass count for SC-005 comparison in `specs/2294-5-primitive-align/baseline.md` (1 pre-existing TUI snapshot fail + 1 pre-existing pytest fail expected per `c6747dd` baseline).
- [X] T002 Read 4 primitive source files (`tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive/*.ts`) and the CC reference (`.references/claude-code-sourcemap/restored-src/src/Tool.ts` :436/489/566; `.references/claude-code-sourcemap/restored-src/src/tools/AgentTool/AgentTool.tsx` for the implementation pattern of `validateInput`/`renderToolResultMessage`); produce a 1-page `specs/2294-5-primitive-align/cc-mapping.md` per memory `feedback_cc_source_migration_pattern`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Ship the shared helper module + the boot-guard module + the 4 primitive **stubs** (isMcp / empty validateInput / placeholder renderToolResultMessage) so that the boot guard can be wired up in Phase 4 with no broken intermediate state. This phase blocks every user-story phase.

**⚠️ CRITICAL**: No user-story work may begin until T005 lands.

- [X] T003 Create `tui/src/tools/shared/primitiveCitation.ts` exporting `extractCitation(adapterMeta) → {real_classification_url, policy_authority}` plus the shared `PrimitiveErrorCode` const-literal union (`AdapterNotFound | CitationMissing | RestrictedMode`); per data-model.md § E5 + contracts/primitive-shape.md § validateInput contract.
- [X] T004 Create `tui/src/services/toolRegistry/bootGuard.ts` implementing `verifyBootRegistry(registry) → BootResult` per `contracts/registry-boot-guard.md` (9-member walk + citation non-empty check + Korean diagnostic + ≤200ms budget); export-only, NOT yet wired into the registry construction site.
- [X] T005 Add minimal compliance stubs to all 4 primitives — set `isMcp = false`, add a default `validateInput` that returns `{result: true}`, add a default `renderToolResultMessage(output) → null`-rejecting placeholder text in 4 files: `tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive/*.ts`. These stubs make `bun typecheck` pass and let Phase 3 + Phase 4 replace each one independently.

**Checkpoint**: `bun typecheck` returns 0 errors; `bun test` shows the same pre-existing snapshot failure but no new failures; the boot guard module exists but is not invoked.

---

## Phase 3: User Story 1 - Citizen looks up emergency-room information by natural language (Priority: P1) 🎯 MVP

**Goal**: A citizen typing `의정부 응급실 알려줘` triggers `lookup(mode='fetch', tool_id='nmc_emergency_search', ...)` after a `resolve_location` precall, the permission prompt shows the NMC `real_classification_url` verbatim, and the Korean adapter result is rendered in the TUI conversation pane.

**Independent Test**: PTY transcript (Phase 7's T024 captures the actual run) — text log shows the canonical Korean strings + citation URL byte-identical.

**Dispatch**: `sonnet-lookup` teammate executes T006–T009 (4 tasks, 3 files: LookupPrimitive.ts + prompt.ts + scripts/smoke-emergency-lookup.expect) — well under the 5-task / 10-file budget.

### Implementation for User Story 1

- [X] T006 [US1] Replace the Phase 2 stub in `tui/src/tools/LookupPrimitive/LookupPrimitive.ts` with the real `validateInput`: for `mode='fetch'`, resolve `tool_id` against ToolRegistry, populate `permissionContext.citations` from `extractCitation()`, return Korean diagnostics on failure; for `mode='search'`, skip resolution and pass through to BM25 hint resolution (Spec 022). Per `contracts/primitive-shape.md § validateInput contract`.
- [X] T007 [US1] Replace the Phase 2 placeholder in `tui/src/tools/LookupPrimitive/LookupPrimitive.ts` with the real `renderToolResultMessage` per `contracts/primitive-shape.md § renderToolResultMessage` Lookup row — render adapter-name + count + first-3 summary for `mode='fetch'`; ranked-hit list for `mode='search'`; Korean error message for `output.ok === false`.
- [X] T008 [US1] Tighten `tui/src/tools/LookupPrimitive/prompt.ts` Korean `description` text — citizen-facing, ≤ 240 chars; remove the P3 MVP stub note from the file header comment now that real dispatch is wired (FR-002 + cleanup of dead `LookupPrimitive.ts:9` comment).
- [X] T009 [US1] Author `specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.expect` per `research.md § R-6` — spawn `bun run tui` → assert `KOSMOS` branding → send `의정부 응급실 알려줘\r` → wait 8s → send `y` → wait 4s → assert `nmc_emergency_search` + `real_classification_url` + Korean result tokens in the transcript → send `\003\003` → expect eof. Smoke is RUN by Lead in Phase 7.

**Checkpoint**: LookupPrimitive's full Tool-shape is implemented; PTY harness exists; SubmitPrimitive/VerifyPrimitive/SubscribePrimitive are still on Phase 2 stubs.

---

## Phase 4: User Story 2 - ToolRegistry validates new primitive shape at boot (Priority: P1)

**Goal**: At process boot the ToolRegistry walks all 22 entries (4 primitives + 18 adapters), asserts the 9-member contract, asserts non-empty citation on each adapter, fails closed with a Korean diagnostic on any mismatch, and emits `tool_registry: 22 entries verified ...` on success in ≤ 200 ms.

**Independent Test**: `bun test src/tools/__tests__/registry-boot.test.ts` passes 4 cases (real boot ✓, missing-renderToolResultMessage ✗, missing-citation ✗, isMcp-undefined ✗).

**Dispatch**: 4 parallel Sonnet teammates — one per primitive plus one for boot-guard integration. Each ≤ 5 tasks AND ≤ 10 files.

### Implementation for User Story 2

- [X] T010 [P] [US2] [sonnet-submit] Replace Phase 2 stub in `tui/src/tools/SubmitPrimitive/SubmitPrimitive.ts` with the real `validateInput` per `contracts/primitive-shape.md` (adapter resolve + citation populate + Korean diagnostic).
- [X] T011 [P] [US2] [sonnet-submit] Replace Phase 2 placeholder in `tui/src/tools/SubmitPrimitive/SubmitPrimitive.ts` with real `renderToolResultMessage` per `contracts/primitive-shape.md § Submit row` — submission receipt id + ministry name + Korean status text.
- [X] T012 [P] [US2] [sonnet-submit] Tighten `tui/src/tools/SubmitPrimitive/prompt.ts` Korean `description` text (≤ 240 chars) and clean P3 MVP stub note in the file header.
- [X] T013 [P] [US2] [sonnet-verify] Replace Phase 2 stub in `tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts` with the real `validateInput`.
- [X] T014 [P] [US2] [sonnet-verify] Replace Phase 2 placeholder in `tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts` with real `renderToolResultMessage` per `contracts/primitive-shape.md § Verify row` — verification status + cited authority.
- [X] T015 [P] [US2] [sonnet-verify] Tighten `tui/src/tools/VerifyPrimitive/prompt.ts` Korean `description` text (≤ 240 chars).
- [X] T016 [P] [US2] [sonnet-subscribe] Replace Phase 2 stub in `tui/src/tools/SubscribePrimitive/SubscribePrimitive.ts` with the real `validateInput`.
- [X] T017 [P] [US2] [sonnet-subscribe] Replace Phase 2 placeholder in `tui/src/tools/SubscribePrimitive/SubscribePrimitive.ts` with real `renderToolResultMessage` per `contracts/primitive-shape.md § Subscribe row` — handle id + cancel CTA + Korean explanation.
- [X] T018 [P] [US2] [sonnet-subscribe] Tighten `tui/src/tools/SubscribePrimitive/prompt.ts` Korean `description` text (≤ 240 chars).
- [X] T019 [US2] [sonnet-bootguard] Wire `verifyBootRegistry` into the existing ToolRegistry construction site (locate via grep for `register(` in `tui/src/services/toolRegistry/`); on failure call `console.error(diagnostic)` + `process.exit(1)`; on success log the single `tool_registry: ...` line; add a `bun run probe:tool-registry` script to `tui/package.json` that boots, prints the line, and exits 0/1.
- [X] T020 [US2] [sonnet-bootguard] Author `tui/src/tools/__tests__/registry-boot.test.ts` covering all 4 cases from `contracts/registry-boot-guard.md § Test plan` — real boot, missing-renderToolResultMessage, missing-citation, isMcp-undefined; assert ≤ 200 ms wall-clock budget on the real-boot case.

**Checkpoint**: All 4 primitives full-shape compliant; boot guard active; `bun run probe:tool-registry` prints `tool_registry: 22 entries verified (4 primitives, 18 adapters) in <N>ms`; `registry-boot.test.ts` 4/4 PASS.

---

## Phase 5: User Story 3 - Adapter policy citation surfaces verbatim in permission UI (Priority: P2)

**Goal**: Every `<PermissionRequest>` rendered for a primitive call contains the adapter's `real_classification_url` + `policy_authority` byte-for-byte, with zero KOSMOS-invented permission language.

**Independent Test**: `bun test src/tools/__tests__/permission-citation.test.ts` walks every Live + Mock adapter, renders the permission prompt with a representative invocation, asserts the citation strings match snapshot, asserts no string from the KOSMOS-invented blocklist appears.

**Dispatch**: 1 Sonnet teammate `sonnet-citation` (1 task, 1 file).

### Implementation for User Story 3

- [X] T021 [US3] [sonnet-citation] Author `tui/src/tools/__tests__/permission-citation.test.ts` — fixture-walk every adapter (Live + Mock from the actual Python adapter manifests imported via the existing IPC stub or a static-fixture variant for CI), render the `<FallbackPermissionRequest>` with a synthetic primitive-call context, snapshot-assert that `real_classification_url` and `policy_authority` strings appear verbatim, blocklist-assert no string from `["안전한 권한 등급", "본 시스템은", "KOSMOS는 다음과 같이", ...]` appears anywhere in the rendered prompt body. Blocklist enumerated in the file's top constant.

**Checkpoint**: 100% of adapter-routed permission prompts contain a verbatim citation; 0% contain KOSMOS-invented copy.

---

## Phase 6: User Story 4 - `resolve_location` continues to behave as a `lookup` sub-mode (Priority: P3)

**Goal**: The `resolve_location` meta-tool (Spec 022 sub-mode of `lookup`) emits byte-identical OTEL span attributes + envelope shape pre/post refactor.

**Independent Test**: `bun test src/tools/__tests__/span-attribute-parity.test.ts` snapshot matches pre-refactor baseline; existing pytest `tests/primitives/test_lookup_resolve_location.py` runs unchanged and passes.

**Dispatch**: 1 Sonnet teammate `sonnet-regress` (2 tasks, 1 file modified + 1 file inspected).

### Implementation for User Story 4

- [X] T022 [P] [US4] [sonnet-regress] Author `tui/src/tools/__tests__/span-attribute-parity.test.ts` — mount `LookupPrimitive`, dispatch a synthetic `lookup(mode='fetch', tool_id='nmc_emergency_search', ...)` call, snapshot OTEL span attributes (`kosmos.tool.id`, `kosmos.tool.mode`, `kosmos.adapter.real_classification_url`, plus existing Spec 021 GenAI/Tool/Permission attribute families); baseline = pre-refactor snapshot from `c6747dd` (capture as part of T001 baseline if not already present).
- [X] T023 [P] [US4] [sonnet-regress] Validate-only — run existing `uv run pytest tests/primitives/test_lookup_resolve_location.py` and confirm it passes unchanged; if the test does NOT exist or has rotted, file a sub-issue rather than expanding scope (per spec FR-010 the sub-mode behaviour is regression-only — no new code expected).

**Checkpoint**: span snapshot matches; resolve_location sub-mode envelope unchanged.

---

## Phase 7: PTY Smoke Capture (Lead solo — User Story 1 final acceptance)

**Goal**: Capture the actual PTY transcript that proves Story 1's full happy path, committed to the spec dir as the merge gate per memory `feedback_pr_pre_merge_interactive_test`.

**Dispatch**: Lead solo. Cannot be a Sonnet teammate (PTY interaction + capture is Lead's responsibility per `feedback_dispatch_unit_is_task_group`).

- [ ] T024 [US1] Run T009's expect script: `expect specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.expect > specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt`. Verify the captured log contains all 5 ordered grep markers from `quickstart.md § 5`. Commit both the script and the captured log on the same WIP commit. If the smoke fails, do NOT proceed — investigate root cause, fix, re-capture.

**Checkpoint**: PTY transcript committed; merge gate satisfied.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final acceptance verification + diff-budget audit + cross-link tidy-up. Lead solo — these are not parallelizable into Sonnet dispatch.

- [ ] T025 [P] Run final acceptance battery from `quickstart.md` — `bun typecheck` (0 errors), `bun test` + `uv run pytest -q` (no NEW failures vs T001 baseline), `bun run probe:tool-registry` (≤ 200 ms), `permission-citation.test.ts` (PASS), `span-attribute-parity.test.ts` (PASS); record results in `specs/2294-5-primitive-align/acceptance-report.md`.
- [ ] T026 [P] Diff-budget audit per SC-006: `git diff --stat main..HEAD -- tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive tui/src/tools/shared/primitiveCitation.ts tui/src/services/toolRegistry/bootGuard.ts tui/src/tools/__tests__` — total inserted+deleted ≤ 1500 net LOC; record in acceptance-report.md.
- [ ] T027 Cross-link finalisation — verify `specs/2294-5-primitive-align/spec.md`, `plan.md`, `tasks.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md` all reference each other consistently and the deferred-items table maps to live issue numbers (after `/speckit-taskstoissues` resolves the 2 `NEEDS TRACKING` markers).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup (T001-T002)**: No dependencies — can start immediately. Lead solo.
- **Phase 2 Foundational (T003-T005)**: Depends on Phase 1 completion. Lead solo. **BLOCKS** all user-story phases.
- **Phase 3 US1 (T006-T009)**: Depends on Phase 2 completion. `sonnet-lookup` teammate.
- **Phase 4 US2 (T010-T020)**: Depends on Phase 2 completion. **Can run in parallel with Phase 3**. 4 sonnet teammates: `sonnet-submit`, `sonnet-verify`, `sonnet-subscribe`, `sonnet-bootguard`. T019-T020 wait on T005-T018 for the registry-boot test fixture data, but boot-guard module (T004) is already shipped in Phase 2.
- **Phase 5 US3 (T021)**: Depends on Phase 4 completion (needs all 4 primitives populating citations). `sonnet-citation` teammate.
- **Phase 6 US4 (T022-T023)**: Depends on Phase 3 completion (Lookup must be real, not stub). `sonnet-regress` teammate. **Can run in parallel with Phase 5**.
- **Phase 7 PTY Smoke (T024)**: Depends on Phases 3, 4, 5, 6 completion. Lead solo.
- **Phase 8 Polish (T025-T027)**: Depends on Phase 7 completion. Lead solo.

### User Story Dependencies

- **US1 (T006-T009 + T024)**: First MVP — ships when Phase 7 captures the PTY transcript.
- **US2 (T010-T020)**: Independent of US1 in terms of acceptance — boot guard cares about all 4 primitives, not just Lookup.
- **US3 (T021)**: Depends on US1+US2 implementation (needs all 4 `validateInput` populating citation slot).
- **US4 (T022-T023)**: Depends on US1 implementation (needs LookupPrimitive `validateInput` populated).

### Within Each User Story

- For US1 / US2: prompt.ts edits can run in parallel with the .ts edits within the same primitive directory only because they are separate files; the canonical sequence is `validateInput → renderToolResultMessage → prompt.ts`.
- Tests (T020, T021, T022) MUST pass before Phase 7 PTY smoke.

### Parallel Opportunities

- T003 + T004 cannot parallel-dispatch (T005 depends on both). T005 cannot parallel-dispatch with T003/T004 because it edits the primitive files which both shared/primitiveCitation.ts (T003) and bootGuard.ts (T004) export types into.
- **T006 / T010 / T013 / T016**: All four primitives' `validateInput` edits — they touch DIFFERENT files, so the four sonnet teammates run truly in parallel.
- **T010-T012 / T013-T015 / T016-T018**: Three independent sonnet teammates run in parallel; intra-teammate the 3 tasks are sequential (same file edited 3 times).
- **T019 + T020**: Same teammate, sequential.
- **T021 + T022 + T023**: Two independent teammates in parallel.

---

## Parallel Example: Phase 4 (US2)

```bash
# Lead Opus dispatches 4 Sonnet teammates simultaneously after Phase 2 + Phase 3 ship:
#
# Teammate sonnet-submit  : T010 → T011 → T012  (3 tasks, 2 files)
# Teammate sonnet-verify  : T013 → T014 → T015  (3 tasks, 2 files)
# Teammate sonnet-subscribe: T016 → T017 → T018 (3 tasks, 2 files)
# Teammate sonnet-bootguard: T019 → T020        (2 tasks, 2 files)
#
# All four touch DISJOINT file sets. Lead reviews each teammate's WIP commit before
# moving to Phase 5. Push / PR / CI / Codex reply happen sequentially after all four merge.
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks US1 + US2 + US3 + US4)
3. Complete Phase 3: US1 LookupPrimitive
4. Skip Phases 4-6
5. Complete Phase 7: PTY smoke
6. **STOP and VALIDATE**: Citizen flow works end-to-end with LookupPrimitive
7. Note that boot guard (US2) would still fail without Submit/Verify/Subscribe migration — so MVP-only ship requires either (a) accepting US2 unfinished, or (b) keeping the Phase 2 stubs in place which DO pass the boot guard. Path (b) is what this Epic intends.

### Incremental Delivery

1. Phase 1 + 2 → foundation ready (boot guard inert).
2. Phase 3 → US1 MVP, PTY smoke run is Phase 7.
3. Phase 4 → US2 boot guard active across 4 primitives.
4. Phase 5 → US3 citation snapshot live.
5. Phase 6 → US4 regression snapshot live.
6. Phase 7 → PTY transcript committed.
7. Phase 8 → diff-budget + acceptance battery + cross-link tidy.

### Parallel Team Strategy

With 4 Sonnet teammates available (Phase 4 fan-out is the peak):

1. Lead solo → Phase 1 + Phase 2.
2. Lead dispatches 1 teammate (sonnet-lookup) for Phase 3 + 4 teammates for Phase 4 → 5 teammates running concurrently.
3. After all 5 commit and Lead reviews → 2 teammates for Phase 5 + 6 in parallel.
4. Lead solo → Phase 7 PTY + Phase 8 acceptance.

---

## Notes

- Total tasks: **27** (well under the 90-task sub-issue budget).
- Sonnet teammate budget: every group ≤ 5 tasks AND ≤ 10 files (verified per dispatch tree above).
- File-collision check: T005 (Phase 2 stubs) edits all 4 primitive files; subsequent Phase 3/4 tasks each edit ONE primitive file at a time, no collisions.
- CC source migration pattern: T002 produces `cc-mapping.md`; T006/T007/T010/T011/T013/T014/T016/T017 all reference it as their starting point per memory `feedback_cc_source_migration_pattern`.
- PTY smoke (T024) is non-deferrable — it is the merge gate per memory `feedback_pr_pre_merge_interactive_test`.
- Push / PR / CI / Codex reply are Lead Opus responsibility after all teammates' WIP commits are reviewed.
- Each task body inlines its acceptance signal (e.g. "0 errors", "≤ 200 ms", "all 4 cases PASS"); a teammate cannot mark a task `[X]` until that signal verifies locally.
