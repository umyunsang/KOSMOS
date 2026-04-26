# KOSMOS v0.1-alpha — KSC 2026 발표 본문

> Slide-ready bullets. 한국어 primary. Chapter 1~6 전체.
> 작성일: 2026-04-26

---

## Slide 1 — Cover

**KOSMOS v0.1-alpha**
한국 공공 API 대화형 AI 플랫폼

KSC 2026 · umyunsang (dbstkd5865@gmail.com)
2026-04-26

*Apache-2.0 / Student Portfolio / Not affiliated with LG AI Research or the Korean Government*

---

## Slide 2 — 목차

1. 프로젝트 개요
2. 기존 문제 및 차별성
3. 프로젝트 진행 내용
4. Role and Responsibilities
5. 진행 결과물
6. 프로젝트 관리 및 일정

---

# Chapter 1 — 프로젝트 개요

## Slide 3 — KOSMOS 한 줄 정의 & 미션

**한국 공공 API를 자연어로 만나는 시민 대화형 AI 플랫폼**

- `data.go.kr` 10만 건 공공 데이터 + 5,000+ API → 단일 자연어 인터페이스
- 시민은 어느 부처가 어떤 API를 운영하는지 알 필요 없음
- LLM이 의도를 분석하고 적절한 공공 API 도구를 자율 호출

**LLM Stack**
- 모델: **K-EXAONE-236B-A23B** (LG AI Research)
- 서빙: FriendliAI Serverless (OpenAI-compatible, 60 RPM Tier 1)

---

## Slide 4 — 시민 사용 시나리오

**Scenario A — 안전 경로**
> "내일 부산에서 서울 가는데, 안전한 경로 추천해줘"
>
> KOSMOS: KOROAD 사고 데이터 + KMA 기상특보 + 도로 위험 지수 융합
> → "경부고속도로 대전-천안 구간 위험 등급, 안개 주의보. 중부내륙 우회를 추천합니다."

**Scenario B — 야간 응급실**
> "아이가 열이 나는데 근처 야간 응급실 어디야?"
>
> KOSMOS: 119 응급의료 API + HIRA 병원정보 융합
> → 위치순 가용 응급실 + 현재 대기시간

**Scenario C — 출산 보조금**
> "출산 보조금 신청하고 싶은데"
>
> KOSMOS: 보건복지부 자격조회 API + Gov24 신청 API
> → 자격 확인 → 필요 서류 → 온라인 신청 가이드

시민은 부처·API 경계를 학습하지 않습니다. **라우팅은 KOSMOS가 합니다.**

---

## Slide 5 — 6-Layer Architecture

| # | Layer | 역할 |
|---|---|---|
| 1 | Query Engine | `while(True)` 도구 루프 — 시민 요청 완전 해결까지 |
| 2 | Tool System | `data.go.kr` API 어댑터 스키마-구동 레지스트리 |
| 3 | Permission Pipeline | 시민 인증 + PIPA 개인정보 보호 게이트 |
| 4 | Agent Swarms | 부처 전문 에이전트 오케스트레이터 협업 |
| 5 | Context Assembly | LLM이 매 턴 받는 3-tier 컨텍스트 |
| 6 | Error Recovery | 공공 API 장애·레이트리밋·점검 대응 |

- Apache-2.0 / 학생 포트폴리오 / KSC 2026
- Not affiliated with LG AI Research or the Korean Government

---

# Chapter 2 — 기존 문제 및 차별성

## Slide 6 — 한국 공공 API 시장 현황

**data.go.kr 규모**
- 공개 데이터셋: **100,000건+**
- 등록 API 수: **5,000+**
- 민간 API 활용 건수: **7,579만 건** (2024년 기준, 행안부 공공데이터 활용 현황)
- OECD OURdata 지수 **1위** (2023) — 개방 선도국

**AI 정책 정합성**
- 대한민국 AI 행동계획 2026-2028 (국가인공지능전략위원회, 2026.2.25)
- 전략분야 7 공공AX — 원칙 8: "모든 민원을 AI 단일창구로 접수/처리"
- 원칙 9: "Open API · OpenMCP로 민간이 공공서비스를 결합해 국민에게 제공"

**KOSMOS는 원칙 8/9의 학생 레퍼런스 구현입니다.**

