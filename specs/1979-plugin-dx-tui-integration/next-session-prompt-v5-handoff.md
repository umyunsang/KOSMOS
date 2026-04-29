# 다음 세션 시작 프롬프트 — Initiative #2290 핸드오프 v5 (Epic β 머지 완료 후)

**작성일**: 2026-04-29 (Epic β 머지 직후)
**상태**: Epic α + β 머지 완료. Epic γ / δ / ε / ζ / η 모두 OPEN. 다음 세션이 별도 Lead Opus 로 다음 Epic 진행.

이 파일은 v4 핸드오프의 후속. v4 가 명시한 두 WIP (Epic β + δ) 중 β 는 본 세션에서 처리 완료, δ 는 worktree 그대로 보존되어 다음 Lead Opus session 의 입력.

---

## 머지 결과 요약

### Epic α #2292 (cc-parity-audit) — 이전 세션 머지 (commit `bc523b7`)
- 218 modified file 분류 (188 Legitimate / 30 Cleanup-needed / 0 Suspicious)
- 21 sub-issues 모두 close (#2299-#2318) + #2319 deferred OPEN

### Epic β #2293 (ui-residue-cleanup) — 본 세션 머지 (PR #2363, commit `43a7bd8`)
- v1 spec 의 30-file blanket-deletion 가설을 caller-graph 박제로 v2 전면 재작성
- 28 Anthropic-residue files 삭제 + 50+ caller call sites cleanup (6 sonnet teammate 병렬 + Lead solo)
- 3 KEEP files 박제 (permissionSetup 11 importer, permissions 14 importer, ui-l2/permission 5 importer Spec 035)
- 3 stub-restored files (tokenEstimation, shell/prefix, WebFetchTool/utils)
- 2 new shims (mcpb-compat, sandbox-runtime-compat)
- Codex P1×2 + P2×1 모두 처리
- **PR pre-merge interactive PTY test 영구 룰 박제**:
  - Memory `feedback_pr_pre_merge_interactive_test.md` (★★★ 최상위 우선)
  - AGENTS.md § TUI verification — PR mandatory hard rule
- 검증 산출물: smoke-pty.txt + smoke-help-pty.txt + smoke.gif + smoke-help.gif
- 20 sub-issues close (#2321-#2340) + #2361 Deferred OPEN

---

## Epic δ #2295 (Backend permissions cleanup + AdapterRealDomainPolicy) — WIP 보존 / 다음 세션 입력

**v4 그대로 유효.** worktree 와 commit 들이 보존됨:

- **Worktree**: `/Users/um-yunsang/KOSMOS-w-2295/`
- **Branch**: `2295-backend-permissions-cleanup` (local only, push 안 됨)
- **Commits**:
  1. `97b85d1` — Sonnet 1차 (~70%, 안전): AdapterRealDomainPolicy + 19 어댑터 metadata 마이그레이션 + caller-side updates
  2. `553bb62` — Sonnet 2차 (test 17 deletion + scope review 필요)

### 다음 세션 권장 처리 (v4 그대로)

1. spec.md 보정 — FR-008 grep gate 정밀화 (`src/kosmos/tools/` adapter metadata 영역으로 좁히고, `src/kosmos/security/audit.py` + `src/kosmos/plugins/checks/q3_security.py` + `src/kosmos/recovery/auth_refresh.py` 등 KOSMOS-needed 영역 명시 제외)
2. SessionContext 보존 결정 (models.py 통째 삭제 X, SessionContext 만 keep)
3. 잔재 16 source file + steps/ deletion (importer 추적 후, models.py + credentials.py 보존)
4. `__init__.py` 재작성: credentials + models.SessionContext + Spec 035 receipt set 만 export
5. 5 단위 테스트 추가 (test_adapter_real_domain_policy.py)
6. pytest baseline diff verify
7. commit + push + PR

**Epic δ 는 백엔드 Python 만 변경 → TUI verification (PR mandatory) 면제** — PR description 에 "TUI no-change" 명시.

---

## Initiative #2290 잔여 Epic 상태

| Epic | # | 상태 | 다음 단계 |
|---|---|---|---|
| α cc-parity-audit | #2292 | CLOSED (merged) | — |
| β ui-residue-cleanup | #2293 | CLOSED (merged) | — |
| γ 5-primitive-align (CC Tool.ts) | #2294 | OPEN | 별도 Lead Opus session — spec cycle 시작 |
| δ backend-permissions-cleanup | #2295 | OPEN, WIP worktree 보존 | 별도 Lead Opus session — 위 권장 절차 |
| ε AX-mock-adapters | #2296 | OPEN | spec cycle 미시작 |
| ζ E2E-smoke | #2297 | OPEN | spec cycle 미시작 |
| η ? | #2298 | OPEN | spec cycle 미시작 |

`memory feedback_dispatch_unit_is_task_group` (Two-layer parallelism) 따라 **각 Epic 마다 별도 Lead Opus session 분리**. 한 conversation 에서 두 Epic 끌면 컨텍스트 한계 + spec cycle 결함 재현.

---

## 본 세션이 박제한 영구 룰

### Memory (★★★ 최상위 우선)
- `feedback_pr_pre_merge_interactive_test.md` — TUI 변경 PR 머지 전 expect/asciinema/script PTY 시나리오 mandatory + Epic β 두 번 누락 사례 박제

### AGENTS.md
- § TUI verification (LLM-readable smoke) — **PR mandatory** hard rule
- 4-layer verification chain (Layer 0 typecheck/test → Layer 1 stdio probe → Layer 2 interactive PTY → Layer 3 vhs gif) 명시
- Bypass 절차 (TUI no-change 선언) 명시

---

## 다음 세션 진입 권장 (사용자 명령: "다음 에픽 진행은 클리어하고 다른 세션에서")

```bash
# 옵션 A: Epic δ 이어서
cd /Users/um-yunsang/KOSMOS-w-2295
# v4 핸드오프 + 위 권장 절차 따라 진행

# 옵션 B: Epic γ 새 시작
cd /Users/um-yunsang/KOSMOS  # main worktree
git worktree add ../KOSMOS-w-2294 -b 2294-5-primitive-align
# /speckit-specify Epic γ 시작

# 옵션 C: Epic ε / ζ / η 새 시작
# 동일 패턴 — 별도 worktree + 별도 session
```

**불변**: 1 Lead Opus = 1 Epic. push/PR/CI/Codex = Lead. ≤ 5 task / ≤ 10 file = sonnet teammate. PR 머지 전 (TUI 변경 시) interactive PTY 시나리오 박제.
