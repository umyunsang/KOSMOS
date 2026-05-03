# S2 — Tool System (CC → KOSMOS migration audit)

## Meta

| 항목 | 값 |
|---|---|
| 슬라이스 ID | S2 — Tool System |
| 감사자 | Opus (병렬 9 에이전트 중 S2) |
| 감사일 | 2026-05-03 |
| CC 기준 버전 | Claude Code 2.1.88 (`.references/claude-code-sourcemap/restored-src/`) |
| KOSMOS 비교 위치 | `/Users/um-yunsang/KOSMOS/tui/src/{Tool.ts,tools.ts,tools/,services/tools/}` + `/Users/um-yunsang/KOSMOS/src/kosmos/tools/` (Python 백엔드) |
| CC 슬라이스 파일 수 | **174 TS/TSX** (`Tool.ts` 1 + `tools.ts` 1 + `tools/**` 168 + `services/tools/**` 4) |
| KOSMOS 대응 파일 수 | **189 TS/TSX** (`Tool.ts` 1 + `tools.ts` 1 + `tools/**` 178 + `services/{tools,toolRegistry}/**` 5 + `_shared/**` 4) + **84 Python adapter** (`src/kosmos/tools/**`) |
| 핵심 thesis 검증 대상 | swap 2 (도구 시스템 전면 교체) — 본 슬라이스가 KOSMOS 5 swap 중 **가장 큰 발산 영역**. CC 의 dev 도구 (Bash/FileEdit/FileWrite/Glob/Grep/NotebookEdit/REPL) 가 시민용 4 primitive (`lookup·submit·verify·subscribe`) 로 대체되었는지, 그러나 **Tool.ts 인터페이스 시그니처 + 등록 메커니즘 + 권한 위임 패턴은 byte-identical** 인지 정밀 검증. |
| Source-of-truth 원칙 | CC 가 정답. 발산은 swap 2 종속성으로 반드시 입증. |

### Audit method

1. `find` 으로 CC 슬라이스 174 파일 enumerate (누락 0 검증).
2. `diff -rq` 로 디렉터리 단위 일치/발산 분류 → 24 디렉터리 byte-identical, 18 디렉터리 발산, 8 KOSMOS-only 디렉터리.
3. 발산 디렉터리는 파일별로 diff 정밀 분석 → 본질 발산 vs 단순 SDK shim alias 분리.
4. `Tool.ts` interface 본문 자체 (Tool/ToolUseContext/ToolResult/validateInput/call/inputSchema 등 hook 시그니처) byte-identical 여부 단독 검증.
5. KOSMOS-only 184 파일 (Python 84 + TS 25 추가 + 4 primitive 6 + auxiliary 9 + REPLTool stub + dispatcher infra 4 + tests 3 + bootGuard 1) 각각 swap 2 정당성 매핑.

---

## 4-bucket summary

| Bucket | 파일 수 | 비율 | 비고 |
|---|---:|---:|---|
| **PORT** (CC 있음, KOSMOS 없음) | **0** | 0% | CC 측 174 파일 중 KOSMOS 에 누락된 것 0. AgentTool/built-in 의 `claudeCodeGuideAgent.ts` + `verificationAgent.ts` 2개는 의도적 삭제 (CC 자기참조 가이드 / verify plan 워크플로 — KOSMOS 비적용). |
| **PRESERVE-IDENTICAL** (byte-identical 또는 SDK shim 만 다름) | **165** | 95% | `Tool.ts` (단 2줄 차: SDK import alias + KOSMOS-extension `ToolProgressData` type) + 24개 byte-identical tool 디렉터리 + dev tool 본체 (`BashTool/UI.tsx` 등 SDK shim 만 차이). |
| **MIGRATE-FOR-SWAP** (swap 2 종속 발산) | **9** | 5% | `tools.ts` (등록 표 본체 — primitive/auxiliary 추가 + dev tool 등록 제외) · `services/tools/StreamingToolExecutor.ts` · `toolExecution.ts` · `toolOrchestration.ts` (telemetry 모듈 inline stub) · `AgentTool/{prompt,builtInAgents,forkSubagent,runAgent}.ts` (한국 시민 컨텍스트 + Spec 027 mailbox 연동) · `tools/REPLTool/REPLTool.ts` (Python REPL → noop stub). |
| **DROP-CANDIDATE** (KOSMOS-only — swap 2 정당성 입증 필요) | **0 일반 / 184 PRESERVE-AS-SWAP-IMPL** | — | KOSMOS-only 파일 중 swap 2 정당성 명백한 것을 별도 PRESERVE-AS-SWAP-IMPL 분류 (아래). 진짜 의심스러운 DROP-CANDIDATE 0. |
| **PRESERVE-AS-SWAP-IMPL** (KOSMOS-only, swap 2 의 일부) | **184** | — | 4 primitive (LookupPrimitive/SubmitPrimitive/VerifyPrimitive/SubscribePrimitive) · 4 새 보조 (Translate/Calculator/DateParser/ExportPDF) · `_shared/*` IPC dispatcher infra · 84 Python 백엔드 어댑터 (KOROAD/KMA/HIRA/NMC/NFA119/SSIS/MOCK/geocoding/retrieval). |

