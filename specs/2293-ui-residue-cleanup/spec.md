# Feature Specification: KOSMOS-original UI Residue Cleanup (Epic β)

**Feature Branch**: `2293-ui-residue-cleanup`
**Created**: 2026-04-29
**Status**: Draft
**Input**: User description: "Epic β — Epic α (#2292, merged in `bc523b7`) audit 결과 30 Cleanup-needed 파일 + 6 KOSMOS-only Tool deletion candidates 를 정리해 Spec 1633 closure 와 Constitution II 준수 완료."
**Authority** (cite in every downstream artefact):
- `AGENTS.md § CORE THESIS` — KOSMOS = AX-infrastructure callable-channel client (3rd thesis canonical)
- `.specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)` — KOSMOS-invented permission classifications removed in Spec 1979 MUST NOT be reintroduced
- `specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 1.2.1, § 1.2.2, § 1.3.4`
- `specs/2292-cc-parity-audit/cc-parity-audit.md` — Epic α deliverable, this Epic 의 직접 입력
- `specs/2292-cc-parity-audit/data/modified-218-classification.json` — 30 Cleanup-needed 파일 list
- `.references/claude-code-sourcemap/restored-src/src/` — CC 2.1.88 byte-identical source-of-truth (research-only)

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Spec 1633 services/api closure (Priority: P1) 🎯 MVP

KOSMOS Lead 가 Epic α 의 Cleanup-needed list 를 받아 후속 cleanup 진입한다. 첫 우선 작업은 `tui/src/services/api/` 의 17 Anthropic dispatcher 잔재 파일과 8 callsite (queryHaiku / queryWithModel / verifyApiKey) 를 모두 제거 또는 KOSMOS 등가물로 마이그레이션해 Spec 1633 closure 를 완료하는 것이다. 이 작업이 끝나면 KOSMOS TUI 에는 더 이상 Anthropic 1P API 잔재가 남지 않는다.

**Why this priority**: Spec 1633 (Anthropic→FriendliAI) closure 가 미완 상태로 4 callsite + 3,419 LOC dispatcher 가 alive 라는 점이 MEMORY.md `project_tui_anthropic_residue` 에 기록되어 있다. 본 cleanup 이 미완이면 K-EXAONE 단일 LLM provider 라는 KOSMOS thesis 가 실 코드에서 verify 되지 않는다.

**Independent Test**: cleanup 후 (a) `tui/src/services/api/` 디렉토리에 17 잔재 파일 0 개 잔존, (b) 8 callsite 모두 0 회 grep 매치, (c) `cd tui && bun typecheck` 0 errors, (d) `bun test` 베이스라인 대비 NEW failure 0 인 상태로 완료되면 통과.

**Acceptance Scenarios**:

1. **Given** Epic α 의 17 services/api Cleanup-needed list, **When** Lead 가 각 파일의 caller 를 grep 으로 추적해 KOSMOS 등가물 (memdir/IPC/i18n 기반 경로) 로 호출 교체 또는 dead feature 인 경우 caller 와 함께 삭제, **Then** `git ls-files tui/src/services/api/` 출력에 17 파일 모두 0 회 매칭.
2. **Given** 8 callsite 의 함수 호출, **When** 각 callsite 의 dead 여부 + 대체 경로 결정, **Then** `grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/` 출력 0 행.
3. **Given** 모든 services/api 잔재 제거 완료, **When** `cd tui && bun typecheck` 실행, **Then** exit code 0 + 0 errors.
4. **Given** typecheck 통과, **When** `cd tui && bun test` 실행 + 사전 baseline 결과와 비교, **Then** NEW failure 0 (이전 실패는 그대로 유지 가능, 새로운 실패만 0).

---

### User Story 2 — Constitution II permission residue 제거 (Priority: P2)

