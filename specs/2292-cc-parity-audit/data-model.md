# Phase 1 Data Model — CC Parity Audit (Epic α)

**Date**: 2026-04-29
**Spec**: [spec.md § Key Entities](./spec.md#key-entities)
**Plan**: [plan.md](./plan.md)
**Research**: [research.md](./research.md)

본 Epic 은 source code 어댑터를 추가하지 않으므로 Pydantic 모델이 강제되지 않는다 (Constitution III N/A — `plan.md § Constitution Check`). 그러나 산출물 (`cc-parity-audit.md` + `data/*.json`) 의 행/객체 구조는 후속 Epic 의 task 입력으로 직접 사용되므로 다음 5 entity 의 schema 를 plaintext markdown 표 + JSON 양 형식으로 강제한다.

---

## 1. AuditEntry — Modified file 1 행

`cc-parity-audit.md § Modified Files` 표의 한 행 + `data/modified-212-classification.json` 의 한 객체.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/` 시작 상대경로. 예: `tui/src/services/api/claude.ts` |
| `cc_source_path` | string \| null | ✅ | 매칭되는 `restored-src/src/` 상대경로. 매칭 없는 KOSMOS-only 파일이 잘못 들어온 경우 `null` 후 reclassify. |
| `classification` | enum {`Legitimate`, `Cleanup-needed`, `Suspicious`} | ✅ | 단일 라벨 (다중 금지, FR-001) |
| `change_summary` | string | ✅ | 한 줄 (≤120 자). 예: "Anthropic 1P 잔재 — Spec 1633 closure 미완" |
| `reference_citation` | string | ✅ | CC source-of-truth path (`restored-src/src/services/api/anthropic.ts`) 또는 KOSMOS spec id (`Spec 1633`). 둘 중 하나는 반드시 (FR-004). |
| `signals` | object | ✅ | 자동 분류 시그널 raw — `{directory_match, git_history_match, import_scan_match}` 각각 string \| null |
| `notes` | string \| null | optional | Suspicious 의 경우 "왜 의심인가" 사유 한 줄. 비-Suspicious 는 null 허용. |

### Validation rules

- `classification == "Suspicious"` ⟹ `notes` 가 non-null (FR-001 + spec.md story 1.3).
- `classification` 이 셋 중 하나가 아니면 schema 위반.
- `kosmos_path` 가 `data/enumerated-modified-212.txt` 에 존재해야 함 (FR-001 모집단 일치).
- 표 전체 행 수 == 212 (drift 발견 시 plan.md FR-010 절차로 정정).

### State transitions

`Suspicious` 행은 후속 Epic β/δ 의 task 본문에 paste 되어 task 단위로 처리. 본 Epic 내부에서는 transition 없음 (read-only invariant).

---

## 2. SpotCheckSample — byte-identical 표본 1 행

`cc-parity-audit.md § Spot-Check (50)` 표 + `data/spot-check-results.json`.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/` 상대경로 |
| `cc_source_path` | string | ✅ | `restored-src/src/` 매칭경로 (1:1) |
| `kosmos_sha256` | string (64-hex) | ✅ | KOSMOS 파일 sha256 |
| `cc_sha256` | string (64-hex) | ✅ | restored-src 파일 sha256 |
| `hash_match` | boolean | ✅ | `kosmos_sha256 == cc_sha256` |
| `sampling_seed` | int | ✅ | 모든 행 동일 — `2292` |
| `sampling_index` | int | ✅ | 0..49 — Python `random.Random(2292).sample(...)` 결과의 인덱스 |

### Validation rules

- 행 수 == 50 (FR-002 / SC-002).
- 모든 행의 `sampling_seed == 2292`.
- `hash_match == false` 인 행은 산출물 § "Reclassified-to-Modified" subsection 에 자동 합류 → AuditEntry 로 추가 분류 (FR-008).
- `kosmos_path` ∈ `data/enumerated-keep-1531.txt`.

### State transitions

`hash_match == false` ⟹ `AuditEntry` 로 reclassify (FR-008). 행 수 ≥ 50 보장 후 추가 mismatch 발견시 표본 확장 (Deferred Items 의 "표본 50 → 100" 트리거).

---

## 3. ImportDiffEntry — SDK-import-only-diff 73 검증 1 행

`cc-parity-audit.md § Import-only Diff (73)` 표 + `data/import-verify-results.json`.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `kosmos_path` | string | ✅ | `tui/src/` 상대경로 |
| `cc_source_path` | string | ✅ | `restored-src/src/` 매칭경로 |
| `import_lines_changed` | array<string> | ✅ | 변경된 import 라인 (KOSMOS / CC 양쪽 페어) |
| `body_diff_present` | boolean | ✅ | import 라인 외 본문 변경 존재 여부 |
| `reclassified_to_modified` | boolean | ✅ | `body_diff_present == true` 면 true (자동) |

### Validation rules

- 행 수 == 73 (FR-003 / SC-003).
- `reclassified_to_modified == true` ⟹ 해당 `kosmos_path` 가 `AuditEntry` (Modified Files 표) 에도 존재 (FR-008).
- `import_lines_changed` 가 빈 배열이면서 `body_diff_present == false` 인 행은 schema 위반 (cc-source-scope-audit § 1.1 가설과 모순).

### State transitions

`reclassified_to_modified == true` ⟹ `AuditEntry` 로 합류 (FR-008).

---

## 4. SuspiciousTransferList — Epic β/δ 입력

`cc-parity-audit.md § Suspicious Transfer List` 섹션 + `data/suspicious-transfer.json`.

### 구조

```json
{
  "epic_beta_2293": [
    {"kosmos_path": "tui/src/...", "change_summary": "...", "notes": "...", "audit_entry_ref": "row#NN"}
  ],
  "epic_delta_2295": [...],
  "uncategorized": [...]
}
```

각 sub-list 는 `AuditEntry` 의 부분집합 (`classification == "Suspicious"`) 을 Epic 라우팅.

### 라우팅 룰

- `kosmos_path` startswith `tui/src/services/api/` ⟹ `epic_beta_2293` (UI/services 잔재)
- `kosmos_path` startswith `tui/src/utils/permissions/` ⟹ `epic_beta_2293` (Spec 033 잔재)
- `kosmos_path` startswith `src/kosmos/permissions/` (백엔드) ⟹ scope 외 — 본 Epic 다루지 않음 (Out of Scope Permanent)
- `change_summary` 에 "5-primitive" 키워드 ⟹ Epic γ #2294 (드물지만 발견되면)
- 그 외 ⟹ `uncategorized` (Lead 수동 라우팅)

### Validation rules

- `len(epic_beta_2293) + len(epic_delta_2295) + len(uncategorized) == count of AuditEntry where classification == "Suspicious"` (SC-004).
- 각 entry 의 `audit_entry_ref` 가 `cc-parity-audit.md § Modified Files` 표의 실제 행 번호 가리킴.

---

## 5. ReproducibilityProcedure — quickstart.md 의 정형화

quickstart.md 가 사람-읽기용 narrative 라면 본 entity 는 그 안의 명령 sequence 를 정형화한 schema. 실제 직렬화는 quickstart.md markdown 코드블럭 + `data/repro-manifest.json` 메타에 박제.

### 필드

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `step_id` | string | ✅ | `R1.enumerate`, `R2.spot-check`, `R3.import-verify`, `R4.classify` |
| `command` | string | ✅ | shell 명령 (절대 경로 또는 repo root 상대) |
| `inputs` | array<string> | ✅ | 입력 파일/디렉토리 list |
| `outputs` | array<string> | ✅ | 산출 파일 list (`data/*.txt|*.json`) |
| `seed` | int \| null | ✅ | 결정적 단계는 시드 명시 (R2 = 2292), 그 외는 null |
| `expected_runtime_seconds` | int | ✅ | reviewer sanity check 용 |

### Validation rules

- 4 step (`R1.enumerate`, `R2.spot-check`, `R3.import-verify`, `R4.classify`) 모두 등장.
- 결정적 step (R2) 의 seed 가 명시.
- 모든 `command` 가 `specs/2292-cc-parity-audit/scripts/` 하위 스크립트 호출 또는 stdlib/시스템 바이너리만 사용 (신규 의존성 0).

---

## 산출물 매핑 요약

| Entity | markdown 위치 | JSON 위치 |
|---|---|---|
| AuditEntry × 212 | `cc-parity-audit.md § Modified Files` | `data/modified-212-classification.json` |
| SpotCheckSample × 50 | `cc-parity-audit.md § Spot-Check (50)` | `data/spot-check-results.json` |
| ImportDiffEntry × 73 | `cc-parity-audit.md § Import-only Diff (73)` | `data/import-verify-results.json` |
| SuspiciousTransferList | `cc-parity-audit.md § Suspicious Transfer List` | `data/suspicious-transfer.json` |
| ReproducibilityProcedure × 4 | `quickstart.md` | `data/repro-manifest.json` |

---

## Constitution III note

본 Epic 은 도구 어댑터를 만들지 않으므로 Pydantic v2 모델 강제 대상이 아니다. 그러나 미래의 후속 Epic (예: Epic γ 가 audit 결과를 입력으로 받을 때) 에서 위 5 entity 를 Pydantic 으로 옮길 가능성을 열어둔다. JSON appendix 의 키 명은 그대로 Pydantic 필드로 전이 가능하도록 snake_case + Literal enum 패턴 유지.
