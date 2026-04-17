# Phase 0 Research — Secrets & Config (Epic #468)

**Date**: 2026-04-17 · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Reference authority per AGENTS.md Spec-driven workflow step 3: `.specify/memory/constitution.md` + `docs/vision.md § Reference materials` + Claude Code thesis anchor. Every decision below maps to a concrete reference.

## Deferred-item validation (Constitution Principle VI gate)

Scanned `spec.md §Scope Boundaries & Deferred Items`:

| Deferred Item | Target Epic | Tracking | Status |
|---------------|-------------|----------|--------|
| LiteLLM master-key + daily budgets | #465 | `#465` | ✅ open Epic |
| `LANGFUSE_*` + `KOSMOS_OTEL_ENDPOINT` code wiring | #501 | `#501` | ✅ open Epic (this Epic catalogues names only) |
| `docker.yml` / `shadow-eval.yml` Infisical migration | #467 | `#467` | ✅ open Epic |
| Secret rotation automation (scheduled) | `NEEDS TRACKING` | post-#468 | ✅ flagged for `/speckit-taskstoissues` |
| Multi-tenant Infisical workspace split | `NEEDS TRACKING` | post-MVP | ✅ flagged |
| Hardware-token MFA enforcement | `NEEDS TRACKING` | post-MVP | ✅ flagged |
| Legacy `KOSMOS_API_KEY` full removal (read-path) | `NEEDS TRACKING` | post-#468 | ✅ flagged |

Text-scan for stray "future epic" / "Phase 2" / "v2" / "separate epic" / "out of scope for v1" phrases: every match in `spec.md` corresponds to a row above. **Principle VI: PASS.**

## R1 — Guard invocation site in `src/kosmos/cli/app.py`

**Decision**: Insert guard call **between** `load_repo_dotenv()` and `setup_tracing()` in `main()` (current lines 245–249).

**Rationale**:
- `_dotenv.py:40` enforces "shell wins over `.env`" (if var is already set in `os.environ`, skip). The guard's validation must therefore run *after* `load_repo_dotenv()` so it observes the final merged environment.
- `setup_tracing()` (OTel SDK init) opens external I/O (OTLP exporter resolution, if enabled). Per Principle II, validation must happen *before* any network-bound subsystem spins up — so the guard runs *before* `setup_tracing()`.
- Claude Code reference: the permission-pipeline runs *before* the tool loop fetches network resources. Mirror that discipline at the startup phase.

**Alternatives considered**:
- **Before `load_repo_dotenv()`**: rejected — would miss `.env`-supplied values, producing false "missing" errors.
- **Inside `_dotenv.load_repo_dotenv()`**: rejected — couples two orthogonal concerns; violates single-responsibility; breaks stdlib-only discipline of `_dotenv.py`.
- **As a pytest fixture / plugin**: rejected — test-time validation doesn't protect production CLI start-up (the #458 regression scenario).

**Reference**: `src/kosmos/_dotenv.py:40`; `src/kosmos/cli/app.py:245–249`; Claude Code `permissions` module (`src/kosmos/permissions/`).

## R2 — Source of truth for required variable names

**Decision**: In-code Python list (`_REQUIRED_VARS: list[RequiredVar]`) inside `src/kosmos/config/guard.py`. Registry markdown (`docs/configuration.md`) is a human mirror; the code is machine truth. `scripts/audit-env-registry.py` reconciles the two, **failing CI** on drift.

**Rationale**:
- Code is executable documentation — if the guard reads a Markdown table at runtime, we introduce a parser dependency and a startup failure mode for malformed docs. Neither is acceptable.
- FR-008 demands a single in-process data structure; the audit script covers the human-doc side separately (FR-020).
- Mirrors pydantic-settings idiom: configuration *schema* lives in Python classes, not external files.

**Alternatives considered**:
- **Derive from `KosmosSettings` class introspection**: rejected — `LLMClientConfig` and `CLIConfig` live in separate modules with different prefixes; a single introspection pass is brittle. Explicit list is clearer.
- **YAML/TOML registry file + runtime parse**: rejected — adds parser dep, opens door to malformed-doc start-up failures, violates Principle III (library must be pure-stdlib for startup path).

**Reference**: 12-Factor App §III "Config"; Doppler/Infisical schema patterns (registry is a projection of code truth).

## R3 — Activation flag semantics (`KOSMOS_ENV`)

**Decision**: `KOSMOS_ENV ∈ {dev, ci, prod}`. Unknown / unset → treat as `dev`. The flag gates only *conditional-required* promotion (e.g., `LANGFUSE_*` becomes required when `KOSMOS_ENV=prod`), never the shape of config.

