# Handoff prompt — KOSMOS K-EXAONE tool wiring (CC reference migration)

> **Epic #2077** · 작성일 2026-04-27 · main HEAD `523b520` 기준 (Epic #1978 머지 후 fdfd3e9 paint chain 통합 후)
> 본 문서는 `/clear` 직후 cold-start session 으로 인계받은 핸드오프. `/speckit-specify` Phase 0 의 reference 인용 source.

---

## 1. 작업 목적 (한 문단)

K-EXAONE 이 `<tool_call>{"name":"Read",...}</tool_call>` 같은 **CC 학습 데이터 도구를 hallucinate 하는 문제**를 해결한다. 진짜 원인은 **TUI 가 `ChatRequestFrame.tools` 를 비워 보내고 backend 도 fallback inject 가 없어서** K-EXAONE 이 `tools=None` 으로 호출되는 것. 그 결과 모델은 KOSMOS 의 5 primitive (`lookup`/`resolve_location`/`submit`/`subscribe`/`verify`) 를 모르고 자기 학습 데이터의 CC tool 들 (Read, Glob, Bash 등) 을 응답에 박는다. 본 epic 은 CC 소스맵의 tool wiring + agentic loop 패턴을 KOSMOS 로 마이그레이션해서 K-EXAONE 이 KOSMOS-등록 도구만 호출하고, 호출 결과가 `tool_use` content block 으로 transcript 에 paint 되고, follow-up turn 까지 진행되도록 만든다.

## 2. Canonical references

- `AGENTS.md` — KOSMOS 룰 (Conventional Commits, English source, no Co-Authored-By, no new runtime dep)
- `docs/vision.md` — 6-layer 아키텍처
- `docs/requirements/kosmos-migration-tree.md § L1-A.A3` — Tool protocol = K-EXAONE native function calling
- `docs/requirements/kosmos-migration-tree.md § L1-B.B6` — composite tool 제거 (LLM primitive chain)
- `docs/requirements/kosmos-migration-tree.md § L1-C.C7` — `plugin.<id>.<verb>` 네임스페이스 · 4 root 예약
- `src/kosmos/llm/_cc_reference/claude.ts:1900-2304` — fdfd3e9 commit 으로 cp 된 CC streaming/agentic baseline
- 메모리 파일들:
  - `feedback_cc_source_migration_pattern.md` — task-level implementation 은 CC 소스맵 복사 → 마이그레이션. 새로 작성 X
  - `feedback_check_references_first.md` — 코딩 전에 reference 인용 후 정합 확인
  - `feedback_runtime_verification.md` — PTY 로 TUI 직접 띄워 사용자 시점 검증까지

## 3. Diagnosis (line-cited, 2026-04-27 main HEAD `523b520`)

### 3.1 Backend 누락 (`src/kosmos/ipc/stdio.py`)

| 영역 | 현재 상태 | 필요 변경 |
|---|---|---|
| `frame.tools` unpack (line 1099-1101) | `LLMToolDefinition.model_validate(t.model_dump())` 정상 | OK — 그대로 유지 |
| **frame.tools 빈 경우 fallback** (line 1117 `tools=llm_tools or None`) | **없음** — `tools=None` 으로 LLM 호출 | `ToolRegistry().export_core_tools_openai()` (registry.py:373) 자동 inject |
| **system prompt 도구 list 주입** (`prompts/system_v1.md` 8 lines) | **없음** — 순수 산문 | system prompt 끝에 `## Available tools` 섹션을 primitive 5종 signature 로 자동 append |
| Registry 인스턴스화 | `_dispatch_primitive()` 안에서만 매번 new — wasteful | session 시작 시 1회 instantiate, `_handle_chat_request` 진입 전 ready |
| Whitelist (line 627-679 / 890-939) | 하드코딩된 `{lookup, resolve_location, submit, subscribe, verify}` | primitives 카탈로그 (`src/kosmos/primitives/__init__.py`) 에서 single source of truth 로 끌어오기 |
| Tool result follow-up (line 1412+) | `LLMChatMessage(role="tool", content=payload, name=fname, tool_call_id=cid)` | OK — 그대로 유지 |

### 3.2 TUI 누락 (`tui/src/query/deps.ts`)

