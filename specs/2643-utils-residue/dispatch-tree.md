# Dispatch Tree — Epic G · Utils 잔존 정리 (Spec 2643)

**Date**: 2026-05-03
**Lead Opus**: claude-opus-4-7 (this session)
**Total tasks**: 32 (T001-T060, with gaps)

```text
Phase 1 Setup (T001-T003):                      Lead solo
Phase 2 Foundational:                            (none — disjoint stories)

Phase 3 US1 sessionTitle (T010-T014):           sonnet-us1   ┐
Phase 4 US2 dateTimeParser (T020-T024):         sonnet-us2   ├─ parallel (Layer-2)
Phase 5 US3 permissions Path B (T030-T034):     sonnet-us3   │
Phase 6 US4 ADR-009 (T040-T043):                sonnet-us4   ┘

Phase 7 Polish (T050-T060):                     Lead solo
```

## Per-teammate file budget (AGENTS.md ≤ 10 file changes)

| Teammate | Tasks | Files touched | Within budget? |
|---|---|---|---|
| sonnet-us1 | T010-T014 (5) | sessionTitle.ts, sessionTitle.test.ts, us1-test-output.txt, us1-typecheck.txt | 4 ✅ |
| sonnet-us2 | T020-T024 (5) | dateTimeParser.ts, dateTimeParser.test.ts, elicitationValidation.ts, us2-test-output.txt, us2-typecheck.txt | 5 ✅ |
| sonnet-us3 | T030-T034 (5) | yoloClassifier.ts, permissions.ts, us3-diff-audit.txt, us3-test-output.txt, us3-typecheck.txt | 5 ✅ |
| sonnet-us4 | T040-T043 (4) | ADR-009-secureStorage-drop.md, decisions.md, scope-S9-utils.md, us4-cross-ref.txt | 4 ✅ |

All teammates well within budget.

## Lead-only Phase 7 (T050-T060) — 11 tasks

Lead Opus serializes after all 4 teammates complete:
- Verification chain (Layer 1a / 1b / 5)
- vhs PNG keyframe smoke
- SC-007 K-EXAONE retry budget measurement
- Diff audit
- CLAUDE.md Recent Changes update
- git add + commit + push
- gh pr create + checks --watch + Codex/Copilot Gate

## Execution mode notice

Per session capacity, this Lead Opus session executes **all phases directly** (no separate teammate session spawn). The dispatch tree is preserved in this document so that any handoff session can reproduce the structure for replay/parallel re-execution.
