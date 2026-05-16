# Unit 15 Pre-Application Screening

- Candidate: `15157820` `중소벤처기업부_중소기업 지원사업 공고 조회 서비스`
- Portal URL: `https://www.data.go.kr/data/15157820/openapi.do`
- Provider: `중소벤처기업부`
- Classification: `산업·통상·중소기업 - 산업·중소기업일반`
- API type: REST
- Data formats: JSON, XML
- Update cycle: daily
- Traffic shown by portal: development account `10,000/day`; operating-account traffic can be increased after use-case registration.
- Review type shown by portal: development `automatic approval`; operating `review approval`.
- Spatial scope: Korea nationwide
- Time scope: current year
- Portal license display: detail page showed `공공저작물 : 출처표시, 변경금지 (제 3유형)` while the application form license row displayed `이용허락범위 제한 없음`; adapter documentation should preserve source attribution and avoid mutating official notice text.

## UMMAYA Fit

This is a strong `lookup` primitive candidate for UMMAYA because small-business and SME support notices are recurring, citizen-facing administrative demand. The API exposes notice title, target, support field, application period, application method, inquiry contact, notice URL, and application URL, so a wrapper can answer eligibility and timing-oriented search queries without inventing policy content.

Natural-language queries this API can support:

- `내 업종에 맞는 정부 지원사업 찾아줘`
- `소상공인이 지금 신청할 수 있는 지원 공고 알려줘`
- `중소기업 기술개발 지원사업 중 신청기간 남은 것 찾아줘`
- `이 공고ID의 신청방법과 문의처 알려줘`
- `최근 수정된 중소기업 지원사업 공고만 보여줘`

## Adapter Mapping

- UMMAYA primitive: `lookup`
- Adapter intent: SME and small-business support notice lookup.
- Main user value: discover public support programs by field, hashtag, notice ID, registration date, update date, target, application period, contact, and application URL.
- Expected usage frequency: medium to high for business owners and sole proprietors because support-program discovery is seasonal, deadline-driven, and query-rich. The displayed 10,000/day development quota is sufficient for prototype use and likely enough for a controlled public demo.

## Official Contract Summary

- Base URL: `https://apis.data.go.kr/1421000/bizinfo`
- Operation: `GET /pblancBsnsService`
- Required query parameter: `serviceKey`
- Optional query parameters: `dataType`, `pageNo`, `numOfRows`, `searchLclasId`, `hashtags`, `pblancId`, `registDe`, `updtPnttm`
- Response fields suitable for answer generation: `pblancNm`, `pblancUrl`, `pblancId`, `jrsdInsttNm`, `excInsttNm`, `bsnsSumryCn`, `pldirSportRealmLclasCodeNm`, `creatPnttm`, `reqstBeginEndDe`, `updtPnttm`, `trgetNm`, `inqireCo`, `hashtags`, `reqstMthPapersCn`, `refrncNm`, `rceptEngnHmpgUrl`

## Decision

Selected and submitted for use.