Spec 033 잔재인 `tui/src/utils/permissions/` 의 3 파일과 `tui/src/schemas/ui-l2/permission.ts` 의 KOSMOS-invented 권한 타입 (PermissionDecisionT / PermissionLayerT) 을 평가해 삭제 또는 cite 후 보존을 결정한다. Constitution II 의 fail-closed 보안 원칙이 코드 레벨에서 enforce 되어 있어야 한다.

**Why this priority**: Constitution II 는 KOSMOS-invented 권한 분류 (5-mode spectrum / pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference) 를 NON-NEGOTIABLE 하게 금지한다. Spec 1979 에서 대부분 제거됐지만 잔재가 남아 있으면 Constitution 위반.

**Independent Test**: cleanup 후 (a) `tui/src/utils/permissions/` 디렉토리가 비어있거나 Spec 035 영수증 ledger 관련 파일만 존재 + 보존 사유 인용, (b) `grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier' tui/src/` 출력 0 행, (c) typecheck/test 통과.

**Acceptance Scenarios**:

1. **Given** `tui/src/utils/permissions/{permissionSetup,permissions,yoloClassifier}.ts` 3 파일, **When** 각 파일의 caller 추적 후 caller 도 함께 삭제 또는 KOSMOS 등가 호출로 교체, **Then** 3 파일 모두 git 에서 사라짐.
2. **Given** `tui/src/schemas/ui-l2/permission.ts`, **When** PermissionDecisionT/PermissionLayerT 사용처 0 인지 확인, **Then** 파일 삭제 (기본 결정) 또는 보존 사유 + Spec 인용을 spec dir 의 Decision Log 에 기록.
3. **Given** Constitution II 금지 토큰 list, **When** `grep -rE` 패턴 매치 검사, **Then** `tui/src/` 하위 0 행 매치.

---

### User Story 3 — KOSMOS-only Tool deletion candidates 평가 (Priority: P3)

`tui/src/tools/` 의 6 KOSMOS-only Tool (MonitorTool / ReviewArtifactTool / SuggestBackgroundPRTool / TungstenTool / VerifyPlanExecutionTool / WorkflowTool) 을 시민 use case 기준으로 평가해 use case 없는 것은 삭제, 있는 것은 사유 기록 후 보존한다. KOSMOS 도구 registry 가 시민 중심 도구만 남도록 정리.

**Why this priority**: Spec 1979 cc-source-scope-audit § 1.3.4 에서 "검토 후 삭제 후보" 로 분류된 6 도구. 본 작업은 도구 registry 의 inventory 정리이며, 시민-facing 기능 (한국 정부 API 어댑터) 과 무관한 개발자 도구 잔재 제거.

**Independent Test**: 6 도구 each 가 (삭제 또는 보존 + 사유) 결정되어 있고, 삭제된 도구는 `tools.ts` 등록부에서도 제거되어 typecheck 통과.

**Acceptance Scenarios**:

1. **Given** 6 후보 도구 디렉토리, **When** 각 도구의 시민 use case 평가 (시민이 한국 공공 서비스에서 호출할 시나리오 존재 여부), **Then** 각 도구마다 `delete` 또는 `keep + rationale` 결정.
2. **Given** 삭제 결정 도구, **When** `tools.ts` registry 와 import 사이트에서 모두 제거, **Then** typecheck 통과 + registry 가 citizen-relevant 도구만 노출.

---

### Edge Cases

