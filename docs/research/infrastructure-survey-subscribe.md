# Infrastructure Survey: subscribe primitive

> Scope. KOSMOS `subscribe` 프리미티브의 실제 카운터파트를 이루는 한국 국가인프라 이벤트/알림 채널을 공개 문서만으로 역공학한 외부 계약(event payload schema · delivery protocol · auth · rate · 토픽/채널 구조) 정찰 보고서.
> Primary audience. `src/kosmos/tools/mock/` 아래 `subscribe` 관련 mock adapter 저자. drop-in replaceability 원칙(AGENTS.md — "shape-compatible mock") 준수를 위해 본 문서의 필드/엔드포인트/enum/코드 번호는 실서버 계약을 **바이트 수준**에서 미러해야 한다.
> 집필 기준. 모든 사실은 공개 출처(공공데이터포털, 기관 개발자 가이드, 국가법령정보, TTA/3GPP 표준, 학술 논문, 공개 블로그 게시물, 위키 백과)만 사용. 확인되지 않은 항목은 "⚠️ OPAQUE — requires institutional disclosure"로 표기. 본 보고서는 관찰자 시점 외부 표면 계약만 기록하며, 내부 구현(큐, DB, AMQP 토폴로지 등)은 다루지 않는다.

---

## Executive summary

`subscribe` 원시의 한국 카운터파트는 크게 **세 층위**로 분해된다. 어느 한 층위가 단일 "토픽 버스"를 제공하지 않는다는 점이 한국 공공 이벤트 생태계의 핵심 특성이다.

1. **Cell Broadcast Service (CBS) 직접 수신 계층.** 단말(UE)이 LTE SIB12/NR SystemInformation으로 수신하는 위급/긴급/안전안내/실종경보 문자. 3GPP TS 23.041 기반, KPAS(Korean Public Alert System)로 구현. 이 계층의 "구독"은 기지국 지역 기반 수동 수신이며 backend API 면은 존재하지 않는다. Mock 대상에서 제외 — 단, payload **사후 공개 채널**(2번)을 통해 동일한 정보가 pull-able JSON으로 재노출된다.
2. **공공 풀(Pull)-기반 알림 API 계층.** 재난문자, 기상특보, 지진통보, 대기오염 예보·경보, 돌발교통, 감염병 발생, DART 공시, 법령 개정이력 등 대부분 REST+JSON/XML 오퍼레이션으로 노출. 사실상 모든 채널이 `serviceKey`(data.go.kr) 또는 `OC`(law.go.kr) 또는 `crtfc_key`(opendart) 쿼리 파라미터 인증 + 폴링 모델. Webhook/SSE/WebSocket은 **거의 부재**. delivery guarantee는 "at-least-once on poll"에 가깝다.
3. **RSS/ATOM 계층.** 식약처 `mfds.go.kr/www/rss`, 서울 열린데이터광장 `data.seoul.go.kr/rss`, OPEN DART 알림마당(RSS). RSS 2.0 XML 피드. 구독 형태(feed reader poll)이지만 서버측 사용자 상태는 없음.

**Drop-in mirrorability 종합.** 평균 4/5 — 대부분 REST+JSON 고정 스키마라서 mock server에서 엔드포인트·필드·enum을 그대로 재현하기 쉽다. 주요 위험 요소는 (a) CBS 계층(단말-OS 경계, mock 불가 → 풀 채널로 우회), (b) 공공데이터포털 신/구 시스템 혼재 — 2023년 이후 `safetydata.go.kr` V2가 기존 `data.go.kr` API를 대체(비대칭 필드명), (c) `serviceKey`의 대문자 'K' 처럼 국지적 API quirk이다.

**Mock 전략 제안.** harness는 `subscribe(channel, filters)` 엔벨로프를 유지하되, adapter 내부는 해당 실제 API의 poll URL을 5–60초 간격으로 long-poll 하는 방식으로 구현한다. 이벤트 전송 보증은 실서버가 at-most-once(증가 번호 중복 허용)이므로 mock은 `(sn, regDt, stnId)` 3튜플 기반 중복 제거로 시뮬레이션한다. 아래 각 시스템의 deep-dive가 mock payload fixture 작성의 근거가 된다.

---

## Protocol taxonomy

| 분류 | 대상 시스템 | 특징 |
|---|---|---|
| Cell Broadcast Service (CBS) | 위급/긴급/안전안내/실종경보 재난문자 (KPAS) | 3GPP TS 23.041 기반. Message Identifier 4370–4385. 단말 직수신. backend API 없음. |
| REST Pull (data.go.kr gateway) | 재난문자 (15134001), 기상특보(15139476), 지진정보(15000420), 에어코리아(15073861), 한국도로공사 문자(15076693), ITS 돌발(15040465), KPX 전력수급(15056640), KDCA 감염병(15139178) | `http://apis.data.go.kr/{prefix}/{ServiceName}/{operation}` · URL 파라미터 `serviceKey`. JSON+XML 동시 지원. |
| REST Pull (safetydata.go.kr V2) | 긴급재난문자 신 API (`/V2/api/DSSP-IF-*`) | 2023+ 데이터만. `serviceKey`(K 대문자 필수), `returnType=json`. |
| REST Pull (기관 직접) | OPEN DART (`opendart.fss.or.kr/api/list.json`), 국가법령정보 (`law.go.kr/DRF/lawSearch.do`), 기상청 API 허브 (`apihub.kma.go.kr`), KPX OpenAPI (`openapi.kpx.or.kr`) | 기관 자체 gateway. 인증키 이름 상이: `crtfc_key`, `OC`, `authKey`. |
| RSS 2.0 feed | 식약처 (mfds.go.kr), 서울 열린데이터광장 (data.seoul.go.kr/rss), OPEN DART 알림마당 | XML 피드, 무인증, 클라이언트 폴링. |
| Webhook / SSE / WebSocket | (없음) | 조사 대상 13개 기관 중 공개 webhook/SSE/WS 엔드포인트 확인 실패. ⚠️ OPAQUE — 일부 민간 파트너용 채널 존재 가능성 있음. |

---

## Systems catalog

