---

description: "Task list for Epic A — P0 회귀 즉시 복구 (#2637)"
---

# Tasks: Epic A — P0 회귀 즉시 복구

**Input**: Design documents from `/specs/2637-p0-regression/`
**Prerequisites**: spec.md (FR-001..FR-016), plan.md, research.md (D1-D4), data-model.md (R-1a..R-7c + V1-V9), quickstart.md (T001-T007), contracts/dispatch-tree.md, contracts/byte-identical-verification.md

**Tests**: Tests are NOT explicitly requested — 본 Epic 은 byte-copy + wire 작업이라 신규 unit test 작성 없음. 검증은 (a) 기존 `bun test` / `pytest` parity 유지 (V2/V3) + (b) byte-identical diff (V4) + (c) PTY/tmux smoke (V5/V7) + (d) audit 재실행 (V8).

**Organization**: 단일 Sonnet teammate sequential. ALL tasks **NO `[P]` marker** — 같은 영역 (TUI types/constants/utils/services) 파일 충돌 + cascade dep 발견 위험으로 병렬 dispatch 금지 (dispatch-tree.md 결정).

## Format: `[ID] [Story] Description`

- **No `[P]` marker** anywhere — sequential only.
- **[Story]**: US1 (OTEL telemetry pipeline 회복) · US2 (Constants/Types byte-identical 회복) · US3 (Headless --print mode) · US4 (Stage-1 NO-OP 박제)
- 모든 path 는 워크트리 `/Users/um-yunsang/UMMAYA-w-2637/` 기준 상대 경로.

## Path Conventions

- TUI 측: `tui/src/...`
- audit docs: `specs/cc-migration-audit/...`
- CC source-of-truth: `.references/claude-code-sourcemap/restored-src/src/...` (read-only)
- worktree spec: `specs/2637-p0-regression/...`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: baseline 측정 + dependency 추가 (tasks 의 prerequisite).

- [X] T001 Baseline 측정 + 8개 OTel dependency 추가
  - **FR**: FR-005 (instrumentation.ts PORT prerequisite)
  - **Quickstart**: 사전 조건 + T004 Step 1
  - **Files changed (1)**: `tui/package.json` + `tui/bun.lock` (생성)
  - **Commands**:
    ```bash
    cd /Users/um-yunsang/UMMAYA-w-2637
    bun test 2>&1 | tail -5  # baseline pass count 기록 (≥983 기대)
    uv run pytest 2>&1 | tail -5  # baseline pass count 기록 (≥3458 기대)
    bun typecheck 2>&1 | tail -5  # baseline pass 검증
    cd tui
    bun add @opentelemetry/semantic-conventions \
            @opentelemetry/exporter-trace-otlp-http \
            @opentelemetry/exporter-trace-otlp-grpc \
            @opentelemetry/exporter-logs-otlp-http \
            @opentelemetry/exporter-logs-otlp-grpc \
            @opentelemetry/exporter-metrics-otlp-http \
            @opentelemetry/exporter-metrics-otlp-grpc \
            @grpc/grpc-js
    cd ..
    bun typecheck 2>&1 | tail -5  # dep 추가 후 회귀 0 확인
    ```
  - **Verification**: `grep -c "exporter-trace-otlp\|exporter-logs-otlp\|exporter-metrics-otlp\|grpc-js\|semantic-conventions" tui/package.json` ≥ 8
  - **Commit**: `chore(2637): add 8 OTel/gRPC dependencies for instrumentation.ts PORT`

**Checkpoint**: dependency baseline 준비 완료, 모든 user story 시작 가능.

---

## Phase 2: User Story 1 — OTEL Telemetry Pipeline 회복 (Priority: P1) 🎯 MVP

**Goal**: UMMAYA 4-tier OTEL 의 Tool layer span emission 회복. instrumentation.ts dynamic import boot path 복구. Spec 021 OTLP collector 가 client-side trace 받음.

