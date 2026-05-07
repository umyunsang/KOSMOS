# Quickstart — Epic A P0 회귀 즉시 복구

**Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Data Model**: [data-model.md](./data-model.md)

> **For Sonnet teammate**: 단일 Sonnet teammate 가 sequential 로 7 task 순차 실행. 각 task 는 PORT/wire/박제 + verification 으로 self-contained.
>
> **워크트리**: `/Users/um-yunsang/KOSAX-w-2637` · **브랜치**: `feat/2637-p0-regression`
>
> **CC source-of-truth**: `.references/claude-code-sourcemap/restored-src/src/` (read-only, NEVER modify).

## 사전 조건

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# 워크트리 확인
git branch --show-current  # → feat/2637-p0-regression

# 작업 시작 전 baseline 측정
bun test 2>&1 | tail -5    # baseline pass count 기록
uv run pytest 2>&1 | tail -5
bun typecheck 2>&1 | tail -5
```

## 작업 순서 (sequential, 7 task)

### T001 — events_mono types byte-copy PORT

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# R-1a: claude_code_internal_event.ts
cp .references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts \
   tui/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts

# R-1b: growthbook_experiment_event.ts
cp .references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts \
   tui/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts

# R-1c: common/v1/auth.ts (디렉토리 신설)
mkdir -p tui/src/types/generated/events_mono/common/v1
cp .references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/common/v1/auth.ts \
   tui/src/types/generated/events_mono/common/v1/auth.ts

# 검증 V4
diff -q tui/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts \
        .references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts
diff -q tui/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts \
        .references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts
diff -q tui/src/types/generated/events_mono/common/v1/auth.ts \
        .references/claude-code-sourcemap/restored-src/src/types/generated/events_mono/common/v1/auth.ts
# 모두 empty output 이어야 함

# logEvent emit 표면 차단: events_mono 타입 import 사이트 확인
grep -rn "from.*events_mono.*claude_code" tui/src/ | head -10
# 결과 callsite 들 검토 → emit 함수 호출이 entry point 에서 차단되는지 확인 (services/analytics/index.ts 가 이미 stub)
```

### T002 — Constants/Types Proxy stub byte-copy PORT

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# R-2a: messages.ts
cp .references/claude-code-sourcemap/restored-src/src/constants/messages.ts \
   tui/src/constants/messages.ts

# R-2b: xml.ts
cp .references/claude-code-sourcemap/restored-src/src/constants/xml.ts \
   tui/src/constants/xml.ts

# R-2c: figures.ts (검증 — 이미 거의 같으나 byte-identical 확인)
diff tui/src/constants/figures.ts .references/claude-code-sourcemap/restored-src/src/constants/figures.ts
# diff 가 1-2 라인 이내면 PASS, 아니면 byte-copy 다시
cp .references/claude-code-sourcemap/restored-src/src/constants/figures.ts \
   tui/src/constants/figures.ts

# R-2d: types/logs.ts
cp .references/claude-code-sourcemap/restored-src/src/types/logs.ts \
   tui/src/types/logs.ts

# 검증 V4 (byte-identical)
for f in constants/messages.ts constants/xml.ts constants/figures.ts types/logs.ts; do
  diff -q tui/src/$f .references/claude-code-sourcemap/restored-src/src/$f
done