| # | 영역 | 시스템 | 프로토콜 | 인증 | 업데이트 | Mirrorability |
|---|---|---|---|---|---|---|
| 1 | 재난경보 | 긴급재난문자 CBS (KPAS) | 3GPP CBS (SIB12) | 무(단말 수신) | 실시간 | 2/5 (OS 계층) |
| 2 | 재난경보 (공개 API) | 행정안전부 긴급재난문자 V2 API | REST/JSON | `serviceKey` | 실시간 pull | 5/5 |
| 3 | 통합재난 | 국민재난안전포털 safekorea.go.kr | 웹+모바일, 안전디딤돌 FCM | FCM token | 실시간 push | 3/5 (OS push) |
| 4 | 기상특보 | 기상청 특보 조회서비스 | REST/JSON+XML | `ServiceKey` | 실시간 | 5/5 |
| 5 | 지진/쓰나미 | 기상청 지진정보 조회서비스 | REST/JSON+XML | `ServiceKey` | 실시간 | 5/5 |
| 6 | 대기오염 | 에어코리아 대기오염정보 API | REST/JSON+XML | `serviceKey` | 실시간 | 5/5 |
| 7 | 교통통제 (고속도로) | 한국도로공사 실시간 문자정보 | REST/JSON+XML | data.ex.co.kr API key | 실시간 | 4/5 |
| 8 | 교통돌발 | ITS 국가교통정보센터 돌발상황 | REST/JSON+XML | `apiKey` | 실시간 | 5/5 |
| 9 | 지자체 | 서울 열린데이터광장 RSS | RSS 2.0 | 무 | 불명 | 5/5 |
| 10 | 식품·약품 | 식약처 RSS | RSS 2.0 | 무 | 실시간 | 5/5 |
| 11 | 금융공시 | OPEN DART 공시검색 | REST/JSON+XML | `crtfc_key` | 실시간 (공시접수 기준) | 5/5 |
| 12 | 전력 | KPX 현재전력수급현황 OpenAPI | REST | `serviceKey` | 5분 단위 | 5/5 |
| 13 | 수도 | K-water opendata portal | 파일+REST | 인증키 | 10분/시간 | 3/5 |
| 14 | 보건 | KDCA 전수신고 감염병 발생현황 | REST/JSON+XML | `serviceKey` | 실시간 | 4/5 |
| 15 | 법령 | 국가법령정보 OPEN API 법령변경이력 | REST/XML+JSON | `OC` | 실시간 (공포 기준) | 5/5 |
| 16 | 공공데이터 메타 | data.go.kr 활용신청 SMS/이메일 알림 | (내부) | 운영자 발송 | 수동 | 1/5 |

---

## Per-system deep dives

### 1. 긴급재난문자 CBS (KPAS — Korean Public Alert System)

- **Event delivery protocol.** 3GPP TS 23.041 기반 Cell Broadcast Service. CBC(Cell Broadcast Centre) → MME → eNodeB → UE. SIB12(LTE)/SystemInformationBlockType12(NR) 페이징 채널로 송출. IP 통신 미사용. 단말이 Warning Message Content IE를 그대로 파싱해 OS 레벨에서 사용자에게 표시한다. 백엔드 API 면 미존재.
- **Subscription setup.** 없음. 단말이 위치한 기지국 CBA(Cell Broadcast Area) 기반 수신. 사용자 제어는 OS 설정(수신 거부 토글)만 존재. 지자체가 원하는 송출 영역을 CBC에 좌표·행정코드로 지정.
- **Event payload schema.** 3GPP TS 23.041 CBS Message 고정 구조. 핵심 필드:
  - `Serial Number` (2 octets): Geographical scope (2 bits) + Message Code (10 bits) + Update Number (4 bits). 같은 메시지의 재방송 구분.
  - `Message Identifier` (2 octets): 4352–6399 warning 대역. 한국 할당 — **4370 위급재난문자, 4371 긴급재난문자, 4372 안전안내문자, 4379 실종경보문자**, 그리고 한국어 외 언어용 보조 채널 **4383 위급, 4384 긴급, 4385 안전안내**.
  - `Data Coding Scheme` (1 octet): UCS-2(0x48) 한글용, GSM 7-bit 대체 허용.
  - `Page Parameter` (1 octet): 총 페이지 중 현재 페이지.
  - `Content of Message` (최대 82 octet/page × N page): 메시지 본문. KPAS는 관행상 위급 60바이트, 긴급 90바이트, 안전안내·실종경보 2000바이트(멀티페이지)로 운용.
- **Event types / categories.** 4단계 등급:
  - 위급재난문자 (Critical, 60+ dB 알림음, 수신 거부 불가, 진동 고정).
  - 긴급재난문자 (Urgent, 40+ dB, 수신 거부 가능).
  - 안전안내문자 (Safety, 사용자 설정 알림음, 수신 거부 가능).
  - 실종경보문자 (Missing Person, 2026년 2월부터 안전안내문자에서 분리).
  세부 재난종류(enum)는 「재난문자방송 기준 및 운영규정」(행정안전부 예규) 별표2·별표3에 표준문안과 함께 명시됨.
- **Delivery guarantees.** At-most-once (메시지 식별자+Serial Number 기준). 같은 Update Number 재방송 시 단말이 중복 suppress. 지역 경계 교차 시 이중 수신 가능.
- **Auth / access tier.** 송출 권한은 계층화 — 행정안전부(전국), 기상청(특보성 재난문자), 지방자치단체(관할 지역). 2026년부터 위급재난문자 일부가 지자체로 이관. 수신 측은 무인증(단말 OS).
- **Rate / frequency.** 발송 빈도 상한 규정 없음, 단 운영규정상 동일 사안 반복 송출 최소화 권고. 단말 측은 실시간.
- **Sources.** 3GPP TS 23.041 §9.4 (Message Identifier); TTAK.KO-06.0263/R4 Korean PWS standard (June 2019); 「재난문자방송 기준 및 운영규정」 (행정안전부 예규 제320호, 2025.3.7.); ko.wikipedia.org 재난문자방송; namu.wiki 재난문자방송; 긴급재난문자 wiki.
- **Drop-in mirrorability: 2/5** — OS 경계 때문에 mock이 실제 단말 전송까지는 재현 불가. 대신 **payload 구조**는 JSON으로 미러 가능 → mock은 3번 항목의 safetydata.go.kr 계약을 primary, CBS 원본 구조는 secondary attribute(`cbs_message_identifier`, `cbs_serial_number`, `cbs_dcs`, `cbs_page_parameter`)로 노출한다.
- **Gaps.** ⚠️ OPAQUE — `CBC ↔ MME SBc-AP` 내부 메시지 스키마는 기관간 계약이라 비공개. Mock에서는 무시.

### 2. 행정안전부 긴급재난문자 V2 API (safetydata.go.kr)

