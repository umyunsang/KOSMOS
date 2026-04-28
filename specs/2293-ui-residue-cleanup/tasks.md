---
description: "Task list for Epic β — KOSMOS-original UI Residue Cleanup (Initiative #2290)"
---

# Tasks: UI Residue Cleanup (Epic β · #2293)

**Input**: Design documents from `/specs/2293-ui-residue-cleanup/` (worktree at `/Users/um-yunsang/KOSMOS-w-2293/`)
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, quickstart.md
**Tests**: 본 Epic 은 신규 unit test 작성 0. baseline (`bun test`) 비교로 NEW failure 0 검증.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일 + 의존성 0
- **[Story]**: US1 (services/api), US2 (permissions), US3 (KOSMOS-only Tools)

## Path Convention

- Worktree: `/Users/um-yunsang/KOSMOS-w-2293/`
- Spec dir: `specs/2293-ui-residue-cleanup/`
- Source: `tui/src/`

---

## Phase 1: Setup

- [ ] T001 baseline 박제 — `cd tui && bun install && bun typecheck 2>&1 | tee ../specs/2293-ui-residue-cleanup/baseline-typecheck.txt && bun test 2>&1 | tee ../specs/2293-ui-residue-cleanup/baseline-test.txt`
- [ ] T002 [P] `specs/2293-ui-residue-cleanup/decision-log.md` 빈 템플릿 작성 (Cleanup Targets / KOSMOS-only Tool Decisions / Callsite Migrations / ui-l2/permission Decision 4 섹션)

---

## Phase 2: Foundational — importer 추적

- [ ] T003 services/api 17 잔재 importer 추적 — `grep -rE` 결과를 `decision-log.md § Cleanup Targets` 표에 박제 (per quickstart § 2.1)
- [ ] T004 8 callsite (queryHaiku/queryWithModel/verifyApiKey) 의 caller 평가 + research.md § R-2 매트릭스 적용 결정 박제 (`decision-log.md § Callsite Migrations`)
- [ ] T005 utils/permissions/ 3 잔재 + ui-l2/permission.ts importer 추적 (per quickstart § 3.1)

**Checkpoint**: importer 그래프 박제 완료 — US1/US2/US3 진입 가능.

---

## Phase 3: User Story 1 — services/api closure (Priority: P1) 🎯 MVP

**Goal**: 17 services/api + 1 tokenEstimation deletion + 8 callsite migration → Spec 1633 closure 완료.

**Independent Test**: `git ls-files tui/src/services/api/` 출력 0 행 (또는 KOSMOS-equivalent 만) + `grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/` 0 행.

- [ ] T006 [US1] 17 services/api 파일 + 1 tokenEstimation.ts 삭제 — 각 importer cleanup 후 `git rm` (per quickstart § 2.2)
- [ ] T007 [US1] 8 callsite migration — research.md § R-2 매트릭스 결정대로 caller block 삭제 또는 KOSMOS 등가 호출 교체 (cli/print.ts, commands/insights.ts, commands/rename/generateSessionName.ts, components/Feedback.tsx, services/toolUseSummary/toolUseSummaryGenerator.ts, tools/WebFetchTool/utils.ts, utils/mcp/dateTimeParser.ts, utils/sessionTitle.ts, utils/shell/prefix.ts)
- [ ] T008 [US1] @anthropic-ai/ import 제거 — `tui/src/utils/plugins/mcpbHandler.ts` + 모든 grep 매치 (per quickstart § 5)
- [ ] T009 [US1] grep gate — `grep -rE 'queryHaiku|queryWithModel|verifyApiKey|@anthropic-ai/' tui/src/` 결과 0 행 검증

**Checkpoint**: US1 단독으로 Spec 1633 closure 완료 — typecheck 통과 가능 상태.

---

## Phase 4: User Story 2 — Constitution II permission residue 제거 (Priority: P2)

**Goal**: 3 utils/permissions/ + 1 ui-l2/permission.ts 평가 + (대부분) deletion → Constitution II compliance 검증.

**Independent Test**: `grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier' tui/src/` 0 행.

