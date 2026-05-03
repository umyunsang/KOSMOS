# Data Model — Epic A P0 회귀 즉시 복구

**Feature**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Date**: 2026-05-03

본 Epic 은 byte-copy + telemetry wire 작업이라 신규 도메인 entity 가 거의 없다. 단, 회귀 추적 + swap-1 식별자 화이트리스트 + OTEL attribute namespace 는 명시적 entity 로 정의해 검증 가능성 확보.

## Entity 1 — RegressionItem

audit Initiative #2636 에서 발견된 9건 회귀 (6 P0 + 3 부수). 각 item 은 PORT/wire/박제 액션 + verification command + post-state 로 정의.

| Field | Type | Description |
|---|---|---|
| `id` | str | 고유 식별자 (e.g., `R-1a`, `R-2c`, `R-7`) |
| `category` | enum | `events_mono` / `proxy_stub` / `cli_print` / `oauth_const` / `instrumentation` / `tool_telemetry` / `stage1_noop` / `cascade_dep` |
| `cc_path` | str \| null | CC source path (`.references/.../src/...`). `null` if CC source absent (Stage-1 NO-OP). |
| `kosmos_path` | str | KOSMOS target path (`tui/src/...`). |
| `pre_loc` | int | 회귀 전 KOSMOS LOC. |
| `cc_loc` | int \| null | CC source LOC. `null` if CC absent. |
| `action` | enum | `port_byte_copy` / `port_with_swap1_replace` / `wire_kosmos_helper` / `header_only_imprint` / `create_kosmos_stub` |
| `priority` | enum | `P0` (US1/US2) / `P2` (US3) / `P3` (US4) |
| `verification_command` | str | post-state 검증 shell 명령 |
| `swap1_whitelist` | list[str] | 허용된 swap-1 식별자 (이 외 diff 는 fail-build) |

### Instances (9 + 1 cascade)

| id | category | cc_path | kosmos_path | pre_loc | cc_loc | action | priority |
|---|---|---|---|---|---|---|---|
| R-1a | events_mono | `.references/.../types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts` | `tui/src/types/generated/events_mono/claude_code/v1/claude_code_internal_event.ts` | 21 | 865 | port_byte_copy | P0 |
| R-1b | events_mono | `.references/.../types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts` | `tui/src/types/generated/events_mono/growthbook/v1/growthbook_experiment_event.ts` | 15 | 223 | port_byte_copy | P0 |
| R-1c | events_mono | `.references/.../types/generated/events_mono/common/v1/auth.ts` | `tui/src/types/generated/events_mono/common/v1/auth.ts` | 0 (missing) | (CC LOC TBD) | port_byte_copy | P0 |
| R-2a | proxy_stub | `.references/.../constants/messages.ts` | `tui/src/constants/messages.ts` | 32 | 1 | port_byte_copy | P0 |
| R-2b | proxy_stub | `.references/.../constants/xml.ts` | `tui/src/constants/xml.ts` | 37 | 86 | port_byte_copy | P0 |
| R-2c | proxy_stub | `.references/.../constants/figures.ts` | `tui/src/constants/figures.ts` | 46 | 45 | port_byte_copy | P0 (검증 only — 이미 plain string) |
| R-2d | proxy_stub | `.references/.../types/logs.ts` | `tui/src/types/logs.ts` | 55 | 330 | port_byte_copy | P0 |
| R-3 | cli_print | `.references/.../cli/print.ts` | `tui/src/cli/print.ts` | 0 (missing) | 5594 | port_with_swap1_replace | P2 |
| R-3-cascade | cascade_dep | (CC: enterprise managed settings, swap-1 dead) | `tui/src/services/remoteManagedSettings/index.ts` | 0 (missing) | (KOSMOS-original stub ~30) | create_kosmos_stub | P2 |
| R-4 | oauth_const | `.references/.../constants/oauth.ts` | `tui/src/constants/oauth.ts` | 0 (missing) | 234 | port_with_swap1_replace | P0 |
| R-5 | instrumentation | `.references/.../utils/telemetry/instrumentation.ts` | `tui/src/utils/telemetry/instrumentation.ts` | 0 (missing) | 825 | port_with_swap1_replace | P0 |
| R-6 | tool_telemetry | (CC: events.ts + sessionTracing.ts cascade — swap-1) | `tui/src/services/tools/toolExecution.ts` (line 91-100 wire) | 9 inline stub | 1745 (본체) | wire_kosmos_helper | P0 |
| R-7a | stage1_noop | (CC source absent) | `tui/src/utils/protectedNamespace.ts` | 7 stub | null | header_only_imprint | P3 |
| R-7b | stage1_noop | (CC source absent) | `tui/src/utils/systemThemeWatcher.ts` | 7 stub | null | header_only_imprint | P3 |
| R-7c | stage1_noop | (CC source absent) | `tui/src/utils/ultraplan/prompt.txt` | 1 placeholder | null | header_only_imprint | P3 |

