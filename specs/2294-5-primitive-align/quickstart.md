# Quickstart: 5-Primitive Align Verification

**Feature**: 2294-5-primitive-align | **Date**: 2026-04-29

This document gives a reviewer (or a Lead-Opus session resuming work) the minimum set of commands to verify Epic γ end-to-end on a developer laptop. Time budget: 15 minutes from clean checkout.

## 0 — Worktree

```bash
cd /Users/um-yunsang/KOSMOS                # main worktree
git pull --ff-only
git worktree list                          # confirm KOSMOS-w-2294 exists
cd ../KOSMOS-w-2294                        # branch 2294-5-primitive-align
git status                                 # expect clean working tree on a fresh review
```

## 1 — Install / sync (one-time)

The Spec Kit + plan was authored without installing dependencies. For implementation review, both stacks must be synced.

```bash
# Python backend
uv sync                                    # rebuilds .venv from uv.lock — no version bump in this Epic

# TUI
cd tui
bun install                                # rebuilds tui/node_modules — no new deps in this Epic
cd ..
```

## 2 — Type-check (Spec SC-004)

```bash
cd tui && bun typecheck && cd ..
```

Expected: `0 errors`. Any non-zero count is a P0 blocker.

## 3 — Unit tests (Spec SC-005)

```bash
cd tui && bun test && cd ..
uv run pytest -q
```

Expected: vs main `c6747dd` baseline — **no NEW failures**. The pre-existing 1 snapshot failure (TUI) and 1 pytest failure are acknowledged and unchanged.

The three new TUI test files added by this Epic should be listed in the bun-test output:
- `tui/src/tools/__tests__/registry-boot.test.ts`
- `tui/src/tools/__tests__/permission-citation.test.ts`
- `tui/src/tools/__tests__/span-attribute-parity.test.ts`

## 4 — Boot guard sanity check (Spec SC-002)

```bash
# Boots the TUI in a probe mode that prints the registry verification line and exits.
cd tui && bun run probe:tool-registry && cd ..
```

Expected output:

```text
tool_registry: 22 entries verified (4 primitives, 18 adapters) in 134ms
```

Acceptance: `entries == 22`, wall-clock `≤ 200ms`. If wall-clock exceeds the budget, Lead Opus should investigate before merging — the registry boot is in the citizen-perceived launch path.

## 5 — PTY smoke (Spec SC-001 — MANDATORY before PR)

```bash
expect specs/2294-5-primitive-align/scripts/smoke-emergency-lookup.expect \
  > specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt
```

Inspect the captured text log:

```bash
grep -E "KOSMOS|의정부|응급실|nmc_emergency_search|real_classification_url" \
  specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt
```

Expected lines, in order:
1. `KOSMOS` branding banner.
2. The `lookup` tool-use announcement (Korean).
3. The `<PermissionRequest>` body containing the NMC `real_classification_url` literal.
4. After the `y` keypress is sent, the adapter result block in Korean.
5. Clean exit on `^C ^C`.

Total wall-clock from prompt → result text rendered: `≤ 8s` (Spec SC-001).

If the smoke fails, do NOT push. Investigate before re-running. The text log is the **single source of truth** for "is the citizen flow intact" per memory `feedback_vhs_tui_smoke`.

## 6 — Citation correctness (Spec SC-003)

The `permission-citation.test.ts` suite walks every adapter and asserts the rendered prompt body contains the citation strings byte-for-byte. The blocklist of forbidden KOSMOS-invented phrases is enumerated at the top of the test file. If any new adapter is added to the registry without a citation, this test fails before the boot guard does — it provides earlier feedback.

```bash
cd tui && bun test src/tools/__tests__/permission-citation.test.ts && cd ..
```

## 7 — Diff size budget (Spec SC-006)

```bash
git diff --stat main..HEAD -- tui/src/tools/{Lookup,Submit,Verify,Subscribe}Primitive \
                              tui/src/services/toolRegistry/bootGuard.ts \
                              tui/src/tools/__tests__
```

Expected: total inserted-lines + deleted-lines ≤ 1500 net. Anything over indicates accidental scope creep into Epic ε territory (new adapters) or Epic ζ (E2E scenarios) — Lead Opus should split or revert before pushing.

## 8 — Span-attribute parity (Spec SC-007)

```bash
cd tui && bun test src/tools/__tests__/span-attribute-parity.test.ts && cd ..
```

Expected: all snapshots match pre-refactor baseline. The only **allowed** new attribute is `kosmos.adapter.real_classification_url` (introduced by Epic δ commit `c6747dd`). Any other drift is a regression.

## Citizen verification checklist (5 minutes)

Aside from the automated checks above, a human reviewer should:

1. Open `specs/2294-5-primitive-align/smoke-emergency-lookup-pty.txt` and confirm the citizen-facing strings are natural Korean (no machine-translated artefacts).
2. Confirm the permission prompt's citation URL is clickable / readable in the terminal (TUI typically renders URLs as plain text — that is fine).
3. Confirm the adapter result is in Korean and matches the NMC Mock fixture's expected shape.
4. Skim the diff for any leaked English permission-language ("safe permission tier", "this system…") — there should be none.

## Failure response

| Symptom | First action |
|---|---|
| `bun typecheck` fails | Inspect error — likely a primitive's `validateInput` / `renderToolResultMessage` signature mismatch with `ToolDef<In, Out>`. |
| `verifyBootRegistry` fails on adapter | Check `src/kosmos/tools/<adapter>/manifest.py` for missing `real_classification_url`. May indicate Epic δ deferred #2362 work surfaced — file as a sub-issue. |
| PTY smoke times out | Check FriendliAI Tier 1 quota + `KOSMOS_LLM_API_KEY` env var. Memory `feedback_env_check_first` applies. |
| Snapshot test diverges | Verify the OTEL span schema didn't drift — check Spec 021's attribute list before assuming a regression. |
