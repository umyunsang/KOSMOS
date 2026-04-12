# CI/CD Infrastructure Setup — Leader Prompt

> This prompt is for a Lead agent (Opus) to orchestrate Agent Teams for building KOSMOS's complete CI/CD pipeline.
> Run in a tmux session with Claude Code.

---

## Context

You are the Lead agent for the KOSMOS project. Read `AGENTS.md` and `docs/vision.md` first.

KOSMOS is a Python 3.12+ project using `uv` + `pyproject.toml` (not pip/poetry). The project has documented conventions (`docs/conventions.md`, `docs/testing.md`, `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE.md`) but **zero automation enforcement** — no `.github/workflows/`, no `pyproject.toml`, no branch protection, no pre-commit hooks.

Your mission: build a production-grade CI/CD pipeline that enforces all documented conventions automatically, with special attention to LLM-generated code quality gates.

## Hard constraints (from AGENTS.md)

- All source text in English. Korean only in domain data.
- `KOSMOS_` prefix for all env vars. Never commit `.env` or `secrets/`.
- Pydantic v2 for all tool I/O. Never `Any`.
- `@pytest.mark.live` tests never run in CI.
- `uv` only — never `pip install`, `requirements.txt`, `setup.py`, or `Pipfile`.
- Conventional Commits. Branches: `feat/`, `fix/`, `docs/`, `refactor/`, `test/`, `chore/`.
- Never `--force` push `main`, `--no-verify`, or bypass signing.
- Apache-2.0 license.
- This is NOT a spec-driven feature — it's infrastructure (`chore:`). No spec cycle needed.

## Branch strategy

- Work on branch `chore/cicd-infrastructure`
- All files are new (no merge conflicts expected)
- PR to `main` when complete with title: `chore: establish CI/CD pipeline and branch protection`

## Deliverables — 8 files + GitHub settings

### File 1: `pyproject.toml` — Project configuration (foundation for everything)

```toml
[project]
name = "kosmos"
version = "0.1.0"
description = "Conversational multi-agent platform for Korean public APIs"
readme = "README.md"
license = "Apache-2.0"
requires-python = ">=3.12"
authors = [{ name = "umyunsang" }]

dependencies = [
    "httpx>=0.27",
    "pydantic>=2.0",
    "typer>=0.12",
    "rich>=13.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "pytest-cov>=5.0",
    "pytest-xdist>=3.5",
    "respx>=0.21",
    "hypothesis[pydantic]>=6.100",
    "mypy>=1.10",
    "ruff>=0.5",
    "pre-commit>=3.7",
    "pip-audit>=2.7",
    "vulture>=2.11",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/kosmos"]

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
addopts = "--strict-markers -q --tb=short"
markers = [
    "live: hits real data.go.kr APIs — skipped in CI (deselect with -m 'not live')",
]
filterwarnings = ["error"]

[tool.coverage.run]
source = ["src/kosmos"]
parallel = true
omit = ["tests/*"]

[tool.coverage.report]
fail_under = 80
show_missing = true
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    "raise NotImplementedError",
]

[tool.ruff]
line-length = 100
target-version = "py312"
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "W",    # pycodestyle warnings
    "I",    # isort (import sorting)
    "N",    # pep8-naming
    "UP",   # pyupgrade
    "S",    # flake8-bandit (security)
    "B",    # flake8-bugbear
    "A",    # flake8-builtins
    "C4",   # flake8-comprehensions
    "T20",  # flake8-print (catches print() calls)
    "SIM",  # flake8-simplify
    "C90",  # mccabe complexity
]
ignore = [
    "S101",  # allow assert in tests
]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["S101", "S106"]  # allow assert and hardcoded test passwords
"src/kosmos/cli/**" = ["T20"]  # allow print() in CLI layer only

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.isort]
known-first-party = ["kosmos"]

[tool.ruff.format]
quote-style = "double"

[tool.mypy]
python_version = "3.12"
strict = true
warn_return_any = true
warn_unused_configs = true
plugins = ["pydantic.mypy"]

[tool.mypy.overrides]
module = "tests.*"
disallow_untyped_defs = false

[tool.pydantic-mypy]
init_forbid_extra = true
init_typed = true
warn_required_dynamic_aliases = true

[tool.vulture]
paths = ["src"]
min_confidence = 80

[tool.commitizen]
name = "cz_conventional_commits"
version = "0.1.0"
tag_format = "v$version"
```

### File 2: `.github/workflows/ci.yml` — Core quality gate

