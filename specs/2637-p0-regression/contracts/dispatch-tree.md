# Dispatch Tree — Epic A P0 회귀 즉시 복구

**Epic**: #2637 · **Branch**: `feat/2637-p0-regression` · **Date**: 2026-05-03

## 결정: 단일 Sonnet teammate sequential

**근거**: 9건 회귀 모두 P0 + 같은 영역 (constants/types/utils/services) 파일 충돌 가능 + cascade dep 발견 시 sequential 처리 필요. AGENTS.md § Agent Teams 의 "1-2 tasks → Lead solo. 3+ independent tasks → 병렬" 원칙은 "independent" 가 핵심. 본 Epic 의 7 task 는 dependency 가 있음 (T004 instrumentation 후 T005 wire / T002 constants 후 T006 print).

## Layer 1 — Epic-level (Lead Opus)

본 Epic 은 **Lead Opus α** (현재 세션) 가 단독 owner. 다른 Epic (예: Epic β #2293 Spec 2522) 와 병렬이지만 영역 완전 분리 (TUI types/constants/utils/services ↔ Python 백엔드 + prompts).

| 단계 | Owner | 산출물 |
|---|---|---|
| Spec 작성 (`/speckit-specify`) | Lead Opus | spec.md + checklists/requirements.md |
| Plan 작성 (`/speckit-plan`) | Lead Opus | plan.md + research.md + data-model.md + quickstart.md + contracts/ |
| Tasks 작성 (`/speckit-tasks`) | Lead Opus | tasks.md (~7 task) |
| Analyze (`/speckit-analyze`) | Lead Opus | constitution compliance 검증 |
| TasksToIssues (`/speckit-taskstoissues`) | Lead Opus | GitHub Task issues 7개 + Sub-Issues API link |
| Implement (`/speckit-implement`) | Lead Opus + Sonnet teammate | code edits + tests + commits |
| PR open + CI watch + Codex review | Lead Opus | PR closed |

## Layer 2 — Task-level inside Epic (Sonnet teammate)

```text
T001 events_mono PORT (R-1a/b/c)            ┐
T002 Constants/Types Proxy stub PORT (R-2*)  │
T003 oauth.ts PORT + swap-1 replace (R-4)    │
T004 instrumentation.ts PORT + 8 deps + cascade stub (R-5) ├─ 단일 Sonnet sequential
T005 toolExecution.ts wire (R-6)             │
T006 cli/print.ts PORT + cascade stub (R-3 + R-3-cascade) │
T007 Stage-1 NO-OP 박제 + decisions.md 업데이트 + 최종 검증 (R-7) ┘
```

**Dispatch 규칙**:
- 단일 Sonnet teammate (`sonnet-2637-impl`) 가 T001 → T007 순차 실행
- 각 task 후 commit (Conventional Commits) — `git push` 는 Lead Opus 가 수행 (AGENTS.md § Agent Teams)
- 각 task 가 ≤ 5 task 안에 ≤ 10 file 변경 — 본 Epic 은 task-당 평균 1-2 file 이라 OK
- task 간 dependency:
  - T004 → T005 (instrumentation 부팅 후 toolExecution wire 가 OTEL routing 활성화)
  - T002 → T006 (constants stub 정합 후 print 가 import 가능)
  - T001-T003 → independent (병렬 가능하지만 cascade 위험으로 sequential)

## Sonnet teammate prompt (≤ 30 lines)

```
너는 sonnet-2637-impl. KOSMOS Epic A (#2637, P0 회귀 즉시 복구) 의 implementation teammate.

워크트리: /Users/um-yunsang/KOSMOS-w-2637 (branch: feat/2637-p0-regression)
스펙: specs/2637-p0-regression/spec.md
계획: specs/2637-p0-regression/plan.md
빠른시작: specs/2637-p0-regression/quickstart.md
데이터모델: specs/2637-p0-regression/data-model.md

작업:
- specs/2637-p0-regression/tasks.md 의 T001-T007 을 순차 실행
- 각 task 의 quickstart.md 명령 따르기 (cp/edit/wire)
- task 종료마다 verification command (data-model.md § VerificationContract V1-V9) 실행
- task 종료마다 commit (Conventional Commits): feat(2637): T0NN <subject>
- 마지막 task 후 tasks.md 의 [X] 마커 모두 업데이트

원칙:
- CC = source of truth, byte-identical default
- swap-1 종속 식별자만 KOSMOS-side 로 교체 (data-model.md § Swap1IdentifierWhitelist)
- 누락/추측/임의 발산 금지
- typecheck 회귀 발견 시 cascade dep stub 패턴 (analytics/index.ts) 참조
- git push / gh pr create / Codex 응답 = Lead Opus 가 수행, 너는 코드 + 테스트 + commit 만

검증 fail 시 root cause 분석 후 fix, 그래도 fail 시 Lead Opus 에 보고.
```

## 충돌 차단

- 다른 worktree `/Users/um-yunsang/KOSMOS-w-2522/` (Spec 2522 Tool surface v4, Epic #2579, 23/49 진행) 와 영역 완전 분리:
  - 본 Epic A: TUI types/constants/utils/services
  - Spec 2522: Python 백엔드 + prompts + docs/api
- 충돌 가능성 0
- 단 main rebase 시 양쪽 변경 동시 반영 가능성 인지 (Lead Opus 가 PR open 시점에 rebase)

## Failure mode handling

- T001/T002/T003 typecheck 회귀 → cascade dep 발견 → 추가 cascade stub 신설 → spec FR-016 처럼 follow-up FR 추가 + Lead Opus 에 보고
- T004 dependency install 실패 → bun add 명령 재시도 + offline cache 확인 → 실패 시 Lead Opus 에 보고
- T005 OTEL trace 누락 → KOSMOS toolSpans.ts attribute namespace 정합 재검증
- T006 cli/print.ts cascade dep 누락 다수 발견 → 본 Epic scope 외부로 deferred (Lead Opus 결정 + spec 업데이트)
- T007 audit 재실행 시 D-bucket 잔존 → root cause 분석 후 추가 fix
