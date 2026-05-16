# 한국국제협력단_사업정보(분야,국가)조회

- Source: <https://www.data.go.kr/data/15158399/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `통일외교안보`
- Category/provider: `통일외교안보` / `공공기관`
- Provider: `한국국제협력단`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국국제협력단_사업정보(분야,국가)조회
- Host: `apis.data.go.kr/B260003/BsnsAddService`
- Schemes: `https, http`
### `GET /getBsnsInfoRealmList`

- Endpoint: `https://apis.data.go.kr/B260003/BsnsAddService/getBsnsInfoRealmList`
- Summary: ODA 분야별 사업목록
- Description: 사업에 기준년도(시작, 종료년도)를 기준으로 사업형태 및 분야코드로 KOICA(한국국제협력단)에서 진행하는 사업을 조회하여 사업시작년도, 사업종료년도 사업명, 사업번호, 사업형태, 코이카지역구분코드, 코이카지역명 국가코드, 국가명, 행번호, 사업분야코드, 사업코드명을 조회하는 ODA 분야별 사업목록 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `P_YEAR` | yes | string | 조회년도 |
| `P_BSNS_TY_CD` | yes | string | 사업의 형태. 문서 15페이지의 사업유형코드 참고 |
| `P_SPORT_REALM_CD` | yes | string | 분야코드. 문서 16페이지의 분야별코드 참고 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `HEADER.RESULT_CODE: 결과코드`
- `HEADER.RESULT_MSG: 결과메세지`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.TOT_CNT: 총 데이터건수`
- `BODY.ITEMS.ITEM.BSNS_BEGIN_YEAR: 사업시작년도`
- `BODY.ITEMS.ITEM.BSNS_END_YEAR: 사업종료년도`
- `BODY.ITEMS.ITEM.BSNS_NM: 사업명`
- `BODY.ITEMS.ITEM.BSNS_NO: 사업번호`
- `BODY.ITEMS.ITEM.BSNS_TY_CD: 사업형태`
- `BODY.ITEMS.ITEM.KOICA_AREA_SE_CD: 코이카지역구분코드`
- `BODY.ITEMS.ITEM.KOICA_AREA_SE_NM: 코이카지역명`
- `BODY.ITEMS.ITEM.NATION_CD: 국가코드`
- `BODY.ITEMS.ITEM.NATION_NM: 국가명`
- `BODY.ITEMS.ITEM.RNUM: 행번호`
- `BODY.ITEMS.ITEM.SPORT_REALM_CD: 사업분야코드`
- `BODY.ITEMS.ITEM.SPORT_REALM_NM: 사업분야명`
- `numOfRows: 한 페이지 결과 수`
- `pageNO: 페이지 번호`
- `totalCount: 데이터 전체 건수 `

### `GET /getBsnsInfoNationList`

- Endpoint: `https://apis.data.go.kr/B260003/BsnsAddService/getBsnsInfoNationList`
- Summary: ODA 국가별 사업목록
- Description: 사업에 기준년도(시작, 종료년도)를 기준으로 사업형태 및 국가코드로 KOICA(한국국제협력단)에서 진행하는 사업을 조회하여 사업시작년도, 사업종료년도 사업명, 사업번호, 사업형태, 코이카지역구분코드, 코이카지역명 국가코드, 국가명, 행번호, 사업분야코드, 사업코드명을 조회하는 ODA 국가별 사업목록 정보 서비스
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `P_YEAR` | yes | string | 조회년도 |
| `P_BSNS_TY_CD` | yes | string | 사업의 형태. 문서 15페이지의 사업유형코드 참고 |
| `P_NATION_CD` | yes | string | 국가코드. 문서 16페이지의 국가코드 참고 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `HEADER: HEADER`
- `HEADER.RESULT_CODE: 결과코드`
- `HEADER.RESULT_MSG: 결과메세지`
- `BODY: BODY`
- `BODY.ITEMS: ITEMS`
- `BODY.ITEMS.ITEM: ITEM`
- `BODY.ITEMS.ITEM.TOT_CNT: 데이터총건수`
- `BODY.ITEMS.ITEM.BSNS_BEGIN_YEAR: 사업시작년도`
- `BODY.ITEMS.ITEM.BSNS_END_YEAR: 사업종료년도`
- `BODY.ITEMS.ITEM.BSNS_NM: 사업명`
- `BODY.ITEMS.ITEM.BSNS_NO: 사업번호`
- `BODY.ITEMS.ITEM.BSNS_TY_CD: 사업형태`
- `BODY.ITEMS.ITEM.KOICA_AREA_SE_CD: 코이카지역구분코드`
- `BODY.ITEMS.ITEM.KOICA_AREA_SE_NM: 코이카지역명`
- `BODY.ITEMS.ITEM.NATION_CD: 국가코드`
- `BODY.ITEMS.ITEM.NATION_NM: 국가명`
- `BODY.ITEMS.ITEM.RNUM: 행번호`
- `BODY.ITEMS.ITEM.SPORT_REALM_CD: 사업분야코드`
- `BODY.ITEMS.ITEM.SPORT_REALM_NM: 사업분야명`
- `numOfRows: 결과 `
- `pageNo: 페이지번호`
- `totalCount: 데이터 총건수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
