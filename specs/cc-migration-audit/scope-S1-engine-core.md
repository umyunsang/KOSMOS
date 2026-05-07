# S1 — Engine Core 감사

## 메타
- 스코프: S1 Engine Core (query loop · agentic dispatch · session/cost tracking · Task system)
- CC 파일수: **24** / 총 LOC: **7,927**
- KOSAX 파일수 (대응 영역, TS): **31** / 총 LOC: **8,891**
- KOSAX Python 백엔드 (LLM swap 종속, `src/kosax/{llm,engine}/`): **19** / 총 LOC: **3,991**
- 작업 일시: 2026-05-03
- 감사자: S1 Lead Opus

## 4-bucket 요약
| Bucket | 파일 수 | 핵심 |
| --- | --- | --- |
| **PORT** (CC 있음, KOSAX 없음) | 0 | 누락 없음. CC 24개 파일 전부 KOSAX 측에 대응 존재. |
| **PRESERVE-IDENTICAL** (byte-동등) | 18 | SHA-256 hash 일치 확인. 변경 금지. |
| **MIGRATE-FOR-SWAP** (둘 다, 발산) | 6 | 모두 swap-1 (Anthropic SDK→KOSAX IPC) / swap-2 (도구 시스템) 혹은 명시적 spec citation 발산. byte-회귀 후보 0. |
| **DROP-CANDIDATE** (KOSAX-only) | 7 (TS) + 19 (Python) | TS 7개 모두 spec-justified (P0 reconstructed / Epic citation / KOSAX-1633/1978/2077). Python 19개는 swap-1 의 backend-side 본체로 정당화 자명. 제거 대상 없음. |

## PRESERVE-IDENTICAL (둘 다 있고 byte-동등) — 18개

SHA-256 일치. **변경 금지** — 회귀 시 즉각 CC 원본으로 복구.

| 경로 (`tui/src/` 기준) | LOC |
| --- | --- |
| `Task.ts` | 125 |
| `tasks.ts` | 39 |
| `costHook.ts` | 22 |
| `query/config.ts` | 46 |
| `query/stopHooks.ts` | 473 |
| `query/tokenBudget.ts` | 93 |
| `coordinator/coordinatorMode.ts` | 369 |
| `tasks/DreamTask/DreamTask.ts` | 157 |
| `tasks/InProcessTeammateTask/InProcessTeammateTask.tsx` | 125 |
| `tasks/InProcessTeammateTask/types.ts` | 121 |
| `tasks/LocalAgentTask/LocalAgentTask.tsx` | 682 |
| `tasks/LocalMainSessionTask.ts` | 479 |
| `tasks/LocalShellTask/guards.ts` | 41 |
| `tasks/LocalShellTask/killShellTasks.ts` | 76 |
| `tasks/LocalShellTask/LocalShellTask.tsx` | 522 |
| `tasks/pillLabel.ts` | 82 |
| `tasks/stopTask.ts` | 100 |
| `tasks/types.ts` | 46 |

소계 **3,598 LOC** byte-identical (CC 7,927 LOC 의 45%). Coordinator/LocalShell/LocalAgent/InProcessTeammate 4 핵심 Task 패밀리가 전부 byte-동등 — CC harness 의 agentic loop 구조가 KOSAX 에서 그대로 살아있다는 강한 시그널.

## MIGRATE-FOR-SWAP (둘 다 있고 다름) — 6개

각 발산은 **2-swap 종속**으로 정당화됨. 회귀 후보 없음.

### 1. `query.ts` (CC 1729 / KOSAX 1675 LOC, diff 222 lines)
**차이 분류**:
- Anthropic SDK import → `./ipc/llmTypes.js` (`KosaxToolUseBlockParam` 등) — **swap-1**
- `services/api/withRetry`/`errors`/`toolUseSummary` 인라인 stub 처리 — Spec 2293 cleanup
- `services/analytics/index` (`logEvent`, `tengu_*` 이벤트 4종) 제거 — Anthropic 1P 텔레메트리 (swap 종속 정당)
- **Epic #2152 R5**: `appendSystemContext` (cwd / gitStatus / claudeMd) 우회 + `prependUserContext` 우회. 시민 도메인 하네스에서는 개발자 컨텍스트 누설 금지. AgentTool 경로는 보존됨.
- KOSAX 추가 함수: `getToolResultIDsFromUserMessage` + `getResolvedToolUseIDs` + tool_use/tool_result orphan resolution 로직 (2077/1978 IPC 보강).