**Rationale**:
- 12-Factor App §III: "strict separation of config from code" — but *not* combinatorial environment config files. A flag that gates *required-ness* (not shape) preserves this.
- Dev experience: a new contributor cloning the repo with no `KOSMOS_ENV` set gets the most permissive mode (dev), so the guard only yells about truly required vars.
- Fail-closed: `prod` is most strict; unknown values *must not* silently enable prod behaviour, hence fall-through to `dev`.

**Alternatives considered**:
- **`NODE_ENV`-style three values with no fall-through** (reject on unknown): rejected — too rigid; a typo shouldn't crash CLI in dev.
- **Boolean `KOSMOS_STRICT`**: rejected — loses the `ci` tier, which has different truths (synthetic tokens allowed) than `prod`.
- **Infer from CI env vars (`GITHUB_ACTIONS=true`)**: rejected — tight coupling to one CI vendor; violates 12-Factor.

**Reference**: 12-Factor App §III; Claude Code's `--permission-mode` tri-value flag (ask/edit/danger) as structural analogue.

## R4 — Infisical OIDC trust policy pinning

**Decision**: Pin `repository=umyunsang/KOSMOS` + `workflow=.github/workflows/ci.yml` + `actor_type=User`. **Do NOT pin `ref`** — PR CI requires arbitrary-branch executions.

**Rationale**:
- GitHub OIDC token claims: `repository`, `workflow`, `ref`, `actor`, `environment`, `job_workflow_ref`. Pinning `repository` and `workflow` bounds the attack surface to this specific workflow in this specific repo.
- Leaving `ref` unpinned means a contributor's PR branch can still fetch test-scope secrets. This is deliberate: blocking PR runs would reduce the value of CI. The **scope of secrets** in the `test` Infisical environment is narrow (test placeholders only; prod secrets live in a separate Infisical environment inaccessible to PR OIDC tokens).
- Alternative: pin `environment=production` for any job that fetches prod secrets (future-Epic concern).

**Alternatives considered**:
- **Pin `ref=refs/heads/main`**: rejected — blocks PR CI, undermines SC-004 (live suite via OIDC).
- **Pin nothing except `repository`**: rejected — weaker trust; any workflow in the repo could steal a token.
- **Use a workload identity federation alternative (AWS/GCP)**: rejected — adds non-Infisical provider; out of Epic scope.

**Reference**: [Infisical GitHub Actions docs](https://infisical.com/docs/integrations/cicd/githubactions); [GitHub OIDC token claims spec](https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect#understanding-the-oidc-token).

## R5 — Audit-script parsing strategy

**Decision**: Regex-based. `audit-secrets.sh` greps YAML workflow files for denylisted patterns; `audit-env-registry.py` regex-matches `KOSMOS_[A-Z_]+` literals in `*.py`, `*.yml`, `*.md`, and parses the registry Markdown via a minimal table-line matcher. **Stdlib only** (`re`, `argparse`, `pathlib`, `sys`).

**Rationale**:
- AST parse of Python + proper YAML parse of workflows would be more precise, but (a) adds PyYAML/libcst deps (AGENTS.md violation), (b) the target strings are deliberate literals — no macro/template expansion occurs in KOSMOS to hide a name from regex, (c) the audit is a **drift alarm**, not a compiler: false positives are tolerable if they prompt a human check.
- Regex `KOSMOS_[A-Z_]+` with word-boundaries captures every prefixed env var in the codebase. The registry Markdown uses a fixed table format (Variable | Required | ... | Source), so a line-regex matches each row.
- Markdown table parse: the registry table is the only such construct in `docs/configuration.md` that starts with `| KOSMOS_` or `| LANGFUSE_`; a 5-line regex is sufficient.

**Alternatives considered**:
- **AST-based Python parse**: rejected — adds complexity without catching more; no `KOSMOS_*` name is constructed dynamically in the current codebase.
- **Full YAML parse of workflows**: rejected — adds PyYAML dep; grep is sufficient for "does this token literal appear?".
- **External audit tool (e.g., TruffleHog, Gitleaks)**: rejected — runs outside the registry-drift use case; `audit-secrets.sh` is specifically about workflow-file hygiene, not git-history scanning.

**Reference**: Existing `scripts/` convention (stdlib + bash); Claude Code's ripgrep-first grep discipline.

## R6 — `.env.example` file format

**Decision**: Dotenv format, one `KOSMOS_X=<redacted>` per line. No `export ` prefix. Comments via `#` prefix group vars by subsystem.

**Rationale**:
- `src/kosmos/_dotenv.py` is the parser of record at runtime (and at contributor setup time via `source .env`). It accepts `KEY=VALUE`. `.env.example` must be copy-paste-compatible with what the parser expects.
- `export KEY=VALUE` would require either shell `source` semantics or a shell-aware parser. `_dotenv.py` does not strip `export` prefixes.
- `<redacted>` (literal string) is the sentinel used throughout this Epic's artefacts for forbidden values — makes accidental commits of real secrets stand out (they won't contain `<redacted>`).

