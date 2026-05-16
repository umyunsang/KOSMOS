# 조달청_나라장터 계약과정통합공개서비스 Update

- Source: <https://www.data.go.kr/data/15129459/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `공공행정`
- Category/provider: `공공행정` / `국가행정기관`
- Provider: `조달청`
- UMMAYA primitive candidate: `find`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- `조달청_OpenAPI참고자료_나라장터_계약과정통합공개서비스_1.0.docx`

## Adapter-Relevant Contract

- Swagger title: 조달청_나라장터 계약과정통합공개서비스
- Host: `apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService`
- Schemes: `https, http`
### `GET /getCntrctProcssIntgOpenFrgcpt`

- Endpoint: `https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenFrgcpt`
- Summary: 계약과정통합공개정보에 대한 외자조회
- Description: 사용자가 [입찰공고번호,사전규격등록번호,발주계획번호,조달요청번호] 중 한 번호를 알고 있는 경우 해당 외자입찰공고의 업무 진행과정(발주계획번호,사업명,발주기관명,사전규격등록번호,입찰공고명,낙찰업체명,낙찰금액,낙찰률,계약번호,계약건명 등)을 조회 단, 입찰공고번호는 입찰공고차수를 입력하지 않아도 관련 공고 정보조회 가능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `inqryDiv` | yes | string | 조회구분 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `bidNtceNo` | no | string | 입찰공고번호 |
| `bidNtceOrd` | no | string | 입찰공고차수 |
| `bfSpecRgstNo` | no | string | 사전규격등록번호 |
| `orderPlanNo` | no | string | 발주계획번호 |
| `prcrmntReqNo` | no | string | 조달요청번호 |
| `type` | no | string | 타입 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.orderBizNm: 발주사업명`
- `body.items.item.orderPlanNo: 발주계획번호`
- `body.items.item.orderPlanUntyNo: 발주계획통합번호`
- `body.items.item.orderInsttNm: 발주기관명`
- `body.items.item.orderYm: 발주년월`
- `body.items.item.prcrmntMethdNm: 조달방식명`
- `body.items.item.cntrctCnclsMthdNm: 계약체결방법명`
- `body.items.item.bfSpecRgstNo: 사전규격등록번호`
- `body.items.item.bfSpecBizNm: 사전규격사업명`
- `body.items.item.bfSpecDminsttNm: 사전규격수요기관명`
- `body.items.item.bfSpecNtceInsttNm: 사전규격공고기관명`
- `body.items.item.opninRgstClseDt: 의견등록마감일시`
- `body.items.item.bidNtceNo: 입찰공고번호`
- `body.items.item.bidNtceOrd: 입찰공고차수`
- `body.items.item.prcrmntReqNo: 조달요청번호`
- `body.items.item.bidNtceNm: 입찰공고명`
- `body.items.item.bidDminsttNm: 입찰수요기관명`
- `body.items.item.bidMthdNm: 입찰방법명`
- `body.items.item.bidNtceDt: 입찰공고일시`
- `body.items.item.bidwinrInfoList: 낙찰자정보목록`
- `body.items.item.cntrctInfoList: 계약정보목록`
- `body.totalCount: 전체 결과 수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지번호`

### `GET /getCntrctProcssIntgOpenThng`

- Endpoint: `https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenThng`
- Summary: 계약과정통합공개정보에 대한 물품조회
- Description: 사용자가 [입찰공고번호,사전규격등록번호,발주계획번호,조달요청번호] 중 한 번호를 알고 있는 경우 해당 물품입찰공고의 업무 진행과정(발주계획번호,사업명,발주기관명,사전규격등록번호,입찰공고명,낙찰업체명,낙찰금액,낙찰률,계약번호,계약건명 등)을 조회 단, 입찰공고번호는 입찰공고차수를 입력하지 않아도 관련 공고 정보조회 가능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `inqryDiv` | yes | string | 조회구분 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `bidNtceNo` | no | string | 입찰공고번호 |
| `bidNtceOrd` | no | string | 입찰공고차수 |
| `bfSpecRgstNo` | no | string | 사전규격등록번호 |
| `orderPlanNo` | no | string | 발주계획번호 |
| `prcrmntReqNo` | no | string | 조달요청번호 |
| `type` | no | string | 타입 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.orderBizNm: 발주사업명`
- `body.items.item.orderPlanNo: 발주계획번호`
- `body.items.item.orderPlanUntyNo: 발주계획통합번호`
- `body.items.item.orderInsttNm: 발주기관명`
- `body.items.item.orderYm: 발주년월`
- `body.items.item.prcrmntMethdNm: 조달방식명`
- `body.items.item.cntrctCnclsMthdNm: 계약체결방법명`
- `body.items.item.bfSpecRgstNo: 사전규격등록번호`
- `body.items.item.bfSpecBizNm: 사전규격사업명`
- `body.items.item.bfSpecDminsttNm: 사전규격수요기관명`
- `body.items.item.bfSpecNtceInsttNm: 사전규격공고기관명`
- `body.items.item.opninRgstClseDt: 의견등록마감일시`
- `body.items.item.bidNtceNo: 입찰공고번호`
- `body.items.item.bidNtceOrd: 입찰공고차수`
- `body.items.item.prcrmntReqNo: 조달요청번호`
- `body.items.item.bidNtceNm: 입찰공고명`
- `body.items.item.bidDminsttNm: 입찰수요기관명`
- `body.items.item.bidMthdNm: 입찰방법명`
- `body.items.item.bidNtceDt: 입찰공고일시`
- `body.items.item.bidwinrInfoList: 낙찰자정보목록`
- `body.items.item.cntrctInfoList: 계약정보목록`
- `body.totalCount: 전체 결과 수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지번호`