**판정**: MIGRATE-FOR-SWAP. swap-1 + Anthropic 1P 제거 + Epic #2152 명시적 발산 + IPC 보강. byte-회귀 불가 (LLM swap 본질).

**권고 P2**: `prependUserContext` / `appendSystemContext` 우회 주석은 Epic #2152 머지된 `R5` 결정으로 명시되어있으므로 그대로 유지. AgentTool 경로 (다른 슬라이스) 와의 일관성은 S2 (tools) 가 검증.

### 2. `QueryEngine.ts` (CC 1295 / KOSAX 1309 LOC, diff 30 lines)
**차이 분류**: 100% Anthropic SDK + analytics 제거.
- `@anthropic-ai/sdk/resources/messages.mjs` → `./ipc/llmTypes.js` — **swap-1**
- `src/services/api/claude.js` (`accumulateUsage`, `updateUsage`) → 인라인 generic 구현 (Spec 2293 P1)
- `src/services/api/logging.js` (`EMPTY_USAGE`, `NonNullableUsage`) → `src/services/api/emptyUsage.js` + sdkUtilityTypes (KOSAX-side 분리, claude.js 전체 제거 정합)
- `services/api/errors.js` (`categorizeRetryableAPIError`) → 인라인 stub (Spec 2293 cleanup)

**판정**: MIGRATE-FOR-SWAP. KOSAX 가 +14 LOC (인라인 stub) 로 늘었지만 의미 보존. 발산 기준 만족.

**권고 P2**: `accumulateUsage`/`updateUsage` 인라인은 generic Record-based 구현 — CC 원본의 정확한 type-safe 구현보다 약함. 같은 함수의 single source of truth 를 `src/sdk-compat.ts` 등으로 묶는 리팩터 후보 (다른 cost-tracker / query 등에 동일 패턴 반복).

### 3. `cost-tracker.ts` (CC 323 / KOSAX 304 LOC, diff 31 lines)
**차이 분류**:
- `BetaUsage as Usage` import → `src/sdk-compat.js` — **swap-1**
- `services/analytics/index` (logEvent, AnalyticsMetadata*) 제거 — Anthropic 1P
- `utils/modelCost.js` (`calculateUSDCost`) 제거 → advisor sub-call 비용 0 처리 — **swap-1** (Anthropic 모델 가격표 제거 정당)

**판정**: MIGRATE-FOR-SWAP. 모든 변경이 swap 종속. CC 원본에서 advisor sub-call 비용을 정확히 트래킹하던 로직은 K-EXAONE 가격 모델로 재구현 가능하나 현재 0-cost stub 으로 명시.

**권고 P1**: K-EXAONE / FriendliAI 가격을 `src/utils/modelCost.ts` 에 KOSAX-original 로 복구하면 advisor sub-call 비용 정확도 회복 가능. KOSAX-only deferred backlog.

### 4. `query/deps.ts` (CC 40 / KOSAX 694 LOC, diff 663 lines)
**차이 분류**: CC 의 deps.ts 는 단순 `queryModelWithStreaming` re-export (40 LOC). KOSAX 는 `KOSAX-1633 P3 wire-up` 으로 **swap-1 핵심 본체** 가 들어가있음:
- Anthropic Claude API → KOSAX Spec 1978 ADR-0001 backend (`kosax.ipc.stdio._handle_chat_request`) IPC bridge
- `getOrCreateKosaxBridge` / `ChatRequestFrame` / `IPCFrame` (Spec 032 envelope)
- `getToolDefinitionsForFrame` (Spec 2077 K-EXAONE 도구 직렬화)
- `buildToolUseResultFromEnvelope`, `stripUiOnlyToolResultFields` (Spec 1979 outbound_traces UI-only 분리)
- Spec 2521 typewriter 회귀 주석 (Layer 5 캡처 근거 박제)

**판정**: MIGRATE-FOR-SWAP. swap-1 (LLM swap) 의 single most important wiring 파일. 모든 추가 LOC 가 명시적 spec citation. byte-회귀 불가.

**권고 P0**: 이 파일은 KOSAX engine core 의 swap-1 contract 그 자체. 내부 helper (3개) 는 `src/ipc/` 로 분리해도 되지만 깨지면 chat 가 안 됨 — 단위 테스트 매트릭스 보강 (orphan helpers 분리는 이미 `query/orphanHelpers.ts` 로 처리됨).

