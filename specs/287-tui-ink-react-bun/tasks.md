---
description: "Task list for Spec 287 TUI (Ink + React + Bun)"
---

# Tasks: Full TUI (Ink + React + Bun)

**Input**: Design documents from `/specs/287-tui-ink-react-bun/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/

**Tests**: Tests ARE REQUIRED for this feature. FR-034 mandates fixture-driven `ink-testing-library` tests per discriminated-union arm; FR-007 / SC-2 mandates a 10-min / 100 ev/s soak test; FR-015 / SC-4 mandates a Korean IME headless test; contracts/ README requires a frame-schema drift CI gate.

**Organization**: Tasks grouped by user story (7 total) for independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1–US7 per spec.md
- Exact file paths required in every task

## Path Conventions

- **TUI workspace**: `tui/` at repo root (TypeScript + Ink + Bun; **only** TypeScript directory allowed per AGENTS.md hard rule)
- **Python backend IPC adapter**: `src/kosmos/ipc/` (new subpackage)
- **Python backend tests**: `tests/ipc/`
- **ADRs**: `docs/adr/`
- **Upstream lifts**: Every file in `tui/src/ink/`, `tui/src/commands/`, `tui/src/theme/`, `tui/src/components/coordinator/`, `tui/src/components/conversation/VirtualizedList.tsx`, `tui/src/hooks/` (selected) MUST carry the attribution header `// Source: .references/claude-code-sourcemap/restored-src/<original-path> (Claude Code 2.1.88, research-use)` per FR-011.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the TUI workspace, pin toolchain, register environment variables, stub the Python IPC entrypoint, and author the three blocking ADRs (FR-057 gates SC-1).

- [X] T001 Create `tui/` directory at repo root with `.gitignore` (node_modules, bun.lockb if non-committed, `*.generated.ts`) in `tui/.gitignore`
- [X] T002 [P] Author ADR `docs/adr/NNN-bun-ink-react-tui-stack.md` approving Bun + TypeScript + Ink 7 + React 19.2 stack with explicit rejection of Node+pnpm+vitest alternative (FR-057, SC-1)
- [X] T003 [P] Author ADR `docs/adr/NNN-claude-code-sourcemap-port.md` documenting research-use + attribution + diff-script policy for files lifted from `.references/claude-code-sourcemap/restored-src/` (FR-011, FR-012, FR-013, SC-9)
- [X] T004 [P] Author ADR `docs/adr/NNN-korean-ime-strategy.md` forcing choice between (a) `@jrichman/ink@6.6.9` fork and (b) Node readline hybrid; recommendation is option (a) per research.md § 2.6 (FR-014, R1)
- [X] T005 Create `tui/package.json` pinning `bun@1.2.x`, `typescript@^5.6`, `react@^19.2`, `@inkjs/ui@^2`, `zod@^3.23`, `ink-testing-library@^4`; `ink` pin resolved post-ADR T004 (either `ink@^7` or `npm:@jrichman/ink@6.6.9`)
- [X] T006 Create `tui/tsconfig.json` with `"strict": true`, `"jsx": "react-jsx"`, `"moduleResolution": "bundler"`, `"target": "es2022"`, `"types": ["bun-types"]`
- [X] T007 Create `tui/NOTICE` declaring research-use reconstruction and attributing Anthropic (FR-012)
- [X] T008 [P] Create `tui/docs/cjk-width-known-issues.md` documenting ink#688 / ink#759 CJK width edge cases (spec Edge Cases, Assumption #3)
- [X] T009 [P] Create `tui/docs/accessibility-checklist.md` skeleton covering keyboard-only navigation + screen-reader manual smoke (FR-055, FR-056)
- [X] T010 [P] Register `KOSMOS_TUI_THEME`, `KOSMOS_TUI_LOG_LEVEL`, `KOSMOS_TUI_SUBSCRIBE_TIMEOUT_S`, `KOSMOS_TUI_IME_STRATEGY`, `KOSMOS_TUI_SOAK_EVENTS_PER_SEC` in `src/kosmos/config/env_registry.py` per #468 registry pattern (FR-041)
- [X] T011 [P] Add `bun run tui`, `bun run gen:ipc`, `bun run diff:upstream`, `bun run tui:fixture`, `bun test:soak` scripts to `tui/package.json`
- [X] T012 Run `bun install` from `tui/` to generate `tui/bun.lockb`; verify Ink + React + @inkjs/ui resolve under the ADR-pinned strategy

**Checkpoint**: Workspace bootstraps; lockfile is committed-ready; ADRs are in place to unblock all lift work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: IPC contract source of truth + code-gen pipeline + base Ink reconciler lift + theme tokens + attribution enforcement. These tasks MUST complete before any user story phase starts — every user story depends on the IPC bridge contract + Ink reconciler.

