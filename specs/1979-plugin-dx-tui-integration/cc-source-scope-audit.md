# CC 원본 소스 기반 스코프 감사 (3차 thesis 기준)

**Status**: 스코프 파악 산출물 (작업 시작 전)
**Date**: 2026-04-29
**Authority**: AGENTS.md § CORE THESIS (3차 정정 final) + `feedback_kosmos_is_ax_gateway_client.md` + `delegation-flow-design.md § 12`
**Trigger**: 사용자 요청 — "기존 cc 원본소스에서 어딜 추가하고 어딜 수정하고 어딜 마이그레이션해야하는지 스코프파악부터 해"

이 문서는 **작업 분류 + 의존성 그래프**입니다. 코드 변경 0건. 다음 단계 (Epic 발행 + 작업 진입)의 근거.

---

## 0. 한 표로 보는 결론

```
┌──────────────────────────────────────────────────────────────────────┐
│  TUI (1,884 CC files vs 2,090 KOSMOS files)                          │
│                                                                       │
│  ✅ KEEP (보존, 절대 수정 X)              1,604 files (85.1%)         │
│      ├─ byte-identical                       1,531                    │
│      └─ SDK import only diff                    73                    │
│                                                                       │
│  🔄 REVIEW (수정 검토 필요)                  212 files (11.3%)        │
│      ├─ services/ (Anthropic→FriendliAI 잔재)  44                     │
│      ├─ utils/ (i18n/theme 적용 등)            62                     │
│      ├─ components/ (한국어 UI)                29                     │
│      └─ 그 외                                  77                     │
│                                                                       │
│  ➕ KOSMOS-only ADDITIONS                    274 files (13.1%)        │
│      ├─ 인프라 디렉토리 (i18n/ipc/theme/...)   35  ← 절대 KEEP         │
│      ├─ 시민 중심 추가 (5-primitive/한국어)   233  ← 대부분 KEEP       │
│      └─ 검토 후 삭제 후보                       6                     │
│                                                                       │
│  ❌ DELETE (CC-only, 이미 삭제됨)            68 files (3.6%)          │
│      └─ 모두 의도적 (Anthropic 1P 잔재)                               │
│                                                                       │
│  🆕 MIGRATE (3차 thesis 신규 작업)         예상 50-80 files           │
│      ├─ 백엔드 permissions/ 정리                25 (삭제)             │
│      ├─ AdapterRealDomainPolicy 모델            1 (신규)              │
│      ├─ 18개 어댑터 메타 마이그레이션           18 (수정)             │
│      ├─ AX-infrastructure mock 어댑터          ~10 (신규)             │
│      ├─ Mock transparency 필드 일괄            ~18 (수정)             │
│      └─ 정책 매핑 문서                         1 (신규)               │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 1. TUI (`tui/src/`) — 5 카테고리 정밀 분류

### 1.1 ✅ KEEP — 1,604 파일 (절대 수정 X)

CC restored-src와 byte-identical (1,531) 또는 SDK import 1-2줄만 차이 (73). 이 파일들은 **CC가 검증한 것을 그대로 사용**하며, 수정 시 사용자 명시적 승인 필수.

대표 보존 영역:
- `query/` — agentic loop (CC 검증, 단 deps.ts는 modified 카테고리)
- `components/permissions/` — 35+ 권한 UI 파일 (Spec 1979 감사 결과 byte-identical)
- `components/messages/`, `components/PromptInput/` 대부분
- `services/skills/`, `services/mcp/`, `services/files/` 등 핵심 인프라
- `tools/AgentTool/`, `MCPTool/`, `TaskCreate/Get/List/Output/Stop/Update/`, `Skill*/`, `Schedule*/`, `Sleep*/` 등 31개 보존 tool
- `keybindings/` 핵심 (resolver, registry, validate, defaultBindings 등)
- `utils/` 대부분 (file ops, IME helpers, OS utilities)
- `screens/` 프롬프트/transcript 컴포넌트들 대부분

**작업 액션**: 0건. 단순히 CC 원본을 base로 인정.

### 1.2 🔄 REVIEW — 212 파일 (수정 카테고리)

CC와 차이 있음. 분류:

#### 1.2.1 services/ — 44 파일 (Spec 1633 잔재)
대부분 **Anthropic→FriendliAI swap**의 진행형. claude.ts 3419 LOC + 4 callsite 잔재 (`verifyApiKey`, `queryHaiku ×2`, `queryWithModel`).

| 파일 | 현재 상태 | 작업 |
|---|---|---|
| `services/api/claude.ts` | 3419 LOC, 4 callsite alive | **DELETE** (Spec 1633 closure) |
| `services/api/sonnet.ts`, `services/api/anthropic.ts` 등 | Anthropic 1P | **DELETE** |
| `services/skills/`, `services/files/`, `services/mcp/` | KOSMOS 변경 (i18n 적용 등) | **MINOR PATCH** — 수정 점 검증 |
| 그 외 ~30 파일 | 미세 변경 | **AUDIT** — 각각 검증 |

#### 1.2.2 utils/ — 62 파일 (i18n/theme/Korean IME 적용)
KOSMOS-specific 한국어 환경 통합 변경. 대부분 정당한 변경.

대표:
- `utils/markdown.ts`, `utils/format.ts` — 한국어 처리 추가
- `utils/keychain.ts`, `utils/secureStorage.ts` — 보안 storage 변경 (CC는 macOS keychain, KOSMOS는 file-based)
- `utils/model/` — K-EXAONE 단일 model로 변경
- `utils/permissions/` — Spec 033 잔재 (3차 thesis로 정리해야 함, 후속)

**작업**: minor audit — 변경의 정당성 검증. 대부분 KEEP.

#### 1.2.3 components/ — 29 파일 (한국어 UI 적용)
- `components/Splash.tsx`, `components/Logo.tsx` — KOSMOS 브랜딩 (UFO 마스코트, 보라색 #a78bfa)
- `components/messages/` — 한국어 톤 적용
- `components/PromptInput/` — 한국어 IME 통합

**작업**: 정당한 변경, KEEP. 단 일부 변경은 문서화 필요.

#### 1.2.4 commands/ — 13 파일
- `commands/help.tsx` 등 — 한국어 적용
- `commands/permissions/` — Spec 033 잔재 정리 후속 (이미 일부 삭제됨)

**작업**: minor — Spec 033 잔재 추가 정리 필요.

#### 1.2.5 tools/ — 9 파일
- `tools/Tool.ts` — Tool 인터페이스 (KOSMOS minor adjustment)
- `tools/tools.ts` — 등록 로직
- 기타

**작업**: 3차 thesis가 정확히 영향 — 5-primitive를 CC Tool.ts 인터페이스에 정확히 align (Phase γ).

#### 1.2.6 그 외 (hooks/keybindings/bridge/constants/types 등)
**작업**: case-by-case audit. 대부분 KOSMOS 정당한 변경.

### 1.3 ➕ KOSMOS-only ADDITIONS — 274 파일

#### 1.3.1 인프라 디렉토리 (35 files) — 절대 KEEP
- `i18n/` (5) — 한국어 메시지 카탈로그
- `ipc/` (14) — KOSMOS Python backend bridge (Spec 032)
- `observability/` (1) — OTEL 확장
- `ssh/` (2) — SSH session (Spec 287)
- `store/` (2) — session-store (Spec 2077 호환)
- `stubs/` (6) — bun-bundle.ts 등 SDK shim
- `theme/` (5) — KOSMOS 보라색 + UFO 토큰 (Spec 035)

**작업**: 0건. 모두 KEEP.

#### 1.3.2 components/ (64 files) — 시민 중심 UI
- `components/onboarding/` — Korean onboarding 5-step (Spec 035)
- `components/plugins/` — Plugin 브라우저/install flow (Spec 1979)
- `components/agents/` — 부처 agent panel (Spec 027)
- `components/coordinator/` — Spec 2077 (이번 1979 Wave 2에서 일부 정리됨)
- `components/help/` — HelpV2 한국어
- `components/config/` — `/config` overlay
- `components/export/` — `/export` PDF (Spec 1635)
- `components/history/` — `/history` search overlay (Spec 288)
- `components/messages/{ContextQuoteBlock,Banner,...}` — 한국어 UI

**작업**: KEEP. 단 일부 (kosmosPendingConsent dead state) 정리 후속.

#### 1.3.3 commands/ (46 files) — 한국어 slash commands
- `/onboarding`, `/plugin`, `/plugins`, `/export`, `/consent`, `/agents`, `/help` 등 KOSMOS 추가

**작업**: KEEP. 일부는 3차 thesis로 mock 어댑터 호출 wiring 추가 필요.

#### 1.3.4 tools/ (30 files) — 시민 중심 도구
- 5-primitive (LookupPrimitive/SubmitPrimitive/VerifyPrimitive/SubscribePrimitive)
- 시민 보조: CalculatorTool, DateParserTool, TranslateTool, ExportPDFTool — kosmos-migration-tree § C.6 MVP 7
- 검토 후 삭제 후보 6개:
  - `MonitorTool` — KOSMOS-original, 시민 use case 불명확
  - `ReviewArtifactTool` — 개발자 use case
  - `SuggestBackgroundPRTool` — 개발자 use case
  - `TungstenTool` — 불명
  - `VerifyPlanExecutionTool` — 개발자 use case
  - `WorkflowTool` — 검토 필요

**작업**: 24 KEEP + 6 검토 후 삭제 후보.

#### 1.3.5 그 외 KOSMOS-only
- `keybindings/` 12 (한국어 IME, hangul search, tier1 handlers)
- `schemas/ui-l2/` 8 (UI L2 Pydantic-equivalent Zod schemas)
- `types/`, `services/`, `hooks/` 등 — Korean 환경 통합

**작업**: 모두 KEEP. 일부 schemas/ui-l2/permission.ts 같은 Spec 033 잔재는 정리 검토.

### 1.4 ❌ CC-only DELETE — 68 파일 (이미 의도적 삭제)

| 카테고리 | 파일 수 | 삭제 사유 |
|---|---|---|
| `utils/teleport/`, `utils/secureStorage/` 등 | 23 | Anthropic 1P (claude.ai sync, macOS keychain, telemetry) |
| `services/api/bootstrap.ts`, `services/oauth/`, `services/policyLimits/`, `services/remoteManagedSettings/`, `services/rateLimitMocking.ts`, `services/mockRateLimits.ts`, `services/claudeAiLimitsHook.ts`, `services/analytics/datadog.ts` | 16 | claude.ai 인증/결제/통계 (KOSMOS = K-EXAONE) |
| `migrations/` | 11 | Anthropic 모델 migration (Sonnet45→46, Opus1m→Sonnet45 등) — KOSMOS는 K-EXAONE 단일 |
| `remote/` (SessionsWebSocket, RemoteSessionManager 등) | 4 | Anthropic 원격 세션 (KOSMOS는 local만) |
| `tools/AgentTool/built-in/{planAgent,claudeCodeGuideAgent,verificationAgent,exploreAgent}` | 4 | Anthropic 사내 agent (KOSMOS는 한국 부처 agent) |
| `commands/login/`, `commands/logout/` | 4 | claude.ai 인증 (KOSMOS = K-EXAONE FriendliAI Tier 1) |
| `constants/oauth.ts`, `constants/betas.ts` | 2 | Anthropic 1P |
| `components/{TeleportResumeWrapper,grove/Grove}.tsx`, `hooks/useTeleportResume.tsx` | 3 | Teleport (claude.ai sync) |
| `types/generated/events_mono/.../auth.ts` | 1 | Anthropic 1P telemetry |

**작업**: 0건. 모두 의도적, KOSMOS-irrelevant.

### 1.5 🆕 MIGRATE (3차 thesis 신규 작업)

3차 thesis (AX-infrastructure callable-channel client)에 맞춰 추가/수정해야 할 영역:

| Task | 파일 | 액션 |
|---|---|---|
| M-1 | `tui/src/schemas/ui-l2/permission.ts` | Spec 033 잔재 검토 후 정리 또는 KEEP (UI 색상용) |
| M-2 | (검토 후 삭제 후보 6 tool — 위 1.3.4) | DELETE 검토 |
| M-3 | (KOSMOS Modified utils/permissions 잔재) | Spec 033 정리 |
| M-4 | system prompt 갱신 (`prompts/system_v1.md` Python backend) | 5-primitive citizen UX + OPAQUE hand-off rule |

---

## 2. Backend Python (`src/kosmos/`) — 카테고리별 분류

### 2.1 디렉토리별 통계
- 19 디렉토리, 259 .py files
- KOSMOS-original full (CC 대응 없음)

### 2.2 KEEP — 보존 영역
- `agents/`, `cli/`, `config/`, `context/`, `engine/`, `eval/`, `ipc/`, `llm/`, `memdir/`, `observability/`, `recovery/`, `safety/`, `security/`, `session/`, `_canonical/` — KOSMOS 인프라, 보존
- `tools/koroad/`, `tools/kma/`, `tools/hira/`, `tools/nmc/`, `tools/nfa119/`, `tools/ssis/` — 12 Live 어댑터 (Phase 1 작품)
- `tools/geocoding/` — resolve_location meta
- `primitives/` — submit/subscribe/verify (lookup은 tools/lookup.py)

### 2.3 🆕 MIGRATE — 3차 thesis 적용

#### 2.3.1 `permissions/` (25개 파일) — KOSMOS-original Spec 033 인프라
TUI에서 이미 삭제됨 (Wave 1-3). 백엔드 동일하게 정리:

| 파일 | 작업 |
|---|---|
| `modes.py` (PermissionMode 5-mode) | DELETE |
| `models.py` (ConsentDecision, ToolPermissionContext, PermissionRule) | DELETE / 일부 schema 보존 검토 |
| `pipeline_v2.py`, `pipeline.py`, `prompt.py`, `rules.py` | DELETE |
| `bypass.py`, `mode_bypass.py`, `mode_default.py` | DELETE |
| `synthesis_guard.py`, `aal_backstop.py`, `killswitch.py` | DELETE (Spec 033 발명물) |
| `cli.py`, `session_boot.py` | DELETE / 검토 |
| `ledger.py`, `action_digest.py`, `hmac_key.py`, `canonical_json.py`, `audit_coupling.py`, `ledger_verify.py` | **부분 보존 검토** — Spec 035 영수증 ledger는 시민 use case 유효 |
| `adapter_metadata.py`, `credentials.py` | 검토 |
| `otel_emit.py`, `otel_integration.py` | KEEP (OTEL 인프라) |
| `steps/` | 검토 |

**작업**: 25개 중 ~20개 DELETE, ~5개 KEEP/부분 보존.

#### 2.3.2 어댑터 메타 마이그레이션 (`tools/models.py` + 18 어댑터)

`GovAPITool` 모델에서 KOSMOS-invented 필드 제거 + `AdapterRealDomainPolicy` citation 추가:

| 변경 | 작업 |
|---|---|
| `auth_level` 필드 제거 | DELETE field |
| `pipa_class` 필드 제거 | DELETE field |
| `is_personal_data` 제거 | DELETE field |
| `dpa_reference` 제거 | DELETE field |
| `is_irreversible` 제거 | DELETE field |
| `requires_auth` 제거 | DELETE field |
| `real_classification_url` 추가 | NEW field (HttpUrl) |
| `real_classification_text` 추가 | NEW field (str) |
| `citizen_facing_gate` 추가 | NEW field (Literal enum) |
| `last_verified` 추가 | NEW field (date) |
| 18개 어댑터 (12 Live + 6 mock) 메타 마이그레이션 | UPDATE 18 files |

**작업**: 1 model 수정 + 18 어댑터 마이그레이션.

#### 2.3.3 신규 mock 어댑터 (3차 thesis AX-infrastructure callable-channel reference shape)

새 mock — Singapore APEX + 공공마이데이터 패턴 base:

| 어댑터 | 카테고리 | LOC 추정 | 우선순위 |
|---|---|---|---|
| `mock_verify_module_simple_auth` (간편인증 LLM-callable) | verify | ~150 | High |
| `mock_verify_module_modid` (모바일신분증 LLM-callable) | verify | ~150 | High |
| `mock_verify_module_kec` (공동인증서 LLM-callable) | verify | ~150 | Medium |
| `mock_verify_module_geumyung` (금융인증서 LLM-callable) | verify | ~150 | Medium |
| `mock_submit_module_hometax_taxreturn` | submit | ~100 | High |
| `mock_submit_module_gov24_minwon` | submit | ~100 | High |
| `mock_submit_module_public_mydata_action` | submit | ~100 | Medium |
| `mock_lookup_module_hometax_simplified` | lookup | ~100 | Medium |
| `mock_lookup_module_gov24_certificate` | lookup | ~80 | Medium |
| `src/kosmos/primitives/delegation.py` (DelegationToken + DelegationContext) | schema | ~80 | High |

**작업**: 9 mock 어댑터 + 1 schema 모듈 신설. 약 ~1,160 LOC.

#### 2.3.4 Mock transparency 필드 일괄 적용

기존 6 mock + 신규 9 mock = 15 mock 모두 다음 필드 응답:
```python
{
  "_mode": "mock",
  "_reference_implementation": "ax-infrastructure-callable-channel",
  "_actual_endpoint_when_live": "...",
  "_security_wrapping_pattern": "OAuth2.1 + mTLS + scope=...",
  "_policy_authority": "국가AI전략위원회 행동계획 2026-2028 §공공AX",
  "_international_reference": "Singapore APEX",
}
```

**작업**: 15 mock 어댑터 수정 (small patch each).

#### 2.3.5 ToolRateLimiter (research finding #9)

per-tool-id 쿼터 (`KOROAD/KMA/HIRA/NFA/MOHW/CBS = 10k/일`, `NMC E-GEN = 1M/일`):

**작업**: `src/kosmos/tools/rate_limiter.py` 이미 존재 — 검토 후 per-tool-id 인덱싱 확인/수정.

#### 2.3.6 어댑터 정리

| 어댑터 | 작업 |
|---|---|
| `mock_verify_digital_onepass.py` | DELETE (서비스 종료 2025-12-30) |
| `mock_verify_any_id_sso.py` | NEW (디지털원패스 후속 stub) |
| `mock_traffic_fine_pay_v1.py` | 이전 또는 transparency 필드 추가 |
| `mock_welfare_application_submit_v1.py` | 이전 또는 transparency 필드 추가 |

---

## 3. Phase 별 실행 sequence

### Phase α — CC parity audit (read-only, 1 sprint, 위험 0)
**목표**: 1,604 KEEP 파일이 진짜 byte-identical인지 spot-check + Modified 212 파일의 변경 정당성 audit.

**산출물**: `cc-parity-audit.md` — 변경 정당성 OK / 의심 / 정리 필요 분류.

**위험**: 0 (read-only).

### Phase β — KOSMOS-original UI 정리 마무리 (1 sprint)
이미 Spec 1979 Wave 1-3에서 대부분 처리됨. 잔재:
- `tui/src/schemas/ui-l2/permission.ts` — Spec 033 PermissionDecisionT/PermissionLayerT 잔재 검토
- `tui/src/utils/permissions/` (있다면) — 검토 후 정리
- 6 KOSMOS-only 검토 삭제 후보 (Monitor/ReviewArtifact/SuggestBackgroundPR/Tungsten/VerifyPlanExecution/Workflow)

**산출물**: 정리 commit.

**위험**: 낮음.

### Phase γ — 5-primitive를 CC Tool.ts 정확 align (2 sprints)
3차 thesis 핵심. 5-primitive Tool 인터페이스 정확히 CC pattern 따름:

```typescript
// CC pattern (tools/AgentTool/AgentTool.tsx 참조)
export const LookupPrimitive: Tool = {
  name, description, inputSchema, isReadOnly, isMcp, validateInput,
  call: async function* (...) { ... },
  renderToolUseMessage, renderToolResultMessage,
}
```

**작업**: 4 primitive (Lookup/Submit/Verify/Subscribe) refactor + ToolRegistry 검증.

**위험**: 중간.

### Phase δ — 백엔드 permissions/ 정리 + AdapterRealDomainPolicy (1 sprint)
- `src/kosmos/permissions/` 25 파일 정리 (~20 DELETE, 5 KEEP/부분)
- `AdapterRealDomainPolicy` Pydantic 모델 신설 (`src/kosmos/tools/models.py` 수정)
- 18 어댑터 메타 마이그레이션 (KOSMOS-invented 필드 → citation_url)

**위험**: 낮음 (이미 frontend에서 해본 패턴).

### Phase ε — AX-infrastructure mock 어댑터 신설 (2 sprints)
3차 thesis 핵심 — Singapore APEX + 공공마이데이터 base mock 신설:
- `src/kosmos/primitives/delegation.py` (DelegationToken/Context schema)
- 9 신규 mock 어댑터 (verify modules + submit modules + lookup modules)
- 모든 15 mock에 transparency 필드 일괄
- digital_onepass 삭제 + any_id_sso 추가

**위험**: 낮음 (mock-only, 외부 의존 X).

### Phase ζ — End-to-end smoke + 정책 매핑 (1 sprint)
- PTY scenario: 시민 "종합소득세 신고" → verify → lookup → submit → 접수번호
- `docs/research/policy-mapping.md` 신설 — KOSMOS adapter ↔ Singapore APEX/X-Road/EUDI/마이나 매핑 표

**위험**: 낮음.

### Phase η — System prompt 갱신 (선택, 1 sprint)
- `prompts/system_v1.md`에서 개발자 tool 언급 삭제
- 5-primitive citizen UX 가이드 추가
- OPAQUE 도메인 hand-off 규칙
- 한국어 시민 친화 톤

**위험**: 낮음 (shadow-eval로 검증).

### 총 추정
6-8 sprints (Sonnet 단독) / 3-4 sprints (Lead+Teammates 병렬).

---

## 4. 의존성 그래프

```
Phase α (CC parity) ──────┐
                          ▼
