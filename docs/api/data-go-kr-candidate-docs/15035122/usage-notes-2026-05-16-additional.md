# 과학기술정보통신부 우정사업본부_우체국 종적 조회

- Source: <https://www.data.go.kr/data/15035122/openapi.do>
- Additional batch: `SCOPED-ADDITIONAL-30-2026-05-16`
- Main-page discovery axis: `category` = `과학기술`
- Category/provider: `과학기술` / `국가행정기관`
- Provider: `과학기술정보통신부 우정사업본부`
- UMMAYA primitive candidate: `check`
- Application status: `not_submitted_confirmation_required`

## Captured Artifacts

- `data-go-kr-detail.html`
- `intake-record-additional-2026-05-16.json`
- `기술문서양식_우정사업본부_통합배송조회_20190311.docx`

## Adapter-Relevant Contract

- Swagger title: 과학기술정보통신부 우정사업본부_우체국 종적 조회
No machine-readable operation was captured. Use the saved detail page/reference document as the source of truth before implementation.
## Wrapping Notes

- Default adapter mode: `Live` only after a direct sanitized `curl` probe proves the documented endpoint, key name, required params, success response, and zero-result shape. Until then this is an intake candidate only.
- Expected auth: data.go.kr `serviceKey` unless the captured detail page says this is a LINK/external portal API.
- CI rule: never call this live endpoint from CI tests; fixtures must be recorded locally and sanitized.
- Permission policy: later adapter docs must cite the official data.go.kr detail page and any provider policy page rather than inventing a UMMAYA-specific classification.
- Application submission note: clicking `활용신청` or submitting the request creates or changes a data.go.kr usage application/API-access record, so it needs explicit action-time confirmation before I operate that UI.
