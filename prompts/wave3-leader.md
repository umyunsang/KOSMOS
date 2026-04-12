# Wave 3 Execution — Leader Prompt

> This prompt is for a Lead agent (Opus) to execute Wave 3 of the Phase 1 roadmap.
> Read `AGENTS.md`, `docs/vision.md`, and `.specify/memory/constitution.md` first.

---

## Context

You are the Lead agent for KOSMOS Phase 1 Wave 3. Prior waves are complete and merged:
- Wave 1: Epic #4 (LLM Client), Epic #6 (Tool System) — DONE
- Wave 2: Epic #5 (Query Engine Core), Epic #7 (API Adapters: KOROAD, KMA) — DONE

The codebase now has:
- `src/kosmos/llm/` — FriendliAI K-EXAONE client, models, retry, usage tracking
- `src/kosmos/tools/` — GovAPITool, ToolRegistry, bilingual search, adapters (KOROAD, KMA)
- `src/kosmos/engine/` — Query engine async generator loop, QueryState, StopReason, preprocessing
- Full test coverage for all above layers

Infrastructure:
- CI/CD: ruff, mypy --strict, pytest (3.12/3.13), CodeQL, security checks
- GitHub Copilot Code Review enabled
- Branch protection: PR required, CI must pass
- Auto-merge: dependabot only. Feature PRs require user approval.

## Wave 3 goal

Four Epics, ALL independent of each other — run all 4 spec cycles in parallel:

```
Wave 3 ─── All parallel-safe (each depends on Wave 2 outputs, not on each other)
  ├── Epic #8   Permission Pipeline v1 (Layer 3)    ← needs Query Engine + Tool System
  ├── Epic #9   Context Assembly v1 (Layer 5)       ← needs Query Engine
  ├── Epic #10  Error Recovery v1 (Layer 6)          ← needs Query Engine
  └── Epic #11  CLI Interface (typer + rich)         ← needs Query Engine
```

## Parallel execution strategy

Since all 4 Epics are independent:
1. Run `/speckit-specify` for all 4 Epics in parallel → present all 4 specs for approval
2. After approval, run `/speckit-plan` for all 4 in parallel → present all 4 plans
3. After approval, run `/speckit-tasks` for all 4 → present all 4 task lists
4. After approval, run `/speckit-analyze` + `/speckit-taskstoissues` for all 4
5. Implementation: spawn Agent Teams across all 4 Epics simultaneously

## Workflow per Epic

Follow `AGENTS.md § Spec-driven workflow`. Same 10-step process as Wave 2.

### Steps 1-6: Spec cycle (run for all 4 Epics in parallel)

For each Epic, follow Steps 1-6 from `prompts/wave2-leader.md`. Key differences per Epic:

#### Epic #8 — Permission Pipeline v1 (Layer 3)
- Reference: `docs/vision.md § Layer 3 — Permission Pipeline`
- Reference sources: OpenAI Agents SDK guardrail pipeline, Claude Code reconstructed permission model
- Scope for v1:
  - 7-step gauntlet skeleton (all steps defined, steps 2-5 as pass-through stubs)
  - Step 1: Configuration rules (per-API access tier: public, authenticated, restricted)
  - Step 6: Sandboxed execution (isolated context, no ambient credentials)
  - Step 7: Audit log (timestamp, citizen id, API, parameters, outcome)
  - Bypass-immune checks (NON-NEGOTIABLE): cannot query another citizen's records, medical records without consent, writes without identity verification
- Constitution: fail-closed defaults are CRITICAL here. Read `.specify/memory/constitution.md § II` carefully.

#### Epic #9 — Context Assembly v1 (Layer 5)
- Reference: `docs/vision.md § Layer 5 — Context Assembly`
- Reference sources: Claude Code reconstructed context assembly, Anthropic docs prompt caching
- Scope for v1:
  - System prompt assembly (platform-wide policies)
  - Session context (conversation state)
  - Per-turn attachments (auth level, in-flight state, API health)
  - Reminder cadence for long sessions
  - Memory tiers 1-4 (system, region, citizen, session). Tier 5 (auto) deferred to Phase 2.

