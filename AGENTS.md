# AGENTS.md — KOSMOS

> Entry point for AI coding agents. Imported by `CLAUDE.md`. Keep under 120 lines. Long-form details live under `docs/`.

## What KOSMOS is

A conversational multi-agent platform that orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. Student portfolio project. Not affiliated with Anthropic, LG AI Research, or the Korean government.

**Canonical vision**: `docs/vision.md` — six-layer design. Read before any architectural change.

## Stack

Python 3.12+ · FriendliAI Serverless (OpenAI-compatible) for K-EXAONE · `typer` + `rich` CLI · `httpx` (async) · `pydantic` v2 · `pytest` + `pytest-asyncio` · `uv` + `pyproject.toml` · Apache-2.0. Changing any requires an ADR under `docs/adr/`.

## Hard rules (never violate)

- All source text in English. Korean domain data is the only exception.
- Env vars prefixed `KOSMOS_`. Never commit `.env` or `secrets/`.
- Stdlib `logging` only; no `print()` outside CLI output layer.
- Pydantic v2 for all tool I/O. Never `Any`.
- Clean-room rule: reference only MIT-licensed SDKs and public documentation listed in `docs/vision.md § Reference materials`. Never clone, read, or reference reconstructed/decompiled source repositories. Borrow architectural patterns, never line-for-line code.
- Never call live `data.go.kr` APIs from CI tests.
- Never add a dependency outside a spec-driven PR.
- Never `--force` push `main`, `--no-verify`, or bypass signing.
- Never create `requirements.txt`, `setup.py`, or `Pipfile`.
- Never commit a file larger than 1 MB without asking.
- Never introduce TypeScript, Go, or Rust.

## Issue hierarchy

Issues follow a tree structure using GitHub Sub-Issues:

```
GitHub Project (Roadmap view)
└── Initiative (label: initiative)        — roadmap phase
    └── Epic (label: epic)                — feature-sized, links to spec
        └── Task (label: agent-ready)     — agent-executable unit
            └── Sub-task (optional)       — fine-grained step
```

Labels: `initiative`, `epic`, `agent-ready`, `needs-spec`, `parallel-safe`, `blocked`, `size/S`, `size/M`, `size/L`, plus layer labels (`query-engine`, `tool-system`, `permission`, `agent-swarm`, `context`, `error-recovery`).

**Creating sub-issue links (required — do not use body mentions as a substitute):**

```bash
# 1. Get the node ID of the child issue
CHILD_NODE_ID=$(gh api graphql -f query='
  query { repository(owner:"umyunsang", name:"KOSMOS") {
    issue(number: CHILD_NUMBER) { id }
  }}' --jq '.data.repository.issue.id')

# 2. Attach child as sub-issue of parent
gh api repos/umyunsang/KOSMOS/issues/PARENT_NUMBER/sub_issues \
  --method POST -f sub_issue_id="$CHILD_NODE_ID"
```

Always use this API to build the hierarchy. Never rely on `#N` mentions or markdown checklists for parent-child relationships.

## Spec-driven workflow

Non-trivial features use [GitHub Spec Kit](https://github.com/github/spec-kit):

1. Create/verify GitHub Issue (citizen-facing terms)
2. `/speckit-specify` → `specs/NNN-slug/spec.md`
3. Human review
4. `/speckit-plan` → `plan.md`
5. `/speckit-tasks` → `tasks.md`
6. `/speckit-implement` → Agent Teams parallel execution
7. Open PR with `Closes #N` → monitor CI checks

Small fixes (typos, one-line bugs, docs-only) skip the cycle.

## Agent Teams

- Lead (Opus, effort=high): planning, spec authoring, code review, synthesis.
- Teammates (Sonnet): implementation, tests, refactoring — spawned at step 6.
- 3+ independent tasks → parallel via Agent Teams. 1-2 tasks → Lead handles solo.
- Each Teammate works in an isolated worktree to avoid file conflicts.
- Recommended agents per role:

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
├── research/
│   ├── papers/           # LaTeX/MD paper drafts
│   ├── experiments/      # Evaluation scripts and results
│   ├── figures/          # Charts, architecture diagrams
│   └── data/             # Evaluation datasets (no PII)
├── .specify/, .claude/
└── .github/
```

## Do not touch

- `.specify/`, `.claude/skills/` — managed by Spec Kit
- `LICENSE` — Apache-2.0, change requires ADR
- `docs/vision.md` layer count/names — change requires ADR
- `.env`, `secrets/` — never commit

## Conflict resolution

Rules in this file win over individual specs. A spec conflicting with `docs/vision.md` is a blocker — open an issue before proceeding. When stuck, open a GitHub Discussion rather than guessing.