**Independent Test**: `bun run tui` 부팅 후 1회 lookup primitive 호출 → Langfuse trace tree 에 `ummaya.tool.id=lookup` span pair 출현 (V5 + V9).

### Implementation for User Story 1

- [X] T002 [US1] events_mono types byte-copy PORT (3 files, R-1a/b/c)
  - **FR**: FR-001
  - **Quickstart**: T001
  - **Files changed (3)**:
    - `tui/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts` (21 → 865 LOC)
    - `tui/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts` (15 → 223 LOC)
    - `tui/src/types/generated/events_mono/common/v1/auth.ts` (신설, 디렉토리 신설 포함)
  - **Verification**: V4 (`diff -q` empty for 3 files via `contracts/byte-identical-verification.md § 1`)
  - **Depends on**: T001
  - **Commit**: `feat(2637): byte-copy events_mono types from CC 2.1.88 (R-1a/b/c)`

- [X] T003 [US1] utils/telemetry/instrumentation.ts byte-copy PORT + cascade stub modules (R-5)
  - **FR**: FR-005
  - **Quickstart**: T004 Step 2-4
  - **Files changed (~6)**:
    - `tui/src/utils/telemetry/instrumentation.ts` (신설 825 LOC, byte-copy from CC)
    - 신설 cascade stub modules (typecheck 에서 누락 모듈 발견 시 신설):
      - `tui/src/utils/telemetry/betaSessionTracing.ts` (NEW stub — exports: `isBetaTracingEnabled`)
      - `tui/src/utils/telemetry/bigqueryExporter.ts` (NEW stub — exports: `BigQueryMetricsExporter`)
      - `tui/src/utils/telemetry/logger.ts` (NEW stub — exports: `ClaudeCodeDiagLogger`)
      - `tui/src/utils/telemetry/perfettoTracing.ts` (NEW stub — exports: `initializePerfettoTracing`)
      - `tui/src/utils/telemetry/sessionTracing.ts` (UPDATE — `endInteractionSpan` + `isEnhancedTelemetryEnabled` exports 추가, 기존 `isBetaTracingEnabled` 보존)
  - **swap-1 화이트리스트** (data-model.md § Swap1IdentifierWhitelist): import path는 UMMAYA-side stub 이 같은 시그니처로 export → diff 0
  - **Verification**:
    - V1 (`bun typecheck` exit 0)
    - V4 (instrumentation.ts diff lines ≤ 20 via `contracts/byte-identical-verification.md § 2.3`)
    - cascade stub 헤더 SWAP cite 검증 (`§ 3`)
  - **Depends on**: T001 (deps), T002 (events_mono — auth.ts 가 telemetry 의존 가능성)
  - **Commit**: `feat(2637): port instrumentation.ts (825 LOC) + cascade stubs (R-5)`

- [X] T004 [US1] toolExecution.ts 9 stub wire (UMMAYA Spec 021 OTEL helper, R-6)
  - **FR**: FR-006
  - **Quickstart**: T005
  - **Files changed (2)**:
    - `tui/src/utils/telemetry/toolSpans.ts` (NEW — Spec 021 OTEL helper for tool spans, ~150 LOC)
    - `tui/src/services/tools/toolExecution.ts` (line 91-100 의 9 inline stub → import statement)
  - **9 함수 시그니처** (data-model.md § OtelAttributeContract):
    - `logOTelEvent(eventName, attrs)`, `addToolContentEvent(span, contentAttrs)`, `endToolBlockedOnUserSpan(reason, source)`, `endToolExecutionSpan(result)`, `endToolSpan(toolResultStr)`, `isBetaTracingEnabled()` → false, `startToolBlockedOnUserSpan(span)` → null, `startToolExecutionSpan(span, name)` → Span | null, `startToolSpan(name, attrs)` → Span | null
  - **OTEL attribute namespace**: `ummaya.tool.{id,outcome,duration_ms,error_type,permission_decision,user_facing_name,input_size_bytes}`
  - **Verification**:
    - V1 (`bun typecheck` exit 0)
    - V5 (PTY smoke — Layer 5 tmux capture, `bun run tui` 부팅 후 lookup 1회 → Langfuse trace 에 `ummaya.tool.id=lookup` span pair 출현)
    - wire 검증 (`contracts/byte-identical-verification.md § 5`): inline stub 잔존 0 + import statement 존재
  - **Depends on**: T003 (instrumentation.ts 가 TracerProvider 등록 → toolExecution wire 가 자동 라우팅)
  - **Commit**: `feat(2637): wire toolExecution.ts 9 stubs to UMMAYA Spec 021 OTEL helper (R-6)`

