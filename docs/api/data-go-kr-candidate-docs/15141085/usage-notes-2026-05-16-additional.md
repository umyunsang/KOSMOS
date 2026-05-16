# 헌법재판소_판례정보 조회 서비스

- Source: <https://www.data.go.kr/data/15141085/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `법률`
- Category/provider: `` / ``
- Provider: ``
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `data-go-kr-inline-swagger.json`
- No downloadable reference document found or the portal exposed only a blank/error download link; saved detail HTML and Swagger instead.

## Adapter-Relevant Contract

- Swagger title: 헌법재판소_판례정보 조회 서비스
- Host: `apis.data.go.kr/9750000/PrecedentInfomationService`
- Schemes: `https, http`
### `GET /getOcprPrcdntList`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getOcprPrcdntList`
- Summary: 공보수록 판례 조회
- Description: 공보,선고년월을 입력하여 공보에 수록된 판례를 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |
| `title` | no | string | 공보(호수) |
| `adjudgeYm` | no | string | 선고년월 (yyyyMM) |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.atchFilePath2: 판례파일 다운로드 링크 주소`
- `body.items.item.title: 공보(호수)`
- `body.items.item.exeCnt: 판례목록 리스트 개수`
- `body.items.item.adjudgeYm: 선고년월(yyyyMM)`
- `body.items.item.atchFileNm1: 공보파일명`
- `body.items.item.atchFilePath1: 공보파일 다운로드 링크 주소`
- `body.items.item.atchFileNm2: 판례파일명`

### `GET /getRealmMainPrcdntList`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getRealmMainPrcdntList`
- Summary: 분야별 주요판례 목록 조회
- Description: 분류,사건명,결정문을 입력하여 분야별주요판례 목록을 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `code` | yes | string | 분류(0 : 전체 1: 정치·선거관계에 관한 결정, 3: 언론 등 정신적 자유에 관한 결정, 4: 경제·재산권·조세관계에 관한 결정, 5: 가족·노동 등 사회관계에 관한 결정, 6: 절차적 기본권 및 형사관계에 관한 결정, 7: 헌법위원회 및 대법원 헌법판례) |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |
| `eventNm` | no | string | 사건명(별칭)에서 찾을 단어를 검색어로 입력 |
| `decisionNm` | no | string | 결정문에서 찾을 단어를 검색어로 입력 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.chgDate: 수정일`
- `body.items.item.seq: 일련번호`
- `body.items.item.nick: 별칭`
- `body.items.item.title: 사건명`
- `body.items.item.eventNo: 사건번호`
- `body.items.item.classNm: 클래스명`
- `body.items.item.adjudgeDt: 종국일자`
- `body.items.item.regDate: 등록일`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getRealmMainPrcdntDetail`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getRealmMainPrcdntDetail`
- Summary: 분야별 주요판례 상세 조회
- Description: 일련번호를 입력하여 분야별주요판례상세내용을 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `seq` | yes | string | 게시물 번호 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.chgDate: 수정일`
- `body.items.item.eventNo: 사건번호`
- `body.items.item.eventNm: 사건명`
- `body.items.item.nick: 별칭`
- `body.items.item.codeName: 분류코드명`
- `body.items.item.adjudgeDt: 종국일자`
- `body.items.item.adjudgeResult: 종국결과`
- `body.items.item.exeBook: 판례집`
- `body.items.item.atchNm: 결정문 파일명`
- `body.items.item.atchFilePath: 결정문 파일링크`
- `body.items.item.content: 결정문 내용`
- `body.items.item.regDate: 등록일`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getKorPrcdntList`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getKorPrcdntList`
- Summary: 한글판례 목록 조회
- Description: 판례유형 및 사건정보,종국결과,종국일자등을 입력하여 한글 판례검색 목록을 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |
| `panreType` | no | string | 01: 결정문, 02: 공보, 03: 판례집 |
| `eventNo` | no | string | 사건번호(절대적으로 일치해야함) |
| `eventNm` | no | string | 사건명(사건번호와 달리 일부분만 입력 가능) |
| `eventType` | no | string | 사건유형(전체, 헌가,헌나,헌다,헌라,헌마,헌바,헌사,헌아) |
| `jgdmtCort` | no | string | 재판부(전체, 전원재판부, 지정재판부) |
| `rstaResult` | no | string | 종국결과(전체, 위헌, 헌법불합치, 한정위헌, 한정합헌, 인용, 합헌, 기각, 각하, 취하, 선정, 기타) |
| `rstaStartDate` | no | string | 종국일자 검색 시작일 → yyyyMMdd 형식 |
| `rstaEndDate` | no | string | 종국일자 검색 종료일 → yyyyMMdd 형식 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.rstaDate: 종국일자`
- `body.items.item.eventNum: 사건일련번호`
- `body.items.item.eventNo: 사건번호`
- `body.items.item.eventNm: 사건명`
- `body.items.item.panreType: 판례유형`
- `body.items.item.eventType: 사건유형`
- `body.items.item.jgdmtCort: 재판부`
- `body.items.item.rstaRsta: 종국결과`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getKorPrcdntDetail`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getKorPrcdntDetail`
- Summary: 한글판례 상세 조회
- Description: 판례일련번호로 판례상세내용을 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `eventNum` | yes | string | 한글판례 검색 목록 조회에서 얻은 사건일련번호(eventNum)를 통해 상세 검색 |
| `panreType` | yes | string | 01 : 결정문, 02 : 공보, 03 : 판례집 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.eventType: 사건유형`
- `body.items.item.eventNum: 판례일련번호`
- `body.items.item.panreType: 판례유형`
- `body.items.item.eventNo: 사건번호`
- `body.items.item.eventNm: 사건명`
- `body.items.item.panreTitle: 판례제목`
- `body.items.item.panreInfo: 판례정보`
- `body.items.item.pansiMatt: 판시사항`
- `body.items.item.decisionGst: 결정요지`
- `body.items.item.adjobtTxt: 심판대상조문`
- `body.items.item.refrnPrvsn: 참조조문`
- `body.items.item.refrnPrcdnt: 참조판례`
- `body.items.item.event: 사건/당사자`
- `body.items.item.eventCol1: 제청법원/청구인/신청인`
- `body.items.item.eventCol2: 제청신청인/피청구인`
- `body.items.item.eventCol3: 당해사건/보조참가인/보안사건/재심대상결정`
- `body.items.item.eventCol4: 선고일/결정일`
- `body.items.item.textOfDecision: 주문`
- `body.items.item.reason: 이유`
- `body.items.item.volumeInfo: 권`
- `body.items.item.seriesInfo: 집`

