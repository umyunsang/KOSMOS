# Phase 1 Data Model: Tool surface v4

**Date**: 2026-05-03
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Research**: [research.md](./research.md)

## Entities

### 1. `GovAPITool` (existing, 변경 X)

기존 UMMAYA `GovAPITool` 메타데이터 schema 그대로. 13 어댑터 + `resolve_location` 모두 이 schema 인스턴스. 사용자 디렉티브 "도메인 독립" + Constitution III (Pydantic v2 strict) 정합.

**Fields** (existing, 인용용):
- `id: str` — stable snake_case identifier (예: `kma_current_observation`)
- `name_ko: str` — Korean display name
- `ministry: str` — agency identifier (예: `KMA`, `HIRA`)
- `category: list[str]`
- `endpoint: str` — base URL
- `auth_type: Literal["public", "api_key", "oauth"]` (Spec 025)
- `input_schema: type[BaseModel]` — pydantic v2 input model (도메인 독립 — agency contract 그대로)
- `output_schema: type[BaseModel]` — pydantic v2 output model
- `llm_description: str` — **v4 핵심 변경 대상** — 5-섹션 골격 적용 (DescriptionSection 5종)
- `search_hint: str` — bilingual ko/en
- `policy: AdapterRealDomainPolicy`
- `is_concurrency_safe: bool`
- `cache_ttl_seconds: int`
- `rate_limit_per_minute: int`
- `is_core: bool`
- `primitive: Literal["lookup", "submit", "verify", "subscribe"]`
- `trigger_examples: list[str]`

**Validation rules**: 기존 `ToolRegistry.register()` 의 V1-V6 invariant (Spec 024 / 025) 보존.

### 2. `DescriptionSection` (new — v4 핵심 abstraction)

`llm_description: str` 의 구조화된 5 섹션. spec.md FR-006 의 골격을 코드 레벨에서 표현.

```python
class DescriptionSection(BaseModel):
    """v4 description 5-섹션 골격의 individual section.

    `llm_description: str` 은 이 5 섹션을 줄바꿈으로 결합한 plain text.
    어댑터 코드 레벨에서는 별도 entity 로 모델링 X (string concatenation 으로 충분).
    이 모델은 spec / docs 레벨의 conceptual entity.
    """

    purpose: str       # 섹션 1 — 목적 (1-2 문장)
    input_quirk: str   # 섹션 2 — 입력 quirk (param 명, encoding, 필수/선택)
    short_reference: str  # 섹션 3 — 17 광역시도 short reference 인라인 (≤200 tokens)
    domain_quirk: str  # 섹션 4 — domain-specific quirk (base_time, _type=json 등)
    self_contained_decl: str  # 섹션 5 — self-contained + autonomous chain 권장
```

**Validation rules**:
- 각 섹션 ≤ 100 tokens
- 총 length ≤ 500 tokens (Anthropic / OpenAI 권장 + LongFuncEval 회귀 영역 회피)
- 섹션 3 의 `short_reference` MUST 17 광역시도 단위 (시군구 250+ 단위 X — LLM 한계 인정)

**State transitions**: N/A (immutable text).

### 3. `ShortReference` (new — mirror data conceptual entity)

각 도메인의 17 광역시도 short reference table. UMMAYA 코드 안 mirror dict (`grid_coords.py:REGION_TO_GRID`, `koroad/code_tables.py:SidoCode` 등) 의 description 인라인 형태.