### 5. `assistant/sessionHistory.ts` (CC 87 / KOSAX 92 LOC, diff 13 lines)
**차이 분류**:
- `constants/oauth.js` (`getOauthConfig`) 제거 → 빈 stub — **swap-1** (Anthropic OAuth 종속 표면)
- `utils/teleport/api.js` (`getOAuthHeaders`, `prepareApiRequest`) 제거 → throw stub — **swap-1** (Anthropic 1P teleport)

**판정**: MIGRATE-FOR-SWAP. Spec 1633 P1+P2 명시적 정당화. KOSAX 는 FriendliAI 사용으로 Anthropic OAuth 불필요.

**권고 P2**: stub 함수가 호출되면 throw — sessionHistory 의 remote-session 코드 경로가 dead-code 인지 확인 후 (S6 Hooks/Services 슬라이스와 교차) 완전 제거 가능.

### 6. `tasks/RemoteAgentTask/RemoteAgentTask.tsx` (CC 855 / KOSAX 862 LOC, diff 17 lines)
**차이 분류**:
- `ToolUseBlock` import → `src/sdk-compat.js` — **swap-1**
- `utils/teleport/api.js` (`fetchSession`) → throw stub
- `utils/teleport.js` (`pollRemoteSessionEvents`, `archiveRemoteSession`) → throw/no-op stub

**판정**: MIGRATE-FOR-SWAP. 모든 발산이 Spec 1633 P1 teleport 제거에 따른 stub. 컴포넌트 본체 (855 LOC) 는 거의 byte-동등.

**권고 P2**: RemoteAgentTask UI 자체가 KOSAX 에서 dead-path 인지 결정 필요 → 살리려면 KOSAX-original remote-agent 백엔드 구현, 죽이려면 컴포넌트 + tasks/types 의 union arm 동시 제거.

## DROP-CANDIDATE (KOSAX-only) — 정당성 감사

### TS 측 KOSAX-only 파일 (7개)

모두 spec-justified. **제거 대상 없음** — 모두 swap-1 또는 P0 reconstructed 재건축 산출물.

| 경로 | LOC | 정당화 |
| --- | --- | --- |
| `tui/src/query/orphanHelpers.ts` | 37 | **Epic #2077 T016**. FR-009 tool_call/tool_result pairing 단위 테스트가 `bun:bundle` 의존성 회피하기 위해 deps.ts 에서 추출. swap-2 (도구 시스템) 종속. |
| `tui/src/query/toolSerialization.ts` | 110 | **Epic #2077 T005**. CC `_cc_reference/api.ts:toolToAPISchema` mirror. Zod → JSON Schema (Draft 2020-12) 변환. swap-2 (도구 시스템 — K-EXAONE native FC). FR-003 published-name 단일소스. |
| `tui/src/query/transitions.ts` | 137 | **P0 reconstructed Pass 3 v2 · agent-verified**. query.ts 의 state-machine continuation reason union 7-variant 타입을 분리. CC 원본은 query.ts 내 inline 이지만 KOSAX 는 분리. swap 종속 X — 순수 타입 추출 리팩터. |
| `tui/src/assistant/AssistantSessionChooser.tsx` | 24 | **KOSAX-1633 P2 / 1978 T009 stub-noop**. CC 의 Anthropic Console session UI 가 KOSAX 에서는 `tui/src/screens/SessionPicker.tsx` 로 대체됨. dynamic import 안전성 위해 null 컴포넌트로 박제. swap-1 종속. |
| `tui/src/assistant/sessionDiscovery.ts` | 149 | **P0 reconstructed Pass 3 · KAIROS assistant session discovery**. CC 의 `feature('KAIROS')` gated 기능 — KOSAX 에서는 항상 functional 로 leave (타입 honesty). 순수 fs 검색. swap 종속 X. |
| `tui/src/tasks/LocalWorkflowTask/LocalWorkflowTask.ts` | 40 | **P0 reconstructed Pass 3 · LocalWorkflowTask state**. `BackgroundTaskState` union 의 한 arm. CC 원본 누락 (소스맵 dead-import 잔재) → 복원. |
| `tui/src/tasks/MonitorMcpTask/MonitorMcpTask.ts` | 41 | **P0 reconstructed Pass 3 · MonitorMcpTask state**. 위와 동일 패턴. `BackgroundTaskState` union arm. |

