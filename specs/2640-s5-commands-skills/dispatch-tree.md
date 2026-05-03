# Epic #2640 Dispatch Tree

```text
Phase 1 Setup (T01 / #2683)            : Lead solo
Phase 2 Foundational                   : skipped (cleanup-only)
Phase 3 US1 Skills (T02 / #2684)       : sonnet-skills    ┐
Phase 4 US2 P0 stubs (T03 / #2685)     : sonnet-stubs     ├─ parallel
Phase 5 US3 gap-3 박제 (T04 / #2686)    : sonnet-gap       ┘
Phase 6 Verification + PR (T05 / #2687): Lead solo
```

## Layer 2 — task / file budget per teammate

| Teammate | Task scope | File scope | Independence |
|---|---|---|---|
| sonnet-skills | T010-T015 (6 tasks) | `tui/src/skills/bundled/{claude-api/, verify/, claudeApi.ts, claudeApiContent.ts, verify.ts, verifyContent.ts, index.ts}` (~58 files: 51 + 3 + 4 dispatchers + 1 index edit) | independent of stubs/gap |
| sonnet-stubs | T020-T023 (4 tasks) | 19 dirs in `tui/src/commands/` + `tui/src/commands.ts` (1 file edit) | independent of skills/gap |
| sonnet-gap | T030-T031 (2 tasks) | `specs/cc-migration-audit/decisions.md` (1 file edit) | independent of skills/stubs |

**Note**: sonnet-skills has > 5 tasks but they are tightly coupled (delete + index.ts edit must happen together for typecheck to pass). All file deletions in the same subdirectory tree (`tui/src/skills/bundled/`) — single review surface.

**Note**: sonnet-stubs has 1 file change (`commands.ts`) but 19 directories deleted (~30+ files) — file count is high but each is a P0 stub homologue, no review depth needed beyond verifying the import/array cleanup is complete.

## Lead Opus responsibilities

- Phase 1 (T001) — verify worktree state.
- Pre-implement — write `dispatch-tree.md` (this file), write `scripts/smoke-slash-autocomplete.sh` (Layer 5 scenario template).
- Phase 6 (T040-T048) — sequential after all Sonnet teammates complete:
  - bun typecheck + bun test
  - Layer 5 tmux capture-pane execution
  - PNG keyframe Read + visual verification
  - git add + commit + push origin feat/2640-s5-commands-skills
  - gh pr create with `Closes #2640`
  - gh pr checks --watch --interval 10
  - Codex inline review handling
  - Copilot Gate completion
  - Epic close + sub-issues batch close

## Risk budget

- 3 parallel teammates → 3 independent file trees, no merge conflict possibility.
- `commands.ts` and `bundled/index.ts` are edited only by stubs/skills respectively (no cross-edit).
- gap-3 박제 only edits `decisions.md` (no source code touch).
