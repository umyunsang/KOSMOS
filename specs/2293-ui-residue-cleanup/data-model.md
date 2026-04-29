# Phase 1 Data Model — UI Residue Cleanup (Epic β · v2)

**Date**: 2026-04-29 (v2 revision) · **Spec**: [spec.md § Key Entities](./spec.md#key-entities)

본 Epic 은 신규 schema 를 어댑터에 추가하지 않으므로 Pydantic v2 강제 X (Constitution III N/A). 그러나 산출물 (`caller-graph.json` + `disposition.json` + `decision-log.md` + `baseline-test.txt` + `after-test.txt`) 의 구조를 정형화하여 후속 Epic 가 입력으로 사용 가능하도록 한다.

v2 변경: `CallerGraph` + `DispositionMatrix` entity 신규 박제. `CleanupTarget` 의 schema 가 caller-graph + disposition 결합 형태로 정정.

---

## 1. CallerGraph (NEW v2) — 30 file × importer 매트릭스

`data/caller-graph.json` 박제. `scripts/build-caller-graph.py` 로 자동 생성.

### Schema (JSON array of objects)

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/...` 상대경로 |
| `module_path` | string | ✅ | import 절단 후 stem (예: `services/api/claude`) |
| `line_count` | int | ✅ | 파일 라인 수 |
| `importer_count` | int | ✅ | 이 파일을 import 하는 다른 파일 수 |
| `importers` | array<string> | ✅ | importer file path list (caller cleanup 시 사용) |
| `internal_anthropic_tokens` | object | ✅ | `{queryHaiku: int, queryWithModel: int, verifyApiKey: int, "@anthropic-ai/": int}` 매치 카운트 |
| `dependency_hits` | object | ✅ | `{sdk-compat, @aws-sdk/client-bedrock-runtime, claude.ai, isClaudeAISubscriber, getClaudeCodeUserAgent, growthbook, "from 'bun:bundle'", "feature("}` 매치 카운트 |
| `first_lines` | string | ✅ | 처음 5 줄 (cleanup risk 판단) |
| `epic_alpha_signal` | object | ✅ | Epic α audit 의 `signals` 그대로 (`directory_match`, `git_history_match`, `import_scan_match`) |
| `epic_alpha_summary` | string | ✅ | Epic α audit 의 `change_summary` 그대로 |

### Validation

- 30 row × 모든 필드 채움
- `importer_count == len(importers)`
- 자동 재생성 가능 — `python3 specs/2293-ui-residue-cleanup/scripts/build-caller-graph.py` 가 idempotent

---

## 2. DispositionMatrix (NEW v2) — 30 file 의 v2 결정

`data/disposition.json` 박제. Lead 가 caller-graph.json 을 입력으로 결정.

### Schema (JSON array of objects)

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/...` 상대경로 |
| `disposition` | enum {`DELETE`, `KEEP`} | ✅ | v2 결정 (v1 의 `migrate` 는 별도 spec 으로 deferred) |
| `rationale` | string | ✅ | 1~3 줄 — 결정 근거 + caller-graph evidence + Spec 인용 |
| `caller_cleanup_required` | bool | ✅ | DELETE 인 경우 importer cleanup 동시 진행 여부 |
| `risk` | enum {`LOW`, `MEDIUM`, `HIGH`, `N/A`} | ✅ | cleanup 의 회귀 위험도 (HIGH = tokenEstimation 11 importer 같은 광범위 영향) |

### Validation

- 30 entry (Cleanup-needed) + 1 entry (schemas/ui-l2/permission.ts, 30 list 외 v1 잘못 추가) = 31 entry
- 28 DELETE + 3 KEEP
- `disposition == "DELETE" && caller_cleanup_required == false` → 0 importer 박제 (caller-graph.json 의 `importer_count == 0`)
- `disposition == "DELETE" && caller_cleanup_required == true` → ≥ 1 importer 박제
- `disposition == "KEEP"` → `risk == "N/A"`

---

## 3. CleanupTarget (v1 → v2 정정) — Cleanup 작업 단위

`decision-log.md` 의 표 1 행. CallerGraph + DispositionMatrix 결합.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/...` 상대경로 |
| `disposition` | enum {`DELETE`, `KEEP`} | ✅ | DispositionMatrix 의 결정 |
| `importer_count` | int | ✅ | CallerGraph 박제 |
| `importers` | array<string> | ✅ | CallerGraph 박제 |
| `caller_cleanup_required` | bool | ✅ | |
| `risk` | enum | ✅ | |
| `rationale` | string | ✅ | DispositionMatrix 박제 |
| `epic_alpha_signal` | object | ✅ | CallerGraph 박제 |

### Validation

- `disposition == "DELETE"` 후 `git ls-files <kosmos_path>` 0 행 (acceptance gate)
- `disposition == "DELETE" && caller_cleanup_required == true` 후 `importers` 의 각 path 도 cleanup 완료 (FR-002 / FR-008 / FR-010 grep gate 통과)
- 31 entry 모두 `disposition` 값 둘 중 하나

---

## 4. DecisionLog — 6 KOSMOS-only Tool + KEEP 결정 박제

`decision-log.md` 의 § "KOSMOS-only Tool Decisions" + § "Cleanup Targets KEEP rows".

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `name` | string | ✅ | Tool 디렉토리 명 또는 파일 명 |
| `decision` | enum {`DELETE`, `KEEP`} | ✅ | |
| `rationale` | string | ✅ | delete 사유 (시민 use case 0) 또는 keep 사유 (caller graph + Constitution II 비충돌 박제) |
| `references` | array<string> | ✅ | Spec / memory id 또는 file path / caller-graph.json + disposition.json |

### Validation

- 6 KOSMOS-only Tool entry (sonnet 1차에서 이미 deletion 완료 — DELETE 결정 박제)
- 3 KEEP entry (permissionSetup / permissions / ui-l2/permission)
- `decision == "KEEP"` 인 항목은 `rationale` 에 caller-graph evidence + Constitution II 비충돌 명시 필수
- `decision == "DELETE"` 인 항목은 `tools.ts` registry 와 import site 모두에서 제거 (acceptance gate)

---

## 5. CallsiteMigration — 8 callsite 정리 기록

`decision-log.md` 의 § "Callsite Migrations".

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | callsite 파일 |
| `original_call` | string | ✅ | 변환 전 함수 호출 (예: `queryHaiku(promptId, args)`) |
| `replacement` | string | ✅ | 변환 후 호출 또는 `feature_deleted` 또는 `dead_import_removed` |
| `migration_type` | enum {`equivalent_replace`, `feature_delete`, `dead_import_only`} | ✅ | |

### Validation

- 8 항목 (R-2 매트릭스의 callsite list 와 일치)
- `migration_type == "feature_delete"` 면 caller block 통째 삭제 후 `git diff` 로 verify
- `grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/` 결과 0 행 (FR-002)
- v2 의 결정상 `migration_type == "equivalent_replace"` 는 0 (K-EXAONE migrate 는 별도 spec 으로 deferred)

---

## 6. TestBaseline + TestAfter

`baseline-test.txt` + `after-test.txt` plain text + (선택) `data/test-diff-summary.json`.

### TestBaseline 필드

| 필드 | 타입 | 필수 |
|---|---|---|
| `total_tests` | int | ✅ |
| `pass_count` | int | ✅ |
| `fail_count` | int | ✅ |
| `failure_test_ids` | array<string> | ✅ |

### Validation

- TestAfter.failure_test_ids ⊆ TestBaseline.failure_test_ids ∪ ∅ (NEW failure 0 invariant; FR-007 / SC-006)

---

## 산출물 매핑

| Entity | markdown 위치 | 보조 데이터 |
|---|---|---|
| CallerGraph (NEW) | (없음 — JSON 직접) | `data/caller-graph.json` |
| DispositionMatrix (NEW) | (없음 — JSON 직접) | `data/disposition.json` |
| CleanupTarget × 31 | `decision-log.md § Cleanup Targets` | caller-graph.json + disposition.json 결합 |
| DecisionLog × 9 (6 Tool + 3 KEEP) | `decision-log.md § KOSMOS-only Tool Decisions + § ui-l2/permission Decision + § utils/permissions KEEP` | — |
| CallsiteMigration × 8 | `decision-log.md § Callsite Migrations` | — |
| TestBaseline + TestAfter | `baseline-test.txt` + `after-test.txt` plaintext | (선택) `data/test-diff-summary.json` |
