# 한국농업기술진흥원_보육업체소개_GW Update

- Source: <https://www.data.go.kr/data/15158646/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `농축수산`
- Category/provider: `농축수산` / `공공기관`
- Provider: `한국농업기술진흥원`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 한국농업기술진흥원_보육업체소개_GW
- Host: `apis.data.go.kr/B554729/careBusiness`
- Schemes: `https, http`
### `GET /careBusinessList`

- Endpoint: `https://apis.data.go.kr/B554729/careBusiness/careBusinessList`
- Summary: 기술사업화 창업지원 보육업체 목록
- Description: 기술 사업화 창업지원 보육업체 목록을를 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지번호`
- `body.numOfRows: 한 페이지 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.companyAddr: 회사주소`
- `body.items.item.companyItem: 회사 주요품목`
- `body.items.item.companyLogo: 회사로고`
- `body.items.item.companyName: 회사명`
- `body.items.item.companyType: 회사타입`
- `body.items.item.homePage: 홈페이지`
- `body.items.item.manager: 대표자명`
- `body.items.item.managerTel: 대표자 연락처`
- `body.items.item.seq: 순번`

### `GET /careBusinessView`

- Endpoint: `https://apis.data.go.kr/B554729/careBusiness/careBusinessView`
- Summary: 기술 사업화 창업지원 보육업체 상세 조회
- Description: 기술 사업화 창업지원 보육업체 내역을 조회
- Produces: `application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `seq` | yes | string | 글번호 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메시지`
- `body: body`
- `body.totalCount: 전체 결과 수`
- `body.pageNo: 페이지번호`
- `body.numOfRows: 한 페이지 결과 수`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.companyAddr: 회사주소`
- `body.items.item.companyIntro: 회사 상세소개`
- `body.items.item.companyLogo: 회사로고`
- `body.items.item.companyName: 회사명`
- `body.items.item.homePage: 홈페이지`
- `body.items.item.manager: 대표자명`
- `body.items.item.managerTel: 대표자 연락처`
- `body.items.item.seq: 순번`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
