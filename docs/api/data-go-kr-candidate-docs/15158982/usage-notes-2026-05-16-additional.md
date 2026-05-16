# 대구광역시_시설정보 조회 서비스_GW

- Source: <https://www.data.go.kr/data/15158982/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `환경기상`
- Category/provider: `환경기상` / `자치행정기관`
- Provider: `대구광역시`
- UMMAYA primitive candidate: `locate/find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 대구광역시_시설정보 조회 서비스_GW
- Host: `apis.data.go.kr/6270000/openData_3`
- Schemes: `https, http`
### `GET /CntrwkList`

- Endpoint: `https://apis.data.go.kr/6270000/openData_3/CntrwkList`
- Summary: 공사정보 조회 서비스
- Description: 일반공사 정보를 제공하는 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `startdate` | yes | string | 시작년월일 |
| `enddate` | yes | string | 종료년월일 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageno` | no | string | 페이지번호 |
| `gubun` | no | string | 공사구분 정보 |
| `pageunit` | no | string | 페이지행개수 정보 |

Representative response fields:
- `rsMsg: 결과정보`
- `rsMsg.statusCode: 결과코드`
- `rsMsg.message: 결과메시지`
- `header: 항목구분`
- `count: 한 페이지 결과 수`
- `tatalCount: 전체 결과 수`
- `list: 목록`
- `list.gubun: 공사구분`
- `list.type: 공사종별`
- `list.connm: 공사명`
- `list.stworkdt: 착공일자`
- `list.completedt: 준공일자`
- `list.condt: 계약일자`
- `list.consn: 공사번호`

### `GET /CntrwkDetail`

- Endpoint: `https://apis.data.go.kr/6270000/openData_3/CntrwkDetail`
- Summary: 공사정보 상세내역 조회
- Description: 일반공사 상세내역 정보를 제공하는 서비스
- Produces: `application/json`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `consn` | yes | string | 공사번호 |

Optional params:
- None captured in Swagger parameters. Check `swaggerOprtinVOs` in `data-go-kr-detail.html` before implementation.

Representative response fields:
- `rsMsg: 결과정보`
- `rsMsg.statusCode: 결과코드`
- `rsMsg.message: 결과메시지`
- `header: 항목구분`
- `list: 조회결과`
- `list.consn: 공사번호`
- `list.gubun: 공사구분`
- `list.deptnm: 공사담당부서`
- `list.type: 공사종별`
- `list.connm: 공사명`
- `list.stworkdt: 착공일자`
- `list.completedt: 준공일자`
- `list.condt: 계약일자`
- `list.completecheckdt: 준공검사일자`
- `list.coname: 업체명`
- `list.publicpay: 관급액`
- `list.firstpay: 도급액`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