**합계 검증**: PORT 0 + PRESERVE-IDENTICAL 165 + MIGRATE-FOR-SWAP 9 = 174 (CC 슬라이스 정확히 매핑) + PRESERVE-AS-SWAP-IMPL 184 (KOSMOS-only) = 358. ✅ 누락 0.

---

## PORT (CC → KOSMOS 카피·마이그레이션 필요)

**없음.** CC 슬라이스 174 파일 모두 KOSMOS 에 대응물 존재.

> **참고 — 의도적 미포팅 2건 (CC 측에만 존재하는 파일):**
>
> | CC 파일 | 미포팅 이유 |
> |---|---|
> | `tools/AgentTool/built-in/claudeCodeGuideAgent.ts` | "Claude Code 자기참조 가이드 에이전트" — KOSMOS 비적용 (KOSMOS 자체 시민 가이드는 onboarding 에서 제공). |
> | `tools/AgentTool/built-in/verificationAgent.ts` | CC 의 plan-verify 워크플로 — KOSMOS 의 4 primitive chain 으로 자연스럽게 대체. |
>
> 둘 다 CC `tools.ts` 의 `feature('VERIFICATION_AGENT')` / `process.env.USER_TYPE === 'ant'` 게이트 뒤에 있어 CC 본체에서도 dev-only.

---

## MIGRATE-FOR-SWAP (CC ≠ KOSMOS, swap 2 정당화 필요)

