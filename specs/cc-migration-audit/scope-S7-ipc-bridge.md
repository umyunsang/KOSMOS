# Scope S7 — IPC + Bridge + Server + Remote + Native (CC → UMMAYA Migration Audit)

**작성일**: 2026-05-03
**감사자**: Lead Opus (S7 슬라이스)
**스코프**: CC `bridge/`(31) + `server/`(3) + `remote/`(4) + `upstreamproxy/`(2) + `native-ts/`(4) = **44 CC 파일**, UMMAYA 측 `tui/src/bridge/`(31) + `tui/src/server/`(3) + `tui/src/upstreamproxy/`(2) + `tui/src/native-ts/`(4) + `tui/src/mcpb-compat.ts`(1) + `tui/src/ipc/`(15+2) + `src/ummaya/ipc/`(13+5) = **74 UMMAYA 파일**.

---

## 1. CORE THESIS 적용

UMMAYA = CC-original harness + 2 swaps. **S7 슬라이스의 default 는 PRESERVE-IDENTICAL**. swap 1(LLM=K-EXAONE)/swap 2(Tool=GovAPITool) 의 어느 종속도 아닌 표면은 byte-identical 이어야 한다. Bridge UI / messaging / OAuth 시그니처 / WebSocket 패턴 / yoga-layout / file-index — 전부 CC 그대로.

**S7 만의 특수 사정**: UMMAYA 가 `Python 백엔드 + TS TUI` 분리 구조를 채택하면서 도입된 `tui/src/ipc/` (TS) ↔ `src/ummaya/ipc/` (Python) stdio JSONL 다리는 swap-implementation 종속물. CC 에는 대응이 없다(CC 는 in-process). 이 문서는 이를 별도 5번째 분류 **PRESERVE-AS-SWAP-IMPL** 로 다룬다(4-bucket 의 DROP-CANDIDATE 가 아닌, swap 의 transport 골격).

---

## 2. CC 파일 목록 (44 / 분류별)

### 2.1 PRESERVE-IDENTICAL (32 파일 / byte-identical 확인)

#### Bridge (24 파일 · diff=0)

| CC 파일 | UMMAYA 위치 | bytes | diff |
|---|---|---|---|
| `bridge/bridgeApi.ts` | `tui/src/bridge/bridgeApi.ts` | 18066 | 0 |
| `bridge/bridgeDebug.ts` | `tui/src/bridge/bridgeDebug.ts` | 4926 | 0 |
| `bridge/bridgeEnabled.ts` | `tui/src/bridge/bridgeEnabled.ts` | 8442 | 0 |
| `bridge/bridgeMessaging.ts` | `tui/src/bridge/bridgeMessaging.ts` | 15703 | 0 |
| `bridge/bridgePermissionCallbacks.ts` | `tui/src/bridge/bridgePermissionCallbacks.ts` | 1411 | 0 |
| `bridge/bridgePointer.ts` | `tui/src/bridge/bridgePointer.ts` | 7611 | 0 |
| `bridge/bridgeStatusUtil.ts` | `tui/src/bridge/bridgeStatusUtil.ts` | 5143 | 0 |
| `bridge/bridgeUI.ts` | `tui/src/bridge/bridgeUI.ts` | 16780 | 0 |
| `bridge/capacityWake.ts` | `tui/src/bridge/capacityWake.ts` | 1841 | 0 |
| `bridge/codeSessionApi.ts` | `tui/src/bridge/codeSessionApi.ts` | 4840 | 0 |
| `bridge/debugUtils.ts` | `tui/src/bridge/debugUtils.ts` | 4240 | 0 |
| `bridge/envLessBridgeConfig.ts` | `tui/src/bridge/envLessBridgeConfig.ts` | 7250 | 0 |
| `bridge/flushGate.ts` | `tui/src/bridge/flushGate.ts` | 1981 | 0 |
| `bridge/jwtUtils.ts` | `tui/src/bridge/jwtUtils.ts` | 9444 | 0 |
| `bridge/pollConfig.ts` | `tui/src/bridge/pollConfig.ts` | 4562 | 0 |
| `bridge/pollConfigDefaults.ts` | `tui/src/bridge/pollConfigDefaults.ts` | 4018 | 0 |
| `bridge/remoteBridgeCore.ts` | `tui/src/bridge/remoteBridgeCore.ts` | 39434 | 0 |
| `bridge/replBridge.ts` | `tui/src/bridge/replBridge.ts` | 100537 | 0 |
| `bridge/replBridgeHandle.ts` | `tui/src/bridge/replBridgeHandle.ts` | 1473 | 0 |
| `bridge/replBridgeTransport.ts` | `tui/src/bridge/replBridgeTransport.ts` | 15523 | 0 |
| `bridge/sessionIdCompat.ts` | `tui/src/bridge/sessionIdCompat.ts` | 2536 | 0 |
| `bridge/sessionRunner.ts` | `tui/src/bridge/sessionRunner.ts` | 18020 | 0 |
| `bridge/types.ts` | `tui/src/bridge/types.ts` | 10161 | 0 |
| `bridge/workSecret.ts` | `tui/src/bridge/workSecret.ts` | 4672 | 0 |

