# Pre-application screening: data.go.kr 15140950

- Unit: 17
- Checked at: 2026-05-16 KST
- Portal URL: https://www.data.go.kr/data/15140950/openapi.do
- API: 헌법재판소_발간자료 조회 서비스
- Provider: 헌법재판소
- Category source: data.go.kr main category `법률`
- Detail classification: 공공질서및안전 - 법무및검찰
- Data format: JSON+XML
- API type: REST
- License: 이용허락범위 제한 없음 / 공공저작물 출처표시 제1유형
- Review: development account automatic approval; operating account requires review

## Selection decision

Selected for UMMAYA as a `lookup` primitive candidate.

Citizen natural-language queries this adapter can answer:

- "헌법재판소에서 발간한 기본권 관련 자료 찾아줘."
- "헌재 발간문헌 중 선거제도 관련 문헌 제목과 저자 알려줘."
- "헌법재판소 연속간행물 중 최근 자료의 원문 링크가 있어?"
- "이 문헌일련번호로 헌재 발간문헌 상세 메타데이터를 조회해줘."

The API fits UMMAYA because it exposes an official national legal-information channel where citizens can search Constitutional Court publications and retrieve detail records using stable identifiers. It does not perform legal advice or filing; it supports evidence-grounded retrieval for legal, civic, education, and policy-literacy questions.

## UMMAYA wrapping logic

- Primitive: `lookup`
- Adapter role: search and retrieve Constitutional Court publication and serial-publication metadata.
- Query mapping:
  - Natural-language topic/title query -> `getSerialPublicationList` or `getPblctLtrtreList`
  - Result identifier -> `getSerialPublicationDetail` or `getPblctLtrtreDetail`
- Response shaping:
  - Return title, author/reporter, series/book, publication date, section, volume info, content, image/file links, and source citation.
  - Include the exact operation and query parameters used for transparency.
- Expected use pattern:
  - Low-to-medium citizen frequency, but high trust value for constitutional/legal research requests.
  - Likely bursts around civic education, litigation news, school assignments, policy explainers, and constitutional-rights questions.

## Risk notes

- This is a reference lookup tool, not a legal-advice or court-filing tool.
- Live adapter must require `serviceKey`; no hardcoded keys.
- Public API endpoint and parameter casing must be verified with direct `curl` before any live adapter claim.
- `fileLink1` and `fileLink2` should be treated as external source links and cited as returned, not transformed into legal interpretations.

## Application action

- Submitted through the data.go.kr browser UI with Computer Use.
- Purpose submitted: `UMMAYA 법률자료 lookup 어댑터: 제목, 저자, 내용으로 헌법재판소 발간문헌과 연속간행물을 검색하고 식별자로 원문 링크와 상세 메타데이터를 조회해 시민 법률정보 질의에 대응.`
- All four detail functions remained selected.
- License agreement checkbox was selected.
- Final confirmation dialog `신청하시겠습니까?` was confirmed.

