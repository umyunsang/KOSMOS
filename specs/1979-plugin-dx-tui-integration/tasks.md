---
description: "Task list for Epic #1979 — Plugin DX TUI integration"
---

# Tasks: Plugin DX TUI integration (Spec 1636 closure)

**Input**: Design documents from `/specs/1979-plugin-dx-tui-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md (all complete)

**Tests**: Tests are included per Constitution §III + §IV mandate (Pydantic v2 invariants + happy-path/error-path discipline) and per the spec's SC-005 baseline-parity invariant.

**Organization**: Tasks grouped by user story so each can be implemented + tested + delivered as an MVP increment.

## Format: `[ID] [P?] [Story] Description with file path`

- **[P]**: Different files, no dependency on incomplete tasks → can run in parallel
- **[Story]**: US1 / US2 / US3 / US4 mapping to spec.md user stories (Setup / Foundational / Polish phases have no Story label)
- All paths are absolute under `/Users/um-yunsang/KOSMOS/`

## Path Conventions

- **Backend**: `src/kosmos/` (Python 3.12+) + `tests/` at repository root
- **TUI**: `tui/src/` (TypeScript 5.6+ on Bun v1.2.x)
- **Spec artifacts**: `specs/1979-plugin-dx-tui-integration/` + `specs/1979-plugin-dx-tui-integration/scripts/`

---

## Phase 1: Setup (Shared baseline + diagnostics)

**Purpose**: Establish the PTY-driven baseline that all subsequent verification stages compare against. Memory `feedback_runtime_verification` mandates a PTY capture before claiming any TUI fix.

- [X] T001 [P] Capture today's broken `/plugin install` UX as a text-log + JSONL artifact pair using the existing 4-layer ladder (`expect` + `script` + raw stdio probe). Output: `specs/1979-plugin-dx-tui-integration/notes-baseline.txt` + `notes-baseline.jsonl`. Reference: docs/testing.md § TUI verification methodology, memory `feedback_runtime_verification`.
- [X] T002 [P] Document the gap analysis in `specs/1979-plugin-dx-tui-integration/notes-baseline.md`: (a) `tui/src/commands.ts:133` mis-routing to CC `commands/plugin/index.tsx`, (b) `plugin_op` IPC frame emit count = 0 (verified via `grep -rn "plugin_op" src/ tui/src/`), (c) orphaned `tui/src/commands/plugin.ts` (singular). Reference: research.md § V1.

**Checkpoint**: Baseline diagnostic artifacts captured under `specs/1979-plugin-dx-tui-integration/`. Backend + TUI are confirmed broken on the citizen install path.

---

## Phase 2: Foundational (Blocking prerequisites for all user stories)

**Purpose**: Backend infrastructure (dispatcher arm + ToolRegistry methods + IPCConsentBridge module) that ALL user stories depend on. None of US1–US4 can be acceptance-tested until this phase completes.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T003 Add `frame.kind == "plugin_op"` arm to `src/kosmos/ipc/stdio.py` if-elif dispatch chain at line ~1675 (after `session_event`). Wrap handler call in try/except → ErrorFrame fanout matching the existing `chat_request` / `tool_result` / `permission_response` arms. Reference: contracts/dispatcher-routing.md § Dispatch logic.
- [X] T004 [P] Create `src/kosmos/ipc/plugin_op_dispatcher.py` (NEW) with `handle_plugin_op_request(frame, *, registry, executor, write_frame, consent_bridge, session_id)` entry point + `handle_install` / `handle_uninstall` / `handle_list` private routers. Reference: data-model.md § E1 + contracts/dispatcher-routing.md.
- [X] T005 [P] Extend `src/kosmos/tools/registry.py:ToolRegistry` with `_inactive: set[str]` field + `set_active(tool_id, active: bool)` + `is_active(tool_id) -> bool` methods + `deregister(tool_id)` method. Filter `_inactive` from `core_tools` / `all_tools` / `to_openai_tool` / BM25 corpus rebuild. Reference: data-model.md § E4.
- [X] T006 [P] Create `src/kosmos/plugins/consent_bridge.py` (NEW) with `IPCConsentBridge` class — sync `__call__(entry, version, manifest) -> bool` matching `installer.ConsentPrompt` signature; emits `PermissionRequestFrame` + awaits `_pending_perms[request_id]` future via `asyncio.wait_for(timeout=60.0)`; returns `False` on TimeoutError (fail-closed). Reference: data-model.md § E2 + contracts/consent-bridge.md.

**Checkpoint**: Backend dispatcher arm exists, dispatcher module skeleton compiles, registry has lifecycle methods, consent bridge ready for injection. User story phases can now proceed.

---

## Phase 3: User Story 1 — Citizen completes plugin install end-to-end (Priority: P1) 🎯 MVP

**Goal**: Close the install loop so a citizen typing `/plugin install seoul-subway` (against fixture catalog) sees the 7-phase progress overlay + consent modal + receipt within 30 s. Backend + IPC + consent bridge all functional.

**Independent Test**: Run scenario from quickstart.md § 1단계–3단계 against `file://` fixture catalog; assert `plugin_op_complete:result="success"` + receipt JSON appended under `~/.kosmos/memdir/user/consent/` + install dir created under `~/.kosmos/memdir/user/plugins/<plugin_id>/`. Captured under L1 unit + L3 expect/script.

