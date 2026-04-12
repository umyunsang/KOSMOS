# Gov24 Public Service API Specification

> Source: Swagger — https://infuser.odcloud.kr/api/stages/44436/api-docs
> Provider: 행정안전부 (Ministry of the Interior and Safety)
> Data name: 대한민국 공공서비스(혜택) 정보
> Base URL: https://api.odcloud.kr/api
> Auth: serviceKey query parameter (KOSMOS_DATA_GO_KR_KEY)
> Daily limit: 500,000 calls
> Formats: JSON, XML

---

## Endpoints

### 1. GET /gov24/v3/serviceList — 공공서비스 목록

#### Request Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | Page index (default: 1) |
| perPage | integer | No | Page size (default: 10) |
| returnType | string | No | JSON or XML |
| serviceKey | string | Yes | API authentication key |
| cond[서비스명::LIKE] | string | No | Service name filter |
| cond[소관기관명::LIKE] | string | No | Agency name filter |
| cond[소관기관유형::LIKE] | string | No | Agency type filter |
| cond[사용자구분::LIKE] | string | No | User category filter |
| cond[서비스분야::LIKE] | string | No | Service sector filter |
| cond[등록일시::LT] | string | No | Registration date < |
| cond[등록일시::LTE] | string | No | Registration date <= |
| cond[등록일시::GT] | string | No | Registration date > |
| cond[등록일시::GTE] | string | No | Registration date >= |
| cond[수정일시::LT] | string | No | Modification date < |
| cond[수정일시::LTE] | string | No | Modification date <= |
| cond[수정일시::GT] | string | No | Modification date > |
| cond[수정일시::GTE] | string | No | Modification date >= |

#### Response Fields (serviceList_model)

| Field | Description |
|-------|-------------|
| 서비스ID | Service unique identifier |
| 지원유형 | Support type |
| 서비스명 | Service name |
| 서비스목적요약 | Service purpose summary |
| 지원대상 | Eligible recipients |
| 선정기준 | Selection criteria |
| 지원내용 | Support details |
| 신청방법 | Application method |
| 신청기한 | Application deadline |
| 상세조회URL | Detail lookup URL |
| 소관기관코드 | Responsible agency code |
| 소관기관명 | Responsible agency name |
| 부서명 | Department name |
| 조회수 | View count |
| 소관기관유형 | Agency type |
| 사용자구분 | User category |
| 서비스분야 | Service sector |
| 접수기관 | Receiving agency |
| 전화문의 | Phone inquiry |
| 등록일시 | Registration datetime |
| 수정일시 | Modification datetime |

---

### 2. GET /gov24/v3/serviceDetail — 공공서비스 상세내용

#### Request Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | Page index (default: 1) |
| perPage | integer | No | Page size (default: 10) |
| returnType | string | No | JSON or XML |
| serviceKey | string | Yes | API authentication key |
| cond[서비스ID::EQ] | string | No | Service ID exact match |

#### Response Fields (serviceDetail_model)

| Field | Description |
|-------|-------------|
| 서비스ID | Service unique identifier |
| 지원유형 | Support type |
| 서비스명 | Service name |
| 서비스목적 | Service purpose (full) |
| 신청기한 | Application deadline |
| 지원대상 | Eligible recipients |
| 선정기준 | Selection criteria |
| 지원내용 | Support details |
| 신청방법 | Application method |
| 구비서류 | Required documents |
| 접수기관명 | Receiving agency name |
| 문의처 | Contact info |
| 온라인신청사이트URL | Online application URL |
| 수정일시 | Modification datetime |
| 소관기관명 | Responsible agency name |
| 행정규칙 | Administrative rules |
| 자치법규 | Local ordinances |
| 법령 | Laws/statutes |
| 공무원확인구비서류 | Documents verified by officials |
| 본인확인필요구비서류 | Documents requiring identity verification |

---

### 3. GET /gov24/v3/supportConditions — 공공서비스 지원조건

#### Request Parameters

| Name | Type | Required | Description |
|------|------|----------|-------------|
| page | integer | No | Page index (default: 1) |
| perPage | integer | No | Page size (default: 10) |
| returnType | string | No | JSON or XML |
| serviceKey | string | Yes | API authentication key |
| cond[서비스ID::EQ] | string | No | Service ID exact match |

#### Response Fields (supportConditions_model)

| Field | Code | Description |
|-------|------|-------------|
| 서비스ID | — | Service unique identifier |
| 서비스명 | — | Service name |
| **Demographics** | | |
| 남성 | JA0101 | Male |
| 여성 | JA0102 | Female |
| 연령 시작 | JA0110 | Age range start |
| 연령 끝 | JA0111 | Age range end |
| **Income brackets** | | |
| 기준중위소득 0~50% | JA0201 | Median income 0-50% |
| 기준중위소득 51~75% | JA0202 | Median income 51-75% |
| 기준중위소득 76~100% | JA0203 | Median income 76-100% |
| 기준중위소득 101~200% | JA0204 | Median income 101-200% |
| 기준중위소득 200% 초과 | JA0205 | Median income >200% |
| **Life status** | | |
| 임신·출산 | JA0301 | Pregnancy/childbirth |
| 장애 | JA0328 | Disability |
| 국가유공자 | JA0329 | Veteran |
| 질병·건강 | JA0330 | Disease/health |
| 근로자/직장인 | JA0313 | Worker/employee |
| 구직자/실업자 | JA0314 | Job seeker/unemployed |
| **Family/household** | | |
| 다문화가정 | JA0401 | Multicultural family |
| 한부모가정 | JA0402 | Single-parent family |
| 다자녀가구 | JA0404 | Multi-child household |
| 북한이탈주민 | JA0403 | North Korean defector |
| **Business** | | |
| 예비창업자 | JA1101 | Pre-startup |
| 영업중 | JA1102 | In operation |
| 산업분야 | JA1201–JA1299 | Industry sector codes |
| **Organization** | | |
| 기업규모 | JA2101–JA2105 | Business size |
| 기관유형 | JA2201–JA2203 | Organization type |

---

## Authentication

Two methods supported:
1. **Header**: `Authorization: Infuser {serviceKey}`
2. **Query parameter**: `?serviceKey={serviceKey}`

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 401 | Invalid authentication key |
| 500 | Internal server error |
