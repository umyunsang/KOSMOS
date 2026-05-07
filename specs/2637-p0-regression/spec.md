# Feature Specification: Epic A — P0 회귀 즉시 복구

**Feature Branch**: `feat/2637-p0-regression`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "Epic A — P0 회귀 즉시 복구. audit `specs/cc-migration-audit/` 에서 발견된 6건 회귀 (events_mono types / Proxy stub 5 / cli/print.ts / constants/oauth.ts / utils/telemetry/instrumentation.ts / toolExecution.ts 11 no-op + Stage-1 NO-OP stub) 를 byte-copy 복원 + telemetry wire. CC source-of-truth = `.references/claude-code-sourcemap/restored-src/src/`. swap-1 종속 식별자만 교체, 그 외 골격 byte-identical."

## Background — UMMAYA CORE THESIS

UMMAYA = CC-original harness + 2 swaps (LLM=K-EXAONE on FriendliAI · Tool=한국 부처 GovAPITool/4 primitive) 만. 그 외 모든 것은 `.references/claude-code-sourcemap/restored-src/src/` 와 byte-identical 유지. 본 Epic은 audit Initiative #2636 (`specs/cc-migration-audit/`) 9-stream 결과에서 발견된 **CORE THESIS 위반 회귀 6건 + 부수 3건** 을 즉시 복구한다.

회귀의 본질: UMMAYA가 P0 baseline reconstruction 단계에서 stub 으로 남겨둔 후 hydrate 안 된 파일들 + OTEL 텔레메트리 파이프라인이 silent 가 되어버린 노드들. 모든 회귀는 swap-1/swap-2 종속이 아니므로 byte-identical 회복이 정답.

## Audit 출처

- `specs/cc-migration-audit/scope-S8-state-boot-misc.md` § P0 D-1, D-2, D-3, D-5
- `specs/cc-migration-audit/scope-S9-utils.md` § P0 #1, D6
- `specs/cc-migration-audit/scope-S2-tool-system.md` § R1
- `specs/cc-migration-audit/decisions.md` § S8 / S9 / S2

## Pre-execution 회귀 실재 확인 (2026-05-03 워크트리 grep/ls)

| # | 파일 | UMMAYA | CC | 상태 |
|---|---|---|---|---|
| 1a | `tui/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts` | 21 LOC | 865 LOC | gutted (97%) |
| 1b | `tui/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts` | 15 LOC | 223 LOC | gutted (93%) |
| 1c | `tui/src/types/generated/events_mono/common/v1/auth.ts` | **MISSING (디렉토리 자체 없음)** | exists | 누락 |
| 2a | `tui/src/constants/messages.ts` | 32 LOC Proxy stub | 1 LOC plain const | 32배 비대 stub |
| 2b | `tui/src/constants/xml.ts` | 37 LOC plain (28 export 누락) | 86 LOC | 부분 reconstruct |
| 2c | `tui/src/constants/figures.ts` | 46 LOC plain | 45 LOC | 거의 같음, export 정합성 검증 필요 |
| 2d | `tui/src/types/logs.ts` | 55 LOC Proxy stub | 330 LOC | gutted (83%) |
| 3 | `tui/src/cli/print.ts` | **MISSING** | 5594 LOC | 누락 |
| 4 | `tui/src/constants/oauth.ts` | **MISSING** | 234 LOC | 누락 |
| 5 | `tui/src/utils/telemetry/instrumentation.ts` | **MISSING** (init.ts:285 dynamic import 깨짐) | 825 LOC | 누락, 부팅 경로 silent fail 위험 |
| 6 | `tui/src/services/tools/toolExecution.ts` | inline 9 stub (line 91-100) | 1745 LOC byte-id | 본체 동일, telemetry import만 stub |
| 부수-a | `tui/src/utils/protectedNamespace.ts` | 7 LOC stub | **CC source 없음** | byte-copy 불가 |
| 부수-b | `tui/src/utils/systemThemeWatcher.ts` | 7 LOC stub | **CC source 없음** | byte-copy 불가 |
| 부수-c | `tui/src/utils/ultraplan/prompt.txt` | 1 LOC placeholder | **CC source 없음** | byte-copy 불가 |

