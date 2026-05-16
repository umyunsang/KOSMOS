# Pre-Application Screening: data.go.kr API 15063444

## Work Unit

- Unit: 11
- Date: 2026-05-16
- Portal ID: 15063444
- API name: 경상남도 의령군_민방위대피시설
- Provider: 경상남도 의령군
- Portal URL: https://www.data.go.kr/data/15063444/openapi.do
- Application status: submitted and approved
- Application reference: 115977808
- UDDI: uddi:9a5cde40-8d6f-4999-8a7a-a128db9c0701

## Reference Bootstrap

- UMMAYA thesis/docs: UMMAYA wraps one agency LLM-callable module as one tool and exposes citizen-facing primitives for Korean public-service infrastructure.
- Adapter/API sources: data.go.kr detail page, schema.org metadata, DCAT metadata, and provider OpenAPI guide saved in this directory.
- Official endpoint source: saved provider guide and DCAT endpoint URL.
- Implementation constraints: no hardcoded service key; live credentials stay out of committed files; live API calls must not run in CI.
- Unknowns: no live credential probe performed in this intake step because the goal is discovery, application, and documentation capture.

## Selection Rationale

This API is a good UMMAYA candidate because it answers immediate disaster-safety questions with official location data.

- Citizen query: "의령군에서 가까운 민방위 대피시설 어디야?"
- Citizen query: "이 대피소 수용인원과 개방여부 알려줘."
- Citizen query: "군민회관 민방위 대피시설 주소랑 관리기관 전화번호 찾아줘."
- UMMAYA primitive fit: `resolve_location` for location-grounded shelter lookup; `lookup` can support facility-name lookup.
- Adapter behavior: query by shelter name or page through all records, then return address, coordinates, area, capacity, open status, normal-use type, manager, manager phone, and data date.
- Expected use: regionally medium during weather, civil-defense, earthquake, fire, or evacuation events; low-to-medium during normal periods for preparedness checks.

The dataset is local rather than national, but it has high citizen value for users physically in or planning travel to Uiryeong-gun. It also has a clean one-operation shape suitable for a small UMMAYA adapter and map-linked responses.

## Application Evidence

- My Page shows `[승인] 경상남도 의령군_민방위대피시설`.
- Application date: 2026-05-16
- Expiry date: 2028-05-16
- Development account traffic: 1,000 requests/day
- Approval flow: automatic approval
- License: 이용허락범위 제한 없음