| 영역 | 현재 상태 | 필요 변경 |
|---|---|---|
| ChatRequestFrame 빌드 (deps.ts:73-81) | `tools` 필드 omit | `getAllBaseTools()` → primitive 5종 + MVP-7 보조 → `ToolDefinition[]` 로 직렬화해 spread |
| Tool object pool (`tui/src/tools.ts:228-257`) | `LookupPrimitive`, `SubmitPrimitive`, `VerifyPrimitive`, `SubscribePrimitive` 정의 존재 | Zod inputSchema → JSON Schema 2020-12 변환 + `name`/`description` 추출하는 `toToolDefinition()` 헬퍼 추가 |
| tool_call frame 처리 (deps.ts:237-242) | `createSystemMessage("🔧 …")` — display-only progress line | CC 패턴으로 `stream_event{content_block_start, content_block:{type:'tool_use', id, name, input}}` + `content_block_stop` yield → `AssistantToolUseMessage` 가 native 렌더 |
| tool_result frame 처리 (deps.ts:245-249) | `createSystemMessage("✓ ok …")` | `tool_use_id` 매칭으로 user-message 에 `tool_result` content block append (`createUserMessage` with tool_result content) |
| permission_request frame 처리 (deps.ts:250-266) | **자동 거부** + warning SystemMessage | `useSessionStore().setPendingPermission(...)` 로 dispatch → `PermissionGauntletModal` 이 modal 표시 → 사용자 Y/N 후 PermissionResponseFrame send |

### 3.3 UI 컴포넌트 (모두 real, paint 위험 0 — verified)

- `AssistantToolUseMessage.tsx` (367 LOC, real) — ToolUseBlockParam input
- `GroupedToolUseContent.tsx` (57 LOC, real) — multi-tool aggregation
- `ErrorEnvelope.tsx` (113 LOC, real) — 3 error styles (llm/parser/tool)
- `AssistantThinkingMessage.tsx` (85 LOC, real) — fdfd3e9 commit 으로 wire 완료
- `MarkdownTable.tsx` (321 LOC, real)
- `permissions/PermissionGauntletModal.tsx` (100+ LOC, real, REPL.tsx:5275-5277 mount 됨)

P0 stub shadow `.ts` 추가 발견 0 건 (직전 세션에서 6 개 청소 완료).

## 4. CC reference cp 매핑

이전 세션에서 cp 완료 (`src/kosmos/llm/_cc_reference/`):
- `claude.ts` (3419 lines)
- `client.ts` (389 lines)
- `errors.ts` (1207 lines)
- `emptyUsage.ts` (22 lines)

**추가 cp 필요** (cp 위치는 `_cc_reference/` 하위에 동일 이름 유지 권장):

| CC 파일 | Lines | 본 epic 에 필요한 이유 | cp 위치 |
|---|---|---|---|
| `src/utils/api.ts` | 718 | `toolToAPISchema()` (line 119-266) — Tool → BetaTool 변환. K-EXAONE OpenAI-compat 매핑 baseline | `src/kosmos/llm/_cc_reference/api.ts` |
| `src/tools.ts` | 389 | `getAllBaseTools()` / `getTools()` / `assembleToolPool()` — tool catalog orchestration | `src/kosmos/llm/_cc_reference/tools.ts` |
| `src/constants/prompts.ts` | 914 | system prompt 동적 composition — tool name/capability 섹션 baseline | `src/kosmos/llm/_cc_reference/prompts.ts` |
| `src/query.ts` | 1729 | LLM ↔ tool_use ↔ tool_result 멀티턴 closure 본체 | `src/kosmos/llm/_cc_reference/query.ts` |
| `src/services/tools/toolOrchestration.ts` | 188 | `runTools()` async generator — concurrent read / serial write 분기 | `src/kosmos/llm/_cc_reference/toolOrchestration.ts` |
| `src/services/tools/toolExecution.ts` | 1745 | `runToolUse()` — input 검증, 실행, 에러 wrap, ToolResultBlockParam 직렬화 | `src/kosmos/llm/_cc_reference/toolExecution.ts` |
| `src/utils/messages.ts` | 5512 | `normalizeContentFromAPI()` + `ensureToolResultPairing()` — Anthropic API content blocks → 내부 MessageType. tool_use ↔ tool_result 페어링 검증 | `src/kosmos/llm/_cc_reference/messages.ts` |
| `src/utils/permissions/permissions.ts` | 1486 | permission gauntlet 본체 (Spec 033 와 매핑) | `src/kosmos/llm/_cc_reference/permissions.ts` |
| `src/utils/toolResultStorage.ts` | (검색 필요) | tool result token budgeting + `processToolResultBlock()` | `src/kosmos/llm/_cc_reference/toolResultStorage.ts` |

