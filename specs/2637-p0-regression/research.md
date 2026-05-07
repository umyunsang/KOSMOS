# Phase 0 Research — Epic A P0 회귀 즉시 복구

**Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-05-03

## docs/vision.md § Reference materials 인용

이 Epic 의 모든 PORT 결정은 UMMAYA Constitution Principle I "Reference-Driven Development" 의 primary migration source — `.references/claude-code-sourcemap/restored-src/src/` (Claude Code 2.1.88) — 에서 직접 파생. AGENTS.md § CORE THESIS 가 강제하는 "UMMAYA = CC + 2 swap만, byte-identical default" 의 직접 위반 영역을 회복한다. 4개 핵심 결정 모두 docs/vision.md § Reference materials 의 Layer 매핑에 anchor.

## D1 — `instrumentation.ts` byte-copy PORT + 8개 OTel dependency 추가

### Decision

CC `restored-src/src/utils/telemetry/instrumentation.ts` (825 LOC) 를 byte-identical 로 PORT. swap-1 종속 import (`auth.ts` helpers — `is1PApiCustomer`, `isClaudeAISubscriber`, `getOtelHeadersFromHelper`, `getSubscriptionType`) 는 UMMAYA `tui/src/utils/auth.ts` (이미 Spec 1633 stub 으로 export) 가 자동 충족. swap-1 종속 telemetry helper (`./betaSessionTracing.js`, `./bigqueryExporter.js`, `./logger.js`, `./perfettoTracing.js`, `./sessionTracing.js`) 는 UMMAYA-side minimal stub 으로 import resolution 충족. `tui/package.json` 에 8개 OTel/gRPC 의존성 추가:

```json
"@opentelemetry/semantic-conventions": "^1.30.0",
"@opentelemetry/exporter-trace-otlp-http": "^0.215.0",
"@opentelemetry/exporter-trace-otlp-grpc": "^0.215.0",
"@opentelemetry/exporter-logs-otlp-http": "^0.215.0",
"@opentelemetry/exporter-logs-otlp-grpc": "^0.215.0",
"@opentelemetry/exporter-metrics-otlp-http": "^0.215.0",
"@opentelemetry/exporter-metrics-otlp-grpc": "^0.215.0",
"@grpc/grpc-js": "^1.12.0"
```

### Rationale

- **AGENTS.md 하드 룰 "spec-driven PR" 조건 충족**: 본 spec 이 plan 단계에서 명시적으로 8개 deps 결정 → 하드 룰 위반 0.
- **Spec 021 (OTEL GenAI v1.40) + Spec 028 (OTLP collector) 의 TS-측 surface 회복**: `entrypoints/init.ts:284` 의 dynamic import 가 silent fail 되던 경로 복구. 4-tier OTEL Tool layer 의 client-side trace 가 Langfuse 에 emit.
- **CC byte-identical 원칙**: `instrumentation.ts` 본체 825 LOC 그대로 보존. UMMAYA 가 OTel 표면을 재발명하지 않음.
- **OTLP HTTP + gRPC 양쪽 모두 PORT**: CC 가 `OTEL_EXPORTER_OTLP_PROTOCOL` env var 로 분기 — UMMAYA 가 어느 쪽이든 사용할 수 있게 양쪽 deps 모두 추가.

### Alternatives considered

- **A. instrumentation.ts 본체 stub 유지**: 거부 — Spec 021 4-tier OTEL TS-측 surface silent. Spec 028 OTLP collector 가 Python-측 spans 만 받아 GenAI/Tool layer 의 client-side trace 누락. CC byte-identical 원칙 위반.
- **B. instrumentation.ts 의 OTLP/gRPC 분기 disabled, HTTP-only minimal PORT**: 거부 — `parseExporterTypes()` (line 121) + `bootstrapTelemetry()` (line 87) 의 분기 로직이 byte-identical 보존 안됨. UMMAYA 가 향후 gRPC 사용 결정 시 다시 PORT 필요 → 현재 한 번에 완료.
- **C. CC swap-1 종속 telemetry helper (perfetto, bigquery, logger 등) 까지 cascade PORT**: 거부 — 모두 Anthropic 1P 종속, UMMAYA 무의미. minimal stub 으로 import resolution 만 충족이 정답.

## D2 — `toolExecution.ts` 9 stub wire 가 UMMAYA-side OTEL helper 직접 사용

### Decision

`tui/src/services/tools/toolExecution.ts` line 91-100 의 9개 inline no-op stub 을 UMMAYA-side OTEL helper 로 wire. wire 대상은 `tui/src/utils/telemetry/sessionTracing.ts` 를 확장하거나 신규 `tui/src/utils/telemetry/toolSpans.ts` 를 만들어 Spec 021 attribute (`ummaya.tool.id`, `ummaya.tool.outcome`, `ummaya.tool.duration_ms` 등) 를 emit. 9개 함수 시그니처:

```ts
logOTelEvent(eventName: string, attrs?: Record<string, unknown>): Promise<void>
addToolContentEvent(span: Span | null, contentAttrs: Attributes): void
endToolBlockedOnUserSpan(reason: string, source: string): void
endToolExecutionSpan(result: { success: boolean; error?: string }): void
endToolSpan(toolResultStr?: string): void
isBetaTracingEnabled(): boolean
startToolBlockedOnUserSpan(span: Span | null): null
startToolExecutionSpan(span: Span | null, name: string): Span | null
startToolSpan(name: string, attrs: Attributes): Span | null
```

UMMAYA 가 `@opentelemetry/api` 의 `trace.getTracer('ummaya.tools')` 를 직접 사용해 spans 생성. instrumentation.ts (D1) 가 부팅 시 TracerProvider 등록 → toolExecution wire 가 자동 라우팅 → OTLP collector → Langfuse.

### Rationale

- **Cascade PORT 폭발 회피**: CC `events.ts` (75 LOC) + `sessionTracing.ts` (927 LOC) + `betaSessionTracing.ts` (491 LOC) + `perfettoTracing.ts` + `bigqueryExporter.ts` + `logger.ts` 모두 swap-1 종속 (Anthropic 1P GrowthBook + BigQuery + Perfetto). 7+ files cascade PORT 후 다시 stubbing 필요 → 의미 0.
- **swap-5 (Observability) 정당성**: UMMAYA 의 4-tier OTEL 은 이미 Spec 021 에서 정당화된 UMMAYA 발산. CC 의 statsig/GrowthBook 기반 베타 trace 와 UMMAYA Spec 021 OTLP routing 은 다른 백엔드. 이 영역 UMMAYA-original 정당.
- **Spec 021 attribute 정합**: `ummaya.tool.id`, `ummaya.tool.outcome` 등 UMMAYA 정의 attribute 를 직접 emit → Langfuse trace tree 에서 일관성.

### Alternatives considered

- **A. CC 7-file telemetry cascade PORT**: 거부 — swap-1 cascade 폭발 + Spec 021 attribute 와 attribute namespace 충돌 (`ummaya.*` vs `claude_code.*`).
- **B. 현재 9 inline stub 유지**: 거부 — Spec 021 4-tier OTEL Tool layer silent. spec FR-006 + SC-006 직접 위반.
- **C. CC events.ts (75 LOC) 만 PORT, sessionTracing 함수만 wire**: 거부 — events.ts 가 `getEventLogger()`, `getPromptId()` 등 bootstrap/state.js 종속 → UMMAYA bootstrap/state.ts 에 이미 모두 있어 PORT 가능하지만, Spec 021 attribute 와 다른 emit 표면 (`logOTelEvent`) 운영 복잡도 증가. 단일 UMMAYA helper 로 통합이 정답.

## D3 — `cli/print.ts` byte-copy PORT + 누락 cascade `remoteManagedSettings/index.ts` UMMAYA-side stub 신설

### Decision

CC `restored-src/src/cli/print.ts` (5594 LOC) 를 byte-identical 로 PORT. cascade dependency 검증 결과:

- ✅ `services/settingsSync/` — UMMAYA 에 존재 (index.ts + types.ts)
- ✅ `services/analytics/` — UMMAYA 에 존재 (Spec 1633 stub-noop replacement)
- ❌ `services/remoteManagedSettings/` — UMMAYA 에 누락. `cli/print.ts:9` 에서 `import { waitForRemoteManagedSettingsToLoad } from 'src/services/remoteManagedSettings/index.js'` 가 import resolution 실패 위험.

→ UMMAYA-side stub 신설 (`tui/src/services/remoteManagedSettings/index.ts`):

```ts
// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #2637 cascade · stub-noop replacement for CC remoteManagedSettings.
// SWAP/anti-anthropic-1p(2637): Anthropic enterprise managed settings (claude.ai 1P)
// surface is dead in UMMAYA. CC's print.ts cascade requires this import to resolve.
// Pattern follows tui/src/services/analytics/index.ts (Spec 1633 P1).

export async function waitForRemoteManagedSettingsToLoad(): Promise<void> {
  // Intentional no-op (Epic #2637 stub). Anthropic remote managed settings (claude.ai 1P)
  // is swap-1 dependent — permanently disabled in UMMAYA.
}
```

`main.tsx` L1960 의 "--print not supported" stderr 차단 메시지 제거. `cli/print.ts` 의 swap-1 종속 식별자 (e.g., `process.env.USER_TYPE === 'ant'` 가드 + `feature('PRINT_REMOTE_REVIEW')` 등) 는 CC 그대로 보존 — UMMAYA 환경에서 자동 비활성.

### Rationale

- **swap 무관 핵심 기능**: `--print` 는 헤드리스 mode → CI/스크립트 자동화 + 정책 batch 분석 직접 종속. spec US3 + FR-013 정의.
- **cascade dep 명확화**: 5594 LOC PORT 시 누락 cascade 1건 (`remoteManagedSettings/`). audit pre-execution 단계에서 미발견 → plan 단계에서 grep 으로 발견 → spec FR-016 추가 필요.
- **UMMAYA analytics/index.ts 패턴 일관성**: Spec 1633 P1 의 stub-noop replacement 와 동일 패턴 → 일관된 swap-1 dead-surface 처리.

### Alternatives considered

