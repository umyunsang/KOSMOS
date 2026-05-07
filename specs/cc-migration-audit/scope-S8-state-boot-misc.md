# S8 — State / Boot / Misc 감사 (CC → UMMAYA 마이그레이션)

> **Auditor**: Opus S8 (병렬 9-agent 중 1)
> **Scope**: bootstrap, cli, entrypoints, setup.ts, main.tsx, memdir, state, context, context.ts, history.ts, migrations, projectOnboardingState.ts, voice, buddy, plugins, constants, schemas, types, i18n
> **Date**: 2026-05-03
> **CC source-of-truth**: `.references/claude-code-sourcemap/restored-src/src/` (2.1.88)
> **UMMAYA target**: `tui/src/` + `src/ummaya/`
> **Frame of reference**: UMMAYA = CC + 2 swaps (LLM=K-EXAONE on FriendliAI, Tool=한국 부처 GovAPITool). S8 슬라이스는 swap 외 영역 — **대부분 PRESERVE-IDENTICAL** 이어야 정상.

---

## 0. 4-Bucket 분류 정의 (S1 prompt 와 동일)

| Bucket | 의미 | 정당성 |
|---|---|---|
| **A. PRESERVE-IDENTICAL** | CC 와 byte-identical (또는 오직 sdk-compat 경로 한 줄만 변경) | swap 무관 — 정상 |
| **B. PRESERVE-WITH-DELETION-justified** | CC 의 일부 코드 블록이 삭제됨, 단 삭제는 명시적인 swap 종속물 (Anthropic 1P / claude.ai / 결제 / growthbook / feature-flag dead) | Spec 1633 / 2293 / 2521 cite |
| **C. UMMAYA-ORIGINAL-justified** | UMMAYA-only 신규 파일, swap 종속물 (i18n, brand, GovAPI, 5-step onboarding, K-EXAONE) | UI L2 / L1-B/C cite |
| **D. REGRESSION** | 정당화 안 된 발산 — 의도치 않은 stub, 미완 마이그레이션, swap 무관 부분에서 기능 손실 | **수정 필요** |

---

## 1. 파일 census 결과

### 1.1 CC 슬라이스 파일 수 (S8 전체)

```
bootstrap/                  1
cli/                        7  (+ handlers/6 + transports/7)
entrypoints/                5  (+ sdk/3)
setup.ts                    1
main.tsx                    1
memdir/                     8
state/                      6
context/                    9
context.ts                  1
history.ts                  1
migrations/                11
projectOnboardingState.ts   1
voice/                      1
buddy/                      6
plugins/                    1  (+ bundled/1)
constants/                 21
schemas/                    1
types/                      7  (+ generated/3)
i18n/                       0  (CC 에 없음)
─────────────────────────────
total                     ~108 .ts/.tsx 파일
```

### 1.2 UMMAYA 슬라이스 차이