**검증**: 24/24 CC 와 정확히 byte-identical. `replBridge.ts` (100KB), `remoteBridgeCore.ts` (39KB), `bridgeApi.ts` (18KB), `bridgeUI.ts` (16KB), `bridgeMessaging.ts` (15KB), `replBridgeTransport.ts` (15KB) 등 핵심 대형 파일 전부 그대로 — UMMAYA 가 CC bridge UX/메시징/세션 골격을 byte-identical 보존했음.

#### Server (2/3 byte-identical)

| CC 파일 | UMMAYA 위치 | bytes | diff |
|---|---|---|---|
| `server/createDirectConnectSession.ts` | `tui/src/server/createDirectConnectSession.ts` | 2193 | 0 |
| `server/types.ts` | `tui/src/server/types.ts` | 1466 | 0 |

#### Upstreamproxy (2/2 byte-identical)

| CC 파일 | UMMAYA 위치 | bytes | diff |
|---|---|---|---|
| `upstreamproxy/relay.ts` | `tui/src/upstreamproxy/relay.ts` | 14937 | 0 |
| `upstreamproxy/upstreamproxy.ts` | `tui/src/upstreamproxy/upstreamproxy.ts` | 9812 | 0 |

#### Native-ts (4/4 byte-identical)

| CC 파일 | UMMAYA 위치 | bytes | diff |
|---|---|---|---|
| `native-ts/color-diff/index.ts` | `tui/src/native-ts/color-diff/index.ts` | 30042 | 0 |
| `native-ts/file-index/index.ts` | `tui/src/native-ts/file-index/index.ts` | 12006 | 0 |
| `native-ts/yoga-layout/index.ts` | `tui/src/native-ts/yoga-layout/index.ts` | 83377 | 0 |
| `native-ts/yoga-layout/enums.ts` | `tui/src/native-ts/yoga-layout/enums.ts` | 2823 | 0 |

**검증**: native-ts 는 CC 가 vendor 한 yoga-layout(83KB) / color-diff(30KB) / file-index(12KB) WASM·layout 엔진. UMMAYA 가 byte-identical 유지 — 어떤 swap 종속도 아니므로 정답.

---

### 2.2 MIGRATE-FOR-SWAP (8 파일 · 발산 + swap 정당화)

#### Bridge (7 파일)