Phase β (UI 잔재 정리) ───┐
                          ▼
Phase δ (백엔드 정리) ────┐
                          ▼
Phase γ (5-primitive align) ──┐
                              ▼
Phase ε (AX mock) ────────────┐
                              ▼
Phase ζ (E2E smoke + 정책 매핑)
                              ▼
Phase η (system prompt, 선택)
```

α/β는 병렬 가능. δ는 γ 의존. ε는 δ + γ 의존 (DelegationToken은 γ의 5-primitive 인터페이스 사용).

---

## 5. 위험 인벤토리

| 위험 | 영향 | 완화 |
|---|---|---|
| Phase α에서 modified 212 파일 중 잘못된 KOSMOS 변경 발견 | 작업 양 증가 | spot-check, 의심 파일만 정밀 audit |
| Phase γ에서 5-primitive 변경이 ToolRegistry boot 깨뜨림 | 회귀 | bun test + uv pytest 통과 보장 |
| Phase δ에서 permissions/ 삭제 시 어댑터 import 깨짐 | 회귀 | 사전 import 그래프 매핑, 단계적 삭제 |
| Phase ε에서 mock fixture가 실 reference (Singapore APEX) 와 불일치 | 정책 reference 신뢰성 저하 | shape_contract.md에 citation 필수, CI 검증 |
| 사용자가 또 정정 (4차) | 작업 폐기 | 본 문서를 사용자에게 검토 요청, 진입 전 합의 |

---

## 6. KEEP 파일 리스트 (보존 의무) — Top categories

다음 파일/디렉토리는 **CC 원본의 byte-identical 보존을 위해 절대 수정 금지**:

```
tui/src/components/permissions/PermissionPrompt.tsx
tui/src/components/permissions/PermissionRequest.tsx
tui/src/components/permissions/PermissionDialog.tsx
tui/src/components/permissions/PermissionExplanation.tsx
tui/src/components/permissions/FallbackPermissionRequest.tsx
tui/src/components/permissions/SandboxPermissionRequest.tsx
tui/src/components/permissions/AskUserQuestionPermissionRequest/
tui/src/components/permissions/EnterPlanModePermissionRequest/
tui/src/components/permissions/ExitPlanModePermissionRequest/
tui/src/components/permissions/SkillPermissionRequest/
tui/src/components/permissions/WebFetchPermissionRequest/
tui/src/components/permissions/ComputerUseApproval/
tui/src/components/permissions/rules/ (8 files)
tui/src/components/permissions/{hooks,utils,shellPermissionHelpers,...}.*
tui/src/query/ (대부분, Spec 2077 관련 modified 제외)
tui/src/keybindings/ (대부분, KOSMOS-only 제외)
tui/src/services/skills/, services/mcp/, services/files/
tui/src/tools/AgentTool/, MCPTool/, TaskCreate.../TaskUpdate/, Skill*/, Schedule*/, Sleep*/, EnterPlanMode/, ExitPlanMode/, EnterWorktree/, ExitWorktree/, ToolSearch/, AskUserQuestion/, RemoteTrigger/, SyntheticOutput/, ConfigTool/, Brief/
tui/src/screens/ (대부분, REPL.tsx 제외)
```

---

## 7. ADD 파일 리스트 (신규 작성)

### Phase ε (AX-infrastructure mock) 신규:
```
src/kosmos/primitives/delegation.py                                     (~80 LOC)
src/kosmos/tools/mock/verify_module_simple_auth.py                      (~150)
src/kosmos/tools/mock/verify_module_modid.py                            (~150)
src/kosmos/tools/mock/verify_module_kec.py                              (~150)
src/kosmos/tools/mock/verify_module_geumyung.py                         (~150)
src/kosmos/tools/mock/verify_module_any_id_sso.py                       (~120) [디지털원패스 후속]
src/kosmos/tools/mock/submit_module_hometax_taxreturn.py                (~100)
src/kosmos/tools/mock/submit_module_gov24_minwon.py                     (~100)
src/kosmos/tools/mock/submit_module_public_mydata_action.py             (~100)
src/kosmos/tools/mock/lookup_module_hometax_simplified.py               (~100)
src/kosmos/tools/mock/lookup_module_gov24_certificate.py                (~80)
docs/research/policy-mapping.md                                         (~200 LOC)
docs/scenarios/hometax-tax-filing.md                                    (~50)
docs/scenarios/gov24-minwon-submit.md                                   (~50)
docs/scenarios/mobile-id-issuance.md                                    (~30)
docs/scenarios/kec-yessign-signing.md                                   (~30)
docs/scenarios/mydata-live.md                                           (~50)
```

총 ~1,720 LOC 신규.

---

## 8. DELETE 파일 리스트 (예정)

### Phase β (UI 잔재):
```
tui/src/schemas/ui-l2/permission.ts (Spec 033 PermissionDecisionT/Layer 잔재 — 검토 후)
tui/src/tools/MonitorTool/, ReviewArtifactTool/, SuggestBackgroundPRTool/, TungstenTool/, VerifyPlanExecutionTool/, WorkflowTool/  [검토 후]
tui/src/utils/permissions/ 잔재 (있다면)
```

### Phase δ (백엔드 정리):
```
src/kosmos/permissions/modes.py
src/kosmos/permissions/models.py (ConsentDecision/PermissionRule)
src/kosmos/permissions/pipeline.py
src/kosmos/permissions/pipeline_v2.py
src/kosmos/permissions/prompt.py
src/kosmos/permissions/rules.py
src/kosmos/permissions/bypass.py
src/kosmos/permissions/mode_bypass.py
src/kosmos/permissions/mode_default.py
src/kosmos/permissions/synthesis_guard.py
src/kosmos/permissions/aal_backstop.py
src/kosmos/permissions/killswitch.py
src/kosmos/permissions/cli.py (검토)
src/kosmos/permissions/adapter_metadata.py (검토)
src/kosmos/permissions/credentials.py (검토)
src/kosmos/permissions/session_boot.py (검토)
src/kosmos/permissions/steps/ (검토)
src/kosmos/tools/mock/verify_digital_onepass.py [서비스 종료]
```

### 보존 (Spec 035 영수증 ledger):
```
src/kosmos/permissions/ledger.py        # 시민 영수증 (KEEP)
src/kosmos/permissions/action_digest.py # 영수증 hash (KEEP)
src/kosmos/permissions/hmac_key.py      # 영수증 HMAC (KEEP)
src/kosmos/permissions/canonical_json.py # JSON canonicalize (KEEP)
src/kosmos/permissions/audit_coupling.py # 영수증 ↔ 어댑터 coupling (KEEP)
src/kosmos/permissions/ledger_verify.py  # 영수증 무결성 (KEEP)
src/kosmos/permissions/otel_emit.py      # OTEL (KEEP)
src/kosmos/permissions/otel_integration.py (KEEP)
```

---

## 9. MODIFY 파일 리스트 (수정 점)

### Phase α 우선:
- 212 modified 파일 spot-check (각각 정당성 확인)
- 의심 파일만 정밀 audit

### Phase γ:
- `tui/src/tools/LookupPrimitive/*` (4 파일)
- `tui/src/tools/SubmitPrimitive/*` (4 파일)
- `tui/src/tools/VerifyPrimitive/*` (4 파일)
- `tui/src/tools/SubscribePrimitive/*` (4 파일)
- `tui/src/tools/Tool.ts` (인터페이스 minor adjust)
- `tui/src/tools/tools.ts` (등록 로직)

### Phase δ:
- `src/kosmos/tools/models.py` — `GovAPITool` 모델 6 필드 제거 + 4 필드 추가
- `src/kosmos/tools/koroad/{accident_search,accident_hazard_search,code_tables}.py` (3)
- `src/kosmos/tools/kma/{forecast_fetch,kma_*}.py` (8)
- `src/kosmos/tools/hira/hospital_search.py` (1)
- `src/kosmos/tools/nmc/{emergency_search,freshness}.py` (2)
- `src/kosmos/tools/nfa119/emergency_info_service.py` (1)
- `src/kosmos/tools/ssis/{codes,welfare_eligibility_search}.py` (2)
- 6 mock 어댑터 (`verify_*.py` 외) (6)

### Phase ε:
- 15 mock 어댑터 transparency 필드 일괄 (15)

### Phase η (선택):
- `prompts/system_v1.md` (1)

---

## 10. 다음 결정 (사용자)

본 스코프 감사 결과:
- ✅ **KEEP 1,604 파일** — CC 원본 byte-identical 보존
- 🔄 **REVIEW 212 파일** — Phase α에서 정당성 검증
- ➕ **ADD 274 파일 보존 + 신규 ~17 파일** — KOSMOS infrastructure + 시민 도구 + 3차 thesis mock
- ❌ **DELETE 68 파일 (이미)** + **추가 25-30 파일** — Anthropic 1P + Spec 033 백엔드 잔재
- 🆕 **MIGRATE ~50 파일** — 어댑터 메타 + transparency 필드 + system prompt

**제안**:
1. **본 문서를 사용자가 검토** — 분류 매트릭스 + Phase 순서가 의도와 일치하는지 확인
2. **Epic 발행** — "AX Infrastructure Caller Refactor (Phase α-η)" Initiative #1631 하위 신규 epic
3. **즉시 진입 가능** — Phase α (CC parity audit, read-only 위험 0)

본 문서 자체는 코드 변경 0건. 다음 단계 진입 결정은 사용자 승인 후.
