# CC 2.1.88 모듈 정밀 분석 — KOSMOS 사용 가능성 매트릭스

**Status**: in-progress (Phase A T003b mid-execution, informs Phase B scope)
**Date**: 2026-04-27
**Scope**: `tui/src/` 영역만. `src/kosmos/` (Python 백엔드)는 별도 분석.
**Memory refs**: `project_tui_architecture` (services/api/만 stdio JSONL로 교체), `feedback_cc_tui_90_fidelity`, `project_tui_anthropic_residue`, `feedback_check_references_first`.

## KOSMOS 결정 사항 (이 분석의 기준)

- **단일 LLM provider**: FriendliAI Serverless + K-EXAONE (메모리 `project_friendli_tier_wait`). Anthropic SDK / Bedrock / Vertex / Foundry 등 일체 무관.
- **Auth**: `KOSMOS_FRIENDLI_TOKEN` (또는 `FRIENDLI_API_KEY`) env-var 단일. OAuth / Console subscription / Claude.ai login / API key helper / Keychain 일체 무관.
- **Telemetry**: Spec 021 OTEL → 로컬 Langfuse (vision.md § L1-A A7, 외부 egress 0). Datadog / BigQuery / 1P event logger / GrowthBook 일체 무관.
- **Tools**: 5-primitive (`lookup`, `resolve_location`, `submit`, `verify`, `subscribe`) + Mock 어댑터 6 디렉토리. CC의 Anthropic-internal tools (REPLTool, SuggestBackgroundPRTool, VerifyPlanExecutionTool, claudeCodeGuideAgent 등) 무관.
- **Remote/Teleport**: KOSMOS는 terminal-native 단일 시민 세션. CC의 remote-session / teleport / Grove 무관.

## CC 모듈 분류 매트릭스

### A. **삭제 대상** (CC-Anthropic 전용, KOSMOS에 가치 0)

> 이 그룹은 caller까지 모두 stub-noop으로 처리. 파일 자체를 삭제하기보다 stub으로 두는 이유는 import 사이트 수가 많아 일괄 변경 시 회귀 위험이 크기 때문.

