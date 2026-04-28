# CC 원본 소스 기반 마이그레이션 실행 계획

**Status**: 실행 계획 (domain-harness-design.md 의 구체화)
**Date**: 2026-04-29
**기준점**: KOSMOS = CC 원본 + 2 swaps. CC 소스맵은 `.references/claude-code-sourcemap/restored-src/` (research-only, 수정 금지). 모든 개발은 CC 원본을 base로 KOSMOS 트리(`tui/src/`, `src/kosmos/`)에서 진행.

---

## 0. 원칙 (한 문단)

CC 원본을 토대로 한다는 것은: **CC가 이미 검증한 모든 인프라 (REPL, ToolRegistry, PermissionRequest, agentic loop, slash commands, message stream, IPC, theme, keybindings)는 byte-identical로 보존**, 두 가지만 바꾼다 — (a) `services/api/` 의 Anthropic 클라이언트를 KOSMOS Python 백엔드로 가는 IPC 브릿지로 (이미 Spec 1633에서 진행 중), (b) `tools/` 디렉토리의 개발자 중심 도구(Bash/Read/Write/Edit/Grep/Glob/Notebook/REPL/PowerShell/LSP/TodoWrite)를 KOSMOS 5-primitive 시민 중심 surface(`lookup/submit/verify/subscribe` + `resolve_location`)로. 그 외 모든 CC tool (AskUserQuestion, Brief, Agent, MCP, Task lifecycle, Team, Skill, Schedule, ToolSearch, EnterPlanMode 등 30개+)은 CC 원본 그대로 보존.

---

## 1. 현재 상태 정확 매핑

CC `restored-src/src/tools/` 43개 vs KOSMOS `tui/src/tools/` 57개를 diff한 결과 (2026-04-29):

### 1.1 Class A — CC 원본 byte-identical 또는 거의 동일 (43개, 보존 대상)

CC와 KOSMOS 양쪽에 모두 존재하는 tool. 대부분 byte-identical (단순 SDK import 경로 차이만 존재).

| Tool | CC role | KOSMOS 처리 |
|---|---|---|
| `AgentTool` | sub-agent dispatch | **보존** — 시민 swarm 모드 (Spec 027) base |
| `AskUserQuestionTool` | 시민-대상 Q&A | **보존** — 시민 인터랙션 핵심 |
| `BashTool` | shell command 실행 | **삭제** — 시민에게 무의미 |
| `BriefTool` | 응답 요약 | **보존** — 한국어 응답 요약에 유용 |
| `ConfigTool` | 설정 변경 | **보존** — KOSMOS_* env 노출 |
| `EnterPlanModeTool` / `ExitPlanModeTool` | plan mode 토글 | **보존** — KOSMOS도 plan mode 지원 |
| `EnterWorktreeTool` / `ExitWorktreeTool` | worktree | **보존** — multi-session 격리 |
| `FileEditTool` / `FileReadTool` / `FileWriteTool` | file 조작 | **삭제** — 시민이 코드 편집 안 함 |
| `GlobTool` / `GrepTool` | 코드 검색 | **삭제** — 시민이 코드 검색 안 함 |
| `ListMcpResourcesTool` / `MCPTool` / `McpAuthTool` / `ReadMcpResourceTool` | MCP 통합 | **보존** — KOSMOS 플러그인 시스템 (Spec 1636) base |
| `LSPTool` | 코드 인텔리전스 | **삭제** — 시민이 코드 안 다룸 |
| `NotebookEditTool` | Jupyter notebook 편집 | **삭제** |
| `PowerShellTool` | PowerShell | **삭제** |
| `REPLTool` | Python REPL | **삭제** |
| `RemoteTriggerTool` | 외부 webhook trigger | **보존** — 정부 시스템 webhook 호환 가능성 |
| `ScheduleCronTool` | cron 작업 | **보존** — 정기 알림(예: 응급실 가용량 모니터링) |
| `SendMessageTool` | 다른 agent에 메시지 전송 | **보존** — swarm |
| `SkillTool` | skill 호출 | **보존** — KOSMOS 스킬 시스템 |
| `SleepTool` | wait/delay | **보존** — workflow utility |
| `SyntheticOutputTool` | 합성 출력 | **보존** — 테스트/시뮬레이션 |
| `TaskCreateTool` / `TaskGetTool` / `TaskListTool` / `TaskOutputTool` / `TaskStopTool` / `TaskUpdateTool` | task 라이프사이클 | **보존** — KOSMOS 다중 작업 추적 |
| `TeamCreateTool` / `TeamDeleteTool` | team 관리 | **보존** — multi-agent 부처 협업 |
| `TodoWriteTool` | 개발자 todo 리스트 | **삭제** — 시민에게 무의미 |
| `ToolSearchTool` | tool 검색 (BM25) | **보존** — 5-primitive 발견 핵심 |

