# AGENTS.md — KOSMOS

> Entry point for AI coding agents. Imported by `CLAUDE.md`. Keep under 100 lines. Long-form details live under `docs/`.

## What KOSMOS is

A conversational multi-agent platform that orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. Student portfolio project. Not affiliated with Anthropic, LG AI Research, or the Korean government.

**Canonical vision**: `docs/vision.md` — six-layer design. Read before any architectural change.

## Stack (current working assumptions)

Python 3.12+ · FriendliAI Serverless (OpenAI-compatible) for K-EXAONE · `typer` + `rich` CLI · `httpx` (async) · `pydantic` v2 · `pytest` + `pytest-asyncio` · `uv` + `pyproject.toml` · Apache-2.0.

Changing any of these requires an ADR under `docs/adr/`.

## Hard rules (never violate)

- All source text in English — comments, logs, errors, CLI output, identifiers. Korean domain data is the only exception. (See `docs/conventions.md`.)
- All environment variables prefixed `KOSMOS_`. Never commit `.env` or `secrets/`.
- Stdlib `logging` only; no `print()` outside the CLI output layer.
- Pydantic v2 for all tool inputs and outputs. Never `Any`.
- Clean-room rule: borrow architectural patterns from publicly discussed conversational coding agents, never line-for-line code. Do not name specific external reconstruction or decompilation repositories in any committed file.
- Never call live `data.go.kr` APIs from CI tests.
- Never add a dependency outside a spec-driven PR.
- Never `--force` push `main`, `--no-verify`, or bypass signing.
- Never write Korean in code identifiers, comments, or log messages.
- Never create `requirements.txt`, `setup.py`, or `Pipfile`.
- Never commit a file larger than 1 MB without asking.
- Never introduce TypeScript, Go, or Rust.

## Spec-driven workflow

Non-trivial features use [GitHub Spec Kit](https://github.com/github/spec-kit):

1. Open a GitHub Issue in citizen-facing terms
2. `/speckit-specify` → `specs/NNN-slug/spec.md`
3. Human review
4. `/speckit-plan` → `plan.md`
5. `/speckit-tasks` → `tasks.md`
6. `/speckit-implement` → incremental commits
7. Open PR with `Closes #N`

Small fixes (typos, one-line bugs, docs-only) skip the cycle.

## Commits, branches, PRs

Conventional Commits. Branches `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`. Prefer PRs for code; direct commits to `main` allowed only for `docs:` and `chore:` changes touching no source. Full details: `docs/conventions.md`.

## New tool adapter

Pydantic v2 I/O · fail-closed defaults · Korean + English `search_hint` · recorded fixture · happy-path + error-path test · no hardcoded keys. Full checklist: `docs/tool-adapters.md`.

## Testing

`uv run pytest` before every commit. Live-API tests marked `@pytest.mark.live` and skipped by default. Full guide: `docs/testing.md`.

## Directory layout

```
KOSMOS/
├── AGENTS.md, CLAUDE.md, README.md
├── pyproject.toml          # once src/ exists
├── src/kosmos/             # source
├── tests/                  # pytest
├── specs/NNN-slug/         # spec-driven features
├── docs/
│   ├── vision.md           # canonical architecture (read first)
│   ├── conventions.md      # language, env vars, commits, branches
│   ├── tool-adapters.md    # adapter checklist, fixtures
│   ├── testing.md          # pytest guide
│   └── adr/                # architecture decisions
├── .specify/, .claude/     # Spec Kit — do not hand-edit
└── .github/
```

## Do not touch

- `.specify/`, `.claude/skills/` — managed by Spec Kit
- `LICENSE` — Apache-2.0, change requires ADR
- `docs/vision.md` layer count/names — change requires ADR
- `.env`, `secrets/` — never commit

## Conflict resolution

Cross-cutting rules in this file win over individual specs. A spec conflicting with `docs/vision.md` is a blocker — open an issue before proceeding. The vision is load-bearing.

When stuck, open a GitHub Discussion rather than guessing.
