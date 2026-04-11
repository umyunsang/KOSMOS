# AGENTS.md — KOSMOS

> Entry point for any AI coding agent (Claude Code, Cursor, Codex, Windsurf, Copilot) working on this repository. This file is imported by `CLAUDE.md`. Keep it under 200 lines.

## What KOSMOS is

KOSMOS is a conversational multi-agent platform that orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. It is an open-source student portfolio project, **not** affiliated with Anthropic, LG AI Research, or the Korean government.

**Canonical vision**: read `docs/vision.md` before making architectural changes. That file is the source of truth for the six-layer design (Query Engine, Tool System, Permission Pipeline, Agent Swarms, Context Assembly, Error Recovery).

**Primary goal**: a working CLI where a citizen can ask natural-language questions (`kosmos ask "..."`) and receive answers backed by live public API data.

## Current working assumptions

These are the current stack choices. They are not frozen — any change requires an ADR under `docs/adr/`, not just a spec.

- **Language**: Python 3.12+. Do not introduce TypeScript, Go, or Rust.
- **Model access**: FriendliAI Serverless OpenAI-compatible endpoint for K-EXAONE. Use the `openai` Python client pointed at `https://api.friendli.ai/serverless/v1`.
- **CLI framework**: `typer` for commands, `rich` for terminal output.
- **HTTP client**: `httpx` (async-first).
- **Validation**: `pydantic` v2 for all tool input and output schemas.
- **Testing**: `pytest` + `pytest-asyncio`. Record fixtures; never hit live public APIs in CI.
- **Packaging**: `uv` + `pyproject.toml`. No `requirements.txt`, no `setup.py`.
- **License**: Apache-2.0.

If a task requires deviating from these, stop and open an issue before changing them.

## Source code language rule

**All source code text must be in English.** This covers comments, docstrings, log messages, error messages, CLI output strings, commit messages, PR titles and bodies, variable and function names.

**Exception**: Korean domain data (real civil-affairs content, legal terms, API response fields as returned by Korean ministries, citizen-facing example dialogues in design docs) is preserved as-is. Do not translate real data.

## Clean-room rule

KOSMOS is inspired by architectural patterns observable in publicly discussed conversational coding agents. The implementation is **independently written in Python** based on publicly observable behavior and third-party architectural commentary.

- Patterns and concepts: fine to borrow
- Line-for-line translation of external code into this repo: forbidden
- Always phrase inspiration as "inspired by, independently reimplemented"
- Do not name specific external reconstruction or decompilation repositories in any file committed to this repo

## Environment variable naming

All environment variables must be prefixed `KOSMOS_`. Examples: `KOSMOS_FRIENDLI_TOKEN`, `KOSMOS_DATA_GO_KR_KEY`, `KOSMOS_LOG_LEVEL`. Document required variables in `.env.example`; never commit `.env`.

## Logging rules

Use stdlib `logging` with module-level loggers (`logger = logging.getLogger(__name__)`). Default level INFO; configurable via `KOSMOS_LOG_LEVEL`. No `print()` outside the CLI output layer (which uses `rich`).

## Spec-driven workflow

This repository uses [GitHub Spec Kit](https://github.com/github/spec-kit). The `.specify/` directory and `.claude/skills/speckit-*` skills are already installed.

For every non-trivial feature:

1. Open a GitHub Issue describing the feature in citizen-facing terms
2. Run `/speckit-specify` — generates `specs/NNN-slug/spec.md`
3. Human reviews and edits `spec.md`
4. Run `/speckit-plan` — generates `specs/NNN-slug/plan.md`
5. Run `/speckit-tasks` — generates `specs/NNN-slug/tasks.md`
6. Run `/speckit-implement` — executes tasks, commits incrementally
7. Open a PR linking the issue (`Closes #N`) and the spec folder

Small fixes (typos, one-line bugs, docs-only changes) skip the spec cycle and go directly to a PR.

## Commit and branch conventions

- **Branches**: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, `refactor/<scope>`, `test/<scope>`, `chore/<scope>`
- **Commits**: Conventional Commits (`feat(tools): add KOROAD adapter`). Keep them atomic.
- **Prefer PRs for code changes.** Direct commits to `main` are acceptable only for `docs:` and `chore:` changes touching no source code.
- **Never** use `--force` on `main`, skip hooks with `--no-verify`, or bypass signing.

## Tool adapter checklist

When adding a new `data.go.kr` API adapter, every PR must include:

- Pydantic input and output models
- Explicit declarations for: authentication requirement, concurrency safety, personal-data flag, cache TTL, rate limit (exact field names are defined by the foundation spec under `specs/`)
- Korean + English discovery hint for future tool search
- One happy-path and one error-path unit test with a recorded fixture
- No hardcoded API keys — read from environment via `KOSMOS_*` variables

## Testing expectations

- Every new module ships with tests in a parallel `tests/` path
- Run `uv run pytest` before every commit
- Once CI is configured, CI must be green before merging a PR
- Integration tests that would hit live public APIs are marked `@pytest.mark.live` and skipped by default

## Never do these

- Never add a top-level directory without updating this file
- Never introduce a dependency without adding it to `pyproject.toml` through a spec-driven PR
- Never commit a binary or file larger than 1 MB without asking
- Never create `requirements.txt`, `setup.py`, or `Pipfile`
- Never write Korean text in code identifiers, comments, or log messages (domain data is the only exception)
- Never call live public APIs from tests that run in CI
- Never bypass `pydantic` validation with `Any` for tool inputs or outputs
- Never read or reference files from external code reconstruction repositories, even as inspiration
- Never manually edit `pyproject.toml` dependency lists outside a spec-driven workflow
- Never commit `.env` or any file under `secrets/`

## Directory layout

```
KOSMOS/
├── AGENTS.md               # you are here
├── CLAUDE.md               # imports AGENTS.md
├── README.md               # user-facing pitch
├── pyproject.toml          # once src/ exists
├── src/kosmos/             # source code
├── tests/                  # pytest
├── specs/                  # spec-driven features (spec.md, plan.md, tasks.md)
├── docs/
│   ├── vision.md           # canonical architectural vision
│   └── adr/                # architecture decision records
├── .specify/               # spec-kit config (do not edit by hand)
├── .claude/                # spec-kit skills (do not edit by hand)
└── .github/                # issue and PR templates, workflows
```

## Do not touch

- `.specify/` and `.claude/skills/` — managed by Spec Kit, regenerated on update
- `LICENSE` — Apache-2.0, do not change without an ADR
- `docs/vision.md` structural changes (layer count, layer names) — require an ADR
- `.env` or any file under `secrets/` — never commit

## Where to find context

- **Project vision**: `docs/vision.md` — read this first
- **README for users**: `README.md`
- **Contribution workflow**: `CONTRIBUTING.md`
- **Design decisions**: `docs/adr/`
- **In-flight feature specs**: `specs/`

## Conflict resolution

- Cross-cutting rules in this file (language, licensing, commit style, negative rules) always win over individual specs
- A spec may introduce new patterns for its own scope; update this file in the same PR if the pattern becomes cross-cutting
- If a spec conflicts with `docs/vision.md`, stop and open an issue before proceeding — the vision is load-bearing

## When you are stuck

Open a GitHub Discussion rather than guessing. If a task is blocked by an unstated decision, ask rather than inventing one.