## 5. 마이그레이션 스코프 (Step 별 분해)

**원칙**: CC reference cp 후 Python 으로 marshal. 한 번에 한 layer 씩, 각 layer 마다 unit test → PTY E2E → VHS 시각 검증.

### Step 1 — CC reference cp + 인덱스 (작업량 30분)
위 § 4 의 9 개 파일 cp. `src/kosmos/llm/_cc_reference/README.md` 작성: 파일별 1-line description + KOSMOS 매핑.

### Step 2 — TUI Tool → ToolDefinition 직렬화 (작업량 2-3h)

CC reference: `_cc_reference/api.ts:toolToAPISchema()` (line 119-266).

`tui/src/query/toolSerialization.ts` (신규):
- `toolToFunctionSchema(tool: Tool): FunctionSchema` — Zod inputSchema → JSON Schema Draft 2020-12 변환. AGENTS.md no-new-runtime-dep 준수 위해 stdlib walker 우선 (또는 zod 자체 `.toJSONSchema()` 검토). `name` (Tool.name), `description` (Tool.userFacingName + Tool.prompt 첫 200 자) 추출
- `getToolDefinitionsForFrame(): ToolDefinition[]` — `getAllBaseTools()` 호출, primitive 5종 + MVP-7 만 필터, `toolToFunctionSchema` 적용

`tui/src/query/deps.ts:73-81` 의 ChatRequestFrame 빌드에 `tools: getToolDefinitionsForFrame()` 추가.

### Step 3 — Backend system prompt 도구 list 자동 inject (작업량 1-2h)

CC reference: `_cc_reference/api.ts:appendSystemContext()` + `_cc_reference/prompts.ts` 의 dynamic composition.

`src/kosmos/llm/system_prompt_builder.py` (신규):
- `build_system_prompt_with_tools(base: str, tools: list[LLMToolDefinition]) -> str` — base 끝에 `\n\n## Available tools\n` 섹션 + 각 tool 에 대해 `### {name}\n{description}\n\n**Parameters**: {parameters JSON, indent=2}\n` append

`src/kosmos/ipc/stdio.py:_handle_chat_request` 진입 시:
- `system_text = await _ensure_system_prompt()`
- `if llm_tools: system_text = build_system_prompt_with_tools(system_text, llm_tools)`
- `frame.system or system_text` 로 LLM 첫 메시지 설정

### Step 4 — Backend registry fallback (작업량 1-2h)

CC reference: `_cc_reference/tools.ts:assembleToolPool()` (line 345-367).

`src/kosmos/ipc/stdio.py`:
- session 시작 (또는 첫 chat_request) 시 `ToolRegistry()` 1 회 instantiate, module-level cache
- `_handle_chat_request` 에서 `if not frame.tools: llm_tools = registry.export_core_tools_openai()` fallback
- `registry.export_core_tools_openai()` (현재 `src/kosmos/tools/registry.py:373`) 가 primitive 5 종 + MVP 보조를 OpenAI function shape 로 반환

### Step 5 — TUI tool_call frame → tool_use content block paint (작업량 2-3h)

CC reference: `_cc_reference/messages.ts:normalizeContentFromAPI()` + `_cc_reference/claude.ts:1995-2052` (content_block_start tool_use case).

`tui/src/query/deps.ts:237-242` 변경:
- 현재 `createSystemMessage("🔧 …")` 단일 yield
- 신규 패턴 (CC mirror):
  ```typescript
  yield { type: 'stream_event', event: { type: 'content_block_start', index: ++blockIndex, content_block: { type: 'tool_use', id: fa.call_id, name: fa.name, input: fa.arguments } } }
  yield { type: 'stream_event', event: { type: 'content_block_stop', index: blockIndex } }
  ```
- 그러면 `handleMessageFromStream` (utils/messages.ts:3024-3037) 가 `streamingToolUses` array 에 push 해서 `AssistantToolUseMessage` 가 native 렌더

`message_start` 시점에 `content` 배열에 tool_use block 누적되도록 final `createAssistantMessage` 도 함께 수정. CC 는 한 turn 에 text block + N 개 tool_use block 다 yield.

### Step 6 — TUI tool_result frame → tool_result user-message (작업량 2-3h)

CC reference: `_cc_reference/messages.ts:ensureToolResultPairing()` (line 1150-1250).

