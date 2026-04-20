---
description: "Task list for Epic #1303 — Shortcut Tier 1 port (spec 288)"
---

# Tasks: Shortcut Tier 1 Port — Citizen-Safe Keybinding Layer

**Input**: Design documents from `/specs/288-shortcut-tier1-port/`
**Prerequisites**: plan.md · spec.md · research.md · data-model.md · contracts/ · quickstart.md
**Parent Epic**: #1303 · **Initiative**: #2 Phase 2 Multi-Agent Swarm · **ADR**: ADR-006 Part C / A-10

**Tests**: This spec explicitly requests TDD-style tests (see spec.md SC-002, SC-003, SC-004, SC-005, SC-006 — all measurable outcomes require automated test evidence). Tests are written BEFORE or alongside their implementation targets; each test task MUST fail before its paired implementation task begins.

**Organization**: Tasks are grouped by user story. All user stories depend on Foundational Phase 2 (registry + resolver core). Within a story, sub-tasks can be parallelised across different files (`[P]`).

**Task budget**: 42 tasks (≤ 90-Task cap per memory rule 2026-04-19). Cohesion-merged where multiple small actions touch the same file.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependencies)
- **[Story]**: `US1`..`US7` maps to the 7 user stories in spec.md
- File paths are absolute-from-repo-root

## Path Conventions

