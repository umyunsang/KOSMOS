# Usage Notes: Unit 09

- Dataset: `15038392`
- Title: `한국대학교육협의회_대학알리미 재정 현황`
- Portal URL: `https://www.data.go.kr/data/15038392/openapi.do`
- Provider: `한국대학교육협의회`
- Classification: `교육 - 고등교육`
- Department/contact: `대학정보공시센터`, `02-6919-3891`
- Data format: XML
- License: `이용허락범위 제한 없음`
- Approval status: submitted via data.go.kr and listed as `[승인]` in My Page on `2026-05-16`
- Application reference: `115976918`
- Expiry shown by portal: `2028-05-16`

## UMMAYA Adapter Fit

Candidate adapter id: `kcue_academyinfo_finance_lookup`

Candidate primitive: `lookup`

This is a good UMMAYA candidate because it answers common citizen and household questions about university affordability: tuition, scholarships, education investment per student, student-loan status, and student-loan usage ratio. The likely users are students, parents, school counselors, admissions consultants, and policy evaluators. Demand is expected to be moderate overall and high during admissions, scholarship, transfer, and enrollment-payment seasons.

Natural-language mapping:

- `연세대 등록금 현황 알려줘.` -> resolve `연세대` to an AcademyInfo `schlId`, call `FinancesService/getComparisonTuitionCrntSt` with `svyYr` and `schlId`, then return official tuition indicators.
- `OO대 장학금 수혜 현황이 어때?` -> resolve the university, call the scholarship operation documented in the DOCX guide, then summarize official scholarship benefit fields.
- `이 대학 학자금 대출 이용 비율 확인해줘.` -> call the student-loan usage-ratio operation and explain the official ratio by year and school.
- `부산 지역 대학 등록금 비교해줘.` -> use the regional operation family with `schlDivCd` and regional response fields, then rank or compare results with source citation.

## Primary Operation

Portal-listed endpoint:

`http://openapi.academyinfo.go.kr/openapi/service/rest/FinancesService/getComparisonTuitionCrntSt`

Request parameters listed by the portal:

- `ServiceKey` or `serviceKey`: required service key. The portal table uses `ServiceKey`; the DOCX examples use `serviceKey`.
- `schlId`: required school id. Portal sample: `0000149`.
- `svyYr`: required disclosure year. Portal sample: `2018`.
- `pageNo`: optional page number. Portal sample: `1`.
- `numOfRows`: optional rows per page. Portal sample: `999`.

Response fields listed by the portal:

- Envelope/page fields: `resultCode`, `resultMsg`, `numOfRows`, `pageNo`, `totalCount`, `Items`, `Item`.
- Item fields: `indctId`, `indctVal1`, `schlDivNm`, `schlEstbNm`, `schlId`, `schlKrnNm`, `svyYr`.

Useful code-resolution endpoint from the DOCX guide:

`http://openapi.academyinfo.go.kr/openapi/service/rest/BasicInformationService/getUniversityCode`

The guide shows `getUniversityCode` accepting fields such as `svyYr`, `schlId`, `schlKrnNm`, `clgcpDivCd`, `schlDivCd`, `schlKndCd`, `znCd`, and `estbDivCd`. The adapter should use this lookup path to turn Korean university names into `schlId` before calling finance operations.

## Broader Finance Operations In Downloaded DOCX

The downloaded guide documents the broader `FinancesService` family:

- `getComparisonTuitionCrntSt`
- `getRegionalTuitionCrntSt`
- `getComparisonScholarshipBenefitCrntSt`
- `getRegionalScholarshipBenefitCrntSt`
- `getRegionalEducationalExpensesReductionCrntSt`
- `getComparisonEducationExpensesLoanCrntSt`
- `getRegionalEducationExpensesLoanCrntSt`
- `getComparisonEducationExpensesLoanUseStudentRatioTuition`
- `getRegionalEducationExpensesLoanUseStudentRatioTuition`

The first live adapter should start with the portal-listed `getComparisonTuitionCrntSt` contract, then expand only after validating that the issued key can call the additional DOCX-documented operations. The DOCX appears to repeat `getComparisonTuitionCrntSt` in one education-expense comparison example, so implementation should verify the exact operation names by direct curl probes after key activation.

## Saved Evidence And Documents

- `data-go-kr-detail.html`: saved portal detail page.
- `openapi-schemaorg.json`: saved schema.org metadata JSON.
- `dcat-metadata.rdf.xml`: saved DCAT metadata. The portal endpoint returns RDF/XML, not JSON.
- `gateway_swagger_guide.pdf`: saved generic gateway Swagger guide.
- `IROS4_OA_DV_0401_OpenAPI활용가이드_25.한국대학교육협의회(대학공시정보)_v2.00.docx`: saved official DOCX guide.
- `IROS4_OA_DV_0401_OpenAPI활용가이드_25.한국대학교육협의회(대학공시정보)_v2.00.docx.txt`: extracted DOCX text for search.
- `pre-application-screening-2026-05-16-unit-09.md`: selection rationale before submission.
- `intake-record-unit-09-2026-05-16.json`: machine-readable intake record.

## Caveats

- The portal completion dialog says the applied API may take `1~2` hours to become callable, and some APIs may take up to 24 hours.
- The portal shows a generic location-information warning on the application form. This dataset is university finance data, but the warning should still be recorded as part of the application-page evidence.
- Do not put the issued service key in source files or fixtures.
