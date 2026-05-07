# Tasks 2641 · S6 Services swap-1 마무리

> Tasks generated from spec.md + plan.md. Each Task is a Sub-Issue candidate.
> [P] = parallel-safe (no dependency on other [P] tasks at the same phase).

## Phase 1 — Setup
- **T001**: Verify worktree state (`/Users/um-yunsang/KOSAX-w-2641` on
  `feat/2641-s6-services-swap1` branch, clean tree). Read project memory + spec.

## Phase 2 — Foundational (no [P], single edit)
_없음 — 본 spec 은 3 개 모듈이 완전 독립이라 Phase 2 생략._

## Phase 3 — User Story 1 [P] · api/client.ts duplicate fix (T002)
**Goal**: `getAnthropicClient` 함수 정의를 정확히 1 개로 축소.
**Independent**: 다른 두 sync 모듈과 zero shared symbols.
**Files**: `tui/src/services/api/client.ts` (1 file)

- **T002 [P]**: Remove the older Spec 2077 async/throw stub (lines 17-40 of
  current `tui/src/services/api/client.ts`). Keep:
  - SPDX header (lines 1-2)
  - `CLIENT_REQUEST_ID_HEADER` export (line 15)
  - SWAP/anti-anthropic-1p(2521) comment block (lines 42-46)
  - The Spec 2521 sync `getAnthropicClient(..._args: unknown[]): null` (lines 47-49)
  Also: rewrite the file-top header comment (lines 2-13) to consolidate
  rationale around the single retained stub. Add a `Spec 2641` reference
  citing the duplicate-fix decision.
  Verify: `bun typecheck` clean, `grep -c "function getAnthropicClient"
  tui/src/services/api/client.ts` returns `1`. (SC-001, SC-002)

## Phase 4 — User Story 2 [P] · teamMemorySync 박제 (T003 + T004)
**Goal**: claude.ts-style 박제 헤더 + dead-call gate on 4 entry-points.
**Independent**: settingsSync 와 zero shared file.
**Files**: `tui/src/services/teamMemorySync/index.ts` +
`tui/src/services/teamMemorySync/__tests__/dead-call-gate.test.ts` (2 files)

- **T003 [P]**: Insert 4-section 박제 header at the top of
  `tui/src/services/teamMemorySync/index.ts` (replace the existing `/** Team
  Memory Sync Service ... */` JSDoc block). Header must contain:
  - SPDX line
  - `Spec 2641 — byte-copy(2641) baseline restored from
    .references/claude-code-sourcemap/restored-src/services/teamMemorySync/index.ts`
  - `swap/llm-provider(2641)` describing `constants/oauth` inline stub
  - `swap/anti-anthropic-1p(2641)` describing `feature('TEAMMEM')=false` chain
  - "This file has zero live callers in tui/src after Spec 2641 (verified by
    callgraph audit: only sibling `teamMemSecretGuard` + `secretScanner` are
    imported elsewhere)."
  Then insert dead-call gate (throw) at the top of each:
  - `pullTeamMemory` (current line ~770)
  - `pushTeamMemory` (current line ~889)
  - `syncTeamMemory` (current line ~1153)
  - `isTeamMemorySyncAvailable` (current line ~762)
  Gate text per FR-003 (env override
  `KOSAX_ENABLE_DEAD_TEAM_MEM_SYNC`). (SC-005)

- **T004 [P]**: Create `tui/src/services/teamMemorySync/__tests__/dead-call-gate.test.ts`.
  Use `bun:test` describe/it. Test the 4 gated entry-points throw with the
  expected message when the env override is unset. Use a `delete process.env.KOSAX_ENABLE_DEAD_TEAM_MEM_SYNC`
  in `beforeEach`. (SC-004)

## Phase 5 — User Story 3 [P] · settingsSync 박제 (T005 + T006)
**Goal**: claude.ts-style 박제 헤더 + dead-call gate on 4 entry-points
(silent-skip variant — caller is critical boot path).
**Independent**: teamMemorySync 와 zero shared file.
**Files**: `tui/src/services/settingsSync/index.ts` +
`tui/src/services/settingsSync/__tests__/dead-call-gate.test.ts` (2 files)

- **T005 [P]**: Insert 4-section 박제 header at the top of
  `tui/src/services/settingsSync/index.ts`. Header content per FR-004
  (including "two callers (`cli/print.ts` + `commands/reload-plugins/`)
  survive but receive early-`false`/early-`void` from the dead-call gate"
  variant). Then insert dead-call gate (silent early-return) at the body
  start of each:
  - `uploadUserSettingsInBackground` (returns void)
  - `doDownloadUserSettings` (returns false; gate inserted before
    `feature('DOWNLOAD_USER_SETTINGS')` branch)
  - `downloadUserSettings` (gate inserted before `if (downloadPromise)`
    short-circuit; on gate-active path return `Promise.resolve(false)`)
  - `redownloadUserSettings` (returns `Promise.resolve(false)`)
  Gate text per FR-005 (env override `KOSAX_ENABLE_DEAD_SETTINGS_SYNC`).
  (SC-006)

- **T006 [P]**: Create `tui/src/services/settingsSync/__tests__/dead-call-gate.test.ts`.
  Test the 4 gated entry-points return early without throwing when the env
  override is unset. Use `delete process.env.KOSAX_ENABLE_DEAD_SETTINGS_SYNC`
  in `beforeEach`. Verify `_resetDownloadPromiseForTesting()` is callable.
  (SC-004)

## Phase 6 — Polish (Lead Opus solo)
- **T007**: Run `bun typecheck` → assert exit 0 + duplicate-symbol warning 0.
  (SC-001, SC-002)
- **T008**: Run `bun test` → assert no new failures vs main baseline.
  (SC-003, SC-004)
- **T009**: Layer 5 tmux capture-pane boot smoke
  (`scripts/tui-tmux-capture.sh /tmp/2641-smoke
  specs/2641-s6-services-swap1/scripts/smoke-boot.sh`). Author the
  smoke-boot.sh scenario script (boot → wait_for_pane "tool_registry" 30s →
  send `/help` Enter → wait_for_pane "Available commands" 10s → exit). Read
  3+ PNG keyframes via Read tool. Commit screenshots + snap-NNN-*.txt under
  `specs/2641-s6-services-swap1/`. (SC-007)
- **T010**: Verify SC-008 (zero new runtime deps) by checking
  `tui/package.json` + `pyproject.toml` diff = empty.
- **T011**: Verify SC-009 (≤ 10 file changes) via `git diff --stat main`.
- **T012**: Commit + push + open PR with `Closes #2641` body. Watch CI.
  Address Codex P1.

## Dependencies
- T002, T003, T004, T005, T006 are independent (different files / different
  modules) → all `[P]`.
- T003 must complete before T004 (test asserts on T003's gate behaviour).
  In practice both go to the same teammate so this is intra-teammate
  ordering, not a parallelism constraint.
- T005 must complete before T006 (same reason).
- T007 ~ T012 require all of T002-T006 to be merged/staged.

## File budget
- T002: 1 file (`api/client.ts`)
- T003+T004: 2 files (`teamMemorySync/index.ts`, `__tests__/dead-call-gate.test.ts`)
- T005+T006: 2 files (`settingsSync/index.ts`, `__tests__/dead-call-gate.test.ts`)
- T009: 1 script + 3+ PNG + 2+ txt under `specs/2641-s6-services-swap1/`
- Total: 5 source files + spec dir artifacts. Within ≤ 10 budget. (SC-009)
