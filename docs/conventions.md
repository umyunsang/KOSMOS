# Conventions

Detailed development conventions for KOSMOS. `AGENTS.md` summarizes the cross-cutting rules; this file is the long form.

## Source code language

All source code text must be in English: comments, docstrings, log messages, error messages, CLI output strings, commit messages, PR titles and bodies, variable and function names.

**Exception**: Korean domain data — real civil-affairs content, legal terms, `data.go.kr` response fields as returned by Korean ministries, citizen-facing example dialogues in design docs — is preserved as-is. Do not translate real data.

Rationale: keeps the project legible to international contributors while respecting that the target domain is Korean.

## Environment variables

All environment variables must be prefixed `KOSMOS_`.

| Variable | Purpose |
|---|---|
| `KOSMOS_FRIENDLI_TOKEN` | FriendliAI Serverless API token |
| `KOSMOS_DATA_GO_KR_KEY` | data.go.kr API key |
| `KOSMOS_LOG_LEVEL` | stdlib logging level (default `INFO`) |

- Document every required variable in `.env.example`
- Never commit `.env` or any file under `secrets/`
- Never hardcode keys in source, tests, or fixtures

## Logging

- Use stdlib `logging` with module-level loggers: `logger = logging.getLogger(__name__)`
- Default level `INFO`, configurable via `KOSMOS_LOG_LEVEL`
- No `print()` outside the CLI output layer (which uses `rich`)
- Never log personal data, API keys, or full citizen profiles — log IDs and categories only

## Commit messages

KOSMOS uses [Conventional Commits](https://www.conventionalcommits.org/).

Format: `<type>(<scope>): <subject>`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `build`, `ci`

Examples:
```
feat(tools): add KOROAD traffic accident adapter
fix(query-engine): prevent cache invalidation on tool result push
docs(vision): clarify 7-step permission gauntlet
chore(deps): bump httpx to 0.28
```

Rules:
- Keep commits atomic — one logical change per commit
- Subject in imperative mood, under 72 characters
- Body explains *why*, not *what* — the diff shows *what*
- Squash noise before opening a PR

## Branches

| Prefix | Purpose |
|---|---|
| `feat/<scope>` | new feature |
| `fix/<scope>` | bug fix |
| `docs/<scope>` | documentation only |
| `refactor/<scope>` | internal restructuring |
| `test/<scope>` | tests only |
| `chore/<scope>` | tooling, CI, dependencies |

Examples: `feat/koroad-adapter`, `fix/cache-invalidation`, `docs/vision-layer-3`.

## Pull requests

- Prefer PRs for code changes. Direct commits to `main` are acceptable only for `docs:` and `chore:` changes touching no source code
- Keep PRs focused — a 2,000-line PR touching five layers is hard to review; split it
- Link the issue with `Closes #N`
- Fill out the PR template completely
- Ensure CI is green before requesting review
- Do not force-push after review starts unless asked

## Git safety

Never:
- `git push --force` on `main`
- `git commit --no-verify` (skip hooks)
- `git commit --no-gpg-sign` (bypass signing)
- `git reset --hard` on published commits
- Amend commits that are already pushed to `main`

## Code style

- **Python**: PEP 8, type-hint public APIs, `ruff` + `mypy` when configured
- **Imports**: stdlib → third-party → local, separated by blank lines
- **Line length**: 100 characters (ruff default)
- **Docstrings**: Google style, one-liner for trivial functions, full form for public APIs
- **Pydantic**: v2 only, never `Any` for tool inputs or outputs
