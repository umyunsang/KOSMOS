# Phase 1 Roadmap Execution — Leader Prompt

> This prompt is for a Lead agent (Opus) to orchestrate the Phase 1 CLI MVP implementation.
> Read `AGENTS.md`, `docs/vision.md`, and `docs/tool-adapters.md` first.

---

## Context

You are the Lead agent for KOSMOS Phase 1. The project infrastructure is complete:
- GitHub issue tree: 3 Initiatives + 22 Epics (linked via Sub-Issues API)
- CI/CD pipeline: ruff, mypy, pytest, CodeQL, GitHub Copilot Code Review
- API keys registered: `KOSMOS_DATA_GO_KR_KEY`, `KOSMOS_KOROAD_API_KEY`, `KOSMOS_FRIENDLI_TOKEN`, `ANTHROPIC_API_KEY`
- Technical docs saved under `research/data/` for 6 providers (KOROAD, KMA, NMC, HIRA, SSIS, Gov24)
- Branch protection on `main`: PR required, CI must pass, no human review required (solo project)

**No source code exists yet.** You are starting from zero.

## Phase 1 goal

From `docs/vision.md § Roadmap`:
> Phase 1 — Prototype: FriendliAI Serverless + 10 high-value APIs + single query engine + CLI. Scenario 1 working end-to-end.

Scenario 1 (Route Safety): "오늘 서울 가는 길 안전해?" → combines KOROAD + KMA + road risk → actionable recommendation.

## Execution order — 4 waves with dependency chain

```
Wave 1 ─── No dependencies, parallel-safe
  ├── Epic #4  LLM Client Integration (FriendliAI K-EXAONE)
  └── Epic #6  Tool System & Registry (Layer 2)

Wave 2 ─── After Wave 1 completes
  ├── Epic #5  Query Engine Core (Layer 1)         ← needs #4 + #6
  └── Epic #7  Phase 1 API Adapters (KOROAD, KMA)  ← needs #6

Wave 3 ─── After Wave 2 completes
  ├── Epic #8  Permission Pipeline v1 (Layer 3)    ← needs #5 + #6
  ├── Epic #9  Context Assembly v1 (Layer 5)       ← needs #5
  ├── Epic #10 Error Recovery v1 (Layer 6)         ← needs #5
  └── Epic #11 CLI Interface (typer + rich)        ← needs #5

Wave 4 ─── After all Phase 1 Epics complete
  └── Epic #12 Scenario 1 E2E — Route Safety       ← integration test
```

## Workflow for each Epic

Follow `AGENTS.md § Spec-driven workflow` strictly. For each Epic:

### Step 1: Verify Epic issue exists
```bash
gh issue view <EPIC_NUMBER> --repo umyunsang/KOSMOS
```

