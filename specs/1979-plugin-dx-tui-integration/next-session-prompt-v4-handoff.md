# 다음 세션 시작 프롬프트 — Initiative #2290 핸드오프 (Epic β / δ WIP 상태)

**작성일**: 2026-04-29 (이전 세션 종료 시점)
**상태**: Epic α 머지 완료. Epic β + δ 병렬 시도 중 두 Sonnet teammates 모두 컨텍스트 한계로 미완. 사용자가 옵션 1 (보존, push 금지) 선택.

이전 세션 보존 산출물 — `next-session-prompt.md` (v3) 도 그대로 유효한 base 문서. 본 파일은 v3 위에 진행된 Epic β / δ 의 partial 상태를 핸드오프.

---

## 머지된 결과 (main 에 반영)

- **Epic α #2292** — `feat(2292): cc parity audit deliverable for Epic α` PR #2320 머지 (commit `bc523b7`).
  - Audit 결과: 218 modified files (188 Legitimate / 30 Cleanup-needed / 0 Suspicious), 50/50 spot-check, 67/67 import-only confirmed.
  - 30 Cleanup-needed list 가 Epic β 의 직접 입력이 됨 (`specs/2292-cc-parity-audit/data/modified-218-classification.json`).
  - 21 sub-issues (#2299–#2318 closed + #2319 deferred OPEN).

---

## Epic β #2293 (UI residue cleanup) — WIP 보존 / push 금지

### 위치

- **Worktree**: `/Users/um-yunsang/KOSMOS-w-2293/`
- **Branch**: `2293-ui-residue-cleanup` (local only, **NOT pushed to remote**)
- **Commits on top of main**:
  1. `2f9663d` — Sonnet 1차 진척 (verified 안전, ~30%)
  2. `10d9754` — Sonmet 2차 finisher 의 광범위 변경 (**scope review 필요**)

### Lead spec 사이클 결과 (이미 박제, 신뢰 가능)

`specs/2293-ui-residue-cleanup/` 아래:
- spec.md (10 FR / 8 SC / 3 user stories)
- plan.md (Constitution Check PASS)
- research.md (R-1~R-5 incl. callsite + 6-Tool decision matrices)
- data-model.md (4 entities)
- quickstart.md (R1~R7)
- tasks.md (T001-T020 — Sonnet 가 [X] 마크했지만 actual 실행은 일부만 완료)
- checklists/requirements.md (16/16 PASS)
- decision-log.md (Sonnet 1차 작성, services/api 17 + 5 callsite 결정 박제)
- baseline-typecheck.txt + baseline-test.txt (T001 baseline)

### Sonnet 1차 (`2f9663d`) — 검증된 안전 진척 30%

- 6 KOSMOS-only Tool 디렉토리 (Monitor / ReviewArtifact / SuggestBackgroundPR / Tungsten / VerifyPlanExecution / Workflow) 의 9 file deletion
- 5 callsite cleanup (cli/print, commands/insights, components/Feedback, utils/mcp/dateTimeParser, utils/sessionTitle)
- `services/api/claude.ts` modify (Spec 2077 KOSMOS-needed pure utility exports preserved; verifyApiKey/queryHaiku/queryWithModel functions removed)

### Sonnet 2차 finisher (`10d9754`) — 광범위 변경, scope review 필요

`10d9754` 의 36 file 변경:
- spec dir 의 after-test.txt + after-typecheck.txt 추가 (verification 산출물)
- spec.md 가 명시한 범위:
  - `tui/src/services/api/{claude,client}.ts` modify
  - `tui/src/sdk-compat.ts` modify
  - `tui/src/services/toolUseSummary/toolUseSummaryGenerator.ts` modify
  - `tui/src/tools/WebFetchTool/utils.ts` modify
  - `tui/src/utils/{cleanup,doctorDiagnostic,plugins/mcpbHandler,plugins/schemas,sessionTitle,shell/powershellProvider,shell/prefix}.ts` modify
  - `tui/src/utils/mcp/dateTimeParser.ts` modify
  - `tui/src/cli/{print,update}.ts` modify
  - `tui/src/commands/{insights,rename/generateSessionName}.ts` modify
  - `tui/src/components/Feedback.tsx` modify
  - `tui/src/schemas/ui-l2/permission.ts` modify
  - `tui/src/tools.ts` modify (registry cleanup)
  - `tui/src/constants/tools.ts` modify
- spec.md 가 명시 안 한 영역 (out-of-scope risk):
  - `tui/src/components/sandbox/SandboxDependenciesTab.tsx`
  - `tui/src/i18n/uiL2.ts`
  - `tui/src/ipc/{llmClient,llmTypes}.ts`
  - `tui/src/screens/REPL.tsx`
  - `tui/src/skills/bundled/claudeApi.ts`
  - `tui/src/tools/VerifyPrimitive/VerifyPrimitive.ts`
  - `tui/src/utils/dxt/helpers.ts`
  - `tui/src/utils/nativeInstaller/{installer,packageManagers}.ts`
  - `tui/src/utils/sandbox/sandbox-adapter.ts`
  - `tui/tsconfig.json`

### 미완 사항

- **services/api 17 잔재 file 그대로** (claude.ts 만 modify; 다른 16 file 은 deletion 안 됨에도 list 가 spec.md FR-001 의 17 deletion target 임)
- **FR-008 grep gate 19 매치 잔존** (목표 0)
- **commit/push/PR 0**

### 다음 세션 권장 처리

1. `git reset --hard 2f9663d` 으로 Sonnet 2차 finisher 의 광범위 변경 폐기.
2. spec.md 의 작업 범위를 Sonnet 1차 + 잔여 단순 deletion 으로 좁힘 (services/api 16 file deletion + utils/permissions 3 file deletion 등).
3. Lead 가 직접 deletion 만 진행 (Edit 없이 `git rm`만, 컨텍스트 절약).
4. typecheck + bun test verify → commit + push + PR.

또는 사용자가 다른 결정 권고.

---

## Epic δ #2295 (Backend permissions cleanup + AdapterRealDomainPolicy) — WIP 보존 / push 금지

### 위치

- **Worktree**: `/Users/um-yunsang/KOSMOS-w-2295/`
- **Branch**: `2295-backend-permissions-cleanup` (local only, **NOT pushed**)
- **Commits**:
  1. `97b85d1` — Sonnet 1차 (~70% 진척 안전)
  2. `553bb62` — Sonnet 2차 finisher (test 17 deletion 안전)

### Lead spec 사이클 결과 (이미 박제, 신뢰 가능)

`specs/2295-backend-permissions-cleanup/` 아래 spec/plan/research/data-model/quickstart/tasks/checklists/adapter-migration-log + baseline-pytest.txt.

### Sonnet 1차 (`97b85d1`) — 검증된 안전 진척

- `src/kosmos/tools/models.py`: `AdapterRealDomainPolicy` Pydantic v2 모델 추가 (frozen=True, extra="forbid", 4 fields)
- 19 어댑터 metadata 마이그레이션:
  - KOROAD ×2 (accident_hazard_search, koroad_accident_search)
  - KMA ×6 (forecast_fetch, kma_current_observation, kma_pre_warning, kma_short_term_forecast, kma_ultra_short_term_forecast, kma_weather_alert_status)
  - HIRA ×1 (hospital_search)
  - NMC ×1 (emergency_search)
  - NFA119 ×1 (emergency_info_service)
  - SSIS ×1 (welfare_eligibility_search)
  - Mock data_go_kr ×1 (fines_pay)
  - Mock mydata ×1 (welfare_application)
  - Mock verify_* ×6 (digital_onepass, ganpyeon_injeung, geumyung_injeungseo, gongdong_injeungseo, mobile_id, mydata)
- caller-side updates (errors / executor / mvp_surface / registry / routing_index / search.py)

### Sonnet 2차 finisher (`553bb62`) — test deletion 안전

- `tests/permissions/` 의 17 잔재 test file deletion (Spec 033 importer test cleanup)
- conftest.py + test_ledger_verify_cli.py adjust
- `tests/tools/test_gov_api_tool_extensions.py`, `tests/tools/test_registry_invariant.py`, `tests/unit/security/test_spec_024_025_preserved.py`, `tests/unit/test_gov_api_tool_extensions.py` 삭제 — **scope review 필요** (Spec 024/025 test 일부 관련 가능성)

### 신규 발견 (spec.md FR-008 grep gate 정밀화 필요)

`auth_level` / `is_irreversible` / `requires_auth` / `dpa_reference` 토큰이 KOSMOS-needed 인프라에서 광범위 합법 사용 중:
- `src/kosmos/tools/permissions.py` — Spec 025 v6 invariant (auth_type ↔ auth_level 매트릭스)
- `src/kosmos/security/audit.py` — Tool security audit (Spec 024)
- `src/kosmos/plugins/cli_init.py` — Plugin init template (auth_level="AAL1" default)
- `src/kosmos/plugins/checks/q3_security.py` — Plugin Q3-V3/V4/V6 invariant 검사
- `src/kosmos/plugins/tests/test_namespace_invariant.py` — Plugin test fixtures

`SessionContext` (auth_level: int field) 도 KOSMOS-needed:
- `src/kosmos/recovery/auth_refresh.py` — credential resolution
- `src/kosmos/cli/{app,repl}.py` — REPL session bootstrap

→ **spec.md FR-008 의 grep gate 가 너무 광범위; spec 보정 필요 (어댑터 metadata 의 KOSMOS-invented `auth_level` 만 잡도록 정밀화)**.

### 미완 사항

- **잔재 17 source file 그대로** (`src/kosmos/permissions/` 의 aal_backstop / adapter_metadata / bypass / cli / killswitch / models / modes / pipeline / pipeline_v2 / prompt / rules / session_boot / synthesis_guard + steps/ 디렉토리)
- `__init__.py` 재작성 (Spec 035 receipt set + credentials/SessionContext 만 export 하도록) 안 됨
- `tests/tools/test_adapter_real_domain_policy.py` 5 단위 테스트 추가 안 됨
- pytest verify / commit / push / PR 0
- **spec.md FR-008 grep gate 정밀화 (보정)**

### 다음 세션 권장 처리

1. spec.md 보정 — FR-008 grep gate 를 어댑터 metadata 영역 (`src/kosmos/tools/`) 으로 좁히고 KOSMOS-needed 영역 (`src/kosmos/security/audit.py`, `src/kosmos/plugins/checks/q3_security.py` 등) 을 명시 제외.
2. SessionContext 보존 결정 (models.py 통째 삭제 X, SessionContext 만 keep).
3. 잔재 16 source file + steps/ deletion (importer 추적 후, models.py + credentials.py 보존).
4. `__init__.py` 재작성: credentials + models.SessionContext + Spec 035 receipt set 만 export.
5. 5 단위 테스트 추가 (test_adapter_real_domain_policy.py).
6. pytest baseline diff verify.
7. commit + push + PR.

---

## Worktree state

```bash
$ git worktree list
/Users/um-yunsang/KOSMOS         bc523b7 [main]
/Users/um-yunsang/KOSMOS-w-2293  10d9754 [2293-ui-residue-cleanup]
/Users/um-yunsang/KOSMOS-w-2295  553bb62 [2295-backend-permissions-cleanup]
```

두 branch 모두 **remote 에 push 되지 않음** (옵션 1 보존). PR 도 없음.

다음 세션이 진입 시 worktree 그대로 사용 가능.

---

## GitHub state

- Initiative #2290 OPEN — Epic α #2292 CLOSED (sub-issue), Epic β #2293 OPEN, Epic δ #2295 OPEN, Epic γ ε ζ η 모두 OPEN
- Epic β #2293 sub-issues: 21 (#2321–#2340 + #2361 deferred) 모두 OPEN
- Epic δ #2295 sub-issues: 21 (#2341–#2360 + #2362 deferred) 모두 OPEN

다음 세션 PR 머지 시점 sub-issues close 진행.

---

## 핸드오프 메모

### 가장 큰 방법론 교훈 (다음 세션 적용 필수) — Two-layer Parallelism

```
Initiative
├─ Epic β  →  Lead Opus β  +  Sonnet team β (sonnet-B1, B2, B3)
└─ Epic δ  →  Lead Opus δ  +  Sonnet team δ (sonnet-D1, D2, D3)
```

**Layer 1 (Epic 단위)**: 각 Epic 마다 **별도 Lead Opus 1명** 배정. 의존성 없는 Epic 들 동시 진행 시 = N Lead Opus 가 별도 session/worktree 에서 동시 작동. **"1 Lead Opus = N Epic" 금지** — Lead 컨텍스트 한계.

**Layer 2 (Task 단위)**: 각 Epic 의 Lead 가 `/speckit-implement` 시 **Sonnet teammates 의 Agent Team** 꾸림. dispatch 단위 = task/task-group (≤ 5 task / ≤ 10 file). **"1 Sonnet teammate = 1 Epic" 금지** — sonnet 컨텍스트 한계. `[P]` 마커 = 즉시 병렬 신호. Sonnet 책임 = 코드 변경 + WIP commit 만; push/PR/CI/Codex 는 Lead.

이번 세션이 두 번 (Epic β + δ) 실패한 진짜 원인 = **두 layer 모두 위반**: Lead 1명 (이 conversation) 이 Epic α 머지 후 Epic β + δ 둘 다 spec-cycle 진행 → Lead 컨텍스트 부담 + 그 Lead 가 각 Epic 을 1 sonnet teammate 에게 통째 위임 → sonnet 도 컨텍스트 한계.

- 박제 위치:
  - `AGENTS.md § Agent Teams` (Layer 1 + Layer 2 섹션, 2026-04-29)
  - `~/.claude/projects/.../memory/feedback_dispatch_unit_is_task_group.md` (★★★ 최상위 우선 메모)
- 다음 세션 진입 시 반드시:
  1. Epic β 와 Epic δ 를 **각각 별도 Lead Opus session 으로 분리** (`/clear` 후 사용자가 두 세션 각자 진입, 또는 한 session 에서 한 Epic 만 처리)
  2. 각 Lead 가 자기 Epic 의 `specs/<feature>/dispatch-tree.md` 작성
  3. 그 dispatch tree 에 따라 ≤ 5 task / ≤ 10 file 단위로 Sonnet teammates 병렬 dispatch
  4. 모든 teammate 완료 후 Lead 가 push/PR/CI/Codex 처리

### 도메인 교훈

- `auth_level` 광범위 합법 사용 발견은 Initiative #2290 전체 thesis 검토 입력. KOSMOS thesis 의 "기관 정책 cite only" 와 Spec 024/025 의 "auth_level 매트릭스 invariant" 가 양립할 수 있는 형태로 spec 보정 필요.
- Epic γ #2294 (5-primitive align with CC Tool.ts) 진입 전 Epic β + δ 정리 권장.

### Epic β + δ 재진입 시 dispatch tree (권장)

**Epic β 재진입**:
```
Lead solo: hard-reset to 2f9663d (sonnet 2차 광범위 변경 폐기)
            ↓
sonnet-A: T006 (16 services/api file deletion via git rm only)
sonnet-B: T010+T011 (utils/permissions 3 + ui-l2/permission deletion)
sonnet-C: T014 (tools.ts registry + REPL.tsx + constants/tools.ts cleanup)
            ↓ (병렬, 각 ≤ 5 file)
Lead solo: T009+T012+T015+T018 (grep gates) + T016+T017 (typecheck/test) + T019+T020 (commit/push/PR/CI)
```

**Epic δ 재진입**:
```
Lead solo: spec.md FR-008 보정 (auth_level grep gate 를 src/kosmos/tools/ adapter metadata 영역으로만 좁힘)
            ↓
sonnet-D: T005-T006 (잔재 16 file deletion + steps/ — 단 models.py KEEP, credentials.py KEEP)
sonnet-E: T007 (__init__.py 재작성)
sonnet-F: T010 (5 unit test 추가)
            ↓ (병렬, 각 ≤ 5 file)
Lead solo: T008+T018 (grep gates + pytest verify) + T019+T020 (commit/push/PR/CI)
```

총 6 sonnet 병렬 + Lead 4 sequential phase. 한 sonnet 도 컨텍스트 한계 안 만남.