Triggers on every PR to `main` and every push to `main`. This is the primary gate.

```yaml
name: CI

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  merge_group:

concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: ${{ github.ref != 'refs/heads/main' }}

jobs:
  lint:
    name: Lint & Type Check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
      - run: uv sync --frozen --all-extras --dev
      - name: Ruff check
        run: uv run ruff check src tests
      - name: Ruff format check
        run: uv run ruff format --check src tests
      - name: Mypy strict
        run: uv run mypy src

  test:
    name: Test (Python ${{ matrix.python-version }})
    needs: lint
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
          cache-dependency-glob: "uv.lock"
          python-version: ${{ matrix.python-version }}
      - run: uv sync --frozen --all-extras --dev
      - name: Run tests with coverage
        run: uv run pytest -n auto --cov=src/kosmos --cov-report=xml -m "not live"
        env:
          KOSMOS_DATA_GO_KR_KEY: "test-placeholder"
          KOSMOS_KOROAD_API_KEY: "test-placeholder"
          KOSMOS_FRIENDLI_TOKEN: "test-placeholder"
      - name: Upload coverage
        if: matrix.python-version == '3.12'
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: coverage.xml

  dead-code:
    name: Dead Code Detection
    needs: lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen --all-extras --dev
      - run: uv run vulture src --min-confidence 80
```

### File 3: `.github/workflows/pr-lint.yml` — PR convention enforcement

```yaml
name: PR Lint

on:
  pull_request:
    types: [opened, edited, reopened, synchronize, ready_for_review]
    branches: [main]

jobs:
  pr-title:
    name: Conventional Commits (PR title)
    runs-on: ubuntu-latest
    steps:
      - uses: amannn/action-semantic-pull-request@v5
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          types: |
            feat
            fix
            docs
            refactor
            test
            chore
            perf
            build
            ci
          requireScope: false
          validateSingleCommit: false
          subjectPattern: ^[a-z].+$
          subjectPatternError: "PR title subject must start with lowercase letter"

  branch-name:
    name: Branch naming convention
    runs-on: ubuntu-latest
    steps:
      - name: Validate branch name
        run: |
          BRANCH="${{ github.head_ref }}"
          PATTERN='^(feat|fix|docs|refactor|test|chore)\/[a-z0-9][a-z0-9\-]*$'
          if ! echo "$BRANCH" | grep -qE "$PATTERN"; then
            echo "::error::Branch name '$BRANCH' does not match pattern: <type>/<kebab-case-scope>"
            echo "Valid prefixes: feat/, fix/, docs/, refactor/, test/, chore/"
            exit 1
          fi
```

### File 4: `.github/workflows/security.yml` — Security scanning

```yaml
name: Security

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]
  schedule:
    - cron: "0 2 * * 1"  # Weekly Monday 2:00 AM UTC

concurrency:
  group: security-${{ github.ref }}
  cancel-in-progress: true

jobs:
  codeql:
    name: CodeQL SAST
    runs-on: ubuntu-latest
    permissions:
      actions: read
      contents: read
      security-events: write
    steps:
      - uses: actions/checkout@v4
      - uses: github/codeql-action/init@v3
        with:
          languages: python
      - uses: github/codeql-action/autobuild@v3
      - uses: github/codeql-action/analyze@v3

  secrets-scan:
    name: Secret Detection
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: trufflesecurity/trufflehog@main
        with:
          path: ./
          base: ${{ github.event.repository.default_branch }}
          extra_args: --only-verified

  dependency-audit:
    name: Dependency Vulnerability Audit
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen --all-extras --dev
      - name: pip-audit
        run: uv run pip-audit

  license-check:
    name: License Compliance (Apache-2.0)
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - run: uv sync --frozen --all-extras --dev
      - run: uv run pip-licenses --format=json --output-file=licenses.json
      - name: Check license compatibility
        run: |
          uv run python -c "
          import json, sys
          BLOCKED = {'GPL-3.0', 'GPL-2.0', 'AGPL-3.0', 'SSPL-1.0', 'BSL-1.1'}
          with open('licenses.json') as f:
              deps = json.load(f)
          violations = [d for d in deps if d.get('License') in BLOCKED]
          if violations:
              for v in violations:
                  print(f'BLOCKED: {v[\"Name\"]} ({v[\"License\"]})', file=sys.stderr)
              sys.exit(1)
          print(f'All {len(deps)} dependencies have compatible licenses.')
          "
```

### File 5: `.github/workflows/claude-review.yml` — Anthropic official Claude Code Action