---

## Slide 7 — 기존 한국 공공 챗봇 한계

| 서비스 | 방식 | 한계 |
|---|---|---|
| 정부24 AI 챗봇 | 단일 부처 / FAQ 기반 | 부처 횡단 불가, 고정 답변 |
| 네이버 CLOVA 공공 | NLP 안내 봇 | 실시간 API 데이터 연결 없음 |
| 카카오 i 공공 | NLP 안내 봇 | 도구 루프 부재, PIPA 게이트 없음 |

**공통 문제**
- 단일 부처 사일로 → 부처 횡단 시나리오 불가
- FAQ/룰 기반 → 실시간 공공 API 데이터 미연동
- LLM 도구 루프 없음 → 복합 질의 처리 불가
- PIPA §26 수탁자 책임 구조 없음

---

## Slide 8 — KOSMOS 차별점

**부처 횡단**
- 24 어댑터 / 7 ministries: KOROAD · KMA · HIRA · NMC · NFA119 · MOHW · 마이데이터
- 단일 세션에서 복수 부처 API 자율 호출

**LLM 도구 루프**
- 4 primitive: `lookup` · `submit` · `verify` · `subscribe`
- BM25 + dense 하이브리드 도구 검색 (kiwipiepy 형태소 분석)

**3-Layer 권한 게이트웨이**
- Layer 1 (green): 공개 조회
- Layer 2 (orange): API 키 인증
- Layer 3 (red): OAuth / PIPA §26 수탁자 — bypass-immune

**5-Tier 플러그인 DX**
- Template / Guide / Examples / Submission / Registry
- 외부 시민·부처 기여 가능 (50-item 검증 워크플로)

---

# Chapter 3 — 프로젝트 진행 내용

## Slide 9 — 6 Phase 개요

| Phase | 내용 | Epic |
|---|---|---|
| P0 | Baseline — 런타임 기초 구축 | #1632 |
| P1+P2 | Provider 통합 — FriendliAI + K-EXAONE-236B-A23B | #1633 |
| P3 | 도구 시스템 — 4 primitive + Python stdio MCP | #1634 |
| P4 | 시민 UI — Onboarding · REPL · 권한 모달 · /agents | #1635 / #1847 |
| P5 | 플러그인 DX — 5-tier 전체 | #1636 / #1927 |
| P6 | 문서 + 통합 검증 — 24 어댑터 spec · 스모크 | #1637 |

모든 6 Phase Epic closed · Initiative #1631 closed

---

## Slide 10 — Phase 상세 (P0~P2)

**P0 — Baseline Runnable**
- TUI 런타임 컴파일·부트 복구
- Python 백엔드 + Ink/Bun TUI 파이프라인 기초

**P1 — Dead Code Elimination**
- 미사용 코드 제거, 컴파일 경고 0
- K-EXAONE 전용 상수 정의

**P2 — Provider 통합**
- LLM 클라이언트 FriendliAI Serverless 연결
- K-EXAONE-236B-A23B native function calling 활성화
- OTEL GenAI v1.40 스팬 (`gen_ai.model.id` = `LGAI-EXAONE/K-EXAONE-236B-A23B`)

---

## Slide 11 — Phase 상세 (P3~P4)

**P3 — 도구 시스템 와이어링**
- 4 primitive 봉투: `PrimitiveInput` / `PrimitiveOutput` (Pydantic v2)
- Python stdio MCP 서버 스텁 ↔ TUI MCP 클라이언트
- 13-tool 표면 closed

**P4 — 시민 UI**
- 5-step onboarding (`preflight → theme → pipa-consent → ministry-scope → terminal-setup`)
- 스트리밍 REPL (≈20 token chunk)
- 권한 모달 `[Y 한번만 / A 세션자동 / N 거부]` + receipt ID
- `/agents` 패널 (D1/D2 상태 표시)
- 접근성 4종 토글 (스크린리더·큰글씨·고대비·reduced motion)

---

## Slide 12 — Spec-Driven Workflow & Constitution

**Spec-driven workflow**
```
/speckit-specify
    → /speckit-plan  (docs/vision.md 참조 필수)
    → /speckit-tasks
    → /speckit-analyze  (Constitution compliance)
    → /speckit-taskstoissues  (GitHub Sub-Issues API v2)
    → /speckit-implement  (Agent Teams 병렬 실행)
    → PR (Closes #EPIC only)
```

