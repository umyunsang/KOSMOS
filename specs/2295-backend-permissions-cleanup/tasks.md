---
description: "Task list for Epic δ — Backend Permissions Cleanup + AdapterRealDomainPolicy (Initiative #2290)"
---

# Tasks: Backend Permissions Cleanup + AdapterRealDomainPolicy (Epic δ · #2295)

**Input**: Design documents from `/specs/2295-backend-permissions-cleanup/` (worktree at `/Users/um-yunsang/KOSMOS-w-2295/`)
**Prerequisites**: spec.md, plan.md, research.md, data-model.md, quickstart.md
**Tests**: 본 Epic 은 신규 unit test 5 개 추가 (`tests/tools/test_adapter_real_domain_policy.py`). 기존 pytest baseline 비교로 NEW failure 0 검증.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: 다른 파일 + 의존성 0
- **[Story]**: US1 (잔재 deletion), US2 (모델 신설), US3 (18 어댑터 마이그레이션)

## Path Convention

- Worktree: `/Users/um-yunsang/KOSMOS-w-2295/`
- Spec dir: `specs/2295-backend-permissions-cleanup/`
- Source: `src/kosmos/permissions/` + `src/kosmos/tools/`

---

## Phase 1: Setup

- [ ] T001 baseline 박제 — `uv sync && uv run pytest 2>&1 | tee specs/2295-backend-permissions-cleanup/baseline-pytest.txt`
- [ ] T002 [P] `specs/2295-backend-permissions-cleanup/adapter-migration-log.md` 빈 템플릿 (Residue Deletions / Spec 035 Receipt Set / Adapter Migrations 3 섹션)

---

## Phase 2: Foundational — importer 추적

- [ ] T003 `src/kosmos/permissions/` ~20 잔재 importer 추적 — `grep -rE "from\s+kosmos\.permissions\.(aal_backstop|adapter_metadata|...)" src/ tests/` 결과를 `adapter-migration-log.md § Residue Deletions` 표에 박제 (per quickstart § 2.1)
- [ ] T004 18 어댑터 metadata 위치 확인 — `find src/kosmos/tools -maxdepth 3 -name "*.py" | xargs grep -lE 'auth_level|pipa_class|is_personal_data'` 결과 list 작성

**Checkpoint**: importer 그래프 + 어댑터 metadata 위치 박제 완료.

---

## Phase 3: User Story 1 — Spec 033 잔재 deletion (Priority: P1) 🎯 MVP

**Goal**: ~20 잔재 파일 deletion + `__init__.py` 정정 → Spec 035 receipt set 8 파일만 보존.

**Independent Test**: `git ls-files src/kosmos/permissions/` 가 8 파일 + `__init__.py` 만 출력 + Constitution II 토큰 grep 0 행.

- [ ] T005 [US1] importer cleanup — T003 산출 importer 의 caller block 삭제 또는 KOSMOS 등가 호출 교체 (Constitution II 강제 — caller 도 함께 cleanup). KEEP: `src/kosmos/recovery/auth_refresh.py` (uses `kosmos.permissions.credentials`), `src/kosmos/engine/models.py` (uses `kosmos.permissions.models.SessionContext` only — remove `PermissionPipeline` import + use), `src/kosmos/cli/{app,repl}.py` (SessionContext path), `tests/permissions/test_canonical_json.py` + `test_ledger_verify_cli.py` + `test_us2_tamper_detect.py` (Spec 035 receipt tests), `tests/observability/test_query_parent_span.py` (SessionContext only). DELETE: `tests/safety/test_patterns.py`, `tests/e2e/test_observability_wiring.py`, `tests/e2e/test_route_safety_permission.py`, `tests/ipc/test_permission_bridge.py` (uses 잔재 permission models heavily).
- [ ] T006 [US1] 잔재 14 source file + `steps/` 디렉토리 deletion — `git rm src/kosmos/permissions/{aal_backstop,adapter_metadata,bypass,cli,killswitch,mode_bypass,mode_default,modes,pipeline,pipeline_v2,prompt,rules,session_boot,synthesis_guard}.py && git rm -r src/kosmos/permissions/steps/`. KEEP: (a) `models.py` — trim to receipt-schema set: `SessionContext` + `ConsentDecision` + `ConsentLedgerRecord` + `LedgerVerifyReport` + `ToolPermissionContext` + `AdapterPermissionMetadata` + inline `PermissionMode` Literal (since modes.py is deleted). DELETE classes: `AccessTier`, `PermissionDecision`, `PermissionCheckRequest`, `PermissionStepResult`, `AuditLogEntry`, `PermissionRule`. Update `models.py` docstring to "Spec 035 receipt set + harness session schema". (b) `credentials.py` — auth_refresh dependency, KEEP unchanged.
- [ ] T007 [US1] `src/kosmos/permissions/__init__.py` 재작성 — Spec 035 receipt 8 모듈 + `SessionContext` (models.py) + credentials helpers (`candidate_env_vars` / `resolve_credential` / `has_credential`) 만 export. KOSMOS-invented 잔재 모듈 export 0.
- [ ] T008 [US1] FR-006 narrowed grep gate — `grep -rE 'pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference' src/kosmos/tools/koroad/ src/kosmos/tools/kma/ src/kosmos/tools/hira/ src/kosmos/tools/nmc/ src/kosmos/tools/nfa119/ src/kosmos/tools/ssis/ src/kosmos/tools/mock/ src/kosmos/permissions/` 결과 0 행. (FR-006 명시 제외 영역은 검사 대상 아님 — `src/kosmos/security/audit.py` / `src/kosmos/tools/permissions.py` / `src/kosmos/tools/register_all.py` / `src/kosmos/plugins/` / `src/kosmos/ipc/` / `src/kosmos/recovery/auth_refresh.py`).