**핵심 발견**:
- audit 본문의 "11 no-op stub" 은 정확히는 **9개** (line 91-100). 본 spec 은 9개 기준으로 진행.
- 부수 3건은 audit 권고가 "byte-copy 채우기" 였으나, CC source-of-truth 에 동일 경로 파일이 없음 (`find .references/.../src -name "protectedNamespace*"` 결과 0건). 따라서 byte-copy 불가능 — UMMAYA-only stub 정당화 (decisions.md cite + SWAP 주석) 으로 처리.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — OTEL Telemetry Pipeline 회복 (Priority: P1)

UMMAYA 운영자가 4-tier OTEL (GenAI/Tool/Permission/Langfuse) trace를 Langfuse 대시보드에서 본다. 현재 Tool layer가 silent 라 tool execution span이 누락됨. 부팅 시 `entrypoints/init.ts:285` 의 dynamic import (`utils/telemetry/instrumentation.js`) 가 throw 가능한 상태.

**Why this priority**: Spec 021 (OTEL GenAI) + Spec 028 (OTLP collector) 의 무결성 직접 종속. UMMAYA의 4-tier observability는 시민 행정 도구 신뢰성 핵심 surface. tool boundary span 누락은 디버깅·감사·SLO 측정 모두 깨짐.

**Independent Test**: `bun run tui` 부팅 후 1회 tool 호출 → Langfuse trace 에 `tool.dispatched` / `tool.completed` span 출현 확인. instrumentation.ts dynamic import 에러 0.

**Acceptance Scenarios**:

1. **Given** UMMAYA 부팅 직후, **When** `init.ts:285` 가 `utils/telemetry/instrumentation.js` dynamic import, **Then** import 성공하고 `initializeOTel()` 호출 후 OTLP exporter 활성화.
2. **Given** lookup primitive 호출 직후, **When** `toolExecution.ts` 의 9개 telemetry hook이 트리거, **Then** Spec 021 OTLP collector 가 `tool.start_span` / `tool.end_span` / `tool.content_event` 모두 수신.
3. **Given** Langfuse Docker 스택 가동, **When** TUI에서 `lookup` 1회 + `verify` 1회, **Then** Langfuse 대시보드 trace tree 에 양쪽 tool boundary span 표시.

---

### User Story 2 — Constants/Types byte-identical 회복 (Priority: P1)

UMMAYA 개발자가 `import { NO_CONTENT_MESSAGE } from 'src/constants/messages.js'` 시 CC와 동일한 plain string 상수 `'(no content)'` 가 반환되어야 한다. 현재는 UMMAYA Proxy stub 가 `Symbol.toPrimitive → ''` 로 빈 문자열 반환 → silent regression. 같은 패턴이 `xml.ts` (XML tag 28개), `figures.ts` (Unicode glyph), `logs.ts` (SerializedMessage type), `oauth.ts` (OAuth endpoint 상수), events_mono types (Buffer/Reader/Writer proto type) 에서도 발생.

**Why this priority**: Spec 2521 byte-copy bridge 의 "claude.ts 컴파일" 요건 + downstream consumer (prompt template XML wrapping, ANSI spinner glyph, log type signature) silent regression 차단. Proxy stub 는 컴파일 통과시키되 런타임에서 빈 값/잘못된 type 반환 → CC fidelity 90% 원칙 위반.

**Independent Test**: byte-identical 검증 `diff -q tui/src/constants/messages.ts .references/claude-code-sourcemap/restored-src/src/constants/messages.ts` empty (또는 swap-1 식별자만 다른 경우 화이트리스트 cite). `import` 사용 callsite (grep으로 enumerate) 가 정상 값 반환.

**Acceptance Scenarios**:

1. **Given** PORT 완료, **When** `import { NO_CONTENT_MESSAGE } from 'src/constants/messages.js'`, **Then** 정확히 `'(no content)'` 반환.
2. **Given** `xml.ts` PORT 완료, **When** prompt template `${COMMAND_NAME_TAG}` interpolation, **Then** `'command_name'` 문자열 출현, 렌더 깨짐 0.
3. **Given** `oauth.ts` PORT 완료, **When** swap-1 식별자 (Anthropic OAuth client_id 등) callsite, **Then** UMMAYA-side null 또는 K-EXAONE 식별자 반환, 그 외 골격 byte-identical (sha256 검증).
4. **Given** events_mono PORT 완료, **When** `import { Buffer, Reader, Writer } from 'src/types/generated/events_mono/.../*.js'`, **Then** type signature CC와 일치, logEvent emit 표면은 entry point 에서 차단.

---

### User Story 3 — Headless --print Mode 동작 회복 (Priority: P2)

UMMAYA 사용자 (정책 분석 자동화 스크립트 작성자) 가 `bun run tui --print "테스트 쿼리"` 로 stdin 없이 stdout 으로 LLM 응답만 받는다. 현재는 `main.tsx L1960` 가 "UMMAYA: --print / non-interactive (headless) mode is not supported" stderr 메시지로 차단.

**Why this priority**: `--print` 는 swap 무관 핵심 기능. CI/스크립트 자동화 + 정책 batch 분석 (예: "100개 민원 사례를 한꺼번에 lookup해 결과를 CSV 로") 직접 종속. CC harness 의 핵심 surface 중 하나, UMMAYA도 시민용이라도 headless 모드는 정책 분석 자동화에 필요.

**Independent Test**: `bun run tui --print "안녕"` → exit code 0, stdout 에 LLM 응답 (UTF-8), stderr 에 차단 메시지 0.

**Acceptance Scenarios**:

1. **Given** `cli/print.ts` PORT 완료 + `main.tsx` L1960 차단 제거, **When** `bun run tui --print "안녕"` 실행, **Then** exit code 0, stdout 에 K-EXAONE 응답 출현.
2. **Given** `--print` 모드, **When** stdin/stdout pipe 사용 (`echo "쿼리" | bun run tui --print -`), **Then** 정상 동작.
3. **Given** `--print` 모드 + tool 호출 발생, **When** lookup primitive 트리거, **Then** 권한 prompt 없이 fail-closed (interactive 권한 prompt 가 headless 에서 동작 불가) — 적절한 에러 메시지로 exit code 1.

---

### User Story 4 — Stage-1 NO-OP Stub 정합성 박제 (Priority: P3)

UMMAYA 개발자가 `tui/src/utils/protectedNamespace.ts` 헤더를 읽고 "이 파일이 왜 stub 으로 남아있는가?" 즉시 이해. 현재는 헤더가 "Stage-1 NO-OP stub — CC TUI Fidelity Meta-Epic 에서 wire" 라 모호. 실제로 CC source-of-truth 에 같은 경로 파일이 없으므로 byte-copy 불가 — UMMAYA-only stub 정당화 cite + SWAP 주석 박제 필요.

**Why this priority**: 잠재적 후속 회귀 차단. 향후 audit 재실행 시 이 3건이 다시 D-bucket 으로 분류되는 것 방지.

**Independent Test**: `head -5` 으로 3 파일 헤더 검증 — `// SWAP/no-cc-source: UMMAYA-original NO-OP stub. CC source 부재 (find 결과 0). decisions.md S9 § Stage-1 cite. ...` 패턴.

**Acceptance Scenarios**:

1. **Given** 3 stub 파일 헤더 박제 완료, **When** audit 재실행, **Then** D-bucket 분류 0, UMMAYA-ORIGINAL-justified bucket 으로 이동.
2. **Given** `decisions.md S9 § Stage-1` 항목, **When** 본 Epic A 종료, **Then** "byte-copy 불가 — UMMAYA-only stub 박제 처리" 로 결정 업데이트.

### Edge Cases