**Constitution 6 Principles**
1. Reference-Driven Design (vision.md + .references/ 인용)
2. Fail-Closed Security (기본값 = 거부)
3. Pydantic v2 Strict Typing (no `Any`)
4. Gov API Compliance (CI에서 live API 호출 금지)
5. Policy Alignment (PIPA §26 + AI Action Plan)
6. Deferred-Work Accountability (비이행 항목 Epic 추적)

---

# Chapter 4 — Role and Responsibilities

## Slide 13 — 역할 & 협업 패턴

**솔로 학생 프로젝트 (umyunsang)**

| 역할 | 담당 내용 |
|---|---|
| Architecture | 6-Layer 설계 · ADR 작성 |
| Backend | Python 어댑터 · LLM 클라이언트 · OTEL |
| Frontend TUI | Ink/React · Bun · IPC 프레임 |
| Tests | pytest · ink-testing-library · fixture |
| Docs | 24 어댑터 spec · JSON Schema · 가이드 |
| Plugin DX | 5-tier 플러그인 인프라 · 검증 워크플로 |
| Release | CI/CD · Copilot/Codex Review Gate · SemVer |

**협업 패턴**
- Lead (전략·리뷰·아키텍처): 계획 → Agent Teams 지시
- Teammates (코딩·테스트): 병렬 독립 태스크 실행

**도구**
- GitHub Spec Kit (`/speckit-*` 스킬) · Sub-Issues API v2 (GraphQL)
- Copilot Review Gate (Cloudflare Worker) · Codex Review

---

# Chapter 5 — 진행 결과물

## Slide 14 — 24 어댑터 카탈로그

**Live 어댑터 (12)**

| 부처 | 어댑터 | primitive |
|---|---|---|
| KOROAD (도로교통공단) | 사고다발지역 검색, 교통사고 검색 | lookup ×2 |
| KMA (기상청) | 단기예보, 초단기예보, 현재관측, 기상특보, 중기예보, 실황조회 | lookup ×6 |
| HIRA (건강보험심사평가원) | 병원 검색 | lookup ×1 |
| NMC (중앙응급의료센터) | 응급실 검색 [L3] | lookup ×1 |
| NFA119 (소방청 119) | 응급정보서비스 | lookup ×1 |
| MOHW (보건복지부) | 복지서비스 자격조회 (SSIS) | lookup ×1 |
| geocoding | resolve_location (Kakao/JUSO/SGIS) | resolve ×1 |

**Mock 어댑터 (11)**

| 분류 | 어댑터 |
|---|---|
| verify ×6 | 모바일ID, 간편인증, 금융인증서, 공동인증서, 디지털원패스, 마이데이터 |
| submit ×2 | 과태료 납부, 복지서비스 신청 |
| subscribe ×3 | CBS 재난문자, RSS 공지, data.go.kr REST-pull |

---

## Slide 15 — 테스트 & 스키마

**935 Tests**
- 928 pass / 4 skip / 3 todo / 0 fail / 0 errors
- `uv run pytest` CI 통과 (live API 테스트는 `@pytest.mark.live` skip)

**25 JSON Schema Draft 2020-12**
- `scripts/build_schemas.py` 결정론적 생성
- Pydantic v2 → 표준 JSON Schema 자동 변환
- 24 어댑터 I/O + 1 공통 envelope

**19 Visual Evidence (ink-testing-library)**
- 5-step onboarding · REPL · 권한 모달 · /agents · /consent · PDF export 등
- TUI 컴포넌트 렌더 스냅샷 검증

---

## Slide 16 — Epic 완료 & 정책 정합