**Checkpoint**: User Story 1 완료. 4-tier OTEL Tool layer 가 Langfuse 에 emit. instrumentation.ts dynamic import 회복. **MVP 가능.**

---

## Phase 3: User Story 2 — Constants/Types byte-identical 회복 (Priority: P1)

**Goal**: 5개 stub 파일 (`messages`/`xml`/`figures`/`logs`/`oauth`) 을 CC byte-identical 로 회복. downstream consumer 가 정상 값 (CC 와 동일) 받음. silent regression 차단.

**Independent Test**: V4 (5 파일 byte-identical diff -q empty/whitelist) + V1 (bun typecheck 통과) + ad-hoc `node -e "require('./tui/src/constants/messages.js')"` 같은 import 검증.

### Implementation for User Story 2

- [X] T005 [US2] Proxy stub 4 files byte-copy PORT (R-2a/b/c/d)
  - **FR**: FR-002
  - **Quickstart**: T002
  - **Files changed (4)**:
    - `tui/src/constants/messages.ts` (32 → 1 LOC byte-copy)
    - `tui/src/constants/xml.ts` (37 → 86 LOC byte-copy)
    - `tui/src/constants/figures.ts` (46 → 45 LOC byte-copy 검증)
    - `tui/src/types/logs.ts` (55 → 330 LOC byte-copy)
  - **Verification**: V4 (4 파일 모두 `diff -q` empty via `contracts/byte-identical-verification.md § 1`) + V1 (`bun typecheck` 통과 — 기존 Proxy callsite 가 plain const 와 호환)
  - **Depends on**: T001 (baseline)
  - **Commit**: `feat(2637): byte-copy constants/{messages,xml,figures} + types/logs from CC 2.1.88 (R-2a/b/c/d)`

