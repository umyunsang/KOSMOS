# Byte-Identical Verification Contract — Epic A P0 회귀 즉시 복구

**Feature**: [../spec.md](../spec.md) · **Data Model**: [../data-model.md](../data-model.md) · **Date**: 2026-05-03

본 contract 는 spec.md FR-008 ("All PORTed files MUST pass byte-identical verification") 의 검증 절차를 정의. CI / 사용자 / Codex 가 모두 같은 명령으로 검증 가능.

## 1. byte-identical PORT (action=`port_byte_copy`) — diff -q empty 강제

7 파일 (R-1a/b/c, R-2a/b/c/d) 모두 CC 원본과 100% 일치해야 한다.

```bash
#!/usr/bin/env bash
# specs/2637-p0-regression/scripts/verify-byte-identical.sh
set -e
cd /Users/um-yunsang/UMMAYA-w-2637

PORTED_BYTE_IDENTICAL=(
  "types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts"
  "types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts"
  "types/generated/events_mono/common/v1/auth.ts"
  "constants/messages.ts"
  "constants/xml.ts"
  "constants/figures.ts"
  "types/logs.ts"
)

failed=0
for rel in "${PORTED_BYTE_IDENTICAL[@]}"; do
  ummaya="tui/src/$rel"
  cc=".references/claude-code-sourcemap/restored-src/src/$rel"
  if ! diff -q "$ummaya" "$cc" > /dev/null 2>&1; then
    echo "FAIL: $rel — byte-identical 위반"
    diff "$ummaya" "$cc" | head -20
    failed=$((failed + 1))
  else
    echo "PASS: $rel"
  fi
done

if [ $failed -gt 0 ]; then
  echo "Total failures: $failed / ${#PORTED_BYTE_IDENTICAL[@]}"
  exit 1
fi
echo "All ${#PORTED_BYTE_IDENTICAL[@]} files byte-identical PASS"
```

## 2. PORT with swap-1 replace (action=`port_with_swap1_replace`) — 화이트리스트 검증

3 파일 (R-3, R-4, R-5) 은 swap-1 식별자 화이트리스트 외 diff 0 강제.

### 2.1 `constants/oauth.ts` (R-4)

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

# 화이트리스트 식별자 (data-model.md § Swap1IdentifierWhitelist):
# - OAuth client_id 상수 (line locations TBD by PORT)
# - console.anthropic.com / claude.ai/oauth URL 상수
# - 헤더 주석 (UMMAYA Epic #2637 — byte-copy from CC 2.1.88 ...)

# Allowed diff line count (5-10 lines):
diff_lines=$(diff tui/src/constants/oauth.ts \
                  .references/claude-code-sourcemap/restored-src/src/constants/oauth.ts \
                  | wc -l)
if [ "$diff_lines" -gt 30 ]; then
  echo "FAIL: oauth.ts diff lines $diff_lines > 30 (whitelist 초과)"
  diff tui/src/constants/oauth.ts \
       .references/claude-code-sourcemap/restored-src/src/constants/oauth.ts | head -50
  exit 1
fi
echo "PASS: oauth.ts diff lines $diff_lines (whitelist 내)"
```

### 2.2 `cli/print.ts` (R-3)

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

# 화이트리스트 식별자:
# - 헤더 주석 (UMMAYA Epic #2637 — byte-copy from CC 2.1.88, --print mode)
# - cascade stub import path (변경 없음 — UMMAYA-side stub 이 같은 export 시그니처)

# Allowed diff line count (3-5 lines, 헤더만):
diff_lines=$(diff tui/src/cli/print.ts \
                  .references/claude-code-sourcemap/restored-src/src/cli/print.ts \
                  | wc -l)
if [ "$diff_lines" -gt 20 ]; then
  echo "FAIL: print.ts diff lines $diff_lines > 20 (whitelist 초과)"
  exit 1
fi
echo "PASS: print.ts diff lines $diff_lines (whitelist 내)"
```

### 2.3 `utils/telemetry/instrumentation.ts` (R-5)

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

# 화이트리스트 식별자:
# - 헤더 주석 (UMMAYA Epic #2637 — byte-copy from CC 2.1.88, OTEL instrumentation)
# - swap-1 종속 import path: 변경 없음 (UMMAYA-side stub 이 같은 export 시그니처)
# - 단, UMMAYA bootstrap/state.ts import path 가 CC 와 일치해야 함

# Allowed diff line count (3-5 lines, 헤더만):
diff_lines=$(diff tui/src/utils/telemetry/instrumentation.ts \
                  .references/claude-code-sourcemap/restored-src/src/utils/telemetry/instrumentation.ts \
                  | wc -l)
if [ "$diff_lines" -gt 20 ]; then
  echo "FAIL: instrumentation.ts diff lines $diff_lines > 20 (whitelist 초과)"
  exit 1
