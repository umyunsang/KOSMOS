---
description: "Task list for Epic β v2 — KOSMOS-original UI Residue Cleanup (Initiative #2290) — caller-graph driven"
---

# Tasks: UI Residue Cleanup (Epic β · #2293 · v2)

**Input**: Design documents from `/specs/2293-ui-residue-cleanup/` (worktree at `/Users/um-yunsang/KOSMOS-w-2293/`)
**Prerequisites**: spec.md (v2), plan.md, research.md (v2), data-model.md (v2), quickstart.md (v2), `data/caller-graph.json`, `data/disposition.json`
**Tests**: 본 Epic 은 신규 unit test 작성 0. baseline (`bun test`) 비교로 NEW failure 0 검증.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일 + 의존성 0
- **[Story]**: US1 (28 DELETE), US2 (KEEP utils/permissions), US3 (KEEP ui-l2/permission)

## Path Convention

- Worktree: `/Users/um-yunsang/KOSMOS-w-2293/`
- Spec dir: `specs/2293-ui-residue-cleanup/`
- Source: `tui/src/`
- v2 입력: `data/caller-graph.json` + `data/disposition.json`

---

## Phase 1: Setup ✅

- [X] T001 baseline 박제 — `cd tui && bun typecheck 2>&1 | tee ../specs/.../baseline-typecheck.txt && bun test 2>&1 | tee ../specs/.../baseline-test.txt` (sonnet 1차에서 박제 완료)
- [X] T002 [P] caller-graph.json 박제 (`scripts/build-caller-graph.py` → `data/caller-graph.json` 30 row)
- [X] T003 disposition.json 박제 (Lead 결정 → `data/disposition.json` 31 entry, 28 DELETE + 3 KEEP)

---

## Phase 2: Spec v2 재작성 ✅

- [X] T004 spec.md v2 재작성 (caller-graph 기반 + KEEP/DELETE 분리)
- [X] T005 [P] quickstart.md v2 재작성 (R1~R7 절차, disposition.json 활용)
- [X] T006 [P] research.md v2 재작성 (R-1 자동 박제, R-3 KEEP 결론 정정)
- [X] T007 [P] data-model.md v2 재작성 (CallerGraph + DispositionMatrix entity 추가)

**Checkpoint**: 모든 spec 산출물이 caller-graph.json + disposition.json 인용으로 일관 → Phase 3 진입 가능.

---

## Phase 3: User Story 1 — 28 DELETE target cleanup (Priority: P1) 🎯 MVP

**Goal**: 28 Anthropic dispatcher 잔재 file deletion + 16 caller cleanup → Spec 1633 closure 완료.

**Independent Test**: 28 path 모두 `git ls-files` 0 매칭 + FR-008 grep gate 0 행 + typecheck/test 통과.

### Phase 3a: 0 importer file batch deletion (Lead solo)

- [ ] T008 [US1] 7 file 단순 `git rm`:
  - `tui/src/services/api/{claude,client}.ts` (Anthropic dispatcher)
  - `tui/src/cli/print.ts` (5601 line, claude-code CLI entry)
  - `tui/src/commands/insights.ts` (3164 line, /insights slash command)
  - `tui/src/tools/WebFetchTool/utils.ts` (queryHaiku WebFetch summary)
  - `tui/src/utils/mcp/dateTimeParser.ts` (queryHaiku date parser)
  - `tui/src/utils/shell/prefix.ts` (queryHaiku shell prefix)

### Phase 3b: N importer file batch deletion (Lead solo)

- [ ] T009 [US1] services/api 14 file `git rm`:
  - adminRequests / errorUtils / errors / filesApi / firstTokenDate / grove / logging / overageCreditGrant / promptCacheBreakDetection / referral / sessionIngress / ultrareviewQuota / usage / withRetry
- [ ] T010 [US1] tokenEstimation `git rm`
- [ ] T011 [US1] 기타 6 file `git rm`:
  - `commands/rename/generateSessionName.ts`
  - `components/Feedback.tsx`
  - `services/toolUseSummary/toolUseSummaryGenerator.ts`
  - `utils/permissions/yoloClassifier.ts`
  - `utils/plugins/mcpbHandler.ts`
  - `utils/sessionTitle.ts`

**Checkpoint**: 28 file 모두 git rm 완료. typecheck 깨짐 예상 — Phase 3c 가 caller cleanup 진입.

### Phase 3c: caller cleanup (Lead solo or sonnet teammates per typecheck error count)