| Group | CC 개수 | UMMAYA 개수 | 비고 |
|---|---|---|---|
| bootstrap | 1 | 1 | 매핑 1:1 |
| cli (top-level) | 7 | 6 | **`print.ts` 누락** (Spec 1633 명시 삭제 — main.tsx L1960 가 차단 메시지로 대체) |
| cli/handlers | 6 | 6 | 매핑 1:1 |
| cli/transports | 7 | 8 | UMMAYA-only `Transport.ts` (인터페이스 추출, +1) |
| entrypoints | 5 | 6 | UMMAYA-only `envGuard.ts` (Spec 1633 fail-closed FRIENDLI_API_KEY 게이트) |
| entrypoints/sdk | 3 | 9 | UMMAYA-only `controlTypes.ts`/`coreTypes.generated.ts`/`runtimeTypes.ts`/`sdkUtilityTypes.ts`/`settingsTypes.generated.ts`/`toolTypes.ts` (+6) |
| memdir | 8 | 11 | UMMAYA-only `consent.ts`/`io.ts`/`ministry-scope.ts` (+3, UI L2 동의 영수증) |
| state | 6 | 6 | 매핑 1:1 |
| context | 9 | 10 | UMMAYA-only `PermissionReceiptContext.tsx` (+1, UI L2 영수증) |
| migrations | 11 | 0 | **전체 삭제** — 모두 Anthropic 모델/설정 마이그레이션 (Sonnet45→46, Opus, Fennec 등). main.tsx L181-185 명시 |
| voice | 1 | 1 | 매핑 1:1 |
| buddy | 6 | 6 | 매핑 1:1 |
| plugins | 2 | 2 | 매핑 1:1 |
| constants | 21 | 21 (≈) | UMMAYA `oauth.ts` 누락 (CC 에는 있음) — UMMAYA-only `querySource.ts` (+1) |
| schemas | 1 | 1+ui-l2/8 | UI L2 schemas 신규 (a11y, agent, error, onboarding, permission, slash-command, ufo) |
| types | 7 | 16 | UMMAYA-only `connectorText.ts`/`fileSuggestion.ts`/`message.ts`/`messageQueueTypes.ts`/`notebook.ts`/`statusLine.ts`/`tools.ts`/`utils.ts` (+8 — CC 에서는 다른 위치에 흩어져 있던 type 들을 이 디렉토리로 통합한 변형으로 추정) |
| types/generated | 3 | 3 | 매핑 1:1 (단, **content 가 stub** — 아래 D. 회귀) |
| i18n | 0 | 5 | **UMMAYA-ORIGINAL** (한국어 primary, swap 종속 정당) |
| Python `src/ummaya/{memdir,observability,permissions,security}` | N/A | 30 + .py | **UMMAYA-ORIGINAL** (백엔드 스택 — swap 의 server-side 대응) |

---

## 2. 4-Bucket 분류 결과 (요약 카운트)

| Bucket | 파일 수 | 비율 |
|---|---|---|
| **A. PRESERVE-IDENTICAL** | 56 | 52% |
| **B. PRESERVE-WITH-DELETION-justified** | 24 | 22% |
| **C. UMMAYA-ORIGINAL-justified** | 24 | 22% |
| **D. REGRESSION** | 4 | 4% |
| **합계** | 108 | — |

### 2.1 Bucket A — PRESERVE-IDENTICAL (byte-identical)

확인된 SHA-256 hash 일치 (확인된 sample):

| 파일 | SHA-256 |
|---|---|
| `context.ts` (189 LOC) | `5d40784d…b1789b` ✓ |
| `history.ts` (464 LOC) | `10277fdf…48ba2` ✓ |
| `projectOnboardingState.ts` (83 LOC) | `8ae2abb4…71713e` ✓ |

`diff -q` empty 인 파일 (전체 byte-identical):

```
state/{AppStateStore.ts, onChangeAppState.ts, selectors.ts, store.ts, teammateViewHelpers.ts}        (5)
context/*  (전체 9 파일)                                                                              (9)
buddy/*    (전체 6 파일)                                                                              (6)
voice/voiceModeEnabled.ts                                                                             (1)
plugins/{builtinPlugins.ts, bundled/index.ts}                                                         (2)
memdir/* (전체 8 파일)                                                                                (8)
schemas/hooks.ts                                                                                      (1)
types/{hooks.ts, ids.ts, plugin.ts}                                                                   (3)
constants/{apiLimits.ts, common.ts, cyberRiskInstruction.ts, errorIds.ts, files.ts, github-app.ts,
           keys.ts, outputStyles.ts, product.ts, spinnerVerbs.ts, system.ts, systemPromptSections.ts,
           toolLimits.ts, turnCompletionVerbs.ts}                                                     (14)
cli/{exit.ts, ndjsonSafeStringify.ts, remoteIO.ts, structuredIO.ts}                                   (4)
cli/handlers/{agents.ts, mcp.tsx, plugins.ts, util.tsx}                                               (4)
cli/transports/{ccrClient.ts, HybridTransport.ts, SerialBatchEventUploader.ts,
                SSETransport.ts, transportUtils.ts, WebSocketTransport.ts, WorkerStateUploader.ts}    (7)
entrypoints/{mcp.ts, sandboxTypes.ts, sdk/controlSchemas.ts, sdk/coreTypes.ts}                        (4)
─────────────────────────────────────────────────────────────────────────────────
                                                                                              합계 56 ✓
```