**Checkpoint**: US1 단독으로 잔재 deletion 완료, Spec 035 receipt 보존 확인.

---

## Phase 4: User Story 2 — AdapterRealDomainPolicy 모델 신설 (Priority: P2)

**Goal**: Pydantic v2 frozen 모델 추가 + 5 단위 테스트 추가.

**Independent Test**: `uv run pytest tests/tools/test_adapter_real_domain_policy.py -v` 5 test pass.

- [ ] T009 [P] [US2] `src/kosmos/tools/models.py` 에 `AdapterRealDomainPolicy` Pydantic v2 모델 추가 (data-model.md § 1 + research.md § R-3 정의 그대로)
- [ ] T010 [P] [US2] 단위 테스트 추가 — `tests/tools/test_adapter_real_domain_policy.py` 5 test (test_model_frozen / test_extra_forbid / test_url_non_empty / test_gate_literal / test_18_adapters_have_policy)
- [ ] T011 [US2] 모델 + 테스트 검증 — `uv run pytest tests/tools/test_adapter_real_domain_policy.py -v` 5 test pass (test_18_adapters_have_policy 는 US3 완료 후 통과)

**Checkpoint**: US2 단독으로 모델 + 4 schema test 통과 (5번째는 US3 완료 후).

---

## Phase 5: User Story 3 — 18 어댑터 metadata 마이그레이션 (Priority: P3)

**Goal**: 18 어댑터 metadata 에 `policy: AdapterRealDomainPolicy` 추가 + 금지 필드 제거.

**Independent Test**: `uv run python -c "from kosmos.tools.registry import ToolRegistry; ..."` 18 어댑터 모두 `policy` 보유 검증 + test_18_adapters_have_policy 통과.

- [ ] T012 [P] [US3] KOROAD 어댑터 ×2 마이그레이션 — `src/kosmos/tools/koroad/*.py` 의 metadata 에서 금지 필드 제거 + `policy=AdapterRealDomainPolicy(real_classification_url="https://www.koroad.or.kr/main/web/policy/data_use.do", ...)` 추가; `adapter-migration-log.md` 표 박제
- [ ] T013 [P] [US3] KMA 어댑터 ×6 마이그레이션 — `src/kosmos/tools/kma/*.py` (`real_classification_url="https://www.kma.go.kr/data/policy.html"`)
- [ ] T014 [P] [US3] HIRA 어댑터 ×1 마이그레이션 — `src/kosmos/tools/hira/*.py`
- [ ] T015 [P] [US3] NMC + NFA119 + MOHW 어댑터 ×3 마이그레이션
- [ ] T016 [P] [US3] Mock 어댑터 ×6 마이그레이션 — barocert / cbs / data_go_kr / mydata / npki_crypto / omnione (placeholder URL + `# TODO: verify URL` 마커, Deferred Items 추적)
- [ ] T017 [US3] Registry boot 검증 — `uv run python -c "from kosmos.tools.registry import ToolRegistry; r = ToolRegistry(); ..."` 18 어댑터 모두 `policy` 보유

**Checkpoint**: US3 단독으로 18 어댑터 마이그레이션 완료, test_18_adapters_have_policy 통과.

---

## Phase 6: Polish — 검증 + commit + PR

- [ ] T018 `uv run pytest` 실행 + baseline 비교 → NEW failure 0 검증; 결과를 `after-pytest.txt` 박제
- [ ] T019 [P] 신규 dependency 0 검증 — `git diff main -- pyproject.toml uv.lock | grep -E '^\+\w+'` 결과 0 행 (FR-008)
- [ ] T020 commit + push + PR — quickstart § 6 절차대로 (`feat(2295): backend permissions cleanup + AdapterRealDomainPolicy`); CI monitoring + Codex P1 처리 + 머지 가능 상태로 보고

**Checkpoint**: PR mergeable + 모든 acceptance gate 통과.

---

## Dependencies & Execution Order

- Phase 1 (T001-T002) → Phase 2 (T003-T004) → Phase 3 (US1) → Phase 4 (US2) → Phase 5 (US3) → Phase 6
- T009 [P] (모델 추가) + T010 [P] (테스트) 병렬 가능 (다른 파일)
- T012-T016 [P] (5 ministry group) 병렬 가능 (각자 다른 디렉토리)
- US2 (T009-T011) 와 US3 (T012-T017) 는 모델이 먼저 박제되어야 어댑터 import 가 작동 → US2 → US3 순서

---

## Implementation Strategy

### MVP First (US1 단독)

1. Phase 1+2 완료
2. US1 (T005-T008) 만 실행 → Constitution II 잔재 0
3. **STOP and VALIDATE**: pytest baseline 대비 NEW failure 0 (단 어댑터 metadata 의 미존재 필드로 인한 import error 가능 — 실제로는 US2+US3 까지 완료해야 무중단 baseline 대비 검증 가능)
4. PR (또는 US2+US3 추가 후 PR)

본 Epic 은 US1+US2+US3 통합 PR 권장 (memory `feedback_integrated_pr_only`) — US1 만으로는 어댑터 metadata 부족.

### Parallel Execution

- T009 + T010 병렬 (다른 파일)
- T012-T016 병렬 (5 group)
- T018 + T019 병렬

---

## Notes

- 총 task 수 = 20 (≪ 90 cap)
- 신규 코드: 1 모델 (Pydantic v2) + 5 단위 테스트 + 18 metadata 인스턴스
- 신규 dependency 0 (FR-008)
- 18 어댑터 마이그레이션 일부 항목 (Mock × 6) 은 placeholder URL + TODO 마커 — Deferred Items #2297 으로 추적
