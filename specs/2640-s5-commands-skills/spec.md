# Feature Specification: S5 Commands/Skills 정리 — claude-api/ 제거 + P0 auto-stub 삭제 + sourcemap gap 검증

**Feature Branch**: `feat/2640-s5-commands-skills`
**Created**: 2026-05-03
**Status**: Draft
**Input**: Initiative #2636 / Epic #2640 — `specs/cc-migration-audit/scope-S5-commands-input.md` 의 DROP-CANDIDATE 정리. 3 cleanup 묶음:
1. **Anthropic SDK skill bundle 일괄 제거** — `tui/src/skills/bundled/claude-api/` 51 파일 + `tui/src/skills/bundled/verify/` 3 파일 + 4 dispatcher 파일 (`claudeApi.ts`, `claudeApiContent.ts`, `verify.ts`, `verifyContent.ts`) + `bundled/index.ts` 등록 정리 = **약 58 skill 파일**.
2. P0 auto-stub commands **20개** (Stage-1 sourcemap reconstruction gap의 NO-OP Proxy stub) caller-graph 검증 후 삭제. `commands.ts` import + COMMANDS array + INTERNAL_ONLY_COMMANDS array 정리.
3. CC sourcemap gap **3개** (`extra-usage/extra-usage-core.ts`, `rename/generateSessionName.ts`, `review/reviewRemote.ts`) 의 KOSAX caller-graph 재검증 → DROP 박제 갱신 (Spec 1633/2293 시점에 inline-stub 으로 처리됨, 본 epic 은 검증 + 문서화).

## Audit references (canonical)

- `specs/cc-migration-audit/scope-S5-commands-input.md` — S5 4-bucket audit, DROP-CANDIDATE 130개 분류표.
- `specs/cc-migration-audit/decisions.md § S5 Commands/Skills` — 결정 3건:
  - claude-api/ 29파일 SDK docs → **제거**.
  - P0 auto-stub 21 commands → **즉시 삭제**.
  - sourcemap gap 3파일 → **caller-graph 재검증 후 PORT 또는 DROP**.
- `AGENTS.md § CORE THESIS` — KOSAX = CC + 2 swap, byte-identical 91% 보존이 정량 증거.
- `docs/vision.md` — Layer 설계 (Commands/Skills 는 UI L2 surface 의 진입점).

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Anthropic SDK skill docs 제거 (Priority: P1)

KOSAX 는 K-EXAONE on FriendliAI 단일 LLM 만 사용한다. `claude-api/` 7-언어 (csharp/curl/go/java/php/python/ruby/typescript/shared) Anthropic SDK 문서 번들과 `verify/` SKILL doc bundle 은 KOSAX scope 외이며, bundled skill loader (`getBundledSkills()`) 가 이들을 슬래시 명령으로 노출시키는 것을 차단한다. 해당 디렉토리를 일괄 삭제하고 `bundledSkills.ts` 의 import/registry 항목을 정리한다.

**Why this priority**: KOSAX 사용자는 Anthropic SDK 코드를 작성하지 않는다. claude-api skill 이 슬래시 명령으로 노출되면 (a) KOSAX scope 와 일관성 위배, (b) Anthropic 종속성 잔재 (CORE THESIS § "swap-1 정당 발산 박제" 위배), (c) 사용자에게 잘못된 mental model 노출. 즉시 제거가 P1.

**Independent Test**: `bun run tui` 실행 후 슬래시 자동완성 드롭다운에서 `/claude-api`, `/verify` (skill) 항목이 더 이상 노출되지 않는지 시각 검증 (Layer 5 tmux capture-pane). `grep -r "claude-api" tui/src/` 가 0 hit (단, 이번 PR 의 `// SWAP:` 박제 코멘트는 검색 결과에서 정당 화이트리스트).

**Acceptance Scenarios**:

1. **Given** `tui/src/skills/bundled/claude-api/` 51 파일이 KOSAX 에 존재하고 `getBundledSkills()` 가 이를 등록한다, **When** 본 spec 의 cleanup 이 머지된다, **Then** 디렉토리는 git 에서 완전 삭제되고 `bundledSkills.ts` import/등록 라인은 제거되며 `bun run tui` 슬래시 자동완성에 `/claude-api*` 항목이 0 개.
2. **Given** `tui/src/skills/bundled/verify/` 3 파일이 KOSAX scope 외 SKILL doc bundle 이다, **When** cleanup 이 머지된다, **Then** 디렉토리는 git 삭제되고 `bun test` 의 bundledSkills 관련 테스트가 통과 (회귀 0).
3. **Given** `bun run tui` 가 부팅된다, **When** 슬래시 자동완성을 호출한다, **Then** PNG 키프레임에 `/claude-api`, `/verify` 항목이 보이지 않고 KOSAX 신설 명령 (`/agents`, `/catalog`, `/consent` 등) 만 보인다.

---

### User Story 2 — P0 auto-stub 20 commands 일괄 삭제 (Priority: P1)

CC 2.1.88 sourcemap reconstruction 시점에서 누락된 20 개 command (`ant-trace/`, `autofix-pr/`, `backfill-sessions/`, `break-cache/`, `bughunter/`, `clear/clear/caches.ts`, `clear/clear/conversation.ts`, `commands/`, `ctx_viz/`, `debug-tool-call/`, `env/`, `good-claude/`, `issue/`, `mock-limits/`, `oauth-refresh/`, `perf-issue/`, `reset-limits/`, `share/`, `summary/`, `teleport/`) 는 모두 동일 NO-OP Proxy stub (`__stub: any = new Proxy(...)`) 를 default export 한다. `commands.ts` 의 import + COMMANDS array 등록 + `INTERNAL_ONLY_COMMANDS` array 등록을 통해 슬래시 명령으로 노출되지만 실행 시 모든 메서드 호출이 self-returning Proxy 로 떨어져 실질적 동작 0. 이를 일괄 git rm 하고 `commands.ts` 의 모든 캐스케이드 reference 를 정리한다. Epic #1633 dead-code elimination tracker 에서 추적된 항목.

**Why this priority**: NO-OP stub 이 슬래시 자동완성에 노출되면 사용자가 클릭해도 실질적 동작 없이 silent fail 한다. 사용자 신뢰 손상 + KOSAX scope 와 무관한 명령으로 인지 부담 증가. 또한 dead code 가 typescript build graph 에 잔존하여 future refactor 시 false-positive import-resolution 위험. P1 즉시 정리.

**Independent Test**: `bun run tui` 실행 후 슬래시 자동완성에서 `/ant-trace`, `/autofix-pr`, `/teleport` 등이 더 이상 노출되지 않는다. `grep -r "from.*commands/ant-trace\|from.*commands/teleport\|from.*commands/share" tui/src/` 가 0 hit. `bun typecheck` PASS.

**Acceptance Scenarios**:

1. **Given** 20 개 P0 stub command 파일이 KOSAX 에 존재하고 `commands.ts` 가 import 한다, **When** cleanup 이 머지된다, **Then** 모든 파일은 git rm 으로 삭제되고 `commands.ts` 의 해당 import 라인 + COMMANDS / INTERNAL_ONLY_COMMANDS array 등록이 일괄 제거되며 `bun typecheck` PASS.
2. **Given** `commands/clear/clear/` 중첩 stub 디렉토리, **When** cleanup 이 머지된다, **Then** 디렉토리 자체가 git rm 되며 (CC sourcemap 의 `commands/clear/clear/` 는 본래 존재하지 않음), `commands/clear/index.ts` (byte-identical preserve) 의 동작은 회귀 0.
3. **Given** P0 stub 삭제 후, **When** `bun run tui` 슬래시 자동완성을 호출한다, **Then** PNG 키프레임에 KOSAX scope 명령만 노출되고 P0 stub 잔재 0.

---

### User Story 3 — CC sourcemap gap 3 파일 caller-graph 재검증 + DROP 박제 (Priority: P2)

3 개 CC 파일 (`extra-usage/extra-usage-core.ts`, `rename/generateSessionName.ts`, `review/reviewRemote.ts`) 은 KOSAX 측에 존재하지 않는다. 이전 audit 라운드 에서는 PORT/DROP 미결로 남았다. 본 spec 은:

