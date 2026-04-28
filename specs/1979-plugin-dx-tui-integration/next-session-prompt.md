# 다음 세션 시작 프롬프트 — Initiative #2290 진입 (Epic 별 spec-driven cycle)

**구조** (사용자 정정 2026-04-29):

```
Initiative #2290 (KOSMOS · AX Infrastructure Callable-Channel Client Reference Implementation)
├─ Epic α (#2292) — CC parity audit (read-only)                          [size/M]
├─ Epic β (#2293) — KOSMOS-original UI residue cleanup                    [size/S]
├─ Epic γ (#2294) — 5-primitive align with CC Tool.ts interface           [size/L]
├─ Epic δ (#2295) — Backend permissions/ cleanup + AdapterRealDomainPolicy [size/M]
├─ Epic ε (#2296) — AX-infrastructure mock adapters                       [size/L]
├─ Epic ζ (#2297) — E2E smoke + policy mapping doc                        [size/M]
└─ Epic η (#2298) — System prompt rewrite (optional)                      [size/M]
```

**각 Epic마다 Lead (Opus) 별도 spec-driven cycle**. Agent Teams 병렬은:
- (a) **Epic 내부**: `/speckit-implement` 단계의 task들에 Sonnet teammates 분배
- (b) **Epic 간**: 의존성 없는 Epic들끼리 동시 진행 가능 (β + δ 병렬, ζ + η 병렬 등)

---

## 의존성 그래프

```
Epic α (#2292, read-only)
   ↓
   ┌── Epic β (#2293) ──┐  ← 병렬 가능 (의존성 0)
   │                    │
   └── Epic δ (#2295) ──┘
                        ↓
                     Epic γ (#2294)
                        ↓
                     Epic ε (#2296)
                        ↓
                     Epic ζ (#2297)
                        ↓
                     Epic η (#2298)
```

---

## 실행 sequence (다음 세션 시작 시)

### Option A — 의존성 그래프 따라 직선 진행 (추천)

각 Epic마다 별도 spec-driven cycle:

```
Step 1: Epic α (#2292)
  └─ /speckit-specify --feature 2292-cc-parity-audit
  └─ /speckit-plan
  └─ /speckit-tasks
  └─ /speckit-analyze
  └─ /speckit-taskstoissues
  └─ /speckit-implement (Agent Teams 병렬: API Tester teammates)
  └─ PR 머지 → Epic α close

Step 2-3: Epic β + Epic δ 병렬 (의존성 없음)
  ├─ Epic β (#2293) — Lead solo cycle (Frontend Dev teammate)
  └─ Epic δ (#2295) — Lead solo cycle (Backend Architect teammate)
  └─ 두 PR 머지 → Epic β + δ close

Step 4: Epic γ (#2294)  ← β/δ 결과 의존
  └─ Lead solo cycle + Frontend Dev teammate
  └─ PR 머지 → Epic γ close

Step 5: Epic ε (#2296)
  └─ Lead solo cycle + Backend Architect teammate
  └─ PR 머지 → Epic ε close

Step 6-7: Epic ζ + Epic η 병렬
  ├─ Epic ζ (#2297) — API Tester + Technical Writer
  └─ Epic η (#2298) — Technical Writer (optional)
  └─ PR 머지 → Initiative #2290 종료
```

### Option B — 한 Epic만 진입 (가장 보수적, 위험 0)