Uses `anthropics/claude-code-action@v1` (official GA release). Three modes:
1. Automated PR review on every PR
2. Interactive `@claude` in PR/issue comments
3. Dedicated security review via `anthropics/claude-code-security-review`

```yaml
name: Claude Code Review

on:
  pull_request:
    types: [opened, synchronize, ready_for_review]
  pull_request_review_comment:
    types: [created]
  issue_comment:
    types: [created]
  issues:
    types: [opened, assigned]

concurrency:
  group: claude-${{ github.event.pull_request.number || github.event.issue.number }}-${{ github.event_name }}
  cancel-in-progress: false

jobs:
  # ── Automated PR review (runs on every PR) ──────────────────────────
  automated-review:
    name: Claude Automated Review
    if: |
      github.event_name == 'pull_request' &&
      github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      issues: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          use_sticky_comment: true
          prompt: |
            Review this PR against KOSMOS project standards defined in CLAUDE.md and AGENTS.md.

            ## Critical checks (flag as ERROR)
            - Any `Any` type in Pydantic tool I/O models
            - Hardcoded API keys, tokens, or secrets in source code
            - Environment variables not prefixed with `KOSMOS_`
            - `print()` calls outside `src/kosmos/cli/` (must use stdlib `logging`)
            - Live API calls in test files without `@pytest.mark.live` decorator
            - Personal data (PII) in test fixtures (must use synthetic data)
            - Permission pipeline bypass or weakening
            - Cross-layer direct imports violating architecture separation

            ## Important checks (flag as WARNING)
            - Missing type hints on public function signatures
            - New tool adapters without both happy-path and error-path tests
            - Tool adapters missing required fields: requires_auth, is_concurrency_safe,
              is_personal_data, cache_ttl_seconds, rate_limit_per_minute
            - Missing bilingual search_hint (Korean + English) on tool adapters
            - Korean text in comments, logs, error messages, or identifiers
              (Korean is ONLY acceptable in domain data values)
            - Functions with cyclomatic complexity > 10

            ## Style checks (flag as INFO)
            - Import ordering: stdlib → third-party → local
            - Line length > 100 characters
            - Missing docstrings on public APIs

            Post findings as inline review comments on the specific lines.
            Use a summary comment with counts: X errors, Y warnings, Z info.
          claude_args: |
            --model claude-sonnet-4-6
            --max-turns 10

  # ── Interactive @claude in comments ─────────────────────────────────
  interactive:
    name: Claude Interactive
    if: |
      (github.event_name == 'issue_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'pull_request_review_comment' && contains(github.event.comment.body, '@claude')) ||
      (github.event_name == 'issues' && contains(github.event.issue.body, '@claude'))
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 1
      - uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          trigger_phrase: "@claude"
          claude_args: |
            --model claude-sonnet-4-6
            --max-turns 15
            --allowedTools "Bash(uv run pytest:*),Bash(uv run ruff:*),Bash(uv run mypy:*),Bash(git diff:*),Bash(git log:*),Read,Edit,Write,Glob,Grep"
          settings: |
            {
              "env": {
                "KOSMOS_DATA_GO_KR_KEY": "test-placeholder",
                "KOSMOS_KOROAD_API_KEY": "test-placeholder",
                "KOSMOS_FRIENDLI_TOKEN": "test-placeholder"
              }
            }

  # ── Dedicated security review ───────────────────────────────────────
  security-review:
    name: Claude Security Review
    if: |
      github.event_name == 'pull_request' &&
      github.event.pull_request.draft == false
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            Perform a security-focused review of this PR. Check for:
            1. OWASP Top 10 vulnerabilities (injection, XSS, SSRF, etc.)
            2. Hardcoded credentials or API keys (especially KOSMOS_* patterns)
            3. Unsafe deserialization (pickle, yaml.load without SafeLoader)
            4. Command injection via subprocess or os.system
            5. Path traversal in file operations
            6. Insecure HTTP calls (should use httpx with TLS)
            7. PII exposure in logs or error messages
            8. Race conditions in async code
            Tag each finding: CRITICAL / HIGH / MEDIUM / LOW.
          claude_args: |
            --model claude-sonnet-4-6
            --max-turns 8
            --allowedTools "Read,Glob,Grep"
```

### File 6: `.pre-commit-config.yaml` — Local git hooks mirroring CI