**삭제 대상 (12개)**: Bash, FileRead, FileWrite, FileEdit, Grep, Glob, LSP, NotebookEdit, PowerShell, REPL, TodoWrite, +PowerShell 보조 1개 = **개발자 전용 도구 12개**.
**보존 대상 (31개)**: 그 외 모든 CC tool.

### 1.2 KOSMOS 추가 (14개, CC에 없음)

| Tool | 목적 | 처리 |
|---|---|---|
| `LookupPrimitive` | 5-primitive lookup verb | **유지** (citizen main verb) |
| `SubmitPrimitive` | 5-primitive submit verb | **유지** |
| `VerifyPrimitive` | 5-primitive verify verb | **유지** |
| `SubscribePrimitive` | 5-primitive subscribe verb | **유지** |
| `CalculatorTool` | 산술 계산 | **유지** — 시민 보조 도구 (kosmos-migration-tree § C.6 MVP 7) |
| `DateParserTool` | 날짜 파싱 | **유지** — § C.6 MVP 7 |
| `ExportPDFTool` | 대화 → PDF | **유지** — § E.4 |
| `TranslateTool` | 한국어↔English | **유지** — § C.6 MVP 7 |
| `MonitorTool` | 외부 시스템 모니터 | **삭제 후보** — KOSMOS-original, 시민 use case 불명확 |
| `ReviewArtifactTool` | artifact 리뷰 | **삭제 후보** — 개발자 use case |
| `SuggestBackgroundPRTool` | PR 제안 | **삭제** — 개발자 use case |
| `TungstenTool` | (불명) | **검사 필요** |
| `VerifyPlanExecutionTool` | plan 실행 검증 | **삭제 후보** — 개발자 use case |
| `WorkflowTool` | workflow 정의 | **검사 필요** |

---

## 2. CC 원본 다른 모듈의 KOSMOS 매핑

### 2.1 `services/api/` (Swap 1: LLM 클라이언트)

**CC 원본**: `services/api/anthropic.ts`, `services/api/claude.ts`, `services/api/sonnet.ts` 등 — Anthropic Messages API 직접 호출.

**KOSMOS**: 이 디렉토리 전체를 **IPC 브릿지로 교체**. 이미 Spec 1633에서 진행 중:
- CC `services/api/claude.ts` (3419 LOC) → KOSMOS `tui/src/ipc/llmClient.ts` (stdio bridge)
- CC `verifyApiKey()`, `queryHaiku()`, `queryWithModel()` → KOSMOS Python 백엔드로 IPC 호출
- 4 callsite 잔재 정리 필요 (memory `project_tui_anthropic_residue`)

**작업**: Spec 1633 dead-code elimination 마무리 + 연결 포인트만 KOSMOS IPC.

### 2.2 `components/permissions/` (보존, 인용 기반 운영)

**CC 원본**: `PermissionRequest.tsx` (216 LOC), `PermissionPrompt.tsx` (335 LOC), `PermissionDialog.tsx`, `PermissionExplanation.tsx`, `FallbackPermissionRequest.tsx`, `BashPermissionRequest/`, `FileEditPermissionRequest/`, etc. — 43개 권한 UI 컴포넌트.

