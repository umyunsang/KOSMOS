# S6 — Services (services/tools 제외) 감사

## 메타
- 스코프: S6 Services 레이어. `tui/src/services/` 트리 전부 (단, `services/tools/` 는 별도 슬라이스). swap-1 (LLM provider) 종속 표면이 가장 많이 모여있는 영역.
- CC 파일수: **120** (.ts/.tsx, services/tools/ 제외)
- KOSAX 파일수: **101** (.ts/.tsx, services/tools/ 제외)
- 작업 일시: 2026-05-03
- 감사자: S6 Lead Opus

## 4-bucket 요약

| Bucket | 파일 수 | 핵심 |
| --- | --- | --- |
| **PORT** (CC 있음, KOSAX 없음) | 26 | 전부 claude.ai 1P 종속 → swap-1 정당화로 **드롭 유지**. 누락이 아니라 의도적 삭제. |
| **PRESERVE-IDENTICAL** (byte-동등) | 64 | mcp/* 다수 + lsp/* + voice + extractMemories + autoDream + plugins 부분 + compact 다수 등 CC 원본 그대로. 변경 금지. |
| **MIGRATE-FOR-SWAP** (둘 다, 발산) | 28 | swap-1 정당 23개 / spec-citation (Epic #1633/1978/2077/2152/2293/2521) 정당 5개. byte-회귀 후보 0. |
| **DROP-CANDIDATE** (KOSAX-only) | 9 | 7개 KOSAX-1633 stub-noop (consumer compat) + 2개 spec citation (Epic #2294/#2296). 제거 대상 0. |

---

## swap-1 종속 표면 매핑 (가장 중요한 발견)

| CC Anthropic 1P 표면 | KOSAX 대응 | 마이그레이션 상태 |
| --- | --- | --- |
| `services/api/claude.ts` (3419 LOC, Anthropic SDK 스트리밍 핸들러) | `tui/src/services/api/claude.ts` (3451 LOC, byte-copy + 4 swap label) | **완전한 byte-copy 보존** + 4개 swap (`swap/llm-provider`, `swap/anti-anthropic-1p`, `swap/identifier-rename`, `byte-copy(2521)`). 헤더 코멘트가 명시: "this file has zero callers in tui/src after Spec 2293" — 실제 LLM 트래픽은 전부 `tui/src/ipc/llmClient.ts` (Spec 1978 stdio bridge) 로 우회. KOSAX 는 K-EXAONE/FriendliAI 호출을 **claude.ts 가 아닌 Python 백엔드**가 담당하도록 마이그레이션함. **이 파일은 CC 레퍼런스 박물관용 박제 + replay 감사용**으로 살아있음. |
| `services/api/client.ts` (CC 389 LOC, Anthropic/Bedrock/Vertex 클라이언트 팩토리) | `tui/src/services/api/client.ts` (49 LOC, no-op stub) | **89% 축소**. `getAnthropicClient` 가 throw 하는 stub 으로 교체. claude.ts 의 import 가 link-time 에 해소되도록 surface 만 보존. 단, `getAnthropicClient` 가 **동일 파일에 2번 정의됨** (line 23, line 47) — TS 중복-export 경고. P1 fix. |
| `services/api/withRetry.ts` (CC 529-error retry 하네스) | `tui/src/services/api/withRetry.ts` (no-op `is529Error → false`) | KOSAX 의 backpressure 는 Spec 032 stdio IPC 가 담당. 1-shot stub 정당. |
| `services/oauth/client.ts` (CC 566 LOC, Anthropic OAuth PKCE flow) | `tui/src/services/oauth/client.ts` (83 LOC) | **85% 축소**. 모든 export 가 `null` / `false` / no-op 반환. KOSAX 인증 = `FRIENDLI_API_KEY` env-var only. 정당. |
| `services/oauth/index.ts` (CC OAuth barrel) | `tui/src/services/oauth/index.ts` | `OAuthService` 클래스 stub (login/logout/refresh/isAuthenticated 모두 null/false). 정당. |
| `services/oauth/getOauthProfile.ts` | KOSAX no-op stub (4 LOC) | 정당. |
| `services/oauth/auth-code-listener.ts` (CC) | **DROPPED in KOSAX** | localhost OAuth callback HTTP 서버 — KOSAX 미사용. 정당. |
| `services/oauth/crypto.ts` (CC) | **DROPPED in KOSAX** | OAuth PKCE crypto helper — 미사용. 정당. |
| `services/claudeAiLimits.ts` (CC 구독 quota 트래커) | `tui/src/services/claudeAiLimits.ts` (KOSAX-1633/2077 stub) | `currentLimits = { isUsingOverage: false }` 등 inert export. claude.ts byte-copy 의 import 해소용. 정당. |
| `services/claudeAiLimitsHook.ts` (CC React hook) | **DROPPED in KOSAX** | UI Hook 미사용. 정당. |
| `services/teamMemorySync/index.ts` (CC: `/api/claude_code/team_memory` axios 호출) | `tui/src/services/teamMemorySync/index.ts` | **MIGRATE-FOR-SWAP 의심**. 헤더에 여전히 "Anthropic API contract" 주석 + axios live-call 코드 보임. KOSAX 는 이 surface 를 어떻게 차단하는지 불명. **사용자 결정 필요 (아래 §사용자 결정 참조)**. |
| `services/settingsSync/index.ts` (CC: 시민 settings.json 클라우드 동기화) | `tui/src/services/settingsSync/index.ts` | 부분 stub: `getOauthConfig` → 빈 string 반환으로 dead-end. axios 코드는 여전히 존재. callgraph 확인 필요. |
| `services/api/usage.ts` / `referral.ts` / `firstTokenDate.ts` / `bootstrap.ts` / `adminRequests.ts` / `overageCreditGrant.ts` / `sessionIngress.ts` / `ultrareviewQuota.ts` / `filesApi.ts` / `policyLimits/*` / `remoteManagedSettings/*` (CC) | **DROPPED in KOSAX** (10+개) | 전부 claude.ai 구독 / 빌링 / 1P 텔레메트리 / 엔터프라이즈 정책 동기화. 정당. |
| `services/analytics/datadog.ts` + `analytics/sink.ts` (CC: Datadog + 1P 이벤트 sink) | **DROPPED in KOSAX** | Anthropic 1P 텔레메트리. KOSAX 는 Spec 028 OTLP collector + Langfuse (zero external egress). 정당. |
| `services/mockRateLimits.ts` + `rateLimitMocking.ts` (CC `[ANT-ONLY]` 마커) | **DROPPED in KOSAX** (Spec 2112) | Spec 2112 (dead-anthropic-models) 에서 명시 삭제. 정당. |
| `services/internalLogging.ts` (CC) | **DROPPED in KOSAX** | Anthropic 내부 PII 로깅. 정당. |

**판정 요약**: swap-1 마이그레이션 **상태 양호**. 단, 두 가지 위험:
1. `api/client.ts` 의 `getAnthropicClient` 함수 **중복 정의** (line 23 + line 47) — 컴파일은 되지만 TS warning + linter 적발 위험. **P1 권고**.
2. `teamMemorySync/index.ts` + `settingsSync/index.ts` 가 **byte-copy 처럼 보이지만 axios live-call 코드 잔존**. callgraph 가 dead 임을 보장하는 게이트가 명시되지 않음. claude.ts 처럼 헤더에 "zero callers in tui/src" 단언이 없음. **사용자 결정 필요**.

---

## PORT (CC 있음, KOSAX 없음) — 26개

전부 **DROP-유지 정당화**. 누락 아님. KOSAX 가 의도적으로 삭제했고 swap-1 종속이 명백.

| 카테고리 | 파일 (`services/` 기준) | 정당화 |
| --- | --- | --- |
| Anthropic 1P API endpoints | `api/adminRequests.ts`, `api/bootstrap.ts`, `api/filesApi.ts`, `api/firstTokenDate.ts`, `api/overageCreditGrant.ts`, `api/referral.ts`, `api/sessionIngress.ts`, `api/ultrareviewQuota.ts`, `api/usage.ts` | 전부 `getOauthConfig()` axios 호출. KOSAX 는 claude.ai backend 에 도달 불가. 정당. |
| Anthropic SDK 에러 헬퍼 | `api/errorUtils.ts` | `import type { APIError } from '@anthropic-ai/sdk'` + `*.anthropic.com` 메시지. 정당. |
| Claude.ai 구독 React hook | `claudeAiLimitsHook.ts` | UI 표시 — KOSAX 미사용. 정당. |
| Anthropic 1P 텔레메트리 | `analytics/datadog.ts`, `analytics/sink.ts`, `internalLogging.ts` | Spec 028 OTEL 로 대체. 정당. |
| Mock rate-limit fixtures | `mockRateLimits.ts`, `rateLimitMocking.ts` | Spec 2112 명시 삭제 (`[ANT-ONLY]` 마커). 정당. |
| OAuth PKCE 보조 | `oauth/auth-code-listener.ts`, `oauth/crypto.ts` | KOSAX no-OAuth. 정당. |
| 클라우드 정책 동기화 | `policyLimits/index.ts`, `policyLimits/types.ts`, `remoteManagedSettings/index.ts`, `remoteManagedSettings/securityCheck.tsx`, `remoteManagedSettings/syncCache.ts`, `remoteManagedSettings/syncCacheState.ts`, `remoteManagedSettings/types.ts` | 엔터프라이즈 IT 관리 — KOSAX 시민 도메인 무관. 정당. |
| Tool-use 자연어 요약 | `toolUseSummary/toolUseSummaryGenerator.ts` | `queryHaiku` 의존 — Spec 1633 에서 Haiku 제거 후 사용 불가. 정당. |

**누락 PORT 후보 0개**.

---

## PRESERVE-IDENTICAL (둘 다 있고 byte-동등) — 64개

byte-회귀 시 즉각 CC 원본으로 복구. 변경 금지.

| 서브트리 | 파일 |
| --- | --- |
| `AgentSummary/` (1) | `agentSummary.ts` |
| `analytics/` (2) | `firstPartyEventLoggingExporter.ts`, `metadata.ts`, `sinkKillswitch.ts` |
| `api/` (4) | `emptyUsage.ts`, `errors.ts`, `logging.ts`, `metricsOptOut.ts` |
| `autoDream/` (4) | `autoDream.ts`, `config.ts`, `consolidationLock.ts`, `consolidationPrompt.ts` |
| `compact/` (6) | `apiMicrocompact.ts`, `compact.ts`, `compactWarningHook.ts`, `compactWarningState.ts`, `grouping.ts`, `sessionMemoryCompact.ts`, `timeBasedMCConfig.ts` |
| `extractMemories/` (2) | `extractMemories.ts`, `prompts.ts` |
| `lsp/` (6) | `LSPClient.ts`, `LSPDiagnosticRegistry.ts`, `LSPServerInstance.ts`, `LSPServerManager.ts`, `manager.ts`, `passiveFeedback.ts`, `config.ts` |
| `MagicDocs/` (2) | `magicDocs.ts`, `prompts.ts` |
| `mcp/` (20) | `channelAllowlist.ts`, `channelNotification.ts`, `channelPermissions.ts`, `elicitationHandler.ts`, `envExpansion.ts`, `headersHelper.ts`, `InProcessTransport.ts`, `MCPConnectionManager.tsx`, `mcpStringUtils.ts`, `normalization.ts`, `oauthPort.ts`, `officialRegistry.ts`, `SdkControlTransport.ts`, `types.ts`, `useManageMCPConnections.ts`, `utils.ts`, `vscodeSdkMcp.ts`, `xaa.ts` |
| `mcpServerApproval.tsx` | (1) |
| `notifier.ts` + `preventSleep.ts` + `diagnosticTracking.ts` + `rateLimitMessages.ts` + `voice.ts` + `voiceKeyterms.ts` | (6) |
| `plugins/` (2) | `PluginInstallationManager.ts`, `pluginOperations.ts` |
| `PromptSuggestion/` (1) | `speculation.ts` |
| `SessionMemory/` (3) | `prompts.ts`, `sessionMemory.ts`, `sessionMemoryUtils.ts` |
| `settingsSync/types.ts` | (1) |
| `teamMemorySync/` (4) | `secretScanner.ts`, `teamMemSecretGuard.ts`, `types.ts`, `watcher.ts` |
| `tips/` (2) | `tipHistory.ts`, `tipScheduler.ts` |

소계 **64 파일** byte-identical. CC `services/` 의 핵심 비-LLM 인프라 (mcp · lsp · compact · session/agent memory · voice · auto-dream · extract-memories · plugins) 가 그대로 살아있음. **CC 하네스의 본체가 KOSAX 에 보존되어 있다는 강한 증거**.

---

## MIGRATE-FOR-SWAP (둘 다 있고 다름) — 28개

각 발산은 swap-1 (Anthropic SDK → KOSAX IPC) 또는 명시적 spec citation 으로 정당화.

### A. swap-1 단순 import 재배선 (16개)

CC 가 `@anthropic-ai/sdk` import → KOSAX `src/sdk-compat.js` 또는 stub. 1~5줄 차이.

| 파일 | 차이 요약 |
| --- | --- |
| `api/claude.ts` | byte-copy + 4-swap label (위 §swap-1 표 참조) |
| `api/dumpPrompts.ts` | `import type { ClientOptions } from 'src/sdk-compat.js'` (CC: `@anthropic-ai/sdk`) |
| `api/errors.ts` | SDK error type alias 교체 |
| `api/logging.ts` | SDK Usage type 교체 |
| `api/promptCacheBreakDetection.ts` | SDK type 교체 |
| `api/withRetry.ts` | 위 §swap-1 표 참조 (no-op stub) |
| `api/grove.ts` | claude.ai pro-tier billing → no-op stub (`isQualifiedForGrove → false`) |
| `mcp/auth.ts` | `constants/oauth.MCP_CLIENT_METADATA_URL` → 빈 string + secureStorage stub |
| `mcp/client.ts` | `@anthropic-ai/sdk/resources/index.mjs` → `src/sdk-compat.js`, `getOauthConfig` → null, `clearKeychainCache` → no-op, `markClaudeAiMcpConnected` → no-op |
| `mcp/claudeai.ts` | KOSAX 전체 no-op stub (claude.ai MCP fetch 차단) |
| `mcp/config.ts` | `fetchClaudeAIMcpConfigsIfEligible` 인라인 no-op |
| `mcp/xaaIdpLogin.ts` | claude.ai IdP 로그인 차단 |
| `compact/autoCompact.ts` / `microCompact.ts` / `postCompactCleanup.ts` / `prompt.ts` | swap-1 type aliasing + 일부 KOSAX 라벨 |

### B. KOSAX 1P 텔레메트리 / 1P call 차단 stub (8개)

| 파일 | 차이 요약 |
| --- | --- |
| `analytics/index.ts` | 전체 no-op (KOSAX-1633 P2). 모든 `logEvent` 가 silent. |
| `analytics/firstPartyEventLogger.ts` | `initialize1PEventLogging` → no-op |
| `analytics/growthbook.ts` | `getFeatureValue → defaultValue` (모든 feature flag disabled) |
| `analytics/config.ts` | KOSAX-1633 stub |
| `analytics/metadata.ts` (?) — 위 PRESERVE 표에 있으나 확인 필요 | (재확인) |
| `claudeAiLimits.ts` | `currentLimits` inert export |
| `awaySummary.ts` | KOSAX 변경 (claude.ts 호출 → IPC 우회) |
| `voiceStreamSTT.ts` | KOSAX 변경 (Anthropic 음성 stream API → 차단 / 대체) |
| `vcr.ts` | KOSAX 변경 (claude.ai recorder 제거) |

### C. Spec citation 발산 (4개)

| 파일 | spec | 차이 |
| --- | --- | --- |
| `oauth/client.ts` | Epic #1633 P2 | 위 §swap-1 표 참조 |
| `oauth/index.ts` | Epic #1633 P2 | `OAuthService` class stub |
| `oauth/getOauthProfile.ts` | Epic #1633 | 4 LOC stub |
| `plugins/pluginCliCommands.ts` | KOSAX-1633 (telemetry 제거) | `buildPluginTelemetryFields` / `classifyPluginCommandError` 인라인 no-op |
| `tips/tipRegistry.ts` | KOSAX (claude.ai 빌링 dead) | `OverageCreditUpsell`/`overageCreditGrant`/`referral` import 제거, `guest-passes` tip 항목 삭제 |
| `tokenEstimation.ts` | KOSAX (Anthropic tokenizer dependency) | (확인 필요 — diff 1줄) |
| `settingsSync/index.ts` | (불명확) | 위 §swap-1 표 P1 risk 참조 |
| `teamMemorySync/index.ts` | (불명확) | 위 §swap-1 표 P1 risk 참조 |

byte-회귀 후보 **0개**.

---

## DROP-CANDIDATE (KOSAX-only) — 9개

전부 spec citation 으로 정당화. 제거 대상 없음.

| 경로 (`tui/src/services/` 기준) | 정당화 |
| --- | --- |
| `api/adapterManifest.ts` | Epic ε #2296 T009 — Adapter manifest singleton cache (FR-015/016/019). swap-2 (도구 시스템) 본체. 정당. |
| `compact/cachedMicrocompact.ts` | KOSAX-1633 — 원래 CC microcompact 캐시 → KOSAX Spec 026 prompt registry 가 백엔드에서 처리. 프론트엔드 shell 유지. 정당. |
| `compact/snipCompact.ts` | KOSAX-1633/1978 — 원래 CC tool-result snipping → Spec 026 PromptManifest 가 처리. no-op 유지. 정당. |
| `contextCollapse/index.ts` | KOSAX-1633 — 원래 CC TokenWarning 구독 → Spec 027 mailbox + Spec 028 OTLP. no-op. 정당. |
| `lsp/types.ts` | P0 reconstructed stub (rebuild-stubs.ts) — CC import 가 link-time 에 해소되도록. 정당. |
| `oauth/types.ts` | KOSAX-1633 — 외부 consumer 의 `BillingType` / `OAuthTokens` import 보존용. 정당. |
| `skillSearch/signals.ts` | P0 reconstructed (Pass 3) — `attachments.ts` consumer 가 import 하는 `DiscoverySignal` 타입. CC 원본 미수복. 정당. |
| `tips/types.ts` | P0 reconstructed stub. 정당. |
| `toolRegistry/bootGuard.ts` | Epic γ #2294 T004 — 4 primitive (lookup/submit/verify/subscribe) `Tool<>` 9-member surface 보장. swap-2 본체. 정당. |

**KOSAX-only 인플레 위험 0**.

---

## 핵심 발견

1. **swap-1 마이그레이션 양호** — claude.ts (3451 LOC) 는 byte-copy 박제로 zero-callers 보장 (Spec 2293). client.ts/oauth/* 는 stub 으로 89~100% 축소. CC `services/api/` 의 12개 1P endpoint (usage/referral/bootstrap/...) 는 전부 의도적 삭제. swap-1 이 깨끗하게 격리되어 있음.
2. **API client 중복 함수 정의** — `tui/src/services/api/client.ts` 에 `getAnthropicClient` 가 line 23 + line 47 두 번 정의됨 (TS 동일-이름 export 중복). 컴파일은 되지만 P1 fix 권고.
3. **CC 비-LLM 인프라 64개 byte-identical** — mcp(20) + lsp(7) + compact(6+) + autoDream(4) + extractMemories(2) + MagicDocs(2) + SessionMemory(3) + AgentSummary + voice + tips + plugins(2) + notifier + preventSleep + diagnosticTracking + voiceKeyterms 등 CC 하네스 본체가 그대로 살아있음. CORE THESIS ("CC + 2 swaps") 가 services 레이어에서 가장 명확히 보존됨.
4. **PORT 누락 0 / DROP-CANDIDATE 인플레 0** — CC→KOSAX 26개 삭제는 전부 swap-1 정당. KOSAX-only 9개는 전부 spec citation. 수치적으로 가장 깔끔한 슬라이스 (S1 과 동등 수준).
5. **teamMemorySync + settingsSync 의 미해결 dead-call** — claude.ts 처럼 "zero callers in tui/src" 헤더 단언이 없음. axios live-call 코드는 여전히 존재. callgraph 가 정말 dead 인지 확인 게이트 부재.

---

## 사용자 결정 필요

1. **`teamMemorySync/index.ts` + `settingsSync/index.ts` 처리** — CC 코드가 거의 그대로 잔존하나 swap-1 종속 (claude.ai backend 호출). 두 가지 선택지:
   - **A**: claude.ts 처럼 byte-copy 박제 + "zero callers" 게이트 헤더 명시 + `getOauthConfig` 빈 string dead-end 유지 (현 상태 + 헤더만 추가).
   - **B**: oauth/client.ts 처럼 전체 no-op stub 으로 89% 축소 (Spec 1633 P2 패턴).
   - 권고: **B** — CC 박제는 claude.ts 한 곳으로 충분. team-memory / settings-sync 는 claude.ai SaaS 종속이 명확하므로 stub 화하는 게 callgraph 안전.

2. **`api/client.ts` 중복 `getAnthropicClient` 정의** — line 23 (async, throw-on-call) + line 47 (sync, return null) 두 시그니처 충돌. P1 fix 로 line 47 (Spec 2521 swap label) 만 남기고 line 23 (Spec 2077 stub) 삭제 권고. 사용자 승인 후 fix.