`tui/src/query/deps.ts:245-249`:
- 현재 `createSystemMessage("✓ ok …")` 만
- 신규: `createUserMessage` with `[{type: 'tool_result', tool_use_id: fa.call_id, content: <envelope>}]` 로 transcript 에 user-role 메시지 append → 이게 다음 turn LLM context 로 자동 들어감 (CC 패턴)

### Step 7 — PermissionGauntletModal 실 연결 (작업량 2-3h)

CC reference: `_cc_reference/permissions.ts` (1486 lines, KOSMOS Spec 033 와 매핑 검토 필요).

`tui/src/query/deps.ts:250-266`:
- 현재 `createSystemMessage(... auto-deny)` + `permission_response` decision='denied' 즉시 send
- 신규:
  - `useSessionStore.getState().setPendingPermission({request_id, primitive_kind, description_ko, description_en, risk_level})` 로 dispatch
  - `await waitForPermissionDecision(request_id)` (Promise — modal 이 Y/N 후 resolve)
  - decision 결과로 `permission_response` send
- `PermissionGauntletModal` (이미 REPL.tsx:5275 에 mount) 에서 Y/N 처리 후 session-store cleared + Promise resolve

## 6. 검증 방법 (사용자 시점)

매 step 마다:

```bash
# Static
cd tui && bun run typecheck && bun test tests/...
cd .. && uv run pytest tests/llm tests/ipc
```

**PTY E2E** (`feedback_runtime_verification` 메모리 기준): /tmp/run_pty_tool_e2e.py 시나리오:
- Step 2 검증: prompt "강남구 응급실" → frame.tools 길이 trace 로 5+ 확인
- Step 3 검증: prompt 동일 → backend log 에서 system prompt 끝에 "lookup" 등장 확인 + K-EXAONE 응답에 `<tool_call>{"name":"Read"}` 0 회
- Step 5/6 검증: prompt 동일 → tool_call frame 1+ 도착 + tool_result frame 1+ 도착 + final response paint
- Step 7 검증: prompt "출생신고 서류 제출" (submit primitive trigger) → PermissionGauntletModal frame 캡처

**VHS GIF** (frame-by-frame, screenshot):

```
# /tmp/probe-tool-loop.tape
Output "/tmp/probe-tool-loop.gif"
Set Shell "bash"; Set FontSize 14; Set Width 1100; Set Height 700; Set Padding 16
Hide
Type "cd ~/KOSMOS/tui"; Enter; Sleep 200ms
Type "set -a; source ../.env; set +a"; Enter; Sleep 200ms
Type "export KOSMOS_FORCE_INTERACTIVE=1 OTEL_SDK_DISABLED=true"; Enter; Sleep 200ms
Type "clear"; Enter; Sleep 200ms
Show
Type "bun run tui"; Enter; Sleep 12s
Type "강남구 근처 24시간 응급실을 알려주세요."
Sleep 1s; Enter
Sleep 60s
Screenshot "/tmp/probe-tool-loop-final.png"
Sleep 500ms
```

기대 시각 시퀀스:
1. user prompt 입력 직후
2. spinner "Querying…" 또는 thinking 채널이 paint (직전 epic 결과)
3. tool_use 박스 (CC-style: `🔧 lookup` + JSON args)
4. tool_result 박스 (envelope summary)
5. 최종 자연어 응답 ("강남구 24시간 응급실은 …")

## 7. 한계 + 후속 epic (out of scope)

