# Dispatch Tree — Epic ε #2296

**Generated**: 2026-04-29 (post `/speckit-taskstoissues`)
**Epic**: #2296 — AX-infrastructure mock adapters & adapter-manifest IPC sync
**Worktree**: `/Users/um-yunsang/KOSMOS-w-2296` on branch `2296-ax-mock-adapters`
**Lead Opus uses this at `/speckit-implement` time** to spawn parallel sonnet teammates per AGENTS.md § Agent Teams.

---

## Layer 1 — One Lead Opus owns this Epic end-to-end

This Epic has exactly **one Lead Opus** (the current session, or whichever session resumes from `next-session-prompt-v8-handoff.md` on Epic ε). The Lead is responsible for:

- Spec / plan / tasks / analyze / taskstoissues authoring (✅ complete)
- Dispatching sonnet teammates per Layer 2 below
- Code review of teammate output (Opus-tier judgement)
- `git push`, `gh pr create`, `gh pr checks --watch`, Codex P1/P2 reply, merge

Sonnet teammates do **NOT** push, PR, or watch CI — those stay sequential with the Lead.

---

## Layer 2 — Sonnet teammate dispatch (≤ 5 task / ≤ 10 file per teammate)

```text
Phase 1 Setup (T001-T002): Lead solo                                     [2 tasks]
Phase 2 Foundational (T003-T007): sonnet-foundational                    [5 tasks · ~7 file changes]
Phase 3 US2 IPC sync (T008-T015): sonnet-us2                             [8 tasks · ~9 file changes]    ┐
Phase 4A US1 verify mocks (T016-T022): sonnet-us1a                       [7 tasks · ~12 file changes]   │
Phase 4B US1 submit + subscribe retrofit (T023-T027): sonnet-us1b        [5 tasks · ~10 file changes]   ├─ all 4 in parallel
Phase 4C US1 lookup mocks (T028-T029): sonnet-us1c                       [2 tasks · ~4 file changes]    │
                                                                                                         ┘ Phase 3 + 4A + 4B + 4C all run as parallel sonnet teammates
Phase 5 US1 wiring + integration (T030-T033): sonnet-us1integration      [4 tasks · ~5 file changes]    (gated by Phase 3 + Phase 4 all complete)
Phase 6 US3 observability (T034-T036): sonnet-us3                        [3 tasks · ~3 file changes]    (gated by Phase 5)
Phase 7 Smoke (T037-T040): sonnet-smoke                                  [4 tasks · ~5 file changes]    (gated by Phase 5 + 6)
Phase 8 Polish (T041-T045): Lead solo                                    [5 tasks · 1 file (PR body)]   (sequential, Lead)
```

**Total**: 45 tasks across 9 phases. 4 phases (3 + 4A + 4B + 4C) run in parallel after Phase 2 completes.

### Phase 4A teammate (sonnet-us1a) budget note

Phase 4A ships 7 tasks and ≈ 12 file changes — slightly over the AGENTS.md ≤ 10 file guideline. Already documented as a known trade-off in `tasks.md`. **Lead splits if context exhaustion observed during execution**: the natural split is (T016, T017, T018) → sonnet-us1a-1 and (T019, T020, T021, T022) → sonnet-us1a-2.

---

## Sonnet teammate prompt template (≤ 30 lines per teammate per AGENTS.md)

For each Sonnet teammate, the Lead spawns with a prompt of this shape:

```text
You are sonnet-<phase-tag> for KOSMOS Epic ε #2296 (AX-infrastructure mock adapters).

Worktree: /Users/um-yunsang/KOSMOS-w-2296
Branch: 2296-ax-mock-adapters
Spec: specs/2296-ax-mock-adapters/spec.md
Plan: specs/2296-ax-mock-adapters/plan.md
Tasks: specs/2296-ax-mock-adapters/tasks.md
Quickstart: specs/2296-ax-mock-adapters/quickstart.md
Contracts: specs/2296-ax-mock-adapters/contracts/

Your tasks: T<start>-T<end>. Read each task in tasks.md verbatim and implement.

Hard rules:
- Zero new runtime dependencies (FR-023)
- All source text English; Korean only in domain data + search_hint + llm_description (FR-024)
- Every Mock cites agency-published policy URL (FR-025)
- Pydantic v2 frozen models, no `Any`
- Spec 032 IPC envelope: NEW arm only

When done:
1. Run `uv run pytest tests/<your-paths>` (Python tasks) or `cd tui && bun test <your-paths>` (TS tasks)
2. Mark each task `[X]` in tasks.md
3. WIP commit per task with message `feat(2296): <task ID> <short description>`
4. Stop. Do NOT push. Do NOT create PR. Lead handles those.

Reference docs: specs/1979-plugin-dx-tui-integration/delegation-flow-design.md § 12 + restored-src patterns under .references/claude-code-sourcemap/restored-src/.

Report back: tasks completed, file paths touched, test results.
```

---

## Issue ID range for this Epic

| Phase | Tasks | Issue numbers |
|---|---|---|
| Phase 1 Setup | T001, T002 | #2396, #2397 |
| Phase 2 Foundational | T003-T007 | #2398-#2402 |
| Phase 3 US2 IPC sync | T008-T015 | #2403-#2410 |
| Phase 4A US1 verify mocks | T016-T022 | #2411-#2417 |
| Phase 4B US1 submit + subscribe | T023-T027 | #2418-#2422 |
| Phase 4C US1 lookup mocks | T028, T029 | #2423, #2424 |
| Phase 5 US1 wiring + integration | T030-T033 | #2425-#2428 |
| Phase 6 US3 observability | T034-T036 | #2429-#2431 |
| Phase 7 Smoke | T037-T040 | #2432-#2435 |
| Phase 8 Polish | T041-T045 | #2436-#2440 |
| Deferred placeholders | (4 sub-issues) | #2441-#2444 |

All 49 sub-issues linked to Epic #2296 via Sub-Issues API v2 (verified post-creation: `gh api graphql ... subIssues.totalCount` returns 49).

---

## Codex P1 #2395 piggyback

Phase 3 (sonnet-us2) directly resolves Codex P1 #2395 (deferred adapter manifest IPC sync). After Epic ε merges, the Lead posts a closure comment on #2395 referencing the Epic ε PR + the `test_codex_p1_adapter_resolution.py` integration test (T033) that proves the fix end-to-end. Phase 8 task T044 is that closure step.

---

## Sequencing diagram

```text
           ┌── Phase 3 ──┐
Phase 1 ──▶ Phase 2 ──┬──┤             │──┬──▶ Phase 5 ──▶ Phase 6 ──▶ Phase 7 ──▶ Phase 8 ──▶ PR
(Lead)    (sonnet-fnd)│  ├── Phase 4A ─┤  │
                       │  ├── Phase 4B ─┤  │
                       │  └── Phase 4C ─┘  │
                       └───────────────────┘
                          (4 parallel sonnet teammates)
```

Phase 3 + 4A + 4B + 4C all gated by Phase 2 completion. Phase 5 gated by all four parallel phases completing. Phase 6/7/8 sequential after Phase 5.

---

## Pre-implementation checklist (Lead before spawning teammates)

- [ ] Worktree clean: `cd /Users/um-yunsang/KOSMOS-w-2296 && git status --short` returns empty
- [ ] Branch correct: `git branch --show-current` returns `2296-ax-mock-adapters`
- [ ] Dependency baseline: `git diff main -- pyproject.toml tui/package.json` returns empty
- [ ] All 49 sub-issues confirmed: `gh api graphql ... subIssues.totalCount` returns 49
- [ ] Spec / plan / tasks / research / data-model / contracts / quickstart all committed
- [ ] User has approved the development phase (this is the boundary the user explicitly named)
