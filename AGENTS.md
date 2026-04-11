# AGENTS.md — KOSMOS

> This file is the entry point for any AI coding agent (Claude Code, Cursor, Codex, Windsurf, Copilot) working on this repository. Read it every session before touching code. If you are Claude Code, this file is also imported by `CLAUDE.md`.

## What KOSMOS is

KOSMOS is a conversational multi-agent platform that orchestrates Korean public APIs from `data.go.kr` through a Claude Code-style tool loop, powered by LG AI Research's K-EXAONE. It is an open-source student portfolio project, **not** affiliated with Anthropic, LG AI Research, or the Korean government.

Primary goal: a working CLI where a citizen can ask natural-language questions (`kosmos ask "..."`) and receive answers backed by live public API data.

## Stack decisions (locked)

- **Language**: Python 3.12+. Do not introduce TypeScript, Go, or Rust.
- **Model access**: FriendliAI Serverless OpenAI-compatible endpoint for K-EXAONE. Use the `openai` Python client pointed at `https://api.friendli.ai/serverless/v1`.
- **CLI framework**: `typer` for commands, `rich` for terminal output.
- **HTTP client**: `httpx` (async-first).
- **Validation**: `pydantic` v2 for all tool input and output schemas.
- **Testing**: `pytest` + `pytest-asyncio`. Record fixtures; never hit live public APIs in CI.
- **Packaging**: `uv` + `pyproject.toml`. No `requirements.txt`, no `setup.py`.
- **License**: Apache-2.0.

If a task requires deviating from this stack, stop and ask the maintainer in an issue before changing it.

## Source code language rule

**All source code text must be in English.** This covers comments, docstrings, log messages, error messages, CLI output strings, commit messages, PR titles and bodies, variable and function names.

**Exception**: Korean domain data (real civil-affairs content, legal terms, API response fields as returned by Korean ministries) is preserved as-is. Do not translate real data.

## Clean-room rule (important)

KOSMOS is inspired by Claude Code architectural patterns, but the implementation must be **independently written in Python**. Never copy code verbatim from any Claude Code sourcemap reconstruction, decompilation, or derivative. Patterns and concepts are fine; line-for-line translation is not.

When an ADR or spec cites Claude Code as inspiration, phrase it as "inspired by, independently reimplemented." Do not paste TypeScript from external reconstruction repositories into this codebase under any circumstance.

## Spec-driven workflow (use this every feature)

This repository uses [GitHub Spec Kit](https://github.com/github/spec-kit). The `.specify/` directory and `.claude/skills/speckit-*` skills are already installed.

For every non-trivial feature, follow this cycle:

1. Open a GitHub Issue describing the feature in citizen-facing terms
2. Run `/speckit-specify` — generates `specs/NNN-slug/spec.md`
3. Human reviews and edits `spec.md`
4. Run `/speckit-plan` — generates `specs/NNN-slug/plan.md`
5. Run `/speckit-tasks` — generates `specs/NNN-slug/tasks.md`
6. Run `/speckit-implement` — executes tasks, commits incrementally
7. Open a PR linking the issue (`Closes #N`) and the spec folder

Small fixes (typos, one-line bugs) skip the spec cycle and go directly to a PR.

## Commit and branch conventions

- **Branches**: `feat/<scope>`, `fix/<scope>`, `docs/<scope>`, `refactor/<scope>`, `test/<scope>`, `chore/<scope>`
- **Commits**: Conventional Commits (`feat(tools): add KOROAD adapter`). Keep them atomic.
- **Never** push directly to `main`. Always through a PR, even for solo work.
- **Never** use `--no-verify`, `--force` on `main`, or skip hooks.

## Tool adapter checklist

When adding a new `data.go.kr` API adapter, every PR must include:

- Pydantic input and output models
- Explicit values for `requires_auth`, `is_concurrency_safe`, `is_personal_data`, `cache_ttl_seconds`, `rate_limit_per_minute`
- Korean + English `search_hint` for future tool discovery
- One happy-path and one error-path unit test with a recorded fixture
- No hardcoded API keys — read from environment via `.env`

## Testing expectations

- Every new module ships with tests in a parallel `tests/` path
- Run `uv run pytest` before every commit
- CI must be green before merging a PR
- Integration tests that would hit live public APIs are marked `@pytest.mark.live` and skipped in CI

## Directory layout

```
KOSMOS/
├── AGENTS.md               # you are here
├── CLAUDE.md               # imports AGENTS.md
├── README.md               # user-facing
├── pyproject.toml          # once src/ exists
├── src/kosmos/             # source code
├── tests/                  # pytest
├── specs/                  # spec-driven features (spec.md, plan.md, tasks.md)
├── docs/
│   └── adr/                # architecture decision records
├── .specify/               # spec-kit config (do not edit by hand)
├── .claude/                # spec-kit skills (do not edit by hand)
└── .github/                # issue and PR templates, workflows
```

## Do not touch

- `.specify/` and `.claude/skills/` — managed by Spec Kit, regenerated on update
- `LICENSE` — Apache-2.0, do not change without an ADR
- `.env` or any file under `secrets/` — never commit

## Where to find context

- **Project vision**: `README.md`
- **Contribution workflow**: `CONTRIBUTING.md`
- **Design decisions**: `docs/adr/`
- **In-flight feature specs**: `specs/`
- **Citizen-facing docs (future)**: `docs/` (to be created)

## When you are stuck

If a task is ambiguous, open a GitHub Discussion rather than guessing. If a spec conflicts with this file, this file wins — update the spec to match, not the other way around.
