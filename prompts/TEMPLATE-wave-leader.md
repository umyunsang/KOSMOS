# Wave Leader Prompt Template

> Use this template to generate a wave-specific leader prompt for any Phase/Wave.
> Fill in the `{{PLACEHOLDER}}` values and delete this instruction block.
>
> **How to use**: Copy this file, replace all `{{...}}` placeholders, and save as `wave<N>-leader.md`.
> Or give this template to Claude with the context and ask it to generate the prompt.

---

# {{WAVE_NAME}} Execution — Leader Prompt

> This prompt is for a Lead agent (Opus) to execute {{WAVE_NAME}} of the Phase {{PHASE_NUMBER}} roadmap.
> Read `AGENTS.md`, `docs/vision.md`, and `.specify/memory/constitution.md` first.

---

## Context

You are the Lead agent for KOSMOS Phase {{PHASE_NUMBER}} {{WAVE_NAME}}. Prior waves are complete:
{{COMPLETED_WAVES}}
<!-- Example:
- Wave 1: Epic #4 (LLM Client), Epic #6 (Tool System) — DONE
- Wave 2: Epic #5 (Query Engine), Epic #7 (API Adapters) — DONE
-->

The codebase now has:
{{EXISTING_CODEBASE}}
<!-- Example:
- `src/kosmos/llm/` — LLM Client
- `src/kosmos/tools/` — Tool System + Adapters
- `src/kosmos/engine/` — Query Engine
-->

Infrastructure:
- CI/CD: ruff, mypy --strict, pytest (3.12/3.13), CodeQL, security checks
- Branch protection: PR required, CI must pass
- Auto-merge: dependabot only. Feature PRs require user approval.

## {{WAVE_NAME}} goal

{{WAVE_EPIC_COUNT}} Epics in this wave:

```
{{WAVE_DEPENDENCY_TREE}}
```
<!-- Example:
Wave 3 ─── All parallel-safe
  ├── Epic #8   Permission Pipeline v1 (Layer 3)
  ├── Epic #9   Context Assembly v1 (Layer 5)
  ├── Epic #10  Error Recovery v1 (Layer 6)
  └── Epic #11  CLI Interface (typer + rich)
-->

{{PARALLEL_NOTE}}
<!-- "All Epics are independent — run spec cycles in parallel." OR
     "Epic #X depends on #Y. Run #Y first, then #X." -->

## Epic-specific notes

{{EPIC_DETAILS}}
<!-- For each Epic, write:

#### Epic #N — Name (Layer)
- Reference: `docs/vision.md § Layer N`
- Reference sources: (from constitution reference mapping table)
- Scope for this phase:
  - Requirement 1
  - Requirement 2
  - What is deferred to next phase
-->

## Workflow per Epic

Follow `AGENTS.md § Spec-driven workflow`. 10-step process:

### Steps 1-6: Spec cycle

#### Step 1: Verify Epic issue exists
```bash
gh issue view <EPIC_NUMBER> --repo umyunsang/KOSMOS
```

#### Step 2: `/speckit-specify` → spec.md
- Read `docs/vision.md` for the relevant layer design
{{SPECIFY_EXTRA_INSTRUCTIONS}}
<!-- For tool adapter Epics: "follow docs/tool-adapters.md § Spec cycle protocol" -->
- Output: `specs/NNN-slug/spec.md`
- **STOP and wait for user approval**

#### Step 3: `/speckit-plan` → plan.md
- Read `docs/vision.md § Reference materials` — map each design decision to a reference source
- Read `.specify/memory/constitution.md` for compliance rules
- Actively reference reconstructed sources:
  - `ChinaSiro/claude-code-sourcemap` — tool loop, permission model, context assembly
  - `openedclaude/claude-reviews-claude` — architecture review, design rationale
  - `ultraworkers/claw-code` — runtime behavior, hook system, tool execution
{{PLAN_EXTRA_INSTRUCTIONS}}
- Output: `specs/NNN-slug/plan.md`
- **STOP and wait for user approval**

#### Step 4: `/speckit-tasks` → tasks.md
- Decompose into implementable tasks
- Mark `parallel-safe` tasks that can be assigned to different Teammates
- Output: `specs/NNN-slug/tasks.md`
- **STOP and wait for user approval**

#### Step 5: `/speckit-analyze` → constitution compliance check

#### Step 6: `/speckit-taskstoissues` → create Task issues
- Create GitHub issues from tasks.md
- Link each as sub-issue of the Epic:
```bash
TASK_ID=$(gh api graphql -f query='query{repository(owner:"umyunsang",name:"KOSMOS"){issue(number:TASK_NUM){id}}}' --jq '.data.repository.issue.id')
gh api repos/umyunsang/KOSMOS/issues/EPIC_NUM/sub_issues --method POST -f sub_issue_id="$TASK_ID"
```
- **STOP and wait for user approval**

