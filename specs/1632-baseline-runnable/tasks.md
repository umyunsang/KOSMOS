---
description: "Task list for Epic #1632 — P0 · Baseline Runnable (CC src 컴파일·런타임 복구)"
---

# Tasks: P0 · Baseline Runnable (CC src 컴파일·런타임 복구)

**Input**: Design documents from `/specs/1632-baseline-runnable/`
**Prerequisites**: [plan.md](./plan.md) · [spec.md](./spec.md) · [research.md](./research.md) · [quickstart.md](./quickstart.md)
**Epic**: [#1632](https://github.com/umyunsang/KOSMOS/issues/1632)

**Tests**: 단위 테스트는 `feature()` stub(US3)에 한정 포함. US1/US2 는 시각·수치 검증만
수행(quickstart.md 절차 기준) — P0 는 인프라 복구로, 새 기능을 만들지 않으므로 TDD
요구사항 없음.

**Organization**: 3 개 User Story 별 Phase 분리. Foundational Phase 가 모든 Story 를
블록.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일·의존 없음 → 병렬 가능
- **[Story]**: US1 (splash render · P1) · US2 (test floor · P2) · US3 (feature stub · P2)
- 모든 경로는 repo root 기준 절대경로(`tui/…`)로 명시

## Path Conventions

- 본 Epic 의 모든 변경은 `tui/` 서브트리에 국한 (`backend/`, `docs/`, `.specify/` 미터치)
- 루트 스펙 디렉터리: `specs/1632-baseline-runnable/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Setup 작업 없음 — `tui/` 디렉터리와 Bun v1.2.x 환경은 Epic #287 에서
이미 초기화됨. 본 Phase 는 스킵.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: 세 User Story 모두에게 필요한 compile/runtime 해석 토대 — 의존성 설치 ·
tsconfig path 매핑 · 이중 중첩 디렉터리 flatten. 이 Phase 완료 전에는 어떤 Story 도
검증 불가 (모든 import 가 실패).

**⚠️ CRITICAL**: Phase 3+ 진입 전에 완료 필수.

- [ ] T001 [P] Add 5 runtime dependencies to `tui/package.json` `dependencies` (FR-001):
  - `@commander-js/extra-typings` · `chalk` · `lodash-es` · `chokidar` · `@anthropic-ai/sdk`
  - 버전은 기본 `^latest` (bun install 이 lockfile 확정)
  - `type` · `engines` · 기존 deps 는 수정 금지

- [ ] T002 Execute `bun install` in `tui/` and commit resulting lockfile (FR-001):
  - 의존: T001 완료 후
  - `cd tui && bun install` — 0 warning / 0 error 확인 (quickstart.md §1)
  - `tui/bun.lock*` (기존 프로젝트 관례 파일) 를 커밋에 포함

- [ ] T003 [P] Extend `tui/tsconfig.json` `compilerOptions.paths` with two new entries (FR-003, FR-004):
  - `"src/*": ["./src/*"]` — CC 원본의 bare-root import 지원
  - `"bun:bundle": ["./src/stubs/bun-bundle.ts"]` — `feature()` stub 매핑
  - 기존 매핑 6 개 (`@/*`, `react/compiler-runtime`, `lodash-es/*`, `@alcalzone/ansi-tokenize`, `semver`, `usehooks-ts`, `@anthropic-ai/sdk/*`) 는 보존

- [ ] T004 [P] Flatten `tui/src/constants/constants/` into `tui/src/constants/` via `git mv` (FR-007):
  - **비충돌 파일** 20 개 (`apiLimits.ts`, `betas.ts`, `common.ts`, `cyberRiskInstruction.ts`, `errorIds.ts`, `files.ts`, `github-app.ts`, `keys.ts`, `oauth.ts`, `outputStyles.ts`, `product.ts`, `prompts.ts`, `spinnerVerbs.ts`, `system.ts`, `systemPromptSections.ts`, `toolLimits.ts`, `tools.ts`, `turnCompletionVerbs.ts`) → 그대로 상위 이동
  - **충돌 3 개** (`figures.ts` · `messages.ts` · `xml.ts`) → 기존 상위 파일(7 줄 KOSMOS stub) **유지**, 하위 CC 원본 **삭제**
    - 근거: consumer 는 canonical `from './constants/figures'` 로 이미 상위 stub 을 사용 중. `grep -rn "constants/constants" tui/src/` = 0 건 (research.md Decision 4 보강)
  - 종료 후 `tui/src/constants/constants/` 디렉터리 제거 (`rmdir` 또는 빈 디렉터리 자연 삭제)

- [ ] T005 [P] Flatten `tui/src/services/services/` into `tui/src/services/` via `git mv` (FR-007):
  - **하위 디렉터리 merge**: `services/services/analytics/*` · `services/services/api/*` 의 파일을 `services/analytics/*` · `services/api/*` 로 이동
  - **충돌 4 개** (`services/analytics/index.ts` · `services/api/errors.ts` · `services/api/overageCreditGrant.ts` · `services/api/referral.ts`):
    - `diff -u <top-level> <nested>` 수행 → 두 버전이 동일하면 nested 삭제, 다르면 상위 유지 + nested 삭제 (Decision 4 규칙: consumer 가 이미 canonical 경로로 작동 중인 상위 버전이 authoritative)
  - **비충돌 신규 파일** (예: `services/services/api/dumpPrompts.ts`, `services/services/api/bootstrap.ts`, `services/services/analytics/growthbook.ts` 등) → 상위로 이동
  - 종료 후 `tui/src/services/services/` 디렉터리 제거

**Checkpoint**: Phase 2 완료 시 (a) `bun install` 0 warn, (b) tsconfig 가 모든 import
를 resolve, (c) 이중 중첩 경로 0 — 세 Story 의 implementation 병렬 착수 가능.

---

## Phase 3: User Story 3 - feature flag stub (Priority: P2)

**Goal**: 960 개 `feature()` call-site 가 단일 stub 으로 수렴해 전부 `false` 반환.

**Independent Test**: `bun test tui/tests/unit/stubs/bun-bundle.test.ts` — stub 이 모든
입력에 대해 `false` 를 동기 반환하고 예외를 던지지 않음.

### Implementation for User Story 3

- [ ] T006 [P] [US3] Create `tui/src/stubs/bun-bundle.ts` with `feature` export (FR-003):
  - 내용: `export function feature(_flag: string): boolean { return false; }`
  - 의존: T003 (tsconfig 에 `bun:bundle` path 등록됨)
  - 파일 헤더에 본 Epic 과 후속 P1 정리 이슈(#1633) 주석 1 줄 포함

- [ ] T007 [P] [US3] Add unit test at `tui/tests/unit/stubs/bun-bundle.test.ts` (FR-003 수용 기준):
  - 17 개 known flag (`COORDINATOR_MODE`, `KAIROS`, `KAIROS_BRIEF`, `KAIROS_CHANNELS`, `TRANSCRIPT_CLASSIFIER`, `DIRECT_CONNECT`, `LODESTONE`, `SSH_REMOTE`, `UDS_INBOX`, `BG_SESSIONS`, `UPLOAD_USER_SETTINGS`, `WEB_BROWSER_TOOL`, `CHICAGO_MCP`, `PROACTIVE`, `HARD_FAIL`, `CCR_MIRROR`, `AGENT_MEMORY_SNAPSHOT`, `BRIDGE_MODE`) 각각 `false` 검증
  - 미지의 flag (`"UNKNOWN_FLAG_XYZ"`) 도 `false` 반환 + throw 없음 검증
  - `bun test tui/tests/unit/stubs/bun-bundle.test.ts` 단독 실행 시 PASS

**Checkpoint**: US3 완료 — `bun:bundle.feature` 심볼이 TypeScript 컴파일·런타임·테스트
세 표면 모두에서 정상 resolve.

---

## Phase 4: User Story 1 - 스플래시 렌더 (Priority: P1) 🎯 MVP

**Goal**: `bun run src/main.tsx` 실행 시 CC 베이스라인 스플래시가 3 초 이상 크래시
없이 렌더.

**Independent Test**: quickstart.md §2 + §5 절차 — 스플래시 3 초 유지 + 부트스트랩
외부 egress 0 확인.

### Implementation for User Story 1

- [ ] T008 [US1] Neutralize Anthropic-only bootstrap side-effects in `tui/src/main.tsx` (FR-002, FR-005, FR-008):
  - 의존: T002 (deps 설치), T003 (paths), T004-T005 (flatten), T006 (stub)
  - **주석 처리 대상** (호출만 비활성, import 는 유지):
    - L11–12 `profileCheckpoint('main_tsx_entry')`
    - L15–16 `startMdmRawRead()`
    - L19–20 `startKeychainPrefetch()`
    - `initializeTelemetryAfterTrust` · `initializeGrowthBook` · `refreshGrowthBookAfterAuthChange` 의 호출부
    - `fetchBootstrapData` · `prefetchPassesEligibility` · `prefetchOfficialMcpUrls` · `prefetchAwsCredentialsAndBedRockInfoIfSafe` · `prefetchGcpCredentialsIfSafe` 의 호출부
    - `src/services/analytics/*` 4 개 import 의 사용처 (호출 삭제, import 유지)
  - **표식**: 각 주석 블록 위에 `// [P0 neutralized] see Epic #1633 P1 dead code elimination` 1 줄 추가 → P1 에서 `git grep '\[P0 neutralized\]'` 로 일괄 추적
  - `src/main.tsx` 의 다른 구조(imports, React render tree, command parser) 는 건드리지 않음 (메모리 `CC TUI 90% fidelity`)

- [ ] T009 [US1] Verify splash renders for ≥3s without crash via manual run (SC-001, FR-002):
  - 의존: T008 완료 후
  - 명령: `cd tui && bun run src/main.tsx` (quickstart.md §2)
  - 합격 조건: 3 초 이상 스플래시 안정 유지 (spec SC-001) · `Ctrl+C` 종료 시 uncaught stack 0 건 · exit code 0 또는 130
  - 결과를 PR 본문 또는 후속 task 코멘트에 기록 (관찰 로그 + 스크린샷 또는 asciinema)

- [ ] T010 [US1] Verify bootstrap egress = 0 via packet capture (SC-004, FR-008):
  - 의존: T009 (실행 경로 검증됨)
  - 절차: quickstart.md §5 의 `tcpdump` 스니펫 실행 — `api.anthropic.com` · `api.growthbook.io` · 기타 telemetry 호스트 대상 SYN 0 건 확인
  - 결과(패킷 카운트 + 호스트 리스트)를 PR 코멘트에 기록

**Checkpoint**: US1 완료 — MVP 달성. Epic #1632 의 acceptance criterion 3 개 중 두 개
(splash 3s, bun install clean) 확보. 이 시점에서 Epic 의 데모 가능.

---

## Phase 5: User Story 2 - 테스트 회귀 플로어 (Priority: P2)

**Goal**: `bun test` 통과 테스트 수 ≥ 540 (upstream 549 대비 ≥ 98%).

**Independent Test**: `bun test` 한 줄 — Passed 수가 threshold 이상.

### Implementation for User Story 2

- [ ] T011 [US2] Run `bun test` and verify `Passed ≥ 540` (SC-003, FR-006):
  - 의존: T002, T003, T004, T005, T006, T008 (모든 foundational + US1/US3 완료)
  - 명령: `cd tui && bun test 2>&1 | tee /tmp/kosmos-p0-bun-test.log`
  - 합격 조건: 요약 라인에서 `Passed: N` (N ≥ 540). 실패한 테스트의 원인이 "missing dep / module not found / doubled nesting" 중 **어느 것도 아님**을 stderr 샘플로 증명
  - 결과(통과·실패 수, 샘플 실패 reason) 를 PR 본문에 기록

- [ ] T012 [US2] Document 540→549 test gap triage in `specs/1632-baseline-runnable/test-gap.md`:
  - 의존: T011 완료 후
  - 내용: T011 에서 관찰된 실패 테스트를 세 카테고리로 분류 —
    (a) **P1 정리 대기** (Anthropic API · OAuth · MDM · GrowthBook 등 #1633 에서 삭제 예정)
    (b) **skip 마킹 필요** (P0 범위에서 즉시 재현 불가, `.skip` 또는 `describe.skip` 주석 권장)
    (c) **불명 / 재조사** (P1 에도 속하지 않는 진짜 버그 — 후속 Epic 필요)
  - 각 카테고리 실패 테스트 ID + 한 줄 사유 리스트. `test-gap.md` 는 post-merge 참고용, Epic #1633 가 반드시 참조

**Checkpoint**: US2 완료 — 회귀 플로어가 CI 에 고정 가능한 수치로 문서화.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: P0 완료 후 후속 Epic 가 변경을 발견·수용하기 위한 표식·검증 마무리.

- [ ] T013 [P] Run full quickstart.md end-to-end validation on clean checkout:
  - 의존: T001–T012 완료
  - 절차: git worktree 또는 fresh clone 에서 quickstart.md §1–§5 전체 실행
  - **추가 합격 조건 (FR-009 명시 검증)**: `cd tui && bun x tsc --noEmit` 0 error 로 종료 — @anthropic-ai/sdk 타입 + any-stub 조합이 TS 컴파일러에 깨끗이 해석됨을 증명
  - 합격: 모든 단계 green · 5 분 이내 완료 (SC-005)
  - 결과(소요 시간, 각 단계 exit status, tsc 결과) 를 PR 본문 Test plan 에 기록

**Checkpoint**: 전체 Epic #1632 acceptance — `bun install` clean · splash ≥3s · `bun
test ≥540` · egress 0 · P1 표식 grep-able.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: 스킵
- **Foundational (Phase 2)** T001–T005: 전부 완료 전에 Phase 3+ 진입 금지
  - T001 → T002 (package.json 편집 → bun install)
  - T003/T004/T005 는 T001 과 병렬 (서로 다른 파일)
- **US3 (Phase 3)** T006–T007: T003 완료 후 착수, US1·US2 와 병렬 가능
- **US1 (Phase 4)** T008 → T009 → T010:
  - T008 은 T002·T003·T004·T005·T006 전부 필요
  - T009 는 T008 필요
  - T010 은 T009 필요
- **US2 (Phase 5)** T011 → T012: T008·T006 필요 (main.tsx·stub 완성 후에야 bun test 가 의미)
- **Polish (Phase 6)** T013: T001–T012 전부 완료 후

### User Story Dependencies

- **US3 (P2)**: 독립 — Foundational 만 요구 (T003) · stub·test 는 타 story 와 무관
- **US1 (P1)**: foundational + US3 산출물(stub) 필요 — main.tsx 가 `feature()` 를 import
- **US2 (P2)**: foundational + US1 산출물 필요 — `bun test` 는 전체 import 그래프 검증

### Within Each Story

- US3: stub 파일 생성(T006) → 단위 테스트(T007). 두 task 는 서로 다른 파일이라 [P].
- US1: 편집(T008) → 실행 검증(T009) → egress 검증(T010). 순차.
- US2: 실행(T011) → 분류 문서(T012). 순차.

### Parallel Opportunities

- **Foundational 내부**: T001/T003/T004/T005 는 네 개의 서로 다른 파일·디렉터리 대상 → 병렬 가능 (단 T002 는 T001 이후)
- **US3 내부**: T006/T007 병렬
- **Story 간**: Foundational 완료 후 US3 전담자와 US1 전담자가 병렬 착수 가능 (US2 는 US1 완료 대기)

---

## Parallel Example: Foundational Phase

```bash
# Developer A — package deps
Task T001: Edit tui/package.json (add 5 deps)
Task T002: cd tui && bun install; commit lockfile

# Developer B (병렬)
Task T003: Edit tui/tsconfig.json paths
Task T004: git mv tui/src/constants/constants/* → tui/src/constants/
Task T005: git mv tui/src/services/services/* → tui/src/services/ (merge carefully)
```

## Parallel Example: After Foundational

```bash
# Developer A — US3
Task T006: Create tui/src/stubs/bun-bundle.ts
Task T007: Create tui/tests/unit/stubs/bun-bundle.test.ts

# Developer B (병렬)
Task T008: Edit tui/src/main.tsx (neutralize 부트스트랩 사이드이펙트)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

Epic #1632 의 시연 가치 = "스플래시 뜸". MVP 경로:

1. Foundational (T001–T005) 완료 — bun install · tsconfig · flatten
2. US3 의 T006 (stub 파일만) — US1 의 main.tsx 가 import 할 수 있도록
3. US1 전체 (T008–T010) — 스플래시 렌더·egress 검증
4. **STOP and VALIDATE**: quickstart.md §1–§2 단독 시연 가능

그 후 US3 의 T007 (테스트) + US2 (테스트 floor) 를 연속 추가.

### Incremental Delivery

- **마일스톤 A**: Foundational + US3 + US1 = Epic 의 demo 가능 (MVP · SC-001 충족)
- **마일스톤 B**: A + US2 = CI gate 고정 가능 (SC-003 충족)
- **마일스톤 C**: B + Polish = PR 머지 준비 (SC-005 · 전체 acceptance)

### Parallel Team Strategy

- Lead (Opus) — spec/plan/review 감독 (이 문서 작성 · PR 리뷰)
- Teammate A (Sonnet) — Foundational (T001/T002/T003) + US1 (T008)
- Teammate B (Sonnet) — Foundational (T004/T005) + US3 (T006/T007)
- Teammate C (Sonnet) — US1 검증 (T009/T010) + US2 (T011/T012) + Polish (T013)

3 개 Teammate 병렬 착수. Foundational 단계에서만 동기화 한 번 필요.

---

## Notes

- **Task budget**: 13 tasks · 90 cap 대비 14% 사용 — 여유 충분.
- **Integrated PR only**: 메모리 `Integrated PR only` — 13 task 전부를 단일 PR (`Closes #1632`) 에 묶어 제출. Task 단위 PR 금지.
- **Commit cadence**: 13 task 각각 conventional commit 1 개씩 권장 (`feat(P0):`, `chore(P0):`, `test(P0):` prefix). Task 완료 → commit → 다음 task.
- **Copilot Review Gate**: 모든 push 후 GraphQL `requestReviewsByLogin` 으로 Copilot 재리뷰 수동 요청 (메모리 `Copilot re-review`).
- **Verification before completion**: 각 task 의 "합격 조건" 을 실제 명령 실행 결과(exit status · 로그 샘플)로 증명 후 체크박스 완료. 선언만으로 체크 금지 (헌법 · verification-before-completion 원칙).
- **Avoid**: `--force` push, `--no-verify`, feature flag 17 개 중 어느 하나라도 `true` 로 설정, Anthropic API 실호출, 개발자 도구(Read/Write/Edit/Bash/Glob/Grep/NotebookEdit) 복구 시도.