추가 byte-near-identical (1-2 줄, sdk-compat 경로 alias 만):
- `bootstrap/state.ts` — 1 line: `'@anthropic-ai/sdk/...'` → `'src/sdk-compat.js'`
- `types/{command.ts, permissions.ts, textInputTypes.ts}` — 동일 alias 1줄
- `state/AppState.tsx` — 2 lines: `useEffectEvent` → `useCallback` (React 19 hook 미사용 호환)

이들은 **A bucket** 으로 분류 (sdk-compat alias 는 Spec 1633 의 dependency-removal swap 종속).

### 2.2 Bucket B — PRESERVE-WITH-DELETION-justified

| 파일 | 삭제된 내용 | 정당성 |
|---|---|---|
| `setup.ts` | 46 lines: `tengu_started`/`tengu_exit` analytics 이벤트 + `prefetchApiKeyFromApiKeyHelperIfSafe` (Anthropic OAuth) | Spec 1633 P1 (analytics + claude.ai OAuth dead) |
| `main.tsx` | **1917 lines** (4683→2766, 41% 감소): `feature()` 게이트 61개 전부 삭제, `logManagedSettings`/`logSessionTelemetry`/`getCertEnvVarTelemetry`/`KAIROS`/`COORDINATOR_MODE`/`DIRECT_CONNECT`/`SSH_REMOTE`/`TRANSCRIPT_CLASSIFIER` 분기 모두 제거. claude.ai MCP fetch / fileDownload / sessionDataUploader 무력화 | Spec 1633 P1 + P2 cite (단, **D-1 회귀 의심** — 아래 4.1 참조) |
| `entrypoints/cli.tsx` | +69 lines (boot tracer 삽입 only — CC 코드 100% 보존) | Spec 1978 T003 디버그 인프라 (UMMAYA-ORIGINAL 추가, CC 본체 무손실) |
| `entrypoints/init.ts` | `policyLimits` + `remoteManagedSettings` import → no-op stub | Spec 1633 P1 — Anthropic enterprise feature dead |
| `entrypoints/agentSdkTypes.ts` | +7 lines: `HookEvent` + `SDKAssistantMessageError` 추가 only (CC 본체 보존) | swap 종속 (UMMAYA hook event 표면) |
| `entrypoints/sdk/coreSchemas.ts` | 3 lines comment: `@anthropic-ai/sdk` → `UMMAYA sdk-compat` 만 | sdk-compat alias |
| `cli/update.ts` | npm 패키지명: `@anthropic-ai/claude-cli` → `@ummaya/tui` | brand swap |
| `cli/handlers/auth.ts` | `commands/logout` import → no-op stub; `services/api/{errorUtils,firstTokenDate}` → no-op | Spec 1633/2293 — Anthropic auth dead |
| `cli/handlers/autoMode.ts` | 전체 함수 본문 stubbed; `utils/permissions/yoloClassifier` 의존 (Anthropic TRANSCRIPT_CLASSIFIER) 제거 | Spec 1633 P2 |
| `migrations/*` (11 파일 전체 삭제) | Sonnet45→46, Opus, Fennec, Pro→Opus, autoUpdates, bypassPermissions, replBridge 등 모든 마이그레이션 제거 | **모두 Anthropic-only**. main.tsx L181-185 가 명시: "Update CURRENT_MIGRATION_VERSION when UMMAYA-specific migrations needed". `CURRENT_MIGRATION_VERSION = 11` 그대로 유지하여 CC settings.json 호환 — 정당. |
| `constants/prompts.ts` | `EXPLORE_AGENT`/`PROACTIVE` import 삭제, `FRONTIER_MODEL_NAME`/`CLAUDE_4_5_OR_4_6_MODEL_IDS` 상수 삭제, `proactiveModule` 게이트 제거 | Spec 1633 + Spec 2521 (model swap) — 정당 |
| `constants/tools.ts` | `WORKFLOW_TOOL_NAME` import + 사용 제거 | Spec 1633 / Epic #2293 — WorkflowTool 삭제 |
| `constants/betas.ts` | CC 의 Anthropic beta header 상수 → UMMAYA bridge stub (claude.ts 컴파일용 inert string) | Spec 2521 byte-copy bridge 정당 (단, 헤더 상수가 CC 와 다른 set 으로 교체됨) |

### 2.3 Bucket C — UMMAYA-ORIGINAL-justified

