# Implementation Plan: S5 Commands/Skills 정리 — claude-api/ + P0 stub + sourcemap gap

**Branch**: `feat/2640-s5-commands-skills` | **Date**: 2026-05-03 | **Spec**: `specs/2640-s5-commands-skills/spec.md`

## Summary

세 갈래 cleanup 을 단일 epic 에서 묶어 실행:

1. **Anthropic SDK skill bundle 일괄 제거** — `tui/src/skills/bundled/claude-api/` (51 파일) + `verify/` (3 파일) + 4 개 dispatcher 파일 (`claudeApi.ts`, `claudeApiContent.ts`, `verify.ts`, `verifyContent.ts`) + `bundled/index.ts` 등록 정리. UMMAYA 는 K-EXAONE on FriendliAI 전용이라 Anthropic SDK 7-언어 docs bundled skill 은 scope 외.
2. **P0 auto-stub commands 20개 일괄 삭제** — Stage-1 sourcemap reconstruction 시점의 NO-OP Proxy stub. `commands.ts` import + COMMANDS array + INTERNAL_ONLY_COMMANDS array 에서 모든 reference 정리.
3. **CC sourcemap gap 3 파일 caller-graph 박제** — `extra-usage-core.ts` / `generateSessionName.ts` / `reviewRemote.ts` 의 UMMAYA 측 caller 가 모두 UMMAYA-2293 / Spec 1633 박제 헤더 + inline no-op stub 으로 처리되었는지 검증 → DROP 박제 갱신.

cleanup-only epic, 신규 코드 0, 신규 dependency 0, byte-identical preservation 영역 변경 0.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x (TUI 측, 본 epic 의 100% 범위) · Python 3.12+ (백엔드, 본 epic 변경 0)

**Primary Dependencies**: 기존 — `ink`, `react`, `@inkjs/ui`, `string-width`, `@modelcontextprotocol/sdk`, `bun:bundle` (text 로더). 신규 dependency 0 (AGENTS.md hard rule).

**Storage**: 본 epic 은 in-memory + filesystem-only. `~/.ummaya/memdir/user/sessions/` (Spec 027), `~/.ummaya/memdir/user/consent/` (Spec 035), `~/.ummaya/memdir/user/plugins/` (Spec 1636) 등 기존 storage 구조 변경 0.

**Testing**: `bun test` (snapshot + frame sequence assertions, Layer 1b/5c), `bun typecheck` (`src/stubs/**` narrows), Layer 5 `scripts/tui-tmux-capture.sh` (slash autocomplete 시각 검증, 3+ PNG 키프레임).

**Target Platform**: macOS / Linux 터미널 (TUI), 외부 egress 0.

**Project Type**: cleanup epic (TS-only deletion + 박제 헤더 추가).

**Performance Goals**: TUI 부팅 latency 회귀 0, slash autocomplete 응답 latency 회귀 0.

**Constraints**:
- byte-identical preservation 영역 (`commands/help/`, `commands/clear/index.ts`, `commands/version.ts`, etc. 157 파일) 변경 0.
- AGENTS.md hard rule: 신규 dependency 0, `--force` push 0, `--no-verify` 0, English source-only.
- CORE THESIS: UMMAYA = CC + 2 swap 만, byte-identical default.

**Scale/Scope**: ~78 파일 삭제 + `commands.ts` ~60 LOC 정리 + `bundled/index.ts` ~10 LOC 정리 + `decisions.md` 1-row 갱신 + `findings.md` 신규 작성.

## Constitution Check

GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.

본 epic 은 cleanup-only (deletion + 박제 헤더 추가) 라서 대부분의 constitutional gate 가 trivially 통과:

| Gate | Status | Note |
|---|---|---|
| §I English source-only | PASS | 박제 헤더는 영문 (`// UMMAYA-2640: ...`). |
| §II Pydantic v2 for tool I/O | N/A | Python 변경 0. |
| §III No-`Any` policy | N/A | TS-only, 신규 코드 0. |
| §IV Stdlib logging | N/A | logging 사용 변경 0. |
| §V No new dependencies | PASS | 0 deps added. |
| §VI Spec-driven workflow | PASS | spec → plan → tasks → analyze → taskstoissues → implement. |
| §VII UMMAYA_* env vars | N/A | env 변경 0. |
| §VIII Byte-identical CC default | PASS | 삭제는 UMMAYA 신설 (P0 stub) 또는 swap-1 종속 (claude-api SDK docs) 만. byte-identical 영역 변경 0. |
| §IX No `requirements.txt`/`setup.py` | PASS | Python 변경 0. |
| §X Live API 미사용 in CI | PASS | live API 호출 0. |
| §XI TUI verification chain | PASS | Layer 1b (bun test) + Layer 5 (tmux capture-pane PNG 3+) 적용 — slash autocomplete dropdown 시각 검증. |
| §XII Issue hierarchy + GraphQL | PASS | Initiative #2636 / Epic #2640 / Tasks via `/speckit-taskstoissues`. |

**Constitution Check 통과**.

## Phase 0 — Research (필독 references)

본 plan 은 다음 references 를 cite:

### Reference 1 — `docs/vision.md § Reference materials`

UMMAYA 디자인의 첫 reference 는 Claude Code (CC) 2.1.88 sourcemap restored-src. 본 epic 의 모든 삭제 결정은 CC sourcemap 과 UMMAYA 의 발산을 추적하여, 발산이 정당한지 (UMMAYA-original justified) 또는 dead code 인지 (P0 stub) 또는 swap-1 종속 (Anthropic SDK only) 인지로 분류.

- claude-api skill: CC bundled skill 의 byte-identical 유지가 default 이지만, UMMAYA swap-1 (LLM provider FriendliAI K-EXAONE) 으로 인해 Anthropic SDK docs 는 scope 외 — 정당 발산 (DROP).
- P0 stub commands: CC sourcemap reconstruction gap. CC 원본 동작은 보존 의도이지만 sourcemap 에 누락된 모듈을 NO-OP Proxy 로 대체. 본 epic 시점의 검증 결과 caller 가 UMMAYA scope 무관 — 정당 dead-code (DROP).
- Sourcemap gap 3: 동일 패턴, UMMAYA 측 caller 가 이미 UMMAYA-2293 박제 처리됨 — DROP 확정.

### Reference 2 — `docs/requirements/ummaya-migration-tree.md § L1-A / § L1-B / § L1-C`

L1-A 의 "FriendliAI Serverless + K-EXAONE 단일 고정" 결정이 claude-api skill bundle 제거의 직접 근거. L1-B / L1-C 는 본 epic scope 와 직접 관련 없음 (도구 시스템 / 메인 동사 추상화 변경 0).

### Reference 3 — `specs/cc-migration-audit/scope-S5-commands-input.md § DROP-CANDIDATE`

S5 audit 의 4-bucket 분류표 (PORT 1 / PRESERVE-IDENTICAL 214 / MIGRATE-FOR-SWAP 40 / DROP-CANDIDATE 130). 본 epic 은 DROP-CANDIDATE 130 중 (a) Skills UMMAYA-only 29 + (b) P0 auto-stub commands 21 + (c) sourcemap gap 추적 3 = 약 53 항목 처리. 나머지 DROP-CANDIDATE 항목은 UMMAYA-original justified (한국 행정 신설 명령 / Spec 288 키바인딩 확장 / Korean IME hooks) 이라 본 epic 에서 보존.

### Reference 4 — `specs/cc-migration-audit/decisions.md § S5 Commands/Skills`

Lead Opus 자체 판단 결정 3건 (claude-api/ 제거 · P0 auto-stub 즉시 삭제 · sourcemap gap caller-graph 재검증) 모두 본 epic 에 포함.

### Reference 5 — `specs/2637-p0-regression/` (Epic A, 머지된 P0 회귀 복구)

Epic A 의 박제 패턴 (UMMAYA-original stub 헤더 with `[SWAP/no-cc-source(2637)]` annotation) 을 참조. 본 epic 은 UMMAYA-2640 헤더로 박제 패턴을 일관 유지.

### Reference 6 — Existing UMMAYA-2293 박제 패턴

`extra-usage.tsx` / `extra-usage-noninteractive.ts` / `rename.ts` / `ultrareviewCommand.tsx` / `ExitPlanModePermissionRequest.tsx` 의 inline UMMAYA-2293 헤더 패턴 (예: `// UMMAYA-2293: extra-usage-core.ts deleted (claude.ai SaaS billing dead).`). 본 epic 은 동일 패턴을 UMMAYA-2640 으로 갱신/유지.