- **Event delivery protocol.** REST GET over HTTPS, JSON(기본) / XML. 페이지네이션 기반 pull.
- **Subscription setup.** `safetydata.go.kr` 회원가입 → 해당 데이터셋(`dataSn=228`)에 활용 신청 → 승인 후 `serviceKey` 발급. 사전에 지역명/조회시작일자 필터만 미리 정함.
- **Event payload schema.** 응답 본문 `body` 배열. 공개된 실사용 예제에서 관찰된 필드와 데이터 상세 화면(safetydata.go.kr/disaster-data/disasterNotification) 기준 필드:
  ```
  {
    "header": { "resultCode": "00", "resultMsg": "NORMAL SERVICE", "totalCount": 51451 },
    "body": [
      {
        "SN": 51451,                        // 일련번호 (신규 필드. 구 API의 MD101_SN 대체)
        "CRT_DT": "2026-04-18 20:13:51",    // 등록일시
        "MSG_CN": "오늘 19:44 장안구 연무동 ... 화재 발생 ...",  // 메시지 본문
        "RCPTN_RGN_NM": "수원시",            // 수신지역명
        "EMRG_STEP_NM": "긴급",              // 긴급단계명 (위급/긴급/안전안내)
        "DST_SE_NM": "화재",                 // 재해구분명
        "REG_YMD": "20260418",              // 등록일자
        "MDFCN_YMD": "20260418"
      }
    ]
  }
  ```
  구 `data.go.kr` API(dataset 3058822)의 필드는 `MD101_SN / CREATE_DT / LOCATION_NAME / LOCATION_ID / DSSTR_SE_NM / MSG_CN` 체계였으며, 신 API에서는 약간 이름이 변경되었다(공개 공지 "공공데이터포털 재난문자방송 API 이용자 대상 차이점 안내" 참조).
- **Event types / categories.** `DST_SE_NM` enum: 지진·태풍·호우·대설·산불·화재·민방공·감염병·교통통제·가축전염병·단수·미세먼지·실종·기타. `EMRG_STEP_NM` enum: 위급/긴급/안전안내/실종경보.
- **Delivery guarantees.** At-least-once on poll — 동일 `SN` 반복 수신 가능. 순서 보장 없음 (`REG_YMD` 기준 정렬 필요). `CRT_DT` 초 단위 해상도.
- **Auth / access tier.** `serviceKey` (URL 인코딩된 값). 대문자 `K` 필수 (velog 예제에서 400 오류 재현 보고). 2023년 이전 데이터는 미제공.
- **Rate / frequency.** 실시간 갱신. 개발계정/운영계정 일일 트래픽 미공개(일반적으로 safetydata.go.kr은 1,000–10,000 req/day). `numOfRows` 최대 1000.
- **Sources.** https://www.safetydata.go.kr/disaster-data/view?dataSn=228; https://www.data.go.kr/data/15134001/openapi.do; https://www.safetydata.go.kr/notice/selectNotice?tbbsSn=1260; velog.io/@gyu_p/재난안전플랫폼 (엔드포인트 예시 `/V2/api/DSSP-IF-00195`).
- **Drop-in mirrorability: 5/5** — 필드 스키마가 단순하고 JSON 구조 고정. mock server는 FastAPI + pydantic으로 `SN`·`CRT_DT`·`MSG_CN`·`EMRG_STEP_NM`·`DST_SE_NM` 만 구현하면 shape-identical.
- **Gaps.** ⚠️ OPAQUE — DSSP-IF-XXXXX 엔드포인트 번호 체계 전체 목록. 긴급재난문자 전용 번호는 공개 자료상 미확인(대피소가 00195). 승인 후 실제 엔드포인트 노출됨.

### 3. 국민재난안전포털 safekorea.go.kr + 안전디딤돌

- **Event delivery protocol.** 시민 측: Android/iOS 네이티브 푸시(FCM/APNs). 관리자 측: 웹 대시보드. 공개 API는 2번 항목(긴급재난문자 API)을 내부적으로 공유.
- **Subscription setup.** 안전디딤돌 앱 설치 → 수신 지역(시/도/시군구) 선택 → 기상특보 수신 여부 토글 → FCM 등록 토큰 발급. 서버측 사용자 state(지역×카테고리 매트릭스) 저장.
- **Event payload schema.** FCM 메시지 payload. 앱 공식 설명상 알림 종류: (1) 위치 기반 긴급재난문자 푸시, (2) 기상특보 푸시, (3) 대피소·병원·소방서 정보 변경, (4) 행동요령. 실제 FCM JSON 스키마는 ⚠️ OPAQUE.
- **Event types / categories.** 재난문자 3등급 × 지역(전국/광역/기초). 기상특보 12종.
- **Delivery guarantees.** FCM 기본 at-least-once. 앱 off-line 시 deliver on next connect.
- **Auth / access tier.** 시민용은 무인증(앱 설치 + 지역선택). 관리자용(시·도 담당자) 별도 인증.
- **Rate / frequency.** 이벤트 발생 시.
- **Sources.** https://www.safekorea.go.kr/; https://apps.apple.com/kr/app/안전디딤돌/id475638064; https://www.gov.kr/portal/service/serviceInfo/PTR000052059.
- **Drop-in mirrorability: 3/5** — FCM 네이티브 통합은 mock 범위를 벗어남. mock은 "push simulator" 모드로만 제공하고, 실제 이벤트는 2번 API의 롱폴링 결과를 그대로 복사해 FCM-shaped envelope으로 감싼다.
- **Gaps.** ⚠️ OPAQUE — FCM payload의 data field 키 이름. 앱 소스 리버스 엔지니어링 금지(방침).

### 4. 기상청 기상특보 조회서비스

- **Event delivery protocol.** REST GET, JSON+XML. data.go.kr gateway 경유.
- **Subscription setup.** data.go.kr 회원가입 → dataset `15139476` 활용신청 → `ServiceKey` 발급. 사전 구독 state 없음.
- **Event payload schema.** 오퍼레이션 `getWthrWrnList` 기준 확인된 요청/응답:
  ```
  GET http://apis.data.go.kr/1360000/WthrWrnInfoService/getWthrWrnList
    ?ServiceKey={key}
    &pageNo=1
    &numOfRows=10
    &dataType=JSON
    &stnId=108                 // 지점코드 (선택)
    &fromTmFc=20260410
    &toTmFc=20260419

  // response.body.items.item[]
  {
    "title": "기상특보",
    "stnId": "108",             // 지점코드 (108=전국, 109=서울/경기, 131=충청, ...)
    "tmSeq": "2026041900000",   // 발표 시퀀스
    "tmFc":  "202604190530",    // 발표시각 YYYYMMDDHHMM
    // t1..t7 필드 — 특보 본문 단락 (공식 설명서에 기재)
  }
  ```