본 epic 이 다루지 **않는** 것:
- `lookup` mode 분리 (search vs fetch BM25 라우팅) — Spec 022 영역
- Adapter-level permission gate (Spec 033) — 본 epic 은 PermissionGauntletModal **modal 자체** 만 wire
- Plugin-tier tools (Epic #1979) — primitive 5종 + MVP-7 only
- `subscribe` primitive long-lived stream — PoC 정도
- Spec 1635 P4 UI L2 의 onboarding/help/etc — paint chain 만 사용

후속 epic:
- Spec 022 follow-up: `lookup(search/fetch)` BM25 + dense 하이브리드 검증
- Permission v2 (Spec 033) layer 2/3 receipt 발급 + audit ledger 영구화
- Epic #1979 Plugin DX TUI integration
- Epic #1980 Agent Swarm TUI integration
- KMA / KOROAD live API 실연

## 8. Spec-driven workflow 권장 흐름

```
/speckit-specify "K-EXAONE tool wiring: TUI sends ChatRequestFrame.tools, backend injects system-prompt tool list, agentic loop closes with tool_use/tool_result content blocks paint"
  ↓
human review spec.md
  ↓
/speckit-plan → Phase 0 read .specify/memory/constitution.md + docs/vision.md § Reference materials
              → Map each design decision to _cc_reference/{api.ts, query.ts, toolExecution.ts, messages.ts, permissions.ts}
human review plan.md
  ↓
/speckit-tasks → 약 15-20 tasks 예상 (7 step × 2-3 sub-tasks)
  ↓
/speckit-analyze → constitution compliance
  ↓
/speckit-taskstoissues → Sub-Issues API 로 Epic 아래 등록
  ↓
/speckit-implement → Agent Teams 병렬 (Sonnet workers, Opus Lead/review)
  ↓
PR with `Closes #2077` only → CI watch → Codex review → merge
```

이 epic 의 Constitution 핵심:
- AGENTS.md hard rules: 모든 source English, no `--no-verify`, no `requirements.txt`, no Go/Rust
- AGENTS.md "no new runtime dep" — `zod-to-json-schema` 추가는 신중히 검토. 가능하면 stdlib walker 로 변환
- L1-A.A3 = K-EXAONE native function calling
- L1-B.B6 = composite tool 제거 — 합쳐지지 않은 primitive list 만 노출
- C7 = `plugin.<id>.<verb>` namespace 예약 — primitive 4 종 root reserved

## 9. 참조 commit history

```
523b520 docs(agents): deprecate § Copilot Review Gate, document Codex inline review (#2076)
fdfd3e9 feat(tui): paint chain unblocked + K-EXAONE thinking via CC reference (KOSMOS-1633 P3) (#2075)
f4d0e8f feat(1978): spec workflow + T001/T002/T003 scaffolding + B1 trace (#2074)
```

## 10. 잠재 risk + mitigation

| Risk | 가능성 | Mitigation |
|---|---|---|
| Zod → JSON Schema 변환이 nested discriminated union 에서 깨짐 | 중 | primitive 5 종은 단순 schema 라 zod 자체 `.toJSONSchema()` 또는 `zod-to-json-schema` lib 검토 |
| K-EXAONE 이 system prompt 에 도구 list 있어도 여전히 `Read` hallucinate | 저-중 | system prompt 에 `Only the following tools are available` 강한 명령 + `<tool_call>` 응답 후 unknown_tool error frame 을 LLM 에게 turn 으로 feedback 해 학습 |
| FriendliAI Tier 1 RPM 한계 (60 RPM) — multi-turn loop 가 한 prompt 당 2-5 회 호출 | 중 | 직전 epic 의 `RetryPolicy` 그대로 동작, 단 burst 시 sleep |
| AssistantToolUseMessage 가 Tool registry lookup 실패하면 빈 paint | 저 | TUI 의 `getAllBaseTools()` 와 paint 시 `findToolByName()` 동일 source 보장 |
| Permission modal 이 long-running tool 동안 사용자 응답 없으면 timeout | 중 | Spec 033 의 5-min timeout + `Esc` interrupt 검증 |

## 11. 변경 파일 예상 list (커밋 대상)

```
src/kosmos/llm/_cc_reference/
  + api.ts (cp from CC)
  + tools.ts (cp from CC)
  + prompts.ts (cp from CC)
  + query.ts (cp from CC)
  + toolOrchestration.ts (cp from CC)
  + toolExecution.ts (cp from CC)
  + messages.ts (cp from CC)
  + permissions.ts (cp from CC)
  + toolResultStorage.ts (cp from CC)
  + README.md (인덱스)

src/kosmos/llm/
  + system_prompt_builder.py (신규)

src/kosmos/ipc/
  M stdio.py (registry fallback + system prompt 도구 inject + whitelist source-of-truth)

tui/src/query/
  + toolSerialization.ts (신규)
  M deps.ts (frame.tools 채움 + tool_call/tool_result/permission_request CC-style projection)

tui/src/store/ 또는 utils/
  M sessionStore (pending_permission setter + waitForDecision Promise)

tests/llm/
  + test_system_prompt_builder.py
tests/ipc/
  M test_stdio.py (registry fallback 분기)
tui/tests/
  + tools/serialization.test.ts
  M ipc/handlers.test.ts (deps.ts 신규 분기)

specs/2077-kexaone-tool-wiring/
  + spec.md (/speckit-specify output)
  + plan.md (/speckit-plan output)
  + tasks.md (/speckit-tasks output)
  + handoff-prompt.md (이 파일)
```
