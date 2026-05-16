# Pre-Application Screening - Unit 02

## Candidate

- Public data ID: `15073554`
- Title: `행정안전부_안전정보 통합공개 조회 서비스`
- Provider: `행정안전부`
- Category: `재난안전`
- Classification: `공공질서및안전 - 안전관리`
- Detail URL: `https://www.data.go.kr/data/15073554/openapi.do`
- Base URL: `https://apis.data.go.kr/1741000/FcltsSafetyInfoService2025`
- Primary primitive: `find`
- Supporting primitive: `locate`
- Candidate tool ID: `mois_facility_safety_info_lookup`
- Screening result: pass.
- Application attempt result: duplicate. The portal returned `이미 신청 된 데이터입니다.` on 2026-05-16, so this candidate is not counted as a new additional usage application.

## Why This API Is UMMAYA-Relevant

The API exposes official safety inspection and diagnosis information for facilities collected through the national safety-information disclosure system. It can answer citizen questions about whether a specific public-use facility has recent safety inspection results, findings, grades, or follow-up actions. This is a national safety infrastructure lookup, not an aggregate statistics dataset.

Expected usage/frequency inference:

- Frequency: medium-high. Parents, caregivers, travelers, patients, tenants, students, and local residents can naturally ask about schools, childcare centers, hospitals, hotels, theaters, public facilities, and other multi-use facilities.
- Strategic value: high. It fills a safety-disclosure gap in the current adapter catalog and supports the target-state UMMAYA scenarios around disaster/safety, caregiving, education, health, housing, and travel.
- Adapter quality: high enough to apply. The API provides a facility-search operation that returns `fcltyCd`, then detail operations consume that official facility key. This creates a defensible two-step tool flow.

## Citizen Query Reasoning Table

| Citizen query | UMMAYA interpretation | API operation and parameters | Official fields returned | Citizen-facing answer |
|---|---|---|---|---|
| `우리 아이가 다니는 어린이집 안전점검 결과 확인해줘.` | The citizen is asking for official safety results for a named childcare facility. Use `locate` only if the citizen provides an address instead of legal-dong codes. | Step 1: `GET /getFcltsInfoSearch_4` with `serviceKey`, `resultType=json`, `fclts_nm=<어린이집명>`, optional `ldong_addr_mgpl_dg_cd`, `ldong_addr_mgpl_sggu_cd`, `ldong_addr_mgpl_sggu_emd_cd`. Step 2: `GET /getCrSafetyInfoSearch_4` with `serviceKey`, `resultType=json`, `fclts_cd=<fcltyCd>`. | Facility search returns `fcltyNm`, `lnmadr`, `latitude`, `longitude`, `fcltyCd`, `seCd`. Childcare safety returns `category`, `chck_start_ymd`, `chck_end_ymd`, `chck_dtls_type`, `chck_inst_nm`, `chck_rslt_safe_grad`, `chck_compt_ymd`, `chck_fllw_managt`, `chck_rslt_cn`, `insrnc_kind`. | UMMAYA can say which matched childcare facility was found, show its address, then summarize the official inspection period, inspection type, result/grade, findings, follow-up management, and action result. |
| `이번에 예약한 호텔 안전점검이나 등급 유효기간 확인해줘.` | The citizen is deciding whether to use a hotel and needs official safety/disclosure information. | Step 1: `GET /getFcltsInfoSearch_4` with `fclts_nm=<호텔명>` and optional location codes. Step 2: `GET /getHotelSafetyInfoSearch_4` with `fclts_cd=<fcltyCd>`. | Hotel safety returns `hotelnmkorean`, `hotelnmeng`, `hotelrumco`, `decsngrad`, `hotelinduty`, `trindsryceregrtpblictnplc`, `allrdnmadr`, `telno`, `hotelhmpgadres`, `gradvalidpdbeginde`, `gradvalidpdendde`, `category`, `chck_start_ymd`, `chck_end_ymd`, `chck_dtls_type`, `chck_inst_nm`, `chck_rslt_safe_grad`, `chck_fllw_managt`, `chck_rslt_cn`, `lnmadres`, `zip`. | UMMAYA can return the matched hotel, official address/contact, grade and validity dates, and the latest documented inspection result and follow-up content. It must not infer current commercial quality beyond the official fields. |
| `근처 공연장이나 다중이용시설에 최근 안전 지적사항이 있었는지 알려줘.` | The citizen wants public-use facility safety results near a location. | Step 1: use `locate` to normalize the address into legal-dong codes. Step 2: `GET /getFcltsInfoSearch_4` with optional legal-dong codes and a facility name/type if provided. Step 3: for a chosen result, call `GET /getMultiUseFacilitySafetyInfoSearch_4` or `GET /getConcerthallSafetyInfoSearch_4` with `fclts_cd`. | Facility search returns name/address/location/key/type. Detail endpoints return `category`, `chck_start_ymd`, `chck_end_ymd`, `chck_dtls_type`, `chck_inst_nm`, `chck_rslt_safe_grad`, `chck_compt_ymd`, `chck_fllw_managt`, `chck_rslt_cn`. | UMMAYA can list matched nearby facilities and, after selection or disambiguation, summarize official inspection result, findings, and follow-up. If multiple facilities match, it should ask the citizen to choose before presenting a specific facility's result. |
| `부모님 장기요양시설 안전점검 결과를 확인해줘.` | The citizen is checking safety disclosure for a long-term care facility. | Step 1: `GET /getFcltsInfoSearch_4` with facility name and optional location codes. Step 2: `GET /getLongTermCareSafetyInfoSearch_4` with `fclts_cd`. | Detail endpoint returns common safety fields including `chck_start_ymd`, `chck_end_ymd`, `chck_dtls_type`, `chck_inst_nm`, `chck_rslt_safe_grad`, `chck_fllw_managt`, `chck_rslt_cn`. | UMMAYA can provide the latest official safety inspection summary for the selected long-term care facility and cite the data.go.kr source. |

## Proposed Adapter Flow

1. Parse the citizen request into `facility_name`, optional `facility_type`, and optional address or region.
2. If the request includes an address, call `locate` to obtain legal-dong code components where possible.
3. Call `GET /getFcltsInfoSearch_4` to retrieve candidate facilities and the official `fcltyCd`.
4. If multiple facilities match, ask the citizen to choose. Do not guess silently.
5. Route by facility type or user-selected type to the detail operation, such as `getCrSafetyInfoSearch_4`, `getScleqipSafetyInfoSearch_4`, `getHotelSafetyInfoSearch_4`, `getHospitalSafetyInfoSearch_4`, `getMultiUseFacilitySafetyInfoSearch_4`, `getConcerthallSafetyInfoSearch_4`, or `getLongTermCareSafetyInfoSearch_4`.
6. Return only official fields: inspection date range, inspection type, target name, result/grade, findings, follow-up management, and action result.

## Rejection Checks

- Not a pure statistics dataset: pass.
- Not promotional/media content: pass.
- Has meaningful parameters: pass. Facility search supports `fclts_nm`, `gp_cd`, and legal-dong region codes; detail operations require official `fclts_cd`.
- Maps to primitive: pass as `find`, with `locate` for address normalization.
- Citizen actionability: pass. Results can guide whether a citizen needs more inquiry, chooses a facility, or asks for an official handoff.
- Privacy risk: low for lookup because returned data is facility-level public safety information, not citizen personal records.
