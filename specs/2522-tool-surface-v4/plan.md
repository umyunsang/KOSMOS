# Implementation Plan: Tool surface v4 — agency-faithful contracts + description-rich + chain-free

**Branch**: `feat/2522-tool-surface-v4` | **Date**: 2026-05-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/2522-tool-surface-v4/spec.md`

## Summary

UMMAYA 13 도구 (KMA 6 / HIRA 1 / NMC 1 / NFA 1 / KOROAD 2 / MOHW 1 / resolve_location 1) 의 surface 를 사용자 디렉티브 (도메인 독립 + chain X + lookup tool X + mirror data 허용 + description quirk + 단일 Epic 갈아엎기) + 4 evidence file 실측 + 4 reviewer report + 3 deep research + 9 domain technical docs 정합으로 근본 재정렬. Spec 2521 회귀 ("Invalid parameters for tool" KMA 호출 실패) 의 architectural 해결.

**Implementation 핵심**: input schema 13 도구 모두 agency contract 그대로 보존. description 5-섹션 골격 (목적 / 입력 quirk / 17 광역시도 short reference / domain quirk / self-contained) 일괄 적용. 1줄 fix 6건 (kma_pre_warning endpoint / kma_weather_alert_status chain / hira `_type=json` / nmc encoding / koroad siDo 2+3-digit / koroad geom_json strip). 2 stub 진짜 구현 (NFA / MOHW). chain 의존성 (`models.py:577`) 정정. resolve_location 출력 4종 필드 표준화 (`lat, lon, b_code, address_name`).

## Technical Context

**Language/Version**: Python 3.12+ (existing baseline)
**Primary Dependencies**: `httpx >=0.27` (async HTTP, existing) · `pydantic >=2.13` (input/output schemas, existing) · `pydantic-settings >=2.0` (env catalog, existing) · `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 spans, existing) · `pytest` + `pytest-asyncio` (test stack, existing). **Zero new runtime dependencies** (AGENTS.md hard rule + spec FR).
**Storage**: N/A — in-memory `ToolRegistry` (boot-time rebuild 으로 mirror dict 자동 load). `~/.ummaya/memdir/user/sessions/` JSONL (Spec 027, 변경 X). 새 storage 도입 X.
**Testing**: `pytest` + `pytest-asyncio` (existing). `@pytest.mark.live` for real `data.go.kr` API tests (Constitution IV — CI skip). TUI PTY smoke (Layer 4) for end-to-end 시민 발화 검증.
**Target Platform**: macOS / Linux terminal (UMMAYA TUI on Bun + Python backend on stdio).
**Project Type**: 단일 Python backend (UMMAYA Python harness — TUI 변경 X, 이번 Epic 은 backend tool surface 만).
**Performance Goals**: 시민 발화 → 도구 호출 응답 ≤ 60s (K-EXAONE on FriendliAI tier 1 의 reasoning latency 30-90s 범위 — 어댑터 자체는 ≤ 5s). description 5-섹션 골격 ≤ 500 tokens / 도구 (Anthropic / OpenAI 권장 + LongFuncEval 회귀 영역 회피).
**Constraints**: ≥ 80% success rate at ≤ 2 turn (10-case 표본). `invalid_params` 에러율 ≤ 10% (Spec 2521 baseline 50%+ → 10%). 13 도구 + resolve_location bun test pass (TUI 회귀 검증). `pytest @pytest.mark.live` 도구별 1+ 케이스 success.
**Scale/Scope**: 13 도구 (Live 11 + Stub 2) + 1 meta-tool (resolve_location). 시민 발화 한국어 우선. 광역시도 17개 단위 정확도 보장. 시군구 250+ 단위 LLM 한계 인정.

## Constitution Check

*GATE: Phase 0 research 전 통과 + Phase 1 design 후 재확인.*

