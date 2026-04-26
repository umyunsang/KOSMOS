# KOSMOS v0.1-alpha — KSC 2026 발표 본문

> 대상 발표: 2026 한국소프트웨어종합학술대회 (KSC 2026) 학생 포트폴리오
> 작성 기준: 2026-04-26 · `main` 브랜치 Initiative #1631 완료
> 출처: `docs/vision.md`, `docs/requirements/kosmos-migration-tree.md`, `AGENTS.md`,
>       `CHANGELOG.md [v0.1-alpha]`, `docs/api/README.md`, `specs/1637-p6-docs-smoke/spec-review-notes.md`,
>       `specs/1637-p6-docs-smoke/smoke-checklist.md`

---

## Chapter 1 — 프로젝트 개요

### KOSMOS 정의 (slide 2)

- **한 줄 정의**: Claude Code의 하네스를 한국 공공서비스 도메인으로 마이그레이션한 시민용 대화형 AI 플랫폼
- **미션** (`docs/vision.md § The ambition`):
  `data.go.kr` 의 5,000+ 분산 공공 API를 단일 대화 인터페이스로 — 시민이 자연어 질문 하나로 부처를 가로질러 실시간 정부 데이터 기반 답변을 얻을 수 있도록
- **포지셔닝**: Claude Code가 "개발자 중심 코딩 하네스"라면 KOSMOS는 "국민·국가행정시스템 작업 하네스"
  (`docs/requirements/kosmos-migration-tree.md § ROOT`)

### 시민 사용 시나리오 (slide 2)

`docs/vision.md § The ambition` 에서 직접 인용:

- **안전 경로**: "내일 부산에서 서울 가는데, 안전한 경로 추천해줘"
  → KOROAD 사고 데이터 + KMA 기상 특보 + 도로위험지수 융합
  → "경부고속도로 대전-천안 구간 위험 등급, 안개 주의보. 중부내륙 우회를 추천합니다."

- **야간 응급실**: "아이가 열이 나는데 근처 야간 응급실 어디야?"
  → 119 응급정보 API (NFA119) + HIRA 병원정보 융합
  → 위치 기반 응급실 목록 + 현재 대기 시간

- **출산 보조금**: "출산 보조금 신청하고 싶은데"
  → MOHW 복지 자격 API + Gov24 신청 안내
  → 자격 확인 · 필요 서류 · 온라인 신청 가이드

### Thesis — 하네스 마이그레이션 (slide 3)

`docs/vision.md § The thesis` 에서:

- **핵심 주장**: Claude Code의 하네스(tool loop · permission gauntlet · context assembly · TUI)는
  "올바른 도구를 올바른 순서로 호출하는" 문제로 환원되는 모든 도메인에 적용 가능한 범용 substrate
- **Claude Code vs KOSMOS 대응**:

  | | Claude Code | KOSMOS |
  |---|---|---|
  | 사용자 | 소프트웨어 개발자 | 대한민국 시민 |
  | 도구 표면 | 파일시스템 · 쉘 · git | `data.go.kr` 공공 API · 행정 포털 |
  | 기본 동사 | Read · Edit · Bash · Grep · WebFetch | `lookup` · `submit` · `verify` · `subscribe` |
  | 권한 관심사 | 위험 쉘 명령 · 파일 덮어쓰기 | PIPA 개인정보 보호 · 본인 인증 · 법령 준수 |

### LLM Stack 및 프로젝트 정보 (slide 4)

- **LLM**: `LGAI-EXAONE/EXAONE-4.0-32B` via FriendliAI Serverless (OpenAI-compatible endpoint)
  (`docs/requirements/kosmos-migration-tree.md § L1-A A1`)
- **Claude Code agentic loop 1:1 보존**: EXAONE native function calling + 동일 loop skeleton 적용
  (`docs/requirements/kosmos-migration-tree.md § L1-A A2`)
- **라이선스**: Apache-2.0
- **분류**: 학생 포트폴리오 프로젝트 · KSC 2026 제출
- **비제휴 선언**: Not affiliated with Anthropic, LG AI Research, or the Korean Government
  (`AGENTS.md § What KOSMOS is`)

### 6-Layer Architecture 요약 (slide 4)

`docs/vision.md § Six-layer architecture` 에서:

- **Layer 1 Query Engine** — `while(True)` tool loop으로 민원 요청 해소 (Async generator state machine)
- **Layer 2 Tool System** — `data.go.kr` API 어댑터 schema-driven 등록·팩토리
- **Layer 3 Permission Pipeline** — PIPA 기반 시민 인증·개인정보 보호 bypass-immune gauntlet
- **Layer 4 Agent Swarms** — 부처별 전문 에이전트 + 코디네이터 오케스트레이션 (파일 기반 mailbox IPC)
- **Layer 5 Context Assembly** — LLM이 매 턴 받는 3-tier 컨텍스트 (System · Memory · Attachments)
- **Layer 6 Error Recovery** — 공공 API 장애·Rate-limit·점검 대응 resilience matrix

---

## Chapter 3 — 프로젝트 진행 내용

### 6 Phase 마이그레이션 시퀀스 (slide 6)

`docs/requirements/kosmos-migration-tree.md § 실행 Phase 순서` 및 `CHANGELOG.md [v0.1-alpha]`:

- **P0 #1632 — Baseline Runnable**
  - Claude Code 2.1.88 src 컴파일·런타임 복구
  - CC 소스맵 기반 TUI 초기 포트 (`tui/` Ink + Bun 스캐폴드)
  - 산출물: 컴파일 성공 + 최소 부트 확인

- **P1+P2 #1633 — Dead-code elimination + Anthropic → FriendliAI 마이그레이션**
  - CC 전용 dead code (`ant-only`, `feature()`, `migration`, `telemetry` 브랜치) 제거
  - Anthropic API 상수 → FriendliAI Serverless 상수 교체
  - K-EXAONE 함수 호출 프로토콜 적용
  - 산출물: FriendliAI endpoint 단일 고정화 + Spec 1633 병합

- **P3 #1634 — Tool system wiring** (`feat/1634-tool-system-wiring`)
  - 4 primitive 선언 — `lookup` · `submit` · `verify` · `subscribe` (`docs/requirements/kosmos-migration-tree.md § L1-C C1`)
  - Python stdio MCP 서버 stub 연결 (`mcp` Python 패키지)
  - BM25 기반 `lookup(mode="search")` 디스패치 구현
  - `PrimitiveInput/Output` 공통 envelope (Pydantic v2)
  - `ToolRegistry.register_all()` + Spec 022 seed 어댑터 4종 등록
  - 산출물: 13-tool closed surface + Spec 031 five-primitive harness 완성

- **P4 #1847 (Epic #1635) — UI L2 시민 포트** (`feat/1635-ui-l2-citizen-port`)
  - **5-step onboarding** (`preflight → theme → pipa-consent → ministry-scope → terminal-setup`) (`docs/requirements/kosmos-migration-tree.md § UI-A`)
  - **REPL Main** — chunk 스트리밍 (≈20 token) · `Ctrl-O` expand/collapse · Markdown table · 에러 envelope 3종 (`docs/requirements/kosmos-migration-tree.md § UI-B`)
  - **Permission Gauntlet UI** — Layer 1/2/3 색상 (green/orange/red) · `[Y 한번만 / A 세션 자동 / N 거부]` modal · receipt ID 표시 (`docs/requirements/kosmos-migration-tree.md § UI-C`)
  - **Ministry Agent panel** (`/agents`) — 5-state proposal-iv UI + SLA/건강/평균응답 (`--detail`) (`docs/requirements/kosmos-migration-tree.md § UI-D`)
  - **보조 surface** — HelpV2 · Config overlay · Plugin browser (⏺/○ 토글) · Export PDF · History search (`docs/requirements/kosmos-migration-tree.md § UI-E`)
  - PDF 인라인 렌더 — `pdf-to-img` WASM (Kitty/iTerm2) + `open` fallback
  - 산출물: TUI CC 90% 시각·구조 동일 포팅 (`memory feedback_cc_tui_90_fidelity`)

- **P5 #1927 (Epic #1636) — 5-tier Plugin DX** (`feat/1636-plugin-dx-5tier`)
  - **Tier 1** — `kosmos-plugin-template` (`is_template` GitHub repo) + `kosmos plugin init` TUI + `uvx kosmos-plugin-init` Python fallback + 30분 quickstart 측정 PASS
  - **Tier 2** — 9개 한국어 primary 가이드 (`docs/plugins/`) + FR-006 Bilingual 용어집
  - **Tier 3** — 4개 예시 레포 (seoul-subway / post-office Live + nts-homtax / nhis-check Mock)
  - **Tier 4** — 50-item validation matrix (`tests/fixtures/plugin_validation/checklist_manifest.yaml`) + 10개 check 모듈 + `.github/workflows/plugin-validation.yml` + plugin_submission issue template
  - **Tier 5** — `kosmos-plugin-store/index` 카탈로그 + 8-phase installer (SLSA v1.0 검증 포함)
  - **PIPA §26** — 수탁자 책임 SHA-256 acknowledgment gate (`docs/plugins/security-review.md` 정규 텍스트)
  - SC 달성: SC-004 BM25 ≤5s / SC-005 install ≤30s / SC-007 OTEL `kosmos.plugin.id` / SC-010 auto_discover <200ms

