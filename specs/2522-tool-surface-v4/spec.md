# Feature Specification: Tool surface v4 — agency-faithful contracts + description-rich + chain-free

**Feature Branch**: `feat/2522-tool-surface-v4`
**Created**: 2026-05-03
**Status**: Draft
**Originating Initiative**: #2290
**Originating Epic**: #2579

**Input**: KOSMOS 13 Live/Stub 도구 surface 의 근본 재정렬. Spec 2521 회귀 ("Invalid parameters for tool" 모든 KMA 호출 실패) 의 architectural 해결안. 사용자 디렉티브 7개 + 4 evidence file 실측 + 4 reviewer report (Software Architect / Backend Architect / Code Reviewer / Security Engineer) + 3 deep research (Commercial 표준 / OSS 프레임워크 / 학술 논문) + 9 domain technical docs (KMA ASOS / KOROAD / HIRA / NMC / NFA / MOHW / SGIS / 행안부) 정합 종합으로 single Epic 근본 해결. Phase 분할 분리 PR 거부 — 13 도구 + chain 의존성 + stub 구현 + description 갈아엎기를 single PR 로 일괄.

## User Scenarios & Testing *(mandatory)*

<!--
  KOSMOS 시민 (대한민국 국민) 이 한국어 자연 발화로 국가 행정 정보를 얻는 시나리오.
  P1 = Spec 2521 회귀 직접 fix. P2-P6 = 13 도구 그룹 별 시민 발화. P7 = chain 의존성 제거 검증.
-->

### User Story 1 - 부산 날씨 1턴 호출 (Priority: P1)

시민이 "부산 날씨 알려줘" 발화 → KOSMOS 가 KMA 어댑터를 호출하여 부산 광역시 단위의 현재 기온·강수·풍속을 응답.

**Why this priority**: Spec 2521 회귀 ("Invalid parameters for tool" 모든 KMA 호출 실패) 의 직접 해결. v0.1-alpha 데모의 가장 빈번한 사용자 발화. 이 시나리오가 동작 안 하면 KOSMOS 의 첫인상이 망가짐.

**Independent Test**: TUI PTY smoke + pytest live 테스트 양쪽에서 "부산 날씨 알려줘" 입력 시 `kma_current_observation` 단일 호출 (or autonomous turn 1 resolve_location + turn 2 KMA) 로 invalid_params 에러 없이 정상 응답 확인.

**Acceptance Scenarios**:

1. **Given** 시민이 KOSMOS TUI 에 진입 후, **When** "부산 날씨 알려줘" 발화, **Then** `kma_current_observation` 가 invalid_params 없이 호출되어 부산 광역 기온·강수 응답.
2. **Given** 시민이 시군구 단위 ("부산 사하구 날씨") 발화, **When** LLM 이 description 의 17 광역시도 표 참조, **Then** 광역 단위 (부산) 로 fallback 응답 (시군구 정확도는 LLM 한계 인정).
3. **Given** 시민이 "오늘 비 와?" 발화 (지역 모호), **When** LLM 가 turn 1 에 시민에게 지역 확인 또는 default region (직전 발화의 지역 / 사용자 onboarding 기본 지역) 사용, **Then** 명확한 지역 기반 KMA 응답.

---

### User Story 2 - 강남구 병원 1턴 호출 (Priority: P2)

시민이 "강남구 근처 병원" 발화 → HIRA 어댑터가 lat/lon 기반 반경 검색 응답.

**Why this priority**: 의료 정보 접근. HIRA 도구는 input schema 가 lat/lon 직접 받아 K-EXAONE 친화적. 단지 `_type=json` param 명 정정 + description 갈아엎기.

**Independent Test**: pytest live `hira_hospital_search` + TUI smoke "강남구 병원" → 병원 3개 이상 응답 확인.

**Acceptance Scenarios**:

1. **Given** 시민이 "강남구 병원" 발화, **When** LLM 이 turn 1 에 autonomous `resolve_location("강남구")` (선택), turn 2 에 `hira_hospital_search(lat=..., lon=..., radius=2000)`, **Then** 병원 명단 응답 (`yadmNm`, `addr`, `telno`).
2. **Given** 시민이 "내과 의원" 발화, **When** HIRA 가 `dgsbjtCdNm=내과` filter 지원하지 않는 경우, **Then** 일반 병원 명단 응답 + LLM 응답에 "내과 필터 미지원" 명시.

---

### User Story 3 - 서울 응급실 1턴 호출 (Priority: P2)