#### Epic #10 — Error Recovery v1 (Layer 6)
- Reference: `docs/vision.md § Layer 6 — Error Recovery`
- Reference sources: OpenAI Agents SDK retry matrix, Claude Agent SDK error handling
- Scope for v1:
  - Error classification: 429, 503, 401, timeout, data inconsistency, hard failure
  - Recovery strategies per class (backoff, alternative API, token refresh, retry, cross-verify, graceful message)
  - Foreground vs background distinction
  - `withRetry`-style composable retry policies
  - Integration with Query Engine loop and Tool System

#### Epic #11 — CLI Interface (typer + rich)
- Reference: NOT Ink/TypeScript. Phase 1 CLI uses Python `typer` + `rich` only.
- Scope for v1:
  - `typer` CLI with `rich` console output
  - Interactive conversation loop (REPL-style)
  - Streaming LLM response display
  - Tool execution progress indicators
  - Error display with user-friendly messages
  - Session management (start, resume, quit)
  - `KOSMOS_` env var configuration

### Steps 7-10: Implementation + Review (run for all 4 Epics)

Same process as Wave 2. For each Epic:

#### Step 7: Implementation with internal code review
- Create feature branch: `feat/<epic-slug>` (e.g., `feat/permission-pipeline-v1`)
- Spawn Teammates (Sonnet) for parallel task execution
- **Step 7a**: Lead reviews each Teammate's code per task
  - Check constitution compliance, spec alignment, code quality
  - APPROVE or REQUEST CHANGES (max 2 rounds)
- **Step 7b**: Integration review after all tasks merged
  - `uv run ruff check src tests && uv run ruff format --check src tests && uv run mypy src && uv run pytest`
  - Cross-module interface consistency check

#### Step 8: PR and CI
- Merge latest main: `git fetch origin main && git merge origin/main`
- Branch name: `feat/<kebab-case-slug>`
- PR body: `Closes #N` for all Task issues
- Monitor CI until pass

#### Step 9: Copilot Code Review response
- Read Copilot comments via `gh api`
- Triage: fix valid issues, skip false positives
- Push fixes, verify CI

#### Step 10: Final report
- PR link, CI status, Copilot summary, internal review summary
- **STOP and wait for user to merge**

## Agent Teams rules

| Role | Agent Type | Model | When to use |
|------|-----------|-------|-------------|
| Lead | — | Opus | Planning, spec authoring, code review, synthesis |
| Backend | Backend Architect | Sonnet | Python implementation |
| Tests | API Tester | Sonnet | Test suites, fixtures |
| Security | Security Engineer | Sonnet | Permission pipeline (#8) |
| Docs | Technical Writer | Sonnet | API docs |

## Hard constraints

- All source text in English. Korean only in domain data.
- Pydantic v2 for all tool I/O. Never `Any`.
- `KOSMOS_` prefix for all env vars. Never commit secrets.
- `@pytest.mark.live` on real API tests — never run in CI.
- Conventional Commits. Branch: `feat/<slug>`.
- `uv run pytest` must pass before every PR.
- Never advance to the next spec step without user approval.
- Phase 1 CLI uses `typer` + `rich` (Python). Do NOT introduce TypeScript or Ink.

## Starting the work

Begin now:
1. `git checkout main && git pull origin main`
2. Read the Wave 2 outputs: `src/kosmos/engine/`, `src/kosmos/tools/adapters/`
3. Verify Epics #8, #9, #10, #11 exist on GitHub
4. Begin `/speckit-specify` for ALL 4 Epics in parallel
5. Present all 4 specs to the user for approval

When all 4 PRs are merged, report readiness for Wave 4 (Scenario 1 E2E).
