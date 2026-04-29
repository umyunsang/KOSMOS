# Phase 0 Research — Backend Permissions Cleanup + AdapterRealDomainPolicy (Epic δ)

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Authority**: AGENTS.md § CORE THESIS · `.specify/memory/constitution.md § II + § III` · cc-source-scope-audit § 2.3.1/2.3.2 · domain-harness-design § 3.2 · delegation-flow-design § 12

---

## Deferred Items 검증 (Constitution VI gate)

spec.md `Scope Boundaries & Deferred Items` 섹션 3 항목:

| 항목 | Tracking | State |
|---|---|---|
| 18 어댑터 `real_classification_url` 실 정책 검증 | NEEDS TRACKING | 조건부 — placeholder 0 이면 자연 close |
| `citizen_facing_gate` 5 카테고리 부족 시 확장 | #2296 (Epic ε) | OPEN ✅ |
| Spec 035 receipt → TUI 노출 통합 | #2297 (Epic ζ) | OPEN ✅ |

`grep -niE '(future epic|future phase|separate epic|deferred to|out of scope for v1|later release)' spec.md plan.md`: Deferred 표 외부 매치 0 건. ✅ Principle VI 통과.

---

## R-1 — `src/kosmos/permissions/` ~20 잔재 importer 추적 절차

**Q**: 20 파일을 안전하게 삭제하려면 importer 를 모두 추적해야 한다. 어떤 절차?

**Decision**: 두 단계 grep:
1. `grep -rE "from\s+kosmos\.permissions\.(aal_backstop|adapter_metadata|bypass|cli|credentials|killswitch|mode_bypass|mode_default|models|modes|pipeline|pipeline_v2|prompt|rules|session_boot|synthesis_guard|steps)" src/ tests/` — Python import 추적
2. `grep -rE "from\s+kosmos\.permissions\s+import\s+(PermissionMode|PermissionTier|...)" src/ tests/` — symbol-level import 추적 (예: `from kosmos.permissions import PermissionTier`)

각 importer 파일에서:
- (a) 호출이 dead — caller 함수/클래스 통째 삭제 또는 KOSMOS-needed 부분만 보존
- (b) 호출이 KOSMOS 등가물로 대체 가능 — 호출부 교체
- (c) caller 자체가 본 Epic 범위 외 — 별도 follow-up issue 생성 (단 Constitution II 잔존 사유 0)

**Rationale**: memory `feedback_no_stubs_remove_or_migrate` + memory `feedback_main_verb_primitive` (메인 동사 추상화는 어댑터 layer tree 에 박제) 강제. Spec 1979 가 이미 대부분 정리했으므로 importer 잔존 가능성 낮음 (하지만 grep 으로 정확히 확인).

**Alternatives**:
- (rejected) `__init__.py` 만 정정해 export 차단: 잔재 파일은 그대로 남고 향후 누군가 직접 import 할 위험.

---

## R-2 — Spec 035 receipt 7 파일 보존 vs 잔재 분리 기준

**Q**: 어떤 파일이 Spec 035 receipt set 인가? 잔재와 어떻게 구분?

**Decision**: 7 파일 명시 list (도메인 역할):
| 파일 | 역할 | Spec 인용 |
|---|---|---|
| `ledger.py` | append-only 영수증 ledger 핵심 | Spec 035 / Spec 1636 |
| `action_digest.py` | 시민 액션 → SHA-256 digest | Spec 035 |
| `hmac_key.py` | HMAC 서명 키 관리 | Spec 035 |
| `canonical_json.py` | RFC 8785 JCS canonical JSON | Spec 035 |
| `audit_coupling.py` | audit ledger ↔ OTEL 결합 | Spec 035 + 021 |
| `ledger_verify.py` | 영수증 chain 검증 | Spec 035 |
| `otel_emit.py` | OTEL span 발행 어댑터 | Spec 021 |
| `otel_integration.py` | OTEL 통합 부트스트랩 | Spec 021 |

