# Pre-Application Screening: Unit 09

- Dataset: `15038392`
- Title: `한국대학교육협의회_대학알리미 재정 현황`
- Portal URL: `https://www.data.go.kr/data/15038392/openapi.do`
- Provider: `한국대학교육협의회`
- Classification: `교육 - 고등교육`
- Candidate adapter id: `kcue_academyinfo_finance_lookup`
- Candidate primitive: `lookup`
- Screening result: pass

## UMMAYA Fit

This API can support citizen and student queries about university finance indicators such as tuition, scholarship benefit status, student-loan counts, and per-student education investment. It fits UMMAYA because users commonly ask comparative higher-education questions in natural language before admissions, transfer, financial-aid, or family budgeting decisions.

Natural-language query mapping:

- `연세대 등록금 현황 알려줘.` -> resolve university name to `schlId`, call the finance endpoint with `svyYr` and `schlId`, return official indicator values.
- `OO대 장학금 수혜 현황이 어때?` -> use the finance-service scholarship operation documented in the DOCX guide when exposed by the issued key.
- `이 대학 학자금 대출 학생 수 확인해줘.` -> use the finance-service loan operation documented in the DOCX guide when exposed by the issued key.

Expected use frequency: moderate to high during university admissions and scholarship seasons. It is not a daily emergency API, but it has strong recurring demand from students, parents, counselors, and policy evaluators.

## Contract Notes Before Application

- Portal-listed service URL: `http://openapi.academyinfo.go.kr/openapi/service/rest/FinancesService/getComparisonTuitionCrntSt`
- Portal request parameters: `ServiceKey` required, `schlId` required, `svyYr` required, `pageNo` optional, `numOfRows` optional.
- Portal response fields include `resultCode`, `resultMsg`, `numOfRows`, `pageNo`, `totalCount`, `Items`, `Item`, `indctId`, `indctVal1`, `schlDivNm`, `schlEstbNm`, `schlId`, `schlKrnNm`, `svyYr`.
- The downloaded DOCX guide is broader than the portal operation table. It documents `FinancesService` operations for tuition, scholarship benefit status, educational expense reduction, student-loan status, and student-loan use ratios. The first adapter cut should pin the page-listed operation and record the broader DOCX operations as expansion candidates after live key validation.

## Application Purpose

`UMMAYA R&D. Build citizen university finance lookup adapter for tuition, scholarship, student-loan, and education-investment questions using official AcademyInfo data. Cite agency source. No resale.`
