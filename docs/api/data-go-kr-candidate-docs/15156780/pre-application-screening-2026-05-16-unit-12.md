# Unit 12 pre-application screening: data.go.kr API 15156780

## Candidate

- Portal ID: `15156780`
- API name: `인사혁신처_공공취업정보 조회 서비스`
- Portal URL: `https://www.data.go.kr/data/15156780/openapi.do`
- Provider: `인사혁신처`
- Classification: `사회복지 - 고용노동`
- Format: `XML`
- Type: `REST`
- Update cadence: real time
- License: no usage restriction

## UMMAYA fit decision

Decision: apply and keep as a UMMAYA `lookup` adapter candidate.

Rationale: this is a national public-sector employment information channel backed by the Ministry of Personnel Management and the `나라일터` public-job feed. It can answer high-frequency citizen requests without agency-site hopping, especially for public-service job seekers who search by agency, public-job type, region, keyword, deadline, and detail attachments.

## Citizen natural-language coverage

- "Find open central-government hiring notices for administrative jobs."
- "Show public-institution job notices that close this week."
- "Find 채용 notices from a specific ministry or local government."
- "Open the detail and attached files for this public-job notice."
- "What grades or job classes are available for this hiring notice?"

## Primitive mapping

- Primary primitive: `lookup`
- Secondary primitive: `submit` is not used for the initial adapter because this API only exposes job information lookup, not application submission.

## Wrapping sketch

The adapter should normalize the citizen's natural-language constraints into `getList` query parameters, return ranked job notices, and use `idx` to enrich a selected notice through `getItem`, `getItemPosition`, and `getItemFile`.

Natural-language query to API mapping:

- agency or institution name -> `Instt_nm`
- national/local/public-institution class -> `Instt_se`
- notice type or employment type -> `Pblanc_ty`
- registration date window -> `Begin_de`, `End_de`
- free-text role or policy keyword -> `Kwrd`
- latest-first ordering -> `Sort_order`
- notice identifier -> `idx`

## Expected usage

Expected usage is medium to high for UMMAYA because public employment is a recurring citizen task, the data is real time, and each conversation may need one list lookup plus one to three detail/file lookups. The development account traffic of 10,000 calls per day per operation is enough for prototype use and fixture capture.

## Application result

- Submitted through Computer Use on data.go.kr.
- My Page status after submission: `[승인] 인사혁신처_공공취업정보 조회 서비스`
- Application date: `2026-05-16`
- Expiry date: `2028-05-16`
- Application reference: `115978222`
- UDDI: `uddi:19c9d3b4-ad5b-4c12-ac11-9a483efdb028_202512300006`
