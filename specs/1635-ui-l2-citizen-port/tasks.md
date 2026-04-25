# Tasks: P4 · UI L2 Citizen Port

**Input**: Design documents from `/specs/1635-ui-l2-citizen-port/`
**Prerequisites**: spec.md (38 FRs across 5 user stories), plan.md (TS 5.6+ on Bun, two new TS deps), research.md (per-FR CC reference mapping), data-model.md (7 Zod entities), contracts/ (slash-commands + keybindings + memdir-paths), quickstart.md (13-step golden path)

**Tests**: Unit tests are included per story since the spec.md success criteria are verifiable only via behavioral assertions on TUI components. The final phase runs the integrated test suite plus a manual quickstart walk-through.

**Organization**: Tasks are grouped by user story (US1 REPL P1 MVP / US2 Permission P1 / US3 Onboarding P2 / US4 Agents P2 / US5 Auxiliary P3) so each story can be implemented and tested independently per spec.md priority ordering.

**Format**: `[ID] [P?] [Story?] Description with file path`
- **[P]**: Different files, no shared-file conflict — eligible to run in parallel.
- **[Story]**: US1..US5 traceability label (set only on user-story phase tasks).

**Path conventions** match plan.md project structure tree. Backend Python is unchanged.

**Reference shorthand**: `cc:<path>` denotes `.references/claude-code-sourcemap/restored-src/src/<path>`.

