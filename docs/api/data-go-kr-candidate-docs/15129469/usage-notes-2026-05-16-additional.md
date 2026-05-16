# 조달청_누리장터 민간계약정보 서비스 Update

- Source: <https://www.data.go.kr/data/15129469/openapi.do>
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
- `조달청_OpenAPI참고자료_누리장터_민간계약정보서비스_1.0.docx`

## Adapter-Relevant Contract

- Swagger title: 조달청_누리장터 민간계약정보 서비스
- Host: `apis.data.go.kr/1230000/ao/PrvtCntrctInfoService`
- Schemes: `https, http`
### `GET /getPrvtCntrctInfoList`

- Endpoint: `https://apis.data.go.kr/1230000/ao/PrvtCntrctInfoService/getPrvtCntrctInfoList`
- Summary: 계약현황 민간조회
- Description: 검색조건을 등록일시, 통합계약번호로 하여 통합계약번호, 업무구분명, 확정계약번호, 계약참조번호, 계약명, 공동계약여부, 계약체결일자, 계약기간, 총계약금액 등의 누리장터시스템에 등록된 계약 정보 조회
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
| `type` | no | string | 타입 |
| `inqryBgnDt` | no | string | 조회시작일시 |
| `inqryEndDt` | no | string | 조회종료일시 |
| `untyCntrctNo` | no | string | 통합계약번호 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.chgDt: 변경일시`
- `body.items.item.untyCntrctNo: 통합계약번호`
- `body.items.item.bsnsDivNm: 업무구분명`
- `body.items.item.dcsnCntrctNo: 확정계약번호`
- `body.items.item.cntrctRefNo: 계약참조번호`
- `body.items.item.cntrctNm: 계약명`
- `body.items.item.cmmnCntrctYn: 공동계약여부`
- `body.items.item.cntrctCnclsDate: 계약체결일자`
- `body.items.item.cntrctPrd: 계약기간`
- `body.items.item.totCntrctAmt: 총계약금액`
- `body.items.item.thtmCntrctAmt: 금차계약금액`
- `body.items.item.grntymnyRate: 보증금률`
- `body.items.item.dfctGrntymnyRate: 하자보증금률`
- `body.items.item.cntrctInfoUrl: 계약정보URL`
- `body.items.item.payDivNm: 지급구분명`
- `body.items.item.cntrctInsttCd: 계약기관코드`
- `body.items.item.cntrctInsttNm: 계약기관명`
- `body.items.item.cntrctInsttChrgDeptNm: 계약담당부서명`
- `body.items.item.cntrctInsttOfclNm: 계약담당자명`
- `body.items.item.cntrctInsttOfclTelNo: 계약담당자전화번호`
- `body.items.item.cntrctInsttOfclFaxNo: 계약담당자팩스번호`
- `body.items.item.corpList: 업체목록`
- `body.items.item.cntrctDtlInfoUrl: 계약상세정보URL`
- `body.items.item.crdtrNm: 채권자명`

### `GET /getPrvtCntrctInfoListPPSSrch`

- Endpoint: `https://apis.data.go.kr/1230000/ao/PrvtCntrctInfoService/getPrvtCntrctInfoListPPSSrch`
- Summary: 나라장터 검색조건에 의한 계약현황 민간조회
- Description: 검색조건을 계약일자, 기관코드, 기관명, 계약번호, 공고번호로하여 통합계약번호, 업무구분명, 확정계약번호, 계약참조번호, 계약명, 공동계약여부, 계약체결일자, 계약기간, 총계약금액 등의 누리장터시스템에 등록된 계약 정보 조회
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
| `type` | no | string | 타입 |
| `inqryBgnDate` | no | string | 조회시작일자 |
| `inqryEndDate` | no | string | 조회종료일자 |
| `insttCd` | no | string | 기관코드 |
| `insttNm` | no | string | 기관명 |
| `ntceNo` | no | string | 공고번호 |
| `cntrctNm` | no | string | 계약명 |
| `cntrctRefNo` | no | string | 계약참조번호 |
| `cntrctNo` | no | string | 계약번호 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.cntrctRefNo: 계약참조번호`
- `body.items.item.untyCntrctNo: 통합계약번호`
- `body.items.item.bsnsDivNm: 업무구분명`
- `body.items.item.dcsnCntrctNo: 확정계약번호`
- `body.items.item.cmmnCntrctYn: 공동계약여부`
- `body.items.item.cntrctCnclsDate: 계약체결일자`
- `body.items.item.cntrctPrd: 계약기간`
- `body.items.item.totCntrctAmt: 총계약금액`
- `body.items.item.thtmCntrctAmt: 금차계약금액`
- `body.items.item.grntymnyRate: 보증금률`
- `body.items.item.dfctGrntymnyRate: 하자보증금률`
- `body.items.item.cntrctInfoUrl: 계약정보URL`
- `body.items.item.payDivNm: 지급구분명`
- `body.items.item.cntrctInsttCd: 계약기관코드`
- `body.items.item.cntrctInsttNm: 계약기관명`
- `body.items.item.cntrctInsttChrgDeptNm: 계약담당부서명`
- `body.items.item.cntrctInsttOfclNm: 계약담당자명`
- `body.items.item.cntrctInsttOfclTelNo: 계약담당자전화번호`
- `body.items.item.cntrctInsttOfclFaxNo: 계약담당자팩스번호`
- `body.items.item.corpList: 업체목록`
- `body.items.item.cntrctDtlInfoUrl: 계약상세정보URL`
- `body.items.item.crdtrNm: 채권자명`
- `body.items.item.cntrctCnclsMthdNm: 계약체결방법명`
- `body.items.item.rgstDt: 등록일시`

### `GET /getPrvtCntrctInfoListChgHstry`

- Endpoint: `https://apis.data.go.kr/1230000/ao/PrvtCntrctInfoService/getPrvtCntrctInfoListChgHstry`
- Summary: 계약현황에 대한 민간변경이력조회
- Description: 검색조건을 변경일시, 통합계약번호로 하여 통합계약번호, 업무구분명, 확정계약번호, 계약참조번호, 계약명, 공동계약여부, 계약체결일자, 계약기간, 총계약금액 등의 누리장터시스템에 등록된 계약변경정보 조회
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
| `type` | no | string | 타입 |
| `inqryBgnDt` | no | string | 조회시작일시 |
| `inqryEndDt` | no | string | 조회종료일시 |
| `untyCntrctNo` | no | string | 통합계약번호 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.cntrctRefNo: 계약참조번호`
- `body.items.item.untyCntrctNo: 통합계약번호`
- `body.items.item.bsnsDivNm: 업무구분명`
- `body.items.item.dcsnCntrctNo: 확정계약번호`
- `body.items.item.cmmnCntrctYn: 공동계약여부`
- `body.items.item.cntrctCnclsDate: 계약체결일자`
- `body.items.item.cntrctPrd: 계약기간`
- `body.items.item.totCntrctAmt: 총계약금액`
- `body.items.item.thtmCntrctAmt: 금차계약금액`
- `body.items.item.grntymnyRate: 보증금률`
- `body.items.item.dfctGrntymnyRate: 하자보증금률`
- `body.items.item.cntrctInfoUrl: 계약정보URL`
- `body.items.item.payDivNm: 지급구분명`
- `body.items.item.cntrctInsttCd: 계약기관코드`
- `body.items.item.cntrctInsttNm: 계약기관명`
- `body.items.item.cntrctInsttChrgDeptNm: 계약담당부서명`
- `body.items.item.cntrctInsttOfclNm: 계약담당자명`
- `body.items.item.cntrctInsttOfclTelNo: 계약담당자전화번호`
- `body.items.item.cntrctInsttOfclFaxNo: 계약담당자팩스번호`
- `body.items.item.corpList: 업체목록`
- `body.items.item.cntrctDtlInfoUrl: 계약상세정보URL`
- `body.items.item.crdtrNm: 채권자명`
- `body.items.item.cntrctCnclsMthdNm: 계약체결방법명`
- `body.items.item.rgstDt: 등록일시`

### `GET /getPrvtCntrctInfoListDltHstry`

- Endpoint: `https://apis.data.go.kr/1230000/ao/PrvtCntrctInfoService/getPrvtCntrctInfoListDltHstry`
- Summary: 계약현황에 대한 민간삭제이력조회
- Description: 검색조건에 삭제일시, 통합계약번호를 입력하여 민간 계약삭제이력정보(삭제일시, 변경구분명, 통합계약번호, 확정계약번호, 계약참조번호) 조회
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
| `type` | no | string | 타입 |
| `inqryBgnDt` | no | string | 조회시작일시 |
| `inqryEndDt` | no | string | 조회종료일시 |
| `untyCntrctNo` | no | string | 통합계약번호 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.cntrctRefNo: 계약참조번호`
- `body.items.item.dltDt: 삭제일시`
- `body.items.item.chgDivNm: 변경구분명`
- `body.items.item.untyCntrctNo: 통합계약번호`
- `body.items.item.dcsnCntrctNo: 확정계약번호`
- `body.totalCount: 전체 결과 수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지번호`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