- [X] T013 Create `src/kosmos/ipc/__init__.py` exposing `IPCFrame` union (Pydantic v2 models matching `specs/287-tui-ink-react-bun/contracts/ipc-frames.schema.json`) in `src/kosmos/ipc/frame_schema.py`
- [X] T014 Add Python contract test in `tests/ipc/test_frame_schema.py` verifying every JSON Schema in `specs/287-tui-ink-react-bun/contracts/*.schema.json` round-trips through `IPCFrame.model_validate_json` + `model_dump_json` for all 10 arms
- [X] T015 Create `tui/scripts/gen-ipc-types.ts` that spawns Python and runs `kosmos.ipc.frame_schema.IPCFrame.model_json_schema()` → writes `tui/src/ipc/frames.generated.ts` via `datamodel-code-generator` or `json-schema-to-typescript`; support `--check` flag for CI drift gate (FR-003)
- [X] T016 Run `bun run gen:ipc` once to produce `tui/src/ipc/frames.generated.ts` and commit it with a do-not-edit banner
- [X] T017 [P] Add CI gate that runs `bun run gen:ipc -- --check` and fails if the committed generated file drifts from the live Pydantic schema (contracts/README.md § Authority)
- [X] T018 Lift Ink reconciler files from `.references/claude-code-sourcemap/restored-src/src/ink/` into `tui/src/ink/` (reconciler.ts, renderer.ts, root.ts, dom.ts, layout/, events/, node-cache.ts, measure-text.ts, render-*.ts, parse-keypress.ts) — every file prepended with the FR-011 attribution header (~29 files)
- [X] T019 [P] Create `tui/scripts/diff-upstream.sh` that walks every file in `tui/src/ink/` / `tui/src/commands/` / `tui/src/theme/` / `tui/src/components/coordinator/` / `tui/src/components/conversation/` with the FR-011 header and diffs them against their `.references/claude-code-sourcemap/restored-src/` source; exit non-zero on divergence (FR-013)
- [X] T020 [P] Add CI check that runs `tui/scripts/diff-upstream.sh` and asserts every lifted file retains its attribution header via grep (FR-011, SC-9)
- [X] T021 Lift theme tokens + 3 built-in themes from `restored-src/src/components/design-system/` into `tui/src/theme/tokens.ts`, `tui/src/theme/default.ts`, `tui/src/theme/dark.ts`, `tui/src/theme/light.ts` with attribution headers (FR-039, FR-040)
- [X] T022 Create `tui/src/theme/provider.tsx` (KOSMOS-original) that reads `KOSMOS_TUI_THEME` env var and provides `ThemeToken` context to all children; default to `default` theme on unset (FR-039, FR-041)
- [X] T023 Create `tui/src/store/session-store.ts` implementing `useSyncExternalStore` reducer store per data-model.md § 3; lift the ≈35-line store pattern from `restored-src/src/store/` with attribution header (FR-050)
- [X] T024 [P] Create `tui/src/i18n/en.ts` + `tui/src/i18n/ko.ts` with bilingual user-visible strings (FR-037); English is source, Korean is co-located translation

**Checkpoint**: Python-side contract + TypeScript-side generated types + Ink reconciler + theme + store + bilingual strings all in place. User stories can now proceed in parallel.

---

## Phase 3: User Story 1 — IPC Bridge + Streaming Chunk Renderer Swap (Priority: P1) 🎯 MVP

**Goal**: TUI can spawn the Python backend over stdio JSONL, receive `assistant_chunk` frames, render them within 50 ms each, detect crashes within 5 s, and sustain 100 ev/s for 10 min.

**Independent Test**: `bun run tui:fixture tests/fixtures/smoke/route-safety.jsonl` renders a scripted 3-turn dialog end-to-end with zero live API calls. `bun test:soak` passes 100 ev/s × 10 min.

### Tests for User Story 1

- [X] T025 [P] [US1] Contract test `tui/tests/ipc/codec.test.ts`: zod-parse every JSON file under `tui/tests/fixtures/ipc/` against `frames.generated.ts` discriminated union; one pass case + one malformed-json case per arm
- [X] T026 [P] [US1] Integration test `tui/tests/ipc/bridge.test.ts`: spawn a stub Python backend (fixture echo) via `Bun.spawn`, assert process-up within 2 s, stream 10 `assistant_chunk` frames, assert FIFO order + p99 ≤ 50 ms per chunk (US1 scenarios 1, 2, 5; FR-001, FR-005, FR-006)
- [X] T027 [P] [US1] Integration test `tui/tests/ipc/crash.test.ts`: kill stub backend mid-stream, assert `<CrashNotice />` renders within 5 s and no `KOSMOS_*` env var values appear in the rendered output (US1 scenario 4; FR-004, SC-5)
- [X] T028 [P] [US1] Soak test `tui/tests/ipc/soak.test.ts` (marked `@slow`; 10-min runtime): replay a fixture stream at 100 ev/s via `tui/scripts/soak.ts`; assert zero dropped frames, p99 chunk latency ≤ 50 ms, RSS growth ≤ 50 MB, clean exit (US1 scenario 3; FR-007, SC-2)
- [X] T029 [P] [US1] Python round-trip test `tests/ipc/test_stdio_roundtrip.py`: pytest-asyncio spawns `uv run kosmos-backend --ipc stdio`, writes 10 frames of each arm, reads responses, asserts byte-for-byte union validity

