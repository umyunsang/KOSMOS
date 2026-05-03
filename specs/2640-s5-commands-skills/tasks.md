---
description: "Task list for Epic #2640 — S5 Commands/Skills 정리"
---

# Tasks: S5 Commands/Skills 정리 — claude-api/ + P0 stub + sourcemap gap

**Input**: `specs/2640-s5-commands-skills/{spec.md,plan.md}`

**Tests**: pre-existing `bun test` baseline 유지 + Layer 5 tmux capture-pane 추가. unit test 신규 작성 0 (cleanup-only epic).

**Organization**: 3 User Stories 병렬 가능. Phase 1 (Setup) + Phase 2 (Foundational, 0 task) → Phase 3 (US1 Skills) ∥ Phase 4 (US2 P0 stubs) ∥ Phase 5 (US3 gap-3 박제) → Phase 6 (Verification + PR).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User Story (US1 = Skills, US2 = P0 stubs, US3 = gap-3 박제)
- Paths absolute relative to worktree root `/Users/um-yunsang/KOSMOS-w-2640`.

---

## Phase 1: Setup (Shared Infrastructure)

- [ ] **T001** Worktree + branch 확인. `git status` clean (worktree 이미 생성됨). `git branch --show-current` = `feat/2640-s5-commands-skills`.

---

## Phase 2: Foundational (Blocking Prerequisites)

본 epic 은 cleanup-only — foundational 변경 0. **Phase 2 skip**.

---

## Phase 3: User Story 1 — Skills bundle 제거 (Priority: P1)

**Goal**: Anthropic SDK skill bundle (claude-api/ + verify/ + 4 dispatchers) 일괄 제거.

**Independent Test**: `find tui/src/skills/bundled/claude-api -type f | wc -l` = 0, `find tui/src/skills/bundled/verify -type f | wc -l` = 0. `bun typecheck` PASS.

- [ ] **T010** [P] [US1] `git rm -r tui/src/skills/bundled/claude-api/` (51 파일 일괄 삭제 — 26 .md.ts + 22 .md + nested subdirs).
- [ ] **T011** [P] [US1] `git rm -r tui/src/skills/bundled/verify/` (3 파일: SKILL.md.ts + examples/cli.md.ts + examples/server.md.ts).
- [ ] **T012** [P] [US1] `git rm tui/src/skills/bundled/claudeApi.ts tui/src/skills/bundled/claudeApiContent.ts tui/src/skills/bundled/verify.ts tui/src/skills/bundled/verifyContent.ts` (4 dispatcher 파일).
- [ ] **T013** [US1] `tui/src/skills/bundled/index.ts` 정리: (a) `import { registerVerifySkill } from './verify.js'` 라인 제거, (b) `registerVerifySkill()` 호출 라인 제거, (c) `if (feature('BUILDING_CLAUDE_APPS')) { ... registerClaudeApiSkill() ... }` 블록 제거, (d) 박제 헤더 추가: `// KOSMOS-2640: claude-api + verify bundled skills removed — Anthropic SDK docs out of scope (Initiative #2636 / Epic #2640).`
- [ ] **T014** [US1] `bun typecheck` 통과 검증 (T010-T013 후). 회귀 시 import resolution 에러 fix.
- [ ] **T015** [US1] grep 검증: `grep -rE "from.*['\"].*claude-api[/'\"]|from.*['\"].*claudeApiContent|from.*['\"].*verifyContent|registerClaudeApiSkill|registerVerifySkill" tui/src/` 0 hit (KOSMOS-2640 박제 코멘트 라인 제외).

**Checkpoint US1**: Skills bundle cleanup 완료. `bun typecheck` PASS, grep clean.

---

## Phase 4: User Story 2 — P0 auto-stub commands 20개 삭제 (Priority: P1)

**Goal**: 20 P0 stub command 디렉토리 제거 + `commands.ts` import / array 정리 + nested `commands/clear/clear/` 제거.

**Independent Test**: `find tui/src/commands/{ant-trace,autofix-pr,backfill-sessions,break-cache,bughunter,commands,ctx_viz,debug-tool-call,env,good-claude,issue,mock-limits,oauth-refresh,perf-issue,reset-limits,share,summary,teleport} -type f 2>/dev/null | wc -l` = 0. `bun typecheck` PASS.

### T020 — `git rm` 19 P0 stub directories (one-shot batch)