### `GET /getEngPrcdntList`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getEngPrcdntList`
- Summary: 영문판례 목록 조회
- Description: 사건명,사건유형,종국결과를 입력하여 영문 판례검색 목록을 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |
| `eventNo` | no | string | 사건번호(영문 / 절대적으로 일치해야함) |
| `eventNm` | no | string | 사건명(영문/ 사건번호와 달리 일부분만 입력 가능) |
| `eventType` | no | string | 사건유형(영문 / All, Hun-Ka, Hun-Na, Hun-Da, Hun-Ra, Hun-Ma, |
| `rstaResult` | no | string | 종국결과(영문 / All, unconstitutional, nonconforming to the Constitution, conditionally unconstitutional, conditionally constitutional, upheld, constitutional, rejected, dismissed, withdrawn, others)) |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.rstaDate: 종국일자(영문)`
- `body.items.item.eventNum: 사건일련번호`
- `body.items.item.eventNo: 사건번호(한글)`
- `body.items.item.eventNm: 사건명(한글)`
- `body.items.item.engEventNo: 영문사건번호`
- `body.items.item.engEventName: 영문사건명`
- `body.items.item.rstaRsta: 종국결과(영문)`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getEngPrcdntDetail`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getEngPrcdntDetail`
- Summary: 영문판례 상세 조회
- Description: 판례일련번호를 입력하여 영문 판례검색 상세내용을 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `eventNum` | yes | string | 판례 검색 상세 조회를 위한 사건 일련번호 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |

Representative response fields:
- `header: header`
- `header.resultCode: 결과코드`
- `header.resultMsg: 결과메세지`
- `body: body`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.xmlContent: xml내용`
- `body.items.item.eventNum: 판례일련번호`
- `body.items.item.eventNo: 사건번호`
- `body.items.item.eventNm: 사건명`
- `body.items.item.engEventNo: 영문사건번호`
- `body.items.item.engEventName: 영문사건명`
- `body.items.item.volumeInfo: 권`
- `body.items.item.seriesInfo: 집(시리즈)`
- `body.items.item.pages: 쪽`
- `body.items.item.eventCtgry: 카테고리`
- `body.items.item.jgdmtCort: 재판부`
- `body.items.item.rstaRsta: 종국결과`
- `body.items.item.rstaDate: 종국일자`
- `body.items.item.eventType: 사건유형`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`
- `body.pageNo: 페이지 번호`

### `GET /getOcprOutlineList`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getOcprOutlineList`
- Summary: 판례요지집 목록 조회
- Description: 판례요지내용,사건번호,판례요지제목을 입력하여 판례요지집 검색 목록 정보를 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |
| `content` | no | string | 판례요지내용에서 검색 |
| `eventNo` | no | string | 판례요지에 연관된 사건번호 검색 |
| `title` | no | string | 판례요지 제목에서 검색 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.chgDate: 수정일`
- `body.items.item.seqNo: 판례요지번호`
- `body.items.item.title: 판례요지제목`
- `body.items.item.cntntpth: 판례경로`
- `body.items.item.regDate: 등록일`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`

### `GET /getOcprOutlineDetail`

- Endpoint: `https://apis.data.go.kr/9750000/PrecedentInfomationService/getOcprOutlineDetail`
- Summary: 판례요지집 상세 조회
- Description: 판례요지번호를 입력하여 판례요지집 검색 상세 정보를 조회하는 기능 제공
- Produces: `application/json, application/xml`

Required params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `serviceKey` | yes | string | 공공데이터포털에서 받은 인증키 |
| `seqNo` | yes | string | 판례요지집 검색 목록에서 조회된 판례요지번호를 입력 |

Optional params:
| Param | Required | Type | Meaning |
|---|---:|---|---|
| `pageNo` | no | string | 페이지번호 |
| `numOfRows` | no | string | 한 페이지 결과 수 |
| `type` | no | string | 응답결과 출력형식(xml,json) 기본값:xml |
| `fields` | no | string | 응답에 노출할 필드명 콤마(,)로 구분해서 입력, 기본 : 모든필드 출력 |

Representative response fields:
- `header: header`
- `header.resultMsg: 결과메세지`
- `header.resultCode: 결과코드`
- `body: body`
- `body.pageNo: 페이지 번호`
- `body.type: 데이터 타입`
- `body.items: items`
- `body.items.item: item`
- `body.items.item.chgDate: 수정일`
- `body.items.item.seqNo: 판례요지번호`
- `body.items.item.title: 제목`
- `body.items.item.content: 내용`
- `body.items.item.cntntpth: 판례경로`
- `body.items.item.eventNo: 연관사건번호`
- `body.items.item.regDate: 등록일`
- `body.totalCount: 전체 결과수`
- `body.numOfRows: 한 페이지 결과 수`
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
