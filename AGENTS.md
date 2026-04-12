# AGENTS.md — KOSMOS

> Entry point for AI coding agents. Imported by `CLAUDE.md`. Keep under 120 lines. Long-form details live under `docs/`.

## What KOSMOS is

A conversational multi-agent platform that orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. Student portfolio project. Not affiliated with Anthropic, LG AI Research, or the Korean government.

**Canonical vision**: `docs/vision.md` — six-layer design. Read before any architectural change.

## Stack

**Backend**: Python 3.12+ · FriendliAI Serverless (OpenAI-compatible) for K-EXAONE · `httpx` (async) · `pydantic` v2 · `pytest` + `pytest-asyncio` · `uv` + `pyproject.toml` · Apache-2.0.
**TUI**: Ink (React for CLIs) + Bun · TypeScript. Ref: Gemini CLI (Apache-2.0) + Claude Code reconstructed architecture.
Stack changes require an ADR under `docs/adr/`.

## Hard rules (never violate)

- All source text in English. Korean domain data is the only exception.
- Env vars prefixed `KOSMOS_`. Never commit `.env` or `secrets/`.
- Stdlib `logging` only; no `print()` outside CLI output layer.
- Pydantic v2 for all tool I/O. Never `Any`.
- Never call live `data.go.kr` APIs from CI tests.
- Never add a dependency outside a spec-driven PR.
- Never `--force` push `main`, `--no-verify`, or bypass signing.
- Never create `requirements.txt`, `setup.py`, or `Pipfile`.
- Never commit a file larger than 1 MB without asking.
- Never introduce Go or Rust. TypeScript is allowed only for the TUI layer (Ink + Bun).

## Issue hierarchy

Issues follow a tree structure using GitHub Sub-Issues (not body mentions):

```
Initiative (label: initiative) → Epic (label: epic) → Task (label: agent-ready)
```

- **Initiative**: created manually (roadmap phase, e.g. "Phase 1 — CLI MVP")
- **Epic**: created manually before spec work (feature-sized, label: `epic`, `needs-spec`)
- **Task**: created ONLY by `/speckit-taskstoissues` from reviewed `tasks.md`

Labels: `initiative`, `epic`, `agent-ready`, `needs-spec`, `parallel-safe`, `blocked`, `size/{S,M,L}`, plus layer labels. All parent-child links use the Sub-Issues API (see Task-to-issue rule).

## Spec-driven workflow

Non-trivial features use [GitHub Spec Kit](https://github.com/github/spec-kit):

1. Create/verify **Epic** issue (citizen-facing terms, label: `epic`)
2. `/speckit-specify` → `specs/NNN-slug/spec.md` → human review
3. `/speckit-plan` → `plan.md` → **must read `docs/vision.md § Reference materials`** → human review
4. `/speckit-tasks` → `tasks.md` → human review
5. `/speckit-analyze` → constitution compliance check
6. `/speckit-taskstoissues` → create Task issues from verified tasks.md
7. Link Task issues as sub-issues of Epic via `gh api` (see Issue hierarchy)
8. `/speckit-implement` → Agent Teams parallel execution
9. Open PR with `Closes #N` → monitor CI checks
10. Copilot Review Gate fix loop → pass required before merge

Small fixes (typos, one-line bugs, docs-only) skip the cycle.

### Copilot Review Gate rule
The "Copilot Review Gate" is a required status check managed by a GitHub App (Cloudflare Worker). After PR creation, Copilot auto-reviews and the gate evaluates: 0 inline comments → pass, 1+ → fail. **You MUST loop until the gate passes**: read Copilot comments → fix valid issues → push → Copilot re-reviews → repeat. Max 3 fix rounds; if still failing, report to user and STOP.

### Reference source rule
Every `/speckit-plan` Phase 0 must consult `.specify/memory/constitution.md` and `docs/vision.md § Reference materials`. All sources are valid: open-source repos, official docs, reconstructed architecture analyses, and leaked-source review documents. Map each design decision to a concrete reference.

### Task-to-issue rule
Task issues come **only** from reviewed `tasks.md` via `/speckit-taskstoissues`. After creation, link each as a sub-issue of its Epic:

```bash
TASK_ID=$(gh api graphql -f query='query{repository(owner:"umyunsang",name:"KOSMOS"){issue(number:TASK_NUM){id}}}' --jq '.data.repository.issue.id')
gh api repos/umyunsang/KOSMOS/issues/EPIC_NUM/sub_issues --method POST -f sub_issue_id="$TASK_ID"
```

## Agent Teams

- Lead (Opus, effort=high): planning, spec authoring, code review, synthesis.
- Teammates (Sonnet): implementation, tests, refactoring — spawned at step 6.
- 3+ independent tasks → parallel via Agent Teams. 1-2 tasks → Lead handles solo.
- Recommended agents per role (each Teammate uses an isolated worktree):

| Role | Agent | Model |
|------|-------|-------|
| Architecture | Software Architect | Opus |
| Backend | Backend Architect | Sonnet |
| CLI/Frontend | Frontend Developer | Sonnet |
| Tests | API Tester | Sonnet |
| Code review | Code Reviewer | Opus |
| Security | Security Engineer | Sonnet |
| Docs | Technical Writer | Sonnet |

## Commits, branches, PRs

Conventional Commits. Branches: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`. PRs for code; direct `main` commits only for `docs:` / `chore:` touching no source. Full details: `docs/conventions.md`.

## New tool adapter

Pydantic v2 I/O · fail-closed defaults · Korean + English `search_hint` · recorded fixture · happy-path + error-path test · no hardcoded keys. Full checklist: `docs/tool-adapters.md`.

## Testing
`uv run pytest` before every commit. Live-API tests marked `@pytest.mark.live`, skipped by default. Full guide: `docs/testing.md`.

## Directory layout

```
KOSMOS/
├── AGENTS.md, CLAUDE.md, README.md
├── pyproject.toml
├── src/kosmos/
├── tests/
├── specs/NNN-slug/
├── docs/
│   ├── vision.md, conventions.md, tool-adapters.md, testing.md
│   └── adr/
├── research/             # papers, experiments, figures, data (no PII)
├── .specify/, .claude/
└── .github/
```

## Do not touch
`.specify/`, `.claude/skills/` (Spec Kit) · `LICENSE` (Apache-2.0, ADR required) · `docs/vision.md` layer names (ADR required) · `.env`, `secrets/` (never commit).

## Conflict resolution
Rules in this file win over individual specs. A spec conflicting with `docs/vision.md` is a blocker — open an issue before proceeding. When stuck, open a GitHub Discussion rather than guessing.
