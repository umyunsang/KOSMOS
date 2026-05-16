# Pre-application Screening: data.go.kr API 15001699

- Date: 2026-05-16
- Portal URL: https://www.data.go.kr/data/15001699/openapi.do
- API name: 건강보험심사평가원_의료기관별상세정보서비스
- Provider: 건강보험심사평가원
- Category: 보건 - 건강보험
- Selection source: data.go.kr main page -> 카테고리별 -> 보건의료 -> 오픈 API page 2
- Current UMMAYA status: not found in active `docs/api` adapters or existing `data-go-kr-candidate-docs`

## Citizen-query fit

| Citizen natural-language query | UMMAYA interpretation | API route | Required upstream context | Citizen-facing answer enabled |
| --- | --- | --- | --- | --- |
| 이 병원 MRI나 CT 장비가 있는지 알려줘. | A citizen already chose a hospital and needs equipment availability before visiting. | `getMedOftInfo2.7` | Encrypted `ykiho` from HIRA hospital basis search. | Equipment names and counts, such as `oftCdNm` and `oftCnt`. |
| 이 병원 응급실이 낮/밤에 운영되는지, 전화번호가 뭔지 확인해줘. | Verify detailed operating and emergency-room contact information for a selected institution. | `getDtlInfo2.7` | Encrypted `ykiho`. | Day/night emergency-room flags and phone fields such as `emyDayYn`, `emyNgtYn`, `emyDayTelNo1`, `emyNgtTelNo1`. |
| 아이 중환자실이나 신생아 중환자실이 있는 병원인지 봐줘. | Check facility capacity relevant to urgent pediatric/neonatal care. | `getEqpInfo2.7` | Encrypted `ykiho`. | Facility and bed-count fields such as `chldSprmCnt`, `nbySprmCnt`, `emymCnt`, address, and phone. |
| 이 병원에 정형외과 전문의가 몇 명인지 알려줘. | Detailed specialty and specialist-count lookup for a selected hospital. | `getSpcSbjtSdrInfo2.7` plus `getDgsbjtInfo2.7` | Encrypted `ykiho`; optionally specialty-code mapping. | Specialty code/name plus doctor and specialist counts. |
| 이 병원까지 대중교통으로 어떻게 가는지 알려줘. | Access guidance after selecting a hospital. | `getTrnsprtInfo2.7` | Encrypted `ykiho`; optionally user location from `locate`. | Public transport route, stop, direction, distance, and remarks. |

## UMMAYA wrapping rationale

- Candidate adapter: `hira_medical_institution_detail`
- Primary primitive: `find`
- Complementary primitive chain: `locate` -> existing `hira_hospital_search` -> this detail adapter.
- Expected usage pattern: high frequency when users ask for a nearby hospital, then ask follow-up questions about equipment, emergency-room operation, departments, specialists, parking, or transport.
- This is not a duplicate of existing `hira_hospital_search`: the existing adapter finds candidate institutions, while this API answers detailed facility/resource questions for a selected institution.
- Personal-data risk: low. The API exposes institutional facility/resource data, not patient records. It does use an encrypted institution identifier `ykiho`, which must remain opaque.
- Limitation: most operations require `ykiho`; UMMAYA should obtain it from the official HIRA hospital basis list rather than guessing or decoding it.

## Official contract snapshot

- Host: `apis.data.go.kr/B551182/MadmDtlInfoService2.7`
- Common query parameters: `serviceKey`, `ykiho`, `pageNo`, `numOfRows`, `_type`
- Operations:
  - `GET /getSpclDiagInfo2.7` - special diagnosis/treatment fields
  - `GET /getTrnsprtInfo2.7` - transport information
  - `GET /getDtlInfo2.7` - operating hours, emergency-room flags, parking, reception, holiday closure
  - `GET /getEqpInfo2.7` - facility and bed-count information
  - `GET /getSpcSbjtSdrInfo2.7` - specialist count by specialty
  - `GET /getDgsbjtInfo2.7` - department/subject information
  - `GET /getMedOftInfo2.7` - medical equipment information
  - `GET /getFoepAddcInfo2.7` - meal surcharge information
  - `GET /getNursigGrdInfo2.7` - nursing grade information
  - `GET /getSpclHospAsgFldList2.7` - designated specialty hospital fields
  - `GET /getEtcHstInfo2.7` - other workforce counts

## Application attempt result

Portal duplicate. After clicking `활용신청` on 2026-05-16, data.go.kr returned `이미 신청 된 데이터입니다.` and redirected to the utilization application status page.

This API remains a strong UMMAYA fit and the official inline Swagger/specification was saved, but it is not counted as a new additional utilization application for the current 100-new-API goal.