- [X] T006 [US2] constants/oauth.ts PORT + swap-1 식별자 교체 (R-4)
  - **FR**: FR-004
  - **Quickstart**: T003
  - **Files changed (1)**: `tui/src/constants/oauth.ts` (신설 234 LOC byte-copy + swap-1 식별자 교체 + 헤더 주석)
  - **swap-1 화이트리스트** (data-model.md § Swap1IdentifierWhitelist):
    - OAuth client_id 상수 → UMMAYA-side `null`
    - `console.anthropic.com` / `claude.ai/oauth` URL 상수 → UMMAYA-side `null` 또는 자리표시자
    - `process.env.USER_TYPE === 'ant'` 가드 → CC 그대로 (자동 prod fallback)
    - 헤더 주석 추가 (UMMAYA Epic #2637 cite)
  - **Verification**: V4 (oauth.ts diff lines ≤ 30 via `contracts/byte-identical-verification.md § 2.1`) + V1
  - **Depends on**: T005 (constants 일관성)
  - **Commit**: `feat(2637): port constants/oauth.ts (234 LOC) with swap-1 identifier replace (R-4)`

**Checkpoint**: User Story 2 완료. 5 파일 byte-identical 회복. silent regression 차단.

---

## Phase 4: User Story 3 — Headless --print Mode 동작 회복 (Priority: P2)

**Goal**: `bun run tui --print "안녕"` 가 정상 응답. CI/스크립트 자동화 surface 회복.

**Independent Test**: V6 (`bun run tui --print "안녕"` exit 0, stdout ≥ 1 byte, stderr 에 "not supported" 0회).

### Implementation for User Story 3

- [X] T007 [US3] cli/print.ts byte-copy PORT + cascade stub + main.tsx 차단 제거 (R-3 + R-3-cascade + FR-016)
  - **FR**: FR-003 + FR-016
  - **Quickstart**: T006
  - **Files changed (3)**:
    - `tui/src/services/remoteManagedSettings/index.ts` (신설 UMMAYA stub ~30 LOC, R-3-cascade — pattern: `tui/src/services/analytics/index.ts`)
    - `tui/src/cli/print.ts` (신설 5594 LOC byte-copy from CC + 헤더 주석)
    - `tui/src/main.tsx` (L1960 "--print not supported" 차단 메시지 + 관련 블록 제거 + cli/print 호출 wire)
  - **swap-1 화이트리스트**:
    - `process.env.USER_TYPE === 'ant'` + `feature(...)` 가드 → CC 그대로 (UMMAYA 자동 비활성)
    - 헤더 주석 추가 (UMMAYA Epic #2637 cite)
    - cascade stub import resolution → UMMAYA-side stub 이 같은 시그니처
  - **Verification**:
    - V4 (print.ts diff lines ≤ 20 via `contracts/byte-identical-verification.md § 2.2`)
    - V6 (`bun run tui --print "안녕"` 정상 응답 — 실제 LLM 호출이라 30-90s 소요 가능)
    - V1 + V2 (`bun typecheck` + `bun test` 회귀 0)
    - cascade stub 헤더 SWAP cite 검증 (`§ 3`)
  - **Depends on**: T005 (constants), T003 (instrumentation — 부팅 경로 의존)
  - **추가 cascade dep 발견 시**: 본 task 안에서 UMMAYA-side stub 추가 (analytics/index.ts 패턴), 5+ 발견 시 Lead Opus 에 보고 (scope creep 결정)
  - **Commit**: `feat(2637): port cli/print.ts (5594 LOC) + remoteManagedSettings cascade stub + main.tsx 차단 제거 (R-3, FR-016)`

**Checkpoint**: User Story 3 완료. `--print` 헤드리스 mode 동작.

---

## Phase 5: User Story 4 — Stage-1 NO-OP Stub 정합성 박제 (Priority: P3)

**Goal**: 3 stub 파일 (`protectedNamespace`/`systemThemeWatcher`/`ultraplan/prompt.txt`) 헤더에 SWAP/no-cc-source(2637) cite 박제. audit 재실행 시 D-bucket 0.

**Independent Test**: 3 파일 헤더에 `SWAP/no-cc-source(2637)` + `decisions.md S9` cite 출현 (`contracts/byte-identical-verification.md § 4`).

### Implementation for User Story 4

- [X] T008 [US4] Stage-1 NO-OP 3 헤더 박제 + decisions.md 업데이트 (R-7a/b/c + FR-007 + FR-015)
  - **FR**: FR-007 + FR-015
  - **Quickstart**: T007 Step 1-4
  - **Files changed (4)**:
    - `tui/src/utils/protectedNamespace.ts` (헤더 패턴 박제, body 그대로)
    - `tui/src/utils/systemThemeWatcher.ts` (헤더 패턴 박제)
    - `tui/src/utils/ultraplan/prompt.txt` (헤더 패턴 박제)
    - `specs/cc-migration-audit/decisions.md` (S9 § Stage-1 행 업데이트 — "byte-copy 채우기" → "CC source 부재 확정 — UMMAYA-only stub 박제 처리, TUI Fidelity Meta-Epic deferred")
  - **헤더 패턴**:
    ```
    // SPDX-License-Identifier: Apache-2.0
    // SWAP/no-cc-source(2637): UMMAYA-only stub. CC source absent
    // (find .references/.../src -name "<file>" returns 0). decisions.md S9 § Stage-1 cite.
    // CC consumer references (envUtils.ts:142 / ThemeProvider.tsx:69) imply CC has
    // runtime equivalents but they're not in restored-src — UMMAYA NO-OP is justified
    // until TUI Fidelity Meta-Epic decides on UMMAYA-original implementation.
    ```
  - **Verification**: 헤더 박제 검증 (`contracts/byte-identical-verification.md § 4`)
  - **Depends on**: 없음 (independent)
  - **Commit**: `docs(2637): imprint Stage-1 NO-OP headers + decisions.md S9 update (R-7a/b/c)`

**Checkpoint**: User Story 4 완료.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: 통합 검증 + 최종 audit closure.

- [X] T009 통합 검증 + audit closure
  - **FR**: FR-008 + FR-009 + FR-010 + FR-011 + FR-012 + FR-013 + FR-014 + SC-001..SC-010
  - **Quickstart**: T007 Step 5-6 + 빠른 검증
  - **Files changed (0)**: 검증 전용 (commit 없음, 별도 verification log 만 PR 본문에 첨부)
  - **Commands**:
    ```bash
    cd /Users/um-yunsang/UMMAYA-w-2637

    # V1 — bun typecheck
    bun typecheck

    # V2 — bun test parity (≥ 983)
    bun test 2>&1 | tail -10

    # V3 — uv run pytest parity (≥ 3458)
    uv run pytest 2>&1 | tail -10

    # V4 — byte-identical 7 PORTed files
    bash specs/2637-p0-regression/scripts/verify-byte-identical.sh

    # V6 — --print mode
    bun run tui --print "안녕" 2>&1 | tail -20

    # V7 — TUI 5-layer smoke (Layer 5 tmux capture)
    bash scripts/tui-tmux-capture.sh /tmp/2637-smoke specs/2637-p0-regression/scripts/smoke-2637.sh
    ls /tmp/2637-smoke/snap-*.txt
    cat /tmp/2637-smoke/final.txt | grep -E "tool_registry: \d+ entries verified|UMMAYA"

    # V8 — audit 재실행 (`contracts/byte-identical-verification.md § 6`)
    # 9개 회귀 항목 모두 D-bucket 0 확인:
    wc -l tui/src/types/generated/events_mono/claude_code/v1/*.ts | tail -1  # 865+ LOC
    grep -l "__noop\|__stub\|Proxy" tui/src/constants/{messages,xml,figures}.ts tui/src/types/logs.ts 2>&1 || echo "no Proxy match"
    ls tui/src/cli/print.ts tui/src/constants/oauth.ts tui/src/utils/telemetry/instrumentation.ts
    head -5 tui/src/utils/{protectedNamespace,systemThemeWatcher}.ts | grep "SWAP/no-cc-source(2637)"
    grep -c "no-op" tui/src/services/tools/toolExecution.ts  # = 0
    ```
  - **Pass criteria**: V1-V8 모두 PASS, audit D-bucket 0
  - **Depends on**: T002 + T003 + T004 + T005 + T006 + T007 + T008 (all)
  - **추가 commit 없음** (검증 전용). PR 본문에 결과 log 첨부.

**Final checkpoint**: 모든 9건 회귀 + 부수 3건 + cascade 1건 모두 해결. PR open 가능.

---

## Dependencies & Execution Order

### Phase Dependencies (sequential 강제)

```
T001 (Setup)
  ↓
T002 [US1] (events_mono)
  ↓
T003 [US1] (instrumentation + cascade stubs)
  ↓
T004 [US1] (toolExecution wire)        ← T003 → T004 (instrumentation ready 후 wire)
  ↓
T005 [US2] (constants/messages,xml,figures + types/logs)
  ↓
T006 [US2] (constants/oauth)            ← T005 → T006 (constants 일관성)
  ↓
T007 [US3] (cli/print + cascade + main.tsx)  ← T005 + T003 (constants + boot path)
  ↓
T008 [US4] (Stage-1 NO-OP 헤더 박제)  ← independent (병렬 가능했지만 sequential 진행)
  ↓
T009 (통합 검증 + audit closure)        ← all
```

### Single Sonnet Sequential Rationale

dispatch-tree.md 결정 근거:
- 9건 회귀 모두 P0/P2/P3 + 같은 영역 (constants/types/utils/services)
- T004 (toolExecution wire) 가 T003 (instrumentation) 부팅 경로 의존
- T007 (cli/print) 가 T005 (constants) + T003 (instrumentation) 모두 의존
- 동시 dispatch 시 cascade dep 발견 → 인접 task 와 file 충돌 가능성
- → 단일 Sonnet teammate sequential 이 안전 + 변경 흐름 추적 용이

### Parallel Opportunities

**없음.** 본 Epic 의 모든 task `[P]` 마커 없음. 단일 Sonnet teammate sequential.

(예외 가능했던 항목: T002 [US1] events_mono ↔ T005 [US2] constants 는 file 충돌 0 이라 병렬 가능했으나, dispatch-tree.md 가 cascade dep 위험으로 sequential 결정.)

---

## Implementation Strategy

### MVP First (User Story 1 — OTEL Pipeline 회복)

1. T001 Setup (deps + baseline)
2. T002 + T003 + T004 (US1 완료)
3. **STOP and VALIDATE**: V5 (Langfuse trace 에 ummaya.tool.id span pair 출현)
4. MVP demo 가능 — 4-tier OTEL Tool layer 회복 단독으로 가치 있음.

### Incremental Delivery

1. T001 → T002 → T003 → T004 → US1 MVP demo
2. T005 → T006 → US2 demo (constants/types byte-identical)
3. T007 → US3 demo (--print headless)
4. T008 → US4 demo (Stage-1 박제 + audit closure)
5. T009 → 통합 검증 → PR open

### Single Teammate Strategy

- 단일 Sonnet teammate (`sonnet-2637-impl`) 가 T001 → T009 순차 실행
- 각 task 후 commit (Conventional Commits) — `git push` 는 Lead Opus
- 각 task 후 typecheck 회귀 0 확인 후 다음 task 진행
- 회귀 발견 시 root cause 분석 후 fix, 그래도 fail 시 Lead Opus 보고

---

## Notes

- **Total tasks**: 9 (T001-T009). 100-cap 의 9% — 안전.
- **Task budget**: 단일 Sonnet teammate 가 9 task sequential 처리 → AGENTS.md "≤ 5 tasks per teammate" 와 일부 충돌하지만, 본 Epic 은 task-당 1-2 file 평균이라 dispatch unit 측면에서 small. 만약 너무 큰 부하라 판단되면 T001-T004 (US1 MVP) + T005-T009 (잔여) 로 2-batch 분할 가능.
- **Verification commands**: `contracts/byte-identical-verification.md` 가 모든 검증 절차 정의. T009 가 통합 실행.
- **cascade dep 발견 시**: T003 (instrumentation) 또는 T007 (print) 안에서 추가 UMMAYA-side stub 신설. analytics/index.ts 패턴 일관 적용. 5+ 발견 시 Lead Opus scope 재검토.
- **Commit message format**: Conventional Commits — `feat(2637)`/`docs(2637)`/`chore(2637)`. PR open 후 Codex review 받음.
- **PR 본문**: `Closes #2637` only (Task sub-issues는 close 마커 X — 머지 후 GraphQL 으로 별도 close).
- **avoid**: vague tasks, swap-1 화이트리스트 외 diff, cascade dep 5+ 발견 시 silent fix (반드시 Lead Opus 보고).
