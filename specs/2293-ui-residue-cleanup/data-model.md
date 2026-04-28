# Phase 1 Data Model — UI Residue Cleanup (Epic β)

**Date**: 2026-04-29 · **Spec**: [spec.md § Key Entities](./spec.md#key-entities)

본 Epic 은 신규 schema 를 어댑터에 추가하지 않으므로 Pydantic v2 강제 X (Constitution III N/A). 그러나 산출물 (`decision-log.md` + `baseline-test.txt` + `after-test.txt`) 의 구조를 정형화하여 후속 Epic γ 가 입력으로 사용 가능하도록 한다.

---

## 1. CleanupTarget — Cleanup 대상 1 항목

`decision-log.md` 의 표 1 행 + `data/cleanup-targets.json` (선택, scripted 추적 시).

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/...` 상대경로 |
| `disposition` | enum {`delete`, `migrate`, `keep_with_rationale`} | ✅ | 결정 |
| `caller_paths` | array<string> | ✅ | 이 파일을 import 하는 다른 KOSMOS 파일 list (cleanup 시 함께 변경) |
| `decision_rationale` | string | ✅ | 1~3 줄 — 결정 근거 + Spec / memory 인용 |
| `epic_alpha_signal` | object | ✅ | Epic α audit 의 `signals` 필드 그대로 (`directory_match`, `git_history_match`, `import_scan_match`) |
| `replacement` | string \| null | optional | migrate 시 대체 경로 (예: `kosmos i18n key` 또는 `IPC channel`) |

### Validation

- `disposition == "delete"` 후 `git ls-files <kosmos_path>` 0 행이어야 함 (acceptance gate)
- 30 entry 모두 `disposition` 값 셋 중 하나
- `caller_paths` 의 각 entry 도 cleanup 후 grep gate (FR-008) 통과

---

## 2. DecisionLog — 6 KOSMOS-only Tool + ui-l2/permission.ts 결정

`decision-log.md` 의 § "KOSMOS-only Tool Decisions" + § "ui-l2/permission Decision" 섹션.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | ✅ | Tool 디렉토리 명 또는 파일 명 |
| `decision` | enum {`delete`, `keep`} | ✅ | |
| `rationale` | string | ✅ | delete 사유 (시민 use case 0) 또는 keep 사유 (시민 use case + Spec 인용) |
| `references` | array<string> | ✅ | Spec / memory id 또는 file path |

### Validation

- 7 항목 (6 Tool + 1 ui-l2/permission) 모두 entry 보유
- `decision == "keep"` 인 항목은 `rationale` 에 시민 use case 의 구체 시나리오 명시
- `decision == "delete"` 인 항목은 `tools.ts` registry 와 import site 모두에서 제거 (acceptance gate)

---

## 3. CallsiteMigration — 8 callsite 변환 기록

`decision-log.md` 의 § "Callsite Migrations" 섹션.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | callsite 파일 |
| `original_call` | string | ✅ | 변환 전 함수 호출 (예: `queryHaiku(promptId, args)`) |
| `replacement` | string | ✅ | 변환 후 호출 또는 `feature_deleted` |
| `migration_type` | enum {`equivalent_replace`, `feature_delete`, `dead_import_only`} | ✅ | |

### Validation

- 8 항목 (R-2 매트릭스의 callsite list 와 일치)
- `migration_type == "feature_delete"` 면 caller block 통째 삭제 후 `git diff` 로 verify
- `grep -rE 'queryHaiku\|queryWithModel\|verifyApiKey' tui/src/` 결과 0 행 (FR-002)

---

## 4. TestBaseline + TestAfter

`baseline-test.txt` + `after-test.txt` plain text + 비교 결과 `test-diff-summary.json` (선택).

### TestBaseline 필드

| 필드 | 타입 | 필수 |
|---|---|---|
| `total_tests` | int | ✅ |
| `pass_count` | int | ✅ |
| `fail_count` | int | ✅ |
| `failure_test_ids` | array<string> | ✅ |

### Validation

- TestAfter.failure_test_ids ⊆ TestBaseline.failure_test_ids ∪ ∅ (NEW failure 0 invariant)

---

## 산출물 매핑

| Entity | markdown 위치 | 보조 데이터 |
|---|---|---|
| CleanupTarget × 30 | `decision-log.md § Cleanup Targets` | (선택) `data/cleanup-targets.json` |
| DecisionLog × 7 | `decision-log.md § KOSMOS-only Tool + ui-l2 Decisions` | — |
| CallsiteMigration × 8 | `decision-log.md § Callsite Migrations` | — |
| TestBaseline + TestAfter | `baseline-test.txt` + `after-test.txt` plaintext | (선택) `data/test-diff-summary.json` |