- **Event types / categories.** 특보 12종 × 2등급(주의보/경보): 강풍·풍랑·호우·대설·건조·폭풍해일·지진해일·태풍·황사·한파·폭염·안개(해상). 178개 시군 + 44개 해역 단위. 오퍼레이션 — `getWthrWrnList`(목록), `getWthrWrnMsg`(통보문), `getInfoList/getInfo`(기상정보), `getBrfList/getBrf`(기상속보), `getPwnList/getPwn`(예비특보), `getWrnCdInfo`(특보코드 조회), `getWrnStatus`(특보현황).
- **Delivery guarantees.** At-least-once on poll. `tmSeq` 기반 중복 제거.
- **Auth / access tier.** `ServiceKey` 필수. 개발/운영 계정 트래픽 차등.
- **Rate / frequency.** 실시간 갱신, 운영계정 보통 10k/day.
- **Sources.** https://www.data.go.kr/data/15139476/openapi.do; https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15000415; https://data.kma.go.kr/data/weatherReport/wsrList.do; https://apihub.kma.go.kr/.
- **Drop-in mirrorability: 5/5** — 엔드포인트·필드·enum 모두 공개. fixture로 `stnId=108` 전국 폭염경보 샘플 1건 작성 가능.
- **Gaps.** `t1..t7` 각 필드의 정확한 용도(우선순위/지역/원인/설명 등)는 "API 인터페이스 정의서" 첨부파일에 기재 — URL 참조 필요.

### 5. 기상청 지진정보 조회서비스 (EqkInfoService)

- **Event delivery protocol.** REST GET, JSON+XML.
- **Subscription setup.** data.go.kr 활용신청 (dataset 15000420).
- **Event payload schema.**
  ```
  GET http://apis.data.go.kr/1360000/EqkInfoService/getEqkMsg
    ?ServiceKey={key}&pageNo=1&numOfRows=10&dataType=JSON
    &fromTmFc=20260101&toTmFc=20260419

  // items.item[]
  {
    "tmFc":   "2026041910230000", // 발표시각
    "tmEqk":  "2026041910200000", // 진앙시
    "mt":     "4.5",              // 규모 (magnitude)
    "lat":    "36.12",            // 위도
    "lon":    "129.35",           // 경도
    "loc":    "경상북도 포항시 북구 북북동쪽 10km 지역",
    "dep":    "12",               // 깊이 km
    "rem":    "기상청 통보",
    "fcTp":   "10",               // 통보종류코드 (10=조기경보, 20=지진속보, 30=지진정보, 40=국외지진)
    "inT":    "IV"                // MMI 진도 (로마숫자 I~X)
  }
  ```
  별도 오퍼레이션: 지진해일통보문(쓰나미) 조회 — 동일한 URL 체계의 `getTsuMsg`(⚠️ 정확한 오퍼레이션명 미확인, 확인 필요).
- **Event types / categories.** `fcTp` enum 4종. 진도 MMI 로마숫자 I–XII.
- **Delivery guarantees.** 조기경보는 P파 도달 후 수초 내 1차 발표 → 수정판(Update Serial) 발송. Mock은 동일 `tmEqk` 하에 다수 `tmFc` 수신을 허용해야 한다.
- **Auth / access tier.** `ServiceKey`. 개발계정 10,000/일.
- **Rate / frequency.** 이벤트 발생 시만 갱신, polling 간격 권고 30–60초.
- **Sources.** https://www.data.go.kr/data/15000420/openapi.do.
- **Drop-in mirrorability: 5/5**.
- **Gaps.** ⚠️ 지진해일 API의 정확한 오퍼레이션명과 쓰나미 필드(`tsuHt`, `tsuArTm` 등) 공개 정보 미확인.

### 6. 에어코리아 대기오염정보 API (한국환경공단)

- **Event delivery protocol.** REST GET, JSON+XML. data.go.kr gateway.
- **Subscription setup.** dataset 15073861 활용신청 → `serviceKey`.
- **Event payload schema.** Base `http://apis.data.go.kr/B552584/ArpltnInforInqireSvc`. 오퍼레이션:
  - `getMinuDustFrcstDspth` (대기질 예보/경보):
    ```
    ?serviceKey={key}&returnType=json&numOfRows=100&pageNo=1
    &searchDate=2026-04-19
    &InformCode=PM10      // 또는 PM25, O3
    ```
    응답:
    ```json
    {
      "response": { "body": { "items": [{
        "dataTime": "2026-04-19 05",
        "informCode": "PM10",
        "informOverall": "[오전] ... [오후] ...",
        "informCause": "원활한 대기 확산 ...",
        "informGrade": "서울 : 좋음,제주 : 좋음,전남 : 좋음, ...",
        "actionKnack": "외출 시 ...",
        "imageUrl1": "http://...", "imageUrl2": "...", ... "imageUrl7": "...",
        "informData": "2026-04-20"
      }]}}
    }
    ```
  - `getCtprvnRltmMesureDnsty` (시도별 실시간), `getMsrstnAcctoRltmMesureDnsty` (측정소별), `getUnityAirEnvrnIdexSnstiveAboveMsrstnList`.
- **Event types / categories.** `informCode` enum: `PM10`, `PM25`, `O3`. `informGrade` enum: 좋음/보통/나쁨/매우나쁨.
- **Delivery guarantees.** At-least-once on poll. 매일 오전 5시/11시/17시/23시 갱신(대기질 예보).
- **Auth / access tier.** `serviceKey`. 개발 500/일, 운영 10,000/일.
- **Rate / frequency.** 실시간 측정자료는 매시 갱신.
- **Sources.** https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15073861; http://openapi.airkorea.or.kr/; https://www.airkorea.or.kr/.
- **Drop-in mirrorability: 5/5**.
- **Gaps.** 없음.

### 7. 한국도로공사 실시간 문자정보 (VMS)

- **Event delivery protocol.** REST GET, JSON+XML. `data.ex.co.kr/openapi` 직접 gateway.
- **Subscription setup.** `data.ex.co.kr` 회원가입 + API key 신청. dataset 15076693는 data.go.kr에서 LINK 형태로 연결.
- **Event payload schema.** 공개 예제 페이지(`data.ex.co.kr/openapi/example/exampleTraffic`) 기준 관찰된 필드(상세는 ⚠️ OPAQUE): `unitCode`(사무소 코드), `routeNo`(노선번호), `routeName`, `vmsMessage`(VMS 전광판 문구), `vmsCode`, `tcsType`, `regDate`. 호출 URL 형태: `http://data.ex.co.kr/openapi/basicinfo/openApiInfoM?apiId=0611`.
- **Event types / categories.** 교통혼잡 / 공사구간 / 사고발생 / 기상특보 (API 소개문 인용).
- **Delivery guarantees.** At-least-once on poll.
- **Auth / access tier.** API key. 무료.
- **Rate / frequency.** 실시간 갱신, 예시상 5분 polling 권고.
- **Sources.** https://data.ex.co.kr/openapi/intro/introduce02; https://www.data.go.kr/data/15076693/openapi.do.
- **Drop-in mirrorability: 4/5** — 구조는 단순하지만 공식 필드 정의서가 개별 API마다 분산.
- **Gaps.** VMS 메시지 코드 enum 전수 조사 필요.