### `GET /getCntrctProcssIntgOpenServc`

- Endpoint: `https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenServc`
- Summary: 계약과정통합공개정보에 대한 용역조회
- Description: 사용자가 [입찰공고번호,사전규격등록번호,발주계획번호,조달요청번호] 중 한 번호를 알고 있는 경우 해당 용역입찰공고의 업무 진행과정(발주계획번호,사업명,발주기관명,사전규격등록번호,입찰공고명,낙찰업체명,낙찰금액,낙찰률,계약번호,계약건명 등)을 조회 단, 입찰공고번호는 입찰공고차수를 입력하지 않아도 관련 공고 정보조회 가능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `inqryDiv` | yes | string | 조회구분 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `bidNtceNo` | no | string | 입찰공고번호 |
| `bidNtceOrd` | no | string | 입찰공고차수 |
| `bfSpecRgstNo` | no | string | 사전규격등록번호 |
| `orderPlanNo` | no | string | 발주계획번호 |
| `prcrmntReqNo` | no | string | 조달요청번호 |
| `type` | no | string | 타입 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.orderBizNm: 발주사업명`
- `body.items.item.orderPlanNo: 발주계획번호`
- `body.items.item.orderPlanUntyNo: 발주계획통합번호`
- `body.items.item.orderInsttNm: 발주기관명`
- `body.items.item.orderYm: 발주년월`
- `body.items.item.prcrmntMethdNm: 조달방식명`
- `body.items.item.cntrctCnclsMthdNm: 계약체결방법명`
- `body.items.item.bfSpecRgstNo: 사전규격등록번호`
- `body.items.item.bfSpecBizNm: 사전규격사업명`
- `body.items.item.bfSpecDminsttNm: 사전규격수요기관명`
- `body.items.item.bfSpecNtceInsttNm: 사전규격공고기관명`
- `body.items.item.opninRgstClseDt: 의견등록마감일시`
- `body.items.item.bidNtceNo: 입찰공고번호`
- `body.items.item.bidNtceOrd: 입찰공고차수`
- `body.items.item.prcrmntReqNo: 조달요청번호`
- `body.items.item.bidNtceNm: 입찰공고명`
- `body.items.item.bidDminsttNm: 입찰수요기관명`
- `body.items.item.bidMthdNm: 입찰방법명`
- `body.items.item.bidNtceDt: 입찰공고일시`
- `body.items.item.bidwinrInfoList: 낙찰자정보목록`
- `body.items.item.cntrctInfoList: 계약정보목록`
- `body.totalCount: 전체 결과 수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지번호`

### `GET /getCntrctProcssIntgOpenCnstwk`

- Endpoint: `https://apis.data.go.kr/1230000/ao/CntrctProcssIntgOpenService/getCntrctProcssIntgOpenCnstwk`
- Summary: 계약과정통합공개정보에 대한 공사조회
- Description: 사용자가 [입찰공고번호,사전규격등록번호,발주계획번호,조달요청번호] 중 한 번호를 알고 있는 경우 해당 공사입찰공고 업무 진행과정(발주계획번호,사업명,발주기관명,사전규격등록번호,입찰공고명,낙찰업체명,낙찰금액,낙찰률,계약번호,계약건명 등)을 조회 단, 입찰공고번호는 입찰공고차수를 입력하지 않아도 관련 공고 정보조회 가능
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `pageNo` | yes | string | 페이지번호 |
| `numOfRows` | yes | string | 한 페이지 결과 수 |
| `inqryDiv` | yes | string | 조회구분 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `bidNtceNo` | no | string | 입찰공고번호 |
| `bidNtceOrd` | no | string | 입찰공고차수 |
| `bfSpecRgstNo` | no | string | 사전규격등록번호 |
| `orderPlanNo` | no | string | 발주계획번호 |
| `prcrmntReqNo` | no | string | 조달요청번호 |
| `type` | no | string | 타입 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.orderBizNm: 발주사업명`
- `body.items.item.orderPlanNo: 발주계획번호`
- `body.items.item.orderPlanUntyNo: 발주계획통합번호`
- `body.items.item.orderInsttNm: 발주기관명`
- `body.items.item.orderYm: 발주년월`
- `body.items.item.prcrmntMethdNm: 조달방식명`
- `body.items.item.cntrctCnclsMthdNm: 계약체결방법명`
- `body.items.item.bfSpecRgstNo: 사전규격등록번호`
- `body.items.item.bfSpecBizNm: 사전규격사업명`
- `body.items.item.bfSpecDminsttNm: 사전규격수요기관명`
- `body.items.item.bfSpecNtceInsttNm: 사전규격공고기관명`
- `body.items.item.opninRgstClseDt: 의견등록마감일시`
- `body.items.item.bidNtceNo: 입찰공고번호`
- `body.items.item.bidNtceOrd: 입찰공고차수`
- `body.items.item.prcrmntReqNo: 조달요청번호`
- `body.items.item.bidNtceNm: 입찰공고명`
- `body.items.item.bidDminsttNm: 입찰수요기관명`
- `body.items.item.bidMthdNm: 입찰방법명`
- `body.items.item.bidNtceDt: 입찰공고일시`
- `body.items.item.bidwinrInfoList: 낙찰자정보목록`
- `body.items.item.cntrctInfoList: 계약정보목록`
- `body.totalCount: 전체 결과 수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지번호`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
