# 기상청_영향예보_조회서비스 Update

- Source: <https://www.data.go.kr/data/15095149/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `보건의료`
- Category/provider: `보건의료` / `국가행정기관`
- Provider: `기상청`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- `(260515) 기상청_영향예보_조회서비스_오픈API활용가이드.zip`

## Adapter-Relevant Contract

- Swagger title: 기상청_영향예보_조회서비스
- Host: `apis.data.go.kr/1360000/ImpactInfoServiceV2`
- Schemes: `https, http`
### `GET /getHWImpactValueV2`

- Endpoint: `https://apis.data.go.kr/1360000/ImpactInfoServiceV2/getHWImpactValueV2`
- Summary: 폭염위험수준조회
- Description: 폭염 영향예보의 발표일자, 예보구역, 영향 분야, 영향도를 조회하는 기능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `tm` | yes | string | 조회일자 년월일(yyyymmdd) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `numOfRows` | no | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | no | string | 페이지 번호Default: 1 |
| `dataType` | no | string | 요청자료형식(XML/JSON)Default: XML |
| `regId` | no | string | 예보구역코드 *별첨 엑셀 자료 참조 |
| `efSn` | no | string | 예보일(1: 내일, 2:모레, 3:전체) |

Representative response fields:
- `numOfRows: 한 페이지당 표출 데이터 수`
- `pageNo: 페이지 수`
- `totalCount: 데이터 총 개수`
- `resultCode: 응답 메시지코드`
- `resultMsg: 응답 메시지 설명`
- `dataType: 응답자료형식 (XML/JSON)`
- `regId: 예보구역코드`
- `tmEf: 발표일자 년월일- 보건 분야 관심단계 이상 예상 시 전일 발표(일 1회, 11:30)`
- `regName: 예보구역명(한글)`
- `clsfc: 폭염 영향 분야 (보건(일반인), 보건(취약인), 산업, 축산업, 농업, 수산양식, 기타)`
- `value: 폭염 위험수준 (관심, 주의, 경고, 위험)`
- `efSn: 예보기준일(1: 내일, 2:모레)`

### `GET /getCWImpactValueV2`

- Endpoint: `https://apis.data.go.kr/1360000/ImpactInfoServiceV2/getCWImpactValueV2`
- Summary: 한파위험수준조회
- Description: 한파 영향예보의 발표일자, 예보구역, 영향 분야, 영향도를 조회하는 기능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `tm` | yes | string | 조회일자 년월일(yyyymmdd) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `numOfRows` | no | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | no | string | 페이지 번호Default: 1 |
| `dataType` | no | string | 요청자료형식(XML/JSON)Default: XML |
| `regId` | no | string | 예보구역코드 *별첨 엑셀 자료 참조 |
| `efSn` | no | string | 예보기준일(1: 내일, 2:모레, 3:전체) |

Representative response fields:
- `numOfRows: 한 페이지당 표출 데이터 수`
- `pageNo: 페이지 수`
- `totalCount: 데이터 총 개수`
- `resultCode: 응답 메시지코드`
- `resultMsg: 응답 메시지 설명`
- `dataType: 응답자료형식 (XML/JSON)`
- `regId: 예보구역코드`
- `tmEf: 발표일자 년월일- 보건 분야 관심단계 이상 예상 시 전일 발표(일 1회, 11:30)`
- `regName: 예보구역명(한글)`
- `clsfc: 한파 영향 분야 (보건, 산업, 시설물, 농축산업, 수산양식, 기타)`
- `value: 한파 위험수준 (관심, 주의, 경고, 위험)`
- `efSn: 예보기준일(1: 내일, 2:모레)`

### `GET /getHWCntrmsrMthdV2`

- Endpoint: `https://apis.data.go.kr/1360000/ImpactInfoServiceV2/getHWCntrmsrMthdV2`
- Summary: 폭염분야별대응기준조회
- Description: 폭염에 따른 영향 분야별 대응기준 및 대응 요령을 조회하는 기능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `clsfc` | yes | string | 폭염 영향 분야 (1.보건(일반인), 2.보건(취약인), 3.산업, 4.축산업, 5.농업, 6.수산양식, 7.기타) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `numOfRows` | no | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | no | string | 페이지 번호 Default: 1 |
| `dataType` | no | string | 요청자료형식(XML/JSON)Default: XML |

Representative response fields:
- `numOfRows: 한 페이지당 표출 데이터 수`
- `pageNo: 페이지 수`
- `totalCount: 데이터 총 개수`
- `resultCode: 응답 메시지코드`
- `resultMsg: 응답 메시지 설명`
- `dataType: 응답자료형식 (XML/JSON)`
- `clsfc: 폭염 영향 분야 (보건(일반인), 보건(취약인), 산업, 축산업, 농업, 수산양식, 기타 )`
- `value: 폭염 위험지수 (관심, 주의, 경고, 심각)`
- `cntrmsrCode: 대응요령 코드`
- `cntrmsrMthdShrt: 분야별 대응요령 단문`
- `cntrmsrMthd: 분야별 대응요령`

### `GET /getCWCntrmsrMthdV2`

- Endpoint: `https://apis.data.go.kr/1360000/ImpactInfoServiceV2/getCWCntrmsrMthdV2`
- Summary: 한파분야별대응기준조회
- Description: 한파에 따른 영향 분야별 대응기준 및 대응 요령을 조회하는 기능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 발급받은 인증키 |
| `clsfc` | yes | string | 한파 영향 분야 (1.보건, 2.산업, 3.시설물, 4.농축산업, 5.수산양식, 6.기타, 7.보건(취약인)) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `numOfRows` | no | string | 한 페이지 결과 수 Default: 10 |
| `pageNo` | no | string | 페이지 번호 Default: 1 |
| `dataType` | no | string | 요청자료형식(XML/JSON)Default: XML |

Representative response fields:
- `numOfRows: 한 페이지당 표출 데이터 수`
- `pageNo: 페이지 수`
- `totalCount: 데이터 총 개수`
- `resultCode: 응답 메시지코드`
- `resultMsg: 응답 메시지 설명`
- `dataType: 응답자료형식 (XML/JSON)`
- `clsfc: 한파 영향 분야 (보건, 산업, 시설물, 농축산업, 수산양식, 기타)`
- `value: 한파 위험지수 (관심, 주의, 경고, 심각)`
- `cntrmsrCode: 대응기준코드`
- `cntrmsrMthdShrt: 분야별 대응요령 단문`
- `cntrmsrMthd: 분야별 대응요령`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