### 8. 국토교통부 ITS 돌발상황 (openapi.its.go.kr)

- **Event delivery protocol.** REST GET, JSON+XML.
- **Subscription setup.** `www.its.go.kr/opendata` 회원가입 → `apiKey` 발급.
- **Event payload schema.**
  ```
  GET https://www.its.go.kr/opendata/opendataList?service=event
    ?apiKey={key}
    &type=all            // all/ex(고속도로)/its/loc/sgg/etc
    &eventType=all       // all/cor(공사)/acc(사고)/wea(기상)/ete(재난)/dis(기타돌발)/etc
    &minX=&maxX=&minY=&maxY=
    &getType=json

  {
    "resultCode": "00", "resultMsg": "OK", "totalCount": N,
    "body": { "items": [{
      "type": "ex",
      "eventType": "acc",
      "eventDetailType": "...",  // 세부 코드
      "startDate": "20260419100000",
      "endDate": "...",
      "coordX": 127.12, "coordY": 37.55,
      "linkId": "...",
      "roadName": "경부고속도로",
      "roadNo": "0010",
      "message": "서울 방향 ..."
    }]}
  }
  ```
- **Event types / categories.** `eventType` 6종 × `eventDetailType` 세부 코드.
- **Delivery guarantees.** At-least-once on poll. 이벤트 종료 시 `endDate`로 마감.
- **Auth / access tier.** apiKey.
- **Rate / frequency.** 집계 주기 5분.
- **Sources.** https://www.its.go.kr/opendata/opendataList?service=event; https://www.data.go.kr/data/15040465/openapi.do.
- **Drop-in mirrorability: 5/5**.
- **Gaps.** `eventDetailType` 전체 코드표는 openapi.its.go.kr 개발자센터에서 PDF 가이드로만 공개.

### 9. 지자체 — 서울 열린데이터광장 RSS (외 2건)

- **Event delivery protocol.** RSS 2.0 XML feed. 클라이언트 HTTP GET.
- **Subscription setup.** 무인증, 피드 URL 구독만.
- **Event payload schema.** RSS 2.0 표준: `<channel>` 아래 `<item>` 리스트, 각 `<title>`, `<link>`, `<description>`, `<pubDate>`, `<guid>`.
- **Event types / categories.** 서울 열린데이터광장 RSS 카테고리 13종:
  - 전체(0000), 일반행정(1000), 도서관리(1001), 환경(1002), **안전(1003)**, 교육(1004), 산업경제(1005), 복지(1006), 교통(1007), 문화관광(1008), 보건(1009), 인구(10001), 주택(10326).
  - URL 패턴: `https://data.seoul.go.kr/rss/rssView.do?searchType={code}`.
- **Delivery guarantees.** RSS 표준 — 클라이언트 측 `guid` 기반 중복 제거.
- **Auth / access tier.** 무인증.
- **Rate / frequency.** ⚠️ OPAQUE — 명시적 갱신주기 없음, 관행상 30분 간격 polling.
- **Sources.** https://data.seoul.go.kr/link/rssList.do.
- **Drop-in mirrorability: 5/5** (RSS 2.0은 표준 parser로 충분).
- **Gaps.** 지자체별 RSS 구조는 상이 — 경기·부산·대구는 기관별 홈페이지 카테고리 RSS 지원 여부가 지자체마다 다르며, 대부분 재난 전용 피드는 제공하지 않음(국민재난안전포털로 일원화).

### 10. 식품의약품안전처 RSS + OpenAPI

- **Event delivery protocol.** RSS 2.0 XML feed (공지·공고·회수). OpenAPI는 식의약데이터포털(data.mfds.go.kr) + 식품안전나라(foodsafetykorea.go.kr) + 의약품안전나라(nedrug.mfds.go.kr)로 분산.
- **Subscription setup.** RSS: 무인증. OpenAPI: 각 포털별 회원가입.
- **Event payload schema.** RSS 2.0. 피드 URL 예:
  - 공지: `http://www.mfds.go.kr/www/rss/brd.do?brdId=ntc0003`
  - 공고: `?brdId=ntc0004`
  - 보도자료: `?brdId=ntc0021`
  - 행정예고: `?brdId=data0009`
  - 최근 개정 법령: `?brdId=data0008`
  - **의약품 행정처분: `?brdId=plc0117`**
  - **의료기기 회수/판매중지: `?brdId=plc0139`**
  각 `<item>`: title, link, pubDate, description(본문 HTML 일부).
- **Event types / categories.** `brdId` prefix로 채널 분리 (`ntc*`, `data*`, `plc*`).
- **Delivery guarantees.** RSS 표준 at-most-once(클라이언트 dedupe by `<link>` or hash).
- **Auth / access tier.** 무인증.
- **Rate / frequency.** 실시간 갱신(게시 시점).
- **Sources.** https://www.mfds.go.kr/www/rss/list.do; https://data.mfds.go.kr/.
- **Drop-in mirrorability: 5/5**.
- **Gaps.** 식품 리콜 실시간 RSS는 `plc*` 계열 외에 추가 피드 존재 가능 — 전체 `brdId` enum은 RSS 안내 페이지에서 확장 필요.

### 11. OPEN DART 공시검색 (금융감독원)

- **Event delivery protocol.** REST GET, JSON(`/api/list.json`) / XML(`/api/list.xml`).
- **Subscription setup.** `opendart.fss.or.kr` 회원가입 → `crtfc_key`(40자) 발급.
- **Event payload schema.** 공식 가이드(DS001/2019001) 명세 그대로:
  ```
  GET https://opendart.fss.or.kr/api/list.json
    ?crtfc_key={40-char key}
    &corp_code={8-char}
    &bgn_de=20260101&end_de=20260419     // YYYYMMDD 필수
    &last_reprt_at=N                      // 최종보고서만 여부
    &pblntf_ty=A                          // 공시유형 A~J
    &pblntf_detail_ty=A001                // 상세유형 (4자리)
    &corp_cls=Y                           // Y:유가, K:코스닥, N:코넥스, E:기타
    &sort=date                            // date/crp/rpt
    &sort_mth=desc                        // asc/desc
    &page_no=1
    &page_count=10                        // 최대 100

  {
    "status": "000", "message": "정상",
    "page_no": 1, "page_count": 10,
    "total_count": 1234, "total_page": 124,
    "list": [{
      "corp_cls": "Y", "corp_name": "삼성전자", "corp_code": "00126380",
      "stock_code": "005930",
      "report_nm": "매출액또는손익구조30%(대규모법인은15%)이상변경",
      "rcept_no": "20260419800123",
      "flr_nm": "삼성전자",
      "rcept_dt": "20260419",
      "rm": "유"
    }]
  }
  ```
