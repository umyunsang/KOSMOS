---

description: "Task list for Epic #1633 — P1+P2 Dead code elimination + Anthropic→FriendliAI migration"
---

# Tasks: P1+P2 · Dead code elimination + Anthropic → FriendliAI migration

**Input**: Design documents from `/specs/1633-dead-code-friendli-migration/`
**Prerequisites**: [spec.md](./spec.md), [plan.md](./plan.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/llm-client.md](./contracts/llm-client.md), [quickstart.md](./quickstart.md)
**Epic**: [#1633](https://github.com/umyunsang/KOSMOS/issues/1633)
**Branch**: `1633-dead-code-friendli-migration`

**Tests**: Test tasks are included — the spec's SC-001..SC-010 each require a verifiable check, and the contract's fail-closed + IPC-protocol invariants need regression coverage.

**Organization**: Tasks are grouped by user story (US1..US4 from spec.md) so that each story can be implemented, tested, and if needed, merged independently. Within a story, order follows the plan's dependency graph: types → skeleton → rewires that depend on the skeleton → deletions that depend on the rewires → tests.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete prior tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- File paths are **absolute from repo root** and reflect the real layout (not Epic body's `services/services/*` typo — see research.md Finding A).

## Path conventions

- TypeScript TUI: `tui/src/`
- Python backend: `src/kosmos/`
- Tests (TS): `tui/test/` (Bun + `bun:test`)
- Tests (Python): `tests/` (pytest)

---

## Phase 1: Setup