### Pre-spec 검증 결과 (Phase 0 deliverables)

| 검증 항목 | 결과 |
|---|---|
| `claude-api/` 51 파일 존재 | confirmed |
| `verify/` 3 파일 존재 | confirmed (`SKILL.md.ts` + `examples/cli.md.ts` + `examples/server.md.ts`) |
| `claudeApi.ts` 가 `claude-api/*.md` 27 파일을 static import | confirmed (`claudeApiContent.ts:4-29`) |
| `verify.ts` 가 `verify/*.md` 3 파일을 static import | confirmed (`verifyContent.ts:4-6`) |
| `bundled/index.ts` 가 `registerVerifySkill` 등록 + `feature('BUILDING_CLAUDE_APPS')` 게이트 하 `registerClaudeApiSkill` 등록 | confirmed |
| `feature()` stub 이 항상 false 반환 → claude-api 는 runtime dead, verify 도 `process.env.USER_TYPE !== 'ant'` early-return 으로 dead | confirmed (`tui/src/stubs/bun-bundle.ts:4-6`) |
| P0 stub 20 commands 모두 동일 NO-OP Proxy 스텁 헤더 보유 | confirmed (`grep -l "P0 auto-stub\|P0 reconstructed" tui/src/commands/*/index.ts`) |
| `commands.ts` 가 20 stub 모두 import + COMMANDS / INTERNAL_ONLY_COMMANDS 등록 | confirmed (line-by-line audit) |
| `commands/onboarding/index.ts` 는 P0 stub 헤더이지만 `commands.ts:33` 의 `import onboarding` 으로 사용 — 별도 처리 필요 | scope-out (Spec 1635 후속) |
| `commands/install-github-app/types.ts`, `commands/plugin/types.ts`, `commands/plugin/unifiedTypes.ts` 는 type import dependency 보유 | scope-out (Epic B 후속) |
| `commands/clear/clear/` 중첩 디렉토리 (CC original 부재) | scope-in (epic 에서 제거) |
| Sourcemap gap 3 파일 UMMAYA caller 모두 UMMAYA-2293 박제 처리됨 | confirmed (`grep -rn "extra-usage-core\|generateSessionName\|reviewRemote" tui/src/`) |

**Phase 0 결론: 사전 검증 완료, 추가 research 불필요.** Phase 1 design 으로 진행.

## Phase 1 — Design

### File deletion plan

**Group A — Skills (claude-api + verify bundle)**:

```
DELETE tui/src/skills/bundled/claude-api/        # 51 files (entire dir)
DELETE tui/src/skills/bundled/verify/            #  3 files (entire dir)
DELETE tui/src/skills/bundled/claudeApi.ts       # dispatcher
DELETE tui/src/skills/bundled/claudeApiContent.ts # .md aggregator
DELETE tui/src/skills/bundled/verify.ts          # dispatcher (gated, dead)
DELETE tui/src/skills/bundled/verifyContent.ts   # .md aggregator
EDIT   tui/src/skills/bundled/index.ts           # remove imports + register calls + add UMMAYA-2640 header
```

**Group B — P0 auto-stub commands (20)**:

```
DELETE tui/src/commands/ant-trace/                       # P0 stub
DELETE tui/src/commands/autofix-pr/                      # P0 stub
DELETE tui/src/commands/backfill-sessions/               # P0 stub
DELETE tui/src/commands/break-cache/                     # P0 stub
DELETE tui/src/commands/bughunter/                       # P0 stub
DELETE tui/src/commands/clear/clear/                     # nested reconstruction artifact
DELETE tui/src/commands/commands/                        # P0 stub (self-ref name)
DELETE tui/src/commands/ctx_viz/                         # P0 stub
DELETE tui/src/commands/debug-tool-call/                 # P0 stub
DELETE tui/src/commands/env/                             # P0 stub
DELETE tui/src/commands/good-claude/                     # P0 stub
DELETE tui/src/commands/issue/                           # P0 stub
DELETE tui/src/commands/mock-limits/                     # P0 stub
DELETE tui/src/commands/oauth-refresh/                   # P0 stub
DELETE tui/src/commands/perf-issue/                      # P0 stub
DELETE tui/src/commands/reset-limits/                    # P0 stub
DELETE tui/src/commands/share/                           # P0 stub
DELETE tui/src/commands/summary/                         # P0 stub
DELETE tui/src/commands/teleport/                        # P0 stub
EDIT   tui/src/commands.ts                               # remove 20 imports + COMMANDS / INTERNAL_ONLY_COMMANDS entries + add UMMAYA-2640 headers
```