| CC 파일 | UMMAYA 파일 | diff lines | 발산 사유 | swap 정당? |
|---|---|---|---|---|
| `bridge/bridgeMain.ts` | `tui/src/bridge/bridgeMain.ts` | 9 | `services/analytics/datadog`·`firstPartyEventLogger` import → 통합 `analytics/index.ts` 로 변경 (Spec 1633 P1+P2) | ✅ swap-종속 (1P 텔레메트리 제거) |
| `bridge/bridgeConfig.ts` | `tui/src/bridge/bridgeConfig.ts` | 5 | `constants/oauth` 삭제 → 빈 stub `getOauthConfig` (Spec 1633) | ✅ swap-종속 (Anthropic OAuth 제거) |
| `bridge/createSession.ts` | `tui/src/bridge/createSession.ts` | 24 | `getOauthConfig` + `getOAuthHeaders` lazy import 4곳 → 빈 stub (Spec 1633 P1+P2 / 1978 T011) | ✅ swap-종속 |
| `bridge/initReplBridge.ts` | `tui/src/bridge/initReplBridge.ts` | 49 | `policyLimits/`·`utils/sessionTitle`(queryHaiku 기반 제목 생성기) 제거 → no-op (Spec 1633 / Epic 2293) | ✅ swap-종속 (Anthropic Haiku 호출) |
| `bridge/inboundAttachments.ts` | `tui/src/bridge/inboundAttachments.ts` | 4 | `@anthropic-ai/sdk/resources/messages.mjs` ContentBlockParam → `src/sdk-compat.js` 로 import 경로 변경 | ✅ swap-종속 (Anthropic SDK 의존 격리) |
| `bridge/inboundMessages.ts` | `tui/src/bridge/inboundMessages.ts` | 4 | 위와 동일 (`messages.mjs` → `sdk-compat.js`) | ✅ swap-종속 |
| `bridge/trustedDevice.ts` | `tui/src/bridge/trustedDevice.ts` | 12 | `constants/oauth` + `utils/secureStorage`(OS keychain) 삭제 → 빈 stub. UMMAYA 는 `.env`-backed secrets 사용 (Spec 1633) | ✅ swap-종속 |

#### Server (1 파일)

| CC 파일 | UMMAYA 파일 | diff lines | 발산 사유 | swap 정당? |
|---|---|---|---|---|
| `server/directConnectManager.ts` | `tui/src/server/directConnectManager.ts` | 10 | `remote/RemoteSessionManager` + `utils/teleport/api` import → `unknown` / 인라인 type stub (Spec 1633 P1+P2 / 1978 T011) | ⚠️ 부분 정당 — `remote/` 4 파일은 미포팅 (§ 2.3 참조). type stub 으로 컴파일 통과시켰지만 dead-import 경로가 남아있음. 이 파일이 호출되는 코드 경로가 UMMAYA 에서 실행되는지 별도 검증 필요. |

---

### 2.3 PORT (4 파일 · CC 에 있고 UMMAYA 에 없음 · 누락)

#### Remote (4/4 미포팅)

| CC 파일 | bytes | UMMAYA 상태 | 영향 |
|---|---|---|---|
| `remote/remotePermissionBridge.ts` | 2378 | ❌ 미포팅 | claude.ai backed remote permission flow — claude.ai 결제/sync 종속이므로 swap 으로 정당. **DROP 으로 재분류 가능.** |
| `remote/RemoteSessionManager.ts` | 9320 | ❌ 미포팅 | claude.ai 호스팅 session 관리자 (RemoteMessageContent / RemotePermissionResponse 타입 export) — swap 정당. |
| `remote/sdkMessageAdapter.ts` | 9060 | ❌ 미포팅 | Anthropic SDK Message ↔ remote envelope 어댑터 — swap 정당. |
| `remote/SessionsWebSocket.ts` | 12505 | ❌ 미포팅 | claude.ai sessions WebSocket — swap 정당. |

**판정 재분류**: remote/ 4 파일은 CC 의 claude.ai-결제·sync 백엔드와의 WebSocket 다리. UMMAYA 의 swap-종속 표면 정의("claude.ai 결제/sync/1P 텔레메트리")에 정확히 해당 → **DROP-FOR-SWAP** 로 정당화 가능. 단, `tui/src/server/directConnectManager.ts` 가 여전히 type-import 만으로 stub-참조 중이므로 다음 두 가지 중 선택:

1. **(권고)** directConnectManager.ts 도 함께 정리 — UMMAYA 에 cloud session 직접연결 시나리오가 없으므로.
2. (현상유지) type stub 만 남기고 dead-runtime path 인지 cmd 검증.

