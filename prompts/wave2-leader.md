# Wave 2 Execution — Leader Prompt

> This prompt is for a Lead agent (Opus) to execute Wave 2 of the Phase 1 roadmap.
> Read `AGENTS.md`, `docs/vision.md`, `docs/tool-adapters.md`, and `.specify/memory/constitution.md` first.

---

## Context

You are the Lead agent for KOSMOS Phase 1 Wave 2. Wave 1 is complete and merged to main:
- Epic #4 (LLM Client Integration) — DONE, merged
- Epic #6 (Tool System & Registry) — DONE, merged

The codebase now has:
- `src/kosmos/llm/` — FriendliAI K-EXAONE client, Pydantic v2 models, retry logic, usage tracking
- `src/kosmos/tools/` — GovAPITool model, ToolRegistry, bilingual search, tool result types
- `tests/llm/` and `tests/tools/` — unit tests for both layers

Infrastructure:
- CI/CD pipeline: ruff, mypy --strict, pytest (3.12/3.13), CodeQL, security checks
- GitHub Copilot Code Review: enabled (auto-reviews PRs)
- Branch protection on `main`: PR required, CI must pass
- Auto-merge: dependabot PRs only. Feature PRs require user approval.
- API keys: `KOSMOS_DATA_GO_KR_KEY`, `KOSMOS_KOROAD_API_KEY`, `KOSMOS_FRIENDLI_TOKEN`

## Wave 2 goal

Two Epics, both depend on Wave 1 outputs:

```
Wave 2
  ├── Epic #5  Query Engine Core (Layer 1)         ← needs LLM Client (#4) + Tool System (#6)
  └── Epic #7  Phase 1 API Adapters (KOROAD, KMA)  ← needs Tool System (#6)
```

Epic #5 and #7 are **independent of each other** — you may run their spec cycles in parallel.

## Workflow for each Epic

Follow `AGENTS.md § Spec-driven workflow` strictly. For each Epic:

### Step 1: Verify Epic issue exists
```bash
gh issue view <EPIC_NUMBER> --repo umyunsang/KOSMOS
```

### Step 2: `/speckit-specify` → spec.md
- Read `docs/vision.md` for the relevant layer design
- For Epic #5 (Query Engine): focus on Layer 1 — async generator loop, QueryState, StopReason, preprocessing pipeline, cost accounting
- For Epic #7 (API Adapters): follow `docs/tool-adapters.md § Spec cycle protocol`
  - Read ALL technical documents under `research/data/koroad/` and `research/data/kma/`
  - Inventory every endpoint, classify include/exclude/defer
  - Reference existing `src/kosmos/tools/` models for adapter interface
- Output: `specs/NNN-slug/spec.md`
- **STOP and wait for user approval**

### Step 3: `/speckit-plan` → plan.md
- Read `docs/vision.md § Reference materials` — map each design decision to a reference source
- Read `.specify/memory/constitution.md` for compliance rules
- Actively reference reconstructed sources:
  - `ChinaSiro/claude-code-sourcemap` — tool loop, permission model, context assembly
  - `openedclaude/claude-reviews-claude` — architecture review, design rationale
  - `ultraworkers/claw-code` — runtime behavior, hook system, tool execution
- For Epic #5: reference Claude Agent SDK async generator loop, Pydantic AI graph-based state machine
- For Epic #7: produce Pydantic v2 input/output schemas from API parameter tables in research docs
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
After each Teammate completes a task, perform code review before merging:

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
1. Run `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run pytest`
2. Verify cross-module imports and interfaces are consistent
3. Check for duplicate code across tasks
4. Resolve any merge conflicts with main

### Step 8: PR and CI
- Merge latest main into the feature branch first:
  ```bash
  git fetch origin main
  git merge origin/main
  ```
- Create PR with `Closes #N` for all completed Task issues
- Branch name MUST match pattern: `feat/<kebab-case-slug>` (not `spec/` or other prefixes)
- Monitor CI: `gh pr checks <PR_NUMBER> --watch --interval 10`
- If checks fail: investigate and fix, push, re-check

### Step 9: Copilot Review Gate — fix loop
The "Copilot Review Gate" required status check is managed by a GitHub App
(Cloudflare Worker). It creates a pending check on PR open/push, then evaluates
Copilot's review: 0 inline comments → pass, 1+ → fail.