```python
class ShortReference(BaseModel):
    """광역시도 17개 단위 mirror reference. v4 description 의 섹션 3.

    실제 구현은 어댑터별 description 문자열에 인라인 (코드 레벨 entity X).
    이 모델은 spec / docs 레벨의 conceptual entity.
    """

    domain: Literal["KMA_GRID", "KMA_STATION", "KOROAD_SIDO", "MOHW_LIFE", "NFA_HQ"]
    rows: list[ShortReferenceRow]  # 17 광역시도 (KMA_GRID/STATION/KOROAD_SIDO/NFA_HQ) 또는 7 enum (MOHW_LIFE)
    source_doc: str  # 출처 docs path (예: "/tmp/ummaya-domain-docs/kma_asos.txt")
    last_verified: date


class ShortReferenceRow(BaseModel):
    """ShortReference 의 한 row.

    예 (KMA_GRID):
      sido_name="서울특별시", short_name="서울", code="60,127" (nx,ny)
    예 (KOROAD_SIDO):
      sido_name="서울특별시", short_name="서울", code="11" (siDo 2-digit)
    예 (MOHW_LIFE):
      sido_name=N/A, short_name="영유아", code="001"
    """

    sido_name: str | None  # MOHW_LIFE 는 None
    short_name: str        # 시민 발화의 일반 형태 (예: "서울", "영유아")
    code: str              # agency wire code
```

**Validation rules**:
- `rows` 길이: 17 (4 광역시도 도메인) 또는 7 (MOHW_LIFE) 또는 17 (NFA_HQ)
- 각 row 의 `code` MUST agency wire format (KMA: "60,127" / KOROAD: "11" / MOHW: "001")
- `source_doc` MUST `/tmp/ummaya-domain-docs/*.txt` 또는 `docs/api/*.md` 의 절대 경로 또는 UMMAYA 코드 모듈 경로 (`src/ummaya/tools/kma/grid_coords.py`)

### 4. `AdapterPolicy` (existing, 변경 X)

기존 `AdapterRealDomainPolicy` 그대로. v4 에서 새 permission 분류 발명 X (Constitution II Fail-Closed).

**Fields**:
- `real_classification_url: str` — 기관 자체 정책 URL
- `real_classification_text: str`
- `citizen_facing_gate: Literal["read-only", "session-private", "consent-prompted"]`
- `last_verified: datetime`

### 5. `ResolveLocationOutput` (modified — v4 표준)

`resolve_location` 어댑터의 출력. v4 에서 4종 필드 표준화 (FR-016).

```python
class ResolveLocationOutput(BaseModel):
    """v4 resolve_location 출력 표준.

    Kakao Local API 단독 백엔드로 4종 필드 모두 도출 (geocoding-evidence.md 검증).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    lat: float = Field(ge=-90, le=90, description="WGS84 위도 (decimal degrees)")
    lon: float = Field(ge=-180, le=180, description="WGS84 경도")
    b_code: str = Field(pattern=r"^[0-9]{10}$", description="10-digit 행정동코드 (Kakao b_code, KOROAD/HIRA adm_cd 직결)")
    address_name: str = Field(min_length=1, description="정규화 주소 문자열 (시민 표시용, 예: '서울특별시 강남구 테헤란로 152')")
    confidence: Literal["high", "medium", "low"]
    source: Literal["kakao", "juso", "sgis"]
```

**Validation rules**:
- 4 필수 필드 (`lat`, `lon`, `b_code`, `address_name`) 누락 시 ValidationError
- `b_code` regex `^[0-9]{10}$` (행정동 10자리)
- `address_name` 정규화된 문자열 (시민 표시 + 후속 도구 verbose render)

**State transitions**: N/A (immutable response).

## Relationships

```
GovAPITool (13 + 1)
  ├── input_schema: type[BaseModel]      # 도메인별 (KMA: nx/ny, HIRA: xPos/yPos, ...)
  ├── output_schema: type[BaseModel]
  ├── llm_description: str               # 5 DescriptionSection 의 string 형태
  ├── policy: AdapterPolicy              # agency citation
  └── (v4 description 의 섹션 3 short_reference 는 도메인별 ShortReference 의 인라인)

resolve_location (meta-tool)
  └── output_schema: type[ResolveLocationOutput]  # v4 4종 필드 표준
```

**Cross-domain**: 의도적으로 0. v4 의 핵심은 도메인 독립. `resolve_location` 의 출력을 다른 어댑터의 input 으로 자동 chain 하는 직접 의존성 X. LLM autonomous chain 만 (시민이 자율로 turn 1 = resolve, turn 2 = 도메인 도구).