- **P6 #1637 — Docs/API specs + Integration smoke** (`feat/1637-p6-docs-smoke`)
  - 24 어댑터 Markdown spec 작성 (`docs/api/`) — 7-section 필수 템플릿
  - 25 JSON Schema Draft 2020-12 export (`docs/api/schemas/`, `scripts/build_schemas.py`)
  - `docs/tools/` → `docs/api/` 통합 (레거시 디렉터리 제거)
  - `road_risk_score` 복합 도구 참조 전체 정리 (0 occurrences, SC-004 ✓)
  - `bun test` 회귀 없음 게이트 PASS
  - 19 visual evidence surface 자동 캡처 (`ink-testing-library`)
  - 산출물: Initiative #1631 closed · KOSMOS v0.1-alpha 출시

### 각 Phase 주요 통계 (slide 7)

| Phase | Epic | 주요 산출물 | 핵심 지표 |
|---|---|---|---|
| P0 | #1632 | CC 2.1.88 runtime 복구 | 컴파일 성공 |
| P1+P2 | #1633 | dead-code 제거 + FriendliAI 전환 | provider 단일화 |
| P3 | #1634 | 4 primitive + 13-tool registry | Spec 031 완성 |
| P4 | #1847 | 5-step onboarding + REPL + Permission + Agents | TUI CC 90% 포팅 |
| P5 | #1927 | 5-tier plugin DX + PIPA §26 gate | 50-item validation |
| P6 | #1637 | 24 어댑터 spec + 25 schema + 19 visual evidence | `bun test` 0 fail |

### Spec-driven Workflow 방법론 (slide 8)

`AGENTS.md § Spec-driven workflow`:

- **순서**: Epic issue 생성 → `/speckit-specify` (spec.md) → `/speckit-plan` (plan.md, `docs/vision.md` 참조 의무) → `/speckit-tasks` (tasks.md) → `/speckit-analyze` (Constitution 준수 검증) → `/speckit-taskstoissues` (Task GitHub issues 생성) → `/speckit-implement` (Agent Teams 병렬 실행) → PR `Closes #EPIC` → CI 모니터링 → merge 후 sub-issues 닫기
- **원칙**: 스펙 없이 코드 작성 금지. 단계별 승인 없이 진행 금지.
- **PR 규칙**: `Closes #EPIC` 만 본문에 등록 — Task sub-issue는 포함하지 않음 (`memory feedback_pr_closing_refs`)

### Agent Teams 활용 (slide 8)

`AGENTS.md § Agent Teams`:

| 역할 | 에이전트 | 모델 |
|---|---|---|
| 아키텍처·스펙·리뷰 | Lead | Claude Opus |
| 백엔드 구현·테스트·리팩토링 | Backend Architect | Claude Sonnet |
| TUI/CLI 구현 | Frontend Developer | Claude Sonnet |
| 테스트 작성 | API Tester | Claude Sonnet |
| 코드 리뷰 | Code Reviewer | Claude Opus |
| 보안 검토 | Security Engineer | Claude Sonnet |
| 문서 작성 | Technical Writer | Claude Sonnet |

- 3개 이상 독립 Task → Agent Teams 병렬 실행 (`/speckit-implement` 단계에서만)
- 1-2개 또는 결합된 Task → Lead 단독

### Constitution 6 Principles (slide 9)

`.specify/memory/constitution.md` (Spec-kit constitution, 각 `/speckit-analyze` 검증 기준):