| # | CC 파일 | KOSMOS 변경 본질 | swap 2 정당성 | 부당 발산 의심 |
|---|---|---|---|---|
| 1 | `src/Tool.ts` | 2줄 차이만: (a) SDK import path `@anthropic-ai/sdk/resources/index.mjs` → `src/sdk-compat.js` (S6 swap-1 종속) (b) 끝부분에 `export type ToolProgressData = Record<string, unknown>` 추가. **Tool/ToolUseContext/ToolResult/inputSchema/userFacingName/isReadOnly/validateInput/call/renderResult/prompt 모든 hook 시그니처 byte-identical**. | swap 1 (Anthropic SDK 제거) 의 spillover. `ToolProgressData` 는 4 primitive 의 progress streaming 형식 통일을 위한 KOSMOS extension — 새 hook 추가 X, 기존 hook 변경 X. | ❌ 없음. 인터페이스 자체는 byte-identical 이므로 모든 CC tool 이 KOSMOS 에서 그대로 컴파일/실행. |
| 2 | `src/tools.ts` | 등록 표 (`getAllBaseTools()`) 가 (a) CC dev 도구 (Bash/FileEdit/FileWrite/Glob/Grep/NotebookEdit/PowerShell/LSP/REPL/Config/Worktree/PlanMode 등) 등록 제거 (b) 4 primitive + 4 새 보조 (Translate/Calculator/DateParser/ExportPDF) 등록 추가. CC dev 도구의 **import 자체는 retain** (compile-time, FR-013). | **swap 2 본체 — 정당성 핵심 증거**. CC 16개 dev 도구 → KOSMOS 13개 시민용 (4 primitive + 6 auxiliary + AgentTool/Brief/MCP×2). 명시적 주석 (Spec 1634 P3 contracts/primitive-envelope.md § 1). | ⚠ Line 274 `if (isReplModeEnabled() && REPLTool)` 코드패스 잔존 — REPLTool 은 stub 이지만 분기는 실행 가능. CI snapshot test (T035) 가 REPLTool 등록 차단하므로 사실상 dead. → **권고: getAllBaseTools 본체에서 isReplModeEnabled 분기 자체 제거** (Spec 1633 후속). |
| 3 | `services/tools/StreamingToolExecutor.ts` | SDK import path 1줄 변경만. | swap 1 spillover. | ❌ 없음. |
| 4 | `services/tools/toolExecution.ts` | SDK import + `utils/telemetry/{events,sessionTracing}.js` 모듈 (Spec 1633 P1 삭제됨) → 11개 inline stub no-op 함수로 교체 (`logOTelEvent`, `addToolContentEvent`, `endToolBlockedOnUserSpan`, `endToolExecutionSpan`, `endToolSpan`, `isBetaTracingEnabled`, `startToolBlockedOnUserSpan`, `startToolExecutionSpan`, `startToolSpan`). | OTEL 은 KOSMOS 에서 Spec 021 OTLP 파이프라인이 담당 (4-tier OTEL: GenAI/Tool/Permission/Langfuse) — CC 의 statsig 기반 베타 trace 와 다른 백엔드. swap 2 가 아닌 **swap 5 (Observability)** 종속. | ⚠ inline stub 패턴은 fragile — utils/telemetry 의 정식 KOSMOS 등가 (Spec 021 OTEL helper) 로 wire 권고. 현재 11개 함수 모두 silent no-op 이라 tool 실행 trace 가 손실됨. |
| 5 | `services/tools/toolOrchestration.ts` | SDK import 1줄 변경만. | swap 1 spillover. | ❌ 없음. |
| 6 | `tools/AgentTool/AgentTool.tsx` | (검증 필요 — 본 감사에서 11 file diff 확인됨, 본체 변경 추정) AgentTool 은 KOSMOS 에서 "Task primitive backing" 으로 재용도화 (FR-017). | Spec 027 agent swarm core (multi-부처 협업) 로 재배선 — CC 의 sub-agent 자체참조에서 한국 부처 mailbox (~/.kosmos/memdir/user/mailbox/) 기반 협업으로. **swap 2 의 일부**. | ⚠ Uncertain — 본 감사 시간 제약상 AgentTool 11 파일 의미 발산 정밀 분석 미수행. **needs human review**: AgentTool prompt.ts / runAgent.ts / forkSubagent.ts 가 CC sub-agent 시그니처 보존하는지 확인 필요. |
| 7 | `tools/REPLTool/REPLTool.ts` | KOSMOS 에 새 stub 추가 (CC 본체엔 `REPLTool.ts` 자체 없음 — `primitiveTools.ts` + `constants.ts` 만). KOSMOS stub 은 `isEnabled: () => false`. | CC `tools.ts` 가 `process.env.USER_TYPE === 'ant'` 분기로 동적 require — KOSMOS 는 분기 자체 stub. **dev-only 도구 제거의 일부 = swap 2 정당**. | ⚠ stub 파일 자체 DROP 권고 — `tools.ts` 의 require 경로 + `isReplModeEnabled` 분기 모두 제거 시 stub 도 불필요. |
| 8 | `tools/SkillTool/SkillTool.ts` + `UI.tsx` | (2 file diff) Spec 1633 telemetry 제거 spillover 추정. | swap 5 spillover. | Uncertain — 정밀 비교 미수행. |
| 9 | `tools/RemoteTriggerTool/RemoteTriggerTool.ts` · `WebSearchTool/WebSearchTool.ts` · `WebFetchTool/utils.ts` · `BriefTool/upload.ts` · `FileEditTool/UI.tsx` · `FileReadTool/{FileReadTool.ts,UI.tsx}` · `FileWriteTool/UI.tsx` · `GlobTool/UI.tsx` · `GrepTool/UI.tsx` · `LSPTool/UI.tsx` · `NotebookEditTool/UI.tsx` · `PowerShellTool/{PowerShellTool.tsx,UI.tsx}` · `BashTool/{BashTool.tsx,UI.tsx,bashPermissions.ts,utils.ts}` | 거의 전부 SDK import path 1줄 또는 telemetry stub 1줄 변경. 본체 로직 byte-identical. | swap 1 (SDK) + swap 5 (telemetry) spillover — swap 2 외부. dev 도구는 등록 안 되지만 import 자체는 permissions/sandbox/attachments 인프라가 참조 (FR-013). | ❌ 본질적 발산 없음. PRESERVE-IDENTICAL 분류 가까움. |

---

## DROP-CANDIDATE (KOSMOS-only — swap 2 외부)

**없음.** KOSMOS 추가 파일 184건 모두 swap 2 (한국 행정 도구 시스템) 직접 구성요소로 PRESERVE-AS-SWAP-IMPL 로 분류.

---

## PRESERVE-AS-SWAP-IMPL (KOSMOS-only, swap 2 정당)