(a) 해당 3 파일의 KOSAX 측 caller (`extra-usage.tsx`, `extra-usage-noninteractive.ts`, `rename/rename.ts`, `ultrareviewCommand.tsx`, `ExitPlanModePermissionRequest.tsx`) 의 현 상태가 모두 **Spec 1633 / Epic #2293 시점의 DROP 박제 상태** (KOSAX-2293 헤더 + inline no-op stub) 임을 검증한다.

(b) 검증 결과를 spec 본문 + `decisions.md` 갱신 형태로 박제하여 차후 audit 에서 "검증 미결" 로 재표류하지 않게 한다.

(c) 추가 정리 필요 여부를 명시한다 (예: KOSAX-2293 헤더가 없는 dangling reference 발견 시 추가 박제).

**Why this priority**: 기능 변경 0, 박제 강화만. 만약 caller-graph 가 깨끗하지 않다면 P1 으로 격상되지만 prior 검증에서 깨끗함이 확인됐으므로 P2.

**Independent Test**: 3 파일의 모든 prior caller 가 KOSAX-2293 헤더 또는 명시적 SWAP 코멘트로 박제되었는지 grep 으로 확인. `grep -rn "extra-usage-core\|generateSessionName\|reviewRemote" tui/src/` 가 모두 박제 코멘트 또는 inline stub 만 hit.

**Acceptance Scenarios**:

1. **Given** 3 CC 파일이 KOSAX 에 부재한다, **When** caller-graph 재검증을 수행한다, **Then** 모든 KOSAX 측 caller (`extra-usage*.tsx/ts`, `rename.ts`, `ultrareviewCommand.tsx`, `ExitPlanModePermissionRequest.tsx`) 가 KOSAX-2293 또는 Spec 1633 박제 코멘트 + inline stub 으로 정리되어 있음을 확인.
2. **Given** 검증 결과, **When** spec.md `## Findings` 와 `decisions.md § S5` 가 갱신된다, **Then** 차후 audit 라운드에서 PORT/DROP 미결 마커가 0.
3. **Given** 만약 미박제 dangling reference 가 발견된다면, **When** 추가 박제를 수행한다, **Then** 해당 caller 에 `// KOSAX-2293: <gap-file>.ts deleted (...)` 헤더 + inline no-op stub 을 추가.

---

### Edge Cases