- [ ] **T020** [US2] 단일 batch `git rm -r` 로 19 directories 일괄 삭제:
  - `tui/src/commands/ant-trace/`
  - `tui/src/commands/autofix-pr/`
  - `tui/src/commands/backfill-sessions/`
  - `tui/src/commands/break-cache/`
  - `tui/src/commands/bughunter/`
  - `tui/src/commands/clear/clear/` (nested reconstruction artifact)
  - `tui/src/commands/commands/`
  - `tui/src/commands/ctx_viz/`
  - `tui/src/commands/debug-tool-call/`
  - `tui/src/commands/env/`
  - `tui/src/commands/good-claude/`
  - `tui/src/commands/issue/`
  - `tui/src/commands/mock-limits/`
  - `tui/src/commands/oauth-refresh/`
  - `tui/src/commands/perf-issue/`
  - `tui/src/commands/reset-limits/`
  - `tui/src/commands/share/`
  - `tui/src/commands/summary/`
  - `tui/src/commands/teleport/`

### T021 — `commands.ts` import + array 정리

- [ ] **T021** [US2] `tui/src/commands.ts` 정리 (단일 surgical edit, 약 60 LOC 변경):
  - 20 개 import 라인 제거 (lines 3, 5, 6, 7, 20, 30, 40, 44, 52, 144, 145, 147, 148-151, 152, 153, 176, 194, 195, 215-244 영역의 stub-only 항목).
  - 정확히는: `autofixPr`, `backfillSessions`, `goodClaude`, `issue`, `breakCache`, `commit?` (확인 필요), `bughunter`, `mockLimits`, `bridgeKick?` (보존), `summary`, `resetLimits`, `resetLimitsNonInteractive`, `share`, `teleport`, `antTrace`, `perfIssue`, `env`, `oauthRefresh`, `debugToolCall`, `ctx_viz` import + array entry 정리.
  - `INTERNAL_ONLY_COMMANDS` array 의 11+ 항목 제거 (`backfillSessions`, `breakCache`, `bughunter`, `ctx_viz`, `goodClaude`, `issue`, `mockLimits`, `bridgeKick?` 보존, `resetLimits`, `resetLimitsNonInteractive`, `summary`, `share`, `teleport`, `antTrace`, `perfIssue`, `env`, `oauthRefresh`, `debugToolCall`, `autofixPr`).
  - COMMANDS array 에는 stub-only 항목이 INTERNAL_ONLY_COMMANDS spread 로만 포함되므로 별도 정리 0.
  - 박제 헤더 추가 (top-of-file comment): `// KOSMOS-2640: 20 P0 auto-stub commands removed — Stage-1 sourcemap reconstruction gap (Initiative #2636 / Epic #2640). Tracked KOSMOS-only stubs from Epic #1633 dead-code elimination.`
  - 예외 보존: `commands/onboarding/index.ts` import (line 33) 는 Spec 1635 의 별도 처리 대상 — **건드리지 않는다**. 같은 패턴으로 `commands/install-github-app/types.ts`, `commands/plugin/types.ts`, `commands/plugin/unifiedTypes.ts` 도 본 epic scope 외.

### T022 — Verification

- [ ] **T022** [US2] `bun typecheck` 통과 검증 (T020 + T021 후). 회귀 시 잔존 import 또는 array entry 추가 정리.
- [ ] **T023** [US2] grep 검증: `grep -rE "from.*['\"].*commands/(ant-trace|autofix-pr|backfill-sessions|break-cache|bughunter|commands/index|ctx_viz|debug-tool-call|env|good-claude|issue|mock-limits|oauth-refresh|perf-issue|reset-limits|share|summary|teleport)['\"]?" tui/src/` 0 hit.

**Checkpoint US2**: P0 stub cleanup 완료. `bun typecheck` PASS, grep clean, `commands.ts` 박제 헤더 추가됨.

---

## Phase 5: User Story 3 — Gap-3 caller-graph 박제 + decisions.md 갱신 (Priority: P2)

**Goal**: `extra-usage-core.ts` / `generateSessionName.ts` / `reviewRemote.ts` 의 KOSMOS caller-graph 가 Spec 1633 / Epic #2293 박제 상태임을 검증 후 `decisions.md` 갱신.

**Independent Test**: `grep -rn "extra-usage-core\|generateSessionName\|reviewRemote" tui/src/` 가 박제 코멘트 또는 inline stub 만 hit (실제 import 0). `decisions.md` 의 § S5 마지막 row 가 "DROP 확정" 으로 갱신.

