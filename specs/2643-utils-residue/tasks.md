---
description: "Task list for Epic G — Utils 잔존 정리 (sessionTitle PORT + dateTimeParser PORT + permissions Path B + secureStorage ADR)"
---

# Tasks: Epic G — Utils 잔존 정리 (S9)

**Input**: Design documents from `/specs/2643-utils-residue/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Test tasks INCLUDED — spec FR-011 mandates Korean fixture regression tests, FR-005 mandates analytics emission, both verified via `bun test`. Permissions regression suite ensures Path B refactor preserves call-site behavior.

**Organization**: Tasks grouped by user story to enable independent Sonnet teammate dispatch (4 user stories × 1 teammate each per AGENTS.md § Agent Teams).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story tag (US1, US2, US3, US4)

## Path Conventions

- **TUI surface**: `tui/src/utils/` (TypeScript on Bun)
- **Tests**: `tui/src/utils/__tests__/` and `tui/src/utils/mcp/__tests__/`
- **ADR**: `docs/adr/`
- **Audit cross-refs**: `specs/cc-migration-audit/`

---

## Phase 1: Setup (Lead solo)

**Purpose**: Verify worktree state + dependency installation + baseline test snapshot.

- [X] T001 Verify worktree at `/Users/um-yunsang/UMMAYA-w-2643/` is on `feat/2643-s9-utils-residue` branch with `.specify/feature.json` pointing to `specs/2643-utils-residue`
- [X] T002 Run `bun install` in `tui/` and `uv sync` at repo root; record `bun test` baseline snapshot to `specs/2643-utils-residue/baseline-bun-test.txt` and `uv run pytest --quiet` baseline to `specs/2643-utils-residue/baseline-pytest.txt`
- [X] T003 [P] Verify `tui/src/services/api/claude.ts:3270` `queryHaiku` exports the signature consumed by CC's sessionTitle.ts and dateTimeParser.ts (grep + line-count gate)

---

## Phase 2: Foundational (none — independent stories)

**Purpose**: No blocking prerequisites; the 4 user stories touch disjoint files and may proceed in parallel after Phase 1.

**Checkpoint**: Foundation ready — all 4 user stories may dispatch to Sonnet teammates in parallel.

---

## Phase 3: User Story 1 — sessionTitle PORT (Priority: P1) 🎯 MVP

**Goal**: Restore `cli/print.ts:156` broken import by porting `utils/sessionTitle.ts` byte-identical from CC with K-EXAONE wired via existing `queryHaiku`.

**Independent Test**: `bun typecheck` passes (`cli/print.ts:156` resolves), `bun test tui/src/utils/__tests__/sessionTitle.test.ts` passes 3+ cases (empty input → null, valid mock → title, abort signal → null).

### Implementation for User Story 1

- [X] T010 [P] [US1] Create `tui/src/utils/sessionTitle.ts` by byte-copying `.references/claude-code-sourcemap/restored-src/src/utils/sessionTitle.ts` and prepending the SWAP attribution comment line per `specs/2643-utils-residue/contracts/sessionTitle.contract.md`
- [X] T011 [P] [US1] Verify all 10 imports in the new `sessionTitle.ts` resolve in UMMAYA (`bun typecheck` against the file path) — escalate any unresolved import to research.md (no fallback rewrites)
- [X] T012 [US1] Create `tui/src/utils/__tests__/sessionTitle.test.ts` with 3 test cases (empty description → null, valid mock response → title, malformed JSON → null) using `bun:test` `mock.module()` per the contract test plan
- [X] T013 [US1] Run `bun test tui/src/utils/__tests__/sessionTitle.test.ts` and confirm 3/3 PASS; capture output to `specs/2643-utils-residue/us1-test-output.txt`
- [X] T014 [US1] Run `bun typecheck` end-to-end and confirm `cli/print.ts:156` import resolves with zero new errors; capture to `specs/2643-utils-residue/us1-typecheck.txt`

**Checkpoint**: US1 fully functional. `cli/print.ts:3803` `generateSessionTitle` callsite reachable.

---

## Phase 4: User Story 2 — dateTimeParser PORT + Korean fixtures (Priority: P1)

**Goal**: Restore Korean natural-language date/time parsing for MCP elicitation surface; replace `elicitationValidation.ts` inline ISO8601-only stub.

**Independent Test**: `bun test tui/src/utils/mcp/__tests__/dateTimeParser.test.ts` passes 5+ Korean fixture cases (`내일 오후 3시`, `다음주 월요일 오전 9시`, `다음주 월요일`, `asdf` reject, looksLikeISO8601 boundary).

### Implementation for User Story 2

- [X] T020 [P] [US2] Create `tui/src/utils/mcp/dateTimeParser.ts` by byte-copying `.references/claude-code-sourcemap/restored-src/src/utils/mcp/dateTimeParser.ts` and prepending the SWAP attribution comment per `specs/2643-utils-residue/contracts/dateTimeParser.contract.md`
- [X] T021 [P] [US2] Create `tui/src/utils/mcp/__tests__/dateTimeParser.test.ts` with 5 test cases (3 Korean success paths + 1 INVALID failure + 1 looksLikeISO8601) using `bun:test` `mock.module()` per the contract test plan
- [X] T022 [US2] Edit `tui/src/utils/mcp/elicitationValidation.ts`: remove lines 10-19 inline stub block, add `import { looksLikeISO8601, parseNaturalLanguageDateTime } from './dateTimeParser.js'` near the existing imports; verify the `validateElicitationInputAsync` callsite at lines 323-339 still type-checks (CC signature is `(input, format, signal)`; UMMAYA callsite already passes `schema.format` + signal so signature matches)
- [X] T023 [US2] Run `bun test tui/src/utils/mcp/__tests__/dateTimeParser.test.ts` and confirm 5/5 PASS; capture to `specs/2643-utils-residue/us2-test-output.txt`
- [X] T024 [US2] Run `bun typecheck` end-to-end and confirm `elicitationValidation.ts` typechecks with the new imports; capture to `specs/2643-utils-residue/us2-typecheck.txt`

**Checkpoint**: US2 fully functional. Korean inputs flow through `validateElicitationInputAsync` → mocked K-EXAONE → ISO 8601 → zod validation.

---

## Phase 5: User Story 3 — permissions Path B 모듈 분리 (Priority: P2)

**Goal**: Restore CC `permissions.ts` import shape by extracting the inline 43-LOC `yoloClassifier` stub into a sibling module, preserving callsite behavior (no-op auto-mode).

**Independent Test**: `tui/src/utils/permissions/yoloClassifier.ts` exists, `permissions.ts` LOC ≤ 1494, `diff` against CC ≤ 8 hunk lines, `bun test` permissions suite 0 regression.

### Implementation for User Story 3

- [X] T030 [P] [US3] Create `tui/src/utils/permissions/yoloClassifier.ts` per `specs/2643-utils-residue/contracts/yoloClassifier.contract.md` — module header + `YoloClassifierResult` type (CC-shape, byte-identical with current inline) + `formatActionForClassifier` stub + `classifyYoloAction` stub returning `{unavailable: true, shouldBlock: false}`
- [X] T031 [US3] Edit `tui/src/utils/permissions/permissions.ts`: delete lines 102-145 (44-LOC inline stub block including the `// UMMAYA Spec 1633 / Epic #2293` comment); replace with the byte-identical CC import: `import { classifyYoloAction, formatActionForClassifier } from './yoloClassifier.js'`
- [X] T032 [US3] Run `wc -l tui/src/utils/permissions/permissions.ts` and verify ≤ 1494 (CC 1486 + max 8 swap-1 lines); run `diff .references/claude-code-sourcemap/restored-src/src/utils/permissions/permissions.ts tui/src/utils/permissions/permissions.ts | grep "^[<>]" | wc -l` and verify ≤ 8; capture both to `specs/2643-utils-residue/us3-diff-audit.txt`
- [X] T033 [US3] Run `bun test` filtered to permissions suite (`bun test tui/src/utils/permissions/`) and confirm 0 regression vs `baseline-bun-test.txt`; capture to `specs/2643-utils-residue/us3-test-output.txt`
- [X] T034 [US3] Run `bun typecheck` end-to-end and confirm zero new errors; capture to `specs/2643-utils-residue/us3-typecheck.txt`

