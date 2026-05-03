# Phase 0 Research: Tool surface v4

**Date**: 2026-05-03
**Status**: Complete
**Spec**: [spec.md](./spec.md)

## Reference Mapping (AGENTS.md hard rule: each design decision → reference)

### v4 design decision 별 reference 매핑

| Design decision | Primary reference | Secondary reference | Rationale |
|---|---|---|---|
| 도구 input schema agency contract 보존 (alias / 통일 X) | `docs/vision.md` § Tool System (Pydantic AI 패턴) | 사용자 디렉티브 (2026-05-03) "통일 X / 도메인 독립" | LangChain / LlamaIndex / Semantic Kernel 모두 input schema 도메인 별 다양성 허용. 통일은 도메인 독립 위반. |
| Description 5-섹션 골격 + 17 광역시도 short reference 인라인 | Anthropic 공식 (≥3-4문장, niche terminology 명시) | Semantic Kernel `[Description("""enum:""")]` 패턴 + MCP-Smelly 2026 (+5.85pp success / 16.67% regression 균형) | description 인라인 = LLM-visible context, 정적 dict 보다 효과 (deep research Agent A·B·C 만장일치). |
| Cross-domain auto-chain 제거 (`models.py:577` 정정) | Anthropic Engineering "Writing tools for agents" — "self-contained" + "do not chain" | 사용자 디렉티브 "chain X" + Google 2025 scaling paper (multi-agent sequential 39-70% 저하) | Spec 2521 회귀의 직접 원인 — 잘못된 LLM 지시가 K-EXAONE 의 chain 시도 유발 + 실패. |
| Mirror reference dict (`grid_coords.py:REGION_TO_GRID` 등) KOSMOS 코드 안 보존 | AGENTS.md hard rule "Korean domain data is the only exception" | 사용자 디렉티브 정정 (2026-05-03) "미러 허용 — reimplementation 의미가 아니었음" | Software Architect reviewer 의 "data 분리도 status-quo refactor" 비판 정합. 분리 비용 < 효과. |
| `kma_pre_warning` endpoint `getPreWrnList` → `getWthrWrnList` | `/tmp/kosmos-evidence/kma-evidence.md` (2026-05-03 live 측정 — 404 vs 200) | KMA OpenAPI 활용가이드 (`/tmp/kosmos-domain-docs/kma_asos.txt` § endpoint 설명) | 단순 typo, evidence 명확. |
| `kma_weather_alert_status` stn_id/tmFc 필수 + autonomous chain 명시 | `/tmp/kosmos-evidence/kma-evidence.md` (resultCode=11 NO_MANDATORY_REQUEST_PARAMETERS_ERROR) | spec.md FR-009 | LLM autonomous turn 1 = pre_warning, turn 2 = alert_status (chain 강제 X, description 으로 권장만). |
| `hira_hospital_search` `_type=json` (param 명) | `/tmp/kosmos-evidence/medical-evidence.md` (3 형식 비교 측정) | HIRA OpenAPI 활용가이드 (`/tmp/kosmos-domain-docs/hira.txt` § 응답 메시지 명세) | type=json / dataType=JSON 모두 XML 반환 (ignored), `_type=json` 만 정답. |
| `nmc_emergency_search` URL encoding 자동화 | `/tmp/kosmos-evidence/medical-evidence.md` (HTTP 400 → 200 with urlencode) | `httpx.params={}` 패턴 (httpx 공식 docs) | "STAGE1=서울특별시" 직접 string interpolation 시 한국어 미인코딩 → HTTP 400. params dict 사용 시 자동 인코딩. |
| KOROAD siDo/guGun 2+3-digit (4-digit 아님) | `/tmp/kosmos-evidence/koroad-mohw-evidence.md` (4-digit 1100/1116 NODATA, 2+3 digit 11/680 LIVE) | KOROAD OpenAPI 활용가이드 § 3.2/3.3 (`/tmp/kosmos-domain-docs/koroad.txt` 표) | docs 의 4-digit 표기는 wire param 형식 오해. 실제 API 는 2-digit + 3-digit 분리. |
| KOROAD `geom_json` strip | `/tmp/kosmos-evidence/koroad-mohw-evidence.md` (~500자 Polygon 필드) | LongFuncEval 2025 (긴 응답 LLM 정확도 저하) | LLM emit 전 strip 으로 token 절약 + 응답 정확도 보존. |
| NFA `nfa_emergency_info_service` 진짜 구현 (stub → 실 구현) | `/tmp/kosmos-evidence/medical-evidence.md` (handle() Layer3GateViolation stub) | NFA OpenAPI 활용가이드 (`/tmp/kosmos-domain-docs/nfa_emg.txt` § 6 sub-operation) | wire param 명세 미확정 (data.go.kr 포털 추가 조사 → P4 implementation step). |
| MOHW `welfare_eligibility_search` 진짜 구현 + `callTp=L` 자동주입 | `/tmp/kosmos-evidence/koroad-mohw-evidence.md` (handle() stub + camelCase 버그) | MOHW SSIS API 가이드 (`/tmp/kosmos-domain-docs/mohw_codes.txt` § 7 enum) | snake_case 정의되어 있지만 API 는 camelCase + `callTp=L`+`srchKeyCode=003` 필수. 어댑터가 자동 주입. |
| `resolve_location` 출력 4종 필드 (`lat, lon, b_code, address_name`) | `/tmp/kosmos-evidence/geocoding-evidence.md` (Kakao 단독 4 시나리오 success) | LlamaIndex / Spring AI "tolerant tools" 패턴 | 4종 누락 시 하위 어댑터 중복 호출. Kakao 단독 충분 (JUSO/SGIS optional). |