- [ ] **T030** [P] [US3] `grep -rn "extra-usage-core\|generateSessionName\|reviewRemote" tui/src/` 실행 후 8 hit 모두 박제 코멘트 또는 inline stub 임을 확인. (이미 spec.md § Gap-3 Caller-Graph 박제 에 검증 결과 작성됨 — 본 task 는 머지 직전 재확인.)
- [ ] **T031** [US3] `specs/cc-migration-audit/decisions.md` § S5 의 마지막 row 갱신:
  - 기존: `**CC sourcemap gap 3파일** (extra-usage-core / generateSessionName / reviewRemote) → **caller-graph 재검증 후 PORT 또는 DROP** (Epic D 에서 처리).`
  - 갱신: `**CC sourcemap gap 3파일** (extra-usage-core / generateSessionName / reviewRemote) → **DROP 확정** (Epic #2640). caller-graph 박제 검증 완료 — `specs/2640-s5-commands-skills/spec.md § Gap-3 Caller-Graph 박제`.`

**Checkpoint US3**: Gap-3 박제 완료. decisions.md 갱신.

---

## Phase 6: Verification & PR (Lead Opus solo, after all US complete)

- [ ] **T040** [Polish] `bun typecheck` 최종 PASS (US1 + US2 모두 머지 후 cumulative).
- [ ] **T041** [Polish] `bun test` 최종 PASS (pre-merge baseline ± 0 신규 fail).
- [ ] **T042** [Polish] Layer 5 tmux capture 시나리오 작성 + 실행: `specs/2640-s5-commands-skills/scripts/smoke-slash-autocomplete.sh`. 시나리오:
  1. `bun run tui` boot
  2. `wait_for_pane "KOSMOS" 30` (branding + tool registry verify)
  3. `tmux send-keys "/" ` (slash autocomplete trigger)
  4. wait + capture `snap-001-slash-dropdown.txt` + screenshot
  5. `tmux send-keys "ant"` (filter prefix matching deleted commands)
  6. capture `snap-002-ant-filter.txt` + screenshot (should show 0 results)
  7. `tmux send-keys C-c C-c` exit
  8. final capture `snap-003-final.txt`
- [ ] **T043** [Polish] PNG 키프레임 3+ 매 (`smoke-keyframe-1-boot.png`, `smoke-keyframe-2-dropdown.png`, `smoke-keyframe-3-empty-filter.png`) 캡처 후 Read tool 로 시각 검증 — `/ant-trace`, `/teleport`, `/share`, `/summary`, `/claude-api*`, `/verify` 0 노출 확인.
- [ ] **T044** [Polish] PR open. body: `Closes #2640` 단일 reference (Task sub-issues 미포함). PR description 에 (a) 삭제 파일 수, (b) Layer 5 PNG 첨부, (c) gap-3 박제 결정 요약, (d) `decisions.md` 갱신 위치 cite.
- [ ] **T045** [Polish] `gh pr checks --watch --interval 10`. 모든 check 통과 확인.
- [ ] **T046** [Polish] Codex inline review 응답. P1 모두 처리. P2/P3 은 reply with rationale.
- [ ] **T047** [Polish] Copilot Gate `completed` 확인. stuck 시 GraphQL 재요청.
- [ ] **T048** [Polish] Lead 가 epic close 시 sub-issues 일괄 close (Task issues — `/speckit-taskstoissues` 로 생성된 항목들).

---

## Dependency Graph

```
T001 (Setup, solo)
  ↓
[Phase 2 skipped]
  ↓
┌──────────────┬──────────────┬──────────────┐
T010 [P]       T020           T030 [P]
T011 [P]       T021           T031
T012 [P]       T022           
T013           T023
T014
T015
└──────────────┴──────────────┴──────────────┘
  ↓
T040 → T041 → T042 → T043 → T044 → T045 → T046 → T047 → T048
```

## Parallelization Strategy

- US1 (T010-T015), US2 (T020-T023), US3 (T030-T031) 는 **독립 디렉토리 + 독립 파일** → 3 Sonnet teammate 병렬 dispatch 가능.
- Phase 6 (T040-T048) 는 **Lead solo** — push / PR / CI / Codex 처리.

## Task count summary

- Phase 1: 1 task (T001)
- Phase 2: 0 tasks (skipped)
- Phase 3 (US1 Skills): 6 tasks (T010-T015) — 3 [P] (T010-T012) + 3 sequential
- Phase 4 (US2 P0 stubs): 4 tasks (T020-T023)
- Phase 5 (US3 gap-3 박제): 2 tasks (T030 [P] + T031)
- Phase 6 (Verification + PR): 9 tasks (T040-T048)
- **Total: 22 tasks**.