**KOSMOS Spec 1979 감사 결과**: 모든 파일 byte-identical (SDK import 2줄 차이만 존재).

**작업 1**: 삭제 예정 개발자 tool에 대응하는 권한 UI 함께 삭제:
- `BashPermissionRequest/` (BashTool 삭제 시)
- `FileEditPermissionRequest/`, `FileReadPermissionRequest/` 또는 `FilePermissionDialog/` (File* tool 삭제 시)
- `FileWritePermissionRequest/`
- `FilesystemPermissionRequest/`
- `NotebookEditPermissionRequest/`
- `PowerShellPermissionRequest/`
- `SedEditPermissionRequest/` (sed 편집 — 개발자 tool)

**작업 2**: KOSMOS 5-primitive 권한 UI는 **CC `FallbackPermissionRequest`를 base로**:
- `lookup` → 데이터 조회 권한 prompt (실제 도메인이 본인인증 요구하면 그 UI)
- `submit` → 제출 권한 prompt (정부24/홈택스는 OPAQUE → 시나리오 핸드오프)
- `verify` → 인증 권한 prompt (마이데이터 표준동의서 등)
- `subscribe` → 구독 권한 prompt (CBS 재난문자 등)

각 5-primitive는 **새로운 권한 컴포넌트를 만들지 않음**. CC `FallbackPermissionRequest` + adapter의 `real_classification_url` 인용으로 구성.

### 2.3 `query/` (CC agentic loop, 보존)

**CC 원본**: `query/index.ts` 내 main agentic loop, `deps.ts` 내 IPC frame consumer (Spec 2077 결과 byte-identical).

**KOSMOS**: 보존. Spec 1633의 services/api/ 교체만 적용되면 자동으로 KOSMOS K-EXAONE으로 라우팅.

### 2.4 `screens/REPL.tsx` (보존, 마운트 포인트만 정리)

**CC 원본**: 거대한 REPL 컴포넌트. CC와 KOSMOS 모두 ~5500 LOC.

**현재 상태**: Spec 1979에서 KOSMOS-original 마운트 포인트(`kosmosPendingConsent`, `kosmosShowBypassConfirm`, `KosmosActivePermissionGate`) 모두 제거됨. CC 원본의 마운트 포인트만 활성.

**작업**: 추가 정리 없음. CC 원본 흐름 그대로 가동.

### 2.5 `commands/` (CC slash commands, 보존)

**CC 원본**: `/help`, `/clear`, `/login`, `/model`, `/config`, `/status`, `/exit`, `/permissions`, `/agent`, `/skill`, `/task` 등.

**KOSMOS 추가 candidate**:
- `/plugin` — 플러그인 install/uninstall/list (Spec 1979 P5)
- `/plugins` — 플러그인 브라우저
- `/onboarding` — 시민 온보딩
- `/export` — PDF 내보내기

**작업**: CC slash commands는 보존. KOSMOS 추가 commands는 별도 파일로 등록.

### 2.6 `permissions/` (KOSMOS-original, 이미 Spec 1979에서 삭제됨)

Spec 033 5-mode spectrum, PIPA §15(2) ConsentDecision, AAL hint, dontAsk — 전부 삭제 완료.

**작업**: 백엔드 Python `src/kosmos/permissions/` (25개 파일)도 같은 운명 — 후속 epic에서 정리.

---

## 3. 단계별 실행 경로 (concrete)

### Phase α — CC 원본 정합성 회복 (선행, 1 sprint)

**목표**: KOSMOS의 모든 CC-ported 파일을 CC 원본과 byte-identical 상태로 정렬. 차이는 SDK import 경로 변환만.

