# Feature Specification: KOSMOS-original UI Residue Cleanup (Epic β)

**Feature Branch**: `2293-ui-residue-cleanup`
**Created**: 2026-04-29
**Revised**: 2026-04-29 v2 (caller-graph 박제 후 전면 재작성 — v1 의 30 cleanup-needed 일괄 deletion 결정이 KOSMOS-needed file 까지 잘못 포함하여 광범위 회귀 위험 발견)
**Status**: Draft v2
**Input**: User description: "Epic β — Epic α (#2292, merged in `bc523b7`) audit 결과 30 Cleanup-needed 파일 + 6 KOSMOS-only Tool deletion candidates 를 정리해 Spec 1633 closure 와 Constitution II 준수 완료. v2: caller-graph 검증 후 진짜 Anthropic dispatcher 잔재만 cleanup."
**Authority** (cite in every downstream artefact):
- `AGENTS.md § CORE THESIS` — KOSMOS = AX-infrastructure callable-channel client (3rd thesis canonical)
- `.specify/memory/constitution.md § II Fail-Closed Security (NON-NEGOTIABLE)` — KOSMOS-invented permission classifications removed in Spec 1979 MUST NOT be reintroduced
- `specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 1.2.1, § 1.2.2, § 1.3.4`
- `specs/2292-cc-parity-audit/cc-parity-audit.md` — Epic α deliverable, this Epic 의 직접 입력
- `specs/2292-cc-parity-audit/data/modified-218-classification.json` — 30 Cleanup-needed 파일 list
- **`specs/2293-ui-residue-cleanup/data/caller-graph.json`** (new in v2) — 30 file × importer 그래프 + Anthropic-token + dependency-token 박제
- **`specs/2293-ui-residue-cleanup/data/disposition.json`** (new in v2) — file 별 DELETE/KEEP 결정 + risk 박제
- `.references/claude-code-sourcemap/restored-src/src/` — Claude Code 2.1.88 byte-identical source-of-truth (research-only)

---

## v1 → v2 변경 요약

v1 가설: 30 Cleanup-needed 모두 DELETE + utils/permissions 3 file + schemas/ui-l2/permission.ts 도 DELETE.