UMMAYA 측에 `tui/src/utils/background/remote/` 가 따로 존재(2 파일) — 이는 CC 의 utils/background/remote(원본 검증 필요)를 별도 포팅한 것으로 보이며 S7 스코프 외(S9 utils 슬라이스 검증 대상).

---

### 2.4 PRESERVE-AS-SWAP-IMPL (UMMAYA-only IPC 인프라 · 4-bucket 외 5번째 분류)

CC 는 in-process 단일 Node 프로세스. UMMAYA 는 Python(LLM/Tool 백엔드) + TS(TUI) 분리 → stdio JSONL IPC 도입. 이 IPC 레이어는 swap 1+2 의 transport-종속물이므로 DROP-CANDIDATE 가 아니라 PRESERVE-AS-SWAP-IMPL.

#### TUI 측 (`tui/src/ipc/`, 17 파일)

| 파일 | 역할 | 분류 |
|---|---|---|
| `frames.generated.ts` (47 KB) | 22-arm IPC discriminated union — Pydantic schema 에서 generation | PRESERVE-AS-SWAP-IMPL |
| `codec.ts` (17 KB) | JSONL encode/decode + checksum | PRESERVE-AS-SWAP-IMPL |
| `bridge.ts` (22 KB) | TS-side stdio bridge | PRESERVE-AS-SWAP-IMPL |
| `bridgeSingleton.ts` | per-process singleton | PRESERVE-AS-SWAP-IMPL |
| `llmClient.ts` (33 KB) | TUI-side LLM 호출 클라이언트 | swap 1 종속 (K-EXAONE FriendliAI) |
| `llmTypes.ts` | swap 1 LLM 타입 | swap 1 종속 |
| `mcp.ts` (18 KB) | MCP client 어댑터 | PRESERVE-AS-SWAP-IMPL (CC mcp 와 별도 — IPC 위) |
| `envelope.ts` | base envelope | PRESERVE-AS-SWAP-IMPL |
| `tx-registry.ts` | correlation_id 추적 | PRESERVE-AS-SWAP-IMPL |
| `crash-detector.ts` | backend crash 감지 | PRESERVE-AS-SWAP-IMPL |
| `backpressure-hud.tsx` | backpressure UI HUD | PRESERVE-AS-SWAP-IMPL |
| `pendingCallSingleton.ts` | pending 호출 추적 | PRESERVE-AS-SWAP-IMPL |
| `pipa.generated.ts` | PIPA 동의 타입 generation | swap 2 종속 (한국 행정 도구) |
| `schema/frame.schema.json` | JSON Schema canonical | PRESERVE-AS-SWAP-IMPL |
| `demo/hud_probe.ts`, `demo/resume_probe.ts` | 데모 프로브 | PRESERVE-AS-SWAP-IMPL (테스트용) |

#### Python 측 (`src/ummaya/ipc/`, 18 파일)

| 파일 | 역할 |
|---|---|
| `frame_schema.py` (47 KB) | 22-arm Pydantic discriminated union (TS frames.generated.ts 의 source) |
| `stdio.py` (101 KB) | stdio JSONL transport 핵심 — backend side |
| `envelope.py` | base envelope |
| `backpressure.py` (21 KB) | flow control |
| `tx_cache.py` (22 KB) | transaction cache |
| `ring_buffer.py` (8 KB) | session ring buffer (Spec 032) |
| `resume_manager.py` (14 KB) | resume_request/response 핸들러 (Spec 032) |
| `heartbeat.py` (10 KB) | heartbeat 프레임 |
| `mcp_server.py` (10 KB) | stdio MCP server stub |
| `adapter_manifest_emitter.py` (15 KB) | swap 2 adapter manifest 동기화 |
| `plugin_op_dispatcher.py` (20 KB) | swap 2 plugin op (Spec 1636) |
| `citizen_request.py` | swap 2 citizen request |
| `otel_constants.py` | OTEL 상수 |
| `demo/*` (6 파일: full_turn_probe, mock_backend, register_irreversible_fixture, session_backend, upstream_429_probe, __init__) | 데모/테스트 |

전부 UMMAYA-only — CC 대응 없음. swap-implementation 인프라.

---