**Group C — Gap-3 caller-graph 박제 검증 + 문서화**:

```
EDIT   specs/cc-migration-audit/decisions.md             # § S5 row → "DROP 확정 (Epic #2640)"
EDIT   specs/2640-s5-commands-skills/spec.md             # § Gap-3 Caller-Graph 박제 (이미 spec.md 안에 작성됨)
```

### `commands.ts` 정리 패턴

각 `import` 라인 → 같은 라인에 박제 코멘트 (CC fidelity preservation 원칙: 삭제만 하지 말고 발산 박제). 예:

```typescript
// UMMAYA-2640: ant-trace P0 auto-stub removed — Stage-1 sourcemap gap (Epic #2640).
// import antTrace from './commands/ant-trace/index.js'  // ← 줄 자체 삭제
// ...
// COMMANDS array 의 antTrace 등록 라인은 단순 삭제 (인라인 코멘트 0 — array 가독성 유지)
```

20 imports + 20 array entries 일괄 정리. 추가로 `INTERNAL_ONLY_COMMANDS` array 에서 backfillSessions / breakCache / bughunter / mockLimits / antTrace / perfIssue / debugToolCall / autofixPr / share / summary / teleport / etc. 등 11+ 항목 제거.

### `bundled/index.ts` 정리 패턴

```typescript
// UMMAYA-2640: claude-api + verify bundled skills removed —
// Anthropic SDK docs out of scope (FriendliAI K-EXAONE single-provider).
// Tracked under Initiative #2636 / Epic #2640.
// (former imports of registerClaudeApiSkill / registerVerifySkill removed)
```

### Verification chain

| Layer | Test | Pass criterion |
|---|---|---|
| Layer 1b — `bun test` | snapshot + REPL component tests | pre-merge baseline ± 0 |
| Layer 1b — `bun typecheck` | tsc resolution | exit 0 |
| Layer 5 — `scripts/tui-tmux-capture.sh` slash autocomplete scenario | tmux capture-pane PNG 3+ keyframes | `/ant-trace`, `/teleport`, `/share`, `/summary`, `/claude-api*`, `/verify` 0 노출 |
| Layer 5c — `frameStreamSnapshot` | bundled skill snapshot test 갱신 | hash sequence match |
| Import scan | `grep -rE "from.*['\"].*commands/(ant-trace|autofix-pr|backfill-sessions|break-cache|bughunter|commands|ctx_viz|debug-tool-call|env|good-claude|issue|mock-limits|oauth-refresh|perf-issue|reset-limits|share|summary|teleport)" tui/src/` | 0 hits |
| Import scan | `grep -rE "from.*['\"].*claude-api\|from.*['\"].*claudeApiContent\|from.*['\"].*verifyContent" tui/src/` | 0 hits (UMMAYA-2640 박제 코멘트 제외) |

### Layer 5 시나리오 outline

`specs/2640-s5-commands-skills/scripts/smoke-slash-autocomplete.sh`:

1. `bun run tui` boot
2. Wait for `UMMAYA` branding regex (`wait_for_pane "UMMAYA" 30`)
3. `tmux send-keys "/" Enter` (slash autocomplete trigger)
4. Sleep 1s + `tmux capture-pane -p` → `snap-001-slash-dropdown.txt` + screenshot via PNG
5. `tmux send-keys "ant" Enter` (filter prefix that should match nothing if cleanup complete)
6. Capture `snap-002-ant-filter.txt` + PNG
7. `tmux send-keys C-c C-c` exit
8. Final capture `snap-003-final.txt` + PNG

Layer 5 outputs: `smoke-keyframe-1-boot.png`, `smoke-keyframe-2-dropdown.png`, `smoke-keyframe-3-empty-filter.png`. Lead Opus Read each PNG to confirm 0 노출.

### Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| `commands.ts` array reorder 변경 으로 인한 byte-identical 회귀 | Medium | 라인 단위 surgical edit; PR diff 시 array 위치 단순 삭제만 (리오더 0) 검증 |
| `bundled/index.ts` import resolution 깨짐 (`feature` 미사용 시 unused import warning) | Low | tsc strict mode 회귀 시 `feature` import 자체 정리 (이미 다른 곳에서 사용 — `BUILDING_CLAUDE_APPS` 외 다른 feature flag 도 있음) |
| Skill snapshot test 가 `claude-api`/`verify` 등록을 하드코딩 | Medium | 발견 시 snapshot 갱신; bun test pre-merge 에서 회귀 확인 |
| `commands/onboarding/index.ts` P0 stub 잔존 → 다음 라운드 audit 에서 misleading | Low | spec § Edge Cases 와 § Deferred Items 에 명시 박제 |
| `INTERNAL_ONLY_COMMANDS` array 가 빈 배열이 되어 `process.env.USER_TYPE === 'ant'` 분기가 dead | Low | 분기 자체 정리는 follow-up epic; 본 epic 은 array 항목만 정리 (20 중 11+ 제거) |
| Layer 5 K-EXAONE LLM 호출 latency | Low | 본 시나리오는 slash autocomplete 만 호출 — LLM 호출 0, reasoning latency 0. |

## Project Structure

### Documentation (this feature)

```text
specs/2640-s5-commands-skills/
├── plan.md                      # this file
├── spec.md                      # /speckit-specify output (gap-3 caller-graph 박제 inlined)
├── tasks.md                     # /speckit-tasks output (next phase)
├── dispatch-tree.md             # /speckit-implement dispatch tree (next phase)
└── scripts/
    └── smoke-slash-autocomplete.sh   # Layer 5 시나리오
```

### Source Code (repository root)

```text
tui/
├── src/
│   ├── commands.ts              # EDIT: 20 imports + array entries + UMMAYA-2640 박제 헤더
│   ├── commands/                # DELETE: 19 P0 stub dirs + clear/clear/ nested
│   │   ├── ant-trace/           # ↓ DELETE
│   │   ├── autofix-pr/          # ↓ DELETE
│   │   ├── backfill-sessions/   # ↓ DELETE
│   │   ├── break-cache/         # ↓ DELETE
│   │   ├── bughunter/           # ↓ DELETE
│   │   ├── clear/clear/         # ↓ DELETE (nested artifact)
│   │   ├── commands/            # ↓ DELETE
│   │   ├── ctx_viz/             # ↓ DELETE
│   │   ├── debug-tool-call/     # ↓ DELETE
│   │   ├── env/                 # ↓ DELETE
│   │   ├── good-claude/         # ↓ DELETE
│   │   ├── issue/               # ↓ DELETE
│   │   ├── mock-limits/         # ↓ DELETE
│   │   ├── oauth-refresh/       # ↓ DELETE
│   │   ├── perf-issue/          # ↓ DELETE
│   │   ├── reset-limits/        # ↓ DELETE
│   │   ├── share/               # ↓ DELETE
│   │   ├── summary/             # ↓ DELETE
│   │   └── teleport/            # ↓ DELETE
│   └── skills/
│       └── bundled/
│           ├── index.ts         # EDIT: imports + register calls + UMMAYA-2640 박제 헤더
│           ├── claudeApi.ts     # ↓ DELETE
│           ├── claudeApiContent.ts # ↓ DELETE
│           ├── claude-api/      # ↓ DELETE (entire subtree, 51 files)
│           ├── verify.ts        # ↓ DELETE
│           ├── verifyContent.ts # ↓ DELETE
│           └── verify/          # ↓ DELETE (entire subtree, 3 files)
specs/
└── cc-migration-audit/
    └── decisions.md             # EDIT: § S5 row → "DROP 확정 (Epic #2640)"
```

**Structure Decision**: Cleanup-only epic. 신규 디렉토리 0, 신규 모듈 0. 모든 변경은 `tui/src/commands*` + `tui/src/skills/bundled/` + `specs/2640-s5-commands-skills/` + `specs/cc-migration-audit/decisions.md` 에 한정.

## Complexity Tracking

> Constitution Check 모두 통과 (PASS). violation 0. Complexity tracking 불필요.