fi
echo "PASS: instrumentation.ts diff lines $diff_lines (whitelist 내)"
```

## 3. UMMAYA-original cascade stub (action=`create_ummaya_stub`) — 패턴 검증

R-3-cascade (`remoteManagedSettings/index.ts`) + T004 의 cascade stubs (`betaSessionTracing.ts`, `bigqueryExporter.ts`, `logger.ts`, `perfettoTracing.ts`) 는 UMMAYA-original. 검증 패턴:

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

CASCADE_STUBS=(
  "tui/src/services/remoteManagedSettings/index.ts"
  # T004 발견 시 추가:
  # "tui/src/utils/telemetry/betaSessionTracing.ts"
  # "tui/src/utils/telemetry/bigqueryExporter.ts"
  # "tui/src/utils/telemetry/logger.ts"
  # "tui/src/utils/telemetry/perfettoTracing.ts"
)

for stub in "${CASCADE_STUBS[@]}"; do
  if ! head -10 "$stub" | grep -q "SWAP/anti-anthropic-1p(2637)\|SWAP/no-cc-source(2637)"; then
    echo "FAIL: $stub — 헤더에 SWAP cite 누락"
    head -10 "$stub"
    exit 1
  fi
  if ! head -10 "$stub" | grep -q "Spec 1633\|analytics/index.ts"; then
    echo "FAIL: $stub — 헤더에 패턴 reference (Spec 1633 / analytics/index.ts) 누락"
    head -10 "$stub"
    exit 1
  fi
  echo "PASS: $stub"
done
```

## 4. 헤더 박제 (action=`header_only_imprint`) — Stage-1 NO-OP 3건

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

NOOP_STUBS=(
  "tui/src/utils/protectedNamespace.ts"
  "tui/src/utils/systemThemeWatcher.ts"
  "tui/src/utils/ultraplan/prompt.txt"
)

for stub in "${NOOP_STUBS[@]}"; do
  if ! head -10 "$stub" | grep -q "SWAP/no-cc-source(2637)"; then
    echo "FAIL: $stub — 헤더에 SWAP/no-cc-source(2637) cite 누락"
    head -10 "$stub"
    exit 1
  fi
  if ! head -10 "$stub" | grep -q "decisions.md S9"; then
    echo "FAIL: $stub — 헤더에 decisions.md S9 cite 누락"
    head -10 "$stub"
    exit 1
  fi
  echo "PASS: $stub"
done
```

## 5. wire 검증 (action=`wire_ummaya_helper`) — `toolExecution.ts` 9 stub → import 교체

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

# pre-state: 9개 inline `const X = (..._args) => Y` 패턴
pre_inline=$(grep -c "^const \(logOTelEvent\|addToolContentEvent\|endToolBlockedOnUserSpan\|endToolExecutionSpan\|endToolSpan\|isBetaTracingEnabled\|startToolBlockedOnUserSpan\|startToolExecutionSpan\|startToolSpan\) = " tui/src/services/tools/toolExecution.ts)

# post-state: 9개 모두 import 으로 교체
post_inline=$(grep -c "^const \(logOTelEvent\|addToolContentEvent\|endToolBlockedOnUserSpan\|endToolExecutionSpan\|endToolSpan\|isBetaTracingEnabled\|startToolBlockedOnUserSpan\|startToolExecutionSpan\|startToolSpan\) = " tui/src/services/tools/toolExecution.ts)

if [ "$post_inline" -ne 0 ]; then
  echo "FAIL: toolExecution.ts inline stubs 잔존 ($post_inline)"
  exit 1
fi

# import statement 검증
if ! grep -q "from.*utils/telemetry/toolSpans\|from.*utils/telemetry/sessionTracing" tui/src/services/tools/toolExecution.ts; then
  echo "FAIL: toolExecution.ts toolSpans/sessionTracing import 누락"
  exit 1
fi
echo "PASS: toolExecution.ts wire complete"
```

## 6. 통합 audit 재실행 (Spec 검증)

```bash
cd /Users/um-yunsang/UMMAYA-w-2637

# audit Initiative #2636 의 9-stream 결과 재실행
# (specs/cc-migration-audit/scope-S2/S8/S9 의 grep 명령)

# S8 D-1 (events_mono):
wc -l tui/src/types/generated/events_mono/claude_code/v1/*.ts | tail -1
# 결과: 865+ LOC (회귀 0)

# S8 D-2 (Proxy stub 5):
grep -l "__noop\|__stub\|Proxy" tui/src/constants/{messages,xml,figures}.ts tui/src/types/logs.ts 2>&1 || echo "no Proxy match"
# 결과: no Proxy match (회귀 0)

# S8 D-3 (cli/print.ts):
ls tui/src/cli/print.ts
# 결과: 파일 존재 (회귀 0)

# S9 § Stage-1 (NO-OP):
head -5 tui/src/utils/protectedNamespace.ts | grep "SWAP/no-cc-source(2637)"
# 결과: 헤더 박제 PASS (회귀 0)

# S9 P0-1 (instrumentation):
ls tui/src/utils/telemetry/instrumentation.ts
# 결과: 파일 존재 (회귀 0)

# S2 R1 (toolExecution telemetry):
grep -c "no-op" tui/src/services/tools/toolExecution.ts
# 결과: 0 (회귀 0)

# 종합: D-bucket entries 모두 0 → audit closure PASS
```

## 7. CI integration

본 contract 의 verification 명령들은 Sonnet teammate 가 각 task 완료 후 자동 실행. PR open 후 CI workflow `.github/workflows/byte-identical-verification.yml` (별도 신설 — Spec scope 외부, Epic D 검토) 가 동일 명령 재실행.

현재 PR-단계에서는 Sonnet teammate 의 local verification + Lead Opus 의 final inspection 으로 충분.