### 2.5 DROP-CANDIDATE (UMMAYA 에 있지만 CC 에 없음)

| UMMAYA 파일 | bytes | swap 종속? | 판정 |
|---|---|---|---|
| `tui/src/mcpb-compat.ts` | 26 lines | swap 외 (mcpb=`@anthropic-ai/mcpb` lazy 로더) | ⚠️ 부분 — Epic #2293 FR-010 으로 신설된 lazy-load shim. CC 에는 없지만 mcpb v3 의 ~700KB heap 비용 회피용. swap 1/2 가 아닌 UMMAYA-original 최적화 → **swap 종속 아님**. CC 가 향후 동일 패턴 채택할 가능성, 현재로서는 UMMAYA-original 혁신으로 분류. **유지하되 ADR 등록 필요.** |

---

## 3. IPC frame schema 호환성

### CC IPC arm vs UMMAYA IPC arm 매핑표

CC 는 `ipc/` 디렉토리가 존재하지 않는다 — 단일 Node 프로세스에서 in-process 호출. 따라서 **"호환성"의 기준선은 CC 의 in-process call signature** 가 된다. UMMAYA 는 swap 종속 transport(stdio JSONL) 에서 22-arm discriminated union 을 정의했고, 각 arm 의 정당성은 다음과 같다:

| Frame arm | role | swap 종속? | CC in-process 대응 | 정당화 |
|---|---|---|---|---|
| `user_input` | TUI→backend 입력 | swap (Python 분리) | 직접 호출 | ✅ transport |
| `chat_request` | TUI→backend LLM 요청 | swap 1 (K-EXAONE) | direct fn call to anthropic SDK | ✅ swap 1 |
| `assistant_chunk` | backend→TUI 스트리밍 | swap 1 | SDK stream callback | ✅ swap 1 |
| `tool_call` | LLM→backend tool 호출 | swap 2 | tool dispatcher | ✅ swap 2 |
| `tool_result` | backend→LLM tool 결과 | swap 2 | tool dispatcher | ✅ swap 2 |
| `coordinator_phase` | 멀티에이전트 조정 | swap 2 (Spec 027) | n/a | ✅ swap 2 |
| `worker_status` | 멀티에이전트 워커 | swap 2 (Spec 027) | n/a | ✅ swap 2 |
| `permission_request` | backend→TUI 권한 요청 | swap (UI는 CC, transport만 IPC) | direct callback | ✅ transport |
| `permission_response` | TUI→backend 권한 응답 | swap (transport) | direct callback | ✅ transport |
| `session_event` | session lifecycle | swap (transport) | direct event emitter | ✅ transport |
| `error` | 에러 envelope | swap (transport) | exception throw | ✅ transport |
| `payload_start/delta/end` | large payload 청크 (3 arms) | swap (transport) | n/a (in-process) | ✅ transport — IPC 만의 필요. Spec 032 limit |
| `backpressure` | flow control | swap (transport) | n/a | ✅ transport |
| `resume_request/response/rejected` | crash recovery (3 arms) | swap (transport) | direct retry | ✅ transport — Spec 032 |
| `heartbeat` | liveness | swap (transport) | n/a | ✅ transport |
| `notification_push` | OS notification | swap (UI) | direct OS call | ⚠️ 검증 필요 — CC 가 직접 OS notification 호출하는지 확인 |
| `plugin_op` | plugin lifecycle | swap 2 (Spec 1636) | n/a | ✅ swap 2 |
| `adapter_manifest_sync` | adapter registry sync | swap 2 | n/a | ✅ swap 2 |

**총 22 arms 모두 정당**: 11 개는 transport-종속(in-process→stdio 분리에 따른 필연), 7 개는 swap 1/2 종속, 1 개(notification_push) 만 검증 필요.

**주의**: TS `frames.generated.ts` 가 Python `frame_schema.py` 에서 generation 되는 1방향 sync. 두 파일의 SHA-256 sync gate 가 CI 에 있는지 별도 확인 필요(generated 파일 drift 방지).

---

## 4. 4-bucket 집계

