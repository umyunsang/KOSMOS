# Contributing to KOSMOS

First, thank you for considering a contribution. KOSMOS is an early-stage academic R&D project exploring how Claude Code-style agent architectures can be transferred into the public-service domain, powered by K-EXAONE. Every issue, design discussion, and pull request helps shape the direction.

This guide covers how to get involved, the standards we hold, and the workflow we expect. Read it once before your first contribution — it will save both of us time.

## Ways to contribute

- **File an issue** — bug reports, architecture questions, API integration requests, documentation gaps
- **Join a discussion** — design debates, ministry-agent scope, model selection, permission pipeline trade-offs
- **Write code** — tool adapters for `data.go.kr` APIs, agent implementations, query engine internals, tests
- **Improve docs** — architecture notes, tutorials, translation (Korean ↔ English), diagrams
- **Share experiments** — benchmark results, ablation studies, failure cases on real civil-affairs scenarios

If you are unsure whether an idea fits, **open a discussion before coding**. We would rather shape scope early than reject a finished PR.

## Development workflow

1. **Fork** the repository and create a feature branch from `main`:
   ```bash
   git checkout -b feat/traffic-accident-adapter
   ```
2. **Follow the branch naming convention**:
   - `feat/<scope>` — new feature
   - `fix/<scope>` — bug fix
   - `docs/<scope>` — documentation only
   - `refactor/<scope>` — internal restructuring
   - `test/<scope>` — tests only
   - `chore/<scope>` — tooling, CI, dependencies
3. **Write commits in Conventional Commits style**:
   ```
   feat(tools): add KOROAD traffic accident adapter
   fix(query-engine): prevent cache invalidation on tool result push
   docs(architecture): clarify 7-step permission gauntlet
   ```
4. **Keep commits atomic**. One logical change per commit. Squash noise before opening a PR.
5. **Open a pull request** against `main` using the PR template. Link the related issue.

## Source code language rule

**All source code text must be written in English.** This includes:

- Code comments and docstrings
- Log messages, error messages, CLI output
- Commit messages, PR titles and bodies
- Variable, function, class, and file names

**Exception**: Korean domain data (actual civil-affairs content, legal terms, API response fields from Korean ministries) is preserved as-is. Do not translate real data.

This rule keeps the project legible to international contributors and reviewers while respecting that the target domain is Korean.

## Coding standards

Coding standards will formalize as the first implementation lands. Until then:

- **Python**: follow PEP 8, type-hint public APIs, prefer `ruff` and `mypy` settings when added
- **TypeScript**: strict mode, no `any` without justification, ESM modules
- **Tests**: every new tool adapter ships with at least one happy-path test and one error-path test
- **Secrets**: never commit API keys, tokens, or personal data. Use `.env` (already gitignored) and document required variables in `.env.example`

## Tool adapter checklist

When adding a new `data.go.kr` API adapter, the PR must include:

- [ ] JSON Schema for input and output (Zod / Pydantic equivalent is acceptable)
- [ ] `requiresAuth`, `isConcurrencySafe`, `isPersonalData`, `cacheTTL`, `rateLimitPerMinute` explicitly set (no defaults assumed)
- [ ] A `searchHint` field with Korean + English keywords for `ToolSearch` discovery
- [ ] Unit test with a recorded fixture response (do not hit live endpoints in CI)
- [ ] Entry in `docs/tools/<provider>.md` documenting the ministry, endpoint, rate limit, and known quirks
- [ ] No hardcoded credentials — read from environment

## Pull request expectations

- Keep PRs focused. A 2,000-line PR touching five layers is very hard to review; split it.
- Fill out the PR template completely. "What, why, how to test" is not optional.
- Ensure CI is green before requesting review. If CI does not exist yet for your area, say so in the PR body.
- Expect review comments. This is a research project and design decisions are debated openly.
- After approval, the maintainer will merge. Do not force-push after review starts unless asked.

## Reporting security issues

Do **not** open a public issue for security vulnerabilities. See [SECURITY.md](SECURITY.md) for the disclosure process.

## Code of Conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). By participating you agree to uphold it. Harassment, discrimination, and bad-faith engagement are not tolerated.

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0, the same license that covers the project. See [LICENSE](LICENSE).

## Questions

Open a GitHub Discussion or file an issue tagged `question`. The maintainer will respond as time allows — this is a student-led research project, so please be patient.