### Implementation for User Story 1

- [X] T007 [US1] Modify `src/kosmos/plugins/installer.py:install_plugin()` to accept optional `progress_emitter: Callable[[int, str, str], Awaitable[None]] | None = None` parameter. Call `await progress_emitter(phase_num, message_ko, message_en)` between each of the 7 phases using canonical text from `specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md § Phases`. Backwards compatible (None → no emit). Reference: contracts/dispatcher-routing.md § Outbound frame sequence.
- [X] T008 [US1] Implement `handle_install` in `src/kosmos/ipc/plugin_op_dispatcher.py`: build progress_emitter closure that wraps each phase tick into a `PluginOpFrame(op="progress", progress_phase=N, progress_message_ko=..., progress_message_en=...)` + `write_frame(...)`. On `install_plugin` return, emit terminal `plugin_op_complete` with `result` + `exit_code` + `receipt_id`. Reference: contracts/dispatcher-routing.md § install sequence.
- [X] T009 [US1] Inject `IPCConsentBridge` into `installer.py:install_plugin()` `consent_prompt` parameter at the dispatcher boundary (T008). The default `_default_consent_prompt` (lines 219-229) stays as the test/in-process fallback; the IPC code path uses the bridge. Reference: contracts/consent-bridge.md § Signature compatibility.
- [X] T010 [P] [US1] Create `src/kosmos/plugins/uninstall.py` (NEW) with `uninstall_plugin(plugin_id, *, registry, executor, progress_emitter=None) -> UninstallResult` 3-phase flow: deregister → rmtree → write `PluginConsentReceipt(action_type="plugin_uninstall")`. Idempotent on already-removed plugin. Reference: data-model.md § E3 + contracts/dispatcher-routing.md § Outbound (uninstall).
- [X] T011 [US1] Implement `handle_uninstall` in `src/kosmos/ipc/plugin_op_dispatcher.py` mirroring T008 with the 3-phase progress emitter from T010. Reuse the same `_allocate_consent_position` flock for receipt position assignment. Reference: contracts/dispatcher-routing.md § uninstall sequence.
- [X] T012 [US1] Implement `handle_list` in `src/kosmos/ipc/plugin_op_dispatcher.py`: enumerate `registry._tools` (filtered through `is_active`) + load each plugin's manifest snapshot from install root → emit `payload_start` + `payload_delta` + `payload_end` triplet carrying `PluginListEntry[]` JSON, then a single `plugin_op_complete` with `correlation_id` matching. Reference: contracts/dispatcher-routing.md § list payload.
- [X] T013 [US1] Wire dispatcher boot in `src/kosmos/ipc/stdio.py`: pass `_ensure_tool_registry()` + `_ensure_tool_executor()` + `write_frame` + freshly-constructed `IPCConsentBridge(write_frame=write_frame, pending_perms=_pending_perms, session_id=frame.session_id)` into the T003 if-elif arm's `handle_plugin_op_request` call. Reference: contracts/dispatcher-routing.md § Dispatch logic.
- [X] T014 [P] [US1] Author unit tests `tests/ipc/test_plugin_op_dispatch.py`: 5 cases — install_request_dispatches, uninstall_request_dispatches, list_request_emits_payload_only, unknown_request_op_returns_error_frame, consent_timeout_emits_complete_exit5. Reference: contracts/e2e-pty-scenario.md § L1.
- [X] T015 [P] [US1] Author unit tests `tests/ipc/test_consent_bridge.py`: 6 cases — allow_once / allow_session / deny / timeout / pii_includes_acknowledgment_sha256 / layer_3_secondary_confirm. Reference: contracts/consent-bridge.md § Test seams + data-model.md § E2.