- **callsite 가 import 만 하고 실제 호출이 없는 dead import**: import 라인만 제거, 본문 변경 없음. typecheck 가 unused-import 를 잡아주므로 자동 검출.
- **`tui/src/services/api/claude.ts` 가 export 하는 type 이 KOSMOS-needed 다른 모듈에서 import 되는 경우**: type 자체를 KOSMOS 등가물로 옮긴 후 claude.ts 삭제. 그렇지 않으면 caller 도 함께 삭제 (memory `feedback_no_stubs_remove_or_migrate`).
- **6 KOSMOS-only Tool 중 보존 결정 도구가 등장**: spec dir 의 Decision Log 에 `keep <ToolName>: 사유 + Spec 인용` 명시.
- **Cleanup-needed 파일이 import 한 다른 jsons/fixtures 가 있을 경우**: 해당 fixture 도 dead 여부 평가 후 별도 cleanup commit (본 Epic 범위 외 기능 회귀 방지).
- **bun test 의 pre-existing failure 가 변동될 경우**: baseline 이전 실패가 `unknown.test.ts` 에서 유지되어야 함; 새로운 import 누락 등으로 실패 양상이 바뀌면 NEW failure 로 간주.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: 30 Cleanup-needed 파일 (Epic α audit 출력) 100% 가 delete 또는 KOSMOS 등가물로 migrate 되어야 한다. `git ls-files tui/src/` 출력에 30 path 모두 0 회 잔존.
- **FR-002**: 8 callsite (queryHaiku / queryWithModel / verifyApiKey) 모두 `grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/` 결과 0 행이어야 한다.
- **FR-003**: `tui/src/utils/permissions/` 의 3 Spec 033 잔재 파일이 삭제되어야 하고, 디렉토리가 비어있거나 Spec 035 receipt 관련 파일 (cite 후) 만 보존.
- **FR-004**: `tui/src/schemas/ui-l2/permission.ts` 가 (a) 삭제되거나 (b) Decision Log 에 보존 사유 + Spec 인용이 기록되어야 한다.
- **FR-005**: 6 KOSMOS-only Tool deletion candidate 각각이 spec dir 의 Decision Log 에 `delete` 또는 `keep + rationale` 결정으로 명시되고, 삭제 결정 도구는 `tools.ts` registry 와 import site 에서 모두 제거되어야 한다.
- **FR-006**: `cd tui && bun typecheck` 가 `0 errors` 를 출력해야 한다 (FR-001~FR-005 완료 후).
- **FR-007**: `cd tui && bun test` 의 NEW failure 가 0 이어야 한다 (사전 baseline 비교 기준).
- **FR-008**: `grep -rE 'PermissionDecisionT|PermissionLayerT|pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference|verifyApiKey|queryHaiku|queryWithModel|@anthropic-ai/' tui/src/` 결과가 0 행이어야 한다 (Constitution II + Spec 1633 closure 동시 검증).
- **FR-009**: 본 Epic 의 모든 commit message 와 spec 산출물이 Authority 4 reference (AGENTS.md / Constitution / cc-source-scope-audit / cc-parity-audit) 를 인용해야 한다.
- **FR-010**: `tui/src/utils/plugins/mcpbHandler.ts` 의 `@anthropic-ai/` import 가 제거되거나 KOSMOS 등가 import 로 교체되어야 한다.

### Key Entities