**Epic 완료 현황**
- 6 Phase Epic 전체 closed (P0~P6)
- Initiative #1631 closed
- 49 sub-issues (GraphQL Sub-Issues API v2)
- 5 Deferred follow-up (#1972~#1976)

**정책 정합**
- AI Action Plan 원칙 8/9: 공공AX 단일창구 + Open API/OpenMCP
- AI Action Plan 원칙 5: 서면→열람승인 (Permission Pipeline 기본값 read-only)
- PIPA §26: 수탁자 책임 명시 (플러그인 설치 시 SHA-256 해시 게이트)
- Apache-2.0 (오픈소스)

---

# Chapter 6 — 프로젝트 관리 및 일정

## Slide 17 — 일정 & 통계

**일정**
- 2026-04-11: Initial commit (Project scaffold)
- 2026-04-24: kosmos-migration-tree.md 사용자 승인
- 2026-04-26: **v0.1-alpha 출시**

**프로젝트 통계**
| 항목 | 값 |
|---|---|
| Commits | 194 |
| PRs | 79 (전체 merged) |
| Specs | 38 (`/speckit-specify` 생성) |
| Sub-issues | 49 |
| Python LOC | 16,498 |
| TypeScript LOC | 5,935 |
| Test count | 935 |
| Adapters | 24 |

---

## Slide 18 — 협업 도구 & CI/CD

**Spec-driven 협업**
- GitHub Spec Kit: 전 단계 자동화
- Sub-Issues API v2 (GraphQL): 이슈 계층 추적
- Copilot Review Gate: CRITICAL 1건 or IMPORTANT 3건 시 fail
- Codex Review: 추가 코드 품질 검토

**CI/CD 파이프라인**
- `uv run pytest` (935 tests, 0 fail)
- Docker multi-stage build (≤ 2 GB)
- OTEL 4-tier: GenAI + Tool + Permission + Langfuse (local)
- Release manifest workflow (`docs/release-manifests/<sha>.yaml`)
- Shadow-eval workflow (prompt 변경 시 twin-run 비교)

---

## Slide 19 — 향후 로드맵

**Q2 2026 — Deferred follow-up**
- #1972: Live API regression 스위트
- #1973: In-TUI 마켓플레이스 브라우저
- #1974: Mobile/Web 포팅 탐색
- #1975: EXAONE fine-tuning 데이터셋 구축
- #1976: 정부 파일럿 MOU 검토

**Q3~Q4 2026**
- KSC 2026 발표 및 피드백 반영
- 추가 부처 어댑터 (교육부·국세청·행안부)
- Tier 2~3 플러그인 외부 기여 온보딩

---

## Slide 20 — 요약

1. **KOSMOS**는 5,000+ 한국 공공 API를 K-EXAONE-236B-A23B LLM 도구 루프로 연결하는 시민 대화형 AI 플랫폼입니다.
2. **24 어댑터 / 4 primitive / 935 tests** — 6 Phase, 38 Spec, 49 sub-issue, 79 PR을 Spec-driven 워크플로로 완성했습니다.
3. **AI Action Plan 원칙 8/9 + PIPA §26** 정합 — 학생 오픈소스(Apache-2.0)로 공공AX 레퍼런스를 제시합니다.

---

## Slide 21 — Q&A

**연락처**
- GitHub: github.com/umyunsang/KOSMOS
- Email: dbstkd5865@gmail.com

**라이선스 & 면책**
- Apache-2.0 오픈소스
- Not affiliated with LG AI Research or the Korean Government
- 학생 포트폴리오 프로젝트 (KSC 2026)

---

## Slide 22 — References

**외부 사실 출처**
- 행안부 공공데이터 활용 현황 (2024-12-31): data.go.kr/data/15076332
- OECD OURdata 지수: mois.go.kr 공공데이터 개방
- e-나라지표 공공데이터 활용 현황: idx_cd=2844
- AI Action Plan 2026-2028 PDF: 국가인공지능전략위원회, 2026.2.25
- 정부24 AI 챗봇 보도: etnews, 2026-04
- K-EXAONE-236B-A23B: huggingface.co/LGAI-EXAONE/K-EXAONE-236B-A23B
- FriendliAI K-EXAONE Serverless: friendli.ai/blog/k-exaone-on-serverless

**KOSMOS 내부 참고 자료 (학술적 인용)**
- `.references/claude-code-sourcemap/` — Claude Code 2.1.88 reconstructed source (ChinaSiro/claude-code-sourcemap)
- `.references/claude-reviews-claude/` — Claude Code architectural review analysis (openedclaude/claude-reviews-claude)
- `.references/claw-code/` — CC-compatible harness implementation (ultraworkers/claw-code)
- `.references/gemini-cli/` — Gemini CLI Apache-2.0 TUI reference (google-gemini/gemini-cli)