**Budget**: 80 tasks total — within the 90-task per-Epic cap (`feedback_subissue_100_cap`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the two TS-only dependencies authorised in the Epic body and scaffold the new directory tree.

- [x] T001 Add `pdf-to-img` (Apache-2.0, FR-010) and `pdf-lib` (MIT, FR-032) to `tui/package.json` dependencies and run `bun install` from `tui/`
- [x] T002 Scaffold the new directory tree under `tui/src/`: `schemas/ui-l2/`, `observability/`, `components/{onboarding,messages,permissions,agents,help,config,plugins,export,history}/`, `context/`, plus `tui/tests/components/{onboarding,messages,permissions,agents,help,config,plugins,export,history}/` and `tui/tests/commands/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Schemas, helpers, catalog, keybindings, and i18n keys that every user-story phase consumes.

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [x] T003 [P] Define `OnboardingState` (data-model §1, FR-001/002) and `AccessibilityPreference` (data-model §5, FR-005) Zod schemas in `tui/src/schemas/ui-l2/onboarding.ts` and `tui/src/schemas/ui-l2/a11y.ts`
- [x] T004 [P] Define `PermissionReceipt` Zod schema in `tui/src/schemas/ui-l2/permission.ts` (data-model §2, FR-018) — include `PermissionLayer`, `PermissionDecision` enums + `rcpt-<id>` regex
- [x] T005 [P] Define `AgentVisibilityEntry` Zod schema and `shouldActivateSwarm` predicate in `tui/src/schemas/ui-l2/agent.ts` (data-model §3, FR-025/027) — A+C union semantics
- [x] T006 [P] Define `SlashCommandCatalogEntry` Zod schema in `tui/src/schemas/ui-l2/slash-command.ts` (data-model §4, FR-014/029) matching `contracts/slash-commands.schema.json`
- [x] T007 [P] Define `ErrorEnvelope` and `UfoMascotPose` Zod schemas in `tui/src/schemas/ui-l2/error.ts` and `tui/src/schemas/ui-l2/ufo.ts` (data-model §6/7, FR-012/035)
- [x] T008 [P] Memdir read/write helper with atomic-rename and version-tag fallback in `tui/src/utils/memdir.ts` for `~/.kosmos/memdir/user/onboarding/state.json` and `~/.kosmos/memdir/user/preferences/a11y.json` (memdir-paths.md, FR-002/005)
- [x] T009 [P] OTEL `kosmos.ui.surface` attribute emitter in `tui/src/observability/surface.ts` wrapping the existing Spec 021 emit path (FR-037, no new collector route per FR-038)
- [x] T010 Slash command catalog SSOT in `tui/src/commands/catalog.ts` seeded with all 12 commands from data-model §4 (FR-014/029) — depends on T006
- [x] T011 Keybinding additions in `tui/src/keybindings/defaultBindings.ts` for Ctrl-O / Shift+Tab / `/` / Y/A/N / Space/i/r/a (FR-009/014/017/022/031) matching `contracts/keybindings.schema.json` — IME safety check (`!useKoreanIME().isComposing`) on every input-mutating binding per `vision.md § Keyboard-shortcut migration`
- [x] T012 [P] Korean i18n keys for onboarding / error / a11y / help / config / plugins / export / history in `tui/src/i18n/ko.ts` (FR-004 primary)
- [x] T013 [P] English fallback i18n keys mirroring T012 in `tui/src/i18n/en.ts` (FR-004 fallback)

**Checkpoint**: Schemas, catalog, keybindings, i18n, memdir, and OTEL helpers are in place. User-story phases may now proceed in parallel.

---

## Phase 3: User Story 1 — REPL Main (Priority: P1) 🎯 MVP

**Goal**: Citizen runs an administrative query through the REPL with chunk streaming, expand/collapse, inline PDF, markdown tables, error envelopes, quote blocks, and slash-command autocomplete.

**Independent Test**: `bun run tui` → enter a Korean administrative query → observe ~20-token chunk streaming, `Ctrl-O` expand, PDF inline (Kitty/iTerm2) or `open` fallback, table parity with CC, three differentiated error envelopes, ⎿ quote box, `/` autocomplete dropdown — non-developer observer scoring per spec.md acceptance scenarios 1–7.

### Implementation for User Story 1

- [x] T014 [P] [US1] `StreamingChunk` component with ~20-token chunk batching and `KOSMOS_TUI_STREAM_CHUNK_TOKENS` env override (default 20) in `tui/src/components/messages/StreamingChunk.tsx` (FR-008, ref `cc:components/Messages.tsx`, `cc:components/Message.tsx`, `cc:components/VirtualMessageList.tsx`)
- [x] T015 [P] [US1] Port `CtrlOToExpand` to `tui/src/components/PromptInput/CtrlOToExpand.tsx` with collapsed/expanded toggle (FR-009, ref `cc:components/CtrlOToExpand.tsx`)
- [x] T016 [P] [US1] `PdfInlineViewer` with Kitty/iTerm2 graphics protocol detection and `pdf-to-img` first-page PNG render in `tui/src/components/messages/PdfInlineViewer.tsx`; fallback to OS `open`; final fallback to text-only (path + size + sha256) for headless terminals (FR-010 + edge case)
- [x] T017 [P] [US1] Port `MarkdownRenderer` (block-level inline preview) to `tui/src/components/messages/MarkdownRenderer.tsx` (FR-011 partial, ref `cc:components/Markdown.tsx`)
- [x] T018 [P] [US1] 1:1 port of `MarkdownTable` to `tui/src/components/messages/MarkdownTable.tsx` (FR-011, ref `cc:components/MarkdownTable.tsx`)
- [x] T019 [P] [US1] `ErrorEnvelope` with three differentiated styles (LLM purple+brain / Tool orange+wrench / Network red+signal-broken) in `tui/src/components/messages/ErrorEnvelope.tsx` (FR-012, ref `cc:components/FallbackToolUseErrorMessage.tsx`)
- [x] T020 [P] [US1] `ContextQuoteBlock` with `⎿` prefix and single-border box in `tui/src/components/messages/ContextQuoteBlock.tsx` (FR-013, ref `cc:components/Message.tsx` quote glyph)
- [x] T021 [P] [US1] Extend `PromptInputFooterSuggestions` with highlighted match + inline preview dropdown driven by the slash-command catalog in `tui/src/components/PromptInput/SlashCommandSuggestions.tsx` (FR-014, depends on T010)
- [x] T022 [US1] Wire all UI-B components into `tui/src/screens/REPL.tsx` and emit `kosmos.ui.surface=repl` on render (FR-037, depends on T014–T021, T009)
- [x] T023 [US1] Network 5-second no-chunk transition handler — switch to `ErrorEnvelope` type=`network` with retry option in `tui/src/screens/REPL.tsx` (edge case "streaming network drop")
- [x] T024 [P] [US1] `bun:test` units in `tui/tests/components/messages/` covering `StreamingChunk`, `PdfInlineViewer`, `ErrorEnvelope`, `ContextQuoteBlock`, `MarkdownTable`, `MarkdownRenderer` (FR-008/010/011/012/013)
- [x] T025 [P] [US1] `bun:test` units in `tui/tests/components/PromptInput/` for `CtrlOToExpand` and `SlashCommandSuggestions` (FR-009/014, SC-005 100ms-after-`/` budget)
- [x] T026 [US1] OTEL surface attribute on every UI-B component activation (FR-037) — covered by T022 wiring + helper from T009

**Checkpoint**: REPL Main is fully functional and testable independently.

---

## Phase 4: User Story 2 — Permission Gauntlet (Priority: P1)

**Goal**: Layer 1/2/3 permission modal with green/orange/red color coding, `[Y/A/N]` decisions, receipt ID surfacing, `/consent list`, `/consent revoke` (idempotent), Shift+Tab mode switch with `bypassPermissions` reinforcement, Ctrl-C and 5-min timeout fail-closed handlers.

**Independent Test**: Trigger Layer 1/2/3 tool calls → confirm color/glyph layering → exercise Y/A/N decision → verify `rcpt-<id>` toast and ledger entry → `/consent list` and `/consent revoke` (twice for idempotency) → Shift+Tab through modes and confirm `bypassPermissions` reinforcement modal — per spec.md acceptance scenarios 1–7.

### Implementation for User Story 2

- [ ] T027 [P] [US2] `PermissionLayerHeader` with `green ⓵ / orange ⓶ / red ⓷` color tokens in `tui/src/components/permissions/PermissionLayerHeader.tsx` (FR-016)
- [ ] T028 [P] [US2] `PermissionGauntletModal` with `[Y/A/N]` 3-choice and Layer 3 reinforcement notice line in `tui/src/components/permissions/PermissionGauntletModal.tsx` (FR-015/017, ref `cc:components/permissions/PermissionDialog.tsx`, `cc:components/permissions/PermissionRequestTitle.tsx`, `cc:components/permissions/PermissionExplanation.tsx`)
- [ ] T029 [P] [US2] `ReceiptToast` displaying `rcpt-<id>` after every decision in `tui/src/components/permissions/ReceiptToast.tsx` (FR-018, ref `cc:context/notifications.tsx`)
- [ ] T030 [P] [US2] Port `BypassReinforcementModal` to `tui/src/components/permissions/BypassReinforcementModal.tsx` (FR-022, ref `cc:components/BypassPermissionsModeDialog.tsx`)
- [ ] T031 [US2] `PermissionReceiptContext` provider managing in-session receipts and revoke surface in `tui/src/context/PermissionReceiptContext.tsx` (FR-018/019, ref `cc:context/notifications.tsx`)
- [ ] T032 [P] [US2] `/consent list` subcommand printing receipts in reverse chronological order with table layout in `tui/src/commands/consent.ts` (FR-019, ref `cc:components/HistorySearchDialog.tsx`)
- [ ] T033 [US2] `/consent revoke <rcpt-id>` subcommand with confirmation modal and idempotent semantics in `tui/src/commands/consent.ts` — toast "이미 철회됨" when already revoked (FR-020/021, depends on T032)
- [ ] T034 [US2] Ctrl-C handler in `PermissionGauntletModal.tsx` — auto-deny with `auto_denied_at_cancel` decision (FR-023, depends on T028)
- [ ] T035 [US2] 5-minute idle handler in `PermissionGauntletModal.tsx` — auto-deny with `timeout_denied` decision and Layer 3 specific application (FR-024, depends on T028)
- [x] T036 [US2] Wire Shift+Tab mode cycle to `BypassReinforcementModal` in `tui/src/screens/REPL.tsx` (FR-022, depends on T030, T011)
- [ ] T037 [P] [US2] `bun:test` units in `tui/tests/components/permissions/` for layer header, modal, toast, bypass-reinforcement (FR-015/016/017/018/022)
- [ ] T038 [P] [US2] `bun:test` units in `tui/tests/commands/consent.test.ts` covering list output ordering and revoke idempotency (FR-019/020/021)
- [x] T039 [US2] Emit `kosmos.ui.surface=permission_gauntlet` on every modal show via T009 helper (FR-037)

**Checkpoint**: Permission Gauntlet works end-to-end. Combined with US1, the REPL is safe for any tool call up to Layer 3.

---

## Phase 5: User Story 3 — Onboarding 5-step (Priority: P2)

**Goal**: First-launch onboarding sequence (`preflight → theme → pipa-consent → ministry-scope → terminal-setup`) with `/onboarding [step]` re-entry, Korean primary + English fallback, four accessibility toggles persisted, audit-preserving consent revocation.

**Independent Test**: Wipe `~/.kosmos/memdir/user/onboarding` and `~/.kosmos/memdir/user/preferences` → `bun run tui` → walk through five steps in order → restart mid-flow and verify resume from last completed step → `/onboarding ministry-scope` reruns step 4 only → toggle `large_font` and verify ≤ 500 ms re-render — per spec.md acceptance scenarios 1–7.

### Implementation for User Story 3

- [ ] T040 [P] [US3] `PreflightStep` with Bun version / graphics-protocol / `KOSMOS_*` env-var ✓-✗ checks in `tui/src/components/onboarding/PreflightStep.tsx` (FR-001 step 1)
- [ ] T041 [P] [US3] `ThemeStep` with UFO mascot idle pose preview using purple palette `#a78bfa` over `#4c1d95` in `tui/src/components/onboarding/ThemeStep.tsx` (FR-001 step 2, FR-035)
- [ ] T042 [P] [US3] `PipaConsentStep` with PIPA §26 trustee notice (visual + textual) in `tui/src/components/onboarding/PipaConsentStep.tsx` (FR-001 step 3, FR-006, ref `cc:components/Onboarding.tsx`)
- [ ] T043 [P] [US3] `MinistryScopeStep` with Spec 035 memdir helper write-through in `tui/src/components/onboarding/MinistryScopeStep.tsx` (FR-001 step 4)
- [ ] T044 [P] [US3] `TerminalSetupStep` with four accessibility toggles + Shift+Tab keybinding hint in `tui/src/components/onboarding/TerminalSetupStep.tsx` (FR-001 step 5, FR-005)
- [ ] T045 [US3] `OnboardingFlow` step driver with persisted `current_step_index` in `tui/src/components/onboarding/OnboardingFlow.tsx` (FR-001/002, depends on T040–T044, ref `cc:components/Onboarding.tsx`)
- [ ] T046 [US3] `/onboarding` command with optional `<step-name>` positional arg in `tui/src/commands/onboarding.ts` (FR-003, depends on T045)
- [ ] T047 [P] [US3] `/lang ko|en` command in `tui/src/commands/lang.ts` flipping the i18n binding at runtime (FR-004)
- [ ] T048 [US3] Wire accessibility toggle persistence in `TerminalSetupStep.tsx` to T008 memdir helper writing `~/.kosmos/memdir/user/preferences/a11y.json` (FR-005, depends on T044, T008)
- [x] T049 [US3] Onboarding entry gate at startup in `tui/src/main.tsx` — skip when `current_step_index === 5`, resume when `< 5`, replay full sequence on `/onboarding` (FR-001 acceptance §1, depends on T045)
- [ ] T050 [P] [US3] `bun:test` units in `tui/tests/components/onboarding/` covering all five step components and the flow driver (FR-001..006)
- [ ] T051 [P] [US3] `bun:test` units in `tui/tests/commands/{onboarding,lang}.test.ts` (FR-003/004)
- [x] T052 [US3] Emit `kosmos.ui.surface=onboarding` on each step render via T009 helper (FR-037)

**Checkpoint**: First-launch onboarding works. Combined with US1+US2, citizens have a complete entry, query, and consent loop.

---

## Phase 6: User Story 4 — Ministry Agent visibility (Priority: P2)

**Goal**: Five-state agent panel (proposal-iv) with `/agents` and `/agents --detail` (SLA + health + rolling-avg response), automatic swarm activation when 3+ ministries are mentioned OR LLM tags the plan as "complex".

**Independent Test**: Issue a single-ministry query → verify swarm stays inactive; issue a 3-ministry query → verify swarm activates and `/agents` shows multi-row panel; `/agents --detail` adds SLA / health / avg-response columns; live state transitions update without re-invocation — per spec.md acceptance scenarios 1–5.

### Implementation for User Story 4

- [ ] T053 [P] [US4] `AgentVisibilityPanel` rendering proposal-iv 5-state per ministry in `tui/src/components/agents/AgentVisibilityPanel.tsx` (FR-025/028, ref `cc:components/agents/AgentsList.tsx`, `docs/wireframes/proposal-iv.mjs`)
- [ ] T054 [P] [US4] `AgentDetailRow` with SLA-remaining / health (green/amber/red) / rolling-avg response in `tui/src/components/agents/AgentDetailRow.tsx` (FR-026, ref `cc:components/CoordinatorAgentStatus.tsx`)
- [ ] T055 [US4] `/agents` command supporting `--detail` flag in `tui/src/commands/agents.ts` (FR-026, depends on T053, T054)
- [x] T056 [US4] Wire `shouldActivateSwarm` predicate (T005) into the REPL plan handler in `tui/src/screens/REPL.tsx` (FR-027 A+C union)
- [ ] T057 [US4] Subscribe `AgentVisibilityPanel` to Spec 027 mailbox event channel for live state transitions in `tui/src/components/agents/AgentVisibilityPanel.tsx` — push, no polling (FR-028, SC-007 ≤500 ms p95)
- [ ] T058 [P] [US4] `bun:test` units in `tui/tests/components/agents/` and `tui/tests/commands/agents.test.ts` including swarm-predicate boundary cases (FR-025/026/027/028)
- [x] T059 [US4] Emit `kosmos.ui.surface=agents` on panel render via T009 helper (FR-037)

**Checkpoint**: Citizens can see who is doing what in real time. With US1+US2+US3+US4 the platform is ready for daily citizen use.

---

## Phase 7: User Story 5 — Auxiliary surfaces (Priority: P3)

**Goal**: Help (4-group), Config (overlay + `.env` isolated editor), Plugins browser (⏺/○ + Space/i/r/a), Export PDF (transcript + tools + receipts), History search (3 filters).

**Independent Test**: `/help` shows 4 groups → `/config` overlay edits non-secret inline and isolates `.env` → `/plugins` keybindings 5-way → `/export` produces PDF with tool-call transcript and receipts but no OTEL/plugin internals → `/history` filters compose with AND semantics — per spec.md acceptance scenarios 1–5.

### Implementation for User Story 5

- [ ] T060 [P] [US5] Port `HelpV2Grouped` rendering 4 groups (Session / Permission / Tool / Storage) in `tui/src/components/help/HelpV2Grouped.tsx` (FR-029, ref `cc:components/HelpV2/HelpV2.tsx`, `cc:components/HelpV2/Commands.tsx`, `cc:components/HelpV2/General.tsx`)
- [ ] T061 [US5] `/help` command emitting 4-group output sourced from catalog in `tui/src/commands/help.ts` (FR-029, depends on T060, T010)
- [ ] T062 [P] [US5] `ConfigOverlay` with inline edit for non-secret settings in `tui/src/components/config/ConfigOverlay.tsx` (FR-030, ref `cc:components/InvalidConfigDialog.tsx`)
- [ ] T063 [P] [US5] `EnvSecretIsolatedEditor` for `.env` secret-edit isolation in `tui/src/components/config/EnvSecretIsolatedEditor.tsx` (FR-030 isolation rule)
- [ ] T064 [US5] `/config` command opening overlay + isolated editor branch in `tui/src/commands/config.ts` (FR-030, depends on T062, T063)
- [ ] T065 [P] [US5] `PluginBrowser` with `⏺`/`○` toggles and Space/i/r/a keybindings in `tui/src/components/plugins/PluginBrowser.tsx` (FR-031, ref `cc:components/CustomSelect/`)
- [ ] T066 [US5] `/plugins` command opening browser in `tui/src/commands/plugins.ts` (FR-031, depends on T065)
- [ ] T067 [P] [US5] `ExportPdfDialog` assembling transcript + tool-call records + receipts with `pdf-lib`, excluding OTEL span IDs and plugin-internal markers in `tui/src/components/export/ExportPdfDialog.tsx` (FR-032, ref `cc:components/ExportDialog.tsx`)
- [ ] T068 [US5] `/export` command writing PDF to platform-default download location in `tui/src/commands/export.ts` (FR-032, depends on T067)
- [ ] T069 [P] [US5] Port `HistorySearchDialog` with 3-filter form (`--date FROM..TO`, `--session <id>`, `--layer <n>`) in `tui/src/components/history/HistorySearchDialog.tsx` (FR-033, ref `cc:components/HistorySearchDialog.tsx`)
- [ ] T070 [US5] `/history` command supporting all three filters with AND composition in `tui/src/commands/history.ts` (FR-033, depends on T069)
- [ ] T071 [P] [US5] `bun:test` units in `tui/tests/components/{help,config,plugins,export,history}/` and `tui/tests/commands/{help,config,plugins,export,history}.test.ts` (FR-029..033, SC-012 zero-OTEL-leak assertion in export tests)
- [x] T072 [US5] Emit `kosmos.ui.surface={help,config,plugins,export,history}` per surface activation via T009 helper (FR-037)

**Checkpoint**: All five user stories independently functional.

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Integrated test sweep, manual quickstart smoke, fidelity scoring, success-criteria verification, doc updates, integrated PR.

- [ ] T073 [P] Run the full `bun test` suite from `tui/` and confirm all units green
- [ ] T074 Walk through `quickstart.md` steps 1–13 manually with a fresh `~/.kosmos` and capture observations in `specs/1635-ui-l2-citizen-port/quickstart-walkthrough.md`
- [ ] T075 Score CC 2.1.88 visual + structural fidelity across the 9 surfaces (REPL, onboarding ×5 steps, permission modal, agents panel, help, config, plugins, export, history) and write `docs/visual-fidelity/1635-scoring.md` (FR-034, SC-009 ≥ 90 %)
- [ ] T076 Verify zero new external network egress with `lsof -p $(pgrep -f 'bun.*tui')` during a representative session and append findings to `docs/visual-fidelity/1635-scoring.md` (FR-038, SC-008)
- [ ] T077 Verify `/export` PDF excludes OTEL span IDs and plugin-internal markers via `grep -E 'traceId=|spanId=|pluginInternal:'` over 20 sample export PDFs and append findings to the scoring doc (FR-032, SC-012)
- [ ] T078 [P] Update `tui/README.md` documenting new commands, keybindings, and the two new TS dependencies (`pdf-to-img`, `pdf-lib`)
- [ ] T079 [P] Update `CLAUDE.md` Active Technologies section if any new spec-driven path emerges from T073–T077 (re-run `update-agent-context.sh claude` if needed)
- [ ] T080 Open the integrated PR with `Closes #1635` only — no Task sub-issue references in the PR body — per `feedback_integrated_pr_only` and `feedback_pr_closing_refs`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no dependencies; T001 + T002 can run sequentially or in parallel.
- **Phase 2 Foundational**: depends on Phase 1. Within Phase 2, T003–T009 run in parallel; T010 depends on T006; T011 depends on T002 + the keybindings contract; T012 + T013 run in parallel after T002.
- **Phase 3 (US1)** + **Phase 4 (US2)** + **Phase 5 (US3)** + **Phase 6 (US4)** + **Phase 7 (US5)**: all depend on Phase 2; with parallel staffing, US1 + US2 + US3 + US4 + US5 can proceed concurrently because each story owns its own `tui/src/components/<surface>/` subtree.
- **Phase 8 Polish**: depends on every desired user-story phase completing.

### User Story Dependencies

- **US1 REPL P1 (MVP)**: depends only on Phase 2.
- **US2 Permission P1**: depends only on Phase 2; integrates with US1 REPL via Shift+Tab modal mounting (T036 touches `REPL.tsx` so it must follow T022).
- **US3 Onboarding P2**: depends only on Phase 2; `main.tsx` entry gate (T049) is independent of US1 mounting.
- **US4 Agents P2**: depends only on Phase 2; T056 wires swarm activation into `REPL.tsx` so it follows T022.
- **US5 Auxiliary P3**: depends only on Phase 2; commands are registered through the catalog SSOT.

### Within each user story

- Models / schemas (Phase 2) → components → commands → screen wiring → unit tests → OTEL surface emission.
- All `[P]` tasks within a phase touch distinct files and may run concurrently.

### Parallel opportunities

- All Phase 2 schemas (T003–T007), helpers (T008–T009), and i18n (T012–T013) run in parallel.
- Within US1: T014–T021 run in parallel; T022 then sequences the wiring.
- Within US2: T027–T030 + T032 run in parallel; T031 / T033 / T034 / T035 / T036 sequence after their dependents.
- Within US3: T040–T044 + T047 run in parallel; T045 / T048 / T049 sequence after.
- Within US4: T053 + T054 + T058 run in parallel; T055 / T056 / T057 sequence after.
- Within US5: T060 + T062 + T063 + T065 + T067 + T069 + T071 run in parallel; T061 / T064 / T066 / T068 / T070 sequence after.
- Phase 8 polish: T073 + T078 + T079 run in parallel; T074 → T075 → T076 → T077 sequence (each consumes the prior session evidence); T080 last.

---

## Parallel Example: User Story 1 (MVP)

```bash
# After Foundational completes, launch all UI-B leaf components together:
Task: "[US1] Create StreamingChunk in tui/src/components/messages/StreamingChunk.tsx"
Task: "[US1] Port CtrlOToExpand in tui/src/components/PromptInput/CtrlOToExpand.tsx"
Task: "[US1] Create PdfInlineViewer in tui/src/components/messages/PdfInlineViewer.tsx"
Task: "[US1] Port MarkdownRenderer in tui/src/components/messages/MarkdownRenderer.tsx"
Task: "[US1] 1:1 port MarkdownTable in tui/src/components/messages/MarkdownTable.tsx"
Task: "[US1] Create ErrorEnvelope in tui/src/components/messages/ErrorEnvelope.tsx"
Task: "[US1] Create ContextQuoteBlock in tui/src/components/messages/ContextQuoteBlock.tsx"
Task: "[US1] Extend PromptInputFooterSuggestions in tui/src/components/PromptInput/PromptInputFooterSuggestions.tsx"

# Then sequentially wire into REPL.tsx and add the network-drop edge case.
```

---

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 Setup → Phase 2 Foundational → Phase 3 US1.
2. STOP and validate REPL Main against spec.md acceptance scenarios 1–7.
3. Demo as P4-MVP if needed, but do not merge — integrated PR rule means MVP demo happens on the feature branch, not a separate PR.

### Incremental delivery (cohesive but staged)

1. Setup + Foundational → cement schemas, catalog, keybindings, i18n.
2. US1 REPL → MVP demo in branch.
3. US2 Permission → adds safety surface; demo again.
4. US3 Onboarding + US4 Agents (parallelisable on a staffed team).
5. US5 Auxiliary (last because lowest priority and largest surface count).
6. Phase 8 polish, then integrated PR.

### Parallel team strategy

With multiple Sonnet Teammates:

1. Lead (Opus) completes Phase 1 + Phase 2 alone or with one Teammate.
2. Once Phase 2 done:
   - Teammate A → US1 REPL (T014–T026)
   - Teammate B → US2 Permission (T027–T039)
   - Teammate C → US3 Onboarding (T040–T052)
   - Teammate D → US4 Agents (T053–T059)
   - Teammate E → US5 Auxiliary (T060–T072)
3. Lead reviews each Teammate's branch-local commits, integrates into the single feature branch, then runs Phase 8 alone.
4. One PR closes #1635.

---

## Notes

- `[P]` tasks touch different files and have no incomplete dependencies; same-file modifications are sequenced explicitly.
- `[US1]..[US5]` labels trace each task to spec.md user stories for review and coverage analysis.
- Tests use `bun:test` (existing TUI stack); no Python tests added.
- Every commit follows Conventional Commits per AGENTS.md; `Closes #1635` appears only on the final integrated PR (T080), never on intermediate commits.
- `feedback_subissue_100_cap`: 80-task budget leaves 10 sub-issue slots for `[Deferred]` placeholders + mid-cycle additions before the GitHub Sub-Issues 100 cap is reached.
- `feedback_no_hardcoding`: every detection (graphics protocol, PDF size threshold, swarm activation) reads runtime signals; no hardcoded keyword tokenisers.
- `feedback_check_references_first`: every component task names a CC restored-src reference path where applicable.