v2 검증 결과 (caller-graph.json):
- `utils/permissions/permissionSetup.ts` — **11 importer** (main.tsx, REPL, Config, plan.tsx 등 핵심) → KOSMOS-needed → **KEEP**
- `utils/permissions/permissions.ts` — **14 importer** (tools.ts registry, AgentTool, BashTool, REPL) → KOSMOS-needed → **KEEP**
- `schemas/ui-l2/permission.ts` — 5 importer (PermissionReceiptContext, ExportPdfDialog, export/consent commands, i18n/uiL2; Spec 035 receipt UX) → KOSMOS-needed → **KEEP** (또한 30 list 에 처음부터 포함되지 않았음)
- `tokenEstimation.ts` — 11 importer (sdk-compat + AWS Bedrock 의존) → DELETE + 11 caller cleanup (HIGH risk)
- 28 file (cli/print, commands/insights, generateSessionName, Feedback, services/api/* 16, toolUseSummaryGenerator, WebFetchTool/utils, dateTimeParser, yoloClassifier, mcpbHandler, sessionTitle, shell/prefix, tokenEstimation) — DELETE 유지

따라서 v2 의 deletion target = **28 file (30 cleanup-needed 중 28)**, KEEP target = **2 file (permissionSetup, permissions) + 1 file (ui-l2/permission, 30 list 외)**.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Spec 1633 Anthropic dispatcher closure (Priority: P1) 🎯 MVP

KOSMOS Lead 가 caller-graph.json + disposition.json 을 입력으로, 28 Anthropic dispatcher 잔재 file 을 deletion 하고 그 caller 를 cleanup 한다. 결과: KOSMOS TUI 에 Anthropic 1P API 잔재 + claude.ai SaaS 호출 + AWS Bedrock 의존 + growthbook A/B testing + queryHaiku/queryWithModel/verifyApiKey + @anthropic-ai/ import 0 잔존.

**Why this priority**: Spec 1633 (Anthropic→FriendliAI) closure 가 미완 상태로 4 callsite + 3,419 LOC dispatcher 가 alive 라는 점이 MEMORY.md `project_tui_anthropic_residue` 에 기록되어 있다. 본 cleanup 이 미완이면 K-EXAONE 단일 LLM provider 라는 KOSMOS thesis 가 실 코드에서 verify 되지 않는다.

**Independent Test**: cleanup 후 (a) 28 deletion target 모두 `git ls-files` 0 매칭, (b) `grep -rE 'queryHaiku|queryWithModel|verifyApiKey|@anthropic-ai/' tui/src/` 0 행, (c) `cd tui && bun typecheck` exit 0 + 0 errors, (d) `cd tui && bun test` baseline 대비 NEW failure 0 인 상태로 완료되면 통과.

**Acceptance Scenarios**:

1. **Given** disposition.json 의 28 DELETE list, **When** caller cleanup 후 `git rm`, **Then** 28 path 모두 git 에서 사라짐 + 11 caller cleanup (tokenEstimation) 진행 완료.
2. **Given** 8 callsite 의 함수 호출, **When** dead caller block 삭제 (또는 dead import 정리), **Then** `grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/` 0 행.
3. **Given** 16 file 의 `@anthropic-ai/` import, **When** 모든 import 라인 제거 (또는 KOSMOS 등가 type 으로 교체), **Then** `grep -rE '@anthropic-ai/' tui/src/` 0 행.
4. **Given** 28 file deletion + caller cleanup 완료, **When** `cd tui && bun typecheck` 실행, **Then** exit 0 + 0 errors.
5. **Given** typecheck 통과, **When** `cd tui && bun test` 실행 + baseline 비교, **Then** NEW failure 0.

---

### User Story 2 — KOSMOS-needed permissions infrastructure 보존 박제 (Priority: P2)

v1 spec 가 잘못 deletion target 으로 잡았던 `utils/permissions/{permissionSetup, permissions}.ts` 두 file 이 KOSMOS-needed 임을 caller-graph + disposition.json + decision-log.md 에 박제한다. 보존 결정의 사유 + 11+14 importer 박제 + Constitution II 와의 충돌 부재 박제.

**Why this priority**: v1 spec 의 가설 ("Spec 033 잔재 3 file deletion") 이 caller-graph 미검토로 KOSMOS-needed CC permissions 인프라까지 잘못 포함. 본 US 가 그 회귀 가능성을 차단하고 Constitution II 가 KOSMOS-invented 권한 분류 (5-mode spectrum / pipa_class / auth_level / permission_tier / is_personal_data / is_irreversible / requires_auth / dpa_reference) 를 NON-NEGOTIABLE 하게 금지한다는 원칙은 별도 audit 영역으로 분리.

**Independent Test**: (a) 두 file 의 11+14 importer 가 caller-graph.json 에 박제, (b) decision-log.md 에 KEEP + rationale + Constitution II 비충돌 박제, (c) `utils/permissions/yoloClassifier.ts` 는 별도 DELETE 결정 (Anthropic + growthbook 의존).

**Acceptance Scenarios**:

1. **Given** caller-graph.json 의 permissionSetup 11 importer + permissions 14 importer, **When** disposition.json 에 KEEP 결정 + 사유 박제, **Then** decision-log.md 의 § Cleanup Targets 표에 두 file 의 KEEP 행 + Authority cite (caller-graph.json) 박제.
2. **Given** Constitution II 의 KOSMOS-invented 권한 분류 금지 토큰, **When** 두 file 의 본문 token-hit 검사 (caller-graph.json `internal_anthropic_tokens` + dependency_hits 모두 0), **Then** Constitution II 비충돌 박제 — KEEP 결정 무위험.
3. **Given** yoloClassifier.ts 의 sdk-compat + growthbook 의존, **When** disposition.json 에 DELETE 결정 + 2 caller cleanup, **Then** 별도 처리 (US1 의 일부).

---

### User Story 3 — Spec 035 UI L2 receipt schema 보존 박제 (Priority: P3)

v1 spec 의 FR-004 + US2 가 잘못 deletion target 으로 잡았던 `schemas/ui-l2/permission.ts` 가 Spec 035 UI L2 receipt UX 의 정상 사용 부분임을 박제한다. caller graph 5 importer (PermissionReceiptContext, ExportPdfDialog, export/consent commands, i18n/uiL2) 가 Spec 035 receipt 출력 구성 — Constitution II 의 KOSMOS-invented 5-mode spectrum 잔재 와 별개.

**Why this priority**: 30 Cleanup-needed list 에 처음부터 포함되지 않은 file 이지만, v1 spec 가 임의로 deletion target 으로 추가한 결정이 Constitution II 와 Spec 035 receipt UX 의 구별 부재에서 비롯. 본 US 가 그 구별을 명시적으로 박제.

**Independent Test**: schemas/ui-l2/permission.ts 의 5 importer 모두 KOSMOS-needed 박제 + decision-log.md 에 KEEP + Constitution II 비충돌 사유 박제.

**Acceptance Scenarios**:

1. **Given** schemas/ui-l2/permission.ts 의 5 importer (PermissionReceiptContext, ExportPdfDialog, export, consent, i18n/uiL2), **When** caller-graph.json + disposition.json 에 박제, **Then** decision-log.md 의 § ui-l2/permission Decision 행이 KEEP + 사유 ("Spec 035 receipt UX, not Spec 033 spectrum residue") + Authority cite (caller-graph.json + disposition.json) 박제.
2. **Given** PermissionLayerT/PermissionDecisionT 의 정의 위치 (schemas/ui-l2/permission.ts), **When** 그 type 들이 receipt UX 구성에만 사용되는지 검사 (caller 5 file 모두 receipt 출력), **Then** Constitution II 의 5-mode spectrum 잔재 카테고리 와 분리됨을 박제.

---

### Edge Cases

- **callsite 가 import 만 하고 실제 호출이 없는 dead import**: import 라인만 제거, 본문 변경 없음. typecheck 가 unused-import 를 잡아주므로 자동 검출.
- **deletion 후 typecheck/test 깨짐**: caller cleanup 누락 → 추가 caller 정리 또는 disposition 재검토. caller-graph.json 의 `importers` list 가 truth source.
- **0 importer 인 large file (cli/print 5601 line, commands/insights 3164 line) 이 dynamic registration 으로 alive 가능**: typecheck 통과 후 `bun run build` 또는 `bun run tui` 으로 entry-point 검증. 깨지면 재분류 (KEEP 또는 partial).
- **bun test 의 pre-existing failure 가 변동될 경우**: baseline 이전 실패 (snapshot 1건) 가 그대로 유지되어야 함; 새로운 import 누락 등으로 실패 양상이 바뀌면 NEW failure 로 간주.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: disposition.json 의 28 DELETE target 100% 가 cleanup 완료. `git ls-files tui/src/` 출력에 28 path 모두 0 회 잔존. (caller-graph.json `importer_count` ≥ 1 인 file 은 caller cleanup 도 동시 진행 — 16 file)
- **FR-002**: 8 callsite (queryHaiku / queryWithModel / verifyApiKey) 모두 `grep -rE 'queryHaiku|queryWithModel|verifyApiKey' tui/src/` 결과 0 행.
- **FR-003**: disposition.json 의 3 KEEP target 보존 — `utils/permissions/permissionSetup.ts`, `utils/permissions/permissions.ts`, `schemas/ui-l2/permission.ts`. decision-log.md 의 표에 KEEP + rationale + caller-graph evidence + Constitution II 비충돌 박제.
- **FR-004**: ~~v1 의 schemas/ui-l2/permission.ts deletion 결정 폐기~~ — caller graph 5 importer 박제로 KEEP. (FR-003 에 통합)
- **FR-005**: 6 KOSMOS-only Tool DELETE 결정은 sonnet 1차 commit (`2f9663d`) 에서 이미 완료. decision-log.md § KOSMOS-only Tool Decisions 표에 6 entry 박제 (이미 존재). 본 Epic 에서 추가 작업 없음.
- **FR-006**: `cd tui && bun typecheck` 가 `0 errors` 를 출력. (FR-001~FR-003 완료 후)
- **FR-007**: `cd tui && bun test` 의 NEW failure 가 0 (baseline 비교).
- **FR-008**: Spec 1633 closure grep gate (call-site invariant) — `grep -rE '(verifyApiKey|queryHaiku|queryWithModel)\(' tui/src/` 결과 0 행 (호출 패턴 0, comment / stub function 정의는 허용). `grep -rE '@anthropic-ai/' tui/src/` 매치는 (a) `tui/src/sdk-compat.ts` (Anthropic SDK type-only shim), (b) `tui/src/mcpb-compat.ts` (KOSMOS Spec #2293 신규 shim — `@anthropic-ai/mcpb` lazy-import + type-only), (c) `tui/src/sandbox-runtime-compat.ts` (KOSMOS Spec #2293 신규 shim — `@anthropic-ai/sandbox-runtime` re-export) 3 KOSMOS-shim 만 허용. (Constitution II 의 KOSMOS-invented 토큰 검사는 별도 audit 영역으로 분리; v1 의 광범위 token list 가 plugin-init.ts/VerifyPrimitive.ts 의 합법 사용까지 잘못 잡았던 결함 보정)
- **FR-009**: 본 Epic 의 모든 commit message 와 spec 산출물이 (a) AGENTS.md / Constitution / cc-source-scope-audit / cc-parity-audit 4 reference + (b) caller-graph.json + disposition.json 인용.
- **FR-010**: `tui/src/` 하위 모든 file 의 `@anthropic-ai/` import 가 제거되거나 KOSMOS shim 으로 교체. 14 file (caller-graph.json 박제 + grep 검증). 잔존 매치는 KOSMOS shim 3 file (`sdk-compat.ts`, `mcpb-compat.ts`, `sandbox-runtime-compat.ts`) 만 — 이들은 KOSMOS 가 의도적으로 도입한 shim 으로 caller 가 `@anthropic-ai/*` 를 직접 import 하지 않고 shim 만 import 하도록 통일.

### Key Entities

- **CleanupTarget**: 단위 cleanup 대상 — `kosmos_path`, `disposition` (`DELETE` / `KEEP`), `importer_count`, `importers`, `internal_anthropic_tokens`, `dependency_hits`, `caller_cleanup_required`, `risk` (`LOW` / `MEDIUM` / `HIGH` / `N/A`), `rationale`. caller-graph.json + disposition.json 에 박제.
- **CallerGraph**: 30 Cleanup-needed file × importer 매트릭스 — `kosmos_path` → `importers[]` + `dependency_hits` (sdk-compat / @aws-sdk/client-bedrock-runtime / claude.ai / growthbook / feature() 등).
- **DispositionMatrix**: 30 file 의 v2 결정 — DELETE/KEEP + risk + rationale + caller_cleanup_required.
- **TestBaseline**: cleanup 직전의 `bun test` 결과 — `total`, `pass`, `fail`, `failure_test_ids`.
- **CallsiteMigration**: 8 queryHaiku/etc callsite 의 변환 기록 — `kosmos_path`, `original_call`, `replacement` (DELETE caller block / DELETE import-only / `feature_deleted`).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: disposition.json 의 28 DELETE target 100% 완료 (`git ls-files` 검증) + 16 caller cleanup 완료.
- **SC-002**: 8 callsite 0 회 잔존 (`grep` 검증).
- **SC-003**: disposition.json 의 3 KEEP target (permissionSetup, permissions, ui-l2/permission) 보존 + decision-log.md 박제.
- **SC-004**: 6 KOSMOS-only Tool deletion 완료 박제 (sonnet 1차 commit `2f9663d` 에 박제).
- **SC-005**: `bun typecheck` exit 0, 0 errors.
- **SC-006**: `bun test` NEW failure 0 (baseline 대비).
- **SC-007**: FR-008 Spec 1633 closure grep gate 0 행 매치.
- **SC-008**: PR `Closes #2293` 단독 / Conventional Commits PR title 통과 / 14 required CI checks 모두 PASS / Codex P1 0건 또는 모두 resolved.
- **SC-009** (NEW v2): caller-graph.json + disposition.json 이 commit 에 포함 + spec.md / quickstart.md / decision-log.md 가 두 file 을 cite.

---

## Assumptions

- Epic α #2292 (merged in `bc523b7`) 의 Cleanup-needed 분류는 caller graph 미검토라 30 file 중 일부 KOSMOS-needed 가 잘못 포함됨 (permissionSetup / permissions). v2 spec 가 caller-graph.json 박제로 진짜 dead 만 deletion target.
- `bun test` baseline 측정은 cleanup 시작 직전에 수행 (sonnet 1차 commit `2f9663d` 직후 상태 기준), 결과를 `specs/2293-ui-residue-cleanup/baseline-test.txt` 에 박제 (이미 박제됨).
- 6 KOSMOS-only Tool 모두 DELETE 결정 (research.md § R-4) — sonnet 1차에서 이미 완료, 별도 검증 불필요.
- Spec 035 receipt ledger 는 백엔드 Python (`src/kosmos/permissions/ledger.py`) + TUI side 의 `schemas/ui-l2/permission.ts` (PermissionLayerT/PermissionDecisionT) — TUI side 의 receipt 출력 컴포넌트는 KOSMOS-needed.
- `claude.ts` / `client.ts` 는 0 importer 박제 (caller-graph.json) — 안전 deletion. sonnet 1차의 modify 결정은 caller graph 검증 없이 추정한 것이며 v2 가 정정.
- 본 Epic 작업은 `/Users/um-yunsang/KOSMOS-w-2293/` worktree 에서 진행되며 main worktree 와 file conflict 없음 (각자 독립 working dir).

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **백엔드 Python (`src/kosmos/permissions/`) 정리**: Epic δ #2295 territory — 본 Epic 은 TUI 만 다룸.
- **5-primitive 를 CC `Tool.ts` 에 align**: Epic γ #2294 territory.
- **AdapterRealDomainPolicy Pydantic 모델 + 18 어댑터 metadata 마이그레이션**: Epic δ #2295.
- **AX-infrastructure mock 어댑터 신설**: Epic ε #2296.
- **KOSMOS-only ADDITIONS 274 파일의 추가 audit**: Epic α 가 KEEP/Modified 만 다뤘듯, 본 Epic 도 Cleanup-needed 만 처리.
- **Spec 287 TUI 인프라 (i18n/ipc/theme/observability/ssh) 변경**: Spec 1979 후속이며 본 Epic 범위 외.
- **`utils/permissions/{permissionSetup, permissions}` 안의 dead `feature()` 제거**: file KEEP 결정으로 작업 종료. 안 쪽 파편 cleanup 은 별도 spec (in-file dead-flag cleanup, ≠ file-level deletion).
- **`schemas/ui-l2/permission.ts` 의 Constitution II 정합성 추가 audit**: 5 importer 모두 Spec 035 receipt UX 라는 caller-graph 박제로 본 Epic 종료. 추후 receipt UX 자체의 Constitution II 정합성 audit 은 별도 spec.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| `utils/permissions/{permissionSetup, permissions}` 안의 dead `feature()` 제거 (12 + 7 occurrences) | 본 Epic 은 file 단위 KEEP/DELETE 결정. in-file dead-flag cleanup 은 Spec 1633 후속 또는 Epic ζ smoke 영역 | Spec 1633 후속 또는 Epic ζ #2297 | TBD (이번 Epic merge 후 issue 생성) |
| K-EXAONE 한국어 자동 명명 (deleted `generateSessionName.ts` 대체) | 본 Epic 은 deletion 만; migrate 별도 spec | Future Epic | TBD |
| K-EXAONE 한국어 도구 사용 요약 (deleted `toolUseSummaryGenerator.ts` 대체) | 동상 | Future Epic | TBD |
| K-EXAONE WebFetch 결과 한국어 요약 (deleted `WebFetchTool/utils.ts` 대체) | 동상 | Future Epic | TBD |
| Constitution II 의 KOSMOS-invented 권한 분류 잔재 audit (`tui/src/` 전체) | 본 Epic 은 30 Cleanup-needed 만 다룸; 274 KOSMOS-only ADDITIONS 의 Constitution II 정합성 audit 은 별도 spec | Spec 1979 의 후속 또는 Epic ζ | TBD |