# 컴파일 회귀 확인 (Proxy stub → plain const 전환 후 callsite 검증)
bun typecheck 2>&1 | grep -E "messages.ts|xml.ts|figures.ts|logs.ts" | head -20
```

### T003 — constants/oauth.ts byte-copy PORT (swap-1 식별자 교체)

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# R-4: byte-copy first
cp .references/claude-code-sourcemap/restored-src/src/constants/oauth.ts \
   tui/src/constants/oauth.ts

# swap-1 식별자 enumerate (data-model.md § Swap1IdentifierWhitelist)
# - OAuth client_id 상수 → KOSAX-side null
# - console.anthropic.com / claude.ai/oauth URL 상수 → KOSAX-side null
# CC 의 USER_TYPE === 'ant' 가드는 그대로 유지 (자동 prod fallback)

# Edit tool 로 swap-1 식별자만 교체:
# - 식별자 기존 값 → null 또는 KOSAX-side placeholder
# - 헤더 주석 추가:
#   // KOSAX Epic #2637 — byte-copy from CC 2.1.88 (oauth.ts).
#   // SWAP/anti-anthropic-1p: Anthropic OAuth client_id + endpoints replaced
#   // with null (FriendliAI K-EXAONE = API-key only, no OAuth flow).
#   // process.env.USER_TYPE === 'ant' guard preserved per CC source.

# 검증 V4 (swap-1 화이트리스트 외 diff 0)
diff tui/src/constants/oauth.ts .references/claude-code-sourcemap/restored-src/src/constants/oauth.ts | wc -l
# 화이트리스트 식별자 (예: 5-10 라인) 외 추가 diff 없어야 함
```

### T004 — utils/telemetry/instrumentation.ts PORT + 8 OTel deps + cascade stub

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# Step 1: 8개 OTel dependency 추가
cd tui
bun add @opentelemetry/semantic-conventions \
        @opentelemetry/exporter-trace-otlp-http \
        @opentelemetry/exporter-trace-otlp-grpc \
        @opentelemetry/exporter-logs-otlp-http \
        @opentelemetry/exporter-logs-otlp-grpc \
        @opentelemetry/exporter-metrics-otlp-http \
        @opentelemetry/exporter-metrics-otlp-grpc \
        @grpc/grpc-js
cd ..

# Step 2: instrumentation.ts byte-copy
cp .references/claude-code-sourcemap/restored-src/src/utils/telemetry/instrumentation.ts \
   tui/src/utils/telemetry/instrumentation.ts

# Step 3: swap-1 종속 cascade stub modules 신설 (각 ~10-30 LOC, no-op exports)
# - tui/src/utils/telemetry/betaSessionTracing.ts (NEW stub)
# - tui/src/utils/telemetry/bigqueryExporter.ts (NEW stub — BigQueryMetricsExporter export)
# - tui/src/utils/telemetry/logger.ts (NEW stub — ClaudeCodeDiagLogger export)
# - tui/src/utils/telemetry/perfettoTracing.ts (NEW stub — initializePerfettoTracing export)
# - tui/src/utils/telemetry/sessionTracing.ts (UPDATE — endInteractionSpan + isEnhancedTelemetryEnabled exports added; 기존 isBetaTracingEnabled 보존)
# - tui/src/utils/telemetryAttributes.ts (확인 — 이미 있는지)
# - tui/src/utils/caCerts.ts (확인 — 이미 있는지)
# - tui/src/utils/cleanupRegistry.ts (확인 — 이미 있는지)
# - tui/src/utils/proxy.ts (확인)
# - tui/src/utils/mtls.ts (확인)
# - tui/src/utils/startupProfiler.ts (확인)

# 각 누락 cascade 발견 시 KOSAX-side stub 패턴:
# // SPDX-License-Identifier: Apache-2.0
# // KOSAX-original — Epic #2637 cascade · stub-noop replacement.
# // SWAP/anti-anthropic-1p(2637): swap-1 dependent telemetry helper (Anthropic 1P
# // GrowthBook/BigQuery/Perfetto) replaced with no-op for instrumentation.ts byte-copy.
# // KOSAX uses Spec 021 OTEL pipeline directly (toolExecution.ts wire, T005).