- **`commands/onboarding/index.ts` (Spec 1635 onboarding)**: 동일 P0 stub 헤더를 가지지만 `commands.ts:33` 에서 import 되어 `/onboarding` 슬래시 명령으로 노출된다. 그러나 KOSAX 의 실제 onboarding 진입점은 `commands/onboarding.ts` (Spec 1635 P4) 가 `parseOnboardingCommand` 로 분기 처리한다 (`screens/REPL.tsx:366`). **결정**: `commands/onboarding/index.ts` 를 같은 NO-OP stub 정리 batch 에 포함시키지 않는다 — `commands.ts` 가 default export 를 import 하고 COMMANDS array 에 등록하는 구조라서 단순 삭제 시 typecheck 회귀. 별도 spec (Spec 1635 후속) 에서 처리. 본 epic 은 stub 헤더가 박제 코멘트로만 정리.
- **`commands/install-github-app/types.ts`, `commands/plugin/types.ts`, `commands/plugin/unifiedTypes.ts`**: P0 reconstructed 헤더를 가지지만 `WorkflowMultiselectDialog.tsx` 등에서 type-only import 로 사용된다. 단순 삭제 시 type 회귀. 본 epic 은 dropping 범위 외 (Epic B/D 후속).
- **`commands/clear/clear/` 중첩 stub 디렉토리**: CC sourcemap reconstruction 시점의 path 중복 artifact (실제 CC 에는 `commands/clear/` 만 존재). 본 epic 에서 디렉토리 자체를 git rm 한다.
- **bundled skill loader 가 빈 디렉토리를 만나는 경우**: `tui/src/skills/bundled/` 가 빈 상태가 되면 `getBundledSkills()` 가 어떻게 동작하는지 확인 필요. 본 epic 은 디렉토리는 보존 (다른 bundled skills 가 잔존: batch.ts, claudeApi.ts, claudeApiContent.ts, claudeInChrome.ts 등 — claude-api/ 와 verify/ 서브디렉토리만 제거).
- **bun test snapshot 회귀**: skill list snapshot test 가 있다면 baseline 갱신 필요.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST `tui/src/skills/bundled/claude-api/` 디렉토리의 모든 파일 (51 파일: 26 .md.ts + 22 .md + 1 SKILL.md + 1 SKILL.md.ts + nested subdirs) 을 `git rm` 으로 제거한다.
- **FR-002**: System MUST `tui/src/skills/bundled/verify/` 디렉토리의 모든 파일 (3 파일: SKILL.md.ts + examples/cli.md.ts + examples/server.md.ts) 을 `git rm` 으로 제거한다.
- **FR-003**: System MUST 4 개 dispatcher 파일 (`tui/src/skills/bundled/claudeApi.ts`, `tui/src/skills/bundled/claudeApiContent.ts`, `tui/src/skills/bundled/verify.ts`, `tui/src/skills/bundled/verifyContent.ts`) 를 `git rm` 으로 제거한다 (FR-001 / FR-002 디렉토리 삭제 후 import resolution 가 깨지므로 함께 삭제 필수).
- **FR-003a**: System MUST `tui/src/skills/bundled/index.ts` 에서 `import { registerVerifySkill } from './verify.js'` import 라인 + `registerVerifySkill()` 호출 + `if (feature('BUILDING_CLAUDE_APPS')) { ... registerClaudeApiSkill() ... }` 블록을 제거하고 인라인 박제 헤더 (`// KOSAX-2640: claude-api + verify bundled skills removed — Anthropic SDK docs out of scope (Epic #2640).`) 추가.
- **FR-004**: System MUST P0 auto-stub commands 20 개 (`ant-trace`, `autofix-pr`, `backfill-sessions`, `break-cache`, `bughunter`, `clear/clear/caches.ts`, `clear/clear/conversation.ts`, `commands/index.ts`, `ctx_viz`, `debug-tool-call`, `env`, `good-claude`, `issue`, `mock-limits`, `oauth-refresh`, `perf-issue`, `reset-limits`, `share`, `summary`, `teleport`) 의 모든 파일을 `git rm` 으로 제거한다.
- **FR-005**: System MUST `tui/src/commands.ts` 에서 FR-004 의 20 명령에 대한 모든 import 라인 + COMMANDS array 등록 + `INTERNAL_ONLY_COMMANDS` array 등록을 제거하고, KOSAX 박제 헤더 (`// KOSAX-2640: <command> removed — Stage-1 P0 auto-stub (Epic #2640).`) 를 인라인 코멘트로 추가한다.
- **FR-006**: System MUST `commands/clear/clear/` 중첩 디렉토리를 통째로 `git rm` 으로 제거한다 (CC sourcemap 에 본래 존재하지 않는 reconstruction artifact).
- **FR-007**: System MUST sourcemap gap 3 파일 (`extra-usage/extra-usage-core.ts`, `rename/generateSessionName.ts`, `review/reviewRemote.ts`) 의 모든 KOSAX caller (`extra-usage.tsx`, `extra-usage-noninteractive.ts`, `rename/rename.ts`, `ultrareviewCommand.tsx`, `ExitPlanModePermissionRequest.tsx`) 가 이미 KOSAX-2293 / Spec 1633 박제 헤더와 inline no-op stub 으로 정리되었는지 grep 검증한다.
- **FR-008**: System MUST FR-007 검증 결과를 본 spec.md `## Gap-3 Caller-Graph 박제` 섹션에 박제하고 `specs/cc-migration-audit/decisions.md § S5` 의 "caller-graph 재검증 후 PORT 또는 DROP" 결정을 "DROP 확정 (caller-graph 박제 완료, Epic #2640)" 으로 갱신한다.
- **FR-009**: System MUST `bun typecheck` (KOSAX narrows to `src/stubs/**`) 통과를 유지한다.
- **FR-010**: System MUST `bun test` 회귀를 유발하지 않는다 (pre-existing failures 동일 baseline 유지).
- **FR-011**: System MUST `bun run tui` 부팅 후 `/help` slash 호출 + 슬래시 자동완성 드롭다운에서 삭제된 명령들 (`/ant-trace`, `/teleport`, `/share`, `/summary` 등) 이 노출되지 않음을 Layer 5 tmux capture-pane PNG 3+ 키프레임으로 시각 검증한다.
- **FR-012**: System MUST `commands/onboarding/index.ts`, `commands/install-github-app/types.ts`, `commands/plugin/types.ts`, `commands/plugin/unifiedTypes.ts` 4 개 borderline P0 stub 파일은 본 epic scope 외로 명시한다 (caller dependency 가 단순 삭제를 막음 — Spec 1635 / Epic 후속 처리).
- **FR-013**: System MUST 신규 의존성 (Python pip / TS npm) 0 개 추가 (AGENTS.md hard rule).
- **FR-014**: System MUST 본 epic 의 모든 변경은 `tui/src/` 와 `specs/2640-s5-commands-skills/` 와 `specs/cc-migration-audit/decisions.md` 에 한정한다 (Python backend / `prompts/` / `docs/` 변경 0).