- TUI: `tui/src/keybindings/`, `tui/src/hooks/`, `tui/src/components/input/`, `tui/src/permissions/`
- Tests: `tui/tests/keybindings/`
- Python integration: existing `src/kosmos/tui/audit.py` (Spec 024) and `src/kosmos/agents/cancellation.py` (Spec 027) — consumed, not modified
- Docs: `docs/adr/`, spec files under `specs/288-shortcut-tier1-port/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `tui/src/keybindings/` module shell and scaffold the test directory. No logic yet.

- [ ] T001 Create module directory `tui/src/keybindings/` with an `index.ts` re-export barrel. Also create `tui/tests/keybindings/` and `tui/tests/keybindings/fixtures/`. Zero logic; structural only. Satisfies plan.md § Project Structure.
- [ ] T002 [P] Copy `contracts/keybinding-schema.ts` into `tui/src/keybindings/types.ts` as the source-of-truth type surface. No edits — verbatim copy. Verifies contract/implementation parity (SC-009).
- [ ] T003 [P] Copy `contracts/user-override.schema.json` into `tui/src/keybindings/schemas/user-override.schema.json`. Used at runtime by `loadUserBindings.ts` for JSON-schema validation and at build time for IDE autocompletion. Reference: plan.md § Storage.

**Checkpoint 1**: Module shell exists; types + schemas are in place; no behaviour yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the registry, parser, resolver, and accessibility announcer that ALL user stories depend on. This phase BLOCKS all seven user stories.

**⚠️ CRITICAL**: No user-story work can begin until this phase completes.

### Port CC keybinding primitives

- [ ] T004 [P] Port `.references/claude-code-sourcemap/restored-src/src/keybindings/parser.ts` → `tui/src/keybindings/parser.ts`. Preserve the EBNF grammar in data-model.md § ChordString. Canonicalise modifier order (`ctrl→shift→alt→meta`). Unit-testable; no dependencies. Satisfies FR-002, SC-009.
- [ ] T005 [P] Port CC `match.ts` → `tui/src/keybindings/match.ts`. Chord-to-event matcher. Handles raw-byte detection (`\x03`, `\x04`) per FR-016 and D2. Unit-testable. Satisfies FR-016.
- [ ] T006 [P] Port CC `shortcutFormat.ts` → `tui/src/keybindings/shortcutFormat.ts`. Chord → human-readable display string (e.g., `ctrl+c` → `Ctrl+C`). Used by `useShortcutDisplay` hook and by the catalogue dump for accessibility (FR-032).
- [ ] T007 [P] Port CC `schema.ts` → `tui/src/keybindings/schema.ts`. Narrow `KEYBINDING_CONTEXTS` to the 4 KOSMOS contexts (Global · Chat · HistorySearch · Confirmation). Mirror `KEYBINDING_CONTEXT_DESCRIPTIONS` but use the Korean+English strings from contracts/keybinding-schema.ts. Satisfies FR-001, data-model.md § 1.
- [ ] T008 Port CC `reservedShortcuts.ts` → `tui/src/keybindings/reservedShortcuts.ts`. KOSMOS reserved set: `agent-interrupt`, `session-exit`. Expose `isReservedAction(action)` and `isReservedChord(chord)`. Depends on T007 (contexts). Satisfies FR-027, D6.

### Registry + override loader

- [ ] T009 Build `tui/src/keybindings/defaultBindings.ts` with the seven Tier 1 entries. Platform-specific `shift+tab` ↔ `meta+m` fallback per D3 (inherit from CC L17-L30). Depends on T004, T007, T008. Satisfies FR-002, data-model.md § 2.
- [ ] T010 Port CC `loadUserBindings.ts` → `tui/src/keybindings/loadUserBindings.ts`. Read `~/.kosmos/keybindings.json`; JSON-schema-validate against `schemas/user-override.schema.json`; silent degrade on missing/invalid (FR-023, FR-024); reject reserved-action remaps with warning (FR-027). Depends on T008. Satisfies FR-023..FR-028.
- [ ] T011 Port CC `validate.ts` → `tui/src/keybindings/validate.ts`. Registry-build-time invariants from data-model.md § KeybindingEntry (reserved ⟹ !remappable; disabled ⟹ !reserved; chord-grammar conformance). Depends on T004, T008. Satisfies data-model.md § 3 invariants.
- [ ] T012 Build the registry assembler in `tui/src/keybindings/registry.ts` that merges `DEFAULT_BINDINGS` + loader output through `validate`. Exposes `KeybindingRegistry` interface from contracts/keybinding-schema.ts. Immutable, built once at TUI boot. Depends on T009, T010, T011. Satisfies FR-001, FR-003.

### Resolver + IME gate (the spec's core behavioural contract)

- [ ] T013 Port CC `resolver.ts` → `tui/src/keybindings/resolver.ts` with precedence modal → form → context → global (D7). Depends on T012. Does NOT yet include IME gate (paired with T014). Satisfies FR-003.
- [ ] T014 Integrate IME gate into resolver. Inject `useKoreanIME().isComposing` at the resolver entry point; short-circuit every action with `mutates_buffer === true` while composing. Returns `ResolutionResult { kind: 'blocked', reason: 'ime-composing' }`. This is the centralisation mandated by FR-007. Depends on T013. Satisfies FR-005, FR-006, FR-007, D4.
- [ ] T014b Integrate OTel span emission into resolver. On every `ResolutionResult` of kind `dispatched` or `blocked`, emit a span with attributes `kosmos.tui.binding`, `kosmos.tui.binding.context`, `kosmos.tui.binding.chord`, `kosmos.tui.binding.reserved`; on blocks, additionally set `kosmos.tui.binding.blocked.reason`. Reserved-action dispatches additionally call the Spec 024 `ToolCallAuditRecord` writer with event types `user-interrupted` / `session-exited`. Depends on T014. Satisfies FR-033, FR-034, data-model.md § Observability fields.

### Accessibility announcer (KOSMOS-original)

- [ ] T015 Build `tui/src/keybindings/accessibilityAnnouncer.ts` implementing the `AccessibilityAnnouncer` interface from contracts/keybinding-schema.ts. Buffered text channel reaching screen readers (NVDA/VoiceOver/센스리더) through standard stdout announce pipeline per D8 and KWCAG 2.1 § 4.1.3. Satisfies FR-030, FR-031.

### React wiring

- [ ] T016 [P] Port CC `KeybindingContext.tsx` → `tui/src/keybindings/KeybindingContext.tsx`. React context exposing the registry + resolver to descendants. No state mutation — the registry is immutable at boot. Depends on T012.
- [ ] T017 [P] Port CC `KeybindingProviderSetup.tsx` → `tui/src/keybindings/KeybindingProviderSetup.tsx`. Wires registry + context provider + accessibility announcer at app root. Depends on T012, T015, T016.
- [ ] T018 [P] Port CC `useKeybinding.ts` → `tui/src/keybindings/useKeybinding.ts`. Per-context hook: `useKeybinding('Chat', handlers)` subscribes a component to resolver events. Depends on T016.
- [ ] T019 [P] Port CC `useShortcutDisplay.ts` → `tui/src/keybindings/useShortcutDisplay.ts`. Hook returning the current `effective_chord` for a given action. Depends on T018.
- [ ] T020 Port CC `src/hooks/useGlobalKeybindings.tsx` → `tui/src/hooks/useGlobalKeybindings.tsx`. Global handler driving `Ink.useInput` raw mode, feeding events into the resolver. This is the single entry point for all ChordEvents. Depends on T014, T017. Satisfies FR-003, FR-016.
- [ ] T021 Wire `<KeybindingProvider>` into `tui/src/main.tsx` root. One-line integration; no logic. Depends on T017.

### Foundational test suite

- [ ] T022 [P] Add `tui/tests/keybindings/parser.test.ts` — grammar conformance, canonicalisation order, rejection of malformed chords. Targets T004. Satisfies SC-009 (shape parity).
- [ ] T023 [P] Add `tui/tests/keybindings/match.test.ts` — chord-to-event matching incl. raw-byte `\x03`, `\x04`, `shift+tab` and Windows fallback `meta+m`. Targets T005. Satisfies FR-016.
- [ ] T024 [P] Add `tui/tests/keybindings/validate.test.ts` — invariants (reserved ⟹ !remappable), malformed override rejection. Targets T011.
- [ ] T025 [P] Add `tui/tests/keybindings/resolver.test.ts` — precedence modal→form→context→global; IME-gate short-circuit on `mutates_buffer` actions; OTel span emission on `dispatched`/`blocked` results (attribute presence + values); burst-input stability (≥ 10 chords / 100 ms, zero dropped `ChordEvent`). Targets T013, T014, T014b. Satisfies FR-003, FR-005, FR-007, FR-033, FR-034.

**Checkpoint 2 — Foundation gate**: registry builds, resolver resolves, IME gate short-circuits, announcer announces, 4 foundational test suites pass. User-story phases may now proceed in parallel.

---

## Phase 3: User Story 1 — Mid-query interrupt (Priority: P1) 🎯 MVP

**Goal**: `ctrl+c` aborts the active agent loop within 500 ms while preserving session + auth state.

**Independent Test**: Per quickstart.md § Step 2. Verify SC-001 (≥ 99% within 500 ms) and audit record presence.

- [ ] T026 [US1] Implement the `agent-interrupt` action handler wiring `ctrl+c` → Spec 027 cancellation envelope + Spec 024 `user-interrupted` audit record. Handler lives in `tui/src/keybindings/actions/agentInterrupt.ts`. Implements double-press arm/fire state machine from data-model.md § State transitions. Depends on T020. Satisfies FR-012, FR-013, SC-001, SC-006.
- [ ] T027 [P] [US1] Add `tui/tests/keybindings/agent-interrupt.test.ts` — loop-abort timing under mocked Spec 027 mailbox; double-press state transitions; audit-record content; screen-reader announcement fires within 1 s (FR-030). Targets T026.

**Checkpoint US1**: `ctrl+c` interrupts cleanly with audit trail. MVP deliverable — demo-ready alone.

---

## Phase 4: User Story 2 — Clean exit (Priority: P1)

**Goal**: `ctrl+d` on empty buffer flushes audit + exits with status 0.

**Independent Test**: Per quickstart.md § Step 5 + Step 9. Verify SC-006 (100% audit presence post-exit).

- [ ] T028 [US2] Implement the `session-exit` action handler in `tui/src/keybindings/actions/sessionExit.ts`. Buffer-empty guard (FR-014), audit flush (FR-015), active-loop confirmation prompt, `process.exit(0)` path. Depends on T020. Satisfies FR-014, FR-015, FR-016, SC-006.
- [ ] T029 [P] [US2] Add `tui/tests/keybindings/session-exit.test.ts` — non-empty-buffer ignore; confirmation on active loop; audit flush completeness (spawn-and-exit harness). Targets T028.

**Checkpoint US2**: citizen can exit cleanly; all audit records recoverable.

---

## Phase 5: User Story 3 — Draft cancel without IME break (Priority: P1)

**Goal**: `escape` clears buffer ONLY when IME idle.

**Independent Test**: Per quickstart.md § Step 3. Verify SC-002 via the IME-composition test suite.

- [ ] T030 [US3] Implement the `draft-cancel` action handler in `tui/src/keybindings/actions/draftCancel.ts`. Clears InputBar buffer on empty-IME state; no-op when composing (resolver-level gate already enforces, but action-level assertion catches regressions). Depends on T014. Satisfies FR-005.
- [ ] T031 [US3] Refactor `tui/src/components/input/InputBar.tsx` — remove its ad-hoc `useInput` escape handler; replace with `useKeybinding('Chat', { 'draft-cancel': ... })` subscription. Pre-existing y/n/enter modal-local handlers stay (FR-004 boundary). Depends on T018, T030. Satisfies FR-004.
- [ ] T032 [US3] Author `tui/tests/keybindings/fixtures/korean-composition-samples.json` — 200 IME-composition samples covering 2350 Hangul syllables plus edge cases (단모음, 이중모음, 복합종성). Seeded from `useKoreanIME.ts` existing tests. Satisfies SC-002.
- [ ] T033 [P] [US3] Add `tui/tests/keybindings/ime-composition.integration.test.ts` — replay all 200 samples against the resolver + draft-cancel handler; assert zero dropped jamo. Targets T030 + T032. Satisfies SC-002.

**Checkpoint US3**: escape never breaks Hangul composition. Largest regression risk from the port is retired.

---

## Phase 6: User Story 4 — Permission-mode cycle (Priority: P1)

**Goal**: `shift+tab` (or `meta+m` fallback) cycles Permission Modes via Spec 033.

**Independent Test**: Per quickstart.md § Step 4. Verify SC-005 (100% block rate on irreversible-action flag).

- [ ] T034 [US4] Implement the `permission-mode-cycle` action handler in `tui/src/keybindings/actions/permissionModeCycle.ts`. Thin adapter over existing `tui/src/permissions/ModeCycle.tsx` (Spec 033). Emits OTel span `kosmos.permission.mode=<new_mode>` on success; emits `ResolutionResult { blocked, reason: 'permission-mode-blocked' }` on irreversible-action block. Screen-reader announcement on success (FR-030). Depends on T020. Satisfies FR-008, FR-009, FR-010, FR-011, SC-005.
- [ ] T035 [P] [US4] Add `tui/tests/keybindings/permission-mode-cycle.test.ts` — wrap order `plan→default→acceptEdits→bypassPermissions→plan`; block on injected irreversible-action flag; 200 ms indicator-update SLO. Targets T034.

**Checkpoint US4**: citizen can cycle Permission Modes without leaving conversation; `bypassPermissions` cannot leak past an irreversible-action flag. All P1 stories now complete.

---

## Phase 7: User Story 5 — History prev/next (Priority: P2)

**Goal**: `up`/`down` navigate the citizen's past queries when the buffer is empty.

**Independent Test**: Per quickstart.md § Step 6 (first half). Verifies FR-017 / FR-018 / FR-019.

- [ ] T036 [US5] Implement `history-prev` + `history-next` action handlers in `tui/src/keybindings/actions/historyNavigate.ts`. Empty-buffer guard (FR-017, FR-018). memdir USER consent-scope visible boundary (FR-019) surfaced through screen-reader announce when crossing from current-session into prior-session entries. Degrades to session-only history when memdir USER tier absent. Depends on T020. Satisfies FR-017, FR-018, FR-019.
- [ ] T036b [P] [US5] Add `tui/tests/keybindings/history-navigate.test.ts` — empty-buffer `up`/`down` loads prior/next query; non-empty-buffer pass-through (draft never overwritten, FR-017/FR-018); memdir USER consent-scope boundary announcement when crossing current↔prior session (FR-019); graceful degradation assertion when memdir USER tier absent. Targets T036.

---

## Phase 8: User Story 6 — History search overlay (Priority: P2)

**Goal**: `ctrl+r` opens a filterable history overlay with 초성 matching.

**Independent Test**: Per quickstart.md § Step 6 (second half). Verifies FR-020..FR-022.

- [ ] T037 [US6] Implement `history-search` action handler in `tui/src/keybindings/actions/historySearch.ts` plus the overlay component `tui/src/components/history/HistorySearchOverlay.tsx`. Overlay reuses Spec 035 `OnboardingShell` modal pattern (D9). Substring + diacritic-insensitive + 초성 matching via existing Spec 022 retrieval tokeniser (no new dep). memdir USER consent scoping + citizen-readable notice when scoped (FR-021). Escape byte-for-byte draft restore (FR-022). Depends on T020. Satisfies FR-020, FR-021, FR-022.
- [ ] T038 [P] [US6] Add `tui/tests/keybindings/history-search.test.ts` covering overlay open ≤ 300 ms, filter correctness on Korean substring + 초성, consent-scope filtering, escape restores draft byte-for-byte. Targets T037.

---

## Phase 9: User Story 7 — Disable/remap via user override (Priority: P2)

**Goal**: citizens satisfy WCAG 2.1.4 by editing `~/.kosmos/keybindings.json`.

**Independent Test**: Per quickstart.md § Steps 7–9. Verifies SC-004.

- [ ] T039 [US7] Author three override fixtures under `tui/tests/keybindings/fixtures/override-files/`: `disable-ctrl-r.json`, `remap-ctrl-r-to-ctrl-f.json`, `invalid-shape.json`. Plus `tui/tests/keybindings/loadUserBindings.test.ts` — asserts FR-023..FR-028 round-trip including reserved-action reject + silent degrade. Targets T010. Satisfies SC-004.

---

## Phase 10: Polish & Cross-Cutting

**Purpose**: accessibility audit, catalogue discovery surface, docs cross-refs.

- [ ] T040 Add a catalogue-dump helper `tui/src/keybindings/template.ts` (port of CC `template.ts`) + KOSMOS help-surface menu entry rendering the active Tier 1 catalogue. Must be reachable by screen-reader users within 30 s of TUI launch (SC-007). Satisfies FR-032, SC-007. Plus: `tui/tests/keybindings/accessibility.test.ts` that asserts every Tier 1 action emits an announcer event within 1 s of dispatch (FR-030), the catalogue is reachable via a non-chord path (menu), and an ADR-006 cross-reference note is appended to `docs/adr/ADR-006-cc-migration-vision-update.md` (§ "A-10 implementation landed in Spec 288" plus link to this tasks.md).

---

## Dependencies & Execution Order

### Phase dependencies

- **Phase 1 (Setup)**: no deps; can start immediately.
- **Phase 2 (Foundational)**: depends on Phase 1. Blocks all user-story phases.
- **Phase 3–9 (User Stories)**: each depends on Phase 2 Checkpoint. Among themselves, US1 is MVP; US2/US3/US4 (P1) run in parallel with US1 post-foundation; US5/US6/US7 (P2) run in parallel post-P1.
- **Phase 10 (Polish)**: depends on US1..US7.

### Within-phase parallel opportunities

- Phase 1: T002, T003 parallel after T001.
- Phase 2: T004, T005, T006, T007 parallel (`[P]`); T008 after T007; T009 after T004/T007/T008; T010 after T008; T011 after T004/T008; T012 after T009/T010/T011; T013 after T012; T014 after T013; T014b after T014; T015 independent; T016/T017/T018/T019 parallel after T012+T015; T020 after T014b+T017; T021 after T017; tests T022/T023/T024/T025 parallel once their target task lands.
- Phase 3–9: within-story tasks are small and mostly sequential, but **the phases themselves** run in parallel across the three Agent Teams per the Agent Team Dispatch section below.

### Cross-story concerns

- All stories consume the same registry/resolver from Phase 2 — no cross-story edits except InputBar (T031, US3 only) which does not touch code paths owned by other stories.
- Spec 024 audit writer and Spec 027 cancellation mailbox are treated as stable upstream contracts — no task here modifies them.

---

## Agent Team Dispatch (for `/speckit-implement`)

Once Phase 2 checkpoint passes, three Sonnet teammates can run in parallel:

### Team A — Frontend Developer (Sonnet)

Phases 3 + 5 + 7 (InputBar + IME + history prev/next). Owns `tui/src/components/input/InputBar.tsx` and all keybinding action handlers that mutate the Chat buffer. Tasks: T026, T030, T031, T032, T033, T036, T036b.

### Team B — Backend Architect (Sonnet)

Phases 4 + 6 (session exit + permission-mode cycle). Owns integration with Spec 024 audit writer and Spec 033 `ModeCycle`. Tasks: T028, T029, T034, T035.

### Team C — Frontend Developer + Accessibility Auditor (Sonnet)

Phases 8 + 9 + 10 (history overlay + user override + accessibility polish + ADR cross-ref). Owns the overlay component and the accessibility audit. Tasks: T037, T038, T039, T040.

Foundational Phase 2 (T004..T025) is executed by the Lead (Opus) solo because it is the shared substrate all three teammates depend on — avoids merge-conflict churn on a 14-file port.

---

## Parallel Example: Phase 2 kickoff

```bash
# After T001 lands, launch parser + match + format + schema ports together
Task T004: "Port parser.ts"
Task T005: "Port match.ts"
Task T006: "Port shortcutFormat.ts"
Task T007: "Port schema.ts (narrowed to 4 contexts)"