# Step 4: 검증 V1 — typecheck
bun typecheck 2>&1 | grep "instrumentation\|telemetry" | head -10
```

### T005 — toolExecution.ts 9 stub wire (KOSAX Spec 021 OTEL helper 직접 사용)

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# Step 1: 신규 KOSAX OTEL helper 작성 (또는 sessionTracing.ts 확장)
# tui/src/utils/telemetry/toolSpans.ts (NEW)
# - logOTelEvent(): @opentelemetry/api logs.getLogger('kosax.tools').emit(...)
# - startToolSpan(name, attrs): trace.getTracer('kosax.tools').startSpan(...)
# - endToolSpan(toolResultStr): span.setAttribute('kosax.tool.outcome', ...).end()
# - addToolContentEvent(span, contentAttrs): span.addEvent('tool.output', contentAttrs)
# - startToolExecutionSpan / endToolExecutionSpan / startToolBlockedOnUserSpan / endToolBlockedOnUserSpan
# - isBetaTracingEnabled(): false (KOSAX 비활성)
#
# Spec 021 attribute namespace:
# - kosax.tool.id, kosax.tool.input_size_bytes, kosax.tool.outcome,
#   kosax.tool.error_type, kosax.tool.duration_ms,
#   kosax.tool.permission_decision, kosax.tool.user_facing_name

# Step 2: toolExecution.ts line 91-100 의 9 inline stub 교체
# 기존:
#   // KOSAX: utils/telemetry/events.js deleted by Spec 1633 P1. logOTelEvent → no-op.
#   const logOTelEvent = (_event: string, _data?: unknown): void => {}
#   ... 8개 더
# 신규:
#   // KOSAX Epic #2637 — Spec 021 OTEL Tool layer wire (4-tier OTEL).
#   import {
#     logOTelEvent,
#     addToolContentEvent,
#     endToolBlockedOnUserSpan, endToolExecutionSpan, endToolSpan,
#     isBetaTracingEnabled,
#     startToolBlockedOnUserSpan, startToolExecutionSpan, startToolSpan,
#   } from '../../utils/telemetry/toolSpans.js'

# Step 3: 검증 V5 (PTY smoke)
# bun run tui --port  → lookup 1회 → Langfuse trace 에 kosax.tool.id 출현 확인

# Step 4: 검증 V1
bun typecheck 2>&1 | grep "toolExecution" | head -5
```

### T006 — cli/print.ts byte-copy PORT + main.tsx 차단 제거 + cascade stub

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# Step 1: cascade stub 신설 (R-3-cascade)
mkdir -p tui/src/services/remoteManagedSettings
cat > tui/src/services/remoteManagedSettings/index.ts <<'EOF'
// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — Epic #2637 cascade · stub-noop replacement for CC remoteManagedSettings.
// SWAP/anti-anthropic-1p(2637): Anthropic enterprise managed settings (claude.ai 1P)
// surface is dead in KOSAX. CC's print.ts cascade requires this import to resolve.
// Pattern follows tui/src/services/analytics/index.ts (Spec 1633 P1 stub-noop).

export async function waitForRemoteManagedSettingsToLoad(): Promise<void> {
  // Intentional no-op (Epic #2637 stub). Anthropic remote managed settings (claude.ai 1P)
  // is swap-1 dependent — permanently disabled in KOSAX.
}
EOF

# Step 2: cli/print.ts byte-copy
cp .references/claude-code-sourcemap/restored-src/src/cli/print.ts \
   tui/src/cli/print.ts

# Step 3: 추가 cascade dep 발견 (typecheck 으로 누락 모듈 enumerate)
bun typecheck 2>&1 | grep -E "Cannot find module|has no exported member" | head -30
# 발견되는 누락 모듈마다:
# - 본체가 swap-1 종속이면 KOSAX-side stub 신설 (analytics/index.ts 패턴)
# - byte-identical 일치 가능하면 추가 byte-copy

# Step 4: main.tsx L1960 "--print not supported" 차단 메시지 제거
# Edit tool 로 차단 블록 제거 + CC 원본 print mode entry point 호출 wire