## Implementation notes

### `llm_description` string assembly

5-섹션 string 의 어댑터별 패턴:

```python
KMA_CURRENT_OBSERVATION_TOOL = GovAPITool(
    id="kma_current_observation",
    ...,
    llm_description=(
        # 섹션 1 — 목적
        "기상청 초단기실황 — 현재 시각 기준 실제 관측 데이터 (기온/강수/습도/풍속/풍향). "
        "시민이 '오늘 날씨'/'지금 비 와'/'현재 기온' 같은 즉시 현재 상태를 묻는 경우 첫 호출.\n\n"

        # 섹션 2 — 입력 quirk
        "**입력**: `nx, ny` (KMA Lambert 격자 좌표, 1-149 / 1-253), "
        "`base_date` (YYYYMMDD), `base_time` (HHMM, 매 정시).\n\n"

        # 섹션 3 — 17 광역시도 short reference (mirror)
        "**광역시도 nx/ny 표** (시민 발화 → 격자 매핑):\n"
        "서울=(60,127) 부산=(98,76) 대구=(89,90) 인천=(55,124) 광주=(58,74) "
        "대전=(67,100) 울산=(102,84) 세종=(66,103) 경기=(60,120) 강원=(73,134) "
        "충북=(69,107) 충남=(68,100) 전북=(63,89) 전남=(51,67) 경북=(89,91) "
        "경남=(91,77) 제주=(52,38). 시군구 단위 정확도는 LLM 한계.\n\n"

        # 섹션 4 — domain quirk
        "**시간 quirk**: `base_time` 매 정시의 :40 이후만 안정. 14:25 호출 시 base_time='1300'. "
        "`resultCode` string '00' 정상 / '03' NO_DATA. dataType=JSON 권장.\n\n"

        # 섹션 5 — self-contained + autonomous chain
        "**self-contained**: 이 도구만 호출하면 됨. resolve_location 등 cross-domain chain 불필요. "
        "시민이 정확한 nx/ny 모르면 LLM 이 자율적으로 turn 1 = resolve_location, turn 2 = 이 도구."
    ),
    ...
)
```

### Mirror dict 보존 (FR-018)

```python
# src/ummaya/tools/kma/grid_coords.py — 변경 X (mirror dict 그대로)
REGION_TO_GRID = {
    "서울": (60, 127),
    "부산": (98, 76),
    # ... 17 광역시도
}

# src/ummaya/tools/koroad/code_tables.py — 변경 X (mirror IntEnum 그대로)
class SidoCode(IntEnum):
    SEOUL = 1100
    BUSAN = 1200
    # ...
```

### `models.py:577` 정정

기존 (잘못):
```python
"- 'all' : 모든 위 정보. 후속 도구에 nx/ny 가 필요하면 'coords' 충분 — "
"KMA 도구는 nx/ny 를 좌표 → grid 변환해서 별도 받음."
```

v4 정정:
```python
"- 'all' : 모든 위 정보. 후속 도구별 input schema 는 각 도구의 description 참조. "
"각 도구는 self-contained — UMMAYA 가 cross-domain chain 강제하지 않음."
```

## Constraints summary

| Constraint | Source | Enforcement |
|---|---|---|
| `llm_description` ≤ 500 tokens / 도구 | research.md Decision 2 | unit test (token count) |
| 17 광역시도 short reference (시군구 X) | spec FR-007 | description 인라인 검증 (regex match) |
| `ResolveLocationOutput` 4 필수 필드 | spec FR-016 | pydantic v2 strict validation |
| `models.py:577` 정정 phrasing | research.md Decision 4 | grep test (잘못된 phrase 부재 확인) |
| 13 도구 모두 5-섹션 골격 적용 | spec FR-006 | description regex match (5 섹션 헤더) |
| Mirror dict UMMAYA 코드 안 보존 (분리 X) | research.md Decision 1 | `data/agency-codes/` 디렉토리 부재 검증 |
