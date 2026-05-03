# Feature Specification: Epic G — Utils 잔존 정리 (sessionTitle PORT + dateTimeParser PORT + permissions Path B + secureStorage ADR)

**Feature Branch**: `feat/2643-s9-utils-residue`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "Epic G — Utils 잔존 정리 (S9). Audit `specs/cc-migration-audit/scope-S9-utils.md` + `decisions.md § S9 Utils` 에서 결정된 4 항목 처리: (1) sessionTitle.ts PORT byte-identical + queryHaiku wire (2) mcp/dateTimeParser.ts PORT byte-identical + 한국어 fixture (3) permissions.ts inline-stub Path B 모듈 분리 (4) secureStorage/ DROP ADR. CORE THESIS = CC + 2 swap만, byte-identical default."

## Background — KOSMOS CORE THESIS

KOSMOS = CC-original harness + 2 swaps (LLM = K-EXAONE on FriendliAI · Tool = 한국 부처 GovAPITool/4 primitive) 만. 그 외 모든 것은 `.references/claude-code-sourcemap/restored-src/src/` 와 byte-identical 유지. 본 Epic은 audit Initiative #2636 (`specs/cc-migration-audit/`) 9-stream S9 (Utils) 결과에서 결정된 **4 잔존 항목** 을 처리한다.

본 Epic이 다루는 잔존의 본질: KOSMOS가 P1 Spec 1633 dead-code purge 단계에서 (a) Anthropic queryHaiku 종속 surface 2개를 inline no-op stub 으로 deleted-mark 했으나 LLM swap 완료 (Spec 2521) 후에도 K-EXAONE re-wire 가 누락된 상태, (b) `yoloClassifier.ts` 삭제 시 inline 흡수로 CC structural fidelity 위반, (c) `secureStorage/` DROP 결정이 ADR 로 박제되지 않음.

## Audit 출처

- `specs/cc-migration-audit/scope-S9-utils.md` § P0-7 / P0-8 / P0-2~6 / 위험 신호 4
- `specs/cc-migration-audit/decisions.md § S9 Utils` (4 결정 row 모두)
- 참조 패턴: `specs/2295-backend-permissions-cleanup/` PR #2364 commit c6747dd (Path B 분리 — derivation table + computed_field backward-compat)
- 참조 Epic: `specs/2637-p0-regression/spec.md` (Epic A — 같은 audit-driven byte-copy 패턴)

## Pre-execution 잔존 실재 확인 (2026-05-03 워크트리 grep/ls)

| # | 파일 | KOSMOS 현재 | CC baseline | 상태 |
|---|---|---|---|---|
| 1 | `tui/src/utils/sessionTitle.ts` | **MISSING (디렉토리 자체 없음)** | 129 LOC `generateSessionTitle` + `extractConversationText` | 누락 |
| 1a | `tui/src/cli/print.ts:156` | `import { generateSessionTitle } from 'src/utils/sessionTitle.js'` | — | **broken import (P1 회귀)** |
| 1b | `tui/src/cli/print.ts:3803` | `await generateSessionTitle(description, titleSignal)` | — | dead callsite |
| 2 | `tui/src/utils/mcp/dateTimeParser.ts` | **MISSING** | 121 LOC `parseNaturalLanguageDateTime` + `looksLikeISO8601` | 누락 |
| 2a | `tui/src/utils/mcp/elicitationValidation.ts:10-19` | inline ISO8601-only stub (10 LOC) | `import { parseNaturalLanguageDateTime, looksLikeISO8601 } from './dateTimeParser.js'` | inline stub |
| 3 | `tui/src/utils/permissions/permissions.ts:103-145` | inline 흡수 (~43 LOC: `formatActionForClassifier` + `YoloClassifierResult` type + `classifyYoloAction`) | `import { classifyYoloAction, formatActionForClassifier } from './yoloClassifier.js'` | CC structural fidelity 위반 |
| 4 | `tui/src/utils/secureStorage/` | **MISSING (디렉토리 자체 없음)** | 6 파일 / 629 LOC (macOS Keychain + fallback + plainText) | 의도적 DROP, ADR 미박제 |
| 4a | `docs/adr/ADR-009-secureStorage-drop.md` | **MISSING** | — | 박제 누락 |