```yaml
# Install: uv run pre-commit install && uv run pre-commit install --hook-type commit-msg
# Manual run: uv run pre-commit run --all-files
# Update hooks: uv run pre-commit autoupdate

repos:
  # ── Ruff: lint + format ───────────────────────────────────────────
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.11.5
    hooks:
      - id: ruff
        args: [--fix, --config=pyproject.toml]
        types_or: [python, pyi]
      - id: ruff-format
        args: [--config=pyproject.toml]
        types_or: [python, pyi]

  # ── Mypy: type checking ──────────────────────────────────────────
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.15.0
    hooks:
      - id: mypy
        args: [--config-file=pyproject.toml]
        files: ^src/
        additional_dependencies:
          - "pydantic>=2.0"
          - "httpx>=0.27"
          - "typer>=0.12"

  # ── uv lock consistency ──────────────────────────────────────────
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.7.12
    hooks:
      - id: uv-lock

  # ── Conventional Commits ─────────────────────────────────────────
  - repo: https://github.com/commitizen-tools/commitizen
    rev: v4.6.0
    hooks:
      - id: commitizen
        stages: [commit-msg]

  # ── Secret detection ─────────────────────────────────────────────
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.24.0
    hooks:
      - id: gitleaks

  # ── General hygiene ──────────────────────────────────────────────
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-merge-conflict
      - id: check-added-large-files
        args: ["--maxkb=500"]
      - id: no-commit-to-branch
        args: ["--branch", "main"]
```

### File 7: `.coderabbit.yaml` — AI-powered PR review (CodeRabbit)

```yaml
language: "en-US"
tone_instructions: "Be concise and direct. Flag KOSMOS convention violations as high priority."
early_access: false

reviews:
  profile: "assertive"
  request_changes_workflow: false
  high_level_summary: true
  high_level_summary_instructions: |
    Summarize: (1) what changed, (2) which KOSMOS layers are affected
    (query engine / tools / permissions / agents / context / error recovery),
    (3) any breaking changes to interfaces.
  poem: false
  review_status: true
  collapse_walkthrough: true
  sequence_diagrams: true

  instructions: |
    This is KOSMOS, a Korean civil-affairs AI agent platform.
    Rules from AGENTS.md and docs/conventions.md:
    - All source code text in English. Korean ONLY in domain data values.
    - All env vars prefixed KOSMOS_. No hardcoded keys.
    - stdlib logging only. No print() outside CLI layer.
    - Pydantic v2. Never bare Any in tool I/O.
    - Line length 100. Google-style docstrings on public APIs.
    - Tool adapters must set: requires_auth, is_concurrency_safe,
      is_personal_data, cache_ttl_seconds, rate_limit_per_minute.
    - Tests: happy-path + error-path minimum per adapter.
    - Conventional Commits format.

  path_instructions:
    - path: "src/kosmos/tools/**"
      instructions: |
        Tool adapter review: verify Pydantic v2 I/O (no Any), all 5 required
        fields set, bilingual search_hint, fail-closed defaults.
        Check for matching test file in tests/tools/.
    - path: "src/kosmos/query_engine/**"
      instructions: |
        Query engine: check state machine completeness, cache invalidation.
        No direct imports from tools/ or permissions/ (layer separation).
    - path: "src/kosmos/permissions/**"
      instructions: |
        Permission pipeline: the 7-step gauntlet must stay intact.
        Any bypass weakening is CRITICAL severity.
    - path: "src/kosmos/agents/**"
      instructions: |
        Agent review: verify handoff contracts.
        Agents must never call data.go.kr directly — go through tools layer.
    - path: "tests/**"
      instructions: |
        Tests: @pytest.mark.live on live API tests.
        No real PII in fixtures — synthetic data only.
        No actual API key values anywhere.
    - path: ".github/workflows/**"
      instructions: |
        CI: secrets via ${{ secrets.* }} only. No hardcoded values.
        Live tests excluded from CI runs.

  path_filters:
    - "!uv.lock"
    - "!**/__pycache__/**"
    - "!tests/fixtures/**/*.json"

  auto_review:
    enabled: true
    auto_incremental_review: true
    drafts: false
    ignore_title_keywords: ["WIP", "DO NOT MERGE", "DRAFT"]
    base_branches: ["main"]

  tools:
    ruff:
      enabled: true
    yamllint:
      enabled: true
    actionlint:
      enabled: true
    gitleaks:
      enabled: true
    semgrep:
      enabled: true

knowledge_base:
  code_guidelines:
    enabled: true
    filePatterns:
      - "CLAUDE.md"
      - "AGENTS.md"
      - "docs/conventions.md"
      - "docs/testing.md"
      - "CONTRIBUTING.md"

chat:
  auto_reply: true
```