# Step 5: 검증 V6 (--print mode)
bun run tui --print "안녕" 2>&1
# exit code 0, stdout 에 K-EXAONE 응답 출현 (실제 LLM 호출이라 시간 30-90s 소요 가능)
# stderr 에 "not supported" 문자열 0회 검증
```

### T007 — Stage-1 NO-OP 3건 헤더 박제 + decisions.md 업데이트 + 최종 검증

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# Step 1: protectedNamespace.ts 헤더 박제
# Step 2: systemThemeWatcher.ts 헤더 박제
# Step 3: ultraplan/prompt.txt 헤더 박제
# 각 파일 헤더 패턴 (Edit tool 사용):
#   // SPDX-License-Identifier: Apache-2.0
#   // SWAP/no-cc-source(2637): KOSAX-only stub. CC source absent
#   // (find .references/.../src -name "<file>" returns 0). decisions.md S9 § Stage-1 cite.
#   // CC consumer references (envUtils.ts:142 / ThemeProvider.tsx:69) imply CC has
#   // runtime equivalents but they're not in restored-src — KOSAX NO-OP is justified
#   // until TUI Fidelity Meta-Epic decides on KOSAX-original implementation.

# Step 4: decisions.md Stage-1 row 업데이트
# specs/cc-migration-audit/decisions.md 의 S9 § Stage-1 행 수정:
# 기존: "byte-copy 채우기 (Epic A에 포함)"
# 변경: "CC source 부재 확정 — KOSAX-only stub 박제 처리 (Epic A #2637 완료),
#        TUI Fidelity Meta-Epic deferred (#TBD-protectedNamespace, #TBD-systemThemeWatcher,
#        #TBD-ultraplan)"

# Step 5: 최종 audit 재실행 (V8)
# specs/cc-migration-audit/scope-S8/S9/S2 의 grep 명령 재실행
# D-bucket entries 0 확인

# Step 6: 전체 검증 V1-V9
bun typecheck                                      # V1
bun test 2>&1 | tail -10                           # V2
uv run pytest 2>&1 | tail -10                      # V3
# V4 — diff -q PORTed 파일들
# V5 — Langfuse trace (Layer 5 tmux smoke)
# V6 — bun run tui --print "안녕"
# V7 — scripts/tui-tmux-capture.sh
# V8 — audit 재실행
# V9 — final.txt 검증
```

## 빠른 검증 (Sonnet teammate 가 PR 전 마지막 sanity check)

```bash
cd /Users/um-yunsang/KOSAX-w-2637

# 1. byte-identical 검증 — PORTed 파일 모두 (T001/T002/T004/T006 의 cp 대상)
PORTED=(
  "tui/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts"
  "tui/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts"
  "tui/src/types/generated/events_mono/common/v1/auth.ts"
  "tui/src/constants/messages.ts"
  "tui/src/constants/xml.ts"
  "tui/src/constants/figures.ts"
  "tui/src/types/logs.ts"
)
for f in "${PORTED[@]}"; do
  cc=".references/claude-code-sourcemap/restored-src/src/${f#tui/src/}"
  diff -q "$f" "$cc" || echo "FAIL: $f"
done
# 모두 empty output 이어야 함 (port_byte_copy 류만)

# 2. swap-1 식별자 화이트리스트 검증 — port_with_swap1_replace 류
for f in tui/src/cli/print.ts tui/src/constants/oauth.ts tui/src/utils/telemetry/instrumentation.ts; do
  cc=".references/claude-code-sourcemap/restored-src/src/${f#tui/src/}"
  diff_lines=$(diff "$f" "$cc" | wc -l)
  echo "$f: $diff_lines diff lines (swap-1 화이트리스트 limits 내)"
done

# 3. 부팅 + Layer 5 smoke
scripts/tui-tmux-capture.sh /tmp/2637-smoke specs/2637-p0-regression/scripts/smoke-2637.sh
ls /tmp/2637-smoke/snap-*.txt
cat /tmp/2637-smoke/final.txt | grep -E "tool_registry: \d+ entries verified|KOSAX"
```

## 회귀 발견 시 대응

각 T0NN 별로 발견된 회귀는 다음 단계로 처리:

1. typecheck 회귀 → 누락 cascade dep 발견 → KOSAX-side stub 신설 (analytics/index.ts 패턴)
2. bun test 회귀 → 회귀 root cause 식별 → byte-copy 정합성 재검증
3. PTY smoke 회귀 → frame_NNNN.txt enumerate (AGENTS.md anti-pattern #1 차단)
4. Langfuse trace 누락 → toolSpans.ts wire 정합 재검증

각 task 완료 후 commit (Conventional Commits, `feat(2637): ...`). 마지막 task 후 단일 PR open.
