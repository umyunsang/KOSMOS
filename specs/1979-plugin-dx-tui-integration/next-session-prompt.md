# 다음 세션 시작 프롬프트 — Initiative #2290 Phase α-η 진입

**사용법**: 새 세션 시작 후 아래 코드블록 내용을 복사해서 그대로 붙여넣기.

**컨텍스트**: AGENTS.md § CORE THESIS + canonical sources는 자동 로드됨. 메모리도 자동 로드. 이 프롬프트는 작업 진입에 필요한 specific context + invocation만 담음.

---

## 프롬프트 (복사 후 paste)

```text
/speckit-specify --feature 2290-ax-infrastructure-caller-refactor

# 목표

Initiative #2290 (KOSMOS · AX Infrastructure Callable-Channel Client Reference Implementation) 의 Epic #2291 (AX Infrastructure Caller Refactor (Phase α-η)) 을 spec-driven으로 정형화. 7 Phase sub-issues #2292-#2298 모두 cover하는 단일 통합 spec.

# Authority — 반드시 인용 (per memory `feedback_check_references_first`)

- `AGENTS.md § CORE THESIS` — 3차 thesis final canonical (KOSMOS = AX-infrastructure callable-channel client)
- `specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md` — 2,090 KOSMOS files vs 1,884 CC files 분류 + 7-phase plan (이번 spec의 base)
- `specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12` — 정정된 architecture (FINAL CANONICAL)
- `specs/1979-plugin-dx-tui-integration/domain-harness-design.md` — 16-도메인 매트릭스 + 5점 충실도
- `specs/1979-plugin-dx-tui-integration/cc-source-migration-plan.md` — CC 원본 file-by-file
- `.references/claude-code-sourcemap/restored-src/` — CC 2.1.88 byte-identical source-of-truth
- `docs/vision.md` + `docs/requirements/kosmos-migration-tree.md` — L1 pillars + UI L2

# Scope — 7 Phase 통합

본 spec은 **Phase α부터 Phase η까지 7개 phase를 단일 spec으로 통합** (각 phase가 user story가 됨). 별도 spec 7개 분리하지 않음 — Epic #2291 single integrated PR이 목표.

각 Phase의 자세한 deliverable + acceptance criteria + risk profile은 GitHub sub-issues #2292-#2298 본문 + `cc-source-scope-audit.md § 3` 참조. 그대로 spec.md User Story로 변환.

## Phase α (#2292) — CC parity audit (read-only)
**Goal**: 1,604 KEEP 파일이 진짜 byte-identical인지 spot-check + 212 modified 파일 정당성 audit.
**Deliverable**: `specs/<spec>/cc-parity-audit.md` — KEEP / MODIFIED / SUSPECT 분류
**Risk**: 0 (read-only)
**Acceptance**: audit doc complete; suspicious modifications flagged

## Phase β (#2293) — KOSMOS-original UI residue cleanup
**Goal**: Spec 033/1979 잔재 정리 — `tui/src/schemas/ui-l2/permission.ts` 평가, 6 KOSMOS-only Tool 삭제 후보 (Monitor/ReviewArtifact/SuggestBackgroundPR/Tungsten/VerifyPlanExecution/Workflow) 결정, 잔여 utils/permissions/ 정리
**Risk**: 낮음
**Acceptance**: bun typecheck 0, bun test no NEW failures, 6 후보 모두 결정

## Phase γ (#2294) — 5-primitive를 CC Tool.ts 인터페이스 정확 align
**Goal**: 4 primitive (Lookup/Submit/Verify/Subscribe) 을 CC `Tool` 인터페이스 (name/description/inputSchema/call/render*) 따라 refactor. Reference: `tui/src/tools/AgentTool/AgentTool.tsx`
**Deliverable**: `tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive/*` 재작성, ToolRegistry boot 검증, BM25 + EXAONE function calling 라운드트립, PTY smoke (시민 "의정부 응급실 알려줘")
**Risk**: 중간 — registry boot 깨질 수 있음
**Acceptance**: bun + uv 회귀 0, PTY smoke 통과 (text log)

## Phase δ (#2295) — 백엔드 permissions/ 정리 + AdapterRealDomainPolicy
**Goal**:
- `src/kosmos/permissions/` 25 파일 정리: ~20 DELETE (Spec 033 KOSMOS-original — modes.py, models.py, pipeline_v2.py, etc.), ~5 KEEP (Spec 035 영수증 ledger — ledger.py, action_digest.py, hmac_key.py, canonical_json.py, audit_coupling.py, ledger_verify.py, otel_emit.py, otel_integration.py)
- `AdapterRealDomainPolicy` Pydantic 모델 신설 in `src/kosmos/tools/models.py`
- 18 어댑터 메타 마이그레이션: 제거 (`auth_level`, `pipa_class`, `is_personal_data`, `dpa_reference`, `is_irreversible`, `requires_auth`) + 추가 (`real_classification_url`, `real_classification_text`, `citizen_facing_gate`, `last_verified`)
**Risk**: 낮음 (TUI Wave 1-3 패턴 재활용)
**Acceptance**: uv pytest 회귀 0, 모든 어댑터에 non-empty `real_classification_url`

## Phase ε (#2296) — AX-infrastructure mock 어댑터 신설
**Goal**: 9 신규 mock + DelegationToken schema (`delegation-flow-design.md § 12.7` 기준)
- `src/kosmos/primitives/delegation.py` (DelegationToken + DelegationContext)
- 5 verify modules: `mock_verify_module_simple_auth`, `mock_verify_module_modid`, `mock_verify_module_kec`, `mock_verify_module_geumyung`, `mock_verify_module_any_id_sso` (디지털원패스 후속)
- 3 submit modules: `mock_submit_module_hometax_taxreturn`, `mock_submit_module_gov24_minwon`, `mock_submit_module_public_mydata_action`
- 2 lookup modules: `mock_lookup_module_hometax_simplified`, `mock_lookup_module_gov24_certificate`
- DELETE: `mock_verify_digital_onepass` (서비스 종료 2025-12-30)
- 모든 15 mock에 6 transparency 필드: `_mode`, `_reference_implementation: "ax-infrastructure-callable-channel"`, `_actual_endpoint_when_live`, `_security_wrapping_pattern`, `_policy_authority: "국가AI전략위원회 행동계획 2026-2028 §공공AX"`, `_international_reference: "Singapore APEX"`
**Risk**: 낮음 (mock-only, 외부 의존 X)
**Acceptance**: 9 신규 mock test 통과, ToolRegistry 27 도구 (12 Live + 15 Mock + resolve_location)

## Phase ζ (#2297) — E2E smoke + 정책 매핑 문서
**Goal**:
- PTY scenario: 시민 "종합소득세 신고해줘" → verify(modid) → lookup(simplified) → submit(taxreturn) → 접수번호. text-log 캡처 (per memory `feedback_vhs_tui_smoke`)
- `docs/research/policy-mapping.md` — KOSMOS adapter ↔ Singapore APEX / Estonia X-Road / EU EUDI / Japan マイナポータル mapping table
- `docs/scenarios/{hometax-tax-filing,gov24-minwon-submit,mobile-id-issuance,kec-yessign-signing,mydata-live}.md` — OPAQUE-forever 도메인 hand-off
**Risk**: 낮음
**Acceptance**: E2E text-log 전체 chain, 모든 15 mock 한 번 이상 호출, policy-mapping.md citation URL 4개 reference

## Phase η (#2298) — System prompt rewrite (선택)
**Goal**: `prompts/system_v1.md` 5-primitive citizen UX + OPAQUE 도메인 hand-off rule + 한국어 시민 친화 톤
**Risk**: 낮음 (shadow-eval 게이트)
**Acceptance**: shadow-eval 통과, prompt manifest hash 갱신
**Status**: optional — Phase α-ζ 결과 보고 결정

# Dependency graph (implement 시 Agent Teams 병렬 활용)

```
α (CC parity audit, read-only)
  ↓
  ┌── β (UI 잔재 정리) ──┐  ◀─ 병렬 가능 ─▶
  │                      │
  └── δ (백엔드 정리) ───┘
                          ↓
                       γ (5-primitive align)
                          ↓
                       ε (AX mock 어댑터)
                          ↓
                       ζ (E2E smoke + 정책 매핑)
                          ↓
                       η (system prompt, 선택)
```

# Agent Teams 병렬 전략 (memory `feedback_speckit_autonomous` + AGENTS.md § Agent Teams)

`/speckit-implement` 단계에서 적용 (specify/plan/tasks/analyze/taskstoissues는 Lead solo):

| Phase | 담당 | Model |
|---|---|---|
| α audit | API Tester (read-only) | Sonnet |
| β UI cleanup ‖ δ 백엔드 정리 (병렬) | Frontend Dev (β) + Backend Architect (δ) | Sonnet × 2 |
| γ 5-primitive align | Frontend Dev | Sonnet |
| ε AX mock 신설 | Backend Architect (Teammate A) | Sonnet |
| ζ E2E smoke + 매핑 doc | API Tester + Technical Writer (병렬) | Sonnet × 2 |
| η system prompt | Technical Writer | Sonnet |
| 전체 review + spec compliance | Code Reviewer (Lead) | Opus |

병렬 진입 조건: 3+ 독립 작업 + Sonnet model 강제 (`model: "sonnet"`).

# 통합 PR 정책 (memory `feedback_integrated_pr_only` + `feedback_pr_closing_refs`)

- 모든 Phase 결과를 단일 PR로 통합 (개별 phase별 PR 분할 금지)
- branch: `feat/2290-ax-infrastructure-caller-refactor`
- PR title: `feat(2290): AX-infrastructure caller refactor — Phase α-η integrated`
- PR body: `Closes #2291` only (Epic만, Phase sub-issue는 머지 후 close per memory `feedback_pr_closing_refs`)
- 매 commit Conventional Commits + Co-Authored-By 금지 (memory `feedback_co_author`)

# CI Gate (모든 PR 머지 전 통과 의무)

14 required checks (Lint & Type Check, Python 3.12+3.13, CodeQL SAST, BM25 Eval, Docker Build, License, Secret Detection, Dead Code, Dependency Audit, FR-011 SC-9, Branch naming, Conventional Commits, TUI PTY boot smoke, Auto-merge 정책).

`gh pr checks --watch --interval 10` 으로 모니터링 (memory: AGENTS.md § PR Completion).

# Memory guardrails (모든 phase에서 honor)

- `feedback_kosmos_is_ax_gateway_client` — KOSMOS = AX-infrastructure callable-channel client (3차 final)
- `feedback_tool_wrapping_is_the_work` — 작업 단위 = 도구 래핑
- `feedback_kosmos_scope_cc_plus_two_swaps` — CC + 2 swaps만
- `feedback_harness_not_reimplementation` — KOSMOS는 harness, 재구현 X
- `feedback_check_references_first` — 모든 결정에 reference 인용
- `feedback_runtime_verification` — TUI 변경은 PTY 검증 필수
- `feedback_vhs_tui_smoke` — text log 기본, gif 보조
- `feedback_no_hardcoding` — LLM 직접 BM25 라우팅, 정적 keyword X
- `feedback_no_stubs_remove_or_migrate` — KOSMOS 미사용 import + call site 모두 제거
- `feedback_cc_source_migration_pattern` — task body에 reference baseline 명시
- `feedback_main_verb_primitive` — 5-primitive (lookup/submit/verify/subscribe + resolve_location) 만 system prompt 노출
- `feedback_integrated_pr_only` — 단일 통합 PR
- `feedback_pr_closing_refs` — `Closes #2291` only
- `feedback_speckit_autonomous` — speckit 단계 승인 대기 X, /speckit-implement에서만 Agent Teams 병렬
- `feedback_codex_reviewer` — push 후 Codex inline review 처리

# 가드레일 (강제)

- 절대 KOSMOS-invented 권한 메타 필드 (pipa_class / auth_level / permission_tier / is_personal_data / dpa_reference / is_irreversible / requires_auth) 재도입 금지
- CC `<PermissionRequest>` 파이프라인 byte-identical 보존 (Class A 35+ files)
- OPAQUE-forever 도메인 (홈택스 신고, 정부24-submit, 모바일ID 발급, KEC/yessign 서명, mydata-live)은 어댑터로 만들지 말 것 — `docs/scenarios/`만
- 신규 runtime 의존성 0 (AGENTS.md hard rule)
- `--no-verify` / `--force` push 금지
- Co-Authored-By 추가 금지

# 진입 즉시 다음 단계

`/speckit-specify` 결과로 `specs/2290-ax-infrastructure-caller-refactor/spec.md` 생성 → 사용자 검토 → `/speckit-plan` (Phase 0 research + Phase 1 design + contracts) → `/speckit-tasks` (phase별 task 분해) → `/speckit-analyze` (consistency + constitution check) → `/speckit-taskstoissues` (Phase α-η 7 sub-issue 이미 존재하므로 task issues는 그 하위로 추가) → `/speckit-implement` (Agent Teams 병렬 진입).
```

---

## 사용 방법

### Option A — 새 세션에서 그대로 paste
1. `claude` (또는 `claude code`) 새 세션 시작
2. 위 코드 블록 내용 전체를 paste
3. Lead가 `/speckit-specify`부터 자율 진행 (메모리 `feedback_speckit_autonomous` 적용)

### Option B — 짧게 invoke
다음 세션에서 다음 한 줄로 시작:
```
specs/1979-plugin-dx-tui-integration/next-session-prompt.md 파일 읽고 그 안의 프롬프트 그대로 실행해
```
→ Lead가 본 파일 읽고 코드블록 내용대로 진행

## Agent Teams 병렬 진행 timing 정확히

| Speckit 단계 | 누가 | 시간 |
|---|---|---|
| `/speckit-specify` | Lead solo (Opus) | spec.md 작성 |
| `/speckit-plan` | Lead solo | plan.md + research.md + data-model.md + contracts |
| `/speckit-tasks` | Lead solo | tasks.md (phase별 task 분해) |
| `/speckit-analyze` | Lead solo | analysis.md (constitution check) |
| `/speckit-taskstoissues` | Lead solo | GitHub task sub-issues 생성 + GraphQL 링크 |
| **`/speckit-implement`** | **Lead + Sonnet Teammates 병렬** | **여기서 Agent Teams 활성화** |

## 위 프롬프트가 보장하는 것

- 7 Phase 모두 cover (단일 통합 spec)
- 의존성 그래프에 따른 implement 단계 병렬 분담
- canonical thesis (3차 final) + memory 14개 가드레일 honor
- 통합 PR 정책 + CI 14 gates
- 학부생 권한 한계 인지 (mock-only가 primary path, Live는 졸업 후)

## 다음 결정 필요 (이번 세션 마지막)

1. **위 프롬프트 그대로 OK?** — 변경 사항 있으면 알려주세요
2. **Dependabot 3 PR** (#1592, #1593, #1594) 머지 여부 — 별도 confirm 필요했음
3. **현재 9 open issues는 다음 세션 진입할 때 그대로** — Initiative #2290 + Epic #2291 + 7 Phase sub-issues