- **CleanupTarget**: 단위 cleanup 대상 — `kosmos_path`, `disposition` (`delete` / `migrate` / `keep_with_rationale`), `caller_paths` (이 파일이 import 되는 곳), `decision_rationale` (대체 경로 또는 보존 사유), `epic_alpha_signal` (Epic α audit 의 분류 + 시그널).
- **DecisionLog**: 6 KOSMOS-only Tool + `ui-l2/permission.ts` 의 결정 기록 — 각 항목 `name`, `decision` (delete/keep), `rationale`, `references`.
- **TestBaseline**: cleanup 직전의 `bun test` 결과 spreadsheet — `total`, `pass`, `fail`, `failure_test_ids`. Cleanup 후 `TestAfter` 와 비교해 NEW failure 검출.
- **CallsiteMigration**: 8 queryHaiku/etc callsite 의 변환 기록 — `kosmos_path`, `original_call`, `replacement` (KOSMOS equivalent 또는 `feature_deleted`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 30 Cleanup-needed 파일 100% 가 delete 또는 migrate 완료 (`git ls-files` 검증).
- **SC-002**: 8 callsite 0 회 잔존 (`grep` 검증).
- **SC-003**: `tui/src/utils/permissions/` 정리 완료 — 3 잔재 파일 0 회 잔존 + 디렉토리 비어있거나 Spec 035 파일만 보존.
- **SC-004**: 6 KOSMOS-only Tool 100% 결정 기록 + 삭제된 도구는 registry 와 import 에서 모두 제거.
- **SC-005**: `bun typecheck` exit 0, 0 errors.
- **SC-006**: `bun test` NEW failure 0 (baseline 대비).
- **SC-007**: Constitution II + Spec 1633 closure grep gate 0 행 매치.
- **SC-008**: PR `Closes #2293` 단독 / Conventional Commits PR title 통과 / 14 required CI checks 모두 PASS / Codex P1 0건 또는 모두 resolved.

---

## Assumptions

- Epic α #2292 (merged in `bc523b7`) 의 audit 결과가 본 Epic 시작 시점에서도 유효 — 30 Cleanup-needed list 가 main 에 박제됨.
- `bun test` baseline 측정은 cleanup 시작 직전에 수행하며 (1979 fixture 정정 commit 6914... 직후 main 상태 기준), 결과를 `/tmp/baseline-2293.txt` 등에 박제.
- 6 KOSMOS-only Tool 모두 시민 use case 0 으로 판정되어 모두 삭제될 가능성이 높음 (Spec 1979 § 1.3.4 의 "검토 후 삭제 후보" 분류) — 단 평가는 평가 단계에서 수행.
- Spec 035 receipt ledger 는 백엔드 Python 에 박제됨 (`src/kosmos/permissions/ledger.py` 등) 이지 TUI side 에는 없음 — 따라서 `tui/src/utils/permissions/` 는 비어도 무방.
- `claude.ts` 가 export 한 type 들 중 일부 (예: 응답 envelope) 가 KOSMOS-needed 일 가능성 — caller 추적으로 확인 후 KOSMOS i18n / IPC layer 로 옮김.
- 본 Epic 작업은 `/Users/um-yunsang/KOSMOS-w-2293/` worktree 에서 진행되며 main worktree 와 file conflict 없음 (각자 독립 working dir).

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **백엔드 Python (`src/kosmos/permissions/`) 정리**: Epic δ #2295 territory — 본 Epic 은 TUI 만 다룸.
- **5-primitive 를 CC `Tool.ts` 에 align**: Epic γ #2294 territory.
- **AdapterRealDomainPolicy Pydantic 모델 + 18 어댑터 metadata 마이그레이션**: Epic δ #2295.
- **AX-infrastructure mock 어댑터 신설**: Epic ε #2296.
- **KOSMOS-only ADDITIONS 274 파일의 추가 audit**: Epic α 가 KEEP/Modified 만 다뤘듯, 본 Epic 도 Cleanup-needed 만 처리.
- **Spec 287 TUI 인프라 (i18n/ipc/theme/observability/ssh) 변경**: Spec 1979 후속이며 본 Epic 범위 외.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| 6 KOSMOS-only Tool 중 보존 결정 도구 (있다면) 의 시민 use case 검증 + 한국어 i18n 적용 | 본 Epic 은 deletion 결정 + dead code 제거 범위; 보존 도구의 i18n 은 별도 spec 필요 | Epic ζ (#2297) E2E smoke 의 일부 또는 별도 follow-up | #2361 (조건부 — 보존 도구 0 이면 자연 close) |
| `tui/src/services/api/claude.ts` 의 type-only export 가 다른 모듈에서 import 되는 경우의 KOSMOS 등가 type 박제 | claude.ts 삭제 시 자동 추적 + 마이그레이션이 본 Epic 범위지만, 추가 type 의 KOSMOS i18n / 한국어 라벨링은 별도 작업 | Epic γ (#2294) 5-primitive align 작업의 일부 (Tool.ts 인터페이스와 함께) | #2294 |
