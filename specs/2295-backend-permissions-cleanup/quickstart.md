# Quickstart — Backend Permissions Cleanup + AdapterRealDomainPolicy (Epic δ)

**Date**: 2026-04-29 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Research**: [research.md](./research.md) · **Data Model**: [data-model.md](./data-model.md)

---

## 0. 사전 조건

- Worktree: `/Users/um-yunsang/KOSMOS-w-2295/` on branch `2295-backend-permissions-cleanup`
- main `bc523b7` 베이스
- `uv sync` 완료
- 신규 dependency 0 (FR-008)

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
git rev-parse HEAD
git status --short
```

---

## 1. R1 단계 — pytest baseline 박제

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
uv sync 2>&1 | tail -3
uv run pytest 2>&1 | tee specs/2295-backend-permissions-cleanup/baseline-pytest.txt
grep -cE '^(FAILED|PASSED|ERROR)' specs/2295-backend-permissions-cleanup/baseline-pytest.txt
```

---

## 2. R2 단계 — `src/kosmos/permissions/` ~20 잔재 importer 추적 + cleanup (US1)

### 2.1 importer 추적

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
RES="aal_backstop|adapter_metadata|bypass|cli|credentials|killswitch|mode_bypass|mode_default|models|modes|pipeline|pipeline_v2|prompt|rules|session_boot|synthesis_guard|steps"
grep -rE "from\s+kosmos\.permissions\.(${RES})" src/ tests/ | sort -u
grep -rE "from\s+kosmos\.permissions\s+import\s+" src/ tests/ | sort -u
```

각 importer:
- (a) Dead → caller 함수/블록 삭제
- (b) Live + Spec 035 receipt 인접 → receipt set 으로 옮기거나 KOSMOS 등가물로 교체
- (c) Live + Constitution II 위반 호출 → caller 도 cleanup (Constitution II 강제)

### 2.2 잔재 파일 deletion

```bash
cd /Users/um-yunsang/KOSMOS-w-2295/src/kosmos/permissions
git rm aal_backstop.py adapter_metadata.py bypass.py cli.py credentials.py
git rm killswitch.py mode_bypass.py mode_default.py models.py modes.py
git rm pipeline.py pipeline_v2.py prompt.py rules.py session_boot.py synthesis_guard.py
git rm -r steps/
```

### 2.3 `__init__.py` 정정

```bash
$EDITOR src/kosmos/permissions/__init__.py
# 기존 잔재 모듈 export 줄 모두 제거
# Spec 035 receipt 모듈만 export:
#   from .ledger import *  # noqa: F401, F403
#   from .action_digest import *  # noqa: F401, F403
#   from .hmac_key import *
#   from .canonical_json import *
#   from .audit_coupling import *
#   from .ledger_verify import *
#   from .otel_emit import *
#   from .otel_integration import *
```

### 2.4 grep gate (Constitution II 토큰)

```bash
grep -rE 'pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference' src/kosmos/
# → 0 행이어야 함
```

---

## 3. R3 단계 — `AdapterRealDomainPolicy` 모델 신설 (US2)

### 3.1 모델 추가

`src/kosmos/tools/models.py` 에 다음 클래스 추가 (data-model.md § 1 참조):

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class AdapterRealDomainPolicy(BaseModel):
    """KOSMOS 어댑터의 단일 권한 표현 — 기관 published 정책의 cite.
    ...
    """
    model_config = ConfigDict(frozen=True, extra="forbid")
    real_classification_url: str = Field(..., min_length=1, ...)
    real_classification_text: str = Field(..., min_length=1, ...)
    citizen_facing_gate: Literal["read-only", "login", "action", "sign", "submit"] = Field(...)
    last_verified: datetime = Field(...)
```

### 3.2 단위 테스트 추가

`tests/tools/test_adapter_real_domain_policy.py`:
- `test_model_frozen`
- `test_extra_forbid`
- `test_url_non_empty`
- `test_gate_literal`
- `test_18_adapters_have_policy` (registry boot 후 모든 어댑터의 `policy` 인스턴스 검증)

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
uv run pytest tests/tools/test_adapter_real_domain_policy.py -v
# 5 test pass 필수
```

---

## 4. R4 단계 — 18 어댑터 metadata 마이그레이션 (US3)

### 4.1 어댑터 metadata 파일 위치

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
find src/kosmos/tools -maxdepth 3 -name "*.py" | xargs grep -lE 'auth_level|pipa_class|is_personal_data|requires_auth|dpa_reference' 2>/dev/null
```