다음 세션에서 Epic α (#2292) 만 진행:

```
/speckit-specify --feature 2292-cc-parity-audit
```

후속 Epic들은 α 결과 검토 후 별도 세션에서 진입.

---

## 다음 세션 진입 프롬프트 (paste 용)

다음 세션 시작 후 아래 코드 블록 내용 그대로 paste:

```text
Initiative #2290 (KOSMOS · AX Infrastructure Callable-Channel Client Reference Implementation) 의 첫 Epic 진입.

# Active Epic
Epic α — #2292 — CC parity audit (read-only, 위험 0, size/M)

# Goal
1,604 KEEP 파일이 진짜 byte-identical with `.references/claude-code-sourcemap/restored-src/` 인지 spot-check + 212 modified 파일의 KOSMOS-change 정당성 audit. read-only deliverable.

# Authority — 반드시 인용 (per memory `feedback_check_references_first`)

- `AGENTS.md § CORE THESIS` — 3차 thesis canonical (KOSMOS = AX-infrastructure callable-channel client)
- `specs/1979-plugin-dx-tui-integration/cc-source-scope-audit.md § 1.1, § 1.2` — 2,090 vs 1,884 file 분류 (이 Epic의 base scope)
- `specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12` — final canonical architecture
- `.references/claude-code-sourcemap/restored-src/` — CC 2.1.88 byte-identical source-of-truth

# Deliverable

`specs/2292-cc-parity-audit/cc-parity-audit.md` 신설:
- 1,531 byte-identical 파일 spot-check (random sample 50개 실 검증)
- 73 SDK-import-only-diff 파일 모두 검증 (간단 grep)
- 212 modified 파일 each 정당성 분류:
  - Legitimate (KOSMOS-needed change, 인정)
  - Cleanup-needed (Spec 1633 잔재 등 정리 후속)
  - Suspicious (의심 — 추가 audit 필요)
- 파일별 변경 사유 + reference 인용
- 종합: 7-Phase plan 기준 다음 Epic 진입 준비 status

# Risk
0 — read-only audit. 어떤 파일도 수정 X.

# Acceptance
- audit doc 사용자 검토 + 사인오프
- 의심 파일 list 분리 (후속 Epic β에서 처리)

# Memory guardrails (강제)

- `feedback_kosmos_is_ax_gateway_client` — 3차 thesis
- `feedback_tool_wrapping_is_the_work` — 작업 단위 = 도구 래핑
- `feedback_kosmos_scope_cc_plus_two_swaps` — CC + 2 swaps만
- `feedback_check_references_first` — 모든 결정에 reference 인용
- `feedback_speckit_autonomous` — speckit 단계 자율 진행, 단계별 승인 X
- `feedback_codex_reviewer` — push 후 Codex inline review 처리

# 통합 PR 정책 (memory `feedback_integrated_pr_only` + `feedback_pr_closing_refs`)

- branch: `feat/2292-cc-parity-audit`
- PR title: `feat(2292): Epic α — CC parity audit deliverable`
- PR body: `Closes #2292` only
- Co-Authored-By 추가 금지
- `--no-verify` / `--force` 금지

# CI Gate
14 required checks. `gh pr checks --watch --interval 10` 으로 모니터링.

# 즉시 진입

`/speckit-specify --feature 2292-cc-parity-audit` 실행 → spec.md 작성 → 사용자 검토 → `/speckit-plan` → `/speckit-tasks` → `/speckit-analyze` → `/speckit-taskstoissues` (Epic α 하위에 task sub-issues) → `/speckit-implement` (API Tester teammate Sonnet 병렬 진입).
```

---

## Agent Teams 분담 (Epic별 implement 시)

| Epic | Lead (Opus) | Teammate (Sonnet) | 비고 |
|---|---|---|---|
| α #2292 | planning, audit review | API Tester (read-only audit) | 병렬 1팀 |
| β #2293 | planning, code review | Frontend Developer | 병렬 1팀 |
| γ #2294 | architecture, code review | Frontend Developer | 병렬 1팀 |
| δ #2295 | planning, code review | Backend Architect | 병렬 1팀 |
| ε #2296 | architecture, code review | Backend Architect (+ API Tester for tests) | 병렬 2팀 |
| ζ #2297 | review, sign-off | API Tester (E2E) + Technical Writer (doc) | 병렬 2팀 |
| η #2298 | shadow-eval gate | Technical Writer | 병렬 1팀 |

기본 원칙 (AGENTS.md § Agent Teams):
- 3+ 독립 task → Sonnet teammates 병렬
- 1-2 task 또는 coupled → Lead solo
- 모든 teammate `model: "sonnet"` 강제

---

## 사용 방법

### 다음 세션에서 Option A (가장 단순)
```
specs/1979-plugin-dx-tui-integration/next-session-prompt.md 파일 읽고 Epic α 부터 진입해
```
→ Lead가 본 파일의 § "다음 세션 진입 프롬프트" 코드블록을 그대로 실행

### 다음 세션에서 Option B (Epic α만 명시)
새 세션에 paste:
```
/speckit-specify --feature 2292-cc-parity-audit

(상기 next-session-prompt.md § "Active Epic" 내용 전체 입력)
```

### 후속 Epic들 진입 (α 완료 후)
α PR 머지 → 다음 세션에서:
```
Epic α 완료. β + δ 병렬 진입. 두 separate session 또는 한 세션에서 양 spec 순차.
```

---

## 그동안의 정정 history (이 파일은 v3)

- v1: Phase α-η 단일 통합 spec (잘못된 설계)
- v2: 통합 spec + Agent Teams 병렬 (여전히 부정확 — phase ≠ task)
- **v3 (이 파일)**: Phase = Epic이 정확한 구조. Epic 별 Lead solo speckit cycle. ✅

---

## 이번 세션 마지막 처리 항목

1. ✅ Epic 구조 정정 (#2291 close, #2292-#2298 → Initiative #2290 직접 child)
2. ✅ Label 변경 (epic + size/X)
3. ✅ Title 변경 (Phase X → Epic X)
4. ✅ next-session-prompt.md v3 작성

다음 세션에서 Epic α 진입할 준비 완료.