시민이 "서울 응급실 가능한 곳" 발화 → NMC 어댑터가 lat/lon 기반 응급실 가용 병상 응답.

**Why this priority**: 응급 상황 핵심 도구. 현재 어댑터는 LIVE 지만 NMC API 호출 시 한국어 query param URL encoding 안 되면 HTTP 400. encoding 자동화 fix.

**Independent Test**: pytest live `nmc_emergency_search` + TUI smoke "서울 응급실".

**Acceptance Scenarios**:

1. **Given** 시민이 "서울 응급실" 발화, **When** NMC 어댑터 호출, **Then** 응급실 명단 + 가용 병상 (`hvgc`, `hvec`) + 신선도 메타 (`hvidate`) 응답.
2. **Given** NMC API 응답이 `hvidate` 5분 이상 stale, **When** Spec 023 freshness gate 발화, **Then** stale_data 에러 + LLM 응답에 "데이터 신선도 미달" 안내.

---

### User Story 4 - 임신·출산 복지 1턴 호출 (Priority: P3)

시민이 "임신·출산 복지서비스" 발화 → MOHW 어댑터 (현재 stub) 가 SSIS API 호출하여 복지서비스 명단 응답.

**Why this priority**: MOHW 어댑터는 현재 `handle()` 미구현 stub. Param 명 버그 (snake_case `search_wrd` 정의됐지만 API 는 camelCase `srchKeyCode` 필수). 진짜 구현 필요.

**Independent Test**: pytest live `mohw_welfare_eligibility_search(life_array="007", search_wrd="출산")` → 21건 이상 응답.

**Acceptance Scenarios**:

1. **Given** 시민이 "임신 복지" 발화, **When** MOHW 어댑터가 `lifeArray=007` (camelCase, `callTp=L` 자동주입) 으로 호출, **Then** 복지서비스 명단 (`servNm`, `jurMnofNm`, `servDtlLink`) 응답.
2. **Given** 시민이 "20대 청년 복지" 발화, **When** LLM 이 description 의 7 enum 표 (`004=청년`) 참조, **Then** `lifeArray=004` 호출 + 응답.

---

### User Story 5 - 강남소방서 구급통계 1턴 호출 (Priority: P3)

시민이 "강남소방서 구급 활동 통계" 발화 → NFA 어댑터 (현재 stub) 가 NFA OpenAPI 호출하여 응급출동 통계 응답.

**Why this priority**: NFA 어댑터는 현재 `handle()` Layer3GateViolation stub. Wire param 명세 미확정 (data.go.kr 포털 추가 조사 필요). 진짜 구현 필요.

**Independent Test**: pytest live `nfa_emergency_info_service(sido_hq_ogid_nm="서울특별시", rsac_gut_fstt_ogid_nm="강남소방서", stmt_ym="202501")` → 통계 데이터 응답.

**Acceptance Scenarios**:

1. **Given** 시민이 "강남소방서 1월 구급통계" 발화, **When** NFA 어댑터 호출, **Then** 구급출동 통계 응답.
2. **Given** 시민이 "내 동네 119 출동 정보" 발화 (소방서명 모호), **When** LLM 이 description 의 17 시도본부 표 참조 + autonomous `resolve_location` 으로 광역시도 도출, **Then** 시도본부 단위 응답 + LLM 가 시민에게 정확한 소방서명 확인 요청.

---

### User Story 6 - 서울 강남구 교통사고 통계 1턴 호출 (Priority: P3)

시민이 "서울 강남구 교통사고 위험지역" 발화 → KOROAD 어댑터가 사고 hazard spot 응답.

**Why this priority**: KOROAD 도구 2개 모두 LIVE. 단 `koroad_accident_search` 의 docs 의 siDo/guGun 코드체계 표기 오류 (4-digit 표기됐지만 실제 API 는 2+3 digit). docs + description 정정 필요.

**Independent Test**: pytest live `koroad_accident_hazard_search(adm_cd="1168000000", year=2024)` → hazard spot 3개 이상 응답.

**Acceptance Scenarios**:

1. **Given** 시민이 "강남구 교통사고 다발지" 발화, **When** LLM 이 turn 1 에 autonomous `resolve_location("강남구")` 로 `b_code="1168000000"` 도출, turn 2 에 `koroad_accident_hazard_search(adm_cd="1168000000")`, **Then** hazard spot 명단 응답 (`spot_nm`, `occrrnc_cnt`, `caslt_cnt`, `geom_json` 제거됨).
2. **Given** 시민이 "서울 강남구 사고 통계" 발화, **When** LLM 이 description 의 시도 17 코드 + 시군구 fallback 정책 참조 + `koroad_accident_search(siDo="11", guGun="680")` (2+3 digit) 호출, **Then** 사고 통계 응답.