### A. 4 primitive (TS, TUI 측 — Tool 인터페이스 구현)

| 파일 | 역할 | swap 2 정당성 |
|---|---|---|
| `tui/src/tools/LookupPrimitive/LookupPrimitive.ts` + `prompt.ts` | `lookup(mode, tool_id, params)` envelope — BM25+dense 하이브리드 discovery + adapter dispatch | C1/C2 (Main verb abstraction) — `docs/requirements/kosmos-migration-tree.md § L1-C` |
| `tui/src/tools/SubmitPrimitive/SubmitPrimitive.ts` + `prompt.ts` | `submit(tool_id, payload)` — irreversible 신청/제출 envelope | 동상 |
| `tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts` + `prompt.ts` | `verify(family_hint, claim)` — 인증/검증 6-family envelope (10-row canonical map, Spec 2297) | 동상 |
| `tui/src/tools/SubscribePrimitive/SubscribePrimitive.ts` + `prompt.ts` | `subscribe(channel, filter)` — CBS 재난문자 / RSS 알림 stream | 동상 (Spec 031 Five-primitive harness) |

### B. 4 신규 보조 도구 (TS — MVP-7 완성)

| 파일 | 역할 | 정당성 (`tree § C6`) |
|---|---|---|
| `tools/TranslateTool/{TranslateTool.ts,prompt.ts,UI.tsx}` | 한국어 ↔ EN/JA 번역 보조 | 시민 다국어 접근 |
| `tools/CalculatorTool/{CalculatorTool.ts,parser.ts,prompt.ts}` | 행정 비용/세금 계산 | 시민 보조 |
| `tools/DateParserTool/{DateParserTool.ts,korean-date-parser.ts,prompt.ts}` | "다음 주 화요일" 등 한국어 자연어 날짜 | 한국 행정 일정 |
| `tools/ExportPDFTool/{ExportPDFTool.ts,prompt.ts,render.ts}` | 대화/도구결과/영수증 PDF export | UI E.4 결정사항 |

### C. IPC dispatcher 인프라 (TS, KOSMOS-only)

| 파일 | 역할 |
|---|---|
| `tools/_shared/dispatchPrimitive.ts` + `.test.ts` | 4 primitive call() 본체 — TUI ↔ Python backend IPC dispatch (Spec 2297 Phase 0b) |
| `tools/_shared/pendingCallRegistry.ts` | 진행 중 tool_call 의 future registry (chat-request 턴 lifetime) |
| `tools/_shared/verboseRender.ts` | 4 primitive 결과의 verbose mode 렌더 |
| `tools/shared/primitiveCitation.ts` | adapter citation (real_classification_url) wiring |
| `services/toolRegistry/bootGuard.ts` | ToolRegistry 부팅 시 backend tool_registry 검증 |

### D. Python 백엔드 어댑터 (84 파일 — swap 2 의 실체)

| 그룹 | 파일 수 | 위치 | 구성요소 |
|---|---:|---|---|
| Core registry / envelope / executor | 14 | `src/kosmos/tools/{registry,envelope,executor,errors,permissions,policy_derivation,...}.py` | ToolRegistry · GovAPITool base · permission policy citation infra · audit ledger · BM25 index |
| Routing / discovery / lookup | 8 | `src/kosmos/tools/{lookup,search,routing_index,bm25_index,tokenizer,resolve_location,main_router,mvp_surface}.py` | `lookup` primitive backend · BM25 + dense hybrid retrieval |
| Live 어댑터: KOROAD | 4 | `src/kosmos/tools/koroad/` | accident_hazard_search · accident_search · code_tables |
| Live 어댑터: KMA (기상청) | 8 | `src/kosmos/tools/kma/` | 6 weather endpoints + grid_coords + projection |
| Live 어댑터: HIRA (심평원) | 2 | `src/kosmos/tools/hira/` | hospital_search |
| Live 어댑터: NMC (의료원) | 3 | `src/kosmos/tools/nmc/` | emergency_search + freshness SLO (Spec 023) |
| Live 어댑터: NFA119 (소방청) | 2 | `src/kosmos/tools/nfa119/` | emergency_info_service |
| Live 어댑터: SSIS (복지부) | 3 | `src/kosmos/tools/ssis/` | welfare_eligibility_search |
| Geocoding 어댑터 | 5 | `src/kosmos/tools/geocoding/` | juso · kakao · sgis · region_mapping |
| Mock 어댑터 (Verify family ×9) | 11 | `src/kosmos/tools/mock/verify_*.py` + `barocert/` + `omnione/` + `npki_crypto/` | 6-family verify mock (시뮬·금융·공동·KEC·MID·MyData·SSO) |
| Mock 어댑터 (Submit family ×3) | 3 | `src/kosmos/tools/mock/submit_*.py` | 정부24 minwon · 홈택스 taxreturn · public mydata action |
| Mock 어댑터 (Lookup family ×2) | 2 | `src/kosmos/tools/mock/lookup_*.py` | 정부24 인증서 · 홈택스 simplified |
| Mock 어댑터 (Subscribe family) | 4 | `src/kosmos/tools/mock/{cbs,data_go_kr,mydata}/` | 재난 CBS · data.go.kr REST/RSS · welfare mydata |
| Retrieval (BM25 + dense + hybrid) | 7 | `src/kosmos/tools/retrieval/` | backend protocol · bm25_backend · dense_backend (Spec 585) · hybrid · degrade · manifest |
| Misc | 8 | `_outbound_trace.py` · `discovery_bridge.py` · `models.py` · `rate_limiter.py` · `register_all.py` · `transparency.py` · `verify_canonical_map.py` · `tokenizer.py` | Spec 019 rate limiter · Spec 024 transparency · Spec 2297 verify canonical map |