- **Event types / categories.** `pblntf_ty` 10종(A 정기공시, B 주요사항보고, C 발행공시, D 지분공시, E 기타공시, F 외부감사관련, G 펀드공시, H 자산유동화, I 거래소공시, J 공정위공시). 각 `pblntf_detail_ty`는 4자리 세부 코드.
- **Delivery guarantees.** At-least-once on poll. `rcept_no`로 dedupe.
- **Auth / access tier.** `crtfc_key` 필수. 일 20,000 요청 초과 시 에러. `corp_code` 최대 100건/호출.
- **Rate / frequency.** 공시 접수 시점 기준 실시간 반영 (분 단위 지연). 권고 polling 30초–1분.
- **Sources.** https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001; https://opendart.fss.or.kr/intro/main.do.
- **Drop-in mirrorability: 5/5** — 전 필드 공개 + 공식 가이드 명시.
- **Gaps.** 공시원문 바이너리 zip (`/api/document.xml`) 응답은 바이너리라 mock 우선순위 낮음.

### 12. 한국전력거래소(KPX) 현재전력수급현황 OpenAPI

- **Event delivery protocol.** REST GET.
- **Subscription setup.** data.go.kr dataset 15056640 활용신청.
- **Event payload schema.**
  ```
  GET https://openapi.kpx.or.kr/openapi/sukub5mMaxDatetime/getSukub5mMaxDatetime

  {
    "resultCode": "00", "resultMsg": "NORMAL",
    "baseDatetime":    "20260419133000",  // YYYYMMDDHHMMSS
    "suppAbility":     92345.6,           // 공급능력 MW
    "currPwrTot":      81234.5,           // 현재수요 MW
    "forecastLoad":    83456.7,           // 최대예측수요 MW
    "suppReservePwr":  11110.1,           // 공급예비력 MW
    "suppReserveRate": 13.68,             // 공급예비율 %
    "operReservePwr":  5678.9,            // 운영예비력 MW
    "operReserveRate":  7.00              // 운영예비율 %
  }
  ```
- **Event types / categories.** 단일 스냅샷. 경보(주의/경계/심각) 신호는 별도 필드 없이 `operReserveRate` 임계치(5,500 MW 등)로 계산.
- **Delivery guarantees.** Latest-only snapshot. 중복은 `baseDatetime` 5분 단위.
- **Auth / access tier.** `serviceKey`. 개발 100/일(낮은 편).
- **Rate / frequency.** 5분 갱신.
- **Sources.** https://www.data.go.kr/data/15056640/openapi.do; https://epsis.kpx.or.kr/.
- **Drop-in mirrorability: 5/5**.
- **Gaps.** 한국전력공사(KEPCO) 실시간 정전속보 API는 공개 목록에서 확인 불가. ⚠️ OPAQUE — 고객센터 전화/앱 푸시(KEPCO 스마트앱)로만 통지되는 것으로 보임.

### 13. K-water 공공데이터 개방포털

- **Event delivery protocol.** REST GET(`opendata.kwater.or.kr`) + data.go.kr gateway + 파일 다운로드.
- **Subscription setup.** 포털 회원가입 + 활용신청.
- **Event payload schema.** 공개 데이터셋 중 "다목적댐 수문운영"(15099110), "공업생활용수 수질정보"(15099100) 등은 정적 측정값 API. JSON/XML. **단수 경보·수질 경보 전용 이벤트 API는 확인되지 않음** — 기관 단수/수질사고 공지는 각 지방상수도 홈페이지 공지사항 웹페이지로만 발송.
- **Event types / categories.** 수질·수위·방류·댐별 저수율. 경보 카테고리 부재.
- **Delivery guarantees.** Snapshot 기반.
- **Auth / access tier.** 포털 인증키.
- **Rate / frequency.** 10분/시간/일 단위.
- **Sources.** https://opendata.kwater.or.kr/open/data/list/list.do; https://www.data.go.kr/data/15099110/openapi.do; https://water-pos.kwater.or.kr/.
- **Drop-in mirrorability: 3/5** — 정기 측정값은 mock 가능하지만 "단수 알림" 이벤트는 계약이 존재하지 않아 mock 설계시 `water_quality_snapshot` 채널로 한정 권장.
- **Gaps.** ⚠️ OPAQUE — 단수·수질사고 Event 구조는 지자체 상수도사업본부 내부 채널.

### 14. 질병관리청 (KDCA) 전수신고 감염병 발생현황

- **Event delivery protocol.** REST GET, JSON+XML. data.go.kr gateway.
- **Subscription setup.** dataset 15139178 활용신청 → `serviceKey`.
- **Event payload schema.** 공개 인터페이스 정의서(엑셀 첨부, v1.0)에 전체 필드 기재. 상위 구조 확인 항목: 감염병분류코드, 감염병명, 환자분류(확진/의사환자), 시도/시군구, 연령대, 성별, 발생건수, 기준연월, 누계.
- **Event types / categories.** 법정감염병 — 1급 17종, 2급 20종, 3급 25종. 「감염병의 예방 및 관리에 관한 법률」 근거.
- **Delivery guarantees.** 실시간 + 통계 확정 재발표 가능 → `update_dt` 기준 갱신 필요.
- **Auth / access tier.** `serviceKey`. 개발계정 1,000/일.
- **Rate / frequency.** 실시간 (방역통합정보시스템).
- **Sources.** https://www.data.go.kr/data/15139178/openapi.do; https://dportal.kdca.go.kr/.
- **Drop-in mirrorability: 4/5** — 인터페이스 정의서 엑셀 필수 확인 후 완성.
- **Gaps.** 감염병 경보(주의→경계→심각)의 별도 event API는 없음 — 질병관리청 보도자료 RSS로만 확산.

### 15. 국가법령정보 OPEN API — 법령 변경이력 목록