---

### User Story 7 - chain 의존성 없이 시민이 자율 호출 (Priority: P2)

시민이 KOSMOS 의 어떤 도메인 도구든 호출할 때, KOSMOS 가 강제로 cross-domain chain 만들지 않음. LLM 이 시민 발화 의도를 보고 turn 단위 자율 chain (필요 시 turn 1 = `resolve_location`, turn 2 = 도메인 도구) 구성.

**Why this priority**: 사용자 디렉티브 핵심. `models.py:577` 의 잘못된 LLM 지시 ("KMA 도구는 nx/ny 변환해서 별도 받음") 가 실제와 불일치. 이 chain 강제 의존성 제거가 v4 의 architectural 핵심.

**Independent Test**: 13 도구 모두에 대해 description 에 "self-contained, do not chain" 명시 확인 + `models.py:577` 정정 확인 + TUI smoke 시나리오에서 KOSMOS 가 chain 강제하지 않는 것 확인.

**Acceptance Scenarios**:

1. **Given** 시민이 "강남구 병원" 발화, **When** KOSMOS 가 LLM 에게 chain 강요하지 않음, **Then** LLM 이 자율적으로 turn 1 = resolve_location (선택, lat/lon 모를 때) → turn 2 = HIRA 호출.
2. **Given** 시민이 "lat 37.5 lon 127.0 병원" 발화 (lat/lon 직접), **When** LLM 이 resolve_location 호출 불필요 판단, **Then** 단일 turn 에 HIRA 만 호출.

---

### Edge Cases

- 시민이 모호한 지역 발화 ("우리 동네 날씨"). LLM 이 turn 1 에 시민에게 지역 확인 요청 또는 onboarding default 지역 사용.
- 시민이 광역시도 외 지명 (강남구, 사하구 등 시군구 단위) 발화. LLM 이 광역 단위로 fallback (description 의 17 광역시도 표 까지만 정확).
- 시민이 도메인 외 발화 ("주식 시세", "비트코인" 등 KOSMOS scope 밖). LLM 이 BM25 후보 0 → "지원하지 않는 도메인" 응답.
- 도메인 API 가 일시 다운 (NMC `getEgytListInfoInqire` 등). 어댑터가 에러 envelope (`upstream_unavailable`) 반환 → LLM 이 시민에게 안내 + 다른 도구 (예: HIRA) 제안.
- 시민이 한국어/영어 혼용 발화 ("Seoul 날씨"). description 의 광역시도 표가 한국어 우선 — 영어 fallback 은 LLM 학습 지식.

## Requirements *(mandatory)*

### Functional Requirements

#### 도메인 독립 + chain 제거 (사용자 디렉티브 핵심)

- **FR-001**: 시스템 MUST 13 도구 모두 agency contract 그대로 input schema 보존 (KMA `nx,ny` / KOROAD `siDo,guGun` 2+3-digit / HIRA `xPos,yPos` / NMC `lat,lon` / NFA `sido_hq_ogid_nm` 등). lat/lon-only normalization 또는 alias 패턴 또는 discriminated union 도입 X.
- **FR-002**: 시스템 MUST `models.py:577` 의 잘못된 LLM 지시 ("후속 도구에 nx/ny 가 필요하면 'coords' 충분 — KMA 도구는 nx/ny 를 좌표 → grid 변환해서 별도 받음") 제거 또는 정정.
- **FR-003**: 시스템 MUST KOSMOS 가 cross-domain auto-chain 강제하지 않도록 모든 어댑터 description 에 "self-contained, do not chain" 명시.
- **FR-004**: 시스템 MUST LLM autonomous chain (시민 자율로 turn 1 = `resolve_location`, turn 2 = 도메인 도구) 을 자연스러운 도구 사용으로 허용. KOSMOS 가 LLM 에 chain 강요하지 않으면 충분.
- **FR-005**: 시스템 MUST parameter lookup 도구 (예: `latlon_to_lcc`, `koroad_admin_lookup`) 신설하지 않음. 어댑터가 자체 backend util 로 처리.

#### Description 5-섹션 골격 일괄 적용