### File 8: `.github/dependabot.yml` — Automated dependency updates

```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels: ["chore", "dependencies"]
    commit-message:
      prefix: "chore(deps)"
    open-pull-requests-limit: 5

  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
      day: "monday"
    labels: ["chore", "ci"]
    commit-message:
      prefix: "ci(deps)"
    open-pull-requests-limit: 3
```

### GitHub Settings (via `gh` CLI — Lead executes directly)

After all files are committed, configure branch protection:

```bash
# 1. Branch protection for main
gh api repos/kosmos-kr/KOSMOS/branches/main/protection \
  --method PUT \
  --input - <<'EOF'
{
  "required_status_checks": {
    "strict": true,
    "contexts": [
      "Lint & Type Check",
      "Test (Python 3.12)",
      "Test (Python 3.13)",
      "Conventional Commits (PR title)",
      "Branch naming convention",
      "CodeQL SAST",
      "Secret Detection",
      "Dependency Vulnerability Audit"
    ]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true
  },
  "restrictions": null,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "required_linear_history": false,
  "required_conversation_resolution": true
}
EOF

# 2. Register ANTHROPIC_API_KEY secret (user must provide the value)
# gh secret set ANTHROPIC_API_KEY --body "<key>"
echo "ACTION REQUIRED: Register ANTHROPIC_API_KEY as a GitHub secret for Claude Code Action."
echo "Run: gh secret set ANTHROPIC_API_KEY"
```

## Agent Teams task decomposition

Split into 4 parallel Teammates (Sonnet, isolated worktrees):

| # | Teammate | Files | Dependencies |
|---|----------|-------|-------------|
| T1 | Backend Architect | `pyproject.toml` | None — start first |
| T2 | DevOps Automator | `.github/workflows/ci.yml`, `.github/workflows/pr-lint.yml` | T1 (needs pyproject.toml for tool configs) |
| T3 | Security Engineer | `.github/workflows/security.yml`, `.github/workflows/claude-review.yml` | T1 |
| T4 | DevOps Automator | `.pre-commit-config.yaml`, `.coderabbit.yaml`, `.github/dependabot.yml` | T1 |

**Execution order:**
1. T1 creates `pyproject.toml` first (all others depend on it)
2. T2, T3, T4 run in parallel after T1 completes
3. Lead merges all worktrees, resolves conflicts, runs `uv sync`
4. Lead configures branch protection via `gh api`
5. Lead creates PR and monitors CI checks

## Verification checklist

Before creating the PR, Lead must verify:

- [ ] `uv sync` succeeds with `pyproject.toml`
- [ ] `uv run ruff check src tests` passes (or no src/tests yet — expected)
- [ ] `uv run mypy src` passes (or no src yet — expected)
- [ ] All YAML files are valid (`python -c "import yaml; yaml.safe_load(open(f))"`)
- [ ] No secrets or API keys in any committed file
- [ ] Workflow files reference only `${{ secrets.* }}` for sensitive values
- [ ] `.pre-commit-config.yaml` hook versions are current (check repos)
- [ ] `.coderabbit.yaml` path_instructions match KOSMOS directory layout
- [ ] `dependabot.yml` uses correct package ecosystem for uv
- [ ] Branch protection API call is ready (but NOT executed until PR is merged)

## Post-merge actions (Lead executes after PR merge)

1. Configure branch protection via the `gh api` command above
2. Remind user to register `ANTHROPIC_API_KEY` as GitHub secret
3. Run `uv run pre-commit install && uv run pre-commit install --hook-type commit-msg` locally
4. Verify branch protection is active: `gh api repos/kosmos-kr/KOSMOS/branches/main/protection`

## Future enhancements (Phase 2+ CI/CD)

These are NOT in scope for this PR but should be tracked as follow-up issues:

- **Mutation testing**: `mutmut` as nightly scheduled workflow
- **Contract testing**: `schemathesis` for data.go.kr API schema compliance
- **SBOM generation**: CycloneDX as release artifact
- **Semantic release**: `python-semantic-release` for automated versioning + CHANGELOG
- **PyPI trusted publishing**: `uv publish` with OIDC when ready for distribution
- **Coverage trends**: Codecov integration with PR comments
- **Merge queue**: Enable GitHub merge queue when PR volume increases
- **LLM output testing**: `promptfoo` or `deepeval` for prompt regression testing
- **Property-based testing**: `hypothesis` integration for Pydantic model fuzzing
- **Snapshot testing**: `syrupy` for API response snapshots