- **A. CC `remoteManagedSettings/` 본체 cascade PORT**: 거부 — Anthropic enterprise managed settings (claude.ai 1P 종속) → swap-1 종속이라 본체 무의미. UMMAYA 어느 시점도 사용 안 함.
- **B. cli/print.ts L9 import 자체 제거 + 호출부 noop 분기**: 거부 — `cli/print.ts` byte-identical 원칙 위반. UMMAYA-side stub 으로 dependency 충족이 정답.
- **C. cli/print.ts PORT 자체를 deferred Epic 으로 분리**: 거부 — spec US3 + FR-003 이미 P2 priority 로 명시. 본 Epic A scope 내 처리가 빠름.

## D4 — Stage-1 NO-OP 3건 박제 (byte-copy 불가, CC source 부재 확정)

### Decision

`tui/src/utils/protectedNamespace.ts` + `systemThemeWatcher.ts` + `ultraplan/prompt.txt` 의 헤더에 다음 패턴 박제:

```
// SPDX-License-Identifier: Apache-2.0
// SWAP/no-cc-source(2637): UMMAYA-only stub. CC source absent (find .references/...
// -name "protectedNamespace.ts" returns 0). decisions.md S9 § Stage-1 cite.
// CC consumer references (envUtils.ts:142 + ThemeProvider.tsx:69) imply CC has
// runtime equivalents but they're not in restored-src — UMMAYA NO-OP is justified
// until TUI Fidelity Meta-Epic decides on UMMAYA-original implementation.
```

byte-copy 시도 안 함 (CC source 부재 확정). `decisions.md` 의 S9 § Stage-1 행 업데이트 — "byte-copy 채우기" → "CC source 부재 확정 — UMMAYA-only stub 박제 처리, TUI Fidelity Meta-Epic deferred".

### Rationale

- **정직성**: audit 권고 ("byte-copy") 가 사실상 불가능한 경우 spec FR-007 + decisions.md 양쪽에서 정확한 처리 명시.
- **회귀 차단**: 향후 audit 재실행 시 D-bucket 분류 0 (UMMAYA-ORIGINAL-justified bucket 으로 이동).
- **AGENTS.md "Do not touch `.references/`"**: research-only mirror 에 정식 구현 추가 금지 — 박제 처리만 가능.

### Alternatives considered

- **A. `.references/.../src/utils/protectedNamespace.ts` 신규 작성**: 거부 — `.references/` modify 금지 (AGENTS.md hard rule).
- **B. UMMAYA 정식 구현 본 Epic 안에서 작성**: 거부 — scope creep. `protectedNamespace` (Node.js global pollution 보호), `systemThemeWatcher` (OSC 11 OS dark/light 감지) 모두 UMMAYA 행정 도구 컨텍스트에서 별도 설계 필요. spec scope outside.

## Phase 0 Deferred Items Validation

spec.md § Scope Boundaries & Deferred Items § Deferred to Future Work 의 6개 항목:

| Item | Tracking Issue | 검증 결과 |
|---|---|---|
| `protectedNamespace.ts` 정식 UMMAYA 구현 | NEEDS TRACKING | ✅ `/speckit-taskstoissues` 가 placeholder issue 발행 예정 |
| `systemThemeWatcher.ts` 정식 UMMAYA 구현 | NEEDS TRACKING | ✅ 동상 |
| `ultraplan/prompt.txt` 실제 시스템 프롬프트 작성 | NEEDS TRACKING | ✅ 동상 |
| audit `decisions.md` 의 D-4 (main.tsx PROACTIVE/BRIEF) 검증 | NEEDS TRACKING | ✅ 동상 |
| `entrypoints/sdk/` 6 파일 UMMAYA-only re-declaration audit | NEEDS TRACKING | ✅ 동상 |
| migration version 12 시작 | NEEDS TRACKING | ✅ 동상 |

spec.md 본문 grep 결과 (`grep -E "separate epic|future epic|Phase [2-9]|v2|deferred to|later release|out of scope for v1"` 패턴):

- `Out of Scope (Permanent)` 에 "별도 TUI Fidelity Meta-Epic" 언급 → Deferred 표 entry 존재 ✅
- `Out of Scope (Permanent)` 에 "swap-1 종속이라 영구 비활성" 언급 → 영구 제외 cite ✅
- `Acceptance Scenarios` US4-2 에 "Epic A 종료, ... 결정 업데이트" → 본 Epic 내 처리 ✅

비표 deferral 패턴 0. **Constitution Principle VI 준수 확인.**

## Spec 업데이트 필요 (FR-016 추가)

D3 결정에 따라 spec.md 에 FR-016 추가:

> **FR-016**: System MUST create `tui/src/services/remoteManagedSettings/index.ts` as a UMMAYA-side stub-noop module exporting `waitForRemoteManagedSettingsToLoad(): Promise<void>` (returns immediately resolved Promise). Required to resolve `cli/print.ts:9` cascade import. Pattern follows `tui/src/services/analytics/index.ts` (Spec 1633 P1).

이 업데이트는 plan 단계 발견이라 spec.md 본문에 직접 추가 후 checklist requirements.md 도 업데이트 필요.