**핵심 발견**:
- 항목 1 (`sessionTitle.ts`) 은 단순 PORT 가 아니라 **현재 broken import 가 살아있는 P1 회귀**. `bun run tui` headless --print 모드 시 dynamic resolution 실패 가능.
- 항목 2 (`dateTimeParser.ts`) 는 한국어 도메인 (KOSMOS 시민 사용자) 에 본질적 (예: 119 신고 reservation, KMA 날씨 시점 질의). inline stub 은 ISO8601 만 통과시킴 → 한국어 자연어 시각 입력 100% 거부.
- 항목 3 (`permissions.ts` inline) 은 KOSMOS-side 흡수가 컴파일 통과시켰지만 CC import 구조를 깨뜨려 향후 CC re-port (audit replay) 시 diff noise 가 발생.
- 항목 4 (`secureStorage/`) 는 KOSMOS = `.env` 단일 의존이 정당하나, 향후 다중 부처 API key (data.go.kr 외에 KOROAD / KMA / HIRA / NMC 별도 키 등장 시) trigger 가 ADR 로 박제되어야 후속 Epic 이 cite 가능.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — 헤드리스 --print 모드 자동 세션 제목 생성 회복 (Priority: P1)

KOSMOS SDK 클라이언트가 `bun run tui --print` 로 호출 후 첫 사용자 메시지를 보내면, K-EXAONE 가 6단어 sentence-case 세션 제목을 자동 생성해 SDK control response (`subtype=generate_session_title`) 로 반환한다. 현재 `cli/print.ts:156` 가 누락된 `utils/sessionTitle.ts` 를 import 하므로 SDK 호출 경로가 dynamic resolve 단계에서 throw 가능.

**Why this priority**: `cli/print.ts` 는 Spec 2637 Epic A 에서 byte-copy 복원 완료된 파일 (5594 LOC). 본 import 가 누락된 채 머지되면 audit-driven byte-copy 약속이 회귀. 또한 SDK headless mode 는 KOSMOS 의 외부 통합 진입점 (Phase 5 plugin DX, MCP server consumer) 이므로 silent regression 차단 필수.

**Independent Test**: `tui/src/utils/sessionTitle.ts` 파일 존재 + `bun typecheck` (cli/print.ts:156 import 정상 resolve) + `bun test` 단위 테스트 (description 입력 → K-EXAONE mock 호출 → JSON `{title}` 추출 → null fallback 검증).

**Acceptance Scenarios**:

1. **Given** PORT 완료 후, **When** `import { generateSessionTitle } from 'src/utils/sessionTitle.js'`, **Then** 함수 시그니처 `(description: string, signal: AbortSignal) => Promise<string | null>` 가 export 되어 cli/print.ts:156 컴파일 성공.
2. **Given** `generateSessionTitle('한강 다리 사고 확인 도와줘', signal)` 호출, **When** K-EXAONE mock 가 `{"title": "한강 다리 사고 조회"}` 반환, **Then** 함수가 `'한강 다리 사고 조회'` 반환.
3. **Given** K-EXAONE 가 unparseable 응답 (예: empty string, malformed JSON) 반환, **When** `generateSessionTitle` catch, **Then** `null` 반환 + `tengu_session_title_generated success=false` analytics 이벤트.
4. **Given** `signal.aborted === true`, **When** 호출, **Then** `null` 반환 + 에러 throw 없음 (catch 가 흡수).

---

### User Story 2 — MCP 도구 한국어 자연어 시각 입력 파싱 회복 (Priority: P1)

KOSMOS 시민 사용자가 MCP 도구 (예: 119 신고 reservation, KMA 단기예보 시점 질의) 의 `date` / `date-time` format 인자에 `내일 오후 3시` / `다음주 월요일 오전 9시` 같은 한국어 자연어를 입력하면, `validateElicitationInputAsync` 가 K-EXAONE 으로 ISO 8601 변환을 시도해 통과시킨다. 현재 inline stub 은 ISO 8601 정규식만 통과시켜 한국어 입력은 모두 거부됨.