| Task | 작업 | 검증 |
|---|---|---|
| α-1 | `tui/src/components/permissions/` 전체 vs CC restored-src diff. SDK import 차이 외 임의 변경 발견 시 CC 원본으로 되돌림 | `diff -r` 결과 0 차이 (import 제외) |
| α-2 | `tui/src/query/` 전체 vs CC restored-src diff. Spec 2077 변경 점검 | 〃 |
| α-3 | `tui/src/screens/REPL.tsx` vs CC. KOSMOS-original 마운트 포인트 잔재 확인 | grep `kosmos*` → 정당한 KOSMOS 추가만 남음 |
| α-4 | `tui/src/services/api/` 전체 정리 — Spec 1633 잔재 4 callsite 제거 | grep `claude\.ts`, `verifyApiKey`, `queryHaiku` → 0건 |

**산출물**: 정합성 보고서 (`specs/1979-plugin-dx-tui-integration/cc-parity-audit.md`)

### Phase β — 개발자 tool 12개 삭제 (1 sprint)

**목표**: CC 원본에는 있지만 시민 use case에 무의미한 12개 tool + 그 권한 UI 삭제.

| Task | 삭제 대상 | 보존 대상 |
|---|---|---|
| β-1 | `tools/BashTool/` 전체 | — |
| β-2 | `tools/FileReadTool/`, `FileWriteTool/`, `FileEditTool/` | — |
| β-3 | `tools/GrepTool/`, `GlobTool/` | — |
| β-4 | `tools/NotebookEditTool/`, `LSPTool/`, `REPLTool/`, `PowerShellTool/`, `TodoWriteTool/` | — |
| β-5 | `components/permissions/BashPermissionRequest/`, `FileEditPermissionRequest/`, `FileWritePermissionRequest/`, `NotebookEditPermissionRequest/`, `PowerShellPermissionRequest/`, `SedEditPermissionRequest/`, `FilePermissionDialog/`, `FilesystemPermissionRequest/` | — |
| β-6 | system prompt에서 삭제된 tool 언급 제거 (`prompts/system_v1.md`) | 5-primitive 안내 추가 |
| β-7 | tool registry / 라우팅 인덱스 갱신 | 삭제 tool은 사라짐, 5-primitive 우선순위 상승 |

**검증**: bun test + uv run pytest 회귀 0건. 삭제 tool import 잔재 0건.

### Phase γ — 5-primitive를 CC tool 패턴으로 재정렬 (2 sprints)

**목표**: KOSMOS `LookupPrimitive`, `SubmitPrimitive`, `VerifyPrimitive`, `SubscribePrimitive` 4개를 **CC의 `Tool.ts` 인터페이스 정확히 따르도록** 재구현.

CC tool shape (`tools/AgentTool/AgentTool.tsx` 등 참조):

```typescript
export const LookupPrimitive: Tool = {
  name: 'lookup',
  description: () => '한국 정부 도메인 데이터 조회 (KOROAD/KMA/HIRA/NMC/...)',
  inputSchema: z.object({
    mode: z.enum(['search', 'fetch']),
    tool_id: z.string(),
    params: z.record(z.unknown()),
  }),
  isReadOnly: () => true,
  isMcp: false,
  validateInput: async (input, context) => { /* BM25 + adapter resolve */ },
  call: async function* (input, context) {
    // route to src/kosmos/tools/<domain>/<adapter>.py via IPC
    // adapter declares real_domain_policy → CC PermissionRequest gate
    // execute live or mock
    // yield PrimitiveOutput envelope
  },
  renderToolUseMessage: (input, context) => { /* 한국어 UI 표시 */ },
  renderToolResultMessage: (output, context) => { /* 한국어 결과 표시 */ },
}
```

| Task | 작업 |
|---|---|
| γ-1 | `LookupPrimitive` Tool.ts 인터페이스 준수 + 한국어 description |
| γ-2 | `SubmitPrimitive` 〃 |
| γ-3 | `VerifyPrimitive` 〃 |
| γ-4 | `SubscribePrimitive` 〃 |
| γ-5 | 4 primitive 모두 CC `FallbackPermissionRequest`를 권한 UI base로 사용 |
| γ-6 | adapter의 `real_domain_policy` 메타가 권한 UI에 직접 인용으로 노출 |
| γ-7 | `resolve_location` meta-tool은 `lookup`의 sub-mode로 통합 (이미 그렇게 되어 있음 — 검증만) |

