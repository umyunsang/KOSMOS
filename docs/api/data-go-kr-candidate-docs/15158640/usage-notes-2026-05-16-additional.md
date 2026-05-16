# 한국농업기술진흥원_종자생산현황_GW Update

- Source: <https://www.data.go.kr/data/15158640/openapi.do>
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

- Swagger title: 한국농업기술진흥원_종자생산현황_GW
- Host: `apis.data.go.kr/B554729/seedSupplyInfo`
- Schemes: `https, http`
### `GET /seedSupplyList`

- Endpoint: `https://apis.data.go.kr/B554729/seedSupplyInfo/seedSupplyList`
- Summary: 재단 종자거래 사업품종 목록
- Description: 재단 종자거래 분류, 특성 등을 제공하는 재단 종자거래 사업품종 목록
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
- `body.items.item.itemImage: 이미지링크`
- `body.items.item.itemName: 작물명`
- `body.items.item.kindName: 품종분류`
- `body.items.item.seq: 종자키값`
- `body.items.item.agriculturalName: 작물분류`
- `body.items.item.breedingOrg: 육종기관`
- `body.items.item.cropName: 품목분류`

### `GET /supplyAreaView`

- Endpoint: `https://apis.data.go.kr/B554729/seedSupplyInfo/supplyAreaView`
- Summary: 재단 종자거래 작물별/지역별 생산량
- Description: 종자품종명을 통해 작물별 지역별 생산량[지역,수량]을 조회하는 재단 종자거래 작물별/지역별 생산량
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
| `seq` | no | string | 종자키값 |

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
- `body.items.item.area: 지역`
- `body.items.item.cropName: 작물명`
- `body.items.item.itemName: 품종명`
- `body.items.item.qty: 수량`
- `body.items.item.releaseYear: 생산년도`
- `body.items.item.seq: 종자키값`

### `GET /supplyYearView`

- Endpoint: `https://apis.data.go.kr/B554729/seedSupplyInfo/supplyYearView`
- Summary: 재단 종자거래 작물/생산년도별 생산량
- Description: 종자품종명을 통해 작물별 생산년도별 생산량[생산년도, 수량]을 조회하는 재단 종자거래 작물/생산년도별 생산량
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
| `seq` | no | string | 종자키값 |

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
- `body.items.item.releaseYear: 생산년도`
- `body.items.item.seq: 종자키값`
- `body.items.item.cropName: 작물명`
- `body.items.item.itemName: 품종명`
- `body.items.item.qty: 수량`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