**Why this priority**: KOSMOS 시민 사용자는 ISO 8601 을 모름 (개발자 페르소나가 아님). 한국어 자연어 시각 입력은 시민 UX 의 핵심 surface (`docs/requirements/kosmos-migration-tree.md § UI-A` 한국어 primary 원칙). `dateTimeParser.ts` 는 LLM swap (Spec 2521) 완료 후 K-EXAONE re-wire 가 즉시 가능하므로 P1 상위.

**Independent Test**: `tui/src/utils/mcp/dateTimeParser.ts` 파일 존재 + Korean fixture 회귀 테스트 (`내일 오후 3시` → ISO 8601 date-time 반환, `다음주 월요일 오전 9시` → ISO 8601 반환, gibberish 입력 → `INVALID` reject).

**Acceptance Scenarios**:

1. **Given** `parseNaturalLanguageDateTime('내일 오후 3시', 'date-time', signal)` 호출, **When** K-EXAONE mock 가 `2026-05-04T15:00:00+09:00` 반환, **Then** `{success: true, value: '2026-05-04T15:00:00+09:00'}` 반환.
2. **Given** `parseNaturalLanguageDateTime('다음주 월요일', 'date', signal)` 호출, **When** K-EXAONE mock 가 `2026-05-11` 반환, **Then** `{success: true, value: '2026-05-11'}` 반환.
3. **Given** `parseNaturalLanguageDateTime('asdf', 'date', signal)` 호출, **When** K-EXAONE mock 가 `INVALID` 반환, **Then** `{success: false, error: 'Unable to parse date/time from input'}` 반환.
4. **Given** `looksLikeISO8601('2026-05-03')`, **Then** `true` 반환. **Given** `looksLikeISO8601('내일')`, **Then** `false` 반환.
5. **Given** `elicitationValidation.ts` import 전환 완료, **When** validateElicitationInputAsync 의 `parseNaturalLanguageDateTime` 호출, **Then** 한국어 입력 → ISO 변환 → zod schema validation pass.

---

### User Story 3 — Permissions Path B 모듈 분리 (CC Structural Fidelity 회복) (Priority: P2)