**You MUST loop until the gate passes:**

1. **Check gate status**:
   ```bash
   gh pr checks <PR_NUMBER> --repo umyunsang/KOSMOS | grep "Copilot Review Gate"
   ```

2. **If gate is pending**: wait 1-2 minutes for Copilot to submit its review.

3. **If gate fails** ("Copilot found N issues"):
   a. Read the inline comments:
      ```bash
      gh api repos/umyunsang/KOSMOS/pulls/<PR_NUMBER>/comments \
        --jq '.[] | select(.user.login == "Copilot") | {path, line, body}'
      ```
   b. Triage each comment:
      - **Valid issue** (bug, security, correctness): fix immediately
      - **Style suggestion** (naming, formatting): fix if consistent with project conventions
      - **False positive** (disagree with suggestion): skip, but document reason
   c. Commit fixes and push
   d. Gate resets to pending → Copilot re-reviews → **repeat from step 1**

4. **If gate passes** ("no issues found"): proceed to Step 10.

**Max 3 fix rounds.** If still failing after 3 rounds, report remaining issues
to user and STOP.

### Step 10: Final report
- Report to user with:
  - PR link and CI status
  - Copilot review summary (issues found / fixed / skipped)
  - Internal code review summary (issues caught per task)
  - List of Task issues that will be closed on merge
- **STOP and wait for user to merge or approve**

## Agent Teams rules

| Role | Agent Type | Model | When to use |
|------|-----------|-------|-------------|
| Lead | — | Opus | Planning, spec authoring, code review, synthesis |
| Backend | Backend Architect | Sonnet | Python implementation, API integration |
| Tests | API Tester | Sonnet | Test suites, fixtures, coverage |
| Security | Security Engineer | Sonnet | Permission pipeline, audit |
| Docs | Technical Writer | Sonnet | API docs, tool adapter docs |

## Epic-specific notes

### Epic #5 — Query Engine Core
- This is the largest Layer 1 component (~5,000 lines estimated)
- Must integrate with both `src/kosmos/llm/` (LLM Client) and `src/kosmos/tools/` (Tool System)
- Key patterns from `docs/vision.md`:
  - Async generator as communication protocol (yield progress events)
  - Mutable conversation history + immutable per-call snapshots (prompt cache optimization)
  - Multi-stage preprocessing pipeline
  - Cost accounting as first-class concern
- Reference: Claude Agent SDK async generator loop, Pydantic AI graph-based state machine

### Epic #7 — Phase 1 API Adapters (KOROAD, KMA)
- 3 adapters: KOROAD accident data, KMA weather alerts, Road Risk Index
- Follow `docs/tool-adapters.md` checklist strictly
- Read ALL files under `research/data/koroad/` and `research/data/kma/` before spec
- Each adapter must:
  - Use Pydantic v2 input/output schemas
  - Have fail-closed defaults (requires_auth=True, is_personal_data per data type)
  - Include bilingual search_hint (Korean + English)
  - Have recorded fixtures for CI (never call live APIs in tests)
  - Have happy-path AND error-path tests
  - Track rate limits via usage_tracker
- Tests marked `@pytest.mark.live` for real API calls (skipped in CI)

## Hard constraints

- All source text in English. Korean only in domain data.
- Pydantic v2 for all tool I/O. Never `Any`.
- `KOSMOS_` prefix for all env vars. Never commit secrets.
- `@pytest.mark.live` on real API tests — never run in CI.
- Conventional Commits. Branch: `feat/<slug>`.
- `uv run pytest` must pass before every PR.
- Never advance to the next spec step without user approval.

## Starting the work

Begin now:
1. Pull latest main: `git checkout main && git pull origin main`
2. Read `docs/vision.md` Layer 1 (Query Engine) and Layer 2 (Tool System) sections
3. Read `src/kosmos/llm/` and `src/kosmos/tools/` to understand Wave 1 outputs
4. Open Epic #5 and #7 on GitHub to confirm they exist
5. Begin `/speckit-specify` for both Epics (they are independent — can run in parallel)
6. Present both specs to the user for approval

When Wave 2 implementation is complete and merged, report readiness for Wave 3.