| 파일 | 정당성 |
|---|---|
| `tui/src/i18n/{en.ts, ko.ts, keys.ts, index.ts, uiL2.ts}` | 한국어 primary 운영 — UMMAYA swap 종속 (시민용 한국 행정 도구) |
| `tui/src/observability/surface.ts` | UI L2 surface activation 이벤트 (Spec 035 onboarding) |
| `tui/src/memdir/{consent.ts, io.ts, ministry-scope.ts}` | UI L2 동의 영수증 + 부처 scope opt-in (Spec 035) |
| `tui/src/context/PermissionReceiptContext.tsx` | UI L2 권한 영수증 표시 (Spec 035) |
| `tui/src/schemas/ui-l2/*.ts` (8 파일) | UI L2 새 표면 (a11y, agent, error, onboarding, permission, slash-command, ufo) — UMMAYA-ORIGINAL Spec 035 + 1635 |
| `tui/src/cli/transports/Transport.ts` | UMMAYA 가 추출한 Transport interface (CC 에서는 inline) — refactor 수준 |
| `tui/src/entrypoints/envGuard.ts` | FRIENDLI_API_KEY fail-closed gate (Spec 1633 T011) |
| `tui/src/entrypoints/sdk/{controlTypes.ts, coreTypes.generated.ts, runtimeTypes.ts, sdkUtilityTypes.ts, settingsTypes.generated.ts, toolTypes.ts}` | CC 의 `@anthropic-ai/sdk` 패키지가 export 하던 타입을 UMMAYA-내부에서 재선언 — swap 의 dependency-removal 일부 (정당, 단 **D-2 의심** — 일부는 단순 누락 가능) |
| `tui/src/types/{message.ts, messageQueueTypes.ts, notebook.ts, statusLine.ts, tools.ts, utils.ts, connectorText.ts, fileSuggestion.ts}` | CC 에서 다른 디렉토리에 흩어진 타입을 `types/` 하위로 통합 — refactor 수준의 swap-tangential |
| `tui/src/constants/querySource.ts` | UMMAYA query source 상수 (Spec 2521 LLM swap 종속) |
| `src/ummaya/memdir/*.py` (758 LOC) | Python 백엔드 — UI L2 동의 영수증 / ministry scope / onboarding 이벤트의 server-side 저장 (Spec 027 + Spec 035) |
| `src/ummaya/observability/*.py` (1011 LOC) | Python OTEL bridge / semantic conventions / metrics — Spec 021 + Spec 028 (UMMAYA 4-tier OTEL) |
| `src/ummaya/permissions/*.py` (2271 LOC) | Permission 시스템 server-side — Spec 024 / 025 / 033 (HMAC ledger, canonical JSON, action digest) |
| `src/ummaya/security/*.py` (455 LOC) | Audit + V12 dual-axis tool security spec — Spec 024 / 1979 |

### 2.4 Bucket D — REGRESSION (정당화 안 됨)

**D-1: `tui/src/types/generated/events_mono/*.ts` — 97% gutted to stub**

- `events_mono/claude_code/v1/claude_code_internal_event.ts`: **CC 865 LOC → UMMAYA 21 LOC** (97% 손실)
- `events_mono/growthbook/v1/growthbook_experiment_event.ts`: 비슷한 비율로 stub
- `events_mono/common/v1/auth.ts`: **UMMAYA 에서 디렉토리 자체 누락**
- UMMAYA 헤더: `// UMMAYA-1633 — protobuf events_mono stub.`

**판정**: GrowthBook 텔레메트리 / claude.ai internal event 는 swap 종속 (정당) 이지만, **`Buffer`/`Reader`/`Writer` 타입 export 자체가 사라져서 이 타입을 import 하는 누구든지 컴파일 깨짐**. Spec 2521 byte-copy 가 강제하는 "claude.ts 가 컴파일되어야 함" 요건과 충돌. 차라리 타입만 남기고 logEvent 호출 표면을 무력화해야 정상.

**D-2: `tui/src/constants/{messages.ts, xml.ts, figures.ts, oauth.ts}` 그리고 `types/logs.ts` — Proxy stub 잔재 (P0 reconstruction 미완)**