KOSMOS 개발자가 `tui/src/utils/permissions/permissions.ts` 를 CC `.references/.../permissions.ts` 와 비교하면, KOSMOS-only 흡수 hunk (line 103-145, ~43 LOC) 가 사라져 CC 와 동일한 import 구조 (`import { classifyYoloAction, formatActionForClassifier } from './yoloClassifier.js'`) 가 회복된다. KOSMOS-side `yoloClassifier.ts` 는 Path B 패턴 (Spec 2295 PR #2364 commit c6747dd) 으로 별도 모듈에 inline-stub 격리.

**Why this priority**: 컴파일은 이미 통과 (P0 회귀 아님). CC fidelity 는 audit replay (`/speckit-implement` re-run, byte-copy verification) 시 noise 차단 + 향후 CC source-map upgrade (CC 2.2.x) 시 patch import 만으로 따라잡을 수 있는 surface 보존. CORE THESIS "byte-identical default" 정책 준수.

**Independent Test**: `tui/src/utils/permissions/yoloClassifier.ts` 파일 존재 + `permissions.ts` 가 CC import 형태 회복 (`diff -u .references/.../permissions.ts tui/src/utils/permissions/permissions.ts` 의 import 섹션 hunk 0) + `bun test` permissions 회귀 0.

**Acceptance Scenarios**:

1. **Given** 모듈 분리 완료 후, **When** `import { classifyYoloAction, formatActionForClassifier, YoloClassifierResult } from './yoloClassifier.js'` 시도, **Then** 3종 export 모두 resolve.
2. **Given** `classifyYoloAction(messages, action, tools, ctx, signal)` 호출, **When** stub 이 즉시 반환, **Then** `{unavailable: true, shouldBlock: false}` (Spec 1633 의 KOSMOS auto-mode = no-op 보존).
3. **Given** `formatActionForClassifier('Bash', {command: 'ls'})`, **When** stub call, **Then** 빈 문자열 `''` 반환 (CC 시그니처 호환).
4. **Given** `permissions.ts` 가 yoloClassifier import 로 전환 완료, **When** `permissions.ts` line range 91-150 의 `// KOSMOS-original`/`// KOSMOS Spec 1633` 흡수 주석 hunk 가 삭제, **Then** `diff` import 섹션 hunk 만 남음 (CC와 1:1).
5. **Given** Path B 모듈 분리 적용, **When** 기존 callsite (permissions.ts line 670 / 710 / 777 의 `inProtectedNamespace` + classifier 호출 경로) 회귀, **Then** `bun test` 모든 permissions 단위 테스트 PASS.

---

### User Story 4 — secureStorage DROP 결정 박제 (ADR-009) (Priority: P3)

KOSMOS 후속 Epic 작성자가 "다중 부처 API key 보관" 요구사항을 만나면, `docs/adr/ADR-009-secureStorage-drop.md` 를 cite 해 (a) 현재 `.env` 단일 의존 정당화 근거, (b) 미래 trigger 조건 (data.go.kr 키 외 별도 부처 키 ≥ 2종 등장 시), (c) 그 시점에서 PORT 할 CC 6 파일 목록 (macOS Keychain + fallback + plainText) 을 1 파일에서 확인할 수 있다.

**Why this priority**: 현재 KOSMOS 는 `.env` 단일 의존만 사용하므로 즉시 영향 없음 (P3). 단, 박제가 누락되면 후속 작업자가 CC restored-src 의 6 파일 부재를 보고 "이거 PORT 해야 하나?" 재검토 시간 낭비 + 잘못된 PORT 결정 위험.

**Independent Test**: `docs/adr/ADR-009-secureStorage-drop.md` 존재 + ADR 표준 5 섹션 (Status / Context / Decision / Consequences / Future trigger) 충족 + `decisions.md § S9 Utils` 에서 ADR 링크 cite + scope-S9-utils.md 의 D2 결정 row 가 ADR 로 cross-reference.

**Acceptance Scenarios**:

1. **Given** ADR 작성 완료, **When** `cat docs/adr/ADR-009-secureStorage-drop.md`, **Then** Status / Context / Decision / Consequences / Future trigger 섹션 모두 출현.
2. **Given** Future trigger 섹션, **When** 읽음, **Then** 트리거 조건 명시 (예: "KOSMOS 가 동시에 ≥2 부처별 별도 API key 를 환경변수 prefix 만으로 관리 어려운 시점, 또는 PIPA-class C2 키 회전 정책이 도입되는 시점").
3. **Given** ADR 의 PORT-time scope, **When** 읽음, **Then** CC 6 파일 경로 모두 명시 (`index.ts` + `macOsKeychainStorage.ts` + `keychainPrefetch.ts` + `macOsKeychainHelpers.ts` + `fallbackStorage.ts` + `plainTextStorage.ts`).

---

### Edge Cases

- **K-EXAONE rate-limit 시 sessionTitle 호출 실패**: `generateSessionTitle` 의 try/catch 가 `null` 반환 → SDK control response 가 `{title: null}` 반환 → 호출자 (`cli/print.ts:3803`) 가 `if (title && persist)` 가드로 무시. 회귀 0.
- **dateTimeParser 가 ISO 형식 입력 받음**: `validateElicitationInputAsync` 가 sync zod validation 으로 먼저 통과 → `parseNaturalLanguageDateTime` 호출 안 함. K-EXAONE 호출 0.
- **`.env` 미설정 상태에서 secureStorage callsite 진입 시도**: KOSMOS 는 `secureStorage/` 자체가 없으므로 callsite 가 import 단계에서 type 에러. ADR-009 가 "현재 부재 정당화 + import 시도 = 코드 회귀" 명시.
- **Path B yoloClassifier 분리 후 callsite 경로**: `classifyYoloAction` 은 항상 `unavailable=true` 반환 → `permissions.ts` 내 분기 (line 670 / 710 / 777) 가 standard prompt path fallback. 시민 UX 무회귀.
- **K-EXAONE 가 한국어 입력에 대해 잘못된 ISO 반환** (예: `INVALID` 대신 `2026-13-45`): `parseNaturalLanguageDateTime` 의 `^\d{4}` sanity check 통과 후 zod schema 가 reject → `validateElicitationInput` 단계에서 사용자에게 재입력 요청. 한국어 fixture 테스트가 이 경로를 `bun test` 에 박제.

## Requirements *(mandatory)*

### Functional Requirements

#### sessionTitle.ts PORT (FR-001 ~ FR-005)

- **FR-001**: System MUST byte-identical port `tui/src/utils/sessionTitle.ts` from `.references/claude-code-sourcemap/restored-src/src/utils/sessionTitle.ts` (129 LOC), preserving CC import order, function signatures, and JSDoc.
- **FR-002**: PORT MUST replace only the `queryHaiku` import resolution to KOSMOS `services/api/claude.ts:3270` `queryHaiku` (already implemented). Module-level prompt constant `SESSION_TITLE_PROMPT` and zod schema unchanged byte-identical.
- **FR-003**: System MUST add `// SWAP/llm-swap(2643): queryHaiku target = K-EXAONE via FriendliAI (Spec 2521 byte-copy bridge).` header line immediately after CC's leading JSDoc block.
- **FR-004**: `generateSessionTitle(description, signal)` MUST return `null` on (a) empty/whitespace-only description, (b) `safeParse` failure, (c) any thrown error, matching CC fail-closed behavior.
- **FR-005**: System MUST emit analytics event `tengu_session_title_generated` with `{success: boolean}` payload on every invocation, regardless of result, preserving CC observability surface.

#### dateTimeParser.ts PORT (FR-006 ~ FR-011)

- **FR-006**: System MUST byte-identical port `tui/src/utils/mcp/dateTimeParser.ts` from `.references/.../utils/mcp/dateTimeParser.ts` (121 LOC), preserving CC system prompt verbatim (English source per AGENTS.md hard rule).
- **FR-007**: PORT MUST replace only the `queryHaiku` import resolution to KOSMOS `services/api/claude.ts` `queryHaiku`, with `// SWAP/llm-swap(2643)` header.
- **FR-008**: `parseNaturalLanguageDateTime(input, format, signal)` MUST return `{success: false, error: 'Unable to parse date/time from input'}` when (a) K-EXAONE returns `'INVALID'`, (b) parsed text fails `^\d{4}` sanity check, (c) parsed text is empty.
- **FR-009**: `looksLikeISO8601(input)` MUST return `true` for `YYYY-MM-DD` and `YYYY-MM-DDTHH:MM:SS` patterns, `false` otherwise. Regex byte-identical with CC.
- **FR-010**: System MUST migrate `tui/src/utils/mcp/elicitationValidation.ts` line 10-19 inline stub to `import { parseNaturalLanguageDateTime, looksLikeISO8601 } from './dateTimeParser.js'`, removing the stub block.
- **FR-011**: Korean fixture regression tests MUST cover: (a) `내일 오후 3시` → date-time success path, (b) `다음주 월요일 오전 9시` → date-time success path, (c) `다음주 월요일` → date success path, (d) `asdf` → `INVALID` failure path. Tests MUST mock `queryHaiku` (not call live K-EXAONE — AGENTS.md hard rule).

#### permissions.ts Path B 분리 (FR-012 ~ FR-016)

- **FR-012**: System MUST create `tui/src/utils/permissions/yoloClassifier.ts` (KOSMOS-side stub module) exporting (a) `formatActionForClassifier(toolName, input): string`, (b) `classifyYoloAction(messages, action, tools, ctx, signal): Promise<YoloClassifierResult>`, (c) `YoloClassifierResult` type, all matching CC's signature shape.
- **FR-013**: KOSMOS-side `yoloClassifier.ts` MUST preserve the no-op behavior currently in `permissions.ts` line 103-145 (returns `{unavailable: true, shouldBlock: false}` from `classifyYoloAction`; returns empty string from `formatActionForClassifier`). Header MUST cite "Path B (Spec 2295 PR #2364 commit c6747dd)" pattern.
- **FR-014**: System MUST replace `permissions.ts` line 102-145 inline stub with byte-identical CC import `import { classifyYoloAction, formatActionForClassifier } from './yoloClassifier.js'`. The replacement hunk MUST shrink `permissions.ts` to ≤ 1486 LOC (CC baseline) ± 5 lines (the residual = `// KOSMOS-original` calculateCostFromTokens stub on line 91 + Anthropic SDK import swap on line 2).
- **FR-015**: `permissions.ts` callsites (line 670 / 710 / 777 `inProtectedNamespace`, classifier check paths in `applyPermissionUpdate`/`applyPermissionUpdates`) MUST remain unchanged. Path B is import-shape only.
- **FR-016**: After Path B migration, `diff .references/.../permissions/permissions.ts tui/src/utils/permissions/permissions.ts` MUST yield only swap-1 hunks (line 2 `@anthropic-ai/sdk` → `src/sdk-compat.js`, line 91 `calculateCostFromTokens` no-op stub) — total diff ≤ 8 lines.

#### secureStorage DROP ADR (FR-017 ~ FR-020)

- **FR-017**: System MUST author `docs/adr/ADR-009-secureStorage-drop.md` following the 5-section ADR template used by ADR-001 ~ ADR-008 (Status / Context / Decision / Consequences / Future trigger).
- **FR-018**: ADR MUST enumerate all 6 CC `secureStorage/` files (`index.ts` / `macOsKeychainStorage.ts` / `keychainPrefetch.ts` / `macOsKeychainHelpers.ts` / `fallbackStorage.ts` / `plainTextStorage.ts`) as the PORT-time scope, with LOC totals.
- **FR-019**: ADR's Future trigger section MUST specify a measurable condition for revisiting (e.g., "KOSMOS simultaneously manages ≥ 2 distinct ministry API keys requiring per-tenant isolation that `KOSMOS_*` env-prefix scoping cannot provide, or PIPA-class C2 key rotation policy is mandated").
- **FR-020**: `specs/cc-migration-audit/decisions.md § S9 Utils` MUST be updated with a one-line cross-reference to ADR-009. `scope-S9-utils.md § P0-2~6` and `§ 사용자 결정 필요 D2` MUST cross-reference ADR-009.

### Key Entities

- **`generateSessionTitle(description, signal)` function**: PORT target. Returns `Promise<string | null>`. Called from `cli/print.ts:3803` SDK headless mode. Emits `tengu_session_title_generated` analytics event.
- **`parseNaturalLanguageDateTime(input, format, signal)` function**: PORT target. Returns `Promise<DateTimeParseResult>` (`success: true` + ISO 8601 value, or `success: false` + error message). Called from `validateElicitationInputAsync` for MCP elicitation surface.
- **`YoloClassifierResult` type**: KOSMOS-side stub type matching CC shape (`unavailable: boolean`, `shouldBlock: boolean`, optional `errorDumpPath`/`usage`/`model`/etc.). Always returns `unavailable=true` in KOSMOS (auto-mode = no-op per Spec 1633).
- **`docs/adr/ADR-009-secureStorage-drop.md` document**: ADR file. 5 sections. Cited from `decisions.md` and `scope-S9-utils.md`. Future trigger condition documented.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `tui/src/utils/sessionTitle.ts` exists with byte-identical CC structure except for swap-1 import line + 1-line SWAP header. `bun typecheck` passes (cli/print.ts:156 import resolves).
- **SC-002**: `tui/src/utils/mcp/dateTimeParser.ts` exists with byte-identical CC structure except for swap-1 import line + 1-line SWAP header. `tui/src/utils/mcp/elicitationValidation.ts` no longer contains inline `parseNaturalLanguageDateTime` stub (lines 10-19 hunk removed, replaced by import).
- **SC-003**: `bun test tui/src/utils/mcp/__tests__/dateTimeParser.test.ts` passes 4+ Korean fixture cases (`내일 오후 3시`, `다음주 월요일 오전 9시`, `다음주 월요일`, `asdf` reject) using mocked `queryHaiku` (no live K-EXAONE).
- **SC-004**: `tui/src/utils/permissions/yoloClassifier.ts` exists. `permissions.ts` LOC count ≤ 1494 (CC 1486 + max 8 swap-1 lines). `diff .references/.../permissions/permissions.ts tui/src/utils/permissions/permissions.ts | grep "^[<>]" | wc -l` ≤ 8.
- **SC-005**: `bun test` permissions suite (existing tests) passes 0 regression (baseline = current main green status).
- **SC-006**: `docs/adr/ADR-009-secureStorage-drop.md` exists with 5 ADR sections. `decisions.md § S9 Utils` row 2 cross-references `ADR-009`. `scope-S9-utils.md § P0-2~6` and `§ D2` cross-reference `ADR-009`.
- **SC-007**: K-EXAONE retry budget measurement: `generateSessionTitle` end-to-end latency on FriendliAI Tier 1 (60 RPM) measured 3 times with non-trivial Korean description, p95 ≤ 6 s (consistent with Spec 2521 K-EXAONE smoke baselines). Documented in `quickstart.md`.
- **SC-008**: TUI Layer 5 tmux capture-pane scenario (`scripts/tui-tmux-capture.sh` + custom scenario sending `한강 다리 사고` chat → header title bar update) emits 3+ PNG keyframes (boot / chat-sent / title-rendered). All 3 read by Lead Opus via Read tool, no broken-frame state observed.

## Assumptions

- KOSMOS `services/api/claude.ts:3270` `queryHaiku` function is stable (Spec 2521 byte-copy bridge complete) and re-routes to FriendliAI K-EXAONE through the swap-1 plumbing. `getSmallFastModel()` (line 3307) returns the K-EXAONE alias per Spec 2112 (`tui/src/utils/model/model.ts:179` `getDefaultHaikuModel`).
- FriendliAI Tier 1 (60 RPM) is in effect (memory `project_friendli_tier_wait`). `generateSessionTitle` + `parseNaturalLanguageDateTime` calls do not exhaust the budget under expected interactive load (≤ 5 calls/min per session).
- `cli/print.ts` SDK headless mode is part of the Spec 2637 Epic A byte-copy restoration (5594 LOC) — present in main as of 2026-05-03, not gated by other in-flight Epics.
- KOSMOS `.env` is the sole credential source. No multi-tenant key isolation requirement exists in P0–P6 scope (kosmos-migration-tree.md Phase order).
- Path B precedent (Spec 2295 PR #2364 commit c6747dd) `AdapterRealDomainPolicy` derivation table + `computed_field` backward-compat applies analogously: KOSMOS extracts inline-stub into a sibling module, preserves CC's import structure, retains call-site backward-compat by exporting matching signatures.
- `bun test` snapshot baseline is the current main `9d559b9` (983 pass / 1 pre-existing fail per Spec 2112 commit message). This Epic must preserve that baseline.
- `pytest` baseline is current main (3458 pass / 1 pre-existing fail). This Epic does not modify Python sources, so pytest delta = 0.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Live K-EXAONE network calls in CI tests** — AGENTS.md hard rule "Never call live `data.go.kr` APIs from CI tests" extends to all live LLM calls; tests use `queryHaiku` mocks.
- **Re-introduction of CC's TRANSCRIPT_CLASSIFIER feature in `permissions.ts`** — Spec 1633 deletion stands; auto-mode classifier remains no-op per Path B `yoloClassifier.ts` stub. KOSMOS auto-mode goes through `cli/handlers/autoMode` no-op stub (per current header line 100-101).
- **Multi-tenant credential storage in this Epic** — `secureStorage/` PORT itself is excluded; only the DROP ADR is in scope. Future Epic trigger documented in ADR-009.
- **Anthropic SDK type bridge alternative for `permissions.ts` line 2 import** — already handled by Spec 2521 `src/sdk-compat.js` shim; not revisited here.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| `protectedNamespace.ts` / `systemThemeWatcher.ts` 7-LOC NO-OP stub 실제 구현 | CC source 자체 부재 (Epic A #2637 결정), TUI Fidelity Meta-Epic 대상 | TUI Fidelity Meta-Epic | #2722 |
| `utils/secureStorage/*` 6 파일 PORT (macOS Keychain + fallback + plainText) | ADR-009 trigger 조건 미충족 (현재 .env 단일 의존) | TBD (다중 부처 키 등장 시) | #2724 |
| `commands/rename/generateSessionName.ts` PORT (kebab-case 자동 명명) | Spec 1633 deletion 유지, `/rename` 명령어 한국어 명명 정책 별도 결정 필요 | UI L2 Phase 4 후속 | #2725 |
| `utils/telemetry/instrumentation.ts` PORT | Epic A #2637 (P0 회귀 복구) 가 이미 처리 중 | Epic A #2637 (in-flight) | #2637 |
| `bridge/initReplBridge.ts` count-3 generateAndPatch 재활성화 | sessionTitle PORT 후 후속 작업, 본 Epic 은 print 경로만 | Phase 5 후속 | #2726 |