- [ ] T012 [US1] `cd tui && bun typecheck` 실행 → 에러 file/line list 추출 → cleanup 분배
- [ ] T013 [US1] [P] tokenEstimation 11 importer cleanup (sonnet teammate 후보, importer list = caller-graph.json #21)
- [ ] T014 [US1] [P] services/api 14 file 의 16 importer cleanup (sonnet teammate 후보)
- [ ] T015 [US1] [P] 기타 8 file 의 ~10 importer cleanup (Lead solo 또는 sonnet teammate)
- [ ] T016 [US1] @anthropic-ai/ import 16 file cleanup (Lead solo 또는 sonnet teammate; import 라인 제거 + 사용처 sdk-compat 의존 정리)

**Checkpoint**: typecheck exit 0 + grep gate 통과까지 반복. transitive caller 발생 시 추가 cleanup.

---

## Phase 4: User Story 2 + 3 — KEEP 박제 (Priority: P2 / P3)

**Goal**: 3 KEEP target (permissionSetup / permissions / ui-l2/permission) 의 보존 결정 + caller graph evidence 박제.

- [ ] T017 [P] [US2] decision-log.md § Cleanup Targets 표에 utils/permissions/permissionSetup KEEP 행 + permissions KEEP 행 추가 (rationale + caller-graph cite)
- [ ] T018 [P] [US3] decision-log.md § ui-l2/permission Decision 섹션 갱신 — KEEP 결정 + Spec 035 receipt UX 박제 + Constitution II 비충돌 박제

**Checkpoint**: decision-log.md 가 31 entry (28 DELETE + 3 KEEP) 모두 박제 + KEEP 의 rationale + caller-graph evidence 명시.

---

## Phase 5: Polish — 검증

- [ ] T019 [P] `cd tui && bun typecheck` exit 0 + 0 errors → `specs/.../after-typecheck.txt` 박제
- [ ] T020 [P] `cd tui && bun test` 실행 + baseline diff → NEW failure 0 검증 → `specs/.../after-test.txt` 박제
- [ ] T021 FR-008 grep gate — `grep -rE 'verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/' tui/src/ --include='*.ts' --include='*.tsx'` 결과 0 행
- [ ] T022 FR-001/FR-002 검증 — `git ls-files tui/src/` 출력에 28 DELETE path 0 매칭 + 8 callsite 0 grep

---

## Phase 6: Ship — commit + PR + CI

- [ ] T023 commit (quickstart.md § 7.1 절차) — Authority cite 4 reference + caller-graph + disposition 박제
- [ ] T024 push + PR (Closes #2293)
- [ ] T025 CI watch (`gh pr checks <PR#> --watch --interval 15`)
- [ ] T026 Copilot review gate 확인 (push 후 2분, 안 풀리면 GraphQL 재요청 또는 사용자 bypass label 요청)
- [ ] T027 Codex review handling (`gh api repos/.../comments` → P1 모두 해소)

**Checkpoint**: PR mergeable 상태 + 모든 acceptance gate 통과.

---

## Dependencies & Execution Order

- Phase 1 (T001-T003) ✅ → Phase 2 (T004-T007) ✅ → Phase 3a (T008) → Phase 3b (T009-T011) → Phase 3c (T012-T016) → Phase 4 (T017-T018) → Phase 5 (T019-T022) → Phase 6 (T023-T027)
- T013, T014, T015, T016 [P]: sonnet teammates 병렬 가능 (다른 importer 영역)
- T017, T018 [P]: 다른 섹션 → 병렬
- T019, T020 [P]: typecheck + test 동시 실행

---

## Implementation Strategy

### Lead-solo heavy (default)

본 Epic 은 단순 `git rm` + import 정리 위주라 Lead solo 가 효율. Sonnet teammate 는 typecheck 에러가 광범위 (≥ 10 file) 인 caller cleanup 만 위임.

### Sonnet teammate trigger

T012 에서 typecheck 결과를 분석 → 에러 file 수 ≥ 10 → file 영역별로 sonnet 분배 (≤ 10 file/teammate, ≤ 5 task/teammate). sonnet 책임 = 코드 변경 + WIP commit 만; push/PR/CI/Codex = Lead.

### Risk handling

- HIGH risk (tokenEstimation): caller cleanup 후 typecheck 재돌림 + bun test 재돌림 → 깨지면 rollback + caller cleanup 재시도
- MEDIUM risk (cli/print, commands/insights, errorUtils, errors, logging, promptCacheBreakDetection, sessionIngress, withRetry, WebFetchTool/utils, yoloClassifier, mcpbHandler): typecheck 에러를 cleanup truth source 로 사용
- LOW risk (나머지): 추가 검증 0

---

## Notes

- 총 task 수 = 27 (≪ 90 cap)
- 모든 산출물은 `specs/2293-ui-residue-cleanup/` 또는 `tui/src/` 변경
- `git rm` + Edit 위주 — 신규 파일은 spec/data 문서 만
- 신규 dependency 0 (FR-008)
- v1 의 30 일괄 deletion 가설을 v2 가 caller-graph 박제로 정정 — 이 정정 자체가 본 Epic 의 핵심 산출물