### Key Entities

- **DROP target**: 삭제 대상 파일 — 51 (claude-api/) + 3 (verify/) + 4 (dispatchers) + 20 (P0 stub commands) + nested clear/clear/ = **약 78+ 파일**.
- **Caller cleanup target**: `tui/src/commands.ts` (import + array 정리, 약 60 lines 변경 예상).
- **Verification artifact**: `specs/2640-s5-commands-skills/findings.md` (gap-3 caller-graph 박제), `decisions.md` 갱신.
- **Smoke artifact**: Layer 5 tmux capture-pane PNG 키프레임 3+ 매 (boot+branding / slash autocomplete dropdown / post-action) under `specs/2640-s5-commands-skills/scripts/` 와 `specs/2640-s5-commands-skills/smoke-keyframe-*.png`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `find tui/src/skills/bundled/claude-api -type f | wc -l` = 0 (was 51).
- **SC-001a**: `find tui/src/skills/bundled -maxdepth 1 -name 'claudeApi*.ts' -o -name 'verify*.ts' | wc -l` = 0 (was 4 dispatcher files).
- **SC-002**: `find tui/src/skills/bundled/verify -type f | wc -l` = 0 (was 3).
- **SC-003**: `find tui/src/commands -type d -name 'clear' -exec find {} -type f \; | grep -c '/clear/clear/'` = 0 (중첩 stub 디렉토리 0).
- **SC-004**: `grep -lE "P0 auto-stub|P0 reconstructed.*rebuild-stubs" tui/src/commands/{ant-trace,autofix-pr,backfill-sessions,break-cache,bughunter,commands,ctx_viz,debug-tool-call,env,good-claude,issue,mock-limits,oauth-refresh,perf-issue,reset-limits,share,summary,teleport}/index.ts 2>/dev/null | wc -l` = 0 (20 P0 stub 파일 모두 부재).
- **SC-005**: `bun typecheck` exit 0 (회귀 0).
- **SC-006**: `bun test` 결과가 pre-merge baseline (Epic #2659 머지 시점) 과 동일 (pass count ± 0, 신규 fail 0).
- **SC-007**: Layer 5 PNG 키프레임 3+ 매 캡처 후 Read tool 검증 — `/ant-trace`, `/teleport`, `/share`, `/summary`, `/claude-api*`, `/verify` 가 슬래시 자동완성 드롭다운에서 0 노출.
- **SC-008**: `decisions.md § S5` 의 "caller-graph 재검증 후 PORT 또는 DROP" 항목이 "DROP 확정 (Epic #2640)" 으로 갱신.
- **SC-009**: 신규 runtime dependency 추가 0 (AGENTS.md hard rule, `git diff package.json pyproject.toml` 변경 0).
- **SC-010**: PR body 가 `Closes #2640` 단일 reference (Task sub-issues 미포함).

## Assumptions

- 본 epic 머지 후에도 `commands/onboarding/index.ts` 의 P0 stub 헤더는 잔존하며, Spec 1635 Phase 후속 spec 에서 정리 (별도 tracking).
- `commands.ts` 의 `INTERNAL_ONLY_COMMANDS` 가 `process.env.USER_TYPE === 'ant'` 게이트 하에서만 등록되며, 본 epic 머지 후 ant gate 자체가 dead code 가 됨 — 다음 라운드 audit 에서 추가 정리 (deferred).
- bundled skill loader 가 디렉토리 단위로 등록한다면 `claude-api/` 와 `verify/` 디렉토리 부재 시 자동 skip; 만약 file-list hardcode 된 경우 `bundledSkills.ts` 의 명시적 import/등록 라인 정리 필요. Plan 단계에서 확인.
- gap-3 검증 결과 caller-graph 가 이미 깨끗하다 (prior 박제 완료 상태) — pre-spec 검증으로 확인됨. 만약 dangling reference 가 발견된다면 추가 박제 작업이 1-2 시간 추가될 수 있음.
- Layer 5 tmux capture-pane 시 K-EXAONE LLM 호출 0 (slash autocomplete 만 호출), 따라서 reasoning latency 우려 0.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Python backend 변경 — 본 epic 은 TS-only.
- `prompts/` 변경 — system prompt 무관.
- `docs/` 사용자 문서 갱신 — slash command list 자동 생성 시스템이 없으므로 user-facing doc 변경 불필요. (단 audit 결과 박제는 `specs/cc-migration-audit/decisions.md` 에 한정.)
- KOSAX 신규 명령 추가 — 본 epic 은 cleanup-only.

## Gap-3 Caller-Graph 박제 (FR-007 / FR-008 deliverable)

**작성일**: 2026-05-03 · **검증자**: Lead Opus, Epic D · **근거**: `specs/cc-migration-audit/decisions.md § S5`.

### 결론

세 파일 모두 **DROP 확정**. KOSAX 측 caller-graph 가 이미 Spec 1633 / Epic #2293 시점에 inline-stub + 박제 헤더로 처리됨. 본 Epic #2640 시점의 재검증에서 dangling reference 0 hit.

### 검증 매트릭스

#### 1. `commands/extra-usage/extra-usage-core.ts`

| 항목 | 값 |
|---|---|
| CC sourcemap | `.references/claude-code-sourcemap/restored-src/src/commands/extra-usage/extra-usage-core.ts` (118 LOC) |
| KOSAX 측 | **부재** |
| KOSAX callers (grep `extra-usage-core`) | 1 hit — `tui/src/commands/extra-usage/extra-usage-noninteractive.ts:1` (코멘트로만) |
| caller 박제 상태 | `// KOSAX-2293: extra-usage-core.ts deleted (claude.ai SaaS billing dead).` 헤더 + inline `Extra usage is not available in KOSAX` 메시지 반환 |
| `extra-usage.tsx` 박제 상태 | 동일 KOSAX-2293 헤더 + inline `runExtraUsage` 대체 (`onDone('Extra usage is not available in KOSAX. Usage is managed via FriendliAI.')`) |
| **DROP 결정 근거** | claude.ai SaaS subscription billing — Anthropic-only. KOSAX FriendliAI 단일 provider 와 무관. CC 의 `runExtraUsage` 는 Anthropic 계정 quota / overage gate 검사용으로, KOSAX 에서 implementable 하지 않음. |
| **PORT 가능성** | 0 — Anthropic-specific business logic. |

#### 2. `commands/rename/generateSessionName.ts`

| 항목 | 값 |
|---|---|
| CC sourcemap | `.references/claude-code-sourcemap/restored-src/src/commands/rename/generateSessionName.ts` (67 LOC) |
| KOSAX 측 | **부재** |
| KOSAX callers (grep `generateSessionName`) | 3 hits — `tui/src/commands/rename/rename.ts:19,20,38` + `tui/src/components/permissions/ExitPlanModePermissionRequest/ExitPlanModePermissionRequest.tsx:9,87` |
| `rename.ts` 박제 상태 | Line 19: `// KOSAX Spec 1633 / Epic #2293 — commands/rename/generateSessionName deleted (Anthropic queryHaiku auto-naming); inline no-op stub.` Line 20: `const generateSessionName = async (..._args: unknown[]): Promise<string \| null> => null` Line 38: `await generateSessionName(...)` 호출은 항상 null 반환 → 사용자가 직접 이름 지정 |
| `ExitPlanModePermissionRequest.tsx` 박제 상태 | Line 9: `// commands/rename/generateSessionName removed — Anthropic queryHaiku auto-naming is Anthropic-only (Spec 1633 / Epic #2293).` Line 87: `// no-op: generateSessionName (Anthropic queryHaiku) removed` |
| **DROP 결정 근거** | CC 의 `generateSessionName` 는 Anthropic Haiku LLM 으로 첫 turn 의 user prompt 를 요약해서 세션 자동 이름 생성. KOSAX 는 K-EXAONE 단일 LLM 이고 자동 세션 naming 은 P2 deferred (Spec 1633 결정). |
| **PORT 가능성** | 향후 K-EXAONE 으로 마이그레이션 가능하지만 별도 Epic. 본 epic 시점에서는 inline no-op stub 이 정답. |

#### 3. `commands/review/reviewRemote.ts`

| 항목 | 값 |
|---|---|
| CC sourcemap | `.references/claude-code-sourcemap/restored-src/src/commands/review/reviewRemote.ts` (316 LOC) |
| KOSAX 측 | **부재** |
| KOSAX callers (grep `reviewRemote`) | 1 hit — `tui/src/commands/review/ultrareviewCommand.tsx:1` (코멘트로만) |
| caller 박제 상태 | `// KOSAX-2293: reviewRemote.ts deleted (ultrareviewQuota + usage SaaS billing dead).` 헤더 + inline `Ultrareview remote sessions are not available in KOSAX` 메시지 반환 |
| **DROP 결정 근거** | CC 의 `reviewRemote` 는 claude.ai CCR (Claude Code Remote) backend 으로 PR review 를 원격 실행하는 경로. KOSAX 는 local-only 작동, 외부 egress 0 (AGENTS.md hard rule). 또한 ultrareviewQuota / overage SaaS billing 도 Anthropic-only. |
| **PORT 가능성** | 0 — claude.ai CCR backend 의존성 + KOSAX 의 local-only 원칙과 양립 불가. |

### 누락된 박제가 있는가?

**없음.** 위 표의 caller 5개 모두 KOSAX-2293 / Spec 1633 박제 헤더로 명시 처리됨. dangling reference 0.

검증 명령:

```bash
$ grep -rn "extra-usage-core\|generateSessionName\|reviewRemote" tui/src/ | wc -l
8  # 모두 박제 코멘트 또는 inline stub 코드만, 실제 import 0
```

### `decisions.md` 갱신 사항

`specs/cc-migration-audit/decisions.md § S5 Commands/Skills` 의 마지막 row:

- **기존**: `CC sourcemap gap 3파일 (extra-usage-core / generateSessionName / reviewRemote) → caller-graph 재검증 후 PORT 또는 DROP (Epic D 에서 처리).`
- **갱신**: `CC sourcemap gap 3파일 (extra-usage-core / generateSessionName / reviewRemote) → DROP 확정 (Epic #2640). caller-graph 박제 검증 완료 — specs/2640-s5-commands-skills/spec.md § Gap-3 Caller-Graph 박제.`

---

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| `commands/onboarding/index.ts` P0 stub 정리 | `commands.ts` import + COMMANDS array 등록 구조 — 단순 삭제 시 typecheck 회귀. Spec 1635 onboarding 의 진입점 분리 작업 필요. | Spec 1635 Phase 후속 | NEEDS TRACKING |
| `commands/install-github-app/types.ts`, `commands/plugin/types.ts`, `commands/plugin/unifiedTypes.ts` 정리 | type-only import dependency (`WorkflowMultiselectDialog.tsx` 등). dead-code elimination 필요. | Epic B (#2638) follow-up | NEEDS TRACKING |
| `INTERNAL_ONLY_COMMANDS` array + `process.env.USER_TYPE === 'ant'` gate 정리 | 본 epic 머지 후 ant gate 자체가 dead — 별도 정리 필요. | 다음 audit 라운드 | NEEDS TRACKING |
| K-EXAONE skill docs (Anthropic SDK 대체) | 사용자 결정 — KOSAX 가 K-EXAONE on FriendliAI docs 를 bundled skill 로 노출할지 미정. | 별도 epic | NEEDS TRACKING |