(8 파일이지만 `otel_emit.py` + `otel_integration.py` 가 Spec 035 의 OTEL emission helper 라 영수증 set 에 포함)

잔재 list (~20 파일): `aal_backstop / adapter_metadata / bypass / cli / credentials / killswitch / mode_bypass / mode_default / models / modes / pipeline / pipeline_v2 / prompt / rules / session_boot / synthesis_guard / steps/*`. 대부분 이름에서 KOSMOS-invented mode / spectrum / pipeline 시그널 명시.

**Rationale**: Spec 035 receipt 가 KOSMOS = AX-infrastructure callable-channel client thesis 의 audit log invariant — 시민 액션을 한 줄도 누락 없이 박제하는 단방향 receipt. 보존 필수.

**Alternatives**:
- (rejected) receipt 도 함께 정리: Spec 035 ledger 가 사용 중인 Spec 1636 plugin DX 와 향후 정책 매핑 (Epic ζ) 모두 회귀 — KOSMOS thesis 의 audit invariant 깨짐.

---

## R-3 — `AdapterRealDomainPolicy` 모델 디자인

**Q**: 4 필드의 정확한 Pydantic v2 정의는?

**Decision**:
```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class AdapterRealDomainPolicy(BaseModel):
    """KOSMOS adapter 의 단일 권한 표현 — 기관 published 정책의 cite.

    KOSMOS는 권한을 invent 하지 않는다 (Constitution II). 본 모델은
    어댑터가 (a) 기관의 published 정책 URL 을 인용하고, (b) 시민에게
    노출할 gate 카테고리를 선언하며, (c) 정책 인용의 마지막 검증 시점을
    박제하는 단일 진실원이다.

    References:
    - AGENTS.md § CORE THESIS (3rd thesis canonical)
    - .specify/memory/constitution.md § II Fail-Closed Security
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
    citizen_facing_gate: Literal["read-only", "login", "action", "sign", "submit"] = Field(
        ...,
        description="시민에게 노출할 gate 카테고리 — UI 가 이 값으로 PermissionRequest UX 결정",
    )
    last_verified: datetime = Field(
        ...,
        description="정책 URL 의 마지막 검증 시점 (ISO 8601, UTC 권장)",
    )
```

**Rationale**:
- `frozen=True`: 인스턴스 불변 — Spec 1979 의 KOSMOS-invented 가변 enum 패턴과 정반대.
- `extra="forbid"`: 모르는 필드 추가 시 ValidationError — KOSMOS-invented 필드의 슬그머니 reintroduction 차단.
- `Literal` 5 카테고리: cc-parity-audit 의 시민 use case 분류 기반 — read-only (lookup), login (verify), action (submit dry-run), sign (electronic signature), submit (정부24 식 final submit).
- `Field(min_length=1)`: empty str 거절.

**Alternatives**:
- (rejected) `pipa_class` / `auth_level` 같은 이름 재사용: Constitution II 위반.
- (rejected) 더 많은 필드 (예: `quota`, `rate_limit`): KOSMOS-needed runtime data 는 별도 adapter config 에 박제, policy 자체에는 cite 만 충분.
- (rejected) `Optional[str]` 로 url/text 허용: Constitution II 의 "기관 정책 cite only" 가 약화 — non-empty 강제.

---

## R-4 — 18 어댑터 마이그레이션 매트릭스

**Q**: 18 어댑터 each 의 published 정책 URL 후보 + citizen_facing_gate 후보?

