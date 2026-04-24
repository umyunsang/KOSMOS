# Feature Specification: P1+P2 · Dead code elimination + Anthropic → FriendliAI migration

**Feature Branch**: `1633-dead-code-friendli-migration`
**Created**: 2026-04-24
**Status**: Draft
**Input**: Epic #1633 — P1 dead-code elimination (ant-only branches · CC version migrations · CC telemetry · CC auth · CC teleport/remote) + P2 Anthropic → FriendliAI rewire (API endpoints · OAuth/model config · policy limits · MCP claudeai · entrypoint rewire · prompt loader wiring).
**Epic**: [#1633 · Dead code + Anthropic→FriendliAI migration](https://github.com/umyunsang/KOSMOS/issues/1633)
**Canonical references**:
- `docs/requirements/kosmos-migration-tree.md § 실행 Phase 순서 → P1 + P2`
- `docs/requirements/kosmos-migration-tree.md § L1-A` (LLM Harness Layer 승인)
- `docs/requirements/epic-p1-p2-llm.md` (Epic body with file-level scope)
- `docs/vision.md § 28-44` (Claude Code harness migration thesis)
- Spec 021 (OTEL observability) · Spec 026 (Prompt Registry) · Spec 032 (IPC stdio hardening)

## DX → AX migration framing *(mission context)*

Epic P0 (#1632, PR #1651) 가 CC 2.1.88 원본을 `tui/src/` 로 전량 포팅하고 컴파일·런타임을 복구했다. 하지만 지금 `tui/src/` 는 **developer 하네스의 뼈대 그대로** — `@anthropic-ai/sdk` 137 회 import, Anthropic OAuth/keychain/teleport, Datadog·GrowthBook 텔레메트리, 11 개 CC 버전 마이그레이션(`migrateSonnet45ToSonnet46.ts` 류) 이 살아있다. 시민 도메인(KOSMOS) 은 그중 대부분이 "있어서는 안 될" 코드다.

| 축 | 현재 (CC 포트 직후 baseline, Epic #1632 종료) | AX target (이 Epic 종료 시점) |
|---|---|---|
| LLM provider | `@anthropic-ai/sdk` v0.x 가 TS 에서 직접 Anthropic API 호출 (137 imports) | TS 런타임에서 `@anthropic-ai/sdk` import **0**, 모든 LLM 호출이 Spec 032 stdio IPC 경유로 Python `LLMClient` → FriendliAI Serverless → K-EXAONE 로 라우팅 |
| 모델 ID | `claude-sonnet-4-6`, `claude-opus-4-7` 등 `getDefaultMainLoopModel()` 이 Anthropic 모델 반환 | `LGAI-EXAONE/EXAONE-4.0-32B` 단일 고정 (L1-A A1 "단일 고정" 결정) |
| 인증 | Anthropic OAuth + macOS Keychain + fallback plaintext + login/logout 명령 | `FRIENDLI_API_KEY` 단일 env var, Python 백엔드만 소비 — TS 는 시크릿 0 접촉 |
| 텔레메트리 | GrowthBook 피처 플래그 · Datadog RUM · FirstParty event logger · session tracing · plugin telemetry (분석 sink 7 개 + telemetry 5 개 = 12 파일) | KOSMOS OTEL (Spec 021) 만 — `kosmos.*` semconv, 외부 egress 0 (docs/vision.md § L1-A A7 "외부 egress 0") |
| System prompt | 하드코딩 문자열이 `tui/src/constants/prompts.ts` 등에 산재 | `prompts/system_v1.md` 를 `PromptLoader` (Spec 026) 로 SHA-256 검증 후 로드 · `kosmos.prompt.hash` OTEL 속성 방출 |
| CC version migration | `migrateSonnet45ToSonnet46.ts` 외 10 개 활성 | 전량 삭제 — KOSMOS 는 버전 migration 대상 제품이 아님 (KOSMOS 최초 릴리스는 Epic 스펙 기반 clean-slate) |
| 유지보수성 | `main.tsx` 4,693 lines (에픽 body 기준 4,683) — `=== "ant"` / `ANT_INTERNAL` 가드 58+ 사이트로 비가독 | `main.tsx` ≤ 2,500 lines (aspirational: 2,000) — ant-가드 0, KOSMOS 전용 부팅 흐름만 남음 |
| 원격 제어 경로 | `remote/` (4) + `teleport.tsx` + `SessionsWebSocket` + `TeleportResumeWrapper` = CC 의 Anthropic dashboard 경유 원격 세션 | 전량 삭제 — 시민 TUI 는 로컬 단독 실행 (Phase 3 이후 별도 Initiative 에서 재설계) |

이 Epic 이 실패하면 KOSMOS 는 "Anthropic 껍데기에 FriendliAI 가 부분 주입된" 상태에 머물며, L1-A A1 (FriendliAI 단일 고정) · A7 (외부 egress 0) · Constitution Principle I (Reference-Driven Development의 rewrite boundary 준수) 을 모두 위반한다.

## User Scenarios & Testing *(mandatory)*

<!--
  Audience: 본 Epic 의 실사용자는 "시민 (citizen)" 과 "KOSMOS 기여자 (contributor)" 두 부류.
  US1 은 시민이 실제 K-EXAONE 응답을 처음 받는 end-to-end 시나리오 (product-level).
  US2/US3/US4 는 기여자 관점의 구조적 기준 (code-level measurable invariants) —
  포팅 clean-up 의 성패는 코드 수준 불변식으로만 검증 가능하기 때문.
-->

### User Story 1 — 시민이 TUI 로 K-EXAONE 응답을 받는다 (Priority: P1)

시민이 `FRIENDLI_API_KEY` 만 환경변수로 설정한 상태에서 KOSMOS TUI 를 실행하고, REPL 입력창에 "출산 보조금 신청 방법 알려줘" 를 입력한다. KOSMOS 는 CC 하네스의 agentic loop 를 그대로 사용하되 LLM 호출 엣지가 **Spec 032 stdio IPC 로 Python 백엔드를 경유**하여 FriendliAI Serverless 의 `LGAI-EXAONE/EXAONE-4.0-32B` 에 도달하고, K-EXAONE 의 첫 스트리밍 토큰이 5 초 이내에 시민 화면에 표시되기 시작한다. 시민은 "Anthropic" · "Claude" · "K-EXAONE" · "FriendliAI" 어느 단어도 볼 필요가 없다.

**Why this priority**: P1. Epic #1633 의 존재 이유 자체이며, 이것이 작동하지 않으면 P3 (tool system) · P4 (UI) · P5 (plugin DX) · P6 (docs) 의 어떤 에픽도 시민에게 전달할 가치를 만들 수 없다. 이 시나리오가 통과하는 순간이 KOSMOS 가 "공급자 교체 완료된 CC 하네스" 에서 **"시민 도메인 LLM 하네스"** 로 전환되는 지점이다.

**Independent Test**: 깨끗한 작업 디렉터리에서 `FRIENDLI_API_KEY` 만 설정 후 TUI 를 실행하고 질의 입력 → 첫 스트리밍 토큰 수신까지 5 초 이내. Python 백엔드는 `src/kosmos/llm/client.py` 의 기존 `LLMClient` 를 그대로 사용하므로, 본 Epic 의 신규 작업은 TUI 측 stdio IPC 클라이언트 + `query.ts` / `QueryEngine.ts` 의 클라이언트 인스턴스 교체 + 부팅 시 IPC 핸드셰이크 배선에 한정된다.

**Acceptance Scenarios**:

1. **Given** 시민이 `FRIENDLI_API_KEY=fr-...` 만 설정하고 `ANTHROPIC_API_KEY` 는 unset 인 상태, **When** 시민이 KOSMOS TUI 를 실행해 질의 "출산 보조금 신청 방법" 을 입력, **Then** Python 백엔드가 Spec 032 frame envelope 을 통해 LLM 요청을 수신하고 FriendliAI `/v1/chat/completions` 로 `model="LGAI-EXAONE/EXAONE-4.0-32B"` 호출을 발사하며, 첫 응답 토큰이 TUI 에 5 초 이내 스트리밍 표시된다.
2. **Given** `FRIENDLI_API_KEY` 가 unset 인 상태, **When** 시민이 TUI 를 실행, **Then** KOSMOS 는 명시적 에러 envelope("`FRIENDLI_API_KEY` 환경변수가 필요합니다 / FRIENDLI_API_KEY environment variable required") 을 표시하고 정상 종료 (uncaught exception 금지) — 절대로 Anthropic 자격증명을 찾지 않는다.
3. **Given** 시민이 TUI 실행 중 `@anthropic-ai/sdk` 가 런타임에 로드됐는지 확인하기 위해 Node/Bun 프로세스의 require-graph 를 inspection, **When** 런타임 모듈 목록을 덤프, **Then** `@anthropic-ai/sdk` 는 등장하지 않는다 (테스트 mock 제외).

---

### User Story 2 — 기여자가 `@anthropic-ai/sdk` 런타임 의존을 0 으로 본다 (Priority: P1)

KOSMOS 기여자가 fresh clone 후 `grep -rn '@anthropic-ai/sdk' tui/src --include='*.ts' --include='*.tsx'` 를 실행하면 런타임 코드 경로에서 0 개 매치가 나온다 (테스트용 `__mocks__/` 또는 `.test.ts` 제외). 동일하게 Anthropic 전용 상수(`ANT_INTERNAL`, `=== "ant"` 분기, OAuth 토큰 URL, Keychain 서비스 이름, Datadog application ID, GrowthBook SDK 키 등) 가 모두 0 매치다. `main.tsx` 는 2,500 lines 이하다.

**Why this priority**: P1. Constitution Principle I ("reference-driven development" 의 rewrite boundary — `services/api/` 만 Python stdio JSONL 로 교체, 나머지는 **구조 유지하되 Anthropic 고유 브랜치는 제거**) 의 직접 검증 기준. 이 기준이 무너지면 KOSMOS 는 "Anthropic 껍데기 + 부분 FriendliAI" 로 남아 감사 · 포팅 · 기여자 교육 모두가 복잡해진다. 또한 에픽 body "Acceptance criteria" 6 개 중 3 개(`@anthropic-ai/sdk` 0 · `logEvent` 등 0 · migration 11 개 삭제) 가 이 스토리에 속한다.

**Independent Test**: 기여자가 머지 후 브랜치에서 `grep` · `wc -l` · `find` 만으로 검증 가능. LLM 이 실행되지 않아도, Python 백엔드가 없어도, 단순 정적 분석만으로 모든 기준을 측정할 수 있다.

**Acceptance Scenarios**:

1. **Given** 머지 완료된 main 브랜치, **When** 기여자가 `grep -rln '@anthropic-ai/sdk' tui/src --include='*.ts' --include='*.tsx' | grep -v '__mocks__\|\.test\.\|\.spec\.'` 실행, **Then** 0 파일.
2. **Given** 동일 브랜치, **When** `grep -rln 'ANT_INTERNAL\|=== "ant"' tui/src --include='*.ts' --include='*.tsx'` 실행, **Then** 0 파일.
3. **Given** 동일 브랜치, **When** `ls tui/src/migrations/migrate*.ts tui/src/migrations/reset*.ts 2>/dev/null | wc -l` 실행, **Then** 0 (11 개 CC 버전 마이그레이션 파일 전량 삭제 확인).
4. **Given** 동일 브랜치, **When** `grep -rln 'logEvent\|profileCheckpoint\|growthbook\|statsig' tui/src --include='*.ts' --include='*.tsx' | grep -v '\.test\.'` 실행, **Then** 0 파일.
5. **Given** 동일 브랜치, **When** `wc -l tui/src/main.tsx` 실행, **Then** 2,500 이하 (목표 2,000, 상한 2,500).

---

### User Story 3 — CC telemetry · auth · teleport 경로가 TUI 에서 호출 불가 (Priority: P2)

기여자가 TUI 를 부팅하면 Anthropic OAuth handshake · macOS Keychain 접근 · Datadog RUM 초기화 · GrowthBook 피처 플래그 fetch · Anthropic teleport 세션 관리 등 CC 내부 전용 경로가 어떤 코드도 실행하지 않는다. 관련 16+ 파일군(analytics 7 + telemetry 5 + secureStorage 6 + oauth 5 + login/logout 2 + remote 4 + teleport 2 + remoteManagedSettings/securityCheck 1 + background/remote 2 + policyLimits 3 + claudeAiLimits 1 + mcp/claudeai 1 + internalLogging 1 + api/bootstrap/usage/overage/referral/admin/grove 6) 이 삭제 또는 stub-noop 으로 치환됐다.

**Why this priority**: P2. 시민 경험에 "직접 보이는" 것은 US1 이지만, US3 이 미완이면 KOSMOS 는 오프라인 공공 환경에서 **외부 egress 가 발생하는 리스크** (L1-A A7 위반) · **Anthropic 서버에 실제로 연결 시도** (PIPA §26 수탁자 책임과 충돌) · **CC 개발자 계정 UX 가 시민 앞에 노출** 의 조합 위험을 남긴다. 법·규정·브랜드 무결성 모두를 깎는다.

**Independent Test**: 기여자가 `tcpdump` 나 dev-tools 없이도 `ls` · `find` · `grep` 만으로 삭제를 확인할 수 있고, `bun test` 가 모든 경로에 대해 "import 실패 없음 + 테스트 녹색" 으로 회귀 없음을 증명.

**Acceptance Scenarios**:

1. **Given** 머지 완료, **When** `ls tui/src/services/services/analytics/ tui/src/utils/telemetry/ tui/src/utils/secureStorage/ tui/src/services/services/oauth/ tui/src/remote/ 2>/dev/null` 실행, **Then** 모두 디렉터리가 존재하지 않거나 내부 파일이 0 (또는 KOSMOS-대체 파일만 존재).
2. **Given** 동일 브랜치, **When** `find tui/src -name 'claudeai*.ts' -o -name 'antModels.ts' -o -name 'betas.ts' -o -name 'modelCost.ts' -o -name 'policyLimits' -type d 2>/dev/null` 실행, **Then** 전량 삭제 상태 (또는 KOSMOS-대체 파일 명시).
3. **Given** 동일 브랜치, **When** 기여자가 `tui/src/entrypoints/init.ts` 를 열어 `initializeTelemetryAfterTrust` 호출을 찾음, **Then** 해당 호출은 삭제되고 대신 Spec 021 기준 KOSMOS OTEL init (예: `initKosmosOtel()`) 호출이 배치돼 있음.
4. **Given** 동일 브랜치, **When** `bun test` 전량 실행, **Then** 실패 0 — "모듈 해석 실패" 또는 "삭제된 symbol 참조 누락" 에 의한 회귀 0.

---

### User Story 4 — System prompt 가 `PromptLoader` 경유로 로드 (Priority: P3)

TUI 가 첫 LLM 호출을 발사하는 시점에 system prompt 는 Spec 026 `PromptLoader` 가 `prompts/manifest.yaml` 의 SHA-256 정합성 검증을 통과한 `prompts/system_v1.md` 내용이어야 한다. 하드코딩된 `const SYSTEM_PROMPT = "You are Claude..."` 같은 문자열은 TUI 런타임 코드에서 0 매치. OTEL 스팬 `gen_ai.client.invoke` 에는 `kosmos.prompt.hash` 속성이 빈값이 아닌 채 기록된다.

**Why this priority**: P3. US1-US3 이 갖춰지면 **운영 가능한 하네스** 는 이미 완성되며, PromptLoader 배선은 Ops 측 traceability 강화 성격. 다만 Spec 026 는 이미 `src/kosmos/prompts/` 에 manifest + hash 검증 + Langfuse 옵션 까지 구현됐으므로 본 Epic 에서 TUI 경로에 **입구만 맞추면** 된다. 추가 구현 부담 < 1 태스크.

**Independent Test**: TUI 가 첫 LLM 호출을 발사하는 단위 테스트 하나를 실행하고 (mocked Python backend), 전달된 messages 의 `system` 필드가 `prompts/system_v1.md` 파일 내용과 바이트 단위 일치하며 OTEL 스팬의 `kosmos.prompt.hash` 속성이 해당 파일의 SHA-256 과 일치함을 어서트.

**Acceptance Scenarios**:

1. **Given** 머지 완료, **When** TUI 가 첫 LLM 호출을 준비, **Then** system prompt 는 `PromptLoader` 가 manifest 검증 후 반환한 `system_v1.md` 내용이다.
2. **Given** `prompts/system_v1.md` 내용이 조작되어 SHA-256 해시가 manifest 값과 불일치, **When** TUI 부팅, **Then** KOSMOS 는 fail-closed 로 부팅 거부하고 명시적 에러 표시 (Spec 026 FR).
3. **Given** 첫 LLM 호출이 발사됨, **When** 생성된 OTEL 스팬을 확인, **Then** `kosmos.prompt.hash` 속성이 존재하며 값이 `prompts/system_v1.md` 의 SHA-256 과 일치.

---

### Edge Cases

- **`FRIENDLI_API_KEY` 누락**: TUI 는 명시적 에러 envelope 로 시민에게 안내하고 정상 종료 (uncaught exception 금지).
- **Python 백엔드 미기동 또는 stdio IPC 핸드셰이크 실패**: TUI 는 "LLM 연결 불가 · 관리자에게 문의" envelope 표시 + 로컬 재시도 정책 (Spec 032 Story 1 의 resume 의미와 일관).
- **`prompts/system_v1.md` hash mismatch**: Spec 026 fail-closed 로 부팅 거부 + 위치/해시 기록.
- **`filesApi.ts` FriendliAI 호환성 미확정**: 플랜 Phase 0 에서 최종 keep-or-delete 판단 (현 spec 은 결정을 강제하지 않음 · Deferred Items 표에 추적).
- **`withRetry.ts` 의 Anthropic-specific 에러 코드**: FriendliAI HTTP 에러 코드 집합으로 재매핑하되 retry 논리 (exponential backoff · max attempts) 는 유지.
- **테스트 경로의 `@anthropic-ai/sdk` 사용 (mock/stub)**: 테스트에서 타입 호환성을 위해 남길 수 있으나, 런타임 코드 경로에서는 0.

## Requirements *(mandatory)*

### Functional Requirements

**Runtime dependency elimination (P1 scope — dead code)**:
- **FR-001**: TUI 런타임 코드(`tui/src/**/*.{ts,tsx}`, 단 `__mocks__/` 또는 `*.test.*` 제외) 에 `@anthropic-ai/sdk` 의 런타임 import(`import ... from '@anthropic-ai/sdk/...'` · `require('@anthropic-ai/sdk')` 형태)는 **0** 이어야 한다. Type-only import 도 함께 제거하거나 KOSMOS 자체 타입으로 교체한다.
- **FR-002**: `tui/src/migrations/migrate*.ts` 와 `tui/src/migrations/reset*.ts` 중 CC 버전 마이그레이션 11 개 파일을 전량 삭제한다. (파일 목록은 Epic body `docs/requirements/epic-p1-p2-llm.md § CC Migrations`.)
- **FR-003**: `ANT_INTERNAL` 식별자와 `=== "ant"` 패턴의 가드 분기(Epic body 기준 58+ 사이트, 10 개 파일) 를 전부 제거하고 해당 코드 블록(분기의 Anthropic-only 측)을 함께 삭제한다.
- **FR-004**: CC telemetry 자산을 제거한다 — `tui/src/services/services/analytics/` (7 파일), `tui/src/utils/telemetry/` (5 파일), `tui/src/types/types/generated/events_mono/`, `tui/src/services/services/internalLogging.ts`. 호출부(`logEvent` · `profileCheckpoint` · `growthbook` · `statsig`) 도 함께 제거하거나 KOSMOS OTEL 호출로 대체한다.
- **FR-005**: CC auth 자산을 제거한다 — `tui/src/utils/auth.ts`, `tui/src/utils/secureStorage/` (6 파일), `tui/src/services/services/oauth/` (5 파일), `tui/src/commands/login/*`, `tui/src/commands/logout/*`. Slash command 레지스트리에서 `/login`·`/logout` 노출도 함께 제거.
- **FR-006**: CC teleport / remote 자산을 제거한다 — `tui/src/remote/` (4 파일), `tui/src/services/services/remoteManagedSettings/securityCheck.tsx`, `tui/src/utils/teleport.tsx`, `tui/src/utils/teleport/gitBundle.ts`, `tui/src/utils/background/remote/remoteSession.ts`, `tui/src/utils/background/remote/preconditions.ts`, `tui/src/components/TeleportResumeWrapper.tsx`, `tui/src/hooks/useTeleportResume.tsx`.

**Anthropic → FriendliAI rewire (P2 scope — replace or strip)**:
- **FR-007**: `tui/src/services/services/api/claude.ts` · `client.ts` 를 KOSMOS stdio IPC 클라이언트(Spec 032 frame envelope) 로 재배선한다. TS 에서 직접 FriendliAI HTTPS 호출은 하지 않는다 — LLM 호출은 반드시 Python 백엔드 경유.
- **FR-008**: Anthropic 전용 API 파일(`bootstrap.ts`, `usage.ts`, `overageCreditGrant.ts`, `referral.ts`, `adminRequests.ts`, `grove.ts`, 그리고 `tui/src/services/api/` 경로의 중복 stub `overageCreditGrant.ts` · `referral.ts` · `errors.ts`) 을 전량 삭제한다.
- **FR-009**: `tui/src/services/services/api/filesApi.ts` 는 plan Phase 0 에서 keep-or-delete 를 결정한다 (본 spec 은 강제하지 않음). 결정 근거와 최종 상태는 plan `research.md` 에 기록.
- **FR-010**: `tui/src/constants/constants/oauth.ts` 의 Anthropic OAuth 상수(토큰 URL · 클라이언트 ID · 리디렉션 URI 등) 를 제거하고 KOSMOS 용 환경변수 상수(`FRIENDLI_API_KEY` 이름만, 실제 값은 Python 백엔드가 소비) 로 교체한다. OAuth 플로 자체는 제거 (TUI 는 API-key 기반만).
- **FR-011**: `tui/src/utils/model/antModels.ts::getDefaultMainLoopModel()` (및 동등 함수) 반환값이 `"LGAI-EXAONE/EXAONE-4.0-32B"` 이어야 한다. Anthropic 모델 ID 는 TUI 어디에도 런타임 참조가 없다.
- **FR-012**: `tui/src/utils/modelCost.ts` 의 Anthropic 토큰 가격표를 제거한다 (KOSMOS 는 사용량 집계를 Python 백엔드 `UsageTracker` 가 수행).
- **FR-013**: `tui/src/utils/betas.ts` 의 Anthropic beta-header 관리를 제거한다.
- **FR-014**: `tui/src/services/services/policyLimits/index.ts` · `types.ts` · `tui/src/services/services/claudeAiLimits.ts` 를 전량 삭제한다. 시민 쿼터 정책의 KOSMOS-등가물 재설계는 본 Epic 범위 밖 (Deferred Items 표 "시민 쿼터 정책" 행 참조).
- **FR-015**: `tui/src/services/services/mcp/claudeai.ts` (Anthropic MCP 통합) 을 삭제한다. KOSMOS-scoped MCP 재도입은 본 Epic 범위 밖 (Deferred Items 표 "Anthropic MCP 통합 재도입" 행 참조).
- **FR-016**: `tui/src/entrypoints/init.ts` 의 `initializeTelemetryAfterTrust` 호출(및 관련 부팅 순서 코드) 을 Spec 021 기준 KOSMOS OTEL 초기화 함수 호출로 대체한다.
- **FR-017**: `tui/src/query.ts` 와 `tui/src/QueryEngine.ts` 에서 `@anthropic-ai/sdk` 로부터 인스턴스화하는 클라이언트 객체를 KOSMOS stdio IPC 클라이언트(TS) 가 노출하는 `llmComplete` 또는 동등 메서드로 대체한다. Agentic loop 구조(메시지 턴, tool-use 디스패치) 는 보존 — AGENTS.md 의 rewrite boundary 원칙 준수.
- **FR-018**: `tui/src/services/services/api/withRetry.ts` 의 재시도 로직(exponential backoff · max attempts) 은 유지하되, 매칭되는 에러 코드 집합을 FriendliAI HTTP 에러 및 stdio IPC 전송 에러 집합으로 재매핑한다.
- **FR-019**: `tui/src/services/services/api/errors.ts` · `errorUtils.ts` 의 구조(에러 계층 · 사용자 친화 메시지 매핑) 는 유지하되, Anthropic-specific 에러 코드(`invalid_request_error` Anthropic 변형, `overloaded_error` 등) 는 제거하고 KOSMOS 에러 envelope(LLM · Tool · Network 3 종, Spec 032 frame 기준) 로 매핑.
- **FR-020**: `tui/src/services/services/api/promptCacheBreakDetection.ts` 는 FriendliAI 가 프롬프트 캐시 토큰을 노출하는 경우에 한해 유지하고, 그렇지 않으면 plan Phase 0 에서 삭제 결정한다. 결정 근거는 `research.md` 에 기록.

**Prompt Registry 연계 (P3 scope — ops)**:
- **FR-021**: TUI 의 system prompt 조립 경로는 Spec 026 `PromptLoader` 를 경유하여 `prompts/system_v1.md` 를 로드한다 (Python 백엔드가 로드 후 IPC 응답 메시지로 TUI 에 전달하거나, TUI 가 Python 백엔드의 `PromptLoader` 결과를 RPC 로 조회 — 결정은 plan Phase 0). 하드코딩된 system prompt 문자열은 TUI 런타임 코드에서 0 매치여야 한다.
- **FR-022**: 첫 LLM 호출을 감싸는 OTEL 스팬(`gen_ai.client.invoke` 또는 동등) 에 `kosmos.prompt.hash` 속성이 기록되며 값은 로드된 `system_v1.md` 의 SHA-256 과 일치한다.

**회귀 방어**:
- **FR-023**: Epic P0 (#1632) 에서 확정된 `bun test` 통과 수 floor (≥ 540) 는 본 Epic 종료 시점에도 유지되어야 한다. 대량 삭제로 인한 테스트 회귀는 허용되지 않으며, 삭제되는 symbol 에 의존하는 테스트는 같은 PR 에서 함께 삭제 또는 KOSMOS-등가물로 대체한다.
- **FR-024**: `bun run tui` 로 TUI 를 실행했을 때 US1 Acceptance Scenarios 1-2 의 가시적 거동이 재현되어야 한다 (시각 검증 · PR 본문에 스크린샷 첨부).

### Key Entities *(include if feature involves data)*

본 Epic 은 주로 **코드 삭제 · 배선 교체** 성격이므로 신규 데이터 엔티티 정의는 없다. 다만 다음 기존 엔티티와의 관계가 변경된다:

- **`FriendliAI LLM request`**: TS TUI 에서 발사되던 Anthropic `Messages.create` 요청이 Spec 032 frame envelope (`payload_start` · `payload_delta` · `tool_result` · `trailer`) 경유 Python 백엔드 `LLMClient` 요청으로 경로 변경.
- **`KOSMOS OTEL span`**: Anthropic telemetry 가 방출하던 Datadog RUM 이벤트 · GrowthBook 피처 이벤트가 제거되고, Spec 021 의 `kosmos.*` semconv OTEL 스팬만 남음. 신규로 `kosmos.prompt.hash` 속성 필드가 첫 LLM 호출 스팬에 추가.
- **`TUI → Python IPC frame`**: Spec 032 의 `correlation_id` · `transaction_id` envelope 에 LLM request/response 페이로드가 실림. 본 Epic 은 새로운 IPC 메시지 타입을 정의하지 않으며, Spec 032 가 정의한 envelope 안에 LLM 메시지를 packing 하는 방식만 확정 (plan Phase 0).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 시민이 `FRIENDLI_API_KEY` 만 설정 후 TUI 를 실행해 첫 질의를 보내면 K-EXAONE 의 첫 스트리밍 토큰이 **5 초 이내** 에 TUI 에 표시된다 (mocked 또는 실제 FriendliAI 엔드포인트 대상, 로컬 Dev 환경).
- **SC-002**: 머지 완료된 main 브랜치에서 `grep -rln '@anthropic-ai/sdk' tui/src --include='*.ts' --include='*.tsx' | grep -v '__mocks__\|\.test\.\|\.spec\.'` 의 결과가 **0 파일**.
- **SC-003**: `wc -l tui/src/main.tsx` 의 결과가 **≤ 2,500 lines** (목표 2,000, 상한 2,500 · 안전 마진 500).
- **SC-004**: `ls tui/src/migrations/migrate*.ts tui/src/migrations/reset*.ts 2>/dev/null | wc -l` 의 결과가 **0** (CC 버전 마이그레이션 11 개 파일 전량 삭제).
- **SC-005**: `grep -rln 'logEvent\|profileCheckpoint\|growthbook\|statsig' tui/src --include='*.ts' --include='*.tsx' | grep -v '\.test\.'` 의 결과가 **0 파일** (CC 텔레메트리 호출 전량 제거).
- **SC-006**: `grep -rln 'ANT_INTERNAL\|=== "ant"' tui/src --include='*.ts' --include='*.tsx'` 의 결과가 **0 파일**.
- **SC-007**: `bun test` 통과 수가 **≥ 540** (Epic #1632 P0 확정 floor 유지) 이며 실패 0.
- **SC-008**: 첫 LLM 호출에 대응하는 OTEL 스팬(`gen_ai.client.invoke`) 의 `kosmos.prompt.hash` 속성이 **공백이 아니며** `prompts/system_v1.md` 의 SHA-256 과 일치.
- **SC-009**: `bun run tui` 로 TUI 를 실행한 후 `lsof -p <tui-pid>` 또는 동등한 방법으로 확인한 모든 열린 HTTPS 커넥션이 **FriendliAI 도메인 이외의 외부(Anthropic · Datadog · GrowthBook · Statsig) 도메인에 연결되지 않음**.
- **SC-010**: TUI 런타임 코드에서 `getDefaultMainLoopModel()` 또는 그 호출 경로를 정적 분석한 결과 반환값 상수가 **`"LGAI-EXAONE/EXAONE-4.0-32B"` 단일 값**.

## Assumptions

- Epic P0 (#1632, PR #1651) 가 2026-04-24 에 main 에 머지되었고, CC 2.1.88 restored-src 의 1,884 개 `.ts/.tsx` 파일이 `tui/src/` 에 완전 복제된 상태 (본 세션에서 검증 완료).
- `FRIENDLI_API_KEY` CI secret 이 Epic P0 범위에서 이미 배선됨 (Spec 026 `.env` 보호 + Infisical OIDC 경로 존재).
- **TUI 는 FriendliAI 에 직접 HTTPS 호출을 하지 않는다**. 모든 LLM 호출은 Spec 032 stdio IPC frame envelope 을 거쳐 Python 백엔드 `src/kosmos/llm/client.py::LLMClient` (964 lines, 이미 구현) 가 대행한다. 이 결정은 `docs/vision.md § L1-A A1` 와 AGENTS.md 의 rewrite boundary ("`services/api/` 만 KOSMOS Python 백엔드 over stdio JSONL") 에서 도출된 확정 의사결정이며, 본 Epic 은 이 전제를 받아들인다.
- Spec 032 frame envelope 이 LLM 스트리밍 토큰 · tool-call trailer · 최종 응답을 전달 가능하다는 점은 Spec 032 Story 1 의 "시민이 놓친 모든 중간 응답(LLM 스트리밍 토큰 + tool-call trailer + 최종 답변)을 순서 유지한 채 재전송" 문구로 확인됨.
- 모델 ID `"LGAI-EXAONE/EXAONE-4.0-32B"` 는 `docs/requirements/kosmos-migration-tree.md § L1-A A1` 에서 "FriendliAI serverless + K-EXAONE 단일 고정" 으로 승인됨. FriendliAI 공개 모델 카탈로그에서의 정확한 ID 스펠링 확인은 plan Phase 0 에서 마무리.
- `main.tsx` 의 2,000 line 목표는 Epic body 의 aspirational 수치이며, 본 spec 은 2,500 을 hard floor 로 두고 2,000 을 best-effort 로 관리한다 — 58+ ant-guard 사이트 제거 + 부팅 시 login/logout 호출 삭제 + telemetry init 간소화 분석 기반.
- `bun test` floor 540 은 Epic #1632 P0 에서 확정된 값이며, 대량 삭제로 테스트가 일부 invalidate 되면 같은 PR 에서 해당 테스트를 삭제 또는 KOSMOS-등가물로 교체한다.
- Spec 026 `PromptLoader` 는 Python 백엔드 측에 이미 구현되어 있고 manifest SHA-256 검증이 동작 중이다 (Spec 026 스펙 + plan 완료 상태). 본 Epic 에서 TUI 측 작업은 "system prompt 를 하드코딩하지 말고 백엔드가 응답한 값을 쓰라" 배선 수준.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Anthropic 이외의 LLM provider 지원**: L1-A A1 이 "FriendliAI serverless + K-EXAONE 단일 고정" 을 승인한 상태. 다중 provider 스위칭은 KOSMOS 의 디자인 원칙 위반이며 영구 제외.
- **모바일/웹 네이티브 LLM 호출 경로**: KOSMOS 는 TUI 단말 기준 설계. Anthropic 의 teleport/remote/SessionsWebSocket 구조는 재도입되지 않는다 (CC 의 개발자 워크스테이션 멀티-디바이스 재개 UX 는 시민 도메인에 불필요).
- **CC 버전 마이그레이션 메커니즘**: KOSMOS 는 Epic 스펙 기반 clean-slate 릴리스를 채택. "Sonnet 4.5 → Sonnet 4.6 설정 마이그레이션" 같은 인플레이스 버전 업그레이드 개념 자체가 없음.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Tool system 재설계 (CC `Tool.ts` 인터페이스 → KOSMOS primitive · live/mock 2-tier · plugin 인프라) | Epic body 에 "Out of scope (P3)" 로 명시. L1-B 승인 사항이며 별도 에픽에서 다룸. | Epic P3 (#1634) · Spec 031 연계 | NEEDS TRACKING |
| UI component 한국어 포팅 (REPL · Onboarding 5-step · Permission Gauntlet · Ministry Agent) | Epic body 에 "Out of scope (P4)" 로 명시. UI L2 승인 사항이며 Spec 035 후속. | Epic P4 (#1635) · Spec 035 후속 | NEEDS TRACKING |
| Plugin DX (template · guide · examples · submission · registry · 한국어 primary · PIPA 수탁자 책임) | Epic body 에 "Out of scope (P5)" 로 명시. L1-B B8 승인 사항. | Epic P5 (#1636) | NEEDS TRACKING |
| docs/api 정리 (어댑터별 Markdown + JSON Schema/OpenAPI + index · L1-B B7) | Epic body 에 "Out of scope (P6)" 로 명시. | Epic P6 (#1637) | NEEDS TRACKING |
| `filesApi.ts` 의 FriendliAI Files API 호환성 최종 판정 및 TUI 경로 존속 여부 | FriendliAI 공개 문서의 Files API 스펙을 plan Phase 0 에서 조사 후 결정. 현 시점에서는 reasonable default 불가능. | Plan Phase 0 (본 Epic 내부) | PLAN-PHASE-0 |
| `promptCacheBreakDetection.ts` 의 FriendliAI 프롬프트 캐시 토큰 지원 여부 조사 및 유지/삭제 결정 | FriendliAI Serverless 의 프롬프트 캐시 노출 방식이 Anthropic 과 다를 수 있음. 현 시점에서 단정 불가. | Plan Phase 0 (본 Epic 내부) | PLAN-PHASE-0 |
| 시민 쿼터 정책 (과거 `policyLimits/*`, `claudeAiLimits.ts` 의 KOSMOS-등가물) | 본 Epic 은 삭제만 수행. 시민용 쿼터 정책은 PIPA 수탁자 책임 + 부처 API 한도 집계와 엮이므로 별도 Initiative 필요. | 후속 Initiative (미지정) | NEEDS TRACKING |
| Anthropic MCP 통합 (`mcp/claudeai.ts`) 의 KOSMOS-scoped 재도입 | 본 Epic 은 Anthropic MCP 만 제거. KOSMOS MCP 통합은 별도 후속 에픽에서 재도입 설계. | 후속 MCP 에픽 | NEEDS TRACKING |