### Steps 7-10: Implementation + Review

#### Step 7: `/speckit-implement` → Agent Teams execution
- Create feature branch: `feat/<epic-slug>`
- If 3+ independent tasks: spawn Teammates (Sonnet) in isolated worktrees
- If 1-2 tasks: Lead handles solo

##### Step 7a: Internal code review (per task)
After each Teammate completes a task:
1. Read the diff
2. Check against constitution: Pydantic v2, fail-closed defaults, no `Any`, no hardcoded keys, English source text
3. Check against spec: implementation matches spec.md and plan.md
4. Check code quality: type hints, error handling, tests (happy + error path), no `print()`, import ordering
5. Verdict: APPROVE → merge, or REQUEST CHANGES → fix → re-review (max 2 rounds)

##### Step 7b: Integration review
After all tasks merged into `feat/<epic-slug>`:
```bash
uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run pytest
```

#### Step 8: PR and CI
- Merge latest main: `git fetch origin main && git merge origin/main`
- Branch name MUST match: `feat/<kebab-case-slug>`
- PR body: `Closes #N` for all Task issues
- Monitor CI: `gh pr checks <PR_NUMBER> --watch --interval 10`
- If checks fail: investigate and fix

#### Step 9: Final report
- PR link, CI status
- List of Task issues that close on merge
- **STOP and wait for user to merge**

## Agent Teams rules

| Role | Agent Type | Model | When to use |
|------|-----------|-------|-------------|
| Lead | — | Opus | Planning, spec authoring, code review, synthesis |
| Backend | Backend Architect | Sonnet | Python implementation |
| Tests | API Tester | Sonnet | Test suites, fixtures |
| Security | Security Engineer | Sonnet | Permission pipeline |
| Docs | Technical Writer | Sonnet | API docs |

## Hard constraints

- All source text in English. Korean only in domain data.
- Pydantic v2 for all tool I/O. Never `Any`.
- `KOSMOS_` prefix for all env vars. Never commit secrets.
- `@pytest.mark.live` on real API tests — never run in CI.
- Conventional Commits. Branch: `feat/<slug>`.
- `uv run pytest` must pass before every PR.
- Never advance to the next spec step without user approval.
{{EXTRA_CONSTRAINTS}}

## Starting the work

Begin now:
1. `git checkout main && git pull origin main`
2. Read existing source code to understand current codebase state
3. Verify all Epic issues exist on GitHub
{{START_INSTRUCTIONS}}
<!-- Example:
4. Begin `/speckit-specify` for all Epics in parallel
5. Present all specs to the user for approval
-->

---

## Template reference — Placeholder descriptions

| Placeholder | Description | Example |
|---|---|---|
| `{{WAVE_NAME}}` | Wave identifier | `Wave 3`, `Phase 2 Wave 1` |
| `{{PHASE_NUMBER}}` | Phase number | `1`, `2`, `3` |
| `{{COMPLETED_WAVES}}` | Bullet list of completed waves + Epics | See above |
| `{{EXISTING_CODEBASE}}` | Bullet list of `src/kosmos/` modules | See above |
| `{{WAVE_EPIC_COUNT}}` | Number of Epics | `4 Epics, ALL parallel-safe` |
| `{{WAVE_DEPENDENCY_TREE}}` | ASCII tree of Epics + dependencies | See above |
| `{{PARALLEL_NOTE}}` | Parallel execution guidance | See above |
| `{{EPIC_DETAILS}}` | Per-Epic reference, scope, and notes | See above |
| `{{SPECIFY_EXTRA_INSTRUCTIONS}}` | Extra instructions for `/speckit-specify` | Tool adapter protocol |
| `{{PLAN_EXTRA_INSTRUCTIONS}}` | Extra instructions for `/speckit-plan` | Schema design notes |
| `{{EXTRA_CONSTRAINTS}}` | Phase-specific constraints | `- Phase 1 CLI: typer + rich only` |
| `{{START_INSTRUCTIONS}}` | Starting steps specific to this wave | See above |

## Constitution reference mapping (copy relevant rows)

| Layer | Primary reference | Secondary reference |
|---|---|---|
| Query Engine | Claude Agent SDK (async generator loop) | Claude Code reconstructed (tool loop internals) |
| Tool System | Pydantic AI (schema-driven registry) | Claude Agent SDK (tool definitions) |
| Permission Pipeline | OpenAI Agents SDK (guardrail pipeline) | Claude Code reconstructed (permission model) |
| Agent Swarms | AutoGen (AgentRuntime mailbox IPC) | Anthropic Cookbook (orchestrator-workers) |
| Context Assembly | Claude Code reconstructed (context assembly) | Anthropic docs (prompt caching) |
| Error Recovery | OpenAI Agents SDK (retry matrix) | Claude Agent SDK (error handling) |
| TUI | Ink + Gemini CLI (React terminal UI) | Claude Code reconstructed (TUI components) |