### KOSMOS-internal cross-references

| 관련 spec | 정합 보장 |
|---|---|
| Spec 024 (ToolCallAuditRecord v1) | v4 의 어댑터는 모두 기존 `make_error_envelope` + `correlation_id` 패턴 그대로 사용. NFA/MOHW stub 진짜 구현 시 동일 패턴 채택. |
| Spec 025 (V6 auth_type ↔ auth_level) | v4 의 13 도구 모두 기존 `(api_key, AAL1)` (KMA / KOROAD / HIRA / NFA / MOHW) 또는 `(api_key, AAL2)` (NMC) 보존. 새 분류 도입 X. |
| Spec 033 (PermissionRule v2) | v4 의 어댑터는 기존 `AdapterPermissionMetadata` 그대로. citizen path / agency path dual-input 패턴 X (사용자 디렉티브 — 도메인 독립 보존), PIPA §15(2) 4-tuple 위반 위험 0. |
| Spec 027 (Agent Swarm Core) | 영향 X — v4 는 backend tool surface 만, mailbox / coordinator 변경 X. |
| Spec 021 (OTel GenAI) | 13 도구 모두 기존 `kosmos.tool.invoke` span 그대로. NFA / MOHW stub 진짜 구현 시 동일 span pattern. |
| Spec 026 (CICD Prompt Registry) | `prompts/system_v1.md` 의 `models.py:577` 잘못된 LLM 지시 정정 시 SHA-256 manifest 갱신 필요. P3 작업의 일부. |
| Spec 1637 (Adapter docs 7-section) | 13 도구 + resolve_location 의 docs/api/* 동기화 P8 작업으로 보장. |

## Deferred Items Validation (Constitution VI gate)

### `/speckit-specify` 산출 spec.md § Scope Boundaries 검증

**Out of Scope (Permanent)** — 7 항목 (모두 spec prose 와 정합):
- 새 도구 추가 (홈택스 / 정부24 / 모바일ID) → 별도 Epic
- TUI 변경 → 이번 Epic 은 backend 만
- LLM 모델 swap → K-EXAONE 유지
- Anthropic dead code 제거 → Spec 1633 진행 중
- resolve_location JUSO/SGIS backend 활성화 → 키 발급 후 별도 Epic
- 시군구 단위 정확도 보장 → LLM 한계 인정
- plugin (Spec 1636) data isolation → KOSMOS 본체 vs plugin 경로 분리

**Deferred to Future Work** — 7 항목 (모두 NEEDS TRACKING — `/speckit-taskstoissues` 가 placeholder 발행):
1. K-EXAONE Korean function-calling benchmark 정량 측정 → Phase 2 — Korean LLM eval
2. `kma_weather_alert_status` autonomous chain 의 Spec 033 consent 정합 → Phase 2 — Permission v3
3. 17 시군구 / 광역시도 외 도서·산악 lookup 정확도 → Phase 2 — resolve_location v2
4. docs/api/* plugin contributor 친화 refresh process → Phase 3 — adapter health monitoring
5. MOHW `srchKeyCode` 003 외 검색 모드 (001 서비스명 / 002 요약) → Phase 2 — MOHW v2
6. NFA 6 sub-operation 별 분리 도구화 → Phase 2 — NFA v2
7. KOROAD 시군구 4-digit 코드 ↔ 행정동코드 자동 변환 → Phase 2 — KOROAD v2

### Unregistered deferral pattern scan (spec.md text)

scan 패턴: `separate epic` / `future epic` / `Phase [2+]` / `v2` / `deferred to` / `later release` / `out of scope for v1`

**결과**: 모든 매치는 `Scope Boundaries & Deferred Items` 표 또는 `Out of Scope (Permanent)` 항목과 cross-reference 됨. ghost work 0건. **Constitution VI gate PASS**.

## NEEDS CLARIFICATION resolution

**Result**: 0 markers. spec.md § Requirements 의 22 FR + 8 SC + 9 assumption 모두 9 docs + 4 evidence + 4 reviewer + 3 deep research 의 종합으로 결정 가능. clarification 필요 0.

## Decisions consolidated

### Decision 1 — Mirror data location

- **Decision**: KOSMOS 코드 안 reference dict (`grid_coords.py:REGION_TO_GRID`, `koroad/code_tables.py:SidoCode·GugunCode·SIDO_GUGUN_MAP` 등) 그대로 보존. `data/agency-codes/*.csv` 분리 도입 X.
- **Rationale**: (a) 사용자 디렉티브 "mirror 허용" 은 reimplementation 거부였지 file 분리 강제 X. (b) Software Architect reviewer 의 "data 분리도 status-quo refactor — 분리 비용 > 효과" 비판 정합. (c) AGENTS.md hard rule "Korean domain data is the only exception" 명시적 면제. (d) 새 디렉토리 도입 = 새 CI workflow + plugin contributor 친화도 영향 — engineering overhead.
- **Alternatives considered**: data file 분리 (v3 plan 의 (iii) 옵션) — Software Architect 비판으로 reject. CSV / JSON loader 도입 — 사용자 디렉티브 "lookup 도구 X" 와 회색 영역.

### Decision 2 — Description 5-섹션 골격 phrasing

- **Decision**: 5-섹션 = 목적 (1-2 문장) / 입력 quirk / 17 광역시도 short reference / domain quirk / self-contained 선언. 각 섹션 ≤ 100 tokens, 도구당 총 ≤ 500 tokens.
- **Rationale**: (a) Anthropic 공식 ≥3-4 문장 권장 + Semantic Kernel `[Description("""""")]` 인라인 패턴 정합. (b) MCP-Smelly 2026 의 +5.85pp success / 16.67% regression 균형 — 너무 길면 regression, 너무 짧으면 LLM 정확도 저하. ≤500 tokens 이 sweet spot. (c) LongFuncEval 2025 의 7-94% degradation 영역 (8K+ tokens / system prompt) 회피.
- **Alternatives considered**: short reference 시군구 250+ 인라인 — LLM token budget 초과 + LLM in-context recall 한계. system prompt 에 표 두기 — LongFuncEval 회귀 영역.

### Decision 3 — Stub 진짜 구현 vs Mock fixture replay

- **Decision**: NFA / MOHW stub 모두 진짜 implementation. Mock fixture replay 만 보존하는 옵션 reject.
- **Rationale**: (a) spec FR-014, FR-015 명시. (b) 사용자 디렉티브 "갈아엎기 = 단일 Epic 근본 해결" 정합. (c) v0.1-alpha 데모의 도구 가용성 13/13 보장 (현재 11 Live + 2 Stub 라 demo 시연 중 reject 케이스). (d) Spec 1637 docs/api 동기화 mandate.
- **Alternatives considered**: stub 유지 + Mock fixture 만 추가 — demo 신뢰도 낮음, 사용자 디렉티브 위반.

### Decision 4 — `models.py:577` 정정 phrasing

- **Decision**: 기존 잘못된 LLM 지시 ("후속 도구에 nx/ny 가 필요하면 'coords' 충분 — KMA 도구는 nx/ny 를 좌표 → grid 변환해서 별도 받음") 제거. 새 phrasing: "각 도구의 description 을 참조하세요. 도구는 self-contained 입니다."
- **Rationale**: (a) 기존 phrasing 이 사실과 불일치 (`kma_forecast_fetch` 1개만 lat/lon 자동 변환, 나머지 3 KMA 도구는 nx/ny 직접 요구). (b) 사용자 디렉티브 "chain X" 정합. (c) 5-섹션 골격의 self-contained 섹션이 도구 별로 chain 권장/금지 명시 — system prompt 의 일반 지시 불필요.
- **Alternatives considered**: 더 구체적 chain 지시 ("KMA 의 6 도구는 lat/lon 으로 input — 어댑터 내부에서 nx/ny 변환") — 사실과 부분만 일치, 도메인 독립 위반.

### Decision 5 — TUI smoke 4 시나리오 testing

- **Decision**: P7 의 4 시민 발화 시나리오 (부산 날씨 / 강남구 병원 / 서울 응급실 / 임신·출산 복지) 모두 PTY smoke (`scripts/tui-tmux-capture.sh` + `tui/src/test-utils/waitForFrame.ts` 패턴 — `feedback_debug_infra_rebuild` 메모리) 로 검증.
- **Rationale**: (a) AGENTS.md mandatory TUI verification (Layer 4). (b) `feedback_pr_pre_merge_interactive_test` 메모리 — TUI 변경 PR 시 expect/asciinema 검증 필수. (c) v4 가 backend 만 변경하지만 TUI 흐름 (시민 발화 → 어댑터 응답) 회귀 검증 필요.
- **Alternatives considered**: pytest live 만 — TUI 회귀 못 잡음 (Spec 2521 회귀와 동일 anti-pattern).

## Open questions: 0

모든 NEEDS CLARIFICATION 해소 + deferred items 검증 완료 + reference 매핑 완료. Phase 1 진행 가능.
