# 기상청_꽃가루농도위험지수 조회서비스(3.0)

- Source: <https://www.data.go.kr/data/15085289/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `과학기술`
- Category/provider: `과학기술` / `국가행정기관`
- Provider: `기상청`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- `꽃가루농도지수 조회서비스(3.0)_설명서 및 행정구역코드 정보 25년1분기.zip`

## Adapter-Relevant Contract

- Swagger title: 기상청_꽃가루농도위험지수 조회서비스(3.0)
- Host: `apis.data.go.kr/1360000/HealthWthrIdxServiceV3`
- Schemes: `https, http`
### `GET /getPinePollenRiskIdxV3`

- Endpoint: `https://apis.data.go.kr/1360000/HealthWthrIdxServiceV3/getPinePollenRiskIdxV3`
- Summary: 꽃가루농도위험지수(소나무)조회
- Description: 지점코드, 발표시간으로 현재일자로부터 3일 이내의 오늘, 내일, 모레, 글피의 예측값을 조회하는 기능(제공: 3월~6월)
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `numOfRows` | yes | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | yes | string | 페이지 번호 Default: 1 |
| `areaNo` | yes | string | 서울지점 공백일때: 전체지점조회 |
| `time` | yes | string | ‘21년7월6일 18시 발표 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `dataType` | no | string | 요청자료형식(XML/JSON) Default: XML |

Representative response fields:
- `header: header`
- `header.resultMsg: 응답메시지 내용`
- `header.resultCode: 응답메시지 코드`
- `body: body`
- `body.dataType: 응답자료형식`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.code: 지수코드`
- `body.items.item.areaNo: 지점코드`
- `body.items.item.date: 발표시간`
- `body.items.item.today: 오늘 예측값`
- `body.items.item.tomorrow: 내일 예측값`
- `body.items.item.dayaftertomorrow: 모레 예측값`
- `body.items.item.todaysaftertomorrow: 글피 예측값`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 번호`
- `body.totalCount: 데이터 총 개수`

### `GET /getWeedsPollenRiskndxV3`

- Endpoint: `https://apis.data.go.kr/1360000/HealthWthrIdxServiceV3/getWeedsPollenRiskndxV3`
- Summary: 꽃가루농도위험지수(잡초류)조회
- Description: 지점코드, 발표시간으로 현재일자로부터 3일 이내의 오늘, 내일, 모레, 글피의 예측값을 조회하는 기능(제공: 8월~10월)
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `numOfRows` | yes | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | yes | string | 페이지 번호 Default: 1 |
| `areaNo` | yes | string | 서울지점 공백일때: 전체지점조회 |
| `time` | yes | string | 21년 7월 6일 18시 발표 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `dataType` | no | string | 요청자료형식(XML/JSON) Default: XML |

Representative response fields:
- `header`
- `body`

### `GET /getOakPollenRiskIdxV3`

- Endpoint: `https://apis.data.go.kr/1360000/HealthWthrIdxServiceV3/getOakPollenRiskIdxV3`
- Summary: 꽃가루농도위험지수(참나무)조회
- Description: 지점코드, 발표시간으로 현재일자로부터 3일 이내의 오늘, 내일, 모레, 글피의 예측값을 조회하는 기능(제공: 3월~6월)
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `numOfRows` | yes | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | yes | string | 페이지 번호 Default: 1 |
| `areaNo` | yes | string | 서울지점 공백일때: 전체지점조회 |
| `time` | yes | string | ‘21년7월6일 18시 발표 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `dataType` | no | string | 요청자료형식(XML/JSON) Default: XML |

Representative response fields:
- `header: header`
- `header.resultCode: 응답메시지 코드`
- `header.resultMsg: 응답메시지 내용`
- `body: body`
- `body.dataType: 응답자료형식`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.code: 지수코드`
- `body.items.item.areaNo: 지점코드`
- `body.items.item.date: 발표시간`
- `body.items.item.today: 오늘 예측값`
- `body.items.item.tomorrow: 내일 예측값`
- `body.items.item.dayaftertomorrow: 모레 예측값`
- `body.items.item.todaysaftertomorrow: 글피 예측값`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 번호`
- `body.totalCount: 데이터 총 개수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