| Principle | Status | 근거 |
|---|---|---|
| **I. Reference-Driven** | ✅ PASS | 9 domain docs + 4 evidence + 3 deep research + `docs/vision.md` § Reference materials (Tool System: Pydantic AI / Claude Agent SDK) 매핑. `research.md` 에서 각 v4 결정 → reference 1:1 매핑. |
| **II. Fail-Closed** | ✅ PASS | 새 permission 분류 발명 X. 13 도구 모두 기존 `AdapterPolicy` (agency citation) 보존. Spec 1979 의 `pipa_class` / `auth_level` 등 UMMAYA-invented 분류 재도입 X. |
| **III. Pydantic v2 Strict** | ✅ PASS | 모든 input/output BaseModel + `frozen=True` + `Any` 사용 X. NFA / MOHW stub 진짜 구현 시 동일 룰. |
| **IV. Government API Compliance** | ✅ PASS | `@pytest.mark.live` gate 유지 (CI skip). `UMMAYA_DATA_GO_KR_API_KEY` 등 모든 키 env. `rate_limit_per_minute` 보존. NFA / MOHW stub 구현 시 happy-path + error-path test. |
| **V. Policy Alignment** | ✅ PASS | Korea AI Action Plan 원칙 8 (single conversational window) / 9 (Open API) 정합. PIPA 7-step gauntlet 변경 X. |
| **VI. Deferred Work** | ✅ PASS | spec.md § Scope Boundaries 의 7 deferred items 모두 NEEDS TRACKING. `/speckit-taskstoissues` 가 placeholder 발행. |

**Post-design re-check (Phase 1 후)**: design 변경 없음 — 위 표 그대로 유효. data-model.md 의 모든 entity 가 Constitution 준수 (Pydantic v2 strict, agency citation, mirror dict UMMAYA 코드 안 보존).

## Project Structure

### Documentation (this feature)

```text
specs/2522-tool-surface-v4/
├── plan.md              # This file
├── research.md          # Phase 0 — references 매핑 + deferred items 검증
├── data-model.md        # Phase 1 — entities (GovAPITool, DescriptionSection, ShortReference, AdapterPolicy, ResolveLocationOutput)
├── quickstart.md        # Phase 1 — 7 시나리오 end-to-end test guide
├── contracts/
│   └── README.md        # Phase 1 — 13 도구 + resolve_location input/output schema 인용
├── checklists/
│   └── requirements.md  # /speckit-specify 산출물
└── tasks.md             # Phase 2 (/speckit-tasks 후)
```

### Source Code (repository root)

```text
src/ummaya/tools/
├── kma/
│   ├── kma_current_observation.py       # description 갈아엎기 + base_time validator
│   ├── kma_short_term_forecast.py       # description 갈아엎기 + base_time 8-시각 validator
│   ├── kma_ultra_short_term_forecast.py # description 갈아엎기 + HH30 validator
│   ├── forecast_fetch.py                # description 갈아엎기 (이미 lat/lon)
│   ├── kma_pre_warning.py               # endpoint 정정 (getPreWrnList → getWthrWrnList) + description
│   ├── kma_weather_alert_status.py      # stn_id/tmFc 필수 + chain 명시 + description
│   ├── projection.py                    # 변경 X (수학 알고리즘)
│   └── grid_coords.py                   # 변경 X (mirror dict 보존)
├── hira/
│   └── hospital_search.py               # _type=json 정정 + description
├── nmc/
│   └── emergency_search.py              # URL encoding 자동화 + description
├── nfa119/
│   └── emergency_info_service.py        # 진짜 구현 (현재 stub) — wire param 조사 + handle()
├── koroad/
│   ├── accident_search.py               # siDo/guGun 2+3-digit description 정정
│   ├── accident_hazard_search.py        # geom_json strip + description
│   └── code_tables.py                   # 변경 X (mirror IntEnum 보존)
├── mohw/
│   └── welfare_eligibility_search.py    # 진짜 구현 (현재 stub) — handle() + camelCase + XML + callTp=L
├── resolve_location.py                  # 출력 4종 필드 표준화
└── models.py                            # :577 chain dependency 잘못된 LLM 지시 정정

src/ummaya/ipc/stdio.py                  # _build_available_adapters_suffix 의 ORDERING 지시 정합

tests/
├── tools/
│   ├── kma/test_*_v4.py                 # 4-case 패턴 (live success / unit mock / fixture replay / autonomous chain)
│   ├── hira/test_*_v4.py
│   ├── nmc/test_*_v4.py
│   ├── nfa119/test_*_v4.py              # NEW (stub 진짜 구현 후)
│   ├── koroad/test_*_v4.py
│   ├── mohw/test_*_v4.py                # NEW (stub 진짜 구현 후)
│   └── test_resolve_location_v4.py      # 4종 필드 출력 표준
└── e2e/
    └── test_tui_smoke_v4_scenarios.py   # 7 시민 발화 시나리오 (Layer 4 PTY smoke)

docs/api/                                # Spec 1637 7-section 동기화 (P8)
├── kma/{current_observation,short_term_forecast,ultra_short_term_forecast,forecast_fetch,pre_warning,weather_alert_status}.md
├── hira/hospital_search.md
├── nmc/emergency_search.md
├── nfa119/emergency_info_service.md     # NEW (진짜 구현 후)
├── koroad/{accident_search,accident_hazard_search}.md
├── mohw/welfare_eligibility_search.md   # NEW (진짜 구현 후)
└── resolve_location/index.md            # 4종 필드 출력 표준 갱신
```

