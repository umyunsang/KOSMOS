# Contract: Brand Guardian Grep CI Gate Specification

**Feature**: 034-tui-component-catalog
**Phase**: 1 (Design & Contracts)
**FR**: 011 (spec lives here; implementation is Deferred Items row 11 → `/speckit-taskstoissues` backfill).
**Downstream consumer**: the post-verdict Task under Epic M that creates `.github/workflows/brand-guardian.yml`.

---

## 1 · Triggered PR paths

The gate runs on pull_request events where any of the following change:

- `tui/src/theme/**`
- `docs/design/brand-system.md`
- `.github/workflows/brand-guardian.yml` (bootstrap case)

## 2 · Rules (identical to `token-naming-grammar.md` §2)

| ID | Regex (applied per identifier in tokens.ts type surface) | Fail message |
|---|---|---|
| BAN-01 | `^claude[A-Za-z0-9_]*$` | "CC-legacy prefix '{name}'. See brand-system.md §2." |
| BAN-02 | `^clawd[A-Za-z0-9_]*$` | "Leaked-source prefix '{name}'." |
| BAN-03 | `^anthropic[A-Za-z0-9_]*$` | "Vendor-specific prefix '{name}'." |
| BAN-04 | `^(primary\|secondary\|tertiary)$` | "Content-free token '{name}'." |
| BAN-05 | `^accent[0-9]+$` | "Numeric suffix '{name}'." |
| BAN-06 | `^mainColor$` | "Undescriptive '{name}'." |
| BAN-07 | `^(background\|foreground)$` | "Standalone '{name}' — qualify with a role." |

## 3 · Allow-list for CC-legacy pre-existing tokens

Legacy tokens already present in `tui/src/theme/tokens.ts` at the commit where the gate workflow ships MUST be enumerated in a companion allow-list file: `tui/src/theme/.brand-guardian-allowlist.txt`. Each line is one exact identifier (no regex). The gate tests only **newly added** identifiers in a PR's diff against the type surface; pre-existing allow-listed names pass silently.

Current (2026-04-20) legacy list inferred from `tui/src/theme/tokens.ts`:

```
autoAccept
bashBorder
claude
claudeShimmer
claudeBlue_FOR_SYSTEM_SPINNER
claudeBlueShimmer_FOR_SYSTEM_SPINNER
permission
permissionShimmer
planMode
ide
promptBorder
promptBorderShimmer
text
inverseText
inactive
inactiveShimmer
subtle
suggestion
remember
background
success
error
warning
merged
warningShimmer
diffAdded
diffRemoved
diffAddedDimmed
diffRemovedDimmed
diffAddedWord
diffRemovedWord
red_FOR_SUBAGENTS_ONLY
blue_FOR_SUBAGENTS_ONLY
green_FOR_SUBAGENTS_ONLY
yellow_FOR_SUBAGENTS_ONLY
purple_FOR_SUBAGENTS_ONLY
orange_FOR_SUBAGENTS_ONLY
pink_FOR_SUBAGENTS_ONLY
cyan_FOR_SUBAGENTS_ONLY
professionalBlue
chromeYellow
clawd_body
clawd_background
userMessageBackground
userMessageBackgroundHover
messageActionsBackground
selectionBg
bashMessageBackgroundColor
memoryBackgroundColor
rate_limit_fill
rate_limit_empty
fastMode
fastModeShimmer
briefLabelYou
briefLabelClaude
rainbow_red
rainbow_orange
rainbow_yellow
rainbow_green
rainbow_blue
rainbow_indigo
rainbow_violet
rainbow_red_shimmer
rainbow_orange_shimmer
rainbow_yellow_shimmer
rainbow_green_shimmer
rainbow_blue_shimmer
rainbow_indigo_shimmer
rainbow_violet_shimmer
```

The Sonnet teammate implementing the workflow MUST regenerate this list from the actual tokens.ts at implementation time (not copy this stale list verbatim) to avoid drift.

## 4 · Gate logic (pseudocode for workflow implementation)

```
1. Parse tui/src/theme/tokens.ts type surface → extract identifier list.
2. Read .brand-guardian-allowlist.txt → legacy set.
3. For each identifier:
     if identifier in legacy_set:
         pass
     elif any BAN-XX regex matches identifier:
         append {identifier, BAN-XX, error_message} to failures
     else:
         pass
4. If failures:
     GITHUB_STEP_SUMMARY <- formatted failure table with PR line-number pointers
     exit 1
   Else:
     echo "Brand Guardian: all {n} new tokens pass §2 doctrine"
     exit 0
```

## 5 · Validation fixtures

A `tui/src/theme/__fixtures__/brand-guardian/` directory MUST be seeded at workflow-impl time with:

- `passes/` — files where every new identifier passes (4 files; one per metaphor-role category).
- `fails/` — files where at least one identifier fails each BAN-XX rule (7 files, one per rule).

Each fixture file has a sibling `.expected` text file declaring the expected exit code + failure set.

## 6 · Non-goals of this gate

- It does NOT validate color hex values (Epic H).
- It does NOT validate contrast (Accessibility Auditor at a later gate).
- It does NOT lint outside `tui/src/theme/`. Downstream components that *use* a token (e.g., `<Text color={theme.orbitalRingShimmer}>`) are validated transitively by TypeScript — if the token name doesn't exist in the type surface, `tsc` already fails.
- It does NOT run on branches outside PRs (no cron, no push triggers). This is a PR-time gate only.

## 7 · Handoff pointer (FR-011 satisfied via this file + downstream Task)

A post-verdict Task under Epic M titled `[Epic M] Implement Brand Guardian grep CI gate` MUST:

1. Add `.github/workflows/brand-guardian.yml` implementing §4 logic.
2. Add `.brand-guardian-allowlist.txt` regenerated from live tokens.ts at impl time.
3. Add the fixtures from §5.
4. Add a README note under `docs/design/brand-system.md` §2 pointing to the workflow's run URL pattern for Brand Guardian reviewers.