**Checkpoint**: User Story 1 fully functional — citizen install end-to-end works against fixture catalog with all 7 progress frames + consent + receipt. Verifiable independently via `pytest tests/ipc/test_plugin_op_dispatch.py tests/ipc/test_consent_bridge.py`.

---

## Phase 4: User Story 2 — Citizen invokes plugin tool through 5-primitive surface (Priority: P1)

**Goal**: After Story 1 install, the next conversational turn carries the new plugin's `tool_id` in `ChatRequestFrame.tools[]`, the model invokes the plugin through one of the 4 root primitives, and the Spec 033 permission gauntlet renders the layer-color modal sourced from the manifest's `permission_layer`.

**Independent Test**: Pre-install a fixture plugin (via Story 1 path or direct `register_plugin_adapter` call); send a citizen turn whose intent matches the plugin's `search_hint_ko`; assert `tool_use` frame for `plugin.<id>.<verb>` + matching `permission_request` with the manifest's layer + decision honoured per Spec 033.

### Implementation for User Story 2

- [X] T016 [US2] In `tui/src/ipc/bridgeSingleton.ts` (or equivalent), add a session-scoped `pluginsModifiedThisSession: boolean` flag. Set `true` on every `plugin_op_complete:result="success"` for `request_op ∈ {install, uninstall}`. Reset to `false` after consumed once on next ChatRequestFrame build. Reference: research.md § R-6 + contracts/dispatcher-routing.md § Tools[] propagation.
- [X] T017 [US2] In TUI ChatRequestFrame builder (likely `tui/src/services/api/` or `tui/src/ipc/bridge.ts` outbound path), if `pluginsModifiedThisSession === true`, set `frame.tools = []` to defer to backend's `registry.export_core_tools_openai()` fallback at `src/kosmos/ipc/stdio.py:1192-1195`. Reset flag after emit. Reference: research.md § R-6.
- [ ] T018 [P] [US2] Author integration test `tests/e2e/test_plugin_install_to_invoke.py:test_install_and_invoke_fixture_plugin`: install fixture plugin via dispatcher → send chat_request matching plugin's search_hint_ko (with `frame.tools=[]`) → assert next outbound `tool_use` frame has `tool_id="plugin.<id>.<verb>"`. Reference: contracts/e2e-pty-scenario.md § L1 + spec.md US2 acceptance scenarios.
- [ ] T019 [P] [US2] Author integration test `tests/e2e/test_plugin_layer_routing.py`: install 3 fixture plugins with `permission_layer ∈ {1, 2, 3}` → invoke each → assert each `permission_request` carries the correct `layer` field; assert layer-3 plugin triggers Spec 033 layer-3 secondary confirm path. Reference: spec.md § FR-011, FR-014.
- [ ] T020 [P] [US2] Author integration test `tests/e2e/test_plugin_pii_acknowledgment.py`: install a fixture plugin with `processes_pii: true` + valid PIPA acknowledgment → invoke → assert `permission_request` carries `acknowledgment_sha256` + `trustee_org_name` from the manifest. Reference: spec.md § FR-012 + contracts/consent-bridge.md § PIPA §26.

**Checkpoint**: User Stories 1 + 2 work together — citizen install + immediate invoke loop is closed. Verifiable via `pytest tests/e2e/test_plugin_install_to_invoke.py tests/e2e/test_plugin_layer_routing.py tests/e2e/test_plugin_pii_acknowledgment.py`.