| 카테고리 | 파일 | KOSMOS 무관 사유 |
|---|---|---|
| **Auth / Subscription** | `services/oauth/client.ts` | Anthropic OAuth flow — KOSMOS는 env-var auth |
| | `services/oauth/getOauthProfile.ts`, `index.ts`, `types.ts` | 同上 |
| | `services/claudeAiLimits.ts`, `services/claudeAiLimitsHook.ts` | Claude.ai subscription tier limits |
| | `services/policyLimits/index.ts`, `types.ts` | Anthropic policy enforcement |
| | `services/remoteManagedSettings/index.ts` | Anthropic remote-managed settings |
| | `hooks/useApiKeyVerification.ts` | Anthropic API key 검증 — 이미 KOSMOS-1978 T005 stub |
| **Anthropic API surface** | `services/api/claude.ts` | Anthropic SDK 본체 — Spec 1978 T010에서 stub-only로 collapse |
| | `services/api/client.ts` | Anthropic HTTP client |
| | `services/api/grove.ts` | Anthropic Grove feature |
| | `services/api/adminRequests.ts` | Anthropic admin endpoints |
| | `services/api/dumpPrompts.ts` | Anthropic prompt dumping |
| | `services/api/filesApi.ts` | Anthropic Files API |
| | `services/api/firstTokenDate.ts` | Anthropic billing tracking |
| | `services/api/withRetry.ts` | Anthropic retry — KOSMOS는 LLMClient.stream 자체에 retry |
| **Analytics / Telemetry** | `services/analytics/datadog.ts` | Datadog 1P sink |
| | `services/analytics/firstPartyEventLogger.ts` | Anthropic 1P event logger |
| | `services/analytics/firstPartyEventLoggingExporter.ts` | 1P logging exporter — 부팅 fail의 직접 원인 (T003b) |
| | `services/analytics/sink.ts` | Analytics sink fanout |
| | `services/analytics/sinkKillswitch.ts` | Anthropic killswitch |
| | `services/analytics/growthbook.ts` | GrowthBook A/B test |
| | `services/analytics/config.ts` | Analytics config |
| | `utils/telemetry/betaSessionTracing.ts`, `bigqueryExporter.ts`, `events.ts`, `instrumentation.ts`, `logger.ts`, `perfettoTracing.ts`, `pluginTelemetry.ts`, `sessionTracing.ts`, `skillLoadedEvent.ts` | Anthropic-internal telemetry stack |
| | `services/api/logging.ts` (대부분) | API logging — `Usage` 타입만 보존 (KOSMOS도 token usage 추적) |
| **Remote / Teleport** | `bridge/{remoteBridgeCore, sessionRunner, replBridge*, codeSessionApi, trustedDevice, jwtUtils, workSecret, capacityWake}.ts` 전체 | Anthropic remote-session bridge — KOSMOS는 stdio NDJSON 단일 |
| | `remote/RemoteSessionManager.ts`, `SessionsWebSocket.ts`, `remotePermissionBridge.ts`, `sdkMessageAdapter.ts` | Anthropic remote sessions |
| | `utils/teleport.tsx`, `utils/teleport/*` | Anthropic teleport |
| | `hooks/useTeleportResume.tsx`, `components/TeleportResumeWrapper.tsx` | Teleport UI |
| | `components/grove/Grove.tsx` | Anthropic Grove |
| **Anthropic-specific tools** | `tools/REPLTool/*` | CC built-in REPL tool |
| | `tools/SuggestBackgroundPRTool/*` | CC built-in PR suggestion |
| | `tools/VerifyPlanExecutionTool/*` | CC built-in plan verification |
| | `tools/AgentTool/built-in/{claudeCodeGuideAgent, exploreAgent, planAgent, verificationAgent}.ts` | CC built-in agents — KOSMOS는 Spec 027 swarm 별도 |
| | `tools/SyntheticOutputTool/SyntheticOutputTool.ts` | CC synthetic output |
| **Anthropic commands** | `commands/login/login.tsx` | Anthropic login |
| | `commands/assistant/assistant.tsx` | Anthropic assistant management |
| | `commands/agents-platform/*` | Anthropic agents-platform CLI |
| | `commands/insights.ts` | Anthropic insights — 이미 KOSMOS-1978 T008 LLMClient stub |
| | `commands/rename/generateSessionName.ts` | Anthropic Haiku — 이미 KOSMOS-1978 T007 LLMClient stub |
| **Auto-installer / version mgmt** | `utils/nativeInstaller/*`, `cli/update.ts`, `cli/install.ts`, `cli/handlers/util.ts:installHandler` | Anthropic native installer |
| | `components/AutoUpdater.tsx`, `AutoUpdaterWrapper.tsx`, `NativeAutoUpdater.tsx`, `PackageManagerAutoUpdater.tsx` | Auto-update UI |
| | `hooks/notifs/useNpmDeprecationNotification.tsx` | Anthropic npm deprecation banner |
| **Anthropic constants / utils** | `constants/betas.ts`, `utils/betas.ts` | Anthropic beta headers |
| | `constants/oauth.ts` | Anthropic OAuth constants |
| | `utils/modelCost.ts` | Anthropic model pricing |
| | `services/contextCollapse/index.ts` | Anthropic context-collapse — KOSMOS uses snipCompact + Spec 026 prompt registry |
| | `services/compact/cachedMicrocompact.ts` | Anthropic cached microcompact |
| | `services/mcp/claudeai.ts` | Claude.ai-specific MCP server config |
| | `ink/devtools.ts` | Ink devtools (optional, 안 써도 무관) |
| | `services/policyLimits/types.ts`, `services/policyLimits/index.ts` | Anthropic policy types |

### B. **유지 대상** (CC fidelity ≥90% — `feedback_cc_tui_90_fidelity` 직접 적용)