**검증**: 시민이 "의정부 응급실 알려줘" → LLM이 `lookup(mode='fetch', tool_id='nmc_emergency_search', ...)` 호출 → `resolve_location` 사전 호출 → NMC 어댑터 실행 → 한국어 응답. End-to-end PTY smoke 통과.

### Phase δ — 백엔드 Python `src/kosmos/permissions/` 정리 (1 sprint)

**목표**: 프론트엔드에서 삭제한 KOSMOS-invented permission 시스템의 **백엔드 미러 25개 파일**도 같은 운명.

| Task | 작업 |
|---|---|
| δ-1 | `src/kosmos/permissions/modes.py` (5-mode PermissionMode), `models.py` (ConsentDecision, ToolPermissionContext, PermissionRule), `pipeline_v2.py`, `pipeline.py`, `prompt.py`, `rules.py`, `bypass.py`, `mode_bypass.py`, `mode_default.py`, `synthesis_guard.py`, `aal_backstop.py`, `killswitch.py` 등 KOSMOS-invented 파일 삭제 |
| δ-2 | adapter 모듈에서 `compute_permission_tier()` / `pipa_class` / `auth_level` import 제거 (10+ 파일) |
| δ-3 | `AdapterRealDomainPolicy` Pydantic 모델 신설 (research doc § 3.2) |
| δ-4 | adapter 메타데이터 마이그레이션 — 모든 12개 Live + 6개 mock에 `real_classification_url` + `last_verified` 부여 |
| δ-5 | `ledger.py`, `action_digest.py`, `hmac_key.py`, `canonical_json.py`, `audit_coupling.py` — 영수증 시스템은 보존 검토 (Spec 035 시민 영수증 ledger는 유효한 KOSMOS 추가) |

**검증**: pytest 회귀 0건. 모든 adapter가 citation URL 보유.

### Phase ε — 한국 정부 도메인 어댑터 정렬 (2 sprints)

**목표**: 12개 Live + 6개 mock 어댑터를 research 매트릭스에 맞춰 정렬.

| Task | 작업 |
|---|---|
| ε-1 | **삭제**: `mock_verify_digital_onepass` (서비스 종료 2025-12-30) |
| ε-2 | **추가**: `mock_verify_any_id_sso` (정부 통합인증 후속 stub) |
| ε-3 | **이전**: `mock_traffic_fine_pay_v1`, `mock_welfare_application_submit_v1` → `docs/scenarios/` |
| ε-4 | 모든 grade-3 mock에 "shape-mirror only" 명시적 disclaimer 추가 |
| ε-5 | 모든 mock 응답에 `_mode: "mock"` 투명성 필드 추가 |
| ε-6 | per-tool `ToolRateLimiter` 구현 (KOROAD/KMA/HIRA/NFA/MOHW/CBS = 10k, NMC = 1M) |
| ε-7 | 새 어댑터 doc template — "Real-domain policy" 섹션 + citation URL 필수 |

**검증**: CI 게이트 통과 — 모든 어댑터 citation URL 보유, byte-mirror grade-5 mock sort_keys-hash 결정성, scenario-only 도메인은 어댑터 파일 없음.

### Phase ζ — 시스템 프롬프트 재작성 (선택, 1 sprint)

**목표**: LLM이 5-primitive를 시민 친화적으로 사용하도록 system prompt 갱신.

| Task | 작업 |
|---|---|
| ζ-1 | `prompts/system_v1.md`에서 개발자 tool (Bash/Read/Write/Edit) 언급 삭제 |
| ζ-2 | 5-primitive (lookup/submit/verify/subscribe) 사용 가이드 추가 |
| ζ-3 | OPAQUE 도메인 인식 규칙 — "홈택스/정부24-submit/모바일ID/공동인증서/금융인증서/마이데이터-live는 도구 호출 X, 시민에게 hometax.go.kr/gov.kr 안내" |
| ζ-4 | 시민 친화 한국어 톤 가이드 — "공무원이 시민에게 안내하듯" |