- `instrumentation.ts` PORT 시 OpenTelemetry SDK 의 `@grpc/grpc-js` 가 UMMAYA `package.json` 에 없을 수 있음 → dependency 추가가 새 의존성 도입(AGENTS.md 하드 룰 위반)이라면 lazy 경로 자체 차단 + 대안 wire (`@opentelemetry/exporter-otlp-http` 만 사용) 검토.
- `cli/print.ts` 5594 LOC PORT 시 내부에서 import 하는 `services/api/claude.ts` 등 swap-1 종속 의존이 UMMAYA 에서 어떻게 wire 되는지 확인. 깊은 import chain 따라가며 누락 모듈 발견 가능.
- `oauth.ts` 234 LOC PORT 시 Anthropic OAuth client_id / authorization_endpoint 등 식별자가 swap-1 종속. UMMAYA-side null 또는 K-EXAONE FriendliAI 식별자로 교체 (FriendliAI 는 OAuth flow 없음 → API key only → null 가능).
- toolExecution.ts 의 9개 stub wire 시 Spec 021 OTLP routing 호출 후 trace 가 Langfuse 에 잘못된 attribute 으로 출현하면 wire 잘못. spec 021 attribute 정의 (`ummaya.tool.id` 등) 확인 필요.
- events_mono PORT 후 logEvent 호출 표면 차단을 entry point 만으로 보장하기 어려운 경우 (deep callsite 다수), import 만 retain 하고 emit body 는 별도 wrapper 로 차단.
- Proxy stub PORT 후 기존 Proxy 패턴에 의존하던 callsite (`Symbol.iterator` 등 dynamic property access) 가 깨질 수 있음 → grep 으로 enumerate.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST PORT `tui/src/types/generated/events_mono/claude_code/v1/*.ts` (CC 865 LOC) + `growthbook/v1/growthbook_experiment_event.ts` (CC 223 LOC) + `common/v1/auth.ts` (CC 디렉토리 전체) byte-identical from `.references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/`.
- **FR-002**: System MUST PORT `tui/src/constants/messages.ts` (CC 1 LOC) + `tui/src/constants/xml.ts` (CC 86 LOC) + `tui/src/constants/figures.ts` (CC 45 LOC) + `tui/src/types/logs.ts` (CC 330 LOC) byte-identical, replacing existing Proxy stub patterns.
- **FR-003**: System MUST PORT `tui/src/cli/print.ts` (CC 5594 LOC) byte-identical from CC, AND remove the corresponding "--print not supported" stderr block in `tui/src/main.tsx` L1960.
- **FR-004**: System MUST PORT `tui/src/constants/oauth.ts` (CC 234 LOC) byte-identical, replacing only swap-1 dependent identifiers (Anthropic OAuth client_id / endpoints) with UMMAYA-side null or K-EXAONE FriendliAI equivalents. All non-swap-1 structure MUST be byte-identical.
- **FR-005**: System MUST PORT `tui/src/utils/telemetry/instrumentation.ts` (CC 825 LOC) byte-identical, ensuring `entrypoints/init.ts:285` dynamic import succeeds at boot AND `initializeOTel()` activates OTLP exporter to localhost:4318.
- **FR-006**: System MUST wire the 9 inline no-op stubs in `tui/src/services/tools/toolExecution.ts` (line 91-100) to UMMAYA Spec 021 OTEL helper functions, restoring tool boundary span emission to Langfuse via the OTLP collector.
- **FR-007**: System MUST update `tui/src/utils/protectedNamespace.ts` + `systemThemeWatcher.ts` + `ultraplan/prompt.txt` headers with `// SWAP/no-cc-source: UMMAYA-original NO-OP stub. CC source absent (find ... 0). decisions.md S9 § Stage-1 cite.` pattern.
- **FR-008**: All PORTed files MUST pass byte-identical verification (`diff -q` empty, OR diff lines confined to a documented swap-1 identifier whitelist with cite).
- **FR-009**: `bun typecheck` MUST pass (UMMAYA narrows to `src/stubs/**` only).
- **FR-010**: `bun test` MUST achieve pass count parity with current main baseline (983 pass / 1 pre-existing snapshot fail per Spec 2112 PR #2517 closure note).
- **FR-011**: `uv run pytest` MUST achieve pass count parity with current main baseline (3458 pass / 1 pre-existing per same closure).
- **FR-012**: TUI 5-layer smoke (Layer 1a Python unit / 1b Ink snapshot / 2 stdio JSONL / 3 PTY / 4 vhs / 5 tmux + waitForFrame) MUST pass per `AGENTS.md § TUI verification`.
- **FR-013**: `bun run tui --print "안녕"` MUST return exit code 0 with K-EXAONE response on stdout AND zero stderr lines containing "not supported".
- **FR-014**: Re-running the audit (`specs/cc-migration-audit/` 9-stream grep verification) on the post-merge state MUST yield zero D-bucket entries for the 9 items addressed (6 P0 + 3 ancillary).
- **FR-015**: System MUST update `specs/cc-migration-audit/decisions.md` Stage-1 row to reflect the actual resolution ("CC source absent — UMMAYA-only stub justified, headers carry SWAP cite").
- **FR-016**: System MUST create `tui/src/services/remoteManagedSettings/index.ts` as a UMMAYA-side stub-noop module exporting `waitForRemoteManagedSettingsToLoad(): Promise<void>` (returns immediately resolved Promise). Required to resolve `cli/print.ts:9` cascade import discovered during plan-stage grep. Pattern follows `tui/src/services/analytics/index.ts` (Spec 1633 P1 stub-noop replacement).

### Key Entities *(include if feature involves data)*

- **CC Source-of-Truth Mirror**: `.references/claude-code-sourcemap/restored-src/src/` — read-only Claude Code 2.1.88 byte-identical reference. All PORT operations source from this tree.
- **UMMAYA TUI Tree**: `tui/src/` — destination for PORTed files. swap-1/swap-2 dependent identifiers may diverge; structure MUST be byte-identical otherwise.
- **OTEL Telemetry Surface**: `tui/src/utils/telemetry/` — re-hydrated by FR-005 + FR-006. Bridges to Spec 021 OTLP collector at `localhost:4318`.
- **Audit Decision Log**: `specs/cc-migration-audit/decisions.md` — updated by FR-015 to close the loop on the 9 items.
- **swap-1 Identifier Whitelist**: enumerated swap-1 (LLM=K-EXAONE on FriendliAI) dependent identifiers permitted to diverge from CC. Non-whitelisted divergences fail FR-008.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 9건 회귀 (6 P0 + 3 부수) 의 grep/ls 검증 통과율 100% (pre-execution: 9건 모두 회귀, post-execution: 0건).
- **SC-002**: `bun test` pass count ≥ 983 (현 main baseline).
- **SC-003**: `bun typecheck` exit code 0 (UMMAYA narrows to `src/stubs/**`).
- **SC-004**: `uv run pytest` pass count ≥ 3458 (현 main baseline).
- **SC-005**: `bun run tui --print "안녕"` exit code 0, stdout 응답 길이 ≥ 1 byte, stderr 에 "not supported" 문자열 0회.
- **SC-006**: Langfuse trace dashboard 에서 1회 lookup primitive 호출당 `tool.dispatched` + `tool.completed` span pair 출현 (Spec 021 attribute `ummaya.tool.id` 포함).
- **SC-007**: byte-identical 검증 — PORTed 파일 중 swap-1 식별자 화이트리스트 외 diff 라인 수 0.
- **SC-008**: audit 재실행 시 `specs/cc-migration-audit/` 의 D-bucket 4 → 0 (decisions.md S8 D-1~D-3 + S9 P0-1 + S2 R1 모두 해결).
- **SC-009**: TUI 5-layer smoke 모두 통과 (Layer 1a/1b/2/3/4/5).
- **SC-010**: AGENTS.md hard rule "Never add a dependency outside a spec-driven PR" 준수 — instrumentation.ts PORT 시 OTel 패키지가 UMMAYA pyproject/package.json 에 이미 있는지 확인, 없으면 spec scope 내에서 명시적 결정.

## Assumptions

- UMMAYA의 OpenTelemetry SDK + OTLP exporter 패키지가 이미 `package.json` (TS 측) 또는 `pyproject.toml` (Python 측 Spec 021/028 종속) 에 declared. instrumentation.ts PORT 가 새 dependency 도입을 강제하지 않음. (검증 필요 — plan 단계에서 확인)
- `cli/print.ts` 5594 LOC 의 깊은 import chain 이 swap-1 종속 영역 (claude.ts 등) 으로만 이어지고, 별도 누락 모듈 발견되지 않음. (plan 단계 grep 으로 검증)
- `oauth.ts` 234 LOC 중 swap-1 종속 식별자는 OAuth client_id + authorization_endpoint + token_endpoint + scope 등 5개 이내. 그 외 (URL parser, redirect_uri 처리, PKCE state 생성) 는 swap 무관 기능이라 byte-identical 보존 가능.
- toolExecution.ts wire 대상 UMMAYA OTEL helper 가 Spec 021 의 `ummaya.tool.*` attribute 를 emit 가능. 만약 Spec 021 정식 helper 가 부족하면 inline wire 로 우회.
- Stage-1 NO-OP 3건 중 `protectedNamespace.ts` (envUtils.ts:142 require) + `systemThemeWatcher.ts` (ThemeProvider.tsx:69 dynamic import) 의 UMMAYA 에서 진짜 동작이 필요한지는 본 Epic 외부. 현 stub 으로 부팅 + 시나리오 동작 검증된 상태 유지.
- Sonnet teammate 단일 sequential 실행. 9건 모두 P0 라 같은 영역 (constants/types/utils/services) 파일 충돌 가능 → 병렬 dispatch 금지.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **events_mono logEvent emit 표면 활성화**: type 만 PORT, 실제 GrowthBook/claude.ai analytics emit 은 swap-1 종속이라 영구 차단. entry point 에서 logEvent body 호출 자체를 무력화.
- **Anthropic OAuth flow 활성화**: `oauth.ts` PORT 는 골격만, OAuth client 동작은 swap-1 종속이라 영구 비활성. K-EXAONE 은 API key only.
- **Stage-1 NO-OP 3 stub 의 진짜 UMMAYA 동작 구현**: `protectedNamespace.ts` (Node.js namespace pollution 보호) / `systemThemeWatcher.ts` (OSC 11 OS dark/light 감지) 의 UMMAYA-side 정식 구현은 별도 TUI Fidelity Meta-Epic. 본 Epic 은 stub 헤더 박제만.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| `protectedNamespace.ts` 정식 UMMAYA 구현 (Node.js global pollution 보호) | CC source 부재 + UMMAYA Specific 행정 도구 namespace 설계 별도 필요 | TUI Fidelity Meta-Epic (P4 UI L2 후속) | #2653 |
| `systemThemeWatcher.ts` 정식 UMMAYA 구현 (OSC 11 dark/light auto-detect) | CC source 부재 + UMMAYA terminal theme 4종 토글 (UI A.4) 와 통합 설계 별도 필요 | UI L2 Theme Polish Epic | #2654 |
| `ultraplan/prompt.txt` 실제 시스템 프롬프트 작성 | UMMAYA 가 ultraplan workflow 를 실제로 사용할지 결정 안 됨 (CC 의 SWE-bench 평가 도구) | Epic D (Commands/Skills 정리) cleanup 후 결정 | #2655 |
| audit `decisions.md` 의 D-4 (main.tsx PROACTIVE/BRIEF) 검증 | Spec 1633 cite 모호 — Anthropic 1P 인지 검증 필요. 본 Epic A scope 외부 | Epic D (Commands/Skills 정리) | #2656 |
| `entrypoints/sdk/` 6 파일 UMMAYA-only re-declaration audit (S8 P1-S8-4) | CC `@anthropic-ai/sdk` d.ts 와 1:1 cross-check sprint, 본 Epic 외부 | Epic E (Services swap-1 마무리) | #2657 |
| migration version 12 시작 (S8 P2-S8-5) | UMMAYA-original migration 도입 시 결정. 현재는 회귀 아님 | 별도 future Epic | #2658 |
