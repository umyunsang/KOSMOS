# AGENTS.md — KOSMOS

> Entry point for AI coding agents. Imported by `CLAUDE.md`. Keep under 120 lines. Long-form details live under `docs/`.

## What KOSMOS is

A conversational multi-agent platform that **migrates the Claude Code harness** (tool loop, permission gauntlet, context assembly, TUI) from the developer domain to the Korean public-service domain. It orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. Student portfolio project. Not affiliated with Anthropic, LG AI Research, or the Korean government.

**Canonical sources** (cite both in every spec and PR):
- `docs/vision.md` — thesis + six-layer design. Claude Code is the first reference for any unclear design decision.
- `docs/requirements/kosmos-migration-tree.md` — L1 pillars A/B/C · UI L2 decisions · brand · P0–P6 phase sequencing. **Approved 2026-04-24.**

## L1 pillars (canonical)

- **L1-A LLM Harness** — Single-fixed provider `FriendliAI Serverless + K-EXAONE` (`LGAI-EXAONE/EXAONE-4.0-32B`). CC agentic loop preserved 1:1. Native EXAONE function calling. `prompts/system_v1.md` + compaction + prompt cache. Sessions in `~/.kosmos/memdir/user/sessions/` JSONL. 4-tier OTEL, zero external egress.
- **L1-B Tool System** — `Tool.ts` rewritten, registered on both TS and Python. Live / Mock 2-tier with 3-layer permissions + Spec 033. Discovery via BM25 + dense `lookup`. Composite tools removed. Korean-primary 5-tier plugin DX with PIPA trustee responsibility explicit.
- **L1-C Main-Verb Abstraction** — Four reserved primitives (`lookup · submit · verify · subscribe`) with shared `PrimitiveInput/Output` envelope. System prompt exposes primitive signatures only; BM25 surfaces adapters dynamically. Permissions live at the adapter layer only.

## Execution phases

P0 Baseline Runnable (#1632 merged) → P1 Dead-code + P2 Anthropic→FriendliAI (#1633 in progress) → P3 Tool-system wiring → P4 UI L2 → P5 Plugin DX → P6 Docs + smoke. Phase sequencing is canonical; spec PRs cite their phase.

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

**Issue tracking = GraphQL only.** Any enumeration of open epics, dependency/sub-issue graph walks, state-transition checks, or tracking-driven recommendations MUST go through `gh api graphql` with explicit field selection of the Sub-Issues API v2 connections (`issue.subIssues` / `issue.parent`, plus `pageInfo.hasNextPage` pagination). Do NOT use `trackedIssues` / `trackedInIssues` — those are the legacy body-mention task-list connection and return empty for issues linked via the "Convert to sub-issue" UI or `addSubIssue` mutation. `gh issue list/view` and REST `repos/.../issues` drop pages, miss Sub-Issues API edges, and hide projectV2 status — they are allowed ONLY for human-readable one-off glances, never as the basis for a tracking claim.

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

## Code review

After every push, read inline review comments left by **Codex** (`chatgpt-codex-connector[bot]`) on the PR and address them:

```bash
gh api repos/umyunsang/KOSMOS/pulls/<N>/comments \
  --jq '.[] | select(.user.login == "chatgpt-codex-connector[bot]") | "\(.path):\(.line) \(.body)"'
```

Codex flags issues with severity badges (P1/P2/P3). Fix or defer each with a reply. Codex auto-reviews on every push — no manual trigger needed.

## New tool adapter

Pydantic v2 I/O · fail-closed defaults · Korean + English `search_hint` · recorded fixture · happy-path + error-path test · no hardcoded keys. Full checklist: `docs/tool-adapters.md`.

**External plugin contributors** (kosmos-plugin-store/`<repo>`): start at [`docs/plugins/quickstart.ko.md`](./docs/plugins/quickstart.ko.md). 50-item validation workflow (Q1-Q10) enforces all rules; PIPA §26 trustee acknowledgment SHA-256 must match canonical hash in [`docs/plugins/security-review.md`](./docs/plugins/security-review.md) when `processes_pii: true`.

## Testing
`uv run pytest` before every commit. Live-API tests marked `@pytest.mark.live`, skipped by default. Full guide: `docs/testing.md`.

## TUI verification (LLM-readable smoke)
"작동 확인" / "정상 동작" / "검증" requests on TUI changes MUST run interactively under PTY — never code-grep alone (memory `feedback_runtime_verification`). Use a layered approach: (1) **stdio JSONL probe** bypasses the TUI for backend baseline, (2) **expect/script/asciinema** captures the full pty session as a text log LLMs can grep (memory `feedback_vhs_tui_smoke`), (3) **vhs `.tape`** produces the gif/mp4 for human visual review only (binary, not LLM-readable). Mismatches between layers identify which layer regressed. Full methodology + recipes: [`docs/testing.md § TUI verification methodology`](./docs/testing.md#tui-verification-methodology).

## Do not touch
`.specify/`, `.claude/skills/` (Spec Kit) · `LICENSE` (Apache-2.0, ADR required) · `docs/vision.md` layer names (ADR required) · `.env`, `secrets/` (never commit).

## Conflict resolution
Rules in this file win over individual specs. A spec conflicting with `docs/vision.md` is a blocker — open an issue before proceeding. When stuck, open a GitHub Discussion rather than guessing.