## Entity 2 — Swap1IdentifierWhitelist

`port_with_swap1_replace` action 을 받은 파일에서 CC 와 KOSMOS 사이 diff 가 허용되는 식별자. 이 화이트리스트 외 diff 는 FR-008 위반 (fail-build).

| File | Allowed Identifier | Substitution | Justification |
|---|---|---|---|
| `constants/oauth.ts` | `process.env.USER_TYPE === 'ant'` 가드 (CC 그대로 유지, 자동 prod fallback) | (no replace, CC 가드가 KOSMOS 에서 자동 비활성) | CC 코드의 Anthropic 내부 환경 가드, KOSMOS 환경에서 자동 prod path 만 활성 |
| `constants/oauth.ts` | OAuth client_id 상수 (e.g., `9d1c250a-...`) | KOSMOS-side `null` (FriendliAI = API key only, OAuth 없음) | swap-1 종속 식별자 |
| `constants/oauth.ts` | `console.anthropic.com` / `claude.ai/oauth` URL 상수 | KOSMOS-side `null` 또는 자리표시자 | 동상 |
| `cli/print.ts` | `process.env.USER_TYPE === 'ant'` + `feature(...)` 가드 | (no replace, CC 그대로 — KOSMOS 자동 비활성) | CC 가드는 KOSMOS 환경에서 자동 dead path |
| `cli/print.ts` | `services/remoteManagedSettings/` import (line 9) | KOSMOS stub resolves identical export | cascade KOSMOS-side stub |
| `instrumentation.ts` | `is1PApiCustomer` / `isClaudeAISubscriber` / `getOtelHeadersFromHelper` / `getSubscriptionType` import (CC L40-44) | KOSMOS `tui/src/utils/auth.ts` 가 같은 이름으로 export (Spec 1633 stub) | swap-1 종속 helper, KOSMOS 가 stub 으로 export |
| `instrumentation.ts` | `./betaSessionTracing.js` / `./bigqueryExporter.js` / `./logger.js` / `./perfettoTracing.js` / `./sessionTracing.js` import (CC L60-66) | KOSMOS-side minimal stub modules (각 ~10-30 LOC, no-op exports) | swap-1 종속 telemetry helper, dependency cascade 회피 |

## Entity 3 — OtelAttributeContract

`toolExecution.ts` wire (R-6) 가 emit 하는 OTEL attribute namespace. Spec 021 4-tier OTEL 의 Tool layer 와 정합.

| Attribute | Type | Source | Required |
|---|---|---|---|
| `kosmos.tool.id` | str | `toolUse.name` | ✅ |
| `kosmos.tool.input_size_bytes` | int | `JSON.stringify(input).length` | ✅ |
| `kosmos.tool.outcome` | enum | `success` / `error` / `blocked_on_user` / `cancelled` | ✅ |
| `kosmos.tool.error_type` | str | `formatError(e).errorType` (if outcome=error) | conditional |
| `kosmos.tool.duration_ms` | int | `Date.now() - startTs` | ✅ |
| `kosmos.tool.permission_decision` | enum | `accept` / `reject` / `bypass` (Spec 033) | conditional |
| `kosmos.tool.user_facing_name` | str | `tool.userFacingName(input)` | ✅ |
| Span name | str | `kosmos.tool.{tool_id}` | ✅ |

Spec 021 OTLP collector → Langfuse 라우팅 시 `service.name = "kosmos-tui"` resource attribute 자동 부여 (instrumentation.ts D1 가 set).

## Entity 4 — VerificationContract

본 Epic 의 acceptance 검증 명령 set. CI / smoke / 사용자 직접 검증 모두 cover.

| ID | Verification | Layer | Pass Criteria |
|---|---|---|---|
| V1 | `bun typecheck` | Layer 1b | exit 0 (KOSMOS narrows to `src/stubs/**` only) |
| V2 | `bun test` | Layer 1b | pass count ≥ 983 (현 main baseline) |
| V3 | `uv run pytest` | Layer 1a | pass count ≥ 3458 (현 main baseline) |
| V4 | `for f in <PORTed files>; do diff -q $f $cc_f; done` | byte-identical audit | swap-1 화이트리스트 외 diff 0 |
| V5 | `bun run tui` 부팅 + `lookup` 1회 | Layer 3 (PTY) | OTEL Langfuse trace 에 `kosmos.tool.id=lookup` span pair 출현 |
| V6 | `bun run tui --print "안녕"` | Layer 3 | exit 0, stdout ≥ 1 byte, stderr 에 "not supported" 0회 |
| V7 | `scripts/tui-tmux-capture.sh` (full smoke) | Layer 5 | snap-NNN 시퀀스 PASS |
| V8 | audit 재실행 (`specs/cc-migration-audit/` 9-stream grep) | audit closure | D-bucket entries 0 for 9 items |
| V9 | `tmux capture-pane` 후 final.txt 에 `tool_registry: \d+ entries verified` + `KOSMOS` branding | Layer 5 | 둘 다 출현 |
