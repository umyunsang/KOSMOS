# Dispatch Tree — UI Residue Cleanup (Epic β · v2)

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Tasks**: [tasks.md](./tasks.md)
**Authority**: AGENTS.md § Agent Teams (Layer 1 + Layer 2)

본 Epic 은 **Lead-solo heavy** dispatch 로 진행. Sonnet teammate 는 Phase 3c 의 caller cleanup 영역이 광범위 (typecheck 에러 ≥ 10 file) 일 때만 호출. file 변경 자체가 단순 (`git rm` + 1-line import edit) 이라 Lead 컨텍스트 부담 작음.

---

## Layer 1 — Epic-level

이 Epic 은 **Lead Opus β = 이번 conversation** 단독. Epic δ #2295 는 별도 Lead Opus session 에서 진행 (핸드오프 v4 가 명시한 분리).

---

## Layer 2 — Task-level (within Epic β)

```
Phase 1+2 (Setup + Spec v2 재작성, T001-T007):
  Lead solo ✅ (이번 turn 진행)
    ├─ caller-graph.json 박제 (자동)
    ├─ disposition.json 박제 (Lead 결정)
    └─ spec.md / quickstart.md / research.md / data-model.md / tasks.md / dispatch-tree.md v2 재작성

Phase 3a (Single deletion batch, T008):
  Lead solo
    └─ 7 file `git rm` (claude / client / cli/print / commands/insights / WebFetchTool/utils / dateTimeParser / shell/prefix)

Phase 3b (Bulk deletion, T009-T011):
  Lead solo
    ├─ T009: services/api 14 file `git rm`
    ├─ T010: tokenEstimation `git rm`
    └─ T011: 6 기타 file `git rm`

Phase 3c (Caller cleanup — typecheck driven, T012-T016):
  Lead solo first: T012 `bun typecheck` 으로 에러 file/line list 추출
    ↓ (분배 결정)
  Lead solo or Sonnet teammates 병렬 (≤ 10 file/teammate):
    ├─ sonnet-A (optional): T013 tokenEstimation 11 importer cleanup
    ├─ sonnet-B (optional): T014 services/api 14 file 의 16 importer cleanup
    ├─ sonnet-C (optional): T015 기타 8 file 의 ~10 importer cleanup
    └─ Lead solo (default): T016 @anthropic-ai/ import 16 file cleanup

  Sonnet teammate trigger 조건:
    - typecheck 에러 file 수 ≥ 10 → sonnet 위임
    - typecheck 에러 file 수 < 10 → Lead solo

Phase 4 (KEEP 박제, T017-T018):
  Lead solo (병렬 [P]: 다른 markdown 섹션)
    ├─ T017: decision-log.md § Cleanup Targets 의 utils/permissions KEEP 행 추가
    └─ T018: decision-log.md § ui-l2/permission Decision 갱신

Phase 5 (Verify, T019-T022):
  Lead solo (병렬 [P]: typecheck + test 동시)
    ├─ T019: bun typecheck → after-typecheck.txt 박제
    ├─ T020: bun test → after-test.txt 박제 + baseline diff
    ├─ T021: FR-008 grep gate
    └─ T022: FR-001/FR-002 검증

Phase 6 (Ship, T023-T027):
  Lead solo (sequential)
    ├─ T023: commit (Authority cite + caller-graph + disposition)
    ├─ T024: push + gh pr create
    ├─ T025: gh pr checks --watch
    ├─ T026: Copilot review gate
    └─ T027: Codex P1 처리
```

---

## Sonnet teammate prompt template (Phase 3c only, 호출 시점에 작성)

```
Sonnet 너는 Sonnet teammate. Lead Opus β 가 Epic β #2293 에서 caller cleanup 위임.

작업:
- file scope: <list of importer files within ≤ 10>
- 각 file 의 import 라인 + 호출 코드를 caller-graph.json #N 의 importers 항목 + 본 Epic 의 spec.md / disposition.json 에 따라 cleanup
- typecheck 통과까지 진행. WIP commit (sonnet 1차 스타일).
- push / PR / CI / Codex 는 Lead 책임 — sonnet 은 진행 X.
- 컨텍스트 절약: caller-graph.json 의 해당 row 만 읽고 진행. spec.md / quickstart.md 는 reference 로만.

산출물:
- 코드 변경 + WIP commit
- decision-log.md 의 § Callsite Migrations 표에 본 작업의 entry 추가 (Edit only, append)
```

---

## Layer 1 분리 박제

Initiative #2290 의 다른 Epic 들 (Epic γ #2294 / Epic δ #2295 / Epic ε #2296 / Epic ζ #2297 / Epic η #2298) 은 본 Epic β session 에서 다루지 않음.

핸드오프 v4 의 Epic δ #2295 는 별도 Lead Opus session 에서 worktree `/Users/um-yunsang/KOSMOS-w-2295/` 에서 진행 — 이번 Epic β merge 후 사용자가 별도 session 시작.