### 4.2 각 어댑터 마이그레이션 (research.md § R-4 매트릭스)

각 어댑터 파일에서:
1. 금지 필드 (`auth_level / pipa_class / is_personal_data / dpa_reference / is_irreversible / requires_auth`) 제거
2. `from kosmos.tools.models import AdapterRealDomainPolicy` import 추가
3. metadata block 에 `policy=AdapterRealDomainPolicy(real_classification_url=..., real_classification_text=..., citizen_facing_gate="...", last_verified=datetime(2026, 4, 29, tzinfo=timezone.utc))` 인스턴스 추가
4. placeholder URL 인 경우 `# TODO: verify URL` 마커 코멘트 추가

18 어댑터 list (research.md § R-4):
- KOROAD ×2: koroad/{*.py} ×2
- KMA ×6: kma/{*.py} ×6
- HIRA ×1
- NMC ×1
- NFA119 ×1
- MOHW ×1
- Mock ×6: barocert / cbs / data_go_kr / mydata / npki_crypto / omnione

각 마이그레이션을 `adapter-migration-log.md § Adapter Migrations` 표에 박제.

### 4.3 Registry boot 검증

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
uv run python -c "
from kosmos.tools.registry import ToolRegistry
r = ToolRegistry()
print(f'Registered: {len(r.all_tools())} tools')
for t in r.all_tools():
    if hasattr(t, 'policy'):
        print(f'  {t.tool_id}: policy.url={t.policy.real_classification_url[:60]}')
    else:
        print(f'  {t.tool_id}: NO POLICY (acceptance fail)')
"
```

---

## 5. R5 단계 — 검증 (pytest + grep gate)

### 5.1 pytest

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
uv run pytest 2>&1 | tee specs/2295-backend-permissions-cleanup/after-pytest.txt
diff <(grep -E '^FAILED' specs/2295-backend-permissions-cleanup/baseline-pytest.txt | sort) \
     <(grep -E '^FAILED' specs/2295-backend-permissions-cleanup/after-pytest.txt | sort)
# after only = NEW failure (0 이어야 PASS)
```

### 5.2 Constitution II grep gate

```bash
grep -rE 'pipa_class|auth_level|permission_tier|is_personal_data|is_irreversible|requires_auth|dpa_reference' src/kosmos/
# → 0 행
```

### 5.3 18 어댑터 schema validation

```bash
uv run pytest tests/tools/test_adapter_real_domain_policy.py -v
# 5 test pass + test_18_adapters_have_policy 통과
```

---

## 6. R6 단계 — commit + push + PR

```bash
cd /Users/um-yunsang/KOSMOS-w-2295
git add -A specs/2295-backend-permissions-cleanup/ src/ tests/
git commit -m "$(cat <<'EOF'
feat(2295): backend permissions cleanup + AdapterRealDomainPolicy

- src/kosmos/permissions/ 의 ~20 Spec 033 KOSMOS-invented 잔재 파일 삭제
- Spec 035 receipt set 8 파일 보존 (ledger / action_digest / hmac_key /
  canonical_json / audit_coupling / ledger_verify / otel_emit / otel_integration)
- AdapterRealDomainPolicy Pydantic v2 모델 신설 (frozen=True, extra="forbid",
  4 필드: real_classification_url / real_classification_text /
  citizen_facing_gate / last_verified)
- 18 어댑터 metadata 마이그레이션:
  KOROAD ×2 + KMA ×6 + HIRA + NMC + NFA119 + MOHW + 6 mocks
- 기존 KOSMOS-invented 권한 분류 (auth_level / pipa_class / is_personal_data /
  is_irreversible / requires_auth / dpa_reference) 코드 레벨 0 회 잔존

Authority:
- AGENTS.md § CORE THESIS
- .specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)
- .specify/memory/constitution.md § III Pydantic v2 Strict Typing
- specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 2.3.1, § 2.3.2
- specs/1979-plugin-dx-tui-integration/domain-harness-design.md § 3.2

Closes #2295
EOF
)"

git push -u origin 2295-backend-permissions-cleanup
gh pr create --title "feat(2295): backend permissions cleanup + AdapterRealDomainPolicy" --body "Closes #2295"
```

### CI monitoring + Codex 처리는 Epic β quickstart 와 동일 절차.
