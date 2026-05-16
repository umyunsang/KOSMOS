# 한국국제협력단_통계정보조회

- Source: <https://www.data.go.kr/data/15158400/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `통일외교안보`
- Category/provider: `통일외교안보` / `공공기관`
- Provider: `한국국제협력단`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국국제협력단_통계정보조회
- Host: `apis.data.go.kr/B260003/StatV2Service`
- Schemes: `https, http`
### `GET /getStatBsnsRecipRankTableList`

- Endpoint: `https://apis.data.go.kr/B260003/StatV2Service/getStatBsnsRecipRankTableList`
- Summary: 유형별 수원 상위표 통계 정보
- Description: 통계정보 기준년도(시작, 종료년도), 순위를 기준으로 순위, 전체사업, 사업유형별(프로젝트, 개발컨설팅, 봉사단, 연수생초청사업, 소규모무상원조, 전문가파견, 민관협력사업, 인도적지원, 국제기구협력사업) 국가, 지원액, 비율을 순위별로 조회하는 유형별 수원 상위표 통계 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `P_START_YEAR` | yes | string | 시작년도 |
| `P_END_YEAR` | yes | string | 종료년도 |
| `M_LANG_MODE` | yes | string | 언어모드.한글/영문 구분(한글:KO,영문:EN) |
| `P_RANK_CNT` | yes | number | 순위 조회 범위값. 기본값 20으로 20위까지 조회 됨. 30위까지 조회하고자 하면 30으로 기술하면 됨. |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `HEADER.RESULT_CODE: 결과코드`
- `HEADER.RESULT_MSG: 결과메세지`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.SAMT_RATE_TOT: 전체사업 비율`
- `BODY.ITEMS.ITEM.TOT_CNT: 총건수`
- `BODY.ITEMS.ITEM.TO_RANK_CNT: 순위노출갯수`
- `BODY.ITEMS.ITEM.FONTCOLOR: 합계표시구분색깔`
- `BODY.ITEMS.ITEM.NATION_NM_01: 프로젝트`
- `BODY.ITEMS.ITEM.NATION_NM_02: 개발컨설팅`
- `BODY.ITEMS.ITEM.NATION_NM_03: 봉사단 `
- `BODY.ITEMS.ITEM.NATION_NM_04: 연수생초청사업 `
- `BODY.ITEMS.ITEM.NATION_NM_05: 소규모무상원조 `
- `BODY.ITEMS.ITEM.NATION_NM_06: 전문가파견 `
- `BODY.ITEMS.ITEM.NATION_NM_07: 민관협력사업 `
- `BODY.ITEMS.ITEM.NATION_NM_08: 인도적지원 `
- `BODY.ITEMS.ITEM.NATION_NM_09: 국제 기구협력사업`
- `BODY.ITEMS.ITEM.NATION_NM: 국가명 `
- `BODY.ITEMS.ITEM.SAMT_DLR_01: 프로젝트 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_02: 개발컨설팅 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_03: 봉사단 지원액 달러 금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_04: 연수생초청사업 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_05: 소규모무상원조 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_06: 전문가파견 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_07: 민관협력사업 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_08: 인도적지원 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_09: 국제기구협력사업 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_DLR_TOT: 전체사업 지원액 달러금액`

### `GET /getStatAreaList`

- Endpoint: `https://apis.data.go.kr/B260003/StatV2Service/getStatAreaList`
- Summary: 지역별 통계 정보
- Description: 통계정보 기준년도(시작,종료년도), 지역을 기준으로 지역, 구분(금액, 전년대비증감, 국가수, 기구수, 건수, 인원수), 연도별합계, 각 연도별 구분값을 조회하는 지역별 통계 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `P_START_YEAR` | yes | string | 조회시작년도 |
| `P_END_YEAR` | yes | string | 조회종료연도 |
| `M_LANG_MODE` | yes | string | 언어모드.한글/영문 구분(한글:KO,영문:EN)\t |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `HEADER.RESULT_MSG: 결과메세지`
- `HEADER.RESULT_CODE: 결과코드`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.DIV: 구분`
- `BODY.ITEMS.ITEM.DIV_[year]: 조회 기간에 따라 동적으로 생성 ex) 조회기간: 2020 ~ 2022 시,  DIV_2020, DIV_2021, DIV_2022`
- `BODY.ITEMS.ITEM.DIV_TOT: 총합계`
- `BODY.ITEMS.ITEM.FONTCOLOR: 폰트색깔 `
- `BODY.ITEMS.ITEM.KOICA_AREA_SE_CD: 코이카지역코드`
- `BODY.ITEMS.ITEM.KOICA_AREA_SE_NM: 코이카지역명`
- `BODY.ITEMS.ITEM.ORDR_NO: 데이터 순서`
- `BODY.ITEMS.ITEM.RNUM: 행번호`
- `BODY.ITEMS.ITEM.TOT_CNT: 데이터 총 건수`
- `totalCount: 데이터 총건수`

### `GET /getStatBsrList`

- Endpoint: `https://apis.data.go.kr/B260003/StatV2Service/getStatBsrList`
- Summary: 사업분야별 통계 정보
- Description: 통계정보 기준년도(시작,종료년도), 국가를 기준으로 사업분야, 구분(금액, 국가수, 기구수, 건수, 인원수), 연도별합계 , 각연도별 사업분야 구분값를 조회하는 사업분야별 통계 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `P_START_YEAR` | yes | string | 시작년도 |
| `P_END_YEAR` | yes | string | 종료년도 |
| `M_LANG_MODE` | yes | string | 한글/영문 구분 (한글:KO, 영문:EN) |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `HEADER.RESULT_MSG: 결과메세지`
- `HEADER.RESULT_CODE: 결과코드`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.TOT_CNT: 데이터 총건수`
- `BODY.ITEMS.ITEM.DIV: 구분`
- `BODY.ITEMS.ITEM.DIV_[year]: 조회 기간에 따라 동적으로 생성 ex) 조회기간: 2020 ~ 2022 시,  DIV_2020, DIV_2021, DIV_2022`
- `BODY.ITEMS.ITEM.DIV_TOT: 총합계`
- `BODY.ITEMS.ITEM.FONTCOLOR: 합계표시 구분색깔`
- `BODY.ITEMS.ITEM.ORDR_NO: 정렬순서`
- `BODY.ITEMS.ITEM.RNUM: 행번호`
- `BODY.ITEMS.ITEM.SPORT_REALM_CD: 사업분야코드`
- `BODY.ITEMS.ITEM.SPORT_REALM_NM: 사업분야명`
- `totalCount: 전체 결과 수 `

### `GET /getStatBtypList`

- Endpoint: `https://apis.data.go.kr/B260003/StatV2Service/getStatBtypList`
- Summary: 사업유형별 통계 정보
- Description: 통계정보 기준년도(시작,종료년도), 국가를 기준으로 사업유형별, 구분(금액, 국가수, 기구수, 건수, 인원수), 연도별합계, 각연도별 사업유형 구분값를 조회하는 사업유형별 통계 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `P_START_YEAR` | yes | string | 시작년도 |
| `P_END_YEAR` | yes | string | 종료년도 |
| `M_LANG_MODE` | yes | string | 한글/영문 구분(한글:KO,영문:EN) |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.BSNS_STLE_NM: 사업구분`
- `BODY.ITEMS.ITEM.BTYP_CD: 사업구분코드`
- `BODY.ITEMS.ITEM.DIV: 구분`
- `BODY.ITEMS.ITEM.DIV_[year]: 조회 기간에 따라 동적으로 생성 ex) 조회기간: 2020 ~ 2022 시,  DIV_2020, DIV_2021, DIV_2022`
- `BODY.ITEMS.ITEM.FONTCOLOR: 합계표시 구분색깔`
- `BODY.ITEMS.ITEM.ORDR_NO: 조회순서`
- `BODY.ITEMS.ITEM.RNUM: 행번호`
- `BODY.ITEMS.ITEM.TOT_CNT: 데이터 총건수`
- `BODY.ITEMS.ITEM.DIV_TOT: 합계`
- `totalCount: 데이터 총건수`

### `GET /getStatIncomeLevelList`

- Endpoint: `https://apis.data.go.kr/B260003/StatV2Service/getStatIncomeLevelList`
- Summary: 소득수준별 통계 정보
- Description: 통계정보 기준년도(시작,종료년도)를 기준으로 연도, 사업유형, 지원액(원,달러), 비율, 국가(기구포함)수, 전체,신규건수, 전체,신규 인원수를 조회하는 소득수준별 통계 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `M_TOT_CNT` | yes | string | 합계 항목명 |
| `M_ALL_TOT_CNT` | yes | string | 총합계 항목명 |
| `M_LANG_MODE` | yes | string | 한글/영문 구분 (한글:KO, 영문:EN) |
| `P_START_YEAR` | yes | string | 시작년도 |
| `P_END_YEAR` | yes | string | 종료년도 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `HEADER.RESULT_MSG: 결과메세지`
- `HEADER.RESULT_CODE: 결과코드`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.TOT_CNT: 총건수`
- `BODY.ITEMS.ITEM.BSNS_STLE_NM: 소득수준구분`
- `BODY.ITEMS.ITEM.FONTCOLOR: 합계표시 구분색깔`
- `BODY.ITEMS.ITEM.ORDR_YEAR: 년도`
- `BODY.ITEMS.ITEM.RNUM: 행번호`
- `BODY.ITEMS.ITEM.SAMT_DLR: 지원액 달러금액`
- `BODY.ITEMS.ITEM.SAMT_RATE: 비율`
- `BODY.ITEMS.ITEM.SAMT_WON: 지원액 원화금액`
- `totalCount: 데이터 총건수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