- **Event delivery protocol.** REST GET, HTML/XML/JSON 3종 포맷.
- **Subscription setup.** `open.law.go.kr` 회원가입 → OC(Open API 인증값, 이메일 ID) 발급. 활용신청 승인 후 사용. 맞춤형서비스(사용자 정의 데이터) 별도 제공.
- **Event payload schema.** 공식 가이드(`lsChgListGuide`) 기준:
  ```
  GET http://www.law.go.kr/DRF/lawSearch.do
    ?OC={email_id_prefix}
    &target=lsHstInf              // 서비스 대상 (lsHstInf = 법령 변경이력)
    &type=XML                     // HTML / XML / JSON
    &regDt=20260419               // 변경일(필수)
    &org=1170000                  // 소관부처 (선택)
    &display=20                   // 결과 개수 (max 100)
    &page=1
    &popYn=N

  <LsChgListSearch>
    <totalCnt>N</totalCnt>
    <page>1</page>
    <law>
      <법령ID>001234</법령ID>
      <법령명한글>개인정보 보호법</법령명한글>
      <공포일자>20260115</공포일자>
      <공포번호>12345</공포번호>
      <시행일자>20260715</시행일자>
      <제개정구분명>일부개정</제개정구분명>
      <소관부처명>개인정보보호위원회</소관부처명>
      <법령구분명>법률</법령구분명>
      <법령상세링크>/LSW/lsInfoP.do?...</법령상세링크>
    </law>
  </LsChgListSearch>
  ```
- **Event types / categories.** `target` enum 다수 — `law`, `lsHstInf`(변경이력), `lsJoHst`(일자별 조문 개정), `lsJoChgHst`(조문별), `lsConf`(신구법), `lsCmp`(3단비교), `ordin`(자치법규), `expc`(법령해석례). 제개정구분: 제정/일부개정/전부개정/폐지 등.
- **Delivery guarantees.** At-least-once on poll by `regDt`. 동일 법령에 대한 여러 개정은 `공포번호`로 구분.
- **Auth / access tier.** `OC` 쿼리 파라미터. 무료. Rate limit 공식 미공개.
- **Rate / frequency.** 공포 시점 기준 실시간. 폴링 일 1회 권고.
- **Sources.** https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=lsChgListGuide; https://www.data.go.kr/data/15058499/openapi.do; https://open.law.go.kr/LSO/information/guide.do.
- **Drop-in mirrorability: 5/5**.
- **Gaps.** `target` enum 전체 80종 이상 — mock에서는 `lsHstInf`만 우선 구현.

### 16. 공공데이터포털 data.go.kr — 활용신청 기반 변경 알림

- **Event delivery protocol.** 기관 담당자 발송 SMS/이메일 (자동 API 아님).
- **Subscription setup.** 활용신청 승인 절차에서 담당자가 SMS/이메일로 신청인에게 결과 통지.
- **Event payload schema.** 표준화 없음.
- **Event types / categories.** 활용신청 승인/반려 / 서비스 변경 공지.
- **Delivery guarantees.** ⚠️ OPAQUE — 제도적 운영, 전자적 API 미제공.
- **Auth / access tier.** 회원가입.
- **Rate / frequency.** 이벤트 기반.
- **Sources.** https://www.data.go.kr/ugs/selectPublicDataUseGuideView.do.
- **Drop-in mirrorability: 1/5** — API 면 부재, mock 대상 제외 권장.
- **Gaps.** 전체가 institutional, 전자 계약 없음.

---

## Cross-cutting patterns (공통 이벤트 shape)

공공 API의 대부분 이벤트에서 반복 관찰되는 필드 집합을 추려 **`KosmosSubscribeEvent`** mock canonical envelope을 다음과 같이 정의 권장.

```python
class KosmosSubscribeEvent(BaseModel):
    channel: Literal[                     # 토픽
        "disaster_msg", "weather_warning", "earthquake",
        "air_quality_forecast", "traffic_incident", "vms_text",
        "disclosure", "power_supply_snapshot", "infectious_disease",
        "law_amendment", "mfds_recall", "seoul_rss_safety",
    ]
    source_system: str                    # "safetydata.go.kr" / "apis.data.go.kr" / "opendart.fss.or.kr"...
    event_id: str                         # 실서버 primary key (SN, rcept_no, tmSeq, guid 등)
    issued_at: datetime                   # 실서버 발표시각 (CRT_DT, tmFc, rcept_dt...)
    received_at: datetime                 # harness 수신시각
    severity: Literal["critical","urgent","safety","info","unknown"]
    category: str                         # 실서버 enum 원값 (DST_SE_NM, wrnCd, eventType...)
    region: Optional[RegionRef]           # 시도·시군구·좌표
    body: Dict[str, Any]                  # 실서버 payload 원본 (mirror)
    raw: Dict[str, Any]                   # Pre-transform raw response
```

**패턴 a — 인증.** 거의 전부 URL 쿼리 `serviceKey`/`crtfc_key`/`OC`/`apiKey`. 헤더 기반 토큰 전무.
**패턴 b — 페이지네이션.** `pageNo` + `numOfRows` (data.go.kr 표준) 또는 `page` + `display`(law.go.kr) 또는 `page_no` + `page_count`(opendart).
**패턴 c — 시간 파라미터.** YYYYMMDD(`bgn_de`, `regDt`, `fromTmFc`) 또는 YYYYMMDDHHMMSS(`baseDatetime`). ISO 8601 미사용.
**패턴 d — 응답 래퍼.** `response.header.resultCode/resultMsg + response.body.items.item[]` (data.go.kr 공용 게이트웨이). OPEN DART는 `status/message/list` 루트 필드. law.go.kr은 `<target>Search` 루트 XML 엘리먼트.
**패턴 e — dedupe 키.** 대부분 단일 primary id: `SN`, `rcept_no`, `tmSeq`, `법령ID+공포번호`, `baseDatetime`. Mock 구현 시 이 키로 at-least-once → exactly-once 변환.
**패턴 f — 카테고리 enum 공개 수준.** enum이 문서에 나열된 경우(DART `pblntf_ty`, KMA 특보 12종, CBS 4등급)와 첨부 엑셀에만 있는 경우(KDCA 감염병 62종, ITS `eventDetailType`) 혼재. Mock fixture는 전자만 우선 완성.
**패턴 g — webhook 부재.** 13개 시스템 중 어느 곳도 공개 webhook·SSE·WebSocket 엔드포인트를 제공하지 않음. KOSMOS는 mock에서 "pseudo-subscribe"(내부 타이머 + poll)으로 이 제약을 그대로 에뮬레이션해야 replaceability가 보장된다.

---

## Unknowns matrix

| 시스템 | ⚠️ Gap 항목 |
|---|---|
| 긴급재난문자 CBS | CBC↔MME SBc-AP 내부 스키마 · TTAK.KO-06.0263/R4 본문 전수 |
| safetydata.go.kr V2 | `DSSP-IF-XXXXX` 엔드포인트 번호 전수, `EMRG_STEP_NM` 대 `emergency_level_code` 매핑 |
| 안전디딤돌 FCM | FCM data payload key 이름 |
| 기상특보 | `t1..t7` 필드 정확한 용도, 특보코드 `wrnCd` enum 테이블(강풍 주의보=?, 호우 경보=?) |
| 지진정보 | 지진해일(`getTsuMsg`?) 정확한 오퍼레이션명, `tsuHt`/`tsuArTm` 필드 |
| 한국도로공사 VMS | vmsCode enum 전수 |
| ITS 돌발 | `eventDetailType` enum 전수 |
| KEPCO 정전 | 실시간 정전속보 이벤트 API 유무 (공개 확인 불가) |
| K-water | 단수/수질사고 이벤트 API (확인 실패) |
| KDCA | 감염병 경보 단계(주의/경계/심각) 전용 이벤트 API (부재로 추정) |
| 법령 | `target` enum 전수 (80종 이상) |
| data.go.kr 알림 | 활용신청 상태 webhook(부재) |