# After T007 lands, launch reserved + defaults + loader + validate in order they unblock
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 + Phase 2 complete → foundation gate passes.
2. Team A executes T026 + T027 (ctrl+c interrupt).
3. STOP + VALIDATE: quickstart.md § Step 2 passes on xterm and Windows Terminal.
4. Demo: citizen interrupts a query without losing the session.

### Incremental delivery after MVP

US2 → US3 → US4 in parallel (all P1); each independently demo-able. Then US5–US7 (P2) in parallel. Phase 10 polish last.

### Parallel team strategy (recommended given 3+ independent tasks post-foundation)

See § Agent Team Dispatch above. Three teammates + Lead coordinating. Expected calendar-time compression: 40 tasks in ~9 parallel task-days (vs. ~25 sequential task-days).

---

## Notes

- Task count: 42 (well under 90-Task budget).
- `[P]` count: 17 of 42 (≈ 40% parallel-safe).
- Tests-before-impl (TDD) strict for SC-bearing stories (SC-001..SC-006). Tests for SC-007 (discoverability under screen reader) are in T040 and are manual/audit-driven, not automated.
- `[Deferred]`-prefixed rows: none in this tasks.md. All deferrals live in spec.md § Deferred table.
- Commit after each checkpoint; never batch a full phase into one commit.
- Verify each test fails before paired implementation lands (TDD discipline).
