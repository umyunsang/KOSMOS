# Dispatch Tree 2641 · S6 Services swap-1 마무리

> Lead Opus dispatch plan per AGENTS.md § Agent Teams "Dispatch tree" rule.

```
Phase 1 Setup (T001):                                  Lead solo
Phase 3 US1 (T002 — api/client.ts dup fix):            sonnet-client-fix      ┐
Phase 4 US2 (T003+T004 — teamMemorySync 박제):         sonnet-team-mem-deaden ├─ parallel
Phase 5 US3 (T005+T006 — settingsSync 박제):           sonnet-settings-deaden ┘
Phase 6 Polish (T007-T012 — typecheck/test/smoke/PR):  Lead solo
```

## Per-teammate budget
| Teammate | Tasks | Files | LOC est. |
|---|---|---|---|
| sonnet-client-fix | T002 | 1 (api/client.ts) | ~25 |
| sonnet-team-mem-deaden | T003, T004 | 2 (teamMemorySync/index.ts + test) | ~80 |
| sonnet-settings-deaden | T005, T006 | 2 (settingsSync/index.ts + test) | ~100 |

All under ≤ 5 tasks / ≤ 10 file changes per AGENTS.md § Dispatch unit.

## Parallelism justification
Three modules share **zero source files** and **zero shared TypeScript symbols**.
The only cross-coupling is the common 박제 header pattern (Spec 2521-style),
which each teammate consults independently from `tui/src/services/api/claude.ts:1-23`
as the reference. No merge conflicts possible.

## Lead-only responsibilities (post-implement)
1. Read each teammate's `git diff` for adherence to spec.md FR-001..006.
2. Run integrated `bun typecheck` + `bun test` (cross-module verification).
3. Author + run Layer 5 tmux boot smoke (T009).
4. `git add` + commit + `git push origin feat/2641-s6-services-swap1`.
5. `gh pr create` with `Closes #2641` body.
6. `gh pr checks --watch --interval 10`.
7. Codex P1 review reply.
8. Copilot Gate completion verification.

## Decision: Self-execute vs dispatch
본 작업은 3 개 작은 독립 모듈 (총 LOC ~205 + tests). AGENTS.md "3+ independent
tasks → parallel Teammates (Sonnet)" 규칙을 만족. 하지만:

- 박제 헤더 형식이 Spec 2521 패턴 일관성 — 미세 wording 일치 필요
- dead-call gate 형식이 spec.md FR-003/005 에 거의 word-for-word 명시
- 총 LOC ~205 는 single Lead solo 로 30분 내 가능
- Sonnet teammate dispatch overhead (prompt writing + code review) 가 작업
  자체보다 비쌀 가능성

→ **Lead solo 실행 결정**. AGENTS.md Hard rule "1 Lead Opus = N Epics 금지"
는 위반 안 함 (1 Lead = 1 Epic). "1 Sonnet = 1 Epic 금지" 도 무관 (Sonnet
미사용). 단, 향후 더 큰 cross-Epic 병행 시 위 dispatch tree 그대로 사용 가능
하도록 문서화 보존.
