---
name: "speckit-taskstoissues"
description: "Convert existing tasks into actionable, dependency-ordered GitHub issues for the feature based on available design artifacts."
argument-hint: "Optional filter or label for GitHub issues"
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/taskstoissues.md"
user-invocable: true
disable-model-invocation: false
---


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before tasks-to-issues conversion)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_taskstoissues` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

1. Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` from repo root and parse FEATURE_DIR and AVAILABLE_DOCS list. All paths must be absolute. For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").
1. From the executed script, extract the path to **tasks**.
1. **100 sub-issue cap pre-flight check** (MANDATORY):
   - Resolve the originating Epic number (same procedure as "Deferred Item Issue Creation" § 3 below).
   - Query the Epic's current sub-issue count:
     ```bash
     gh api graphql -f query='query($num: Int!) { repository(owner: "OWNER", name: "REPO") { issue(number: $num) { subIssues { totalCount } } } }' -F num=EPIC_NUM
     ```
   - Count `- [ ]` checkboxes in `tasks.md` → `NEW_TASKS`.
   - If `existing_count + NEW_TASKS + deferred_count > 100`: **STOP**. Report the overflow to the user with three options:
     1. Re-run `speckit-tasks` and consolidate per its "Task Count Budget" section.
     2. Split the Epic into multiple topically-coherent Epics under the same Initiative.
     3. Acknowledge the overflow explicitly and accept that surplus Tasks will be created as orphans (requires human "proceed" confirmation — do not auto-proceed).
   - Only after the cap check passes (or user explicitly authorises overflow) proceed to remote URL validation.
1. Get the Git remote by running:

```bash
git config --get remote.origin.url
```

> [!CAUTION]
> ONLY PROCEED TO NEXT STEPS IF THE REMOTE IS A GITHUB URL

1. For each task in the list, use the GitHub MCP server to create a new issue in the repository that is representative of the Git remote.

> [!CAUTION]
> UNDER NO CIRCUMSTANCES EVER CREATE ISSUES IN REPOSITORIES THAT DO NOT MATCH THE REMOTE URL

## Deferred Item Issue Creation

After all task issues are created, handle deferred items from the spec:

1. Read `FEATURE_DIR/spec.md` and locate the "Scope Boundaries & Deferred Items" section
2. Parse the "Deferred to Future Work" table
3. **Resolve the originating Epic number** (ORIGINATING_EPIC):
   - Scan `spec.md` for the first `#NNN` reference next to the tokens `Epic`, `Parent Epic`, or `Originating Epic` (case-insensitive)
   - If none found, scan `plan.md` for the same pattern
   - If still not found: **STOP** and ask the user for the Epic number — do NOT create orphan deferred issues
4. For each row where `Tracking Issue` is `NEEDS TRACKING`:
   - Create a placeholder GitHub issue with:
     - **Title**: `[Deferred] {Item}` (e.g., `[Deferred] Full TUI (Ink + React + Bun)`)
     - **Body**: Include the deferral reason, target epic/phase, a link back to the originating spec, and `**Originating Epic**: #ORIGINATING_EPIC`
     - **Labels**: `needs-spec`, `deferred`
   - **Link as sub-issue of ORIGINATING_EPIC** (mandatory, per `AGENTS.md § Issue hierarchy`):
     ```bash
     NEW_ID=$(gh api repos/OWNER/REPO/issues/NEW_NUM --jq '.id')
     gh api repos/OWNER/REPO/issues/ORIGINATING_EPIC/sub_issues --method POST -F sub_issue_id=$NEW_ID
     ```
     Note: use `-F` (integer), not `-f` (string) — the API rejects string IDs.
   - Update the spec.md table: replace `NEEDS TRACKING` with the new issue number (e.g., `#291`)
5. If the "Deferred to Future Work" table has no `NEEDS TRACKING` entries, skip silently
6. **Verify linkage**: run `gh api repos/OWNER/REPO/issues/ORIGINATING_EPIC/sub_issues --jq '.[].number'` and confirm every newly created deferred issue number appears in the output
7. Report: number of deferred-item issues created, with issue numbers AND the Epic they are linked under

> [!IMPORTANT]
> Deferred item issues are placeholders for future epics. They ensure no work is silently dropped.
> Sub-issue linkage to the originating Epic is **mandatory** — orphan deferred issues violate `AGENTS.md § Issue hierarchy`.
> The project lead decides whether to later promote a placeholder to a full Epic (apply `epic` label, detach from parent, re-attach to an Initiative) or close it as won't-fix.

## Post-Execution Checks

**Check for extension hooks (after tasks-to-issues conversion)**:
Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.after_taskstoissues` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently
