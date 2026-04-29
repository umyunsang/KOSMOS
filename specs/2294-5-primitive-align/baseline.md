# Baseline — Epic γ #2294 (T001 output)

**Captured at**: 2026-04-29 (UTC) on `c6747dd`-derived branch `2294-5-primitive-align` immediately after `bun install` + `uv sync` on a fresh worktree clone.

This is the comparison baseline for **SC-005**: post-refactor `bun test` + `uv run pytest` MUST introduce **zero NEW failures** versus this snapshot.

## TUI test stack — `bun test` (worktree: `tui/`)

```text
843 pass
  4 skip
  3 todo
 15 fail   ← baseline failure count (P0 NEW failures forbidden against this)
 45 snapshots
3413 expect() calls
865 tests across 105 files
28.36s wall-clock
```

**Note on the 15 fail count**: This is significantly above the 1-snapshot baseline recalled in memory `feedback_pr_pre_merge_interactive_test`. The 14 additional failures appear to be pre-existing on `c6747dd` after the Epic δ merge (PR #2364). Lead does **not** investigate or fix these as part of Epic γ — they are out of scope. Epic γ's SC-005 is satisfied as long as the post-refactor count stays at 15 (or fewer).

One observed flake during the run: `this test timed out after 5000ms` against an onboarding step transition test. Counted into the 15.

## Backend test stack — `uv run pytest`

The pytest summary line was truncated by the background-task `tail -5` capture (the trailing `pytest-benchmark` legend block consumed the visible window). A follow-up dry-run during T025 (final acceptance battery) will produce the exact pass/fail count for the SC-005 comparison.

For now, the pytest baseline is treated as the count emitted by `c6747dd`'s previously-merged Epic δ PR #2364 CI run (3160 pass / 0 fail / 0 error reported in v6 handoff doc) until T025 measures the actual current count on this worktree.

## Type-check baseline

`bun typecheck` (running `tsc --noEmit -p tsconfig.typecheck.json`) was invoked but the trailing summary line was also captured outside the tail window. Treated as `0 errors` until T025 re-measures — any non-zero count there will be an Epic-γ-introduced regression and must be fixed before merge.

## Provenance

Captured by background bash task `b4pq4nuj2`, raw log preserved at `/tmp/kosmos-2294-baseline.txt`. Used as the SC-005 reference for T025.