- **I. Reference-Driven Design** — 모든 설계 결정은 `docs/vision.md § Reference materials` 또는 Claude Code 소스맵 인용 후 정당화
- **II. Fail-Closed Defaults** — 어댑터 신규 등록 시 `requires_auth=True`, `is_personal_data=True`가 기본값; 명시적 override 없이 공개 불가
- **III. Pydantic v2 Everywhere** — tool I/O는 전부 Pydantic v2 모델; `Any` 타입 사용 금지
- **IV. Government API Compliance** — CI에서 실제 `data.go.kr` API 호출 금지; 라이브 테스트는 `@pytest.mark.live` 격리
- **V. Policy Alignment** — PIPA §26 수탁자 책임 · Korea AI Action Plan 원칙 8/9 정렬
- **VI. Deferred Work Tracking** — 설계 범위 밖 항목은 삭제하지 않고 [Deferred] 레이블 sub-issue로 후속 추적

---

## Chapter 5 — 진행 결과물

### 정량 결과 — 어댑터 매트릭스 (slide 12)

`docs/api/README.md § Matrix A` 기준 24 어댑터:

**Live tier (12개)** — 실제 `data.go.kr` endpoint 호출:

| 기관 | tool_id | Primitive | Permission tier |
|---|---|---|---|
| KOROAD (도로교통공단) | `koroad_accident_search` | `lookup` | 1 |
| KOROAD | `koroad_accident_hazard_search` | `lookup` | 1 |
| KMA (기상청) | `kma_current_observation` | `lookup` | 1 |
| KMA | `kma_short_term_forecast` | `lookup` | 1 |
| KMA | `kma_ultra_short_term_forecast` | `lookup` | 1 |
| KMA | `kma_weather_alert_status` | `lookup` | 1 |
| KMA | `kma_pre_warning` | `lookup` | 1 |
| KMA | `kma_forecast_fetch` | `lookup` | 1 |
| HIRA (건강보험심사평가원) | `hira_hospital_search` | `lookup` | 1 |
| NMC (국립중앙의료원) | `nmc_emergency_search` | `lookup` | **3 (L3-gated)** |
| NFA119 (소방청) | `nfa_emergency_info_service` | `lookup` | 1 |
| MOHW (보건복지부) | `mohw_welfare_eligibility_search` | `lookup` | 1 |

**Mock tier (11개)** — 공개 스펙 기반 fixture-replay:

- `verify` ×6: `mock_verify_digital_onepass` · `mock_verify_mobile_id` · `mock_verify_gongdong_injeungseo` · `mock_verify_geumyung_injeungseo` · `mock_verify_ganpyeon_injeung` · `mock_verify_mydata`
- `submit` ×2: `mock_traffic_fine_pay_v1` · `mock_welfare_application_submit_v1`
- `subscribe` ×3: `mock_cbs_disaster_v1` · `mock_rss_public_notices_v1` · `mock_rest_pull_tick_v1`

**Meta (1개)**: `resolve_location` (Geocoding meta-tool, `lookup` 클래스)

### 정량 결과 — 스키마 및 테스트 (slide 13)

- **25 JSON Schema** Draft 2020-12 파일 (`docs/api/schemas/`) — 24 어댑터 + 1 `lookup` dispatch meta-tool
  - `scripts/build_schemas.py` (stdlib + Pydantic v2 only) 결정론적 생성
  - `uv run python scripts/build_schemas.py --check` → exit 0 (idempotency 확인, SC-002 ✓)
  (`specs/1637-p6-docs-smoke/spec-review-notes.md § Schemas count`)

- **bun test 결과**: **928 pass / 4 skip / 3 todo / 0 fail / 0 errors** (총 935 tests)
  - `tui/tests/keybindings/`: 189 pass / 0 fail — keybindings + chord resolution 계약 적용
  (`specs/1637-p6-docs-smoke/smoke-checklist.md § Pre-existing automated coverage`)

- **어댑터 spec 구조 lint**: 24/24 YAML front matter 포함 · 23/24 정확히 7개 `## ` 섹션
  - 1개 예외 (`nmc/emergency_search.md`) — Freshness sub-tool 추가 섹션, 의도적 (Spec FR-002)
  (`specs/1637-p6-docs-smoke/spec-review-notes.md § T030`)

- **30초 cold-read self-test** (SC-007): `docs/api/README.md` 시작 → `koroad_accident_search` spec 확인 → schema `$schema` URI 검증 → **실제 소요 19초** (목표 30초 이내 PASS)
  (`specs/1637-p6-docs-smoke/spec-review-notes.md § SC-007`)

### 정량 결과 — Visual Evidence (slide 13)

`specs/1637-p6-docs-smoke/smoke-checklist.md § Surfaces dumped automatically`:

- **19 surface** 자동 캡처 완료 (목표 18 → 1개 초과 달성)
- 캡처 방법: `tui/scripts/dump-tui-frames.tsx` — `ink-testing-library` `render()` + `lastFrame()` 기록

| 카테고리 | Surface 수 | 대표 항목 |
|---|---|---|
| 5-step Onboarding | 5 | splash · theme · PIPA · ministry-scope · terminal |
| Primitive flows | 5 | lookup-search · lookup-fetch (×2) · submit-receipt · verify · subscribe |
| Error envelopes | 3 | LLM 4xx (🧠) · tool fail-closed (🔧) · network timeout (📡) |
| Slash commands | 3 | `/plugins` browser · `/consent` issued · `/consent` revoked (×2) |
| PDF render | 1 | 인라인 렌더 loading state |
| 수동 (deferred) | 2 | `/agents` · `/help` — full keybinding-provider context 필요 |

**Visual contracts 검증** (`smoke-checklist.md § Visual contracts verified`):
- 브랜드 글리프 ✻ — plugin browser 타이틀 확인 (CC 컨벤션 유지)
- 한국어 primary + 영어 key hint 이중언어 출력 (FR-021)
- AAL 라벨 — PIPA consent surface에 `2단계 인증 (AAL2)` 표시 (Spec 033)
- 에러 border 색상 3종 — purple (LLM) / orange (tool) / red (network)

### 정성 결과 (slide 14)

- **Initiative #1631 closed** — 6 Phase Epic 전체 (`#1632 → #1633 → #1634 → #1847 → #1927 → #1637`) 병합 완료
- **KOSMOS v0.1-alpha shipped** — 2026-04-26 (`CHANGELOG.md [v0.1-alpha]`)
- **Zero new runtime dependencies** — 마이그레이션 전 단계 AGENTS.md hard rule 유지 (`CHANGELOG.md § Highlights`)
- **Zero CRITICAL Copilot Review Gate findings** — PR #1977 merge 조건 (SC-008)
- **`docs/tools/` 완전 제거** — `docs/api/` 로 흡수 (`test ! -d docs/tools && echo gone` → `gone`, SC-006 ✓)
- **`road_risk_score` 복합 참조 0건** — `grep -rn 'road_risk_score' docs/` 결과 없음 (SC-004 ✓)

### 후속 Follow-up — Deferred 5종 (slide 14)

`CHANGELOG.md [v0.1-alpha] § Out of v0.1-alpha (deferred)`:

| 이슈 | 내용 | 사유 |
|---|---|---|
| **#1972** | `/agent-delegation` Full OpenAPI 3.0 specification | JSON Schema가 1차 계약; OpenAPI는 별도 설계 pass 필요 |
| **#1973** | `ministries_for_composite()` API 영구 제거 | 미래 composite 계획 확정 후 제거 |
| **#1974** | 12 Live-tier 어댑터 live regression coverage | CI에서 실제 API 키 + `@pytest.mark.live` 격리 운영 필요 |
| **#1975** | Pydantic docstring 기반 어댑터 spec stub 자동 생성 | 24 수동 spec 이후 generator 도입 |
| **#1976** | OPAQUE mock stub (`barocert/` · `npki_crypto/` · `omnione/`) → `docs/scenarios/` 이전 | byte/shape mirror 불가 항목 시나리오 문서화 |

### 정렬 (slide 15)

**Korea AI Action Plan (2026-2028)** (`docs/vision.md § Aligned with` via `CHANGELOG.md`):

- **원칙 8** — 단일 대화형 인터페이스로 5,000+ 공공 API 접근 (KOSMOS 핵심 미션)
- **원칙 9** — Open API + OpenMCP 연동 (BM25 discovery + plugin DX 5-tier)
- **원칙 5** — 동의 기반 접근 (PIPA §26 수탁자 모델 + permission gauntlet receipt)

**PIPA §26 수탁자 모델** (`AGENTS.md § What KOSMOS is`):

- KOSMOS는 PIPA §26 수탁자(수탁자 기본 해석)
- 개인정보 처리 어댑터 전부 permission gauntlet (Spec 033) 통과 의무
- 처리 영수증 user-tier memdir (`~/.kosmos/memdir/user/consent/`) 기록
- Plugin 기여자: `processes_pii: true` 시 `docs/plugins/security-review.md` SHA-256 trustee acknowledgment CI 강제 검증