```ts
// constants/messages.ts (UMMAYA) 1행:
// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
const __stub: any = new Proxy(function () {} as any, { ... });
export default __stub;
```

CC 의 `messages.ts` 는 단 1줄: `export const NO_CONTENT_MESSAGE = '(no content)'`. UMMAYA 는 32줄짜리 Proxy stub 로 대체. 마찬가지로 `xml.ts` (CC 32 LOC of plain string consts → UMMAYA 22 LOC of Proxy), `figures.ts` (CC 의 Unicode glyph 상수 vs UMMAYA 의 stub-fallback), `types/logs.ts` (CC 의 `SerializedMessage` type vs UMMAYA Proxy).

**판정**: 이건 **Spec 1633 dead-code 가 아니라 P0 byte-copy 누락**. CC 원본의 plain string 상수를 그대로 복사할 수 있는 작업인데도 Proxy stub 로 남아있음 → consumer 가 `NO_CONTENT_MESSAGE` 를 쓸 때 `''` (stub 의 `Symbol.toPrimitive`) 가 반환되어 silent regression 발생. **즉시 수정 필요** — CC 원본을 그대로 복사할 것.

**D-3: `tui/src/cli/print.ts` 완전 누락**

- main.tsx L1960 가 "UMMAYA: --print / non-interactive (headless) mode is not supported" 메시지로 차단
- 정당성 cite: Spec 1633 / Epic #2293
- 그러나 `--print` (headless mode) 는 **swap 무관 기능** — CC harness 의 핵심 기능 중 하나 (CI/스크립트에서 LLM 출력만 stdout 으로). UMMAYA 가 시민용이라도 headless 모드는 정책 분석 자동화에 필요.
- **판정**: dead-code 라기 보다 **P3+ 후속 마이그레이션 보류**. 현재 차단 메시지가 충분한 fallback 이지만, 회귀로 분류하여 추적 필요.

**D-4: `main.tsx` 의 1917 LOC 삭제 중 `feature()` 게이트 61개 → 0 의 일부 over-aggressive 가능**

- 명백히 swap 종속 삭제: `KAIROS` (Anthropic 사내 assistant), `COORDINATOR_MODE` (Anthropic 1P swarm), `DIRECT_CONNECT` (claude.ai), `SSH_REMOTE` (claude.ai 원격), `TRANSCRIPT_CLASSIFIER` (Anthropic GrowthBook)
- **의심 케이스**: `WORKFLOW_SCRIPTS`, `PROACTIVE`, `BRIEF` — 이 중 `WORKFLOW_SCRIPTS` 는 Spec 1633 / Epic #2293 cite 가 명시적이지만 `PROACTIVE` / `BRIEF` 는 main.tsx 에 `_options: unknown` 으로 시그니처만 남고 본체는 noop. 정말 swap 종속인지 검증 필요.
- **판정**: D bucket 으로 명시적 분류는 하지 않고 "수정 필요 사항" 으로 둠. Phase 1 수동 검토 권장.

---

## 3. main.tsx 섹션별 발산 분석 (4683 → 2766 LOC, 1917 LOC 삭제 = 41%)