- [ ] T010 [P] [US2] utils/permissions/ 3 파일 deletion — caller cleanup 후 `git rm tui/src/utils/permissions/{permissionSetup,permissions,yoloClassifier}.ts`
- [ ] T011 [US2] schemas/ui-l2/permission.ts 평가 + (대부분) deletion. caller 0 면 `git rm`. caller 발견 시 Decision Log 에 keep + 사유 + Constitution II 상충 검토 (Constitution II 강제 — bar 매우 높음, default delete)
- [ ] T012 [US2] Constitution II grep gate — `grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference' tui/src/` 결과 0 행 검증

**Checkpoint**: US2 단독으로 Constitution II 코드 레벨 enforce 완료.

---

## Phase 5: User Story 3 — 6 KOSMOS-only Tool 평가 + deletion (Priority: P3)

**Goal**: 6 도구 평가 → 시민 use case 0 도구는 deletion + tools.ts registry entry 제거.

**Independent Test**: 6 도구 디렉토리 모두 git ls-files 에서 사라짐 (또는 keep 결정 도구는 Decision Log + use case 인용).

- [ ] T013 [P] [US3] 6 KOSMOS-only Tool 평가 (research.md § R-4 매트릭스) — 각 도구의 README/주석 + caller grep 으로 시민 use case 검증; 결정을 `decision-log.md § KOSMOS-only Tool Decisions` 표에 박제
- [ ] T014 [US3] DELETE 결정 도구 디렉토리 제거 + `tui/src/tools.ts` registry entry + import 제거 (per quickstart § 4.2)
- [ ] T015 [US3] Decision Log 검증 — 7 entries (6 Tool + 1 ui-l2/permission) 모두 decision/rationale/references 채움

**Checkpoint**: US3 단독으로 도구 registry 가 시민-relevant 만 노출.

---

## Phase 6: Polish — 검증 + commit + PR

- [ ] T016 [P] `cd tui && bun typecheck` exit 0 + 0 errors 검증; 결과를 `specs/2293-ui-residue-cleanup/after-typecheck.txt` 박제
- [ ] T017 [P] `cd tui && bun test` 실행 + baseline 비교; NEW failure 0 검증; 결과를 `after-test.txt` 박제
- [ ] T018 종합 grep gate (FR-008) — `grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference|verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/' tui/src/` 0 행
- [ ] T019 commit + push + PR — quickstart § 7 절차대로
- [ ] T020 CI monitoring (`gh pr checks --watch`) + Codex P1 처리 + 머지 가능 상태로 보고

**Checkpoint**: PR mergeable 상태 + 모든 acceptance gate 통과.

---

## Dependencies & Execution Order

- Phase 1 (T001 baseline) → Phase 2 (T003-T005 추적) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6 (Polish)
- US1, US2, US3 는 의존성 없으나 순차 권장 (각자 grep gate 가 누적적이라 순서대로 진행 시 검증 단순)
- T010 [P]: US2 와 US1 가 다른 파일 → 병렬 가능
- T013 [P]: US3 와 US1/US2 다른 파일 → 병렬 가능
- T016 [P], T017 [P]: typecheck + test 동시 실행 가능

---

## Implementation Strategy

### MVP First (US1 단독)

1. Phase 1+2 완료
2. US1 (T006-T009) 만 실행 → Spec 1633 closure 산출물
3. **STOP and VALIDATE**: typecheck 통과 + bun test NEW failure 0
4. PR (또는 incremental US2/US3 추가 후 PR)

### Parallel Execution

T010, T013, T016, T017 [P] 병렬 가능. 단 본 Epic 은 단일 worktree 단일 reviewer 환경이라 sequential 권장.

---

## Notes

- 총 task 수 = 20 (≪ 90 cap)
- 모든 산출물은 `specs/2293-ui-residue-cleanup/` 또는 `tui/src/` 변경
- `git rm` 위주 — 신규 파일 0 (Decision Log 1 + baseline/after .txt 4 만)
- 신규 dependency 0 (FR-008)
