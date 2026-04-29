# Phase 1 Data Model — Backend Permissions Cleanup + AdapterRealDomainPolicy (Epic δ)

**Date**: 2026-04-29 · **Spec**: [spec.md § Key Entities](./spec.md#key-entities)

본 Epic 은 (a) 신규 Pydantic v2 모델 1 개, (b) 18 어댑터의 metadata 필드 변경, (c) 산출물 entity 정형화. Constitution III (Pydantic v2 strict) 직접 강제.

---

## 1. AdapterRealDomainPolicy — 신규 Pydantic v2 모델 (코드 entity)

**위치**: `src/kosmos/tools/models.py` (기존 파일에 추가)

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class AdapterRealDomainPolicy(BaseModel):
    """KOSMOS 어댑터의 단일 권한 표현 — 기관 published 정책의 cite.

    KOSMOS는 권한을 invent 하지 않는다 (.specify/memory/constitution.md § II).
    본 모델은 어댑터가 (a) 기관의 published 정책 URL 을 인용하고,
    (b) 시민에게 노출할 gate 카테고리를 선언하며,
    (c) 정책 인용의 마지막 검증 시점을 박제하는 단일 진실원이다.

    References:
    - AGENTS.md § CORE THESIS — KOSMOS = AX-infrastructure callable-channel client
    - .specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)
    - .specify/memory/constitution.md § III Pydantic v2 Strict Typing
    - specs/1979-plugin-dx-tui-integration/domain-harness-design.md § 3.2
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    real_classification_url: str = Field(
        ...,
        min_length=1,
        description="기관의 published 정책 URL (https:// 시작 권장)",
    )
    real_classification_text: str = Field(
        ...,
        min_length=1,
        description="기관 정책의 한국어 인용 (시민에게 노출되는 텍스트)",
    )
    citizen_facing_gate: Literal[
        "read-only", "login", "action", "sign", "submit"
    ] = Field(
        ...,
        description="시민-facing gate 카테고리 — UI 가 이 값으로 PermissionRequest UX 결정",
    )
    last_verified: datetime = Field(
        ...,
        description="정책 URL 의 마지막 검증 시점 (ISO 8601, UTC 권장)",
    )
```

### Invariants

- **frozen=True**: 인스턴스 불변 — 향후 KOSMOS-invented 가변 enum 패턴 reintroduction 차단.
- **extra="forbid"**: 모르는 필드 추가 시 ValidationError — Constitution II 우회 차단.
- **Literal 5 카테고리**: read-only / login / action / sign / submit 5 카테고리 외 거절. 5 카테고리는 시민 use case 분류 (cc-parity-audit + delegation-flow-design § 12 의존).
- **min_length=1 (str fields)**: empty url/text 거절.

### State transitions

본 모델은 frozen 이라 transition 없음. 어댑터 등록 시 한 번 인스턴스화되며 registry boot 동안 변경 0.

---

## 2. ResidueFile — 잔재 deletion 1 행

`adapter-migration-log.md` 의 § "Residue Deletions" 섹션.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `path` | string | ✅ | `src/kosmos/permissions/...` 상대경로 |
| `importers` | array<string> | ✅ | 이 파일을 import 하는 곳 (grep 결과) |
| `disposition` | enum {`delete`, `keep_with_rationale`} | ✅ | 기본 `delete` (Constitution II 강제) |
| `migration_target` | string \| null | optional | importer cleanup 절차 (예: "caller block 통째 삭제") |

### Validation

- ~20 entry 의 `disposition` 모두 `delete`
- 8 receipt 파일 (Spec 035 set) 은 별도 entity (KeepFile) 로 분리

---

## 3. KeepFile — Spec 035 receipt 보존 1 행

`adapter-migration-log.md` 의 § "Spec 035 Receipt Set" 섹션.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `path` | string | ✅ | `src/kosmos/permissions/<name>.py` |
| `role` | string | ✅ | 1 줄 — receipt set 내 역할 |
| `references` | array<string> | ✅ | Spec id (예: ["Spec 035", "Spec 1636"]) |

### Validation

- 7~8 entry — Spec 035 / Spec 021 receipt + OTEL helper
- 모든 entry 가 `__init__.py` 의 export list 에 포함

---

## 4. AdapterMigration — 18 어댑터 마이그레이션 1 행

`adapter-migration-log.md` 의 § "Adapter Migrations" 섹션.

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `adapter_id` | string | ✅ | 예: `koroad.accident_hazard_search` |
| `adapter_path` | string | ✅ | `src/kosmos/tools/koroad/...` |
| `agency` | string | ✅ | 예: `도로교통공단 (KOROAD)` |
| `removed_fields` | array<string> | ✅ | 제거된 KOSMOS-invented 필드 list |
| `policy.real_classification_url` | string | ✅ | 신규 인용 URL (또는 placeholder + TODO) |
| `policy.real_classification_text` | string | ✅ | 한국어 인용 |
| `policy.citizen_facing_gate` | enum (5) | ✅ | |
| `policy.last_verified` | string (ISO 8601) | ✅ | |
| `policy_url_verified` | boolean | ✅ | placeholder 면 false |

### Validation

- 18 entry — agency 별 (KOROAD ×2 + KMA ×6 + HIRA + NMC + NFA119 + MOHW + 6 mocks)
- 모든 entry 의 `removed_fields` 가 Constitution II 금지 토큰 set 의 부분집합
- 모든 entry 가 `policy` 인스턴스 보유
- `policy_url_verified == false` 인 entry 는 spec.md Deferred Items NEEDS TRACKING 으로 추적

### State transitions

`policy_url_verified: false → true` 는 후속 Epic ζ (#2297) 에서 실 정책 URL 검증 시 발생.

---

## 5. TestBaseline + TestAfter (pytest 결과)

`baseline-pytest.txt` + `after-pytest.txt` plaintext.

### 필드 (TestBaseline)

| 필드 | 타입 | 필수 |
|---|---|---|
| `total_tests` | int | ✅ |
| `pass_count` | int | ✅ |
| `fail_count` | int | ✅ |
| `failure_test_ids` | array<string> | ✅ |

### Validation

- TestAfter.failure_test_ids ⊆ TestBaseline.failure_test_ids (NEW failure 0)

---

## 산출물 매핑

| Entity | 위치 | 비고 |
|---|---|---|
| AdapterRealDomainPolicy | `src/kosmos/tools/models.py` (코드) + 단위 테스트 `tests/tools/test_adapter_real_domain_policy.py` | Pydantic v2 strict |
| ResidueFile × ~20 | `adapter-migration-log.md § Residue Deletions` | markdown 표 |
| KeepFile × 8 | `adapter-migration-log.md § Spec 035 Receipt Set` | markdown 표 |
| AdapterMigration × 18 | `adapter-migration-log.md § Adapter Migrations` | markdown 표 |
| TestBaseline + TestAfter | `baseline-pytest.txt` + `after-pytest.txt` | plaintext |