---

## References

1. **KPAS / CBS / 3GPP 표준**
   - 3GPP TS 23.041 Cell Broadcast Service (CBS) — https://www.tech-invite.com/3m23/toc/tinv-3gpp-23-041_q.html
   - TTAK.KO-06.0263/R4 "Requirements and Message Format for Korean Public Alert System over Mobile Network" (June 2019)
   - 「재난문자방송 기준 및 운영규정」 행정안전부 예규 제320호(2025.3.7. 시행) — https://www.law.go.kr/행정규칙/재난문자방송기준및운영규정 · https://www.mois.go.kr/frt/bbs/type001/commonSelectBoardArticle.do?bbsId=BBSMSTR_000000000016&nttId=116185
   - 재난문자방송 Wikipedia(ko) — https://ko.wikipedia.org/wiki/재난문자방송
   - 재난문자방송 Namuwiki — https://namu.wiki/w/재난문자방송
   - 긴급재난문자 Namuwiki — https://namu.wiki/w/긴급재난문자
   - "Cell Broadcast Service를 이용한 재난정보 전송에 관한 연구" (이유석·오승희, 한국방송·미디어공학회 2020 하계학술대회) — https://koreascience.or.kr/article/CFKO202023758834212.pdf
   - 한국사물인터넷협회 「공공경보시스템(PWS) 이슈리포트」(2023.06) — https://www.aiotkorea.or.kr/2023/webzine/KIoT/(2023-06)IssueReport.pdf
2. **재난안전·국민재난안전포털**
   - 재난안전데이터공유플랫폼 — https://www.safetydata.go.kr/
   - 행정안전부 긴급재난문자 dataset — https://www.safetydata.go.kr/disaster-data/view?dataSn=228 · https://www.data.go.kr/data/15134001/openapi.do
   - "공공데이터포털 재난문자방송 API 이용자 대상 차이점 안내" — https://www.safetydata.go.kr/notice/selectNotice?tbbsSn=1260
   - 재난안전 플랫폼 API 활용 예제(velog) — https://velog.io/@gyu_p/재난안전플랫폼
   - 국민재난안전포털 — https://www.safekorea.go.kr/
   - 안전디딤돌 앱(Play Store) — https://play.google.com/store/apps/details?id=kr.go.nema.disasteralert_new
3. **기상청 (KMA)**
   - 기상청 특보 조회서비스 — https://www.data.go.kr/data/15139476/openapi.do · https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15000415
   - 기상청 지진정보 조회서비스 — https://www.data.go.kr/data/15000420/openapi.do
   - 기상자료개방포털 기상특보 탭 — https://data.kma.go.kr/data/weatherReport/wsrList.do?pgmNo=647&tabNo=2
   - 기상청 API허브 — https://apihub.kma.go.kr/
4. **대기환경 (AirKorea)**
   - 한국환경공단 에어코리아 대기오염정보 — https://www.data.go.kr/tcs/dss/selectApiDataDetailView.do?publicDataPk=15073861
   - AirKorea OpenAPI — http://openapi.airkorea.or.kr/
5. **교통 (ITS / 한국도로공사)**
   - ITS 국가교통정보센터 돌발상황 — https://www.its.go.kr/opendata/opendataList?service=event · https://www.data.go.kr/data/15040465/openapi.do
   - 한국도로공사 실시간 문자정보 — https://www.data.go.kr/data/15076693/openapi.do · https://data.ex.co.kr/openapi/intro/introduce02
6. **식품·의약품 (MFDS)**
   - 식약처 RSS 최신정보 제공 서비스 — https://www.mfds.go.kr/www/rss/list.do
   - 식의약데이터포털 — https://data.mfds.go.kr/
7. **전력 (KPX / KEPCO)**
   - KPX 현재전력수급현황 OpenAPI — https://www.data.go.kr/data/15056640/openapi.do
   - EPSIS — https://epsis.kpx.or.kr/
   - KEPCO 전력데이터 개방 포털 — https://bigdata.kepco.co.kr/
8. **수도 (K-water)**
   - K-water 공공데이터 개방포털 — https://opendata.kwater.or.kr/open/data/list/list.do
   - K-water 한국수자원공사 공공데이터 — https://www.kwater.or.kr/gov3/pubdataPage.do
9. **보건 (KDCA)**
   - 전수신고 감염병 발생현황 API — https://www.data.go.kr/data/15139178/openapi.do
   - 질병관리청 감염병포털 — https://dportal.kdca.go.kr/
10. **법령 (법제처 / 국가법령정보센터)**
    - 국가법령정보 OPEN API 이용안내 — https://open.law.go.kr/LSO/information/guide.do
    - OPEN API 활용가이드 — https://open.law.go.kr/LSO/openApi/guideList.do
    - 법령 변경이력 목록 조회 API 가이드 — https://open.law.go.kr/LSO/openApi/guideResult.do?htmlName=lsChgListGuide
    - 법제처 법령 변경이력 목록 조회 — https://www.data.go.kr/data/15058499/openapi.do
11. **금융공시 (DART / 금융감독원)**
    - OPEN DART 오픈API 소개 — https://opendart.fss.or.kr/intro/main.do
    - OPEN DART 공시검색 개발가이드 — https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019001
    - OPEN DART 공시서류원본파일 가이드 — https://opendart.fss.or.kr/guide/detail.do?apiGrpCd=DS001&apiId=2019003
12. **지자체 · 공공데이터 메타**
    - 서울 열린데이터광장 RSS 리스트 — https://data.seoul.go.kr/link/rssList.do
    - 서울 안전누리 — https://safecity.seoul.go.kr/
    - 공공데이터포털 이용가이드 — https://www.data.go.kr/ugs/selectPublicDataUseGuideView.do
    - 공공데이터포털 소개 — https://www.data.go.kr/ugs/selectPortalInfoView.do
13. **국제 표준**
    - OASIS Common Alerting Protocol v1.2 — https://docs.oasis-open.org/emergency/cap/v1.2/CAP-v1.2-os.html
    - Common Alerting Protocol Wikipedia — https://en.wikipedia.org/wiki/Common_Alerting_Protocol