| 카테고리 | 파일 |
|---|---|
| **Main agent loop** | `query.ts` (1,200+ lines, ReAct loop) — CC 그대로 |
| | `QueryEngine.ts` — CC 그대로 |
| | `query/deps.ts` (KOSMOS-1633 P2 stub로 LLM call만 redirected) |
| | `Tool.ts`, `tools.ts` — tool abstraction |
| | `commands.ts` — slash command framework |
| **REPL / UI** | `screens/REPL.tsx`, `screens/*` |
| | `components/PromptInput/*` (시민 입력 surface) |
| | `components/permissions/*` (Spec 033) |
| | `components/agents/*` (Spec 027 — partial; CC fidelity 보존) |
| | `themes/*`, `colors/*`, ink wrapper components |
| **Permissions** | `permissions/*` — Spec 033 v2 spectrum |
| **Compaction** | `services/compact/{compact, autoCompact, microCompact, snipCompact, reactiveCompact}.ts` — CC fidelity (Spec 026 prompt registry는 별 layer) |
| **Tool implementations** | `tools/{Edit, Read, Write, Bash, Grep, Glob, Task, NotebookEdit, BashOutput, KillShell}/...` — CC 5-tool 그대로 (Phase 4에서 5-primitive로 추가 wiring) |
| | `tools/{CalculatorTool, DateParserTool, ExportPDFTool, TranslateTool, WebFetchTool, WebSearchTool}/...` — 보조 도구 (Constitution V Principle 9) |
| | `tools/{LookupPrimitive, SubmitPrimitive, SubscribePrimitive, VerifyPrimitive}/*` — KOSMOS Spec 031 (이미 ship) |
| **IPC / Bridge** | `ipc/{bridge, bridgeSingleton, codec, llmClient, llmTypes, frames.generated, schema/*}.ts` — Spec 032 |
| | `ipc/{backpressure-hud, crash-detector, envelope, mcp, pipa.generated, tx-registry}.ts` |
| **Hooks (대부분)** | `hooks/*.tsx` (useApiKeyVerification 제외, useTeleportResume 제외) — CC 그대로 |
| **Utils (대부분)** | `utils/{commands, debug, log, messages, model/*, plugins/*, sandbox/*, scratchpad/*, sinks, fileSystem, ...}.ts` — CC fidelity |
| **Bootstrap / state** | `bootstrap/*.ts`, `state/*.ts`, `store/*.ts` — CC core |

### C. **KOSMOS-original** (CC에 없음 — 신규 KOSMOS 코드)

| 파일 | 출처 | 비고 |
|---|---|---|
| `ipc/llmClient.ts` | Spec 1633 | KOSMOS-original LLMClient stream adapter |
| `ipc/mcp.ts` | Spec 1634 | KOSMOS stdio-MCP client |
| `ipc/schema/frame.schema.json` | Spec 032 | 19-arm KOSMOS-original |
| `entrypoints/envGuard.ts` | Spec 1633 T011 | KOSMOS fail-closed credential gate |
| `query/deps.ts` (`queryModelWithStreaming`) | Spec 1633 P2 | DI boundary stub |
| `tools/{Lookup,Submit,Subscribe,Verify}Primitive/*` | Spec 031 | 5-primitive surface |
| `services/analytics/index.ts`, `metadata.ts` | Spec 1633 P2 | stub-noop |
| `services/oauth/{client,index,types,getOauthProfile}.ts` | Spec 1633 P2 | stub-noop |
| `commands/env/index.ts/.js` | Spec 1632 P0 | KOSMOS-1632 P0 auto-stub |

## Phase B 정밀 scope (이 audit의 결과)

기존 spec.md FR-004 / 86-task plan에서 Phase B는 "4 callsite migration + claude.ts collapse"로 좁게 정의됨. 그러나 실제 부팅 막는 결손 export는 **caller 측 stubification 미완**의 결과 — 즉 Phase B scope가 더 넓어야 함.

### Phase B 확장 대상 (caller stubification)