**검증**: shadow-eval 워크플로우 (Spec 026)로 fixture-only 평가.

---

## 4. CC 원본을 토대로 한다는 것의 의미 — 명확한 정의

### 의미 1: byte-identical 보존 (CC가 검증한 것은 그대로)

다음은 **수정 없이** CC 원본 그대로 사용:

```
tui/src/components/permissions/PermissionPrompt.tsx       (335 LOC)
tui/src/components/permissions/PermissionRequest.tsx      (216 LOC)
tui/src/components/permissions/PermissionDialog.tsx       (71 LOC)
tui/src/components/permissions/PermissionExplanation.tsx  (271 LOC)
tui/src/components/permissions/FallbackPermissionRequest.tsx (332 LOC)
tui/src/components/permissions/PermissionRequestTitle.tsx (65 LOC)
tui/src/components/permissions/PermissionRuleExplanation.tsx (120 LOC)
tui/src/components/permissions/PermissionDecisionDebugInfo.tsx (459 LOC)
tui/src/components/permissions/SandboxPermissionRequest.tsx (162 LOC)
tui/src/components/permissions/AskUserQuestionPermissionRequest/ 전체
tui/src/components/permissions/EnterPlanModePermissionRequest/ 전체
tui/src/components/permissions/ExitPlanModePermissionRequest/ 전체
tui/src/components/permissions/SkillPermissionRequest/ 전체
tui/src/components/permissions/WebFetchPermissionRequest/ 전체
tui/src/components/permissions/ComputerUseApproval/ 전체
tui/src/components/permissions/rules/ 전체 (8개)
tui/src/components/permissions/{hooks,utils,shellPermissionHelpers,useShellPermissionFeedback,WorkerBadge,WorkerPendingPermission}.* 등
```

총 **35+ 파일**이 CC 원본과 동일.

### 의미 2: KOSMOS-original 발명물 삭제 (이미 Spec 1979에서 완료)

`permissions/` 디렉토리 전체 (25 KOSMOS-only 파일) — Spec 1979 Wave 1-3에서 삭제됨.

### 의미 3: CC tool 중 개발자 전용 12개 삭제 (Phase β)

상세는 §1.1 참조.

### 의미 4: 5-primitive를 CC Tool.ts 패턴으로 (Phase γ)

CC가 정의한 `Tool` 인터페이스 (name/description/inputSchema/call/render*) **그대로 따름**. 5-primitive는 그 인터페이스의 인스턴스일 뿐이며, 호출 시 백엔드 `src/kosmos/tools/<domain>/<adapter>.py` 로 IPC 라우팅.

### 의미 5: adapter는 real_domain_policy 인용으로만 권한 결정 (Phase δ)

adapter는 **권한 정책을 발명하지 않음**. 각 어댑터가 메타데이터로 명시:

```python
@dataclass
class KomaAdapter:
    real_domain_policy = AdapterRealDomainPolicy(
        domain_owner="KMA 기상청",
        real_classification_url="https://www.data.go.kr/data/15084084/openapi.do",
        citizen_facing_gate=CitizenGate(
            kind="none_developer_only",   # 시민 본인인증 X
            citation_url="...",
            description_ko="공공데이터 일반 공개 — 별도 동의 불필요",
        ),
        ...
    )
```

권한 UI는 이 메타를 읽어 **CC `<FallbackPermissionRequest>`** 또는 **CC `<PermissionPrompt>`** 에 그대로 dispatch. KOSMOS는 새 권한 컴포넌트를 만들지 않음.

---

## 5. 5분 ramp-up — 신규 학부생 기여자가 즉시 따라할 수 있는 절차