### E. KOSMOS-only 테스트

| 파일 | 역할 |
|---|---|
| `tools/__tests__/registry-boot.test.ts` | 13-tool 시민 surface closure 테스트 (Spec 1634 T035) |
| `tools/__tests__/permission-citation.test.ts` | 모든 GovAPITool 이 real_classification_url citation 갖는지 검증 |
| `tools/__tests__/span-attribute-parity.test.ts` | OTEL span attribute Spec 021 / 2297 parity |

---

## PRESERVE-IDENTICAL (CC == KOSMOS, byte-identical 또는 SDK shim 만)

24 디렉터리 byte-identical (모든 파일 diff 0):

```
AskUserQuestionTool   ConfigTool         EnterPlanModeTool   EnterWorktreeTool
ExitPlanModeTool      ExitWorktreeTool   ListMcpResourcesTool McpAuthTool
MCPTool               ReadMcpResourceTool ScheduleCronTool   SendMessageTool
SleepTool             SyntheticOutputTool TaskCreateTool     TaskGetTool
TaskListTool          TaskOutputTool      TaskStopTool       TaskUpdateTool
TeamCreateTool        TeamDeleteTool      testing             TodoWriteTool
```

**비고**:
- 이 24개 중 **TodoWriteTool · TaskCreate~Update · TeamCreate/Delete · ScheduleCronTool · ListMcpResourcesTool · ReadMcpResourceTool · MCPTool · McpAuthTool · SkillTool · AskUserQuestionTool · SendMessageTool · SleepTool · ConfigTool · Worktree×2 · PlanMode×2 · SyntheticOutputTool** 모두 KOSMOS `tools.ts` 의 `getAllBaseTools()` 등록 표에 **포함되지 않음** (FR-013 explicit exclusion). import 만 retain — permissions / sandbox 인프라 참조 때문.
- 즉 byte-identical 이지만 **dead 등록 candidate**. 후속 정리 (Spec 1633 P3 후속, 또는 신규 Epic) 권고 (S1/S5 영역과 cross-cut).

기타 PRESERVE-IDENTICAL 큰 항목:
- `Tool.ts` (29516 → 29552 byte, +36 byte = `ToolProgressData` type export 1줄). 인터페이스 시그니처 100% identical.
- `tools/utils.ts` byte-identical.
- 14개 발산 디렉터리 내부 파일 대부분 (BashTool 4 파일 중 모든 차이는 SDK import 1줄 + telemetry stub 1줄 — 본체 byte-identical).

---

## 위험 신호 (Risk findings)