- [ ] T001 Verify branch is `1633-dead-code-friendli-migration` and `.specify/feature.json` points to `specs/1633-dead-code-friendli-migration`; run `bun install` under `tui/` and `uv sync` at repo root to confirm baseline compiles after P0 (#1632) merge.

---

## Phase 2: Foundational (Blocking prerequisites)

**Purpose**: Introduce the TS LLM type shim + stub client **before** any Anthropic SDK import is stripped. Without these two files, `query.ts` and `QueryEngine.ts` lose their type surface and the TUI stops compiling.

**⚠️ CRITICAL**: No user-story work can begin until T002 + T003 are merged or staged.

- [ ] T002 [P] Create `tui/src/ipc/llmTypes.ts` with `KosmosRole`, `KosmosContentBlockParam` (Text / ToolUse / ToolResult variants), `KosmosMessageParam`, `KosmosToolDefinition`, `KosmosMessageStreamParams`, `KosmosUsage`, `KosmosRawMessageStreamEvent`, `KosmosMessageFinal` per [contracts/llm-client.md § 2](./contracts/llm-client.md). No runtime behavior; type-only exports. (FR-001, FR-017)
- [ ] T003 Create `tui/src/ipc/llmClient.ts` exporting the `LLMClient` class skeleton (constructor accepting `{ bridge, model, sessionId }`, `stream()` returning a throwing async generator, `complete()` throwing `not implemented`, and `LLMClientError` subclass). This is the import target for T004/T005; full implementation arrives in US1. (FR-007, FR-017)

**Checkpoint**: TypeScript compiles with `llmTypes.ts` + `llmClient.ts` present. `bun test` still passes at the P0 floor (≥ 540 passing).

---

## Phase 3: User Story 1 — Citizen receives K-EXAONE streaming response (Priority: P1) 🎯 MVP

**Goal**: End-to-end LLM turn from TUI REPL input through stdio IPC to Python backend to FriendliAI `EXAONE-236B-A23B` and back as streaming tokens within 5 seconds.

**Independent Test**: With `KOSMOS_FRIENDLI_TOKEN` set, run `bun run tui/src/main.tsx`, type a citizen query, observe first token within 5 s. Without the env var, observe a bilingual fail-closed error envelope and non-zero exit. (Quickstart Scenarios 1 & 2 · SC-001)

### Implementation for User Story 1

- [ ] T004 [P] [US1] In `tui/src/query.ts`, replace `import type { ... } from '@anthropic-ai/sdk/resources/index.mjs'` with imports from `tui/src/ipc/llmTypes.ts`. Preserve agentic-loop control flow (rewrite-boundary rule, Constitution I). (FR-001, FR-017)
- [ ] T005 [P] [US1] In `tui/src/QueryEngine.ts`, replace `import type { ContentBlockParam } from '@anthropic-ai/sdk/resources/messages.mjs'` with `import type { KosmosContentBlockParam as ContentBlockParam } from './ipc/llmTypes.js'`. Rewire any `Stream` / `BetaMessageStreamParams` imports to their Kosmos counterparts. (FR-001, FR-017)
- [ ] T006 [US1] In `tui/src/utils/model/model.ts`, modify `getDefaultMainLoopModel()` (line ~206) to return the string literal `"LGAI-EXAONE/K-EXAONE-236B-A23B"`. Remove any branch that reads `getAntModelOverrideConfig()?.defaultModel` or anthropic-scope fallbacks. The constant MUST be the sole production return value (Contract G3: model ID is a single constant in prod builds; tests may pass a mock through the LLMClient constructor). (FR-011, SC-010, Contract G3)
- [ ] T007 [US1] In `tui/src/ipc/llmClient.ts`, implement `stream()`: construct `UserInputFrame` with fresh `makeUUIDv7()` correlation_id, send via `bridge.sendFrame()`, consume inbound `AssistantChunkFrame` / `ToolCallFrame` stream for that correlation_id, translate to `KosmosRawMessageStreamEvent` per [data-model.md](./data-model.md) mapping, finalize on `done=true` trailer. On `BackpressureSignalFrame(kind=llm_rate_limit)`, pause consumption for `retry_after_ms` before resuming the same generator — **do NOT** retry the full turn (Python backend owns retry per Spec 019; Contract G5). (FR-007, FR-017, Contract G1, G2, G5, G6)
- [ ] T008 [US1] In `tui/src/ipc/llmClient.ts`, implement `complete()` as a thin wrapper that awaits `stream()` to exhaustion and returns `KosmosMessageFinal` (accumulated content blocks + stop_reason + usage). (Contract § 1.1)
- [ ] T009 [US1] In `tui/src/ipc/llmClient.ts`, wire OTEL span `gen_ai.client.invoke` with attributes `gen_ai.system="friendli_exaone"`, `gen_ai.operation.name="chat"`, `gen_ai.request.model=<model>`, `gen_ai.request.max_tokens=<params.max_tokens>`, `kosmos.correlation_id=<envelope.correlation_id>`, `kosmos.session_id=<sessionId>`. Populate `gen_ai.usage.input_tokens` / `output_tokens` from final trailer. (FR-022, SC-008, Contract § 4)
- [ ] T010 [US1] In `tui/src/ipc/llmClient.ts`, attach `kosmos.prompt.hash` span attribute by reading the hash from the backend's first response frame metadata (propagated via `PromptLoader` on Python side per Spec 026). If hash is absent, surface a warning log but do not fail — Spec 026 boot-time hash check already fails closed if manifest mismatch. (FR-022, SC-008)
- [ ] T011 [US1] In `tui/src/entrypoints/init.ts`, add a pre-bridge env-var check: if neither `FRIENDLI_API_KEY` nor `KOSMOS_FRIENDLI_TOKEN` is set, print bilingual error envelope to stderr (`"FRIENDLI_API_KEY 환경변수가 필요합니다 / FRIENDLI_API_KEY environment variable required"`) and exit with status 1 before any bridge.ts invocation. No Anthropic credential lookup anywhere. (FR-004 Edge case, Contract § 5)
- [ ] T012 [US1] In `tui/src/entrypoints/init.ts`, remove the `initializeTelemetryAfterTrust(...)` call and replace with a KOSMOS OTEL init that instantiates the OTLP exporter against Spec 021's default endpoint and sets `deployment.environment` from `KOSMOS_ENV`. (FR-016)
- [ ] T013 [US1] In `tui/src/services/api/withRetry.ts`, strip the Anthropic-specific 401/529 branches and set the retry target set to `{ 429, 500, 502, 503, 504 }`. Keep exponential backoff (1 s / 2 s / 4 s) and add `Retry-After` header honouring. (FR-018, Research Decision 7)
- [ ] T014 [US1] In `tui/src/services/api/errors.ts` + `errorUtils.ts`, remove Anthropic-specific codes (`invalid_request_error` Anthropic variant, `overloaded_error`, `permission_error` strings tied to anthropic surface) and re-map to KOSMOS envelope classes `llm`/`tool`/`network` per the Research Decision 6 matrix. Keep error-class structure + user-friendly message mapping. (FR-019, Research Decision 6)
- [ ] T015 [US1] In `tui/src/services/api/promptCacheBreakDetection.ts`, rewire the usage-field parsing to read `prompt_tokens_details.cached_tokens` (FriendliAI OpenAI-compat field) instead of Anthropic's `cache_creation_input_tokens` / `cache_read_input_tokens`. Detection logic (drop-between-turns threshold) unchanged. (FR-020, Research Decision 3)
- [ ] T016 [US1] Delete `tui/src/services/api/claude.ts` (its role is fully replaced by `llmClient.ts`). Update any remaining callers to import from `tui/src/ipc/llmClient.ts`. (FR-007, FR-008)
- [ ] T017 [US1] Delete `tui/src/services/api/client.ts` (direct FriendliAI HTTPS client superseded by IPC bridge). Update callers. (FR-007)

### Tests for User Story 1

- [ ] T018 [P] [US1] Add `tui/test/ipc/llmClient.test.ts`: mock `IPCBridge`, emit a canned `AssistantChunkFrame` sequence, assert `stream()` yields `message_start` + N × `content_block_delta` + `content_block_stop` + `message_delta` + `message_stop` in order with accumulated text equal to concatenated deltas. (FR-017, Contract G1/G2/G6)
- [ ] T019 [P] [US1] Add `tui/test/ipc/llmClient.error.test.ts`: mock `ErrorFrame(class=llm, code=auth)`, assert `stream()` throws `LLMClientError` with `class='llm'` + `code='auth'` and does not retry. (FR-019, Contract G4)
- [ ] T020 [P] [US1] Add `tui/test/entrypoints/failClosed.test.ts`: simulate `FRIENDLI_API_KEY` unset, invoke the init path, assert process.exit(1) with bilingual stderr message. Assert zero imports of `@anthropic-ai/sdk` in `require.cache`. (FR-004 Edge case, SC-009 partial)
- [ ] T021 [P] [US1] Add `tui/test/ipc/otelSpan.test.ts`: with a fake OTEL SDK recorder, invoke `LLMClient.complete()`, assert a `gen_ai.client.invoke` span is recorded with non-empty `kosmos.prompt.hash` attribute and `gen_ai.request.model = "LGAI-EXAONE/K-EXAONE-236B-A23B"`. (SC-008, SC-010)

**Checkpoint**: User Story 1 functional. A citizen sees a K-EXAONE answer within 5 s. `@anthropic-ai/sdk` is still importable in some files (US2 handles full elimination), but the LLM call path no longer depends on it.

---

## Phase 4: User Story 2 — `@anthropic-ai/sdk` runtime 0 + `main.tsx` ≤ 2,500 lines (Priority: P1)

**Goal**: Strip all remaining Anthropic-SDK import sites, delete CC version migrations, delete Anthropic-internal API endpoints, shrink `main.tsx` by removing ant-guards and obsolete boot hooks.

**Independent Test**: From a clean checkout run the five grep invariants in [quickstart.md § Scenario 3](./quickstart.md); each returns 0 matches. `wc -l tui/src/main.tsx` ≤ 2500. `bun test` passes ≥ 540. (SC-002, SC-003, SC-004, SC-005, SC-006, SC-007)

### CC version migrations — delete (FR-002, SC-004)

- [ ] T022 [US2] Delete all eleven CC version-migration files under `tui/src/migrations/` and update `tui/src/migrations/index.ts` (if present) to drop their exports. Targets:
  - `migrateAutoUpdatesToSettings.ts`
  - `migrateBypassPermissionsAcceptedToSettings.ts`
  - `migrateEnableAllProjectMcpServersToSettings.ts`
  - `migrateFennecToOpus.ts`
  - `migrateLegacyOpusToCurrent.ts`
  - `migrateOpusToOpus1m.ts`
  - `migrateReplBridgeEnabledToRemoteControlAtStartup.ts`
  - `migrateSonnet1mToSonnet45.ts`
  - `migrateSonnet45ToSonnet46.ts`
  - `resetAutoModeOptInForDefaultOffer.ts`
  - `resetProToOpusDefault.ts`
  Verify: `ls tui/src/migrations/migrate*.ts tui/src/migrations/reset*.ts 2>/dev/null | wc -l` → 0.

### Anthropic-internal API endpoints — delete (FR-008)

- [ ] T023 [US2] Delete all Anthropic-internal API endpoint files under `tui/src/services/api/`. Targets:
  - `bootstrap.ts` (Anthropic-side bootstrap handshake; init-path caller handled by T012)
  - `usage.ts` (Anthropic usage/billing endpoint)
  - `overageCreditGrant.ts`
  - `referral.ts`
  - `adminRequests.ts`
  - `grove.ts` (Grove is Anthropic-internal; remaining `commands/*` imports resolved in T045)
  Verify: none of these files exist under `tui/src/services/api/` after the task. Any callers surfaced by the tsc pass are fixed in T045.

### `filesApi.ts` — stub out (FR-009, Research Decision 2)

- [ ] T024 [US2] In `tui/src/services/api/filesApi.ts`, replace the Anthropic-Public-Files implementation with a rejecting no-op stub that exports the same symbols (`downloadFile`, `uploadFile`) returning `Promise.reject(new Error("Files API removed in Epic #1633; replacement handled in P3 tool system."))`. Remove `axios` and all `ANTHROPIC_*` environment references. Keep file (not delete) so tool files (`FileWriteTool`, `FileEditTool`, `NotebookEditTool`, `GlobTool`, `PowerShellTool/pathValidation`) compile unchanged until Epic #1634. (Contract § 6)

### Model / OAuth / betas / policy config — delete (FR-010..FR-015)

- [ ] T025 [P] [US2] Delete `tui/src/utils/model/antModels.ts` (Ant-only GrowthBook override; unused after T006). (FR-011, Finding C)
- [ ] T026 [P] [US2] Delete `tui/src/utils/modelCost.ts` (Anthropic token pricing table; KOSMOS uses Python `UsageTracker`). (FR-012)
- [ ] T027 [P] [US2] Delete `tui/src/utils/betas.ts` and `tui/src/constants/betas.ts` (both carry Anthropic beta-header codes; Finding C adds the constants/-side sibling). (FR-013)
- [ ] T028 [US2] In `tui/src/constants/constants/oauth.ts` (or wherever the Anthropic OAuth constants live — verify path via grep), remove `TOKEN_URL`, `CLIENT_ID`, `REDIRECT_URI`, and any `ANTHROPIC_*` constants. If the file becomes empty, delete it and scrub imports. (FR-010)

### Compile scrub — `@anthropic-ai/sdk` import 0 (FR-001, SC-002)

- [ ] T029 [US2] Sweep all remaining `import ... from '@anthropic-ai/sdk/...'` sites across `tui/src/**/*.{ts,tsx}` (excluding `__mocks__/` and `*.test.*`). Replace with `tui/src/ipc/llmTypes.ts` equivalents or remove dead imports tied to just-deleted files. Verify with `grep -rln '@anthropic-ai/sdk' tui/src --include='*.ts' --include='*.tsx' | grep -v '__mocks__\|\.test\.\|\.spec\.'` → 0 matches. (FR-001, SC-002)

### `main.tsx` reduction (FR-003, SC-003, SC-006)

- [ ] T030 [US2] In `tui/src/main.tsx`, sweep every `if (USER_TYPE === "ant")` and `if (ANT_INTERNAL)` guard, remove the Anthropic-side branch of each, and remove login/logout + analytics/telemetry boot wiring (calls to `getOauthAccountInfo`, keychain prefetch, login command registration, GrowthBook / Datadog / FirstParty / session-tracing init). Verify: `grep -c 'ANT_INTERNAL\|=== "ant"' tui/src/main.tsx` → 0, and `wc -l tui/src/main.tsx` ≤ 2,500 (target 2,000). Single sequential task (shared file). (FR-003, FR-004, FR-005, SC-003, SC-006)

### Tests for User Story 2

- [ ] T031 [P] [US2] Add `tui/test/invariants/grep.test.ts` (or equivalent ci-invariant harness): shell out to `grep` for SC-002 / SC-004 / SC-005 / SC-006, each expected to return 0 matches, AND `wc -l tui/src/main.tsx ≤ 2500` for SC-003. Exits non-zero if any invariant fails. (SC-002, SC-003, SC-004, SC-005, SC-006)
- [ ] T032 [US2] Run `bun test` full suite under `tui/`, confirm ≥ 540 passing and 0 failing. Document pass count in PR body. (SC-007)

**Checkpoint**: `@anthropic-ai/sdk` is a dead dependency in the runtime graph, 11 migrations are gone, Anthropic-internal APIs are gone, `main.tsx` fits the ceiling. US2 is complete.

---

## Phase 5: User Story 3 — CC telemetry · auth · teleport removed (Priority: P2)

**Goal**: Strip the remaining dead-code groups — CC analytics sinks, telemetry modules, secure storage, OAuth flow, remote/teleport session management, policy-limits, Anthropic MCP integration, internal logging.

**Independent Test**: `ls` / `find` show the deletions; `bun test` regressions stay at 0; `lsof -p <tui-pid>` shows no HTTPS connection to Anthropic / Datadog / GrowthBook / Statsig domains when TUI is running. (SC-009, FR-004..FR-006)

### Analytics + telemetry — delete (FR-004)

- [ ] T033 [US3] Delete the entire `tui/src/services/analytics/` directory (7 files: `growthbook.ts`, `datadog.ts`, `firstPartyEventLogger.ts`, `sink.ts`, `sinkKillswitch.ts`, `metadata.ts`, `index.ts`). Scrub any external imports exposed by tsc after deletion.
- [ ] T034 [US3] Delete the entire `tui/src/utils/telemetry/` directory (5 files: `sessionTracing.ts`, `betaSessionTracing.ts`, `instrumentation.ts`, `pluginTelemetry.ts`, `skillLoadedEvent.ts`).
- [ ] T035 [P] [US3] Delete `tui/src/services/internalLogging.ts` and `tui/src/types/types/generated/events_mono/` directory (generated Anthropic analytics event types).

### CC auth — delete (FR-005)

- [ ] T036 [US3] Delete CC-auth surface: `tui/src/utils/auth.ts`, the entire `tui/src/utils/secureStorage/` directory (6 files: `keychainPrefetch.ts`, `macOsKeychainStorage.ts`, `macOsKeychainHelpers.ts`, `fallbackStorage.ts`, `plainTextStorage.ts`, `index.ts`), the entire `tui/src/services/oauth/` directory (5 files: `client.ts`, `index.ts`, `auth-code-listener.ts`, `crypto.ts`, `getOauthProfile.ts`), and the `tui/src/commands/login/` and `tui/src/commands/logout/` directories. Scrub remaining imports.

### CC teleport / remote — delete (FR-006)

- [ ] T037 [US3] Delete the entire `tui/src/remote/` directory (4 files: `RemoteSessionManager.ts`, `remotePermissionBridge.ts`, `sdkMessageAdapter.ts`, `SessionsWebSocket.ts`).
- [ ] T038 [US3] Delete remaining teleport / remote surface: `tui/src/services/remoteManagedSettings/securityCheck.tsx`, `tui/src/utils/teleport.tsx`, `tui/src/utils/teleport/gitBundle.ts` (+ empty parent dir), `tui/src/utils/background/remote/remoteSession.ts` + `preconditions.ts` (+ empty parent dir), `tui/src/components/TeleportResumeWrapper.tsx`, `tui/src/hooks/useTeleportResume.tsx`.

### Policy limits + MCP Anthropic — delete (FR-014, FR-015)

- [ ] T039 [US3] Delete policy-limit surface: the entire `tui/src/services/policyLimits/` directory (`index.ts`, `types.ts`), `tui/src/services/claudeAiLimits.ts`, `tui/src/services/claudeAiLimitsHook.ts` (Finding C), `tui/src/services/mcp/claudeai.ts` (remove the `mcp/` dir if last file). (FR-014, FR-015)

### Slash command registry cleanup (Research Decision 9)

- [ ] T040 [US3] Strip `/login` and `/logout` registrations: `tui/src/commands.ts` slash registry, autocomplete in `tui/src/screens/REPL.tsx`, help entries in `tui/src/commands/help.tsx`. Smoke-check Spec 035 onboarding (`tui/src/onboarding/*`) still terminates at `terminal-setup` and references no deleted login command. No UX change expected.

### Tests for User Story 3

- [ ] T041 [P] [US3] Add `tui/test/invariants/deletions.test.ts`: assert directories `services/analytics`, `utils/telemetry`, `utils/secureStorage`, `services/oauth`, `remote` do NOT exist under `tui/src/`. Assert files `antModels.ts`, `auth.ts`, `betas.ts`, `claudeai.ts` do NOT exist. (FR-004..FR-006, FR-014, FR-015)
- [ ] T042 [P] [US3] Add `tui/test/invariants/noExternalEgress.smoke.ts`: spawn TUI under a fake-OTLP stub, run a 10-second session with one query, assert `lsof`-equivalent output shows HTTPS connections only to `*.friendli.ai` domains. Expect zero connections to `*.anthropic.com`, `*.datadoghq.com`, `*.growthbook.io`, `*.statsig.com`. (SC-009)

**Checkpoint**: All CC-internal surfaces gone. KOSMOS citizens cannot trip into Anthropic-account, telemetry-sink, remote-session code paths. Citizen telemetry flows to KOSMOS OTEL + local Langfuse (Spec 021/028) only.

---

## Phase 6: User Story 4 — System prompt via PromptLoader (Priority: P3)

**Goal**: Ensure the system prompt shipped to K-EXAONE originates from `prompts/system_v1.md` via Spec 026 `PromptLoader`, not an inline TS constant. Emit `kosmos.prompt.hash` attribute on every LLM invocation span.

**Independent Test**: Unit test that mocks `LLMClient.stream()` and asserts the `system` field in the outbound `UserInputFrame` matches `prompts/system_v1.md` content byte-for-byte, and the OTEL span carries `kosmos.prompt.hash` equal to that file's SHA-256. (SC-008, FR-021, FR-022)

- [ ] T043 [US4] In `tui/src/constants/prompts.ts` (or wherever a hard-coded system-prompt string lives), remove the inline string and replace with a runtime call that retrieves the system prompt from the Python backend's `PromptLoader` via a handshake-time IPC metadata field. Update `tui/src/ipc/bridge.ts` so the session handshake frame carries `system_prompt` + `system_prompt_hash` fields populated by the Python backend (TUI caches; no new frame kind). Verify `LLMClient.stream()` passes the cached system prompt as `params.system` and populates `kosmos.prompt.hash` span attribute from the cached hash (T009 already wired; this task cross-checks the source). (FR-021, FR-022, SC-008)
- [ ] T044 [P] [US4] Add `tui/test/prompt/loader.test.ts`: mock the handshake response with a known system-prompt string + hash, invoke LLMClient.stream(), assert the UserInputFrame payload includes the exact system string and the span attribute matches the hash. (FR-021, FR-022, SC-008)

**Checkpoint**: Every LLM turn now cites a hash-verified prompt. Langfuse UI can group sessions by prompt version.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T045 [P] Run `bun run check:types` (or equivalent TypeScript strict typecheck) on `tui/`. Zero type errors expected. (FR-023 regression)
- [ ] T046 [P] Regression — Spec 032 resume smoke: kill Python backend mid-stream, verify TUI emits `ResumeRequestFrame` with `last_seen_correlation_id`, backend re-streams buffered frames, answer completes without duplicate tokens. (Quickstart Scenario 4)
- [ ] T047 [P] CI workflow update — append the Epic #1633 invariants block from [quickstart.md § CI regression harness](./quickstart.md) to the existing `.github/workflows/ci.yml` (or the CC-port job). Ensure the five grep invariants + `wc -l` invariant + `bun test` floor all run on every PR touching `tui/` or `specs/`.
- [ ] T048 Capture `bun run tui` screenshots (cold boot + REPL with a K-EXAONE answer streaming) and attach to PR body as US1 visual evidence. (SC-001 visual · FR-024)
- [ ] T049 Update `README.md` Status line if Epic #1633 PR merges: bump from "P0 merged" to "P0+P1+P2 merged". No other README changes. (Docs propagation PR #1652 already covered canonical tree propagation.)
- [ ] T050 Open PR with `Closes #1633` in the body (Epic only — per AGENTS.md `PR close rule`, never list Task sub-issues). Attach bun test count, `wc -l` result, grep-invariant outputs, and the bilingual fail-closed screenshot.

---

## Dependencies between stories

```
Setup (T001)
  └─ Foundational (T002, T003) ── blocks all stories
      ├─ US1 (T004..T021) ── citizen K-EXAONE path
      │    └─ blocks US2 T029 (full @anthropic-ai/sdk sweep needs llmTypes first)
      ├─ US2 (T022..T032) ── dead-code + main.tsx reduction
      ├─ US3 (T033..T042) ── CC telemetry/auth/teleport
      │    └─ largely independent of US1/US2
      └─ US4 (T043..T044) ── PromptLoader wiring
           └─ builds on US1's LLMClient (T009 OTEL hook)
Polish (T045..T050) ── after every story's Checkpoint passes
```

### Parallel execution opportunities

- **Phase 2 → US1**: T004 + T005 are `[P]` (different files). T007-T010 implement different methods of the same file so sequential. T013-T015 independent-file rewires (`[P]` eligible once LLMClient skeleton T003 lands).
- **US2**: T022-T028 are mostly `[P]` (independent file/dir drops). T029 (SDK sweep) sequential — touches the whole tree. T030 (main.tsx) sequential — single file.
- **US3**: T033-T042 are mostly `[P]` (independent dirs + files). T040 (slash-command cleanup) depends on T036 having finished deleting the `commands/login|logout/` dirs.
- **US4**: T043 sequential (shared bridge.ts); T044 test is `[P]`.
- **Polish**: T045-T048 `[P]`; T049-T050 sequential at the end.

---

## Implementation strategy — MVP first, incremental delivery

1. **Setup + Foundational** (T001-T003) — 1-2 hours. Must merge-or-stage first.
2. **MVP = US1** (T004-T021) — 1-2 days. At this point a citizen can talk to K-EXAONE end-to-end. This alone is a shippable increment if the remaining dead code is considered deferred.
3. **US2** (T022-T032) — 2-3 days. Dead-code deletion batches (T022-T028) are parallel-safe; T029 SDK sweep + T030 main.tsx reduction are the highest-care single-file sequential work. Bun test regression floor enforced at T032.
4. **US3** (T033-T042) — 1 day (mostly parallel deletions, a few consolidated into single tasks per directory).
5. **US4** (T043-T044) — half a day.
6. **Polish** (T045-T050) — half a day (CI wiring, screenshots, PR authoring).

**Total**: ~5-7 days for one engineer serial; ~3-4 days with 3 parallel Teammates (Agent Teams, spawned at `/speckit-implement`).

---

## Sub-Issue budget check (AGENTS.md `Sub-Issue 100-cap`)

- **Task count**: 50 checkboxes (T001..T050).
- **Consolidation applied**: 11 CC migration deletions → 1 task (T022); 6 Anthropic-internal API deletions → 1 task (T023); 7 analytics deletions → 1 task (T033); 5 telemetry deletions → 1 task (T034); 6 secureStorage + 5 OAuth + 2 login/logout dir deletions → 1 task (T036); 4 remote dir + 6 peripheral teleport files → 2 tasks (T037, T038); 4 policy+MCP deletions → 1 task (T039); 3 slash-registry edits → 1 task (T040); main.tsx sweep (4 sub-steps) → 1 task (T030); PromptLoader wiring (3 sub-steps) → 1 task (T043).
- **Budget status**: **50 ≤ 90 (soft) ≤ 100 (hard)**. **PASS** — 40-slot headroom for mid-cycle Task additions or `[Deferred]` placeholders.
- **File-level auditability**: preserved via bullet-list sub-items inside consolidated tasks (e.g. T022 lists all 11 migration files). Code-review diff is still file-by-file; the consolidation is only at the GitHub Sub-Issue layer.

## Notes

- Every file-path reference in this document was verified against the real repository layout (research.md Finding A: single `services/`, not `services/services/`).
- `getDefaultMainLoopModel()` line number (~206) is approximate; verify via `grep -n 'export function getDefaultMainLoopModel' tui/src/utils/model/model.ts` before editing.
- Spec 032 resume semantics (T046) already covered by existing regression suite under `tui/test/ipc/` — T046 adds a specific cold-kill scenario rather than duplicating basic-resume coverage.
- Python backend (`src/kosmos/llm/client.py`) is unchanged in this Epic per plan § Summary — model ID `EXAONE-236B-A23B` already matches.