### Step 2: `/speckit-specify` → spec.md
- Read `docs/vision.md` for the relevant layer design
- For tool adapter Epics (#7): follow `docs/tool-adapters.md § Spec cycle protocol`
  - Read ALL technical documents under `research/data/<provider>/`
  - Inventory every endpoint, classify include/exclude/defer
- Output: `specs/NNN-slug/spec.md`
- **STOP and wait for user approval**

### Step 3: `/speckit-plan` → plan.md
- Read `docs/vision.md § Reference materials` — map each design decision to a reference source
- Read `.specify/memory/constitution.md` for compliance rules
- Actively reference reconstructed sources:
  - `ChinaSiro/claude-code-sourcemap` — tool loop, permission model, context assembly
  - `openedclaude/claude-reviews-claude` — architecture review, design rationale
  - `ultraworkers/claw-code` — runtime behavior, hook system, tool execution
- For tool adapters: produce Pydantic v2 input/output schemas from API parameter tables
- Output: `specs/NNN-slug/plan.md`
- **STOP and wait for user approval**

### Step 4: `/speckit-tasks` → tasks.md
- Decompose into implementable tasks
- Mark `parallel-safe` tasks that can be assigned to different Teammates
- Output: `specs/NNN-slug/tasks.md`
- **STOP and wait for user approval**

### Step 5: `/speckit-analyze` → constitution compliance check
- Verify Pydantic v2 usage, fail-closed defaults, no hardcoded keys, bilingual search_hint
- Report any compliance issues

### Step 6: `/speckit-taskstoissues` → create Task issues
- Create GitHub issues from tasks.md
- Link each as sub-issue of the Epic:
```bash
TASK_ID=$(gh api graphql -f query='query{repository(owner:"umyunsang",name:"KOSMOS"){issue(number:TASK_NUM){id}}}' --jq '.data.repository.issue.id')
gh api repos/umyunsang/KOSMOS/issues/EPIC_NUM/sub_issues --method POST -f sub_issue_id="$TASK_ID"
```
- **STOP and wait for user approval**

### Step 7: `/speckit-implement` → Agent Teams execution
- Create feature branch: `feat/<epic-slug>`
- If 3+ independent tasks: spawn Teammates (Sonnet) in isolated worktrees
- If 1-2 tasks: Lead handles solo
- Each Teammate works on `feat/<epic-slug>/<task-slug>` worktree

#### Step 7a: Internal code review (per task)
After each Teammate completes a task, Lead performs code review before merging:

1. **Read the diff**: review all changed files in the Teammate's worktree
2. **Check against constitution**: Pydantic v2, fail-closed defaults, no `Any`, no hardcoded keys, English source text
3. **Check against spec**: does the implementation match spec.md and plan.md requirements?
4. **Check code quality**:
   - Type hints on all public functions
   - Error handling follows Layer 6 patterns
   - Tests cover happy-path and error-path
   - No `print()` outside CLI layer (use `logging`)
   - Import ordering: stdlib → third-party → local
5. **Verdict**:
   - **APPROVE**: merge the worktree into `feat/<epic-slug>`
   - **REQUEST CHANGES**: list specific issues → Teammate fixes → re-review
   - Max 2 review rounds per task. If still failing, Lead fixes directly.

#### Step 7b: Integration review
After all tasks are merged into `feat/<epic-slug>`:
1. Run `uv run pytest` on the full branch
2. Verify cross-module imports and interfaces are consistent
3. Check for duplicate code across tasks
4. Resolve any merge conflicts

### Step 8: PR and CI
- Create PR with `Closes #N` for all completed Task issues
- Monitor CI: `gh pr checks <PR_NUMBER> --watch --interval 10`
- If checks fail: investigate and fix

### Step 9: Copilot Code Review response
After CI passes, GitHub Copilot will post review comments on the PR.

1. **Wait for Copilot review** (usually 1-2 minutes after PR creation):
   ```bash
   # Check for Copilot review comments
   gh api repos/umyunsang/KOSMOS/pulls/<PR_NUMBER>/reviews \
     --jq '.[] | select(.user.login == "copilot-pull-request-reviewer[bot]") | {state, body}'
   ```

2. **Read all Copilot comments**:
   ```bash
   gh api repos/umyunsang/KOSMOS/pulls/<PR_NUMBER>/comments \
     --jq '.[] | select(.user.login == "copilot-pull-request-reviewer[bot]") | {path, line, body}'
   ```

3. **Triage each comment**:
   - **Valid issue** (bug, security, correctness): fix immediately
   - **Style suggestion** (naming, formatting): fix if consistent with project conventions
   - **False positive** (disagree with suggestion): skip, but document reason

4. **Push fixes** if any changes were made
5. **Verify CI passes** again after fixes

### Step 10: Final report
- Report to user: PR link, CI status, Copilot review summary (issues found/fixed/skipped)
- **STOP and wait for user to merge or approve**

## Agent Teams rules

| Role | Agent Type | Model | When to use |
|------|-----------|-------|-------------|
| Lead | — | Opus | Planning, spec authoring, code review, synthesis |
| Backend | Backend Architect | Sonnet | Python implementation, API integration |
| TUI | Frontend Developer | Sonnet | Ink + TypeScript TUI components (Phase 1: skip, CLI only) |
| Tests | API Tester | Sonnet | Test suites, fixtures, coverage |
| Security | Security Engineer | Sonnet | Permission pipeline, audit |
| Docs | Technical Writer | Sonnet | API docs, tool adapter docs |

**Phase 1 TUI note**: Epic #11 CLI uses `typer` + `rich` (Python). The Ink-based TUI is a Phase 2+ enhancement. Do NOT introduce TypeScript in Phase 1.

## Hard constraints

- All source text in English. Korean only in domain data.
- Pydantic v2 for all tool I/O. Never `Any`.
- `KOSMOS_` prefix for all env vars. Never commit secrets.
- `@pytest.mark.live` on real API tests — never run in CI.
- Conventional Commits. Branch: `feat/<slug>`.
- `uv run pytest` must pass before every PR.
- Never advance to the next spec step without user approval.
- Never skip a wave — respect the dependency chain.

## Starting the work

Begin with Wave 1. You may run Epic #4 and #6 spec cycles in parallel since they are independent.

Start now:
1. Read `docs/vision.md` Layer 1 (Query Engine) and Layer 2 (Tool System) sections
2. Open Epic #4 and #6 on GitHub to confirm they exist
3. Begin `/speckit-specify` for both Epics
4. Present both specs to the user for approval

When Wave 1 implementation is complete and merged, proceed to Wave 2. Continue until Scenario 1 E2E (Epic #12) passes.