> "KOSMOS 어떻게 시작해요?" 라는 질문에 대한 정답.

1. **CC 원본 읽기** — `.references/claude-code-sourcemap/restored-src/` 클론본을 읽는다. 이게 토대.
2. **`tui/src/`와 비교** — 동일 경로의 KOSMOS 파일을 읽는다. 다르면 `diff` — 차이점이 SDK import 1-2줄이면 정상, 그 외 차이는 KOSMOS의 의도적 변경 (보존 가치 검증 필요).
3. **권한 UI 작성 시 확인** — `components/permissions/PermissionPrompt.tsx` (CC 원본) 그대로 사용. 새 권한 컴포넌트 만들지 말 것.
4. **Tool 추가 시 확인** — `tools/AgentTool/AgentTool.tsx` (CC 원본)의 `Tool` 인터페이스 따름.
5. **한국 정부 어댑터 추가 시 확인** — `src/kosmos/tools/koroad/koroad_accident_search.py`를 reference로 복사. `real_domain_policy` 메타에 citation URL 필수.
6. **개발자 도구를 시민에게 노출하지 말 것** — Bash/Read/Write/Edit/Grep/Glob/Notebook은 삭제 진행 중. 새로 import하지 말 것.
7. **OPAQUE 도메인은 시나리오 only** — 홈택스/정부24-submit/모바일ID/공동인증서/금융인증서/마이데이터-live는 어댑터 만들지 말고 `docs/scenarios/<domain>.md`로.

---

## 6. 위험 및 의존성

| 위험 | 완화책 |
|---|---|
| Phase β에서 CC tool 삭제 시 system prompt가 그 tool을 가리킴 → LLM이 존재하지 않는 tool 호출 | Phase β-6 — system prompt 동시 갱신 |
| Phase γ에서 5-primitive가 CC Tool.ts 인터페이스를 정확히 안 따르면 ToolRegistry가 라우팅 실패 | bun test에 `ToolRegistry.register()` 통과 검증 추가 |
| Phase δ 백엔드 정리 시 adapter 회귀 발생 | adapter 단위 테스트가 이미 존재, pytest 통과 보장 |
| Phase ε에서 grade-3 mock의 fixture가 실 API와 불일치 | shape_contract.md에 인용 URL 필수, CI가 검증 |
| 사용자 학습 곡선 — "왜 5-primitive로 다 모았어요?" | 본 문서 §5 ramp-up + `docs/vision.md`의 시민 use case 명확화 |

---

## 7. 다음 결정

본 마이그레이션 계획을 사용자가 승인하면:

1. **즉시 실행**: Phase α (CC 정합성 감사) — read-only, 위험 0, 산출물 명확
2. **차순위**: Phase β (개발자 tool 12개 삭제) — 위험 낮음, 시민 use case에 명백히 무의미
3. **3순위**: Phase γ (5-primitive Tool.ts 재정렬) — Phase α/β 의존
4. **차후**: Phase δ/ε/ζ — 별도 sprint

각 phase는 별도 PR + 별도 sub-issue로 분할 가능 (Spec 1979 후속 epic).

총 추정: **6 sprint** (~6-8 weeks Sonnet 단독 또는 ~3-4 weeks Lead+Teammates 병렬).

---

## 8. 본 문서의 위치

- **research basis**: `specs/1979-plugin-dx-tui-integration/domain-harness-design.md` (§1-§9 도메인 매트릭스 + 충실도 등급)
- **execution plan**: 본 문서 (CC 원본 단위 마이그레이션 경로)
- **canonical references**:
  - `docs/vision.md § Reference materials` (CC reference thesis)
  - `docs/requirements/kosmos-migration-tree.md` (L1 pillars + UI L2 + P0-P6)
  - `.references/claude-code-sourcemap/restored-src/` (CC 2.1.88 source-of-truth)

향후 모든 권한 UX, tool 추가, 어댑터 작성은 본 문서 + research design 문서 + CC 원본을 인용해야 함 (per `feedback_check_references_first`).
