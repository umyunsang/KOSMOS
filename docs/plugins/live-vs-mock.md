# Live vs Mock 어댑터 선택 가이드

> 새 플러그인을 Live 또는 Mock tier 중 어디로 시작할지 결정하는 가이드. 50-item 검증 워크플로의 Q7 (5 항목) 이 두 tier 의 invariant 를 enforce 합니다.
>
> 참고: [Memory `feedback_mock_evidence_based`](../../specs/1636-plugin-dx-5tier/research.md), [Memory `feedback_mock_vs_scenario`](../../specs/1636-plugin-dx-5tier/research.md), [Constitution §IV — Live API 차단](../../.specify/memory/constitution.md), [Spec 022 BM25 retrieval](../../specs/022-mvp-main-tool/spec.md).

---

## TL;DR — 의사결정 트리

```
업스트림 시스템에 OpenAPI / 공개 endpoint 가 있는가?
├─ 예 → Authentication 흐름이 KOSMOS partnership 으로 발급 가능한가?
│       ├─ 예 → ✅ Live tier
│       └─ 아니오 (NPKI/sessionId 등) → ⚠️ Mock tier (fallback)
└─ 아니오 → 사이트 화면 / 비공식 자료에서 응답 shape 추정 가능한가?
        ├─ 예 → ⚠️ Mock tier
        └─ 아니오 (OPAQUE) → ❌ scenario 만 작성 (`docs/scenarios/`); plugin 작성 보류
```

---

## 5점 척도 매트릭스 (memory `feedback_mock_evidence_based`)

새 플러그인을 시작하기 전 **반드시** 다음 5개 차원을 명시적으로 평가:

| 차원 | 만점 (5) | 1점 (실격) |
|---|---|---|
| 📄 **Public spec** | 공식 OpenAPI / Swagger 사양 | 사이트 화면만 존재 |
| 🔑 **Authentication** | 시민용 OAuth / data.go.kr 일반 인증키 | NPKI + 부처 partnership 필수 |
| 🌐 **Egress** | HTTPS GET 1회로 응답 | 다단계 세션 + sessionId state |
| 🧪 **Evidence** | 공식 문서 + 발급 안내 페이지 | 비공식 reverse-engineering |
| 📜 **License** | KOGL / Apache-2.0 / 명시적 자유 이용 | 라이선스 불명 |

**판정 룰**:
- 5/5 모두 4점 이상 → Live tier 권장
- 1개 이상이 2점 이하 → Mock tier 시작 + 자료 출처 `mock_source_spec` 명시
- 5개 차원 중 3개 이상이 1점 → plugin 자체 보류 → `docs/scenarios/` 에 시나리오만 기록

평가 결과는 README.ko.md 의 "왜 Mock 인가?" 섹션에 명시 (Q4-CITE 가 외부 참조 URL 1개 이상 요구).

---

## Live tier — 작성 시 인지 사항

### 매니페스트 차이

```yaml
tier: live
mock_source_spec: null              # 반드시 null
processes_pii: false                # 또는 true (PII 처리 시 PIPA 블록 필수)
permission_layer: 1                 # 또는 2 / 3 (PII / irreversible 시)
```

### adapter.py 구조

```python
import os
import httpx                        # ← Q7-LIVE-USES-NETWORK 가 import 존재 검증
from .schema import LookupInput, LookupOutput

ENDPOINT = "https://api.example.go.kr/v1/lookup"

async def adapter(payload: LookupInput) -> dict:
    api_key = os.environ["KOSMOS_<MINISTRY>_API_KEY"]   # 하드코딩 금지
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.get(ENDPOINT, params={..., "serviceKey": api_key})
        response.raise_for_status()
        return _normalise(response.json())
```

### 테스트

테스트는 fixture replay (Constitution §IV — CI 는 절대 live 호출 안함):

```python
@pytest.mark.allow_network          # autouse block_network 우회
async def test_happy_path(monkeypatch, fixture_payload):
    async def _fake_get(self, url, **_):
        return _FakeResponse(fixture_payload)
    monkeypatch.setattr(httpx.AsyncClient, "get", _fake_get)
    result = await adapter(LookupInput(...))
    LookupOutput.model_validate(result)
```

Live API 를 직접 호출하는 통합 테스트는 `@pytest.mark.live` + 수동 실행 전용 (`uv run pytest -m live`).

### CI / 50-item 결과