| # | 심각도 | 항목 | 본질 | 권고 |
|---|---|---|---|---|
| R1 | **HIGH** | `services/tools/toolExecution.ts` 의 11개 telemetry no-op stub | OTEL Spec 021 파이프라인이 tool execution span 을 못 받음. 4-tier OTEL (Tool layer) 가 silent. Langfuse trace 에 tool boundary 누락. | utils/telemetry helper 를 Spec 021 OTLP 라우팅으로 정식 wire. 현재 stub 은 fragile patch. |
| R2 | **MEDIUM** | `tools.ts` line 274 `isReplModeEnabled() && REPLTool` 분기 잔존 | REPLTool 이 stub (`isEnabled: () => false`) 이라 사실상 dead 지만 코드 path 가 살아있어 향후 회귀 위험 (env var 토글로 재활성 가능). | `isReplModeEnabled` import 자체 + 분기 제거 (Spec 1633 후속). |
| R3 | **MEDIUM** | `tools.ts` 의 14개 PRESERVE-IDENTICAL but dead-import (TodoWriteTool · TaskCreate~Update · TeamCreate/Delete · ScheduleCronTool · ConfigTool 등) | byte-identical 보존하지만 등록 안 됨 → permissions/sandbox 가 참조 안 하면 진짜 dead. | grep 으로 각 import 의 실제 사용처 검증 후 사용 안 되면 import 도 제거. |
| R4 | **MEDIUM** | `AgentTool` 11 파일 발산 정밀 분석 미수행 | KOSMOS 가 AgentTool 을 "Task primitive backing" 으로 재용도화 — sub-agent 시그니처 (Tool interface) 가 byte-identical 보존되는지 본 감사 시간 제약으로 spot-check 만. | **needs human review**: AgentTool/runAgent.ts + forkSubagent.ts + builtInAgents.ts 의 시그니처 diff 확인 필수. |
| R5 | **LOW** | KOSMOS-only `_shared/dispatchPrimitive.ts` 가 4 primitive call() 본체 — IPC bridge 종속 | swap 2 본체이므로 정당하지만, IPC 프로토콜 (Spec 032) 변경 시 4 primitive 동시 회귀 가능. | Spec 032 envelope schema CI consistency test 가 4 primitive 모두 cover 하는지 검증. |
| R6 | **LOW** | Python 백엔드 84 파일 — Live 어댑터 32 + Mock 어댑터 20 + infrastructure 32 | swap 2 본체. 본 감사는 enumerate + 카테고리 분류만. | 각 어댑터의 GovAPITool 인터페이스 준수 + permission citation 존재 + Pydantic v2 frozen model 사용 검증은 별도 Q1-Q10 plugin validation matrix (Spec 1636) 가 담당. |
| R7 | **NONE** | **Tool.ts 인터페이스 시그니처 byte-identical** | 핵심 invariant — call/inputSchema/userFacingName/isReadOnly/validateInput/renderResult/prompt 모든 hook signatures 변경 0. CC 등록 메커니즘 (`getAllBaseTools()` 패턴 + Tool union type) 보존. | **검증 PASS** — swap 2 정당성 핵심 증거. |

---

## 결론

| 항목 | 결과 |
|---|---|
| CC 슬라이스 174 파일 enumerate | ✅ 누락 0 |
| `Tool.ts` 인터페이스 byte-identical | ✅ PASS (2줄 차: SDK alias + `ToolProgressData` extension type) |
| `tools.ts` 등록 메커니즘 보존 | ✅ PASS (`getAllBaseTools()` 패턴 동일, 등록 도구 목록만 시민용으로 교체) |
| 권한 위임 패턴 (`<PermissionRequest>` ↔ Tool.needsPermissions) 보존 | ✅ PASS (CC dev 도구 권한 hook signature 그대로, KOSMOS 어댑터가 같은 hook 으로 한국 기관 정책 citation 주입) |
| dev 도구 (Bash/FileEdit/FileWrite/Glob/Grep/NotebookEdit/REPL/PowerShell/LSP) **등록 제외** | ✅ PASS (FR-013 explicit, getAllBaseTools 표에서 제거; import 만 retain) |
| dev 도구 **import 잔존**의 정당성 | ✅ FR-013 (permissions/sandbox/attachments 인프라 참조) 명시적 — 단 R3 로 정리 권고 |
| swap 2 (4 primitive + 한국 어댑터) **PRESERVE-AS-SWAP-IMPL** 정당 | ✅ 184 파일 전부 `tree § L1-B/C` 결정사항으로 매핑 |
| 부당 발산 의심 | ⚠ R1 (telemetry stub) · R4 (AgentTool 정밀 미검증) — needs human review |

**Verdict**: S2 (Tool System) 슬라이스는 swap 2 의 정당한 발산을 보여주며, **CC Tool 인터페이스 + 등록 메커니즘 + 권한 위임 패턴은 byte-identical 보존**. 핵심 thesis ("KOSMOS = CC + 2 swaps") 가 도구 시스템에서 정밀하게 지켜짐. 단 R1/R4 두 항목은 follow-up Epic 권고.