소계 **538 LOC**. 전부 정당화 충족.

### Python 백엔드 (`src/kosax/{llm,engine}/`) — 19 파일 / 3,991 LOC

이 영역은 **swap-1 (LLM swap) 의 backend-side 본체**. CC 와 비교 가능한 파일이 없는 것이 정당함 — CC 원본의 `services/api/claude.ts` 가 process 내부 Anthropic API 호출이었던 반면, KOSAX 는 Spec 1978 ADR-0001 에 따라 Python backend (FriendliAI 호출 / K-EXAONE thinking / tool_call dispatch) 를 stdio JSONL IPC 로 분리. 이 전체 트리가 swap-1 의 정의 그 자체.

| 디렉토리 | 파일 수 | LOC | 역할 |
| --- | --- | --- | --- |
| `src/kosax/llm/` | 10 | 2,393 | FriendliAI 클라이언트 + K-EXAONE 시스템 프롬프트 어셈블러 + tool_call parser + retry + usage |
| `src/kosax/engine/` | 9 | 1,598 | per-session QueryEngine + query.py (CC `query.ts` 의 backend 측 미러) + preprocessing + events + tokens |

**판정**: 전부 swap-1 정당화. **제거 대상 없음**. 

**권고 P2**: `src/kosax/engine/query.py` (419 LOC) 와 CC `tui/src/query.ts` (1675 LOC) 의 책임 분배가 명확한지 별도 cross-stack contract 문서 (S1 → backend) 정합성 점검 필요. 현재 deps.ts comment 가 backend 책임을 명시하지만 단일 ADR refresh 가 도움이 될 것.

## 위험 신호 / 사용자 결정 필요

1. **인라인 stub 패턴 중복** (P2 리팩터 후보)
   `query.ts` / `QueryEngine.ts` / `cost-tracker.ts` 3곳이 각자 `services/api/{withRetry,errors,logging,toolUseSummary}` 의 작은 부분을 inline stub 으로 재정의함. 같은 stub 이 3 파일에 흩어져있음 — `src/sdk-compat.ts` 또는 `src/services/api/stubs.ts` 단일 모듈로 합치면 회귀 위험 감소. **단, 머지 전 swap-1 wiring 을 흩지 말 것 — Spec 2293 cleanup 의 후속 P3 작업으로 별도 epic 권장.**

2. **`RemoteAgentTask` 의 dead-path 결정 필요** (사용자 결정)
   CC 의 RemoteAgentTask 는 Anthropic 의 remote agent / teleport 인프라 의존. KOSAX 에서는 stub throw 로 무력화됨. 컴포넌트 자체 (862 LOC) 가 살아있는데 호출 경로가 죽어있음. 결정 옵션:
   - (A) 완전 제거 (`tasks/types.ts` 의 union arm 동시 제거 — byte-identical 깨짐 → 다른 방식)
   - (B) KOSAX-original remote-agent 구현 (Spec 027 mailbox 위에 build 가능)
   - (C) 현 stub 상태 유지 (dead-path 로 박제)
   
   현 권고: (C) 유지 — byte-identical 보존 우선, 향후 사용자 시나리오 결정 시 (B).

3. **`AssistantSessionChooser.tsx` 의 stub-noop 처리** (사용자 확인)
   24 LOC noop 컴포넌트가 `screens/SessionPicker.tsx` (KOSAX-original) 와 공존. 이름 충돌 / dynamic import 위험은 없으나 의도가 명확한지 확인 필요. 권고: 현 stub 유지 + comment 의 KOSAX-original 경로 cross-link 강화.

4. **`query/transitions.ts` 가 P0 reconstructed 표시** 
   137 LOC 의 타입-only 모듈이 "agent-verified" 라벨로 박제됨. CC 원본 `query.ts` 의 inline literal 과 enumeration 일치하는지 한 번 더 spot check 권장 (P2). 회귀 시 query state machine 의 reason discriminator 가 silently drift 가능.

5. **위험 없음 — 누락 회귀 없음**
   CC 24 파일 중 PORT (KOSAX 누락) 0건. byte-identical 18 / swap-justified 발산 6 / 모두 카테고리 정합. 이 슬라이스는 CORE THESIS ("CC + 2 swaps") 를 가장 잘 지키는 영역.
