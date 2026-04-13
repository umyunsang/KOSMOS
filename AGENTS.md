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

`Initiative` → `Epic` → `Task` (Sub-Issues API, not body mentions). Initiatives/Epics: manual. Tasks: ONLY from `/speckit-taskstoissues`. Labels: `initiative`, `epic`, `agent-ready`, `needs-spec`, `parallel-safe`, `blocked`, `size/{S,M,L}`, plus layer labels.

## Spec-driven workflow

Non-trivial features use [GitHub Spec Kit](https://github.com/github/spec-kit):

1. Create/verify **Epic** issue (label: `epic`)
2. `/speckit-specify` → `specs/NNN-slug/spec.md` → human review
3. `/speckit-plan` → `plan.md` → **read `docs/vision.md § Reference materials`** → human review
4. `/speckit-tasks` → `tasks.md` → human review
5. `/speckit-analyze` → constitution compliance check
6. `/speckit-taskstoissues` → create Task issues → link as sub-issues of Epic
7. `/speckit-implement` → Agent Teams parallel execution
8. PR with `Closes #EPIC` only (not Task sub-issues) → monitor CI → close Task sub-issues after merge

Small fixes (typos, one-line bugs, docs-only) skip the cycle.

**Reference source rule**: Every `/speckit-plan` Phase 0 must consult `.specify/memory/constitution.md` and `docs/vision.md § Reference materials`. Map each design decision to a concrete reference.
**Task-to-issue rule**: Tasks ONLY from `/speckit-taskstoissues`. Link as sub-issues of Epic via `gh api`. Code: `docs/conventions.md § Task linking`.
**PR close rule**: `Closes #EPIC` only — never Task sub-issues (GitHub fails at 50+). Close sub-issues after merge. Code: `docs/conventions.md § PR closing`.

## Agent Teams

- Lead (Opus): planning, spec authoring, code review, synthesis.
- Teammates (Sonnet): implementation, tests, refactoring — spawned at `/speckit-implement`.
- 3+ independent tasks → parallel Agent Teams. 1-2 tasks → Lead solo.

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

## Copilot Review Gate

Cloudflare Worker (`infra/copilot-gate-app/`) → Check Run gate. **CRITICAL >= 1 → fail**, **IMPORTANT >= 3 → fail**, else pass. Deploy: `cd infra/copilot-gate-app && npx wrangler deploy`.

**After every push (including fix commits from Copilot review feedback):**
1. Read Copilot review comments (`gh api 'repos/OWNER/REPO/pulls/N/comments'`), fix issues, commit and push.
2. **Always** re-request Copilot review via GraphQL after push — it does NOT auto-trigger:
   ```bash
   PR_NODE_ID=$(gh api repos/umyunsang/KOSMOS/pulls/<N> --jq '.node_id')
   gh api graphql -f query='mutation($input: RequestReviewsByLoginInput!) { requestReviewsByLogin(input: $input) { pullRequest { id } } }' \
     -F "input[pullRequestId]=$PR_NODE_ID" -F 'input[botLogins][]=copilot-pull-request-reviewer[bot]' -F 'input[union]:=true'
   ```
3. If gate stays `pending`/`in_progress` for 2+ min after re-request, add label `copilot-review-bypass`.
4. `requestReviewsByLogin` has **~1/3 failure rate** — retry once before resorting to bypass label.

Full procedure: `docs/copilot-gate.md`.

## New tool adapter

Pydantic v2 I/O · fail-closed defaults · Korean + English `search_hint` · recorded fixture · happy-path + error-path test · no hardcoded keys. Full checklist: `docs/tool-adapters.md`.

## Testing
`uv run pytest` before every commit. Live-API tests marked `@pytest.mark.live`, skipped by default. Full guide: `docs/testing.md`.

## Do not touch
`.specify/`, `.claude/skills/` (Spec Kit) · `LICENSE` (Apache-2.0, ADR required) · `docs/vision.md` layer names (ADR required) · `.env`, `secrets/` (never commit).

## Conflict resolution
Rules in this file win over individual specs. A spec conflicting with `docs/vision.md` is a blocker — open an issue before proceeding. When stuck, open a GitHub Discussion rather than guessing.