| 분류 | 파일 수 | 비고 |
|---|---|---|
| **PORT** (CC 에 있고 UMMAYA 에 없음) | 4 | 전부 `remote/` (claude.ai 백엔드) — DROP-FOR-SWAP 으로 재분류 가능 |
| **PRESERVE-IDENTICAL** | 32 | bridge 24 + server 2 + upstreamproxy 2 + native-ts 4 |
| **MIGRATE-FOR-SWAP** | 8 | bridge 7 (analytics/oauth/Haiku/secureStorage 종속 stub) + server 1 (remote import stub) |
| **DROP-CANDIDATE** | 1 | `mcpb-compat.ts` (Epic 2293 FR-010 lazy shim, UMMAYA-original 혁신) |
| **PRESERVE-AS-SWAP-IMPL** | 35 | TUI ipc 17 + Python ipc 18 (stdio JSONL transport — CC 단일프로세스 대비 transport 종속) |

---

## 5. 핵심 발견

### Finding 1: Bridge 골격 24/31 byte-identical — 우수
`replBridge.ts`(100KB), `remoteBridgeCore.ts`(39KB), `bridgeApi.ts`(18KB), `bridgeUI.ts`(16KB), `bridgeMessaging.ts`(15KB) 등 핵심 대형 파일이 전부 byte-identical 보존. UMMAYA 가 CC bridge UX/메시징/세션 골격을 선언적으로 유지 — CORE THESIS 충실.

### Finding 2: `remote/` 4 파일 미포팅 — DROP-FOR-SWAP 재분류 정당
CC 의 `remote/` (claude.ai backed remote session WebSocket, 33KB) 가 UMMAYA 에 미포팅. 이는 UMMAYA swap 종속 표면 정의("claude.ai 결제/sync") 에 정확히 해당 → DROP 으로 재분류 가능. 단 `server/directConnectManager.ts` 의 type stub dead-import 가 남아있어 깔끔한 정리 필요(권고).

### Finding 3: IPC 22-arm schema — swap 종속물로 정당, 단 1 arm 검증 필요
UMMAYA 가 CC in-process 모델을 stdio JSONL 로 분리하면서 도입한 22-arm discriminated union 은 11(transport) + 7(swap 1/2) + 3(payload chunking) + 1(검증필요) 로 분해됨. **`notification_push` arm 만 CC 가 직접 OS notification 호출하는지 vs IPC 우회 필요한지 별도 검증 필요**.

### Finding 4: TS `frames.generated.ts` ↔ Python `frame_schema.py` drift gate 검증 필요
TS 47KB generated 파일이 Python 47KB Pydantic schema 에서 1방향 sync. CI 에 SHA-256 gate 또는 codegen 재실행 + diff 검사가 있는지 별도 확인 필요. 없으면 schema drift 회귀 위험.

### Finding 5: `mcpb-compat.ts` — UMMAYA-original 혁신, ADR 등록 권고
Epic #2293 FR-010 의 mcpb v3 lazy-load shim 은 CC 대응 없음. swap 1/2 가 아닌 성능 최적화(700KB heap 회피) → UMMAYA-original 혁신으로 분류. 유지 정당, 단 ADR 등록해 향후 CC 재포팅 시 결정 근거 보존 필요.

---

## 6. 사용자 결정 필요 사항

1. **`remote/` 4 파일 처리**: PORT (CC 와 동기화)? 또는 DROP-FOR-SWAP 로 정식 분류 + `server/directConnectManager.ts` 의 dead type-import 도 함께 정리? **권고: DROP + cleanup**.
2. **`notification_push` IPC arm 검증**: CC 가 OS notification 을 어떻게 호출하는지 확인 후, IPC arm 이 transport-필연인지 swap-UI 종속인지 확정. (S7 스코프 외 모듈 검토 필요할 수 있음)
3. **TS↔Python schema drift gate**: `frames.generated.ts` 와 `frame_schema.py` 의 SHA-256/codegen gate 가 CI 에 있는지 확인. 없으면 추가 권고.
4. **`mcpb-compat.ts` ADR 등록**: UMMAYA-original 혁신 결정 근거 박제 필요(`docs/adr/`).