| 항목 | 결과 |
|---|---|
| Q7-TIER-LITERAL | ✓ (`tier: live`) |
| Q7-MOCK-SOURCE | ✓ (`mock_source_spec: null`) |
| Q7-LIVE-USES-NETWORK | ✓ (httpx import 존재) |
| Q7-MOCK-NO-EGRESS | ✓ (live tier 는 면제) |
| Q7-LIVE-FIXTURE | ✓ (tests/fixtures/*.json 존재) |

---

## Mock tier — 작성 시 인지 사항

### 매니페스트 차이

```yaml
tier: mock
mock_source_spec: "https://www.example.go.kr (no public API; mock per memory feedback_mock_evidence_based)"
processes_pii: false                # mock 단계에서는 합성 fixture 만 — PII 미발생
permission_layer: 2                 # 보통 — live 전환 시 시민 동의 필요한 데이터인 경우
```

`mock_source_spec` 은 **반드시** 비어 있지 않은 문자열 (Q7-MOCK-SOURCE). 권장 형식: `<URL> (사유)`.

### adapter.py 구조

```python
# httpx import 금지 (Q7-MOCK-NO-EGRESS).
import json
from pathlib import Path
from .schema import LookupInput, LookupOutput

_FIXTURE_PATH = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "plugin.<id>.lookup.json"

async def adapter(payload: LookupInput) -> dict:
    raw = json.loads(_FIXTURE_PATH.read_text(encoding="utf-8"))
    _ = payload.model_dump()    # mock 은 input 무시; 진짜 어댑터는 여기서 사용.
    return raw
```

`tier=mock` scaffold (`kosmos plugin init <name> --tier mock`) 가 위 패턴을 자동 emit.

### 테스트

```python
async def test_replays_fixture():
    result = await adapter(LookupInput(...))
    parsed = LookupOutput.model_validate(result)
    # mock fixture 의 모든 식별자가 "MOCK-" 접두로 시작하는지 검증 — 진짜 PII 가
    # 섞여있지 않다는 보장.
    assert all(d["document_id"].startswith("MOCK-") for d in parsed.documents)
```

`@pytest.mark.allow_network` 불필요 — mock 어댑터는 socket 자체를 열지 않습니다.

### CI / 50-item 결과

| 항목 | 결과 |
|---|---|
| Q7-TIER-LITERAL | ✓ (`tier: mock`) |
| Q7-MOCK-SOURCE | ✓ (`mock_source_spec` 비어있지 않음) |
| Q7-LIVE-USES-NETWORK | ✓ (mock tier 는 면제) |
| Q7-MOCK-NO-EGRESS | ✓ (httpx / aiohttp / requests import 없음) |
| Q7-LIVE-FIXTURE | ✓ (tests/fixtures/*.json 존재) |

---

## Mock vs Scenario (memory `feedback_mock_vs_scenario`)

5점 척도에서 *3개 이상이 1점* 인 경우는 plugin 자체를 작성하지 않습니다 — `docs/mock/` (byte/shape mirror 가능 6종) 와 `docs/scenarios/` (OPAQUE 항목, 정부24 제출·KEC 서명·NPKI 포털세션) 의 분리 정책이 적용됩니다.

| 분류 | 위치 | Plugin 가능? |
|---|---|---|
| Live tier | `kosmos-plugin-store/kosmos-plugin-<name>` | ✓ |
| Mock tier (mirror 가능) | `kosmos-plugin-store/kosmos-plugin-<name>` + `docs/mock/` 출처 cite | ✓ |
| OPAQUE (시나리오만) | `docs/scenarios/<name>.md` | ✗ — scenario 문서만 |

KOSMOS host 는 OPAQUE 항목을 plugin 으로 받지 않습니다. 이는 PII 처리 invariant chain (Spec 024 V2-V4) 을 우회 가능한 attack surface 가 됩니다.

---

## Live ↔ Mock 전환 절차

### Mock → Live (partnership / OpenAPI 출시 후)

1. `manifest.yaml`: `tier: live`, `mock_source_spec: null`. PII 처리 시 `processes_pii: true` + `pipa_trustee_acknowledgment` 블록 추가 (`docs/plugins/security-review.md`).
2. `permission_layer` 재검토 — live 데이터의 민감도에 따라 1 → 2 또는 2 → 3.
3. `adapter.py`: `import httpx` 추가, `_FIXTURE_PATH` replay 제거, 실제 호출 + SSRF/timeout/size-cap 패턴 적용.
4. `tests/fixtures/<id>.json` 갱신 — 실제 응답 한 번 호출 후 PII 마스킹 정제 (`docs/plugins/data-go-kr.md` § 5 fixture 기록 절차).
5. `uv run pytest` + 50-item validation workflow → 50/50 녹색 확인.
6. SemVer minor bump (0.1.0 → 0.2.0) — tier 전환은 contract change.

### Live → Mock (API 폐쇄 / partnership 종료)

1. `manifest.yaml`: `tier: mock`, `mock_source_spec` 출처 명시.
2. `adapter.py` 의 httpx 의존 제거, fixture replay 로 교체.
3. `tests/fixtures/<id>.json` 을 mock 합성값으로 정제 (실제 응답 흔적 제거).
4. SemVer major bump (1.x.y → 2.0.0) — 기능 다운그레이드.
5. README 의 "왜 Mock 인가?" 섹션 업데이트 + history 명시.

---

## 흔한 안티 패턴

### ❌ Live 인 척하는 Mock

```yaml
tier: live
mock_source_spec: null
```

```python
# adapter.py
import httpx  # 표면상 live
async def adapter(payload):
    return _SYNTHETIC_RESPONSE   # 실제 호출 없음 — Q7-LIVE-USES-NETWORK 통과시키기 위한 위장
```

→ Q7-LIVE-FIXTURE 가 적발하지 못하지만 maintainer 보안 리뷰 시 reject. tier 정직성은 자가 보고 + maintainer 신뢰 모델.

### ❌ Mock 인데 네트워크 라이브러리 import

```yaml
tier: mock
```

```python
import httpx   # ← Q7-MOCK-NO-EGRESS 가 적발
```

→ AST scan 으로 즉시 fail.

### ❌ `mock_source_spec` 빈 문자열

```yaml
tier: mock
mock_source_spec: ""
```

→ Q7-MOCK-SOURCE 가 fail. 출처를 명시하지 못하면 mock 자체가 의심스러움.

---

## Bilingual glossary

> 이 섹션은 9개 가이드 (`docs/plugins/*.md`) 모두에 동일한 형식으로 포함됩니다 (FR-006).

| 한국어 | English | 설명 |
|---|---|---|
| Live tier | live tier | 실제 외부 API 호출. httpx import 필수 (Q7-LIVE-USES-NETWORK). |
| Mock tier | mock tier | recorded fixture replay. httpx import 금지 (Q7-MOCK-NO-EGRESS). |
| 출처 사양 | mock_source_spec | mock tier 의 mirror 출처 URL/문구. tier=mock 시 비어 있지 않음 (Q7-MOCK-SOURCE). |
| Byte mirror | byte mirror | OpenAPI 사양과 byte-equivalent 한 어댑터 (`source_mode: OPENAPI`). |
| Shape mirror | shape mirror | OSS SDK / 응답 shape 만 mirror (`source_mode: OOS`). |
| OPAQUE | OPAQUE | 정부24 제출 / KEC 서명 / NPKI 포털세션 등 mirror 불가 항목 — plugin 으로 작성 안함. |
| 합성값 | synthetic value | mock fixture 의 가짜 데이터. "MOCK-" 접두사 권장 — 실제 PII 와 구분. |
| Fixture replay | fixture replay | 테스트가 recorded JSON 을 monkey-patch 로 주입. |
| 보수적 default | conservative default | fail-closed 원칙으로 작은 rate-limit / 짧은 cache-TTL 부터 시작. |

---

## Reference

- [Memory `feedback_mock_evidence_based`](../../specs/1636-plugin-dx-5tier/research.md) — 5점 척도 매트릭스
- [Memory `feedback_mock_vs_scenario`](../../specs/1636-plugin-dx-5tier/research.md) — Plugin vs scenario 분리 정책
- [Constitution §IV](../../.specify/memory/constitution.md) — Live API CI 차단
- [Spec 022 BM25 retrieval](../../specs/022-mvp-main-tool/spec.md) — Tier 가 BM25 검색 결과에 영향 없음 (검색은 search_hint 기반)
- [docs/plugins/data-go-kr.md](data-go-kr.md) — Live tier 키 발급 + fixture 기록 절차
- [docs/plugins/security-review.md](security-review.md) — PII / Layer 3 시 PIPA §26 + sandboxing