| 섹션 (CC 라인) | 함수/구역 | UMMAYA 처리 | 분류 |
|---|---|---|---|
| L1-70 | top-level imports + `feature()` 모듈 게이트 (KAIROS/COORDINATOR_MODE/TRANSCRIPT_CLASSIFIER 등) | 모두 삭제. UMMAYA 는 `feature()` 호출 0건 | B (Spec 1633 cite) |
| L70-215 | teammate utils + 기타 module-level constants | 보존 (line 41-138 UMMAYA) | A |
| L216-228 | `logManagedSettings()` | **삭제** | B (analytics) |
| L232-278 | `isBeingDebugged()` | 보존 | A |
| L279-290 | `logSessionTelemetry()` | **삭제** | B (analytics) |
| L291-324 | `getCertEnvVarTelemetry()` | **삭제** | B (analytics) |
| L325-360 | `runMigrations()` | 보존, 본체는 `// If model-alias migrations are needed for UMMAYA, add them here.` 주석으로 단순화 | B (모든 CC migration 이 Anthropic 모델용 → 정당) |
| L360-432 | prefetch + settings load functions | 보존 | A |
| L432-580 | `loadSettingsFromFlag` / `loadSettingSourcesFromFlag` / `eagerLoadSettings` / `initializeEntrypoint` + `_pendingConnect`/`_pendingAssistantChat`/`_pendingSSH` const | 게이트 변수 `_pendingConnect`/`_pendingAssistantChat`/`_pendingSSH` (DIRECT_CONNECT/KAIROS/SSH_REMOTE feature) **삭제** | B (1P 기능) |
| L585-4611 | **`async function main()` 본체 — CC 4026 LOC, UMMAYA 2356 LOC**  | 1670 LOC 삭제 | 혼합 (대부분 B, 일부 D-4 의심) |
| ↳ main 안의 onboarding | CC 의 1P `showSetupScreens` 호출 → UMMAYA 의 5-step `OnboardingFlow` 추가 호출 (UMMAYA-ORIGINAL +50 LOC) | C (UI L2) |
| ↳ main 안의 print mode | CC 의 `runPrint(..)` → UMMAYA 의 차단 stderr 메시지 | D-3 |
| ↳ main 안의 file flag | CC 의 `--file` flow → UMMAYA 의 unsupported 메시지 | B (Spec 1633) |
| ↳ main 안의 claude.ai MCP fetch / sessionDataUploader / fileDownloadPromise | UMMAYA 에서 모두 nullified | B |
| ↳ main 안의 version 표시 | `MACRO.VERSION` → `${MACRO.VERSION} (UMMAYA)` | C (brand) |
| L4611-4622 | `maybeActivateProactive()` | UMMAYA 는 본체 비움 (`_options: unknown`) | D-4 의심 |
| L4622-4653 | `maybeActivateBrief()` | UMMAYA 는 본체 비움 | D-4 의심 |
| L4653-4683 | `resetCursor()` + teammate options | 보존 | A |

**main.tsx 결론**: 1917 LOC 삭제 중 ~95% 는 Spec 1633 cite 로 정당. 나머지 ~5% (`maybeActivateProactive`/`maybeActivateBrief`/`runPrint`) 는 헤더 cite 가 모호. PR 시 review 받아야.

---

## 4. Python 백엔드 정당성 (`src/ummaya/` 의 4 모듈)

S8 의 Python 측은 "TUI 는 client, Python 은 server" 이중 구조의 server-side 대응. 4 모듈 모두 UMMAYA swap 의 server-side 표면으로 정당화됨.

| 모듈 | LOC | 정당성 cite |
|---|---|---|
| `memdir/` (consent_ledger, ministry_scope, user_consent, onboarding_events) | 758 | UI L2 (`docs/requirements/ummaya-migration-tree.md § UI-A.5/C.3`) — 동의 철회 ledger, 부처 scope opt-in. Spec 027 mailbox 인프라 위에 빌드. 정당. |
| `observability/` (event_logger, events, metrics, otel_bridge, semconv, tracing) | 1011 | Spec 021 (4-tier OTEL: GenAI / Tool / Permission / Langfuse) + Spec 028 (OTLP collector). CC 의 client-side `services/analytics/` 가 UMMAYA 에서 OTEL bridge 로 swap. 정당. |
| `permissions/` (action_digest, audit_coupling, canonical_json, credentials, hmac_key, ledger_verify, ledger, models, otel_emit, otel_integration) | 2271 | Spec 024 (Tool Template Security v1) + Spec 025 (V6 auth_type ↔ auth_level) + Spec 033 (Permission v2 spectrum). HMAC-SHA-256 ledger seal, RFC 8785 JCS canonical JSON, append-only audit. CC 의 client-side permission UX 만으로는 부족 — 정부 행정 도구는 server-side audit 의무 (PIPA §26). 정당. |
| `security/` (audit, v12_dual_axis) | 455 | Spec 024 + Spec 1979. V12 = `auth_level × pipa_class` 2축 분류. 정당. |

**Python `permissions/steps/` 디렉토리는 비어 있음** (`__pycache__` 만) — Spec 1635 P4 UI L2 의 step components 가 TS 측으로만 구현됐음을 시사. 정당, 회귀 아님.

---

## 5. 핵심 발견 (P0/P1 액션 후보)

