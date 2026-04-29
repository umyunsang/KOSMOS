# Implementation Plan: KOSMOS-original UI Residue Cleanup (Epic β)

**Branch**: `2293-ui-residue-cleanup` | **Date**: 2026-04-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/2293-ui-residue-cleanup/spec.md`

## Summary

Initiative #2290 의 두 번째 Epic. Epic α (#2292, merged in `bc523b7`) 의 cc-parity-audit 산출물에서 Cleanup-needed 로 분류된 30 TUI 파일과 Spec 1979 § 1.3.4 의 6 KOSMOS-only Tool deletion candidate 를 정리. Spec 1633 (Anthropic→FriendliAI) closure 의 마지막 미완 영역 + Constitution II 잔재를 모두 제거해 KOSMOS 의 "CC + 2 swaps" thesis 가 코드 레벨에서 verify 되도록 한다.

기술 접근:
- (a) `tui/src/services/api/` 17 잔재 파일 + `tui/src/services/tokenEstimation.ts` 의 importer 를 `grep -r` 로 추적해 caller 마이그레이션 또는 caller 와 함께 삭제 (memory `feedback_no_stubs_remove_or_migrate`)
- (b) 8 callsite (queryHaiku / queryWithModel / verifyApiKey) 의 dead 여부 평가 후 KOSMOS i18n / IPC / memdir 등가 호출로 교체 또는 dead feature 인 경우 caller block 통째 삭제
- (c) `tui/src/utils/permissions/` 3 Spec 033 잔재 + `tui/src/schemas/ui-l2/permission.ts` (PermissionDecisionT/PermissionLayerT) 평가 후 삭제 (Constitution II 강제 — 보존 사유 거의 없음 예상)
- (d) 6 KOSMOS-only Tool 평가: 각 도구의 시민 use case 검증 — 발견 시 keep + Decision Log 인용; 발견 못하면 도구 디렉토리 + tools.ts registry entry + 모든 import site 삭제
- (e) `tui/src/utils/plugins/mcpbHandler.ts` 의 `@anthropic-ai/` import 제거 (KOSMOS 등가 import 또는 caller 블록 삭제)
- (f) Spec 1633 + Constitution II 통합 grep gate 로 0-residue 검증

모든 작업은 `/Users/um-yunsang/KOSMOS-w-2293/` worktree 에서 수행. main worktree 와 file conflict 없음. 산출물은 (i) 코드 변경 (deletions + migrations), (ii) `specs/2293-ui-residue-cleanup/` 의 spec/plan/tasks/decision-log/baseline-test/after-test 박제.

## Technical Context

**Language/Version**: TypeScript 5.6+ on Bun v1.2.x (TUI layer, existing Spec 287 stack — no version bump). Python 3.12+ (백엔드, 본 Epic 은 변경하지 않음).
**Primary Dependencies**: 기존 — `ink`, `react`, `@inkjs/ui`, `string-width`, `@modelcontextprotocol/sdk`. 신규 dependency 0 (AGENTS.md hard rule + spec FR-008 invariant 보존).
**Storage**: 본 Epic 은 in-memory + filesystem-only — `~/.kosmos/memdir/user/sessions/` (Spec 027) 등 기존 storage 구조 변경 없음. 산출물 신규 파일은 spec dir 내부.
**Testing**: `bun test` (TUI 단위 테스트, 기존). 본 Epic 은 신규 unit test 작성 안 함 — 기존 테스트가 deletion 후 typecheck + 회귀 검증 역할. 단 잔재 파일을 직접 import 하던 dead test 는 함께 삭제.
**Target Platform**: macOS / Linux dev 환경 (Bun + Node fallback). CI는 Linux container (`lint-and-test` workflow + `Dead Code Detection`).
**Project Type**: TUI cleanup — TypeScript source code 변경. 신규 모듈 0, 신규 추상화 0. 100% deletion + migration.
**Performance Goals**: 본 Epic 은 정리 작업이라 별도 perf goal 없음. `bun typecheck` < 60 s, `bun test` < 5 min (기존 baseline).
**Constraints**: read-only 입력 디렉토리 = `.references/claude-code-sourcemap/restored-src/src/` (변경 금지, AGENTS.md § Do not touch). 모든 변경은 `tui/src/`, 산출물은 `specs/2293-ui-residue-cleanup/`.
**Scale/Scope**: 30 Cleanup-needed paths + 6 KOSMOS-only Tool candidates + 1 ui-l2 permission file = 약 37 file/dir 평가 대상. 예상 commit 수 5~10. 예상 라인 변경: -3,500 ~ -5,000 (대부분 삭제) / +50 ~ +200 (Decision Log + spec 산출물).

## Constitution Check

*GATE: Phase 0 진입 전 통과 필수. Phase 1 종료 후 재검토.*

| Principle | 적용 여부 | 평가 |
|---|---|---|
| **I. Reference-Driven Development** | ✅ 직접 적용 | 본 Epic 의 cleanup target 은 모두 Epic α audit + Spec 1979 audit + restored-src parity 비교에서 도출. 새 코드 0 작성. spec.md 가 4 reference (AGENTS.md / Constitution / cc-source-scope-audit / cc-parity-audit) 를 박제. |
| **II. Fail-Closed Security (NON-NEGOTIABLE)** | ✅ 직접 강제 | 본 Epic 의 핵심 동인. PermissionDecisionT / PermissionLayerT / pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference 잔재 0 회 잔존을 grep gate 로 코드 레벨 enforce. Constitution II 가 NON-NEGOTIABLE 이므로 본 Epic 의 acceptance 가 곧 Constitution 준수 검증. |
| **III. Pydantic v2 Strict Typing** | N/A | TypeScript 변경만 다룸. |
| **IV. Government API Compliance** | N/A | 어댑터 metadata 변경 없음 — Epic δ #2295 territory. |
| **V. Policy Alignment** | N/A | 시민 데이터 흐름 변경 없음. |
| **VI. Deferred Work Accountability** | ✅ 적용 | spec.md `Deferred to Future Work` 표 2 항목 (보존 도구 i18n + claude.ts type 마이그레이션) — 1 개는 NEEDS TRACKING (조건부), 1 개는 #2294 매핑. 본문 grep 결과 unregistered "future epic / Phase [2+] / v2 / deferred to" 패턴 0 건. |

**결론**: PASS. Constitution 위반 0 건. Complexity Tracking 표 비움.

## Project Structure

### Documentation (this feature)

```text
specs/2293-ui-residue-cleanup/
├── spec.md                    # ✅ /speckit-specify 산출물
├── plan.md                    # ✅ 본 파일
├── research.md                # ✅ Phase 0 산출물
├── data-model.md              # ✅ Phase 1 산출물
├── quickstart.md              # ✅ Phase 1 산출물
├── checklists/
│   └── requirements.md        # ✅ /speckit-specify 산출물
├── tasks.md                   # ⏳ /speckit-tasks 산출물
├── decision-log.md            # 🎯 implement 단계 산출물 — 6 KOSMOS-only Tool + ui-l2/permission.ts 결정 기록
├── baseline-test.txt          # 🎯 implement 직전 bun test 결과 박제
└── after-test.txt             # 🎯 implement 후 bun test 결과 박제 (NEW failure 검출 input)
```

### Source Code (repository root)

```text
# 본 Epic 은 deletion + migration 만 — tui/src/ 하위 변경.
tui/src/
├── services/api/        ← DELETE 17 files (claude.ts 등 Spec 1633 dispatcher 잔재)
├── services/tokenEstimation.ts  ← DELETE (anthropic-sdk import)
├── services/toolUseSummary/toolUseSummaryGenerator.ts  ← MIGRATE (queryHaiku 호출)
├── cli/print.ts                ← MIGRATE (verifyApiKey + queryHaiku)
├── commands/insights.ts        ← MIGRATE (queryWithModel)
├── commands/rename/generateSessionName.ts  ← MIGRATE (queryHaiku)
├── components/Feedback.tsx     ← MIGRATE (queryHaiku)
├── tools/WebFetchTool/utils.ts ← MIGRATE (queryHaiku)
├── utils/mcp/dateTimeParser.ts ← MIGRATE (queryHaiku)
├── utils/sessionTitle.ts       ← MIGRATE (queryHaiku)
├── utils/shell/prefix.ts       ← MIGRATE (queryHaiku)
├── utils/permissions/          ← DELETE permissionSetup.ts + permissions.ts + yoloClassifier.ts
├── utils/plugins/mcpbHandler.ts ← MIGRATE (@anthropic-ai/ import 제거)
├── schemas/ui-l2/permission.ts ← DELETE (Constitution II) 또는 keep + Decision Log
└── tools/                       ← DELETE up to 6: MonitorTool/ ReviewArtifactTool/ SuggestBackgroundPRTool/ TungstenTool/ VerifyPlanExecutionTool/ WorkflowTool/

tools.ts (registry)              ← UPDATE: 삭제된 도구 entries 제거
.references/claude-code-sourcemap/restored-src/  # 읽기 전용 (AGENTS.md § Do not touch)
specs/2293-ui-residue-cleanup/   # 산출물 디렉토리
```

**Structure Decision**: 본 Epic 은 "code deletion + caller migration" 패턴. 신규 디렉토리 0, 신규 모듈 0. tools.ts registry 의 import list + tool array 갱신 외에는 모두 deletion. plan-template 의 Option 1/2/3 트리는 사용하지 않음 — 기존 KOSMOS TUI 구조를 그대로 유지하면서 Anthropic 1P + Spec 033 잔재만 제거.

## Complexity Tracking

> **Constitution Check 가 PASS 이므로 본 표는 비워둠.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (none) | (n/a) | (n/a) |
