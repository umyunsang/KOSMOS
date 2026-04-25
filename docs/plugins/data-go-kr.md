# `data.go.kr` 포털 키 연동 가이드

> 공공데이터포털([data.go.kr](https://data.go.kr)) API 키를 안전하게 사용해 KOSMOS 플러그인을 작성하는 방법.
>
> 참고: [`docs/tool-adapters.md § Recording fixtures`](../tool-adapters.md), [`AGENTS.md` hard rules — 키 하드코딩 금지](../../AGENTS.md), [Spec 022 BM25 retrieval](../../specs/022-mvp-main-tool/spec.md), [Constitution §IV — Live API CI 차단](../../.specify/memory/constitution.md).

---

## 1. 키 발급 절차

1. <https://data.go.kr> 회원가입 (무료)
2. 사용하려는 API (예: KOROAD 사고 다발 지역, KMA 단기예보) 의 "활용신청" 클릭
3. 일반 인증키 (Encoding) 와 일반 인증키 (Decoding) 두 종류가 발급됩니다 — KOSMOS 는 **Encoding 키**를 그대로 사용합니다 (URL-encoded value 가 발급됨).
4. 승인까지 평균 1-2시간 (자동), 일부 부처 API 는 1-2일 소요.

> **중요**: 일반 인증키는 IP 화이트리스트 없이 발급되지만, 트래픽 추적을 위해 발급자 정보가 로그됩니다. 키를 공유 / 유출하지 마세요.

---

## 2. 환경변수 패턴 (`KOSMOS_*` 강제)

KOSMOS 의 모든 API 키는 반드시 `KOSMOS_` prefix env var 로 읽어야 합니다 (AGENTS.md hard rule):

```python
# ✓ 올바른 패턴
import os
api_key = os.environ["KOSMOS_DATA_GO_KR_API_KEY"]

# ✗ 금지: 하드코딩
api_key = "abcd1234..."  # PR 차단됨

# ✗ 금지: 다른 prefix
api_key = os.environ["DATA_GO_KR_KEY"]  # KOSMOS_ prefix 누락
```

기존 host 어댑터들은 `data.go.kr` 통합 키 (`KOSMOS_DATA_GO_KR_API_KEY`) 를 공유합니다. 부처별로 별도 키가 필요한 경우 다음 패턴을 따르세요:

| 환경변수 | 용도 |
|---|---|
| `KOSMOS_DATA_GO_KR_API_KEY` | 공공데이터포털 통합 키 (KOROAD / KMA / HIRA 공유) |
| `KOSMOS_KAKAO_API_KEY` | Kakao REST API |
| `KOSMOS_JUSO_CONFM_KEY` | 행정안전부 도로명주소 확인키 |
| `KOSMOS_SGIS_KEY` / `KOSMOS_SGIS_SECRET` | 통계청 SGIS |
| `KOSMOS_<MINISTRY>_API_KEY` | 신규 부처 API (플러그인이 직접 정의) |

`pydantic_settings.BaseSettings` 와 결합하면 자동 로드 + validation 이 가능합니다 — 자세한 패턴은 `src/kosmos/settings.py` 참고.

---

## 3. `.env` 파일 + git-ignore

로컬 개발 시 다음 패턴 사용:

```bash
# .env (절대 commit 하지 말 것; .gitignore 에 등록 필수)
KOSMOS_DATA_GO_KR_API_KEY=your-encoding-key-here
KOSMOS_KAKAO_API_KEY=your-kakao-key-here
```

`.gitignore` 에 다음 라인이 반드시 포함:

```gitignore
.env
.env.local
secrets/
```

CI 에서는 GitHub Actions Secrets 사용 (`KOSMOS_DATA_GO_KR_API_KEY` 같은 이름으로 등록):

```yaml
# .github/workflows/plugin-validation.yml
- run: uv run pytest -m "not live"
  # CI 는 live test 를 건너뛰므로 키 노출 위험 없음
```

---

## 4. Rate-limit 인지

`data.go.kr` API 의 일반 인증키는 보통 **일일 1,000 / 10,000 / 100,000 호출** 중 하나의 quota 가 발급됩니다. 어댑터 작성 시:

```python
# adapter.py 의 GovAPITool 정의
TOOL = GovAPITool(
    # ...
    rate_limit_per_minute=10,    # 보수적 default; 실제 quota 와 균형
    cache_ttl_seconds=300,        # 응답 캐시로 quota 부담 완화
)
```

**보수적 default** (Spec 022 fail-closed):
- `rate_limit_per_minute=10` — 분당 10건 (일 14,400 calls 한도)
- `cache_ttl_seconds=0` (캐시 안함) → 부처 데이터 변동 빈도 보고 늘리기

KOROAD / KMA / HIRA 는 `rate_limit_per_minute=30` 을 채택 — 데이터가 분 단위 변동성을 가져 캐시 효용이 크지 않기 때문 (`src/kosmos/tools/koroad/koroad_accident_search.py` 참고).

---

## 5. Fixture 기록 (CI 안전성)

Constitution §IV: **CI 는 절대 live `data.go.kr` API 를 호출하지 않음**. 모든 테스트는 recorded fixture 로 동작합니다.

### 기록 절차

1. 어댑터를 작성하고 로컬에서 `.env` 키로 한 번 호출:

```python
# scripts/record_fixture.py 패턴
import asyncio
import json
from pathlib import Path
from plugin_busan_bike.adapter import adapter
from plugin_busan_bike.schema import LookupInput

async def main():
    payload = LookupInput(district="해운대구")
    result = await adapter(payload)
    fixture_path = Path("tests/fixtures/plugin.busan_bike.lookup.json")
    fixture_path.parent.mkdir(parents=True, exist_ok=True)
    fixture_path.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(f"Wrote {fixture_path}")

asyncio.run(main())
```

2. PII 가 응답에 섞여있을 수 있다면 **수기로 fixture 를 정제** — 주민등록번호, 휴대전화번호, 정확한 주소 등은 마스킹 (`010-****-1234`) 또는 합성값으로 교체.
3. fixture 를 commit:

```bash
git add tests/fixtures/plugin.busan_bike.lookup.json
git commit -m "test: record happy-path fixture for busan_bike"
```

### 테스트에서 fixture 사용

```python
# tests/test_adapter.py
import json
from pathlib import Path
import pytest

_FIXTURE = json.loads(
    Path(__file__).parent.joinpath("fixtures/plugin.busan_bike.lookup.json").read_text()
)


@pytest.mark.asyncio
async def test_adapter_happy_path_with_fixture(monkeypatch):
    async def _fake_get(*args, **kwargs):
        class R:
            def raise_for_status(self): pass
            def json(self): return {"stations": [...]}
        return R()
    monkeypatch.setattr("httpx.AsyncClient.get", _fake_get)
    # ... 어댑터 호출 + fixture 와 round-trip 비교
```

Live 호출이 필요한 통합 테스트는 `@pytest.mark.live` 마커로 격리 — CI 에서 자동 skip:

```python
@pytest.mark.live
@pytest.mark.asyncio
async def test_adapter_against_real_api():
    """수동 실행 전용. CI 에서 skip."""
    # ...
```

---

## 6. 부처별 특수 사항

### KOROAD (도로교통공단)

- 응답이 **일반 인증키 Encoding 형식 그대로** 받음 — URL decode 불필요.
- 사고 다발 지역 검색은 `adm_cd` (행정구역 코드) 기반 — `resolve_location` primitive 가 먼저 좌표/주소를 `adm_cd` 로 변환.

### KMA (기상청)

- 단기예보는 **격자 좌표 (LCC)** 기반 — `latlon_to_lcc()` (host 내장) 가 위경도를 격자 X/Y 로 변환.
- 시간 포맷이 부처마다 상이 (`HH00` / `HHmm` / `YYYYMMDDHH`) — 응답 파싱에 주의.

### HIRA (건강보험심사평가원)

- 병원 검색은 좌표 + 반경 (m) 기반.
- 응답이 종종 **빈 배열** 로 옴 (반경 부족) — 어댑터에서 `LookupCollection(items=[], total_count=0)` 으로 정규화.

### NMC (국립중앙의료원)

- 응급실 병상 정보는 **L3 gated** — Live tier 로 작성하지 말고 `tier=mock` 으로 시작 (`docs/plugins/live-vs-mock.md`).

---

## 7. PII 처리 시 주의사항

응답에 PII 가 포함된다면 **반드시** `manifest.yaml` 에 다음을 설정:

```yaml
processes_pii: true
pipa_trustee_acknowledgment:
  trustee_org_name: "<수탁자 조직명>"
  trustee_contact: "<연락처>"
  pii_fields_handled:
    - resident_registration_number
    - phone_number
  legal_basis: "PIPA §15-1-2"
  acknowledgment_sha256: "<canonical hash>"
```

acknowledgment_sha256 는 `docs/plugins/security-review.md` 의 canonical 텍스트 SHA-256 과 byte-equal 해야 합니다 — `kosmos plugin pipa-text` 명령으로 자동 계산 + 표시 가능.

자세한 PIPA §26 수탁자 책임은 [`docs/plugins/security-review.md`](security-review.md) 참고.

---

## Bilingual glossary

> 이 섹션은 9개 가이드 (`docs/plugins/*.md`) 모두에 동일한 형식으로 포함됩니다 (FR-006).

| 한국어 | English | 설명 |
|---|---|---|
| 일반 인증키 | service key | data.go.kr 발급 API 키. URL-encoded "Encoding" 형식 사용. |
| 일일 quota | daily quota | 일반 인증키별 일일 호출 한도 (1k / 10k / 100k). |
| 격자 좌표 | LCC grid | 기상청 단기예보 좌표계 (Lambert Conformal Conic). |
| 행정구역 코드 | adm_cd | 통계청 SGIS 행정구역 ID; 광역(2) / 시군구(5) / 읍면동(8자리). |
| 보수적 default | conservative default | fail-closed 원칙으로 작은 rate-limit / 짧은 cache-TTL 부터 시작. |
| Recorded fixture | recorded fixture | 한 번 live 호출 → JSON 저장 → CI 에서 monkey-patch 로 replay. |
| Live tier | live tier | 실제 외부 API 호출. SLSA 검증 + recorded fixture 두 트랙 모두 충족 필수. |
| Mock tier | mock tier | 외부 spec 만 참조; 실제 호출 없음. `mock_source_spec` 필수. |