### Implementation for User Story 1

- [X] T030 [P] [US1] Implement Python IPC reader/writer loop in `src/kosmos/ipc/stdio.py`: `asyncio.StreamReader` on `sys.stdin.buffer`, `sys.stdout.buffer.write` + `flush` for output; uses stdlib only (no new runtime deps)
- [X] T031 [P] [US1] Add `--ipc stdio` CLI flag to `src/kosmos/cli/__main__.py` that dispatches to `kosmos.ipc.stdio:run()` instead of the existing REPL
- [X] T032 [P] [US1] Create `tui/src/ipc/codec.ts` (KOSMOS-original) providing `encodeFrame(frame: IPCFrame): string` and `decodeFrame(line: string): IPCFrame | { error }` with zod validation (belt-and-braces against generated types)
- [X] T033 [US1] Create `tui/src/ipc/bridge.ts` wrapping `Bun.spawn(["uv", "run", "kosmos-backend", "--ipc", "stdio"], { stdio: ["pipe","pipe","pipe"] })`; line-split stdout on `\n`; push each decoded frame into a FIFO async queue consumed by the store reducer (FR-001, FR-002, FR-005, FR-009)
- [X] T034 [US1] Create `tui/src/ipc/crash-detector.ts`: subscribe to `child.exited`, watch stderr flush, detect non-zero exit or fatal stderr within ≤ 5 s; emit a synthetic `error` frame whose `message` + `details` are run through a KOSMOS_*-env-var redactor (reuse #468 guard pattern) (FR-004)
- [X] T035 [US1] Create `tui/src/components/conversation/CrashNotice.tsx` rendering the redacted crash payload with a restart hint (US1 scenario 4)
- [X] T036 [US1] Create `tui/src/components/conversation/StreamingMessage.tsx` (lift from `restored-src/src/components/` streaming-message pattern with attribution header) that reads from `session-store` via `useSyncExternalStore` and only re-renders its own message slot on new chunks (FR-050, US1 scenario 2)
- [X] T037 [US1] Create `tui/src/main.tsx` / `tui/src/entrypoints/tui.tsx` wiring `bridge → store → ThemeProvider → <App />`; SIGTERM child on Ctrl-C or `session_event.exit` with ≤ 3 s timeout before SIGKILL (FR-009)
- [X] T038 [US1] Create `tui/scripts/soak.ts` replay helper that drives `tui/tests/fixtures/soak/` at configurable events/sec; used by T028
- [X] T039 [US1] Create `tui/tests/fixtures/smoke/route-safety.jsonl` (hand-curated from #507 recorded responses) showing 3-turn route-safety dialog used by quickstart step 2 (FR-035)
- [X] T040 [US1] Add DEBUG-level frame logging controlled by `KOSMOS_TUI_LOG_LEVEL` in `tui/src/ipc/bridge.ts`; default WARN (FR-010)

**Checkpoint**: `bun run tui` against the real Python backend shows streaming output in Korean; `bun test:soak` passes.

---

## Phase 4: User Story 2 — Command Dispatcher + Theme Engine + Session Commands (Priority: P1)

**Goal**: `/save`, `/sessions`, `/resume`, `/new` work via IPC. Theme engine applies `default` / `dark` / `light` via `KOSMOS_TUI_THEME`. Command registry shape preserves upstream structure for diff tracking.

**Independent Test**: `ink-testing-library` injects `/save` into the input stream and asserts a `session_event` IPC frame is emitted; swap `KOSMOS_TUI_THEME=dark` and assert Box/Text tokens flip.

### Tests for User Story 2

- [X] T041 [P] [US2] Component test `tui/tests/commands/dispatcher.test.ts`: inject `/save`, `/sessions`, `/resume <id>`, `/new`, and an unknown `/foo`; assert (a) each valid command emits the matching `session_event` frame, (b) `/foo` renders a help snippet (no crash) (US2 scenarios 1, 2, 4; FR-038, FR-042)
- [X] T042 [P] [US2] Component test `tui/tests/theme/provider.test.tsx`: set `KOSMOS_TUI_THEME=light|dark|default` and assert `<ThemeProvider />` exposes the matching token set; unset → default token set (US2 scenario 3; FR-039)
- [X] T043 [P] [US2] Registry-shape test `tui/tests/commands/registry.test.ts`: load `tui/src/commands/registry.ts` and assert its shape (keys, per-entry interface) is structurally identical to `restored-src/src/commands/` registry per FR-036 / US2 scenario 5
- [X] T044 [P] [US2] i18n test `tui/tests/i18n/strings.test.ts`: assert `en.ts` and `ko.ts` export the same key set; no English string in `ko.ts` except technical identifiers (FR-037)

### Implementation for User Story 2

- [X] T045 [US2] Lift `tui/src/commands/dispatcher.ts` from `restored-src/src/commands.ts` + `restored-src/src/commands/` registry shape with attribution header (FR-036)
- [X] T046 [P] [US2] Create `tui/src/commands/save.ts` emitting `session_event: "save"` via IPC bridge (FR-038, US2 scenario 2)
- [X] T047 [P] [US2] Create `tui/src/commands/sessions.ts` emitting `session_event: "list"` + rendering returned list (FR-038, US2 scenario 1)
- [X] T048 [P] [US2] Create `tui/src/commands/resume.ts` emitting `session_event: "resume"` with `{id}` payload (FR-038)
- [X] T049 [P] [US2] Create `tui/src/commands/new.ts` emitting `session_event: "new"` + clearing store (FR-038)
- [X] T050 [US2] Wire dispatcher into `tui/src/entrypoints/tui.tsx` — slash-prefixed input intercepted before `user_input` frame emission
- [X] T051 [US2] Add help renderer for unknown commands in `tui/src/commands/dispatcher.ts` reading registered names (FR-042, US2 scenario 4)
- [X] T052 [US2] Wire `ThemeProvider` into `tui/src/main.tsx` at root; all Box/Text components consume `useTheme()` hook — no inline hex colors permitted (FR-040)
- [X] T053 [P] [US2] Document `KOSMOS_TUI_THEME` in `docs/configuration.md` with the 3 values (FR-039)

**Checkpoint**: Slash commands round-trip through IPC; theme switch works; upstream registry diff applies cleanly.

---

## Phase 5: User Story 3 — Five-Primitive Renderers (Priority: P1)

**Goal**: Every `tool_result` variant from Spec 031 + Spec 022 has a dedicated Ink renderer. Unknown `kind` falls through to `<UnrecognizedPayload />`. No string sniffing.

**Independent Test**: For each component, feed a single fixture JSON via `ink-testing-library` and assert the rendered output matches the expected shape — no IPC, no backend.

### Tests for User Story 3

- [X] T054 [P] [US3] Component test `tui/tests/components/primitive/PointCard.test.tsx` — LookupPoint + LookupRecord fixtures from `tui/tests/fixtures/lookup/point/` (US3 scenario 1; FR-017)
- [X] T055 [P] [US3] Component test `tui/tests/components/primitive/TimeseriesTable.test.tsx` — LookupTimeseries fixture; assert semantic headers appear, raw codes (TMP/PCP/REH) do NOT (US3 scenario 2; FR-018)
- [X] T056 [P] [US3] Component test `tui/tests/components/primitive/CollectionList.test.tsx` — LookupList + LookupCollection fixture; assert pagination row + "Load more" affordance triggers a follow-up `lookup(mode="fetch", page=...)` IPC frame (US3 scenario 3; FR-019)
- [X] T057 [P] [US3] Component test `tui/tests/components/primitive/DetailView.test.tsx` — LookupDetail fixture (FR-020)
- [X] T058 [P] [US3] Component test `tui/tests/components/primitive/ErrorBanner.test.tsx` — LookupError with `reason=auth_required` (permission-consent dialog) + 4 other reason values (US3 scenario 4; FR-021)
- [X] T059 [P] [US3] Component test `tui/tests/components/primitive/CoordPill.test.tsx` — resolve_location coords slot (FR-022)
- [X] T060 [P] [US3] Component test `tui/tests/components/primitive/AdmCodeBadge.test.tsx` — 10-digit adm_cd + Korean name (FR-023)
- [X] T061 [P] [US3] Component test `tui/tests/components/primitive/AddressBlock.test.tsx` — road + jibun + zipcode (FR-024)
- [X] T062 [P] [US3] Component test `tui/tests/components/primitive/POIMarker.test.tsx` — POI id + canonical name (FR-025)
- [X] T063 [P] [US3] Component test `tui/tests/components/primitive/SubmitReceipt.test.tsx` — all 5 submit families + `[MOCK: <reason>]` chip for 4 mock_reason values (US3 scenario 6; FR-026)
- [X] T064 [P] [US3] Component test `tui/tests/components/primitive/SubmitErrorBanner.test.tsx` — revocation/rollback hint (FR-027)
- [X] T065 [P] [US3] Component test `tui/tests/components/primitive/EventStream.test.tsx` — CBS / REST pull / RSS modality banner + live event append; assert RSS `guid` dedup indicator and CBS storm throttle surface (US3 scenario 7; FR-028)
- [X] T066 [P] [US3] Component test `tui/tests/components/primitive/StreamClosed.test.tsx` — 3 close_reason values (exhausted, revoked, timeout) (FR-029)
- [X] T067 [P] [US3] Component test `tui/tests/components/primitive/AuthContextCard.test.tsx` — all 18 Korea tier values as primary label + NIST AAL hint absent/present; assert primary label never omitted (US3 scenario 8; FR-030, FR-031)
- [X] T068 [P] [US3] Component test `tui/tests/components/primitive/AuthWarningBanner.test.tsx` — downgrade + expiry + AAL drift (FR-032)
- [X] T069 [P] [US3] Component test `tui/tests/components/primitive/UnrecognizedPayload.test.tsx` — unknown `kind`, missing `kind`, malformed nested payload; assert warning log emitted + no crash (US3 scenario 9, Edge Cases; FR-033)

### Implementation for User Story 3

- [X] T070 [P] [US3] Create `tui/src/components/primitive/PointCard.tsx` rendering key-value table + collapsible raw-JSON expander (FR-017)
- [X] T071 [P] [US3] Create `tui/src/components/primitive/TimeseriesTable.tsx` with semantic column headers only (FR-018)
- [X] T072 [P] [US3] Create `tui/src/components/primitive/CollectionList.tsx` with pagination + "Load more" callback emitting follow-up IPC frame (FR-019)
- [X] T073 [P] [US3] Create `tui/src/components/primitive/DetailView.tsx` (FR-020)
- [X] T074 [P] [US3] Create `tui/src/components/primitive/ErrorBanner.tsx` with per-reason icon + retry; `auth_required` wires to permission-consent dialog (FR-021)
- [X] T075 [P] [US3] Create `tui/src/components/primitive/CoordPill.tsx` (FR-022)
- [X] T076 [P] [US3] Create `tui/src/components/primitive/AdmCodeBadge.tsx` (FR-023)
- [X] T077 [P] [US3] Create `tui/src/components/primitive/AddressBlock.tsx` (FR-024)
- [X] T078 [P] [US3] Create `tui/src/components/primitive/POIMarker.tsx` (FR-025)
- [X] T079 [P] [US3] Create `tui/src/components/primitive/SubmitReceipt.tsx` handling all 5 families + `[MOCK: <reason>]` chip (FR-026)
- [X] T080 [P] [US3] Create `tui/src/components/primitive/SubmitErrorBanner.tsx` (FR-027)
- [X] T081 [P] [US3] Create `tui/src/components/primitive/EventStream.tsx` consuming subscribe AsyncIterator frames; modality banner + dedup/throttle indicators (FR-028)
- [X] T082 [P] [US3] Create `tui/src/components/primitive/StreamClosed.tsx` (FR-029)
- [X] T083 [P] [US3] Create `tui/src/components/primitive/AuthContextCard.tsx` — korea_tier primary label; NIST hint advisory-only (FR-030, FR-031)
- [X] T084 [P] [US3] Create `tui/src/components/primitive/AuthWarningBanner.tsx` (FR-032)
- [X] T085 [P] [US3] Create `tui/src/components/primitive/UnrecognizedPayload.tsx` with warning-log side effect; no structure inference (FR-033)
- [X] T086 [US3] Create `tui/src/components/primitive/index.tsx` exporting a `PrimitiveDispatcher` that switches on `envelope.kind` + subtype discriminator and routes to the 14 renderers; exhaustive switch compile-time checked against generated TS union (FR-008)
- [X] T087 [US3] Wire `PrimitiveDispatcher` into `tui/src/components/conversation/MessageList.tsx` so every `tool_result` frame in the store renders via the dispatcher
- [X] T088 [US3] Pull fixtures from #507 + #1052 recorded responses into `tui/tests/fixtures/{lookup,resolve_location,submit,subscribe,verify}/` per FR-035; document provenance in `tui/tests/fixtures/README.md`

**Checkpoint**: Every 5-primitive output variant renders in isolation via fixture + full dispatch works end-to-end.

---

## Phase 6: User Story 4 — Coordinator Phase + Per-Worker Status + Permission-Gauntlet Modal (Priority: P2)

**Goal**: Multi-agent surface from #13 / #14 is visible. Permission requests block input and round-trip through the gauntlet modal.

**Independent Test**: Inject scripted `coordinator_phase` + `worker_status` + `permission_request` IPC frames via `ink-testing-library`; assert phase indicator, status row, modal render; simulate citizen approval → `permission_response` emitted.

### Tests for User Story 4

- [X] T089 [P] [US4] Component test `tui/tests/components/coordinator/PhaseIndicator.test.tsx` — all 4 phase values; assert active streaming message is not disrupted (US4 scenario 1; FR-043)
- [X] T090 [P] [US4] Component test `tui/tests/components/coordinator/WorkerStatusRow.test.tsx` — role_id label + primitive iteration indicator (US4 scenario 2; FR-044)
- [X] T091 [P] [US4] Component test `tui/tests/components/coordinator/PermissionGauntletModal.test.tsx` — assert modal renders, all input blocks, `y` emits `permission_response: granted`, `n` emits `denied`; round-trip `request_id` (US4 scenarios 3, 4; FR-045, FR-046)
- [X] T092 [P] [US4] Integration test `tui/tests/fixtures/coordinator/three-specialist.jsonl` (scripted Transport + Health + Emergency scenario from #14) replayed via fixture bridge; assert all 3 worker rows visible concurrently + independent updates (US4 scenario 5; SC-7)

### Implementation for User Story 4

- [X] T093 [P] [US4] Lift `tui/src/components/coordinator/PhaseIndicator.tsx` from `restored-src/src/components/` coordinator phase component(s) with attribution header (FR-047)
- [X] T094 [P] [US4] Lift `tui/src/components/coordinator/WorkerStatusRow.tsx` from `restored-src/src/components/CoordinatorAgentStatus.tsx` + `AgentProgressLine.tsx` with attribution header (FR-044, FR-047)
- [X] T095 [P] [US4] Lift `tui/src/components/coordinator/PermissionGauntletModal.tsx` from `restored-src/src/components/ToolPermission*.tsx` + `BypassPermissionsModeDialog.tsx` with attribution header (FR-045)
- [X] T096 [P] [US4] Lift `tui/src/hooks/useCanUseTool.ts` from `restored-src/src/hooks/useCanUseTool.tsx` with attribution header
- [X] T097 [US4] Wire the coordinator frames into `tui/src/store/session-store.ts` reducer: `coordinator_phase` → overwrite `coordinator_phase`; `worker_status` → upsert worker; `permission_request` → set `pending_permission` (blocks input)
- [X] T098 [US4] Wire `PhaseIndicator` + `WorkerStatusRow` + `PermissionGauntletModal` into the root layout in `tui/src/components/conversation/MessageList.tsx` / `tui/src/entrypoints/tui.tsx`
- [X] T099 [US4] Emit `permission_response` IPC frame from modal's granted/denied callbacks; clear `pending_permission` in store reducer (FR-046)
- [X] T100 [US4] Create `tui/tests/fixtures/coordinator/three-specialist.jsonl` scripting Transport + Health + Emergency workers concurrently (SC-7)

**Checkpoint**: Scripted 3-specialist scenario runs end-to-end with visible phase + worker rows + approval modal.

---

## Phase 7: User Story 5 — Korean IME Input Module (Priority: P2)

**Goal**: Hangul composition works on macOS (Korean IME) and Linux (fcitx5 / ibus). Mid-composition Backspace deletes the partial syllable atomically. Strategy is codified in the ADR from T004.

**Independent Test**: Headless stdin injection of Hangul composition sequences (e.g., `ㅎ ㅏ ㄴ` → `한`) via `node --experimental-permission` harness; assert composed glyph is emitted.

### Tests for User Story 5

- [X] T101 [P] [US5] Headless IME test `tui/tests/hooks/useKoreanIME.test.ts` — inject `ㅎ + ㅏ + ㄴ` → assert `한` emitted as single codepoint; inject mid-composition Backspace → assert atomic partial-syllable deletion (US5 scenarios 1, 2; FR-015, FR-016)
- [X] T102 [P] [US5] CI precondition test `tui/tests/adr-precheck.test.ts` — assert `docs/adr/NNN-korean-ime-strategy.md` exists; fail build otherwise (US5 scenario 3; FR-014, FR-057)

### Implementation for User Story 5

- [X] T103 [US5] Based on ADR T004 outcome: if option (a) fork, update `tui/package.json` pin `"ink": "npm:@jrichman/ink@6.6.9"` + rerun `bun install` + regenerate lockfile; if option (b) readline, implement the stdlib readline hybrid in `tui/src/ipc/readline-bridge.ts` (KOSMOS-original) and keep Ink pin at `@^7`
- [X] T104 [US5] Create `tui/src/hooks/useKoreanIME.ts` strategy-selector hook reading `KOSMOS_TUI_IME_STRATEGY` env var; dispatch to fork-based `useInput` OR readline hybrid per ADR (FR-014)
- [X] T105 [US5] Create `tui/src/components/input/InputBar.tsx` consuming `useKoreanIME` hook; renders composition-state buffer + emits `user_input` frame on Enter (FR-015)
- [X] T106 [US5] Wire `InputBar` into `tui/src/entrypoints/tui.tsx` replacing any placeholder text input
- [X] T107 [P] [US5] Document chosen IME strategy in `tui/docs/korean-ime.md` with fallback instructions if the strategy fails on an uncommon terminal

**Checkpoint**: `한글` composed correctly on macOS + Linux; backspace deletes jamo atomically.

---

## Phase 8: User Story 6 — Session Persistence via IPC (Priority: P3)

**Goal**: TUI reads/writes sessions exclusively through backend IPC. Zero TUI-side session state.

**Independent Test**: `/save`, kill TUI, restart, `/resume <id>` → conversation history restored without re-streaming.

### Tests for User Story 6

- [X] T108 [P] [US6] Integration test `tui/tests/commands/session-roundtrip.test.ts` — `/save` emits `session_event.save`; `/sessions` renders list with id + timestamp + turn_count; `/resume <id>` restores prior turns in message list without re-streaming (US6 scenarios 1–3; FR-038)
- [X] T109 [P] [US6] Stateless-TUI invariant test `tui/tests/store/no-persistence.test.ts` — assert no file writes occur under `tui/` after any `session_event` (kill-and-restart simulation; US6 scenario 4; spec § Assumptions)
- [X] T110 [P] [US6] Python backend session test `tests/ipc/test_session_events.py` — verify `session_event: save|load|list|resume|new|exit` frames round-trip through existing Phase 1 JSONL store (FR-038)

### Implementation for User Story 6

- [X] T111 [P] [US6] Extend `src/kosmos/ipc/stdio.py` to route `session_event` frames to existing Phase 1 session store (`src/kosmos/session/`) without duplication
- [X] T112 [US6] Confirm store reducer handles `session_event.load` / `resume` by replaying historical messages into the message list WITHOUT triggering `assistant_chunk` re-render animation (US6 scenario 3)
- [X] T113 [P] [US6] Add `session_event.exit` handler in TUI triggering SIGTERM chain per FR-009

**Checkpoint**: Kill-and-restart cycle restores full conversation state via backend-only storage.

---

## Phase 9: User Story 7 — Performance: Virtualization + Double-Buffered Redraws (Priority: P3)

**Goal**: 1,000-message fixture replay at 100 ev/s holds ≤ 50 ms redraws, zero dropped frames, scrollback via `overflowToBackbuffer`.

**Independent Test**: Replay a 1,000-message fixture at 100 ev/s via stdin injection; assert no dropped frames + ≤ 50 ms per redraw.

### Tests for User Story 7

- [X] T114 [P] [US7] Perf test `tui/tests/components/conversation/VirtualizedList.test.tsx` — mount 1,000-message fixture; assert only the visible viewport re-renders on new-message append (US7 scenario 1; FR-048)
- [X] T115 [P] [US7] Perf test `tui/tests/components/conversation/overflowToBackbuffer.test.tsx` — conversation exceeds terminal height; assert scrollback works without re-rendering historical messages (US7 scenario 4; FR-052)
- [X] T116 [P] [US7] Store-selector test `tui/tests/store/useSyncExternalStore.test.ts` — append a chunk; assert only the affected `<StreamingMessage />` re-renders (US7 scenario 3; FR-050)

### Implementation for User Story 7

- [X] T117 [US7] Lift `tui/src/components/conversation/VirtualizedList.tsx` from `restored-src/src/components/` virtualization implementation with attribution header (FR-048)
- [X] T118 [US7] Add Gemini CLI's `overflowToBackbuffer` pattern on top of VirtualizedList, referencing `.references/gemini-cli/packages/cli/` for structure (FR-052) — KOSMOS-original integration; no attribution header to restored-src, but add a comment referencing Gemini CLI Apache-2.0 licensing
- [X] T119 [US7] Implement double-buffered redraw pattern in `tui/src/ink/renderer.ts` lift (already from T018); verify via component test that redraw-batch coalescing matches Claude Code behavior (FR-049)
- [X] T120 [US7] Wire `VirtualizedList` into `MessageList.tsx` replacing any naive list rendering

**Checkpoint**: 1,000-message replay passes perf thresholds; scrollback preserves history.

---

## Phase 10: Polish & Cross-Cutting Concerns

**Purpose**: Observability, final attribution compliance, documentation updates, release polish.

- [ ] T121 [P] Add `kosmos.ipc.frame` OTEL span emission in `src/kosmos/ipc/stdio.py` (child of session span from Spec 021) with attrs `kosmos.session.id`, `kosmos.frame.kind`, `kosmos.frame.direction`, `kosmos.ipc.latency_ms` (FR-053)
- [ ] T122 [P] Ensure OTEL span emission is fire-and-forget async (not on render thread) in `tui/src/ipc/bridge.ts` (FR-054)
- [ ] T123 [P] Keyboard-only navigation pass across all interactive components — `PermissionGauntletModal`, session list `<Select />`, CollectionList "Load more" — documented in `tui/docs/accessibility-checklist.md` (FR-055)
- [ ] T124 [P] Manual screen-reader smoke on macOS VoiceOver + Linux Orca documented in `tui/docs/accessibility-checklist.md` (FR-056)
- [ ] T125 [P] Final attribution audit — run `tui/scripts/diff-upstream.sh` + grep for missing `// Source:` headers across every file lifted to `tui/src/ink/`, `tui/src/commands/`, `tui/src/theme/`, `tui/src/components/coordinator/`, `tui/src/components/conversation/VirtualizedList.tsx`, `tui/src/hooks/` (FR-011, SC-9)
- [ ] T126 [P] Bun single-binary build via `bun build --compile --outfile dist/kosmos-tui src/main.tsx`; verify on macOS arm64 + Linux x64 per spec § Assumption "bun build --compile"
- [ ] T127 [P] Run `quickstart.md` end-to-end on macOS + Linux and document any deltas in `tui/docs/README.md`
- [ ] T128 [P] Smoke test SC-8 Scenario 1 (route safety) via the real Python backend + TUI; archive a screencast under `tui/docs/demos/` if available
- [ ] T129 [P] Smoke test a Phase 2 multi-ministry scenario end-to-end via TUI (SC-8) — fixture OK if live APIs unavailable
- [ ] T130 Update `specs/287-tui-ink-react-bun/spec.md` `NEEDS TRACKING` rows with the actual issue numbers created by `/speckit-taskstoissues` (Constitution Principle VI back-fill)
- [ ] T131 Final review: confirm all six Constitution principles (I–VI) still pass post-implementation in a new `specs/287-tui-ink-react-bun/checklists/final-review.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — T002/T003/T004 (ADRs) are authoring-only; T005 depends on T004; T012 depends on T005
- **Foundational (Phase 2)**: Depends on Phase 1 completion — BLOCKS all user stories
  - T013 → T014 → T015 → T016 → T017 chain for IPC codegen
  - T018 (Ink lift) + T019/T020 (diff tooling) + T021 (theme lift) + T022/T023/T024 are parallel-safe given different files
- **User Stories (Phase 3+)**: All depend on Phase 2; within Phase 2, T016 (generated types) + T023 (store) + T018 (Ink) are the critical-path for US1
- **Polish (Phase 10)**: Depends on US1–US7 substantially complete

### User Story Dependencies

- **US1 (P1)**: First after Phase 2. IPC bridge is foundational for everything else.
- **US2 (P1)**: After Phase 2. Command dispatcher is independent of US1 renderers; can run in parallel with US1 tail.
- **US3 (P1)**: After Phase 2 + US1's bridge. Renderer tests require IPC frames to exist as fixtures.
- **US4 (P2)**: After US1 + US3. Needs bridge + `UnrecognizedPayload` fallback to exist.
- **US5 (P2)**: After Phase 2. IME is input-path-isolated; does not depend on US3 renderers.
- **US6 (P3)**: After US2 (commands) + US1 (bridge).
- **US7 (P3)**: After US3 (components to virtualize). Perf hardens what US3 rendered.

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD enforced per FR-034).
- Generated types (T016) must exist before any component test referencing `IPCFrame`.
- Models / store reducers before services / dispatchers before entrypoints.
- Commit after each logical group.

### Parallel Opportunities

- Phase 1: T002/T003/T004 (three independent ADRs) + T008/T009/T010/T011 can all run in parallel.
- Phase 2: T018 (Ink lift) + T021 (theme lift) + T023 (store lift) + T024 (i18n) + T019/T020 (diff tooling) — all parallel.
- US3: T070–T085 (14 primitive components) + T054–T069 (14 component tests) — all parallel within the phase.
- US4: T093/T094/T095/T096 (four lifts) parallel; tests T089–T092 parallel.
- US1–US7 themselves: with Agent Teams, 3 specialists can own US3 / US4 / US7 concurrently after Phase 2.

---

## Parallel Example: User Story 3

```bash
# Launch all 14 primitive component tests in parallel:
bun test tui/tests/components/primitive/

# Launch all 14 primitive component implementations in parallel (different files):
Task: "Create tui/src/components/primitive/PointCard.tsx"
Task: "Create tui/src/components/primitive/TimeseriesTable.tsx"
Task: "Create tui/src/components/primitive/CollectionList.tsx"
# ... (14 total)
```

---

## Implementation Strategy

### MVP First (User Stories 1 + 2 + 3 — all P1)

1. Complete Phase 1: Setup (ADRs unblock lifts).
2. Complete Phase 2: Foundational (IPC contract + codegen + Ink + theme + store).
3. Complete Phase 3 (US1): IPC bridge + streaming chunk + crash detection + soak test.
4. Complete Phase 4 (US2): Commands + theme switch.
5. Complete Phase 5 (US3): 14 renderers + dispatcher.
6. **STOP and VALIDATE**: Run `quickstart.md` steps 1–5 end-to-end; run SC-8 Scenario 1 (route safety) smoke.
7. Ship MVP (all three P1 user stories).

### Incremental Delivery

1. Setup + Foundational → Foundation ready.
2. Add US1 → Bridge smoke + soak → Deploy.
3. Add US2 → Commands + theme → Deploy.
4. Add US3 → Primitives → Deploy. **← Natural MVP checkpoint**
5. Add US4 → Coordinator + permission gauntlet → Deploy.
6. Add US5 → IME → Deploy (must be done before Korean user demo).
7. Add US6 → Session persistence → Deploy.
8. Add US7 → Virtualization + perf → Deploy.
9. Polish phase → Final release.

### Parallel Team Strategy (Agent Teams — Sonnet)

After Phase 2 completes, at `/speckit-implement` time spawn 3 Teammates:

- Teammate A (Sonnet): US1 (IPC bridge + crash detection + soak).
- Teammate B (Sonnet): US3 (14 primitive renderers — highest parallelism within).
- Teammate C (Sonnet): US2 (dispatcher + theme + commands).

Once MVP ships, re-fan:

- Teammate A: US4 (coordinator surface).
- Teammate B: US5 (Korean IME).
- Teammate C: US6 + US7 (persistence + perf).

---

## Notes

- All TypeScript lives in `tui/` only — AGENTS.md hard rule.
- No new Python runtime dependencies — AGENTS.md hard rule (SC-008 Spec 031 parallel).
- Every lifted file carries the FR-011 attribution header; CI grep-check in T020.
- Fixtures come from #507 + #1052 recorded responses; never hand-crafted fictional data (FR-035).
- Commit after each task or logical group.
- At any checkpoint, stop and validate the current user story independently.
- IME strategy is ADR-gated (T004); downstream tasks T103–T107 cannot start until the ADR is approved.
