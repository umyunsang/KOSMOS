# 다음 세션 시작 프롬프트 — Initiative #2290 핸드오프 v7 (Epic γ 머지 완료)

**작성일**: 2026-04-29 (Epic γ 머지 직후)
**상태**: Epic α + β + γ + δ 머지 완료. Epic ε / ζ / η OPEN. 다음 세션이 별도 Lead Opus 로 다음 Epic 진행.

---

## 머지 결과 요약

| Epic | # | 상태 | 머지 commit |
|---|---|---|---|
| α cc-parity-audit | #2292 | CLOSED | `bc523b7` |
| β ui-residue-cleanup | #2293 | CLOSED | `43a7bd8` |
| **γ 5-primitive-align (CC Tool.ts)** | **#2294** | **CLOSED** | **`b47db4c` (PR #2394)** |
| δ backend-permissions-cleanup | #2295 | CLOSED | `c6747dd` |
| ε AX-mock-adapters | #2296 | OPEN | — |
| ζ E2E-smoke | #2297 | OPEN | — |
| η ? | #2298 | OPEN | — |

### Epic γ #2294 핵심 산출물 (이번 세션)

- **9-member shape**: 4 primitive (Lookup/Submit/Verify/Subscribe) 모두 CC `Tool<>` 9 member 준수 — `validateInput` + `renderToolResultMessage` + 명시 `isMcp = false` 추가.
- **Helper**: `tui/src/tools/shared/primitiveCitation.ts` (extractCitation + PrimitiveErrorCode).
- **Boot guard**: `tui/src/services/toolRegistry/bootGuard.ts` + `tui/src/main.tsx` 통합 + `bun run probe:tool-registry` 스크립트. Codex P2 fix 로 reserved-set 4-primitive 존재 검증까지.
- **Tests**: `registry-boot.test.ts` (5 cases) + `permission-citation.test.ts` (20 tests, 75 expects, 6-phrase blocklist) + `span-attribute-parity.test.ts` (14 tests).
- **PTY transcript**: `specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt` (7977 LOC, boot guard + 한국어 입력 + agentic loop 진입 검증).
- **30 sub-issues 처리**: 27 task (#2365–#2391) CLOSED, 3 deferred (#2392/#2393/#2395) OPEN.
- **Codex P1 deferred → #2395**: TS-side `context.options.tools` (14 KOSMOS tools) ≠ backend Python registry (18 agency adapters). adapter manifest IPC sync 가 Epic ε piggyback.
- **acceptance-report.md**: 6/7 SC PASS, SC-006 (≤1500 LOC) 71 LOC over 명시 수용. Constitution 6/6 PASS.

---

## 다음 세션 진입 (1 Lead Opus = 1 Epic)

`memory feedback_dispatch_unit_is_task_group` (Two-layer parallelism) 따라 **각 Epic 마다 별도 Lead Opus session 분리** 필수.

### Epic ε #2296 — AX-mock-adapters (Codex P1 piggyback 권장)

```bash
cd /Users/um-yunsang/KOSMOS  # main worktree
git pull --ff-only
git worktree add ../KOSMOS-w-2296 -b 2296-ax-mock-adapters
cd ../KOSMOS-w-2296
# /speckit-specify Epic ε 시작 — 9 mock adapter (5 verify + 3 submit + 1 subscribe)
# + DelegationToken/DelegationContext 스키마 + Codex P1 #2395 (adapter manifest IPC sync)
```

**spec scope 권장**: 9 mock adapter 신설 외에 Codex P1 deferred (#2395) 도 같이 다루기 — 새 mock adapter 가 등록될 때 backend manifest 가 TS 로 sync 되는 IPC frame 도 같이 추가하면 primitive validateInput 의 adapter resolution 이 비로소 작동.

### Epic ζ #2297 — E2E smoke + 정책 매핑 doc

```bash
cd /Users/um-yunsang/KOSMOS && git pull --ff-only
git worktree add ../KOSMOS-w-2297 -b 2297-e2e-smoke
cd ../KOSMOS-w-2297
# /speckit-specify Epic ζ 시작 — End-to-end 시나리오 + docs/scenarios OPAQUE + KOSMOS v0.1-beta tag
```

### Epic η #2298 — 본문 미정

이슈 본문 채우기 + speckit cycle 진행.

---

## 불변 규칙 (이번 세션 박제)

1. **1 Lead Opus = 1 Epic** (Layer 1 parallelism). 의존성 없는 Epic 들은 **별도 session/worktree** 에서 동시 진행.
2. **Sonnet teammate 단위 = task/task-group** (≤ 5 task / ≤ 10 file). "1 Sonnet = 1 Epic" 금지.
3. **push/PR/CI/Codex = Lead** (sequential, sonnet teammates 완료 후).
4. **Codex P1/P2 처리 패턴**: P2 = 즉시 fix + reply. P1 (architecture mismatch) = deferred sub-issue + spec.md 백필 + reply (Acknowledged + 추적 # 명시).
5. **PR title subject 첫 글자 lowercase** 강제 (Conventional Commits action) — `feat(NNNN): align ...` ✓, `feat(NNNN): Align ...` ✗.
6. **`gh issue close --quiet` 금지** — `--quiet` 가 silent fail 일으킴 (이번 세션 27 sub-issue close 시도 시 발견). flag 빼고 close.
7. **PTY smoke 가 backend 로직 보장 안 함** — `KOSMOS_BACKEND_CMD=sleep 60` mock 은 stale-import / dead-JSX-path 회귀만 보장. adapter dispatch 검증은 별도 (Epic ε 의 mock fixture 도입 후 가능).
8. **신규 dep 0** (AGENTS.md hard rule). pyproject.toml `[project.dependencies]` / `tui/package.json` dependencies 변경 X.
9. **이슈 추적 = GraphQL Sub-Issues API only** (`subIssues` / `parent` 필드, `trackedIssues` X). 단, **closure verify 는 REST per-issue** (GraphQL eventual consistency).

---

## 다음 세션 첫 명령 후보

```
/clear → 새 conversation
이 파일 (specs/1979-plugin-dx-tui-integration/next-session-prompt-v7-handoff.md) 읽고 Epic <ε/ζ/η> #<번호> resume.
```

또는 사용자가 우선순위를 직접 지정.