**Decision matrix** (best-effort initial; Deferred Items #2297 으로 실 검증):
| Adapter | 기관 | url 후보 | gate |
|---|---|---|---|
| KOROAD ×2 | 도로교통공단 | `https://www.koroad.or.kr/main/web/policy/data_use.do` | read-only |
| KMA ×6 | 기상청 | `https://www.kma.go.kr/data/policy.html` | read-only |
| HIRA | 건강보험심사평가원 | `https://www.hira.or.kr/policy/...` | read-only |
| NMC | 국립의료원 응급의료 | `https://www.nemc.or.kr/policy/...` | read-only |
| NFA119 | 소방청 119 | `https://www.nfa.go.kr/policy/...` | read-only |
| MOHW | 보건복지부 | `https://www.mohw.go.kr/policy/...` | read-only |
| Mock barocert | 바로인증 (모의) | `https://example.gov.kr/policy/barocert # TODO: verify` | login |
| Mock cbs | 행정안전부 CBS (모의) | `https://example.gov.kr/policy/cbs # TODO: verify` | submit |
| Mock data_go_kr | 공공데이터포털 (모의) | `https://www.data.go.kr/policy/...` | read-only |
| Mock mydata | 마이데이터 (모의) | `https://example.gov.kr/policy/mydata # TODO: verify` | login |
| Mock npki_crypto | 공동인증서 암호 (모의) | `https://example.gov.kr/policy/npki # TODO: verify` | sign |
| Mock omnione | OmniOne 신원지갑 (모의) | `https://example.gov.kr/policy/omnione # TODO: verify` | login |

placeholder 항목 (TODO 마커) 는 Deferred Items 의 NEEDS TRACKING entry 로 추적 — 실 정책 검증은 후속 spec.

**Rationale**: Live 어댑터는 기관 published 정책 URL 추정 가능; Mock 어댑터는 도메인 자체가 OPAQUE 또는 미공개 정책이라 placeholder + TODO 마커. 단 KOSMOS thesis (cite only) 는 placeholder 라도 보존.

**Alternatives**:
- (rejected) Mock 은 `policy=None` 허용: 모델이 Optional 안 함 + Constitution II 가 cite invariant 유지.
- (rejected) 18 어댑터 모두 placeholder: Live 어댑터의 실 URL 추정은 가능하므로 placeholder 만 사용하는 것은 정보 손실.

---

## R-5 — pytest baseline + 18 어댑터 schema validation 절차

**Q**: NEW failure 0 + 18 어댑터 schema validation 의 정확한 절차는?

**Decision**:
1. cleanup 시작 직전: `cd /Users/um-yunsang/KOSMOS-w-2295 && uv run pytest 2>&1 | tee specs/2295-backend-permissions-cleanup/baseline-pytest.txt`
2. cleanup + 모델 추가 + 18 마이그레이션 후: `uv run pytest 2>&1 | tee specs/2295-backend-permissions-cleanup/after-pytest.txt`
3. NEW failure diff: `diff <(grep -E '^FAILED' baseline-pytest.txt | sort) <(grep -E '^FAILED' after-pytest.txt | sort)` — after only 가 NEW failure (0 이어야 PASS)
4. 18 어댑터 schema test: 신규 단위 테스트 1 개 — `tests/tools/test_adapter_real_domain_policy.py`:
   - test_model_frozen (instance 변경 시 ValidationError)
   - test_extra_forbid (모르는 필드 추가 시 ValidationError)
   - test_url_non_empty (empty url 거절)
   - test_gate_literal (5 카테고리 외 거절)
   - test_18_adapters_have_policy (`from kosmos.tools.registry import ToolRegistry; for adapter in registry.all(): assert hasattr(adapter, "policy") and adapter.policy.real_classification_url`)

**Rationale**: 본 Epic 의 acceptance 가 (a) 잔재 deletion 안전 + (b) 신규 모델 strict + (c) 18 어댑터 마이그레이션 정확. 5 단위 테스트가 (b) + (c) 를 직접 enforce; (a) 는 baseline 비교.

**Alternatives**:
- (rejected) schema test 없이 import smoke 만: ValidationError 시나리오 (frozen, extra="forbid", literal) 검증 안 됨.

---

## Constitution Re-check (post-research)

R-1~R-5 모두 Constitution I/II/III/VI 충족. 신규 dependency 0. Phase 1 진입 가능.