### P0-S8-1 (Critical): `constants/{messages,xml,figures,oauth}.ts` + `types/logs.ts` 의 Proxy stub 잔재

CC 원본은 단순 string 상수 / type alias 인데 UMMAYA 가 P0 reconstruction 단계에서 generic Proxy stub 으로 대체한 채 hydrate 되지 않음. 결과:
- `NO_CONTENT_MESSAGE` import 시 `''` 반환 (CC 는 `'(no content)'`)
- XML 태그 상수 (`COMMAND_NAME_TAG` 등) 전부 stub → prompt template 의 XML wrapping 깨짐
- Unicode glyph (`BLACK_CIRCLE` 등) 일부만 hardcoded, 나머지 platform 분기 깨짐
- `oauth.ts` 는 UMMAYA 에서 파일 자체 누락

→ **수정**: CC 원본 5개 파일을 그대로 복사. swap 에 영향 없음.

### P0-S8-2 (Critical): `types/generated/events_mono/*` 97% gutted

`Buffer`/`Reader`/`Writer` proto type export 자체가 사라져 import 시 컴파일 가능하더라도 type signature 가 `unknown`. Spec 2521 byte-copy 의 "claude.ts 컴파일" 요건과 충돌. logEvent 호출 표면만 무력화하고 type 은 남겨야.

→ **수정**: CC events_mono/* 원본 복원, logEvent 호출은 entry point 에서만 막음.

### P1-S8-3 (Major): main.tsx 의 `maybeActivateProactive` / `maybeActivateBrief` / `cli/print.ts` 누락

이 3개는 명시적인 Spec 1633 cite 없이 무력화/삭제됨. PROACTIVE / BRIEF 는 Anthropic 1P 인지 검증 필요. `--print` 는 headless mode 로 swap 무관 핵심 기능이지만 차단됨 (Spec 2293 follow-up 대기).

→ **수정**: 3개 항목을 별도 Spec issue 로 분리해 정당성 검토.

### P1-S8-4 (Major): `entrypoints/sdk/` 6 파일의 UMMAYA-only re-declaration 검증 부족

`controlTypes.ts`, `coreTypes.generated.ts`, `runtimeTypes.ts`, `sdkUtilityTypes.ts`, `settingsTypes.generated.ts`, `toolTypes.ts` 가 모두 UMMAYA-only. CC 는 이 타입들을 `@anthropic-ai/sdk` 패키지에서 가져옴. UMMAYA 에서 재선언 자체는 정당하지만 type signature 가 CC 와 1:1 인지 cross-check 안 됨 → **silent type drift** 가능.

→ **수정**: CC `@anthropic-ai/sdk` 의 d.ts 와 UMMAYA 재선언 비교 audit Sprint.

### P2-S8-5 (Minor): 마이그레이션 11개 전체 삭제 — `CURRENT_MIGRATION_VERSION = 11` 보존이 long-term 호환성 가져감

11개 마이그레이션이 모두 Anthropic 모델 alias / claude.ai 전용 — 삭제 정당. 그러나 `CURRENT_MIGRATION_VERSION = 11` 을 그대로 두는 결정은 향후 UMMAYA-specific migration (예: K-EXAONE 모델 alias 변경) 도입 시 version space 충돌 위험. 12부터 UMMAYA-original 로 시작하는 게 안전.

---

## 6. 사용자 결정 필요 사항

1. **D-1 (events_mono stub) 즉시 수정**: CC 원본 865+237 LOC 복원? 아니면 stub 유지하고 logEvent 표면만 차단?
2. **D-2 (Proxy stub 잔재) 복원**: CC 원본 5개 파일 byte-copy? Spec issue 발행?
3. **D-3 (`cli/print.ts` 누락)**: P3+ headless mode 마이그레이션 Epic 발행할지?
4. **D-4 (main.tsx PROACTIVE/BRIEF)**: 추가 검토 후 복원/삭제 결정?
5. **P1-S8-4**: CC `@anthropic-ai/sdk` d.ts vs UMMAYA 재선언 audit Sprint 발행?

---

**이상 S8 감사 보고. 총 108 파일, 12 회귀 항목 (D bucket 4 + main.tsx 1917 LOC 일부 + events_mono stub + Proxy stub).**