T003b 수습 + 부팅 unblocking 위해 즉시 stubify 해야 하는 caller (= "삭제 대상" 그룹의 파일들):

**P1 (현재 부팅 막음)**:
- `services/analytics/sink.ts`
- `services/analytics/firstPartyEventLoggingExporter.ts`

**P2 (P1 처리 후 cascade로 노출 예상)**:
- `services/analytics/{datadog, firstPartyEventLogger, growthbook, config, sinkKillswitch}.ts`
- `services/api/{grove, adminRequests, dumpPrompts, filesApi, firstTokenDate, withRetry, client}.ts`
- `services/{claudeAiLimits, claudeAiLimitsHook}.ts`
- `services/policyLimits/{index, types}.ts`
- `services/remoteManagedSettings/index.ts`
- `services/mcp/claudeai.ts`
- `services/contextCollapse/index.ts`
- `bridge/{remoteBridgeCore, sessionRunner, replBridge*, codeSessionApi, trustedDevice, jwtUtils, workSecret, capacityWake}.ts`
- `remote/{RemoteSessionManager, SessionsWebSocket, remotePermissionBridge, sdkMessageAdapter}.ts`
- `commands/{login, assistant, agents-platform}/*`
- `tools/{REPLTool, SuggestBackgroundPRTool, VerifyPlanExecutionTool, SyntheticOutputTool}/*`
- `tools/AgentTool/built-in/{claudeCodeGuideAgent, exploreAgent, planAgent, verificationAgent}.ts`
- `utils/teleport*`, `utils/nativeInstaller/*`, `utils/telemetry/*`, `utils/modelCost.ts`, `utils/betas.ts`
- `constants/{betas, oauth}.ts`
- `cli/update.ts`, `cli/install.ts`, `cli/handlers/util.ts` (installHandler / doctorHandler)
- `components/{AutoUpdater*, NativeAutoUpdater, PackageManagerAutoUpdater, TeleportResumeWrapper, grove/Grove}.tsx`
- `hooks/{useTeleportResume.tsx, notifs/useNpmDeprecationNotification.tsx}`

**P3 (cascade가 더 깊어질 가능성)**:
- caller들이 stub-noop화될 때 그 caller들의 caller 또한 평가 — `screens/REPL.tsx`나 `main.tsx`가 위 일부를 import할 수 있음. 그 때는 import 자체를 제거 또는 conditional.

### Stubification 패턴 (`feedback_cc_source_migration_pattern` 일관 적용)

각 stub 파일에 표준 헤더:

```typescript
// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T003b — stub-noop replacement.
//
// Original CC module: <CC restored-src path>
// CC version: 2.1.88
// KOSMOS deviation: <one-line reason — Anthropic-only feature, OAuth, Datadog, etc>
//
// Function shapes preserved so existing call sites compile without
// mass-editing. Runtime effect is zero — KOSMOS routes equivalent
// behaviour through <KOSMOS replacement: OTEL pipeline / FriendliAI /
// Spec 027 swarm / etc>.
```

각 stub function은 CC original signature 보존, 본문은 no-op 또는 safe default (`return null` / `return false` / `return Promise.resolve()` / `return {} as Record<...>`).

## 다음 액션

이 audit를 기반으로:

1. **즉시** (T003b 부팅 unblock): `services/analytics/sink.ts` + `firstPartyEventLoggingExporter.ts` stubify
2. **Phase A 마무리** (T003 PromptInput guard + T004 patch): 부팅 banner 안정화 후 진단 재개
3. **Phase B 정식 진행** (T005-T016 + 위 P2 caller list 확장): 86-task plan 그대로 진행하되 P2 caller list를 task body에 명시적으로 추가. tasks.md 갱신 또는 cohesive merge 적용 (메모리 `feedback_subissue_100_cap`).
4. **Long-term** (별도 cleanup PR): 위 "삭제 대상" 카테고리 A 파일들 중 import callsite가 0이 된 것은 실제 파일 삭제. Constitution §I rewrite boundary 명시.