**Alternatives considered**:
- **Shell-export format**: rejected — inconsistent with parser.
- **YAML `env.yaml.example`**: rejected — not a drop-in; changes contributor workflow.

**Reference**: `src/kosmos/_dotenv.py:26–46`; dotenv convention per 12-Factor App tooling ecosystem.

## R7 — Bootstrap-secret elimination via Infisical OIDC

**Decision**: Use Infisical's "Universal Auth via OIDC" (GitHub Actions federation). Workflow stores **zero** Infisical secrets in GitHub Encrypted Secrets. `INFISICAL_CLIENT_ID` (public identifier, not a secret) stored in `vars.*` (GitHub Actions repository variables) is acceptable; a GitHub Encrypted Secret for it would also be acceptable but is not required.

**Rationale**:
- Confirmed from Infisical docs during spec research: the `Infisical/secrets-action@v1` action supports `method: oidc` which exchanges the GitHub-issued OIDC JWT for an Infisical access token. No long-lived client-secret is ever stored in the repo.
- The `INFISICAL_CLIENT_ID` is not sensitive (it's an identifier, not a credential). Storing it as a GitHub Actions `var` keeps the workflow declarative and makes rotation a one-line edit.
- The Infisical dashboard's OIDC trust policy (machine identity) holds the *bidirectional* trust — repo+workflow pair on their side, no bootstrap secret on ours.

**Alternatives considered**:
- **Static `INFISICAL_TOKEN` in GitHub Secrets**: rejected — defeats the whole Epic; long-lived token.
- **`INFISICAL_CLIENT_ID` + `INFISICAL_CLIENT_SECRET` both in Secrets**: rejected — retains a bootstrap secret; doesn't meet SC-001.

**Reference**: [Infisical OIDC auth docs](https://infisical.com/docs/documentation/platform/identities/oidc-auth/github); [`Infisical/secrets-action` README on `method: oidc`](https://github.com/Infisical/secrets-action).

## Cross-Epic conflict check

| Other Epic | Potential overlap | Resolution |
|------------|-------------------|------------|
| #507 (MVP tools) | Names `KOSMOS_KAKAO_API_KEY`, `KOSMOS_LOOKUP_TOPK`, `KOSMOS_NMC_FRESHNESS_MINUTES` | ✅ Registry reflects these exact names — no conflict. |
| #501 (observability) | Owns `LANGFUSE_*` + `KOSMOS_OTEL_ENDPOINT` runtime wiring | ✅ Epic #468 *catalogues* names only; code wiring deferred. Conditional-required rule added in registry with "owner: #501". |
| #467 (CI/CD & Prompt Registry) | Owns `docker.yml`, `shadow-eval.yml`, `build-manifest.yml` | ✅ #468 touches `ci.yml` only; forbidden-file list explicit. |
| #465 (LiteLLM) | Will add 6 new env vars (`KOSMOS_LITELLM_MASTER_KEY`, etc.) | ✅ Registry schema designed to accept new rows without breaking audit regex. Entities in `data-model.md` support forward growth. |
| #458 (CLOSED — Kakao degradation) | Root cause: missing `KOSMOS_KAKAO_API_KEY` silently downgraded tool | ✅ This Epic's guard is the named regression guard (spec §User Story 1). |

No conflicts found.

## Infisical Free tier capacity check

Infisical Cloud Free (as of 2026-04): **3 workspaces** × **unlimited secrets** × **unlimited members**. KOSMOS needs 1 workspace (`KOSMOS`) × 2 environments (`test`, `prod`) × ~20 secrets. **Well within limits.** No paid-tier upgrade required for this Epic.

**Stop-condition check**: Free tier not exhausted → proceed.

## Summary — Phase 0 resolutions

- All 7 research topics resolved with concrete decisions and reference citations.
- Zero `[NEEDS CLARIFICATION]` markers produced (below the 3-marker stop condition).
- Deferred-item validation passes.
- No cross-Epic conflicts.
- Infisical Free tier sufficient.

**Gate: PASS.** Proceed to Phase 1.