- **FR-006**: 시스템 MUST 13 도구 모두 description 5-섹션 골격 적용:
  1. 목적 (1-2 문장)
  2. 입력 quirk (param 명 정확 / encoding 룰 / 필수 vs 선택 / agency-specific 명명)
  3. 17 광역시도 short reference 인라인 (≤200 tokens, mirror data) — KMA nx/ny 17개 / KOROAD siDo 17개 / KMA stn_id 17개 / MOHW 7 enum / NFA 시도본부 17개 (도메인별 적합한 형태)
  4. Domain quirk (`base_time :40 안정` / `_type=json` / `resultCode "00" string` / `geom_json strip` / `callTp=L 필수` 등)
  5. Self-contained 명시 + autonomous chain 권장 ("시민이 정확한 코드 모르면 LLM 이 자율적으로 turn 1 = resolve_location, turn 2 = 이 도구")
- **FR-007**: 시스템 MUST 모든 description 의 17 광역시도 short reference 가 ≤200 tokens 이내. 시군구 250+ 단위 매핑은 description 에 포함 X (LLM 한계 인정).

#### 1줄 / 단순 fix (8 도구)

- **FR-008**: `kma_pre_warning` 어댑터의 endpoint MUST `getPreWrnList` (404) 에서 `getWthrWrnList` (실제 동작) 로 정정.
- **FR-009**: `kma_weather_alert_status` 어댑터 MUST `stn_id` 또는 `tmFc` 필수 파라미터로 받음. description 에 autonomous chain (turn 1 = `kma_pre_warning` 결과의 stn_id 사용, turn 2 = 이 도구) 명시.
- **FR-010**: `hira_hospital_search` 어댑터 MUST `_type=json` param 명 사용 (현재 추정 `type=json` → XML 반환).
- **FR-011**: `nmc_emergency_search` 어댑터 MUST URL encoding 자동화 (`httpx.params={}` dict 사용, string interpolation 금지).
- **FR-012**: `koroad_accident_search` 어댑터의 docs 와 description MUST siDo/guGun 코드체계를 2+3-digit (예: 서울 = "11", 강남구 = "680") 으로 정정. 4-digit 표기 (예: "1100", "1116") 는 실제 API 동작 X.
- **FR-013**: `koroad_accident_hazard_search` 어댑터 MUST 응답의 `geom_json` Polygon 필드 (~500자) 제거 후 LLM 에 emit (token 절약).

#### Stub 진짜 구현 (2 도구)

- **FR-014**: `nfa_emergency_info_service` 어댑터 MUST 진짜 `handle()` 구현. 현재 Layer3GateViolation stub. data.go.kr 포털에서 wire param 명세 (정확한 camelCase / snake_case / `stmtYm` vs `stmt_ym` 등) 확인 후 구현. 6 sub-operation (activity / transfer / condition / firstaid / vehicle_dispatch / vehicle_info) 모두 지원.
- **FR-015**: `mohw_welfare_eligibility_search` 어댑터 MUST 진짜 `handle()` 구현. `callTp=L` + `srchKeyCode=003` 자동주입. camelCase 파라미터 직렬화 (`lifeArray`, `trgterIndvdlArray` 등). UTF-8 XML 응답 파싱. 7 enum (life_array) 매핑 처리.

#### resolve_location 출력 표준화

- **FR-016**: `resolve_location` 어댑터 출력 MUST 4종 필드 보장: `lat: float`, `lon: float`, `b_code: str` (10-digit 행정동코드), `address_name: str` (정규화 주소 문자열). 누락 시 하위 어댑터 중복 호출 발생.
- **FR-017**: `resolve_location` 어댑터 MUST Kakao Local API 단독 백엔드로 충분. JUSO / SGIS 백엔드는 optional fallback 으로 유지 (env 키 없으면 skip).

#### Mirror data 정책

- **FR-018**: 시스템 MUST mirror reference data (예: `grid_coords.py:REGION_TO_GRID`, `koroad/code_tables.py:SidoCode·GugunCode·SIDO_GUGUN_MAP`) 를 KOSMOS 코드 안에 둘 수 있음. 별도 data file 분리 강제 X. 단, 새로운 mirror dict 도입 시 출처 기관 docs URL 인용 의무.
- **FR-019**: 시스템 MUST 사용자 디렉티브 "도메인끼리 chain 하지 마" 와 "parameter lookup 도구 만들지 마" 를 어기지 않는 한도에서 mirror 사용 자유. mirror 가 없으면 어댑터 input schema 가 LLM 친화적이지 않은 도메인 (KMA Lambert grid, KOROAD 4-digit 코드, KMA station 156개) 도구 가용성 손실.

