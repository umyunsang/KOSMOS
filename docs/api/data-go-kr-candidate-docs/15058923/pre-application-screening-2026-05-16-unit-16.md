# Unit 16 Pre-Application Screening

- Candidate: `15058923` `축산물품질평가원_축산물통합이력정보`
- Portal URL: `https://www.data.go.kr/data/15058923/openapi.do`
- Provider: `축산물품질평가원`
- Classification: `농림 - 임업·산촌`
- Category seen from portal navigation: `농축수산`
- API type: REST
- Data format: XML
- Update cycle: realtime
- Traffic shown by portal: development account `10,000/day`; operating-account traffic can be increased after use-case registration.
- Review type shown by portal: development `automatic approval`; operating `automatic approval`.
- Portal license display: `이용허락범위 제한 없음`

## Reference Bootstrap

- UMMAYA thesis/docs: `docs/vision.md`, `docs/requirements/ummaya-migration-tree.md`, `docs/onboarding/codex-continuation.md`
- Adapter/API sources: `docs/api/README.md`, public-data portal detail page, downloaded DOCX guide
- External primary sources: data.go.kr detail page and `축산물품질평가원_OpenAPI활용가이드_축산물통합이력정보조회_v2.10.docx`
- CC restored-source files: not directly touched; this unit is candidate intake/application only, not runtime behavior.
- Unknowns or blocked evidence: live credential request was not probed; adapter implementation must run direct sanitized `curl` validation before claiming live contract behavior.

## UMMAYA Fit

This is a strong `lookup` and `verify` primitive candidate because livestock traceability is a citizen-facing safety and provenance question. The API maps an entered livestock trace number or bundle number to farming, movement, slaughter, packaging, inspection, grade, and distribution fields. That lets UMMAYA answer natural consumer queries without guessing from unstructured text.

Natural-language queries this API can support:

- `이 쇠고기 이력번호 조회해줘`
- `돼지고기 묶음번호로 도축장과 포장처리업소 확인해줘`
- `이 축산물 등급과 도축일자 알려줘`
- `닭/오리/계란 이력번호로 농장과 검사 결과 확인해줘`
- `이 고기 묶음번호에 포함된 개체 이력들을 확인해줘`

## Adapter Mapping

- UMMAYA primitive: `lookup`
- Secondary primitive fit: `verify`
- Adapter intent: livestock traceability lookup and provenance verification.
- Main user value: convert a trace number or bundle number into official supply-chain facts such as farm, farmer/manager, birth or registration date, slaughterhouse, slaughter date, inspection result, grade, processor, packaging date, and trace-number type.
- Expected usage frequency: medium. Queries are occasional but high-intent, likely around grocery purchases, food-safety incidents, catering/procurement checks, and consumer complaint scenarios. The `10,000/day` development quota is far above expected prototype demand.

## Official Contract Summary

- Endpoint: `GET http://data.ekape.or.kr/openapi-data/service/user/animalTrace/traceNoSearch`
- Required query parameters from portal table: `traceNo`, `serviceKey`
- Optional query parameters from portal table: `optionNo`, `corpNo`
- DOCX examples use `ServiceKey` casing while the portal table lists `serviceKey`; the live adapter must confirm accepted casing with direct `curl` before final implementation.
- `optionNo` values:
  - `1`: cattle individual / pig raising information
  - `2`: cattle birth and reporting information
  - `3`: cattle/pig slaughter information
  - `4`: cattle/pig packaging information
  - `5`: cattle foot-and-mouth vaccine information
  - `6`: cattle disease information
  - `7`: cattle brucellosis information
  - `8`: bundle basic information
  - `9`: bundle composition detail
- Trace-type coverage shown by DOCX examples: `CATTLE/CATTLE_NO`, `CATTLE/LOT_NO`, `PIG/PIG_NO`, `PIG/LOT_NO`, `FOWL/HIST_NO`, `DUCK/HIST_NO`, `EGG/HIST_NO`, `FOWL/LOT_NO`, `DUCK/LOT_NO`
- Response fields suitable for answer generation include `traceNoType`, `infoType`, `birthYmd`, `farmAddr`, `farmerNm`, `mngrNm`, `farmNo`, `farmUniqueNo`, `cattleNo`, `pigNo`, `histNo`, `lotNo`, `lsTypeNm`, `sexNm`, `butcheryPlaceNm`, `butcheryPlaceAddr`, `butcheryYmd`, `gradeNm`, `inspectPassYn`, `processPlaceNm`, `processPlaceAddr`, `processYmd`, `corpNo`, `resultCode`, and `resultMsg`.

## Decision

Selected and submitted for use.