**Structure Decision**: 단일 Python backend 재구성. 새 디렉토리 / 패키지 도입 X. `src/ummaya/tools/` 의 13 어댑터 + `resolve_location.py` + `models.py` + `ipc/stdio.py` 만 변경. data file 분리 (`data/agency-codes/`) 도입 X — Decision 1 (research.md) 정합.

## Phase plan (10d 견적, single Epic single PR)

| Phase | 범위 | 시간 | 의존 |
|---|---|---|---|
| **P0** | 13 도구 description 5-섹션 골격 일괄 재작성 (17 광역시도 short reference 포함) | 2d | 9 docs (있음) + evidence (있음) |
| **P1** | 1줄 fix 6건 — kma_pre_warning endpoint / hira `_type=json` / nmc encoding / koroad siDo description / koroad geom_json strip / kma_weather_alert_status validator | 0.5d | — |
| **P2** | `kma_weather_alert_status` `stn_id`/`tmFc` model_validator + autonomous chain description 명시 | 0.5d | P1 |
| **P3** | `models.py:577` chain dependency 잘못된 LLM 지시 정정 + `ipc/stdio.py` ORDERING 지시 정합 | 0.5d | — |
| **P4** | NFA stub 진짜 구현 — wire param 조사 (data.go.kr 포털) + handle() + fixture + 6 sub-operation 분기 | 2d | data.go.kr 포털 wire param 명세 확인 |
| **P5** | MOHW stub 진짜 구현 — handle() + camelCase serialize + UTF-8 XML 파싱 + `callTp=L` 자동 주입 + 7 enum 매핑 | 2d | docs/api/mohw 명세 |
| **P6** | `resolve_location` 출력 4종 필드 표준화 (`ResolveLocationOutput` 신모델) | 0.5d | — |
| **P7** | TUI PTY smoke 7 시나리오 single-tool / 2-turn success 검증 (Layer 4) | 1d | P0-P6 |
| **P8** | docs/api/* 13 어댑터 doc 7-section 동기화 (Spec 1637 호환) | 1d | P0 |

**총 10d**. 단일 PR, Phase 분리 X. Lead Opus + Sonnet teammates 병렬 dispatch (P0 / P1 / P2 / P3 / P6 / P8 동시 가능, P4 / P5 의존성 별도, P7 마지막).

## Complexity Tracking

> **Constitution check 모두 PASS — violation 없음.**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| (없음) | (없음) | (없음) |

Phase 1 design 후 재확인 결과 — research.md 의 5 Decision 모두 Constitution 준수. data-model.md 의 5 entity 모두 Pydantic v2 strict + agency citation + mirror dict UMMAYA 코드 안 보존. **violation 0건**.