#### 검증 / 테스트

- **FR-020**: 시스템 MUST 13 도구 모두 pytest unit (Mock) + pytest live (`@pytest.mark.live`) 양쪽 케이스 통과.
- **FR-021**: 시스템 MUST TUI PTY smoke 4 시나리오 (부산 날씨 / 강남구 병원 / 서울 응급실 / 임신·출산 복지) single-turn 또는 2-turn success.
- **FR-022**: 시스템 MUST docs/api/* 13 어댑터 doc 의 7-section 템플릿 동기화 (Spec 1637 호환).

### Key Entities *(include if feature involves data)*

- **GovAPITool**: 14 도구 (13 ministry adapter + `resolve_location`) 의 공통 메타데이터. `id`, `input_schema`, `output_schema`, `llm_description` (5-섹션 골격 적용), `policy` (agency citation), `is_concurrency_safe`, `cache_ttl_seconds`, `rate_limit_per_minute`, `is_core`, `primitive`.
- **DescriptionSection**: 5-섹션 골격의 individual section. 5종 (목적 / 입력 quirk / short reference / domain quirk / self-contained 선언).
- **ShortReference**: 17 광역시도 단위 mirror table. KMA nx/ny / KOROAD siDo / KMA stn_id / MOHW 7 enum / NFA 시도본부 17개. ≤200 tokens.
- **AdapterPolicy**: 어댑터의 agency-published policy citation. `real_classification_url`, `real_classification_text`, `citizen_facing_gate`, `last_verified`. KOSMOS 권한 발명 X (사용자 디렉티브).
- **ResolveLocationOutput**: 4종 필드 표준화. `lat`, `lon`, `b_code`, `address_name`. v4 표준.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 시민이 "부산 날씨 알려줘" 발화 시 ≤2 turn 안 (turn 1 optional `resolve_location`, turn 2 `kma_current_observation`) `invalid_params` 에러 없이 응답. Spec 2521 회귀 baseline 100% 실패율 → 0% 실패율.
- **SC-002**: 13 도구 모두 ≤2 turn success rate ≥ 80% (10 case 표본, K-EXAONE on FriendliAI tier 1 환경).
- **SC-003**: `invalid_params` 에러율 ≤ 10% (4 evidence file 측정 baseline 50%+ → 10% 이하).
- **SC-004**: TUI PTY smoke 4 시나리오 (부산 날씨 / 강남구 병원 / 서울 응급실 / 임신·출산 복지) 모두 single-turn 또는 2-turn success. evidence: `specs/2522-tool-surface-v4/scripts/smoke-*.expect` + `specs/.../frames/`.
- **SC-005**: pytest @pytest.mark.live 도구별 1+ 케이스 success. 13 도구 × 1 case ≥ 13 success.
- **SC-006**: NFA / MOHW stub 진짜 구현 후 docs/api/* 7-section 동기화 100% (Spec 1637 호환).
- **SC-007**: `bun test` (TUI 측 — 이 spec 의 변경은 backend 만이지만 회귀 검증) 100% pass / `pytest` 100% pass.
- **SC-008**: description 5-섹션 골격 13 도구 일괄 적용 검증 — 각 description 가 5-섹션 헤더 (목적 / 입력 quirk / short reference / domain quirk / self-contained) 포함 + ≤500 tokens 총 길이.

## Assumptions

- 시민 발화는 한국어 (영문 fallback 가능). description 의 short reference 표는 한국어 우선.
- K-EXAONE on FriendliAI tier 1 (60 RPM) 환경. 이미 Spec 2521 에서 검증.
- `KOSMOS_DATA_GO_KR_API_KEY` (KMA / KOROAD / HIRA / NMC / NFA / MOHW 통합), `KOSMOS_KAKAO_API_KEY` (Kakao Local), `KOSMOS_FRIENDLI_TOKEN` 모두 설정됨.
- 9 domain technical docs (KMA ASOS / KOROAD HWP / HIRA DOCX / NMC HWP / NFA DOCX + 119 station CSV / MOHW DOC / SGIS PDF / 행안부 CSV) 가 wire param 명세의 정합한 source-of-truth.
- 4 evidence file (2026-05-03 live API 측정) 가 endpoint / param 명 / 응답 schema 의 정합한 측정값.
- resolve_location 의 Kakao 백엔드 quota 100K/day 는 v0.1-alpha 데모 사용량 (≤1K/day 추정) 충분.
- Spec 2521 회귀의 root cause (description 정보 부족 → K-EXAONE 가 nx/ny 추측 → invalid_params) 가 v4 의 description 5-섹션 골격으로 해소됨.
- 시군구 단위 정확도 (예: 부산 사하구의 정확한 nx/ny) 는 LLM 한계 — 광역시도 단위까지만 정확. 사용자 디렉티브 "description 에 광역시도 17개만 인라인" 와 정합.
- mirror data 가 KOSMOS 코드 안에 있는 것이 사용자 디렉티브 (2026-05-03 정정 "미러 허용 — reimplementation 의미가 아니었음") 에 따라 허용됨.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **새 도구 추가** — 국세청 홈택스 / 정부24 wrapping / 모바일ID 발급 등 신규 어댑터 wrapping. 별도 Epic.
- **TUI 변경** — 이번 Epic 은 backend tool surface 만. TUI 의 verbose render / multi-tool layout / permission gauntlet 변경 X.
- **LLM 모델 swap** — K-EXAONE on FriendliAI 유지. 다른 LLM 도입 X.
- **Anthropic dead code 제거** — Spec 1633 Epic 진행 중. v4 와 별도.
- **resolve_location JUSO/SGIS backend 활성화** — Kakao 단독 충분 evidence (geocoding-evidence.md). JUSO/SGIS 키 발급 후 별도 Epic.
- **시군구 단위 정확도 보장** — 250+ 시군구 매핑은 LLM 한계. 광역시도 17개까지만 정확. 사용자 디렉티브 "광역시도까지만" 정합.
- **plugin (Spec 1636) data isolation** — v4 의 mirror data 는 KOSMOS 본체 코드 안. plugin contributor 는 별도 isolation 경로 (`~/.kosmos/memdir/user/plugins/<plugin_id>/`).

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| K-EXAONE 의 Korean function-calling benchmark 정량 측정 (BFCL Korean 등) | 학술 deep research 결과 — 한국어 function-calling benchmark 부재. KOSMOS 가 첫 정량 evidence 가 됨. v4 implementation 후 별도 evaluation 필요. | Phase 2 — Korean LLM eval | #2629 |
| `kma_weather_alert_status` 의 stn_id 자동 chaining (turn 1 = `kma_pre_warning`, turn 2 = 이 도구) 의 Spec 033 PermissionRule 정합 | autonomous chain 의 Spec 033 consent flow 영향 — 시민이 도구 1개 동의했는데 도구 2개 호출되는 경우의 consent re-prompt 정책 정의 필요. | Phase 2 — Permission v3 | #2630 |
| 17 시군구 / 광역시도 외 지역 (도서 / 산악) lookup 정확도 향상 | description 의 17 광역시도 표는 광역만. 도서/산악 (예: 울릉도 stn_id=115) 은 LLM 학습 지식 의존. 별도 어댑터 또는 SGIS backend 활성화 시 해소. | Phase 2 — resolve_location v2 | #2631 |
| docs/api/* 의 plugin contributor 친화 refresh process | data.go.kr 의 wire param 명세 변경 시 KOSMOS 가 어떻게 추적할지. 자동 diff / health check / breaking-change 알람 mechanism. | Phase 3 — adapter health monitoring | #2632 |
| `mohw_welfare_eligibility_search` 의 `srchKeyCode=003` 외 검색 모드 (`001` 서비스명 / `002` 요약) 지원 | v4 는 `003` (둘 다) 만 default. 시민이 명시적으로 검색 모드 선택 발화 시 description 추가 필요. | Phase 2 — MOHW v2 | #2633 |
| `nfa_emergency_info_service` 의 6 sub-operation 별 분리 도구화 vs 단일 도구 + operation enum | v4 는 단일 어댑터 + `operation` discriminator. 시민이 sub-operation 별로 자연 발화 시 description 5-섹션 부족 가능성. 향후 evidence 기반으로 도구 분리 검토. | Phase 2 — NFA v2 | #2634 |
| `koroad_accident_search` 의 시군구 4-digit 코드 (KOROAD 자체 enum) → 행정동코드 (resolve_location.b_code) 매핑 자동화 | 현재 LLM autonomous chain 으로 처리. 향후 어댑터 내부에서 b_code → KOROAD 4-digit 자동 변환 검토. | Phase 2 — KOROAD v2 | #2635 |
