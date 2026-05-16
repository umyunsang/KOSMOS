# Unit 14 pre-application screening: data.go.kr API 15158905

## Candidate

- Portal ID: `15158905`
- API name: `한국예탁결제원_금융용어조회서비스_GW`
- Portal URL: `https://www.data.go.kr/data/15158905/openapi.do`
- Provider: `한국예탁결제원`
- Classification: `일반공공행정 - 재정·금융`
- Category seen: `재정금융`
- Format: `XML`
- Type: `REST`
- Update cadence: real time
- License: `저작자표시-비영리`; public-work type 2, source attribution required, commercial use prohibited

## UMMAYA fit decision

Decision: apply and keep as a UMMAYA `lookup` adapter candidate.

Rationale: this API exposes an official financial-terms dictionary from Korea Securities Depository. It is not a transaction channel, but it is a strong UMMAYA support adapter because many citizen-facing administrative and financial queries contain terms that block understanding before the citizen can act. A `lookup` wrapper can explain securities, bonds, disclosure, settlement, and market infrastructure terms using an official source instead of free-form model memory.

## Citizen natural-language coverage

- "대량주식 보유상황 공시제도가 무슨 뜻이야?"
- "Repo가 뭔지 공공기관 자료 기준으로 설명해줘."
- "채권 원리금 확정이라는 표현을 쉽게 풀어줘."
- "전자등록, 보호예수, 의무보유등록 차이를 알려줘."
- "공시 문서에 나온 금융용어 뜻을 공식 정의로 찾아줘."

## Primitive mapping

- Primary primitive: `lookup`
- Secondary primitive: none for the initial adapter. The API returns term definitions only and does not submit, verify identity, subscribe, or mutate records.

## Wrapping sketch

The adapter should map a citizen's finance-term question to the single lookup operation:

1. Extract the target term from the citizen query.
2. Normalize synonyms and surrounding phrases into a concise `term` query.
3. Call `/getFinancialTermMeaning` with `serviceKey`, `term`, and optional pagination.
4. Strip or sanitize HTML tags from `ksdFnceDictDescContent` before returning the answer.
5. Return the official term name, official description, result count, and source citation.

Natural-language query to API mapping:

- financial term phrase -> `term`
- paging request such as "more results" -> `pageNo`
- result-size preference -> `numOfRows`

## Expected usage

Expected usage is medium-high as a support adapter. It is not an everyday standalone service like welfare, jobs, or health, but it can be invoked frequently inside multi-step financial, tax, securities, procurement, and disclosure conversations. The development traffic limit is 100 calls per day, so the prototype should cache fixture responses for common terms and avoid live CI calls.

## Application result

- Submitted through Computer Use on data.go.kr.
- My Page status after submission: `[승인] 한국예탁결제원_금융용어조회서비스_GW`
- Application date: `2026-05-16`
- Expiry date: `2028-05-16`
- Application reference: `115979053`
- UDDI: `uddi:4dc039b9-381f-4edd-9c15-cdc4a89c91e8_202604131639`
- Submitted purpose: `UMMAYA lookup adapter: financial term dictionary for citizen queries about securities, bonds, disclosure, settlement, and market terminology.`