**Checkpoint**: US3 fully functional. CC `permissions.ts` import structure preserved.

---

## Phase 6: User Story 4 — secureStorage DROP ADR (Priority: P3)

**Goal**: Author `docs/adr/ADR-009-secureStorage-drop.md` with 5-section structure and measurable future-trigger; cross-reference from audit docs.

**Independent Test**: ADR-009 file exists with all 5 sections, all 6 CC `secureStorage/` files enumerated with LOC, `decisions.md` and `scope-S9-utils.md` updated with `ADR-009` cross-references.

### Implementation for User Story 4

- [X] T040 [P] [US4] Create `docs/adr/ADR-009-secureStorage-drop.md` with 5 sections (Status: Accepted / Context: UMMAYA .env-only credential surface vs. CC's 6-file Keychain stack / Decision: drop the secureStorage subtree / Consequences: simpler attack surface, unsuitable for multi-tenant per-ministry keys / Future trigger: measurable conditions per FR-019), enumerate all 6 CC files with LOC totals per FR-018
- [X] T041 [US4] Edit `specs/cc-migration-audit/decisions.md` § S9 Utils row 2 (`utils/secureStorage/ DROP 확정`) to append `(see [ADR-009](../../docs/adr/ADR-009-secureStorage-drop.md))`
- [X] T042 [US4] Edit `specs/cc-migration-audit/scope-S9-utils.md` § P0-2~6 (line ~60-62) and § 사용자 결정 필요 § D2 (line ~129) to append `→ resolved by [ADR-009](../../docs/adr/ADR-009-secureStorage-drop.md)`
- [X] T043 [US4] Verify ADR cross-reference round-trip: `grep -l "ADR-009" specs/cc-migration-audit/` returns both `decisions.md` and `scope-S9-utils.md`; capture to `specs/2643-utils-residue/us4-cross-ref.txt`

**Checkpoint**: US4 fully functional. ADR-009 in place; audit doc tree links to it from 2 entry points.

---

## Phase 7: Polish & Cross-Cutting (Lead solo)

**Purpose**: End-to-end verification chain (Layer 1a-5), K-EXAONE retry budget measurement, PR preparation.

- [X] T050 Run `uv run pytest --quiet` and confirm parity with `baseline-pytest.txt` (no Python changes expected); capture to `specs/2643-utils-residue/after-pytest.txt`
- [X] T051 Run `bun test` (all suites) and confirm net delta = +5 ~ +8 passing tests vs `baseline-bun-test.txt` (US1: 3, US2: 5; US3: 0 new; US4: 0 new); capture to `specs/2643-utils-residue/after-bun-test.txt`
- [X] T052 Run `bun typecheck` end-to-end and confirm 0 new errors; capture to `specs/2643-utils-residue/after-typecheck.txt`
- [ ] T053 Author `specs/2643-utils-residue/scripts/smoke-session-title.sh` per quickstart.md Layer 3 protocol; run `scripts/tui-tmux-capture.sh specs/2643-utils-residue/smoke-frames specs/2643-utils-residue/scripts/smoke-session-title.sh` and capture frames to `specs/2643-utils-residue/smoke-frames/`
- [ ] T054 Author `specs/2643-utils-residue/scripts/smoke.tape` per quickstart.md Layer 4 protocol with 3 `Screenshot` directives; run `vhs specs/2643-utils-residue/scripts/smoke.tape` and verify 3 PNG keyframes generated; Lead Opus reads each via Read tool to confirm UI state
- [ ] T055 SC-007 K-EXAONE retry budget measurement: author `specs/2643-utils-residue/scripts/measure-session-title-latency.ts` per quickstart.md, run manually 3 times with non-trivial Korean inputs, capture to `specs/2643-utils-residue/sc-007-measurements.json`, verify p95 ≤ 6 s, update quickstart.md with measured values
- [X] T056 Diff audit: run the 3 `diff` commands from quickstart.md "Diff Audit" section; verify (a) sessionTitle.ts diff ≤ 3 hunk lines (SWAP comment), (b) dateTimeParser.ts diff ≤ 3 hunk lines (SWAP comment), (c) permissions.ts diff ≤ 8 hunk lines; capture to `specs/2643-utils-residue/diff-audit.txt`
- [X] T057 Update CLAUDE.md "Recent Changes" entry with one-line summary citing Epic #2643, all 4 PORT/ADR items, zero new deps, bun/pytest delta
- [X] T058 `git add` all spec dir + `tui/src/utils/sessionTitle.ts` + `tui/src/utils/mcp/dateTimeParser.ts` + edited `elicitationValidation.ts` + new `yoloClassifier.ts` + edited `permissions.ts` + new ADR-009 + edited audit docs + CLAUDE.md; commit with conventional message `feat(2643): utils residue — sessionTitle PORT + dateTimeParser PORT + permissions Path B + secureStorage ADR (closes Epic #2643)`; push to `origin feat/2643-s9-utils-residue`
- [X] T059 Create PR with `gh pr create --title "feat(2643): utils residue — sessionTitle PORT + dateTimeParser PORT + permissions Path B + secureStorage ADR" --body "Closes #2643"` (body MUST contain only `Closes #2643`, no Task sub-issues per AGENTS.md PR close rule)
- [ ] T060 Monitor `gh pr checks --watch --interval 10`; address Codex inline review per AGENTS.md § Code review; verify Copilot Gate transitions to `completed`

---

## Dependency Graph

```text
Phase 1 (Setup):                T001 → T002 → T003
Phase 2 (Foundational):          (none)

Phase 3 (US1):                  T010 ──┐
                                T011 ──┼─→ T012 → T013 → T014
                                       │
Phase 4 (US2):                  T020 ──┤
                                T021 ──┼─→ T022 → T023 → T024
                                       │
Phase 5 (US3):                  T030 ──┤
                                       │
                                T031 → T032 → T033 → T034
Phase 6 (US4):                  T040 ──┘
                                T041 → T042 → T043

Phase 7 (Polish):               T050 → T051 → T052 → T053 → T054 → T055 → T056 → T057 → T058 → T059 → T060
```

**Parallel opportunities**:
- T003, T010, T011, T020, T021, T030, T040 are all `[P]` — fully parallel-safe between teammates (different files, no shared state).
- T010 + T020 + T030 + T040 form the canonical 4-Sonnet-teammate dispatch unit (one teammate per user story).

## Dispatch Tree (drafted here, finalised in `dispatch-tree.md` during /speckit-implement)

```text
Phase 1 Setup (T001-T003): Lead solo
Phase 2 Foundational: (none)
Phase 3 US1 (T010-T014): sonnet-us1 (sessionTitle)         ┐
Phase 4 US2 (T020-T024): sonnet-us2 (dateTimeParser)       ├─ parallel
Phase 5 US3 (T030-T034): sonnet-us3 (permissions Path B)   │
Phase 6 US4 (T040-T043): sonnet-us4 (ADR-009)              ┘
Phase 7 Polish (T050-T060): Lead solo
```

Each Sonnet teammate gets ≤ 5 tasks AND ≤ 5 file changes (well within the AGENTS.md ≤ 10 file budget per teammate).

## Implementation Strategy

**MVP scope**: User Story 1 alone restores the broken `cli/print.ts:156` import — the highest-impact single deliverable. US1 + US2 together complete both Korean-citizen-UX critical surfaces. US3 + US4 finalise CC structural fidelity and forensic ADR pinning.

**Incremental delivery**:
1. **Iteration 1**: Phase 1 (T001-T003) → Phase 3 US1 (T010-T014) merged ⇒ broken import fixed.
2. **Iteration 2**: Phase 4 US2 (T020-T024) ⇒ Korean date/time parsing restored.
3. **Iteration 3**: Phase 5 US3 (T030-T034) ⇒ CC structural fidelity restored.
4. **Iteration 4**: Phase 6 US4 (T040-T043) ⇒ ADR-009 pinned, audit cross-references updated.
5. **Iteration 5**: Phase 7 (T050-T060) ⇒ end-to-end verification + PR + CI.

In practice, all 4 user stories dispatch in parallel under one Lead Opus (Layer 2 Sonnet teammate dispatch per AGENTS.md), then Lead serializes Phase 7. Total Tasks: **23** — well within the 90-task GitHub Sub-Issues cap.

## Notes

- Task count: 23 (T001-T003 setup + T010-T014 US1 + T020-T024 US2 + T030-T034 US3 + T040-T043 US4 + T050-T060 polish). Well within the 90-task budget.
- All test tasks are `bun test`-only — `pytest` baseline preserved (Python untouched).
- No new runtime dependencies introduced (zero deps invariant per AGENTS.md hard rule + spec assumption).
- Spec FR-001 ~ FR-020 fully covered: FR-001 → T010, FR-002 → T010, FR-003 → T010, FR-004 → T012, FR-005 → T012; FR-006 → T020, FR-007 → T020, FR-008 → T021, FR-009 → T021, FR-010 → T022, FR-011 → T021/T023; FR-012 → T030, FR-013 → T030, FR-014 → T031/T032, FR-015 → T031, FR-016 → T032/T056; FR-017 → T040, FR-018 → T040, FR-019 → T040, FR-020 → T041/T042/T043.
- Spec SC-001 ~ SC-008 fully covered: SC-001 → T014, SC-002 → T024, SC-003 → T023, SC-004 → T032, SC-005 → T033/T051, SC-006 → T040/T043, SC-007 → T055, SC-008 → T053/T054.