---

## Phase 5: User Story 3 — Citizen browses installed plugins via TUI surface (Priority: P2)

**Goal**: `/plugin install` and `/plugins` slash commands route to the KOSMOS citizen path (not CC marketplace residue). The `PluginBrowser` (Spec 1635 T065) renders installed plugins with tier badges + layer color glyphs + trustee org names. UI-E.3 keystrokes (Space/i/r/a) work; `a` displays the deferred-to-#1820 message.

**Independent Test**: Run `/plugins` against a fixture environment with 3 pre-installed plugins (mixed tier + layer); verify all 3 rows render correctly; press `r` on a row → confirmation modal → Y → row disappears + uninstall receipt appended; press `a` → Korean deferred message visible.

### Implementation for User Story 3

- [X] T021 [US3] **CRITICAL wire-up**: In `tui/src/commands.ts`, change line 133 from `import plugin from './commands/plugin/index.js'` to `import plugin from './commands/plugin.js'`. This is the single line that activates the entire KOSMOS citizen plugin path; all subsequent US3 tasks depend on it. Reference: research.md § V1 verdict.
- [X] T022 [P] [US3] In `tui/src/commands/plugin.ts`, remove the H7 review-eval deferred suffix from acknowledgement strings at lines 111-112, 135-136, 164-166 (`"(backend dispatcher not yet wired — use ...)"`). Backend is now wired. Reference: spec.md § Background Gap 1.
- [X] T023 [US3] In `tui/src/commands/plugins.ts`, replace the `KOSMOS_PLUGIN_REGISTRY` env-var stub (lines 32-51) with: emit `plugin_op_request:list` with fresh correlation_id → await matching `plugin_op_complete` + reassembled payload → parse `PluginListEntry[]` → return as `PluginEntry[]`. Reference: data-model.md § E5 + contracts/citizen-plugin-store.md § /plugins browser data flow.
- [X] T024 [P] [US3] Extend `PluginEntry` type in `tui/src/components/plugins/PluginBrowser.tsx:26-33` with 6 additive optional fields: `tier`, `layer`, `trustee_org_name`, `install_timestamp_iso`, `search_hint_ko`, `search_hint_en`. Backwards compatible with existing Spec 1635 T065 tests. Reference: contracts/citizen-plugin-store.md § PluginEntry shape.
- [ ] T025 [US3] Render the 6 new columns in `tui/src/components/plugins/PluginBrowser.tsx` layout (status glyph + name + version + tier badge + layer color glyph + description + active hint). Preserve ≥90% Spec 1635 T065 visual fidelity. Reference: contracts/citizen-plugin-store.md § Visual layout.
- [ ] T026 [P] [US3] Implement detail modal sub-component (or extend existing `onDetail` callback's render path) in `tui/src/components/plugins/PluginDetail.tsx` (NEW) — renders manifest summary including PIPA acknowledgment SHA-256 for `processes_pii=true` plugins. Reference: contracts/citizen-plugin-store.md § Detail view.
- [ ] T027 [P] [US3] Implement remove confirmation modal in `tui/src/components/plugins/PluginRemoveConfirm.tsx` (NEW) — Y emits `plugin_op_request:uninstall`. Reference: contracts/citizen-plugin-store.md § Remove confirmation.
- [X] T028 [P] [US3] Wire `onMarketplace` callback in `tui/src/components/plugins/PluginBrowser.tsx:73,105` to render the deferred Korean message: `"스토어 브라우저는 #1820 에서 작업 중입니다 (deferred)"`. Reference: contracts/citizen-plugin-store.md § Keystroke contract `a`.
- [ ] T029 [P] [US3] Implement in-flight install placeholder row in `tui/src/components/plugins/PluginBrowser.tsx`: when a `plugin_op_progress` frame arrives for a plugin not yet in the list, render `⏳ <name> ... (설치 중… 단계 N/7)`. Replace with real row when terminal `plugin_op_complete` arrives. Reference: contracts/citizen-plugin-store.md § In-flight install indicator.
- [X] T030 [P] [US3] Author bun tests `tui/src/components/plugins/PluginBrowser.test.tsx` + `tui/src/commands/plugins.test.ts`: 6 cases — renders 3 entries with mixed tier/layer + Space toggles isActive visually + r emits uninstall + a renders deferred message + i opens detail with PII fields + executePlugins round-trips list. Reference: contracts/citizen-plugin-store.md § Test seams.

**Checkpoint**: Citizen typing `/plugins` opens the PluginBrowser populated from real backend state via IPC round-trip. Pressing `r` removes a plugin via the dispatcher. `a` displays the deferred message.

---

## Phase 6: User Story 4 — Verification engineer captures the integration loop via 4-layer PTY ladder (Priority: P2)

**Goal**: Produce grep-friendly proof under `specs/1979-plugin-dx-tui-integration/` that Stories 1+2+3 work end-to-end. Codex review and human review can both verify the artifacts.

**Independent Test**: Run `bash specs/1979-plugin-dx-tui-integration/scripts/run-e2e.sh`; assert all 4 layer artifacts exist (L1 pytest+bun output, L2 JSONL, L3 text-log, L4 gif). Grep L3 for canonical phase markers per FR-021.

### Implementation for User Story 4

- [ ] T031 [P] [US4] Author fixture catalog + bundle under `specs/1979-plugin-dx-tui-integration/scripts/fixtures/`: `catalog.json` (CatalogIndex schema with 1 entry pointing at file:// URLs), `seoul-subway.tar.gz` (containing `manifest.yaml` + `adapter.py` + minimal Pydantic v2 input/output schemas), `seoul-subway.intoto.jsonl` (SLSA provenance compatible with `KOSMOS_PLUGIN_SLSA_SKIP=true` test path). Reference: contracts/e2e-pty-scenario.md § L2 + spec/1636 contracts/manifest.schema.json.
- [ ] T032 [P] [US4] Author L2 stdio JSONL probe `specs/1979-plugin-dx-tui-integration/scripts/smoke-stdio.sh` (executable shell script) that pipes raw `plugin_op_request` frames into backend stdio mode + captures the JSONL response stream → outputs `specs/1979-plugin-dx-tui-integration/smoke-stdio.jsonl`. Includes 4 inbound frames: list-before / install / permission-response / list-after / chat_request. Reference: contracts/e2e-pty-scenario.md § L2.
- [ ] T033 [P] [US4] Author L3 expect script `specs/1979-plugin-dx-tui-integration/scripts/smoke-1979.expect` driving the TUI under PTY (via `script(1)`) → outputs `smoke-1979.txt`. Covers happy path + 3 negative paths in sibling scripts: `smoke-1979-deny.expect` (consent N → exit_code=5), `smoke-1979-bad-name.expect` (catalog miss → exit_code=1), `smoke-1979-revoke.expect` (install + revoke + re-invoke fail-closed). Reference: contracts/e2e-pty-scenario.md § L3.
- [ ] T034 [P] [US4] Author L4 vhs `.tape` script `specs/1979-plugin-dx-tui-integration/scripts/smoke-1979.tape` driving the citizen scenario for visual review. Output: `specs/1979-plugin-dx-tui-integration/smoke-1979.gif` (gitignored). Reference: contracts/e2e-pty-scenario.md § L4 + memory `feedback_vhs_tui_smoke`.
- [ ] T035 [US4] Author master orchestrator `specs/1979-plugin-dx-tui-integration/scripts/run-e2e.sh`: runs L1 (`uv run pytest tests/ipc/ tests/plugins/ tests/e2e/` + `bun test --cwd tui`) + L2 (T032) + L3 (T033 happy path + 3 negatives) sequentially; reports SC-1..SC-4 evidence map. L4 is manual-only (`bun run vhs ...`). Reference: contracts/e2e-pty-scenario.md § Run conditions + § Acceptance evidence.

**Checkpoint**: All 4 layers produce committed artifacts (L4 gitignored). Codex review can grep L3 for canonical markers; human review can play L4 gif.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final checks + documentation + spec.md deferred items update for the 2 new tracking entries discovered during Phase 0.

- [X] T036 [P] Update `specs/1979-plugin-dx-tui-integration/spec.md` § "Deferred to Future Work" table with 2 new rows surfaced by research.md V1 + R-3/R-4 verdicts: (1) "CC marketplace residue cleanup (commands/plugin/*, services/plugins/*, utils/plugins/*) — Spec 1633-style follow-up — NEEDS TRACKING", (2) "Plugin runtime enable/disable IPC (plugin_op_request:activate/deactivate) — Post-P5 plugin-lifecycle Epic — NEEDS TRACKING". Reference: research.md § Deferred Items Validation.
- [X] T037 [P] Add `.gitignore` entry for `specs/1979-plugin-dx-tui-integration/smoke-1979.gif` (binary, > 1 MB risk per AGENTS.md hard rule).
- [ ] T038 Run final `quickstart.md` validation manually: walk through the 5-step citizen scenario; confirm each step's expected output matches the prose mock-up; capture any discrepancies as bug fixes before PR. Reference: quickstart.md.

**Checkpoint**: All Epic #1979 artifacts ready for PR. SC-001 through SC-010 verifiable.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies. T001 + T002 can run in parallel.
- **Phase 2 (Foundational)**: Depends on Phase 1. T003 must complete before T004 (dispatcher arm wires the module). T005 + T006 are independent; T004 depends on T005 (uses `_inactive`/`is_active`) and T006 (passes consent_bridge in handler signature). So Phase 2 ordering: T003 → (T005 ‖ T006) → T004.
- **Phase 3 (US1)**: Depends on Phase 2. T007 (progress_emitter param) MUST land before T008 (handle_install uses it). T008/T011/T012 implement the 3 dispatcher routes — can land in parallel after T007. T009 sequence-depends on T008 (consent_bridge injection lives at the dispatcher boundary). T010 [P] independent of T011/T012. T013 (boot wiring) gates the test runs; lands after T008/T011/T012. T014 + T015 [P] are independent test files.
- **Phase 4 (US2)**: Depends on Phase 3 (need install path live). T016 + T017 are sequential (T017 reads T016's flag). T018/T019/T020 [P] are independent test files.
- **Phase 5 (US3)**: Depends on Phase 3 (T013 boot wiring) for the `/plugin` slash command to reach backend. **T021 is the critical wire-up that unblocks US3 acceptance test**. T022 [P] is text-only edit. T023 depends on T021. T024 [P] is type extension. T025 depends on T024. T026/T027/T028/T029 [P] are independent components. T030 depends on all visual tasks completed.
- **Phase 6 (US4)**: Depends on Phase 5 fully complete (E2E exercises citizen-typed slash commands). T031 [P] is fixture authoring. T032/T033/T034 [P] are independent script files. T035 sequence-depends on T032/T033 (orchestrator references them).
- **Phase 7 (Polish)**: Depends on Phases 3+4+5+6 all complete.

### User Story Dependencies

- **US1** (P1): Foundational only.
- **US2** (P1): Foundational + US1 (need install path live to deliver Story 2's "after install, model invokes" flow). Test fixtures can pre-install via direct backend call; production path needs full US1.
- **US3** (P2): Foundational + US1 (need backend dispatcher live to power `/plugins` data binding). The `commands.ts:133` swap (T021) is the gate.
- **US4** (P2): Foundational + US1 + US2 + US3 (E2E exercises the integrated flow).

### Within Each User Story

- Models / module skeletons before services / handlers
- Backend handlers before TUI consumers
- Tests (per Constitution §IV happy-path + error-path) follow implementation but precede checkpoint verification

### Parallel Opportunities

- All Phase 1 tasks marked [P] (T001 + T002).
- Phase 2: T005 + T006 [P] after T003 lands.
- Phase 3: T010 [P] after T009 lands; T014 + T015 [P] after handlers land.
- Phase 4: T018 + T019 + T020 [P] after T016 + T017 land.
- Phase 5: T022 + T024 [P] after T021. T026 + T027 + T028 + T029 [P] after T025. T030 [P] after components.
- Phase 6: T031 + T032 + T033 + T034 [P] independent fixtures + scripts. T035 after.
- Phase 7: T036 + T037 [P]; T038 after.

---

## Parallel Example: User Story 1 (Phase 3)

```bash
# After T003 (stdio.py arm) lands:
# Run T005 + T006 in parallel (different files):
Task: "Extend ToolRegistry with _inactive set + set_active/is_active/deregister methods in src/kosmos/tools/registry.py"
Task: "Create IPCConsentBridge class in src/kosmos/plugins/consent_bridge.py"

# After T007 (progress_emitter param) lands:
# Run T008 + T010 + T011 in parallel (different functions in dispatcher + new uninstall module):
Task: "Implement handle_install in src/kosmos/ipc/plugin_op_dispatcher.py"
Task: "Create uninstall_plugin in src/kosmos/plugins/uninstall.py"
Task: "Implement handle_uninstall in src/kosmos/ipc/plugin_op_dispatcher.py"

# After T013 (boot wiring) lands:
# Run T014 + T015 in parallel (different test files):
Task: "Author tests/ipc/test_plugin_op_dispatch.py"
Task: "Author tests/ipc/test_consent_bridge.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 only — citizen install loop)

1. Complete Phase 1: Setup (T001 + T002 PTY baseline).
2. Complete Phase 2: Foundational (T003–T006).
3. Complete Phase 3: User Story 1 (T007–T015).
4. **STOP and VALIDATE**: `pytest tests/ipc/test_plugin_op_dispatch.py tests/ipc/test_consent_bridge.py` + manual `kosmos --ipc stdio` against fixture catalog.
5. Citizen install loop is shippable as a partial MVP; defer Stories 2/3/4 to subsequent commits.

### Incremental Delivery

- **MVP1** (Phases 1+2+3): Citizen can install — but `/plugin` is still routed to CC marketplace residue (T021 not yet done). Programmatic install via `uvx kosmos plugin install` shell entry-point works.
- **MVP2** (+Phase 4): Citizen can install + invoke. Programmatic-only install path; TUI slash command still mis-routed.
- **MVP3** (+Phase 5 with T021 swap): Full citizen experience — `/plugin install <name>` + `/plugins` browser + auto-invoke after install.
- **MVP4** (+Phase 6+7): E2E verified, deferred items tracked, ready for PR + Codex review.

### Parallel Team Strategy (Agent Teams)

Per AGENTS.md § Agent Teams + memory `feedback_speckit_autonomous`:

- **Lead (Opus)** — owns Phase 0/1/2 design + T003 critical-path arm.
- **Teammate A (Sonnet · Backend Architect)** — Phase 2/3 backend (T004, T005, T006, T007, T008, T010, T011, T012, T013).
- **Teammate B (Sonnet · API Tester)** — Phase 3/4/5 tests (T014, T015, T018, T019, T020, T030).
- **Teammate C (Sonnet · Frontend Developer)** — Phase 5 TUI (T021, T022, T023, T024, T025, T026, T027, T028, T029).
- **Teammate D (Sonnet · API Tester)** — Phase 6 E2E (T031, T032, T033, T034, T035).

3+ independent tasks → parallel Teammates per AGENTS.md trigger. Lead synthesizes + reviews + final integration.

---

## Notes

- [P] tasks = different files, no dependency on incomplete tasks.
- [Story] label maps each task to a specific user story for traceability + independent test.
- Each user story should be independently completable + testable per the spec template.
- Per Constitution §IV: every adapter / endpoint addition includes happy-path + error-path tests.
- Per memory `feedback_speckit_autonomous`: implement skill 진입 시 단계별 승인 대기 X — Lead + Teammates proceed autonomously up to PR.
- Per memory `feedback_integrated_pr_only`: bun test 통과 + PTY 검증 통과 후 단일 통합 PR.
- Per memory `feedback_pr_closing_refs`: PR body uses `Closes #1979` only (Epic); Task sub-issues closed post-merge by `gh issue close`.
- Per memory `feedback_codex_reviewer`: after every push, query `chatgpt-codex-connector[bot]` PR comments + address each.
- Per memory `feedback_subissue_100_cap`: 38 tasks ≪ 90-task budget (with 52 slots reserve for `[Deferred]` placeholders + mid-cycle additions).

**Final task count**: 38 tasks across 7 phases. Well under SC-007 ≤ 90 sub-issue budget.
