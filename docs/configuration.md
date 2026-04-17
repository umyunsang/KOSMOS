# KOSMOS Environment Variable Registry

Authoritative reference for every environment variable consumed by KOSMOS. Machine-parsed by
`scripts/audit-env-registry.py`. Adding a row here — not elsewhere — is the single source of truth.

---

## Overview

KOSMOS follows [12-Factor App Config](https://12factor.net/config): every runtime parameter that
varies between deploy environments (dev, ci, prod) is stored in the process environment, never
baked into source code.

**Prefix rule**: every variable MUST start with `KOSMOS_`. The sole permitted exception is the
`LANGFUSE_*` family, which uses the vendor SDK's default prefix convention and cannot be renamed
without forking the SDK. No other non-`KOSMOS_` prefix is allowed in `src/` code (FR-040,
FR-043).

**`.env` is read-only**: the file `.env` in the repository root is a symlink owned by your local
toolchain (e.g., a 1Password CLI shim, a macOS Keychain-backed mount). No KOSMOS code path may
write, rewrite, rename, or stat `.env`. The stdlib loader in `src/kosmos/_dotenv.py` reads through
the symlink without following it as a file.

**Shell wins over `.env`**: environment variables already set in the process environment take
priority over values in `.env`. This guarantees CI secret injection (Infisical, GitHub Actions
`env:` blocks) always wins over any local developer overrides.

---

## Quick Reference Table

Column definitions:

- **Required** — `Yes (dev/ci/prod)` means the startup guard fails immediately on absence in any
  environment. `Yes (prod only)` means the guard only enforces the variable when `KOSMOS_ENV=prod`.
  `No` means optional in all environments. `Deprecated` means the variable is still honoured for
  backward compatibility but MUST NOT be used for new tools. `Override pattern` marks a family row.
- **Default** — value used when the variable is absent and `Required` is `No`. `—` means no default
  (absence is a guard failure or the field stays empty).
- **Range** — accepted format or value set.
- **Consumed by** — fully qualified `module.Class.attribute` or `module.function` path.
- **Source doc** — where the credential is issued or the setting is documented.

| Variable | Required | Default | Range | Consumed by | Source doc |
|----------|----------|---------|-------|-------------|------------|
| `KOSMOS_ENV` | No | `dev` | `dev` \| `ci` \| `prod` | `kosmos.config.guard.current_env` | This doc |
| `KOSMOS_KAKAO_API_KEY` | Yes (dev/ci/prod) | — | REST API key string | `kosmos.settings.KosmosSettings.kakao_api_key` | [Kakao Developers Console](https://developers.kakao.com) |
| `KOSMOS_FRIENDLI_TOKEN` | Yes (dev/ci/prod) | — | Bearer token | `kosmos.llm.config.LLMClientConfig.token` | [FriendliAI Suite](https://suite.friendli.ai) |
| `KOSMOS_DATA_GO_KR_API_KEY` | Yes (dev/ci/prod) | — | API key string | `kosmos.settings.KosmosSettings.data_go_kr_api_key` | [공공데이터포털](https://www.data.go.kr) |
| `KOSMOS_JUSO_CONFM_KEY` | No (optional fallback) | — | Confirmation key string | `kosmos.settings.KosmosSettings.juso_confm_key` | [도로명주소 개발자센터](https://business.juso.go.kr) |
| `KOSMOS_SGIS_KEY` | No (optional fallback) | — | Consumer key string | `kosmos.settings.KosmosSettings.sgis_key` | [SGIS API](https://sgis.kostat.go.kr) |
| `KOSMOS_SGIS_SECRET` | No (optional fallback) | — | Consumer secret string | `kosmos.settings.KosmosSettings.sgis_secret` | [SGIS API](https://sgis.kostat.go.kr) |
| `KOSMOS_FRIENDLI_BASE_URL` | No | `https://api.friendli.ai/serverless/v1` | Valid HTTPS URL | `kosmos.llm.config.LLMClientConfig.base_url` | FriendliAI Suite |
| `KOSMOS_FRIENDLI_MODEL` | No | `LGAI-EXAONE/K-EXAONE-236B-A23B` | Model identifier string | `kosmos.llm.config.LLMClientConfig.model` | FriendliAI Suite |
| `KOSMOS_LLM_SESSION_BUDGET` | No | `100000` | Integer > 0 (tokens) | `kosmos.llm.config.LLMClientConfig.session_budget` | This doc |
| `KOSMOS_LOOKUP_TOPK` | No | `5` | Integer [1, 20] | `kosmos.settings.KosmosSettings.lookup_topk` | This doc |
| `KOSMOS_NMC_FRESHNESS_MINUTES` | No | `30` | Integer [1, 1440] (minutes) | `kosmos.settings.KosmosSettings.nmc_freshness_minutes` | Epic #507 |
| `KOSMOS_CLI_HISTORY_SIZE` | No | `1000` | Integer >= 0 | `kosmos.cli.config.CLIConfig.history_size` | This doc |
| `KOSMOS_CLI_SHOW_USAGE` | No | `true` | `true` \| `false` | `kosmos.cli.config.CLIConfig.show_usage` | This doc |
| `KOSMOS_CLI_WELCOME_BANNER` | No | `true` | `true` \| `false` | `kosmos.cli.config.CLIConfig.welcome_banner` | This doc |
| `KOSMOS_THEME` | No | `default` | `default` \| `dark` \| `light` | `kosmos.cli.themes.load_theme` | This doc |
| `KOSMOS_CLI_THEME` | No | `default` | `default` \| `dark` \| `light` | `kosmos.cli.themes.load_theme` (alias for `KOSMOS_THEME`) | This doc |
| `KOSMOS_OTEL_ENDPOINT` | Yes (prod only) | — | Valid HTTPS URL | `kosmos.observability.otel (#501)` | Epic #501 |
| `LANGFUSE_PUBLIC_KEY` | Yes (prod only) | — | `pk-lf-…` format string | `kosmos.observability.langfuse (#501)` | [Langfuse Cloud](https://cloud.langfuse.com) |
| `LANGFUSE_SECRET_KEY` | Yes (prod only) | — | `sk-lf-…` format string | `kosmos.observability.langfuse (#501)` | [Langfuse Cloud](https://cloud.langfuse.com) |
| `KOSMOS_{TOOL_ID}_API_KEY` | Override pattern | — | API key string | `kosmos.permissions.credentials._tool_specific_var` | [Per-tool override pattern](#per-tool-override-pattern) |
| `KOSMOS_API_KEY` | **Deprecated** | — | API key string | `kosmos.permissions.credentials.resolve_credential` (global fallback) | [Deprecation notice](#kosmos_api_key-deprecated) |

> **Row count**: 22 rows (17 `KOSMOS_*` active + 2 `LANGFUSE_*` + 1 `KOSMOS_OTEL_ENDPOINT` +
> 1 override-family pattern + 1 deprecated). `KOSMOS_KOROAD_API_KEY` and
> `KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY` are concrete expansions of the
> `KOSMOS_{TOOL_ID}_API_KEY` override-family pattern and are covered by that row.

---

## Variable Details

### `KOSMOS_ENV`

Controls which environment the process is running in. The startup guard uses this value to decide
which conditional-required variables to enforce.

Valid values: `dev` (default), `ci`, `prod`. Any unrecognised value falls through to `dev`
semantics.

When `KOSMOS_ENV ∈ {prod}`, the guard also enforces `KOSMOS_OTEL_ENDPOINT`,
`LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY`.

---

### <a id="kosmos_kakao_api_key"></a>`KOSMOS_KAKAO_API_KEY`

Kakao REST API key. Required in all environments. Consumed by `KosmosSettings.kakao_api_key` and
the permission pipeline's credential resolver at `kosmos.permissions.credentials`.

Source: [Kakao Developers Console](https://developers.kakao.com) → My Application → App Keys →
REST API key.

---

### <a id="kosmos_friendli_token"></a>`KOSMOS_FRIENDLI_TOKEN`

FriendliAI Serverless API bearer token for K-EXAONE inference. Required in all environments.
The `LLMClientConfig.token` field validates that the value is non-empty after stripping whitespace.

Source: [FriendliAI Suite](https://suite.friendli.ai) → API Keys.

---

### <a id="kosmos_data_go_kr_api_key"></a>`KOSMOS_DATA_GO_KR_API_KEY`

Shared 공공데이터포털 (data.go.kr) API key. Required in all environments. Used as the shared
provider credential for KOROAD, KMA, HIRA, and NMC tool adapters. A per-tool override
(`KOSMOS_{TOOL_ID}_API_KEY`) takes precedence when present.

> **Defect note (FR-050)**: Prior to Epic #468, `.github/workflows/ci.yml` injected this variable
> under the typo name `KOSMOS_DATA_GO_KR_KEY`. That typo is fixed as part of this Epic's CI
> migration. If you see the old name in any file surface, it is stale and should be rewritten.

Source: [공공데이터포털](https://www.data.go.kr) → 마이페이지 → 인증키.

---

### <a id="kosmos_juso_confm_key"></a>`KOSMOS_JUSO_CONFM_KEY`

행정안전부 도로명주소 API 확인키. **Optional fallback** — when unset, the JUSO geocoding branch
in `resolve_location.py` logs-and-skips gracefully (the adapter falls through to SGIS / Kakao).
Consumed by `KosmosSettings.juso_confm_key`.

Source: [도로명주소 개발자센터](https://business.juso.go.kr) → 신청 및 현황 → 개발자 확인키.

---

### <a id="kosmos_sgis_key"></a>`KOSMOS_SGIS_KEY`

SGIS (통계지리정보서비스) consumer key, paired with `KOSMOS_SGIS_SECRET`. **Optional fallback** —
when either is unset, the SGIS branch in `resolve_location.py` logs-and-skips gracefully.

Source: [SGIS API](https://sgis.kostat.go.kr) → 활용신청 → 서비스ID/인증키.

---

### <a id="kosmos_sgis_secret"></a>`KOSMOS_SGIS_SECRET`

SGIS consumer secret paired with `KOSMOS_SGIS_KEY`. **Optional fallback** — see
`KOSMOS_SGIS_KEY` above for the skip-when-unset behaviour.

Source: [SGIS API](https://sgis.kostat.go.kr) → 활용신청 → 서비스ID/인증키.

---

### <a id="kosmos_otel_endpoint"></a>`KOSMOS_OTEL_ENDPOINT`

OTLP HTTP endpoint for OpenTelemetry trace export. Conditional-required: the startup guard enforces
this variable only when `KOSMOS_ENV=prod`. In `dev` and `ci`, the OTel SDK is initialised in
no-op mode and this variable is not consulted.

The consuming code lives in Epic #501 (`kosmos.observability.otel`), which is not yet merged.

---

### <a id="langfuse_public_key"></a>`LANGFUSE_PUBLIC_KEY`

Langfuse public key for trace ingestion. Conditional-required (`KOSMOS_ENV=prod`). The
`LANGFUSE_*` prefix is the only permitted non-`KOSMOS_` prefix in this registry; it is used
because the Langfuse Python SDK reads these variables by default and renaming them would require
forking the SDK (FR-040, FR-043).

Source: [Langfuse Cloud](https://cloud.langfuse.com) → Settings → API Keys.

---

### <a id="langfuse_secret_key"></a>`LANGFUSE_SECRET_KEY`

Langfuse secret key paired with `LANGFUSE_PUBLIC_KEY`. Conditional-required (`KOSMOS_ENV=prod`).

Source: [Langfuse Cloud](https://cloud.langfuse.com) → Settings → API Keys.

---

### <a id="per-tool-override-pattern"></a>Per-tool Override Pattern: `KOSMOS_{TOOL_ID}_API_KEY`

Any env var matching the expansion `KOSMOS_<TOOL_ID_UPPER>_API_KEY` (e.g.,
`KOSMOS_KOROAD_ACCIDENT_SEARCH_API_KEY`) is a per-tool credential override. When present, it takes
priority over the provider-level key (`KOSMOS_DATA_GO_KR_API_KEY` or `KOSMOS_KAKAO_API_KEY`) in
the lookup chain defined by `kosmos.permissions.credentials.resolve_credential`.

The audit script treats any env var name matching this pattern as covered by this family row,
suppressing "undocumented" false positives for concrete expansions.

Lookup order (from `kosmos.permissions.credentials.resolve_credential`):

1. `KOSMOS_{TOOL_ID_UPPER}_API_KEY` (this override)
2. Provider-level key (`KOSMOS_KAKAO_API_KEY` or `KOSMOS_DATA_GO_KR_API_KEY`)
3. `KOSMOS_API_KEY` (deprecated global fallback)

Do NOT add per-tool concrete expansions as individual registry rows. Use this family row.

---

### <a id="kosmos_api_key-deprecated"></a>`KOSMOS_API_KEY` — Deprecated

**Do not use for new tool adapters.** This is the legacy global credential fallback honoured by
`kosmos.permissions.credentials.resolve_credential` as the last resort in the lookup chain.

Replacement: use the appropriate provider-level key (`KOSMOS_KAKAO_API_KEY` or
`KOSMOS_DATA_GO_KR_API_KEY`) or a per-tool override (`KOSMOS_{TOOL_ID}_API_KEY`).

Removal target: post-#468 (tracking issue #744). Removal requires a cross-tool refactor to
eliminate all remaining callers; that work is deferred.

---

## How to Add a Variable

Adding a new `KOSMOS_*` variable is a **three-file change** (NFR-006). No schema migration, no
row reordering required.

### Step 1 — Add a row to this registry

Append a new row to the [Quick Reference Table](#quick-reference-table) above. Fill all six
columns:

```
| `KOSMOS_MY_NEW_VAR` | Yes (dev/ci/prod) | — | Description of format | `kosmos.my_module.MyClass.field` | Where credential is issued |
```

Also add a `###` detail section below the table with the anchor
`<a id="kosmos_my_new_var"></a>`.

Allowed `Required` column values: `Yes (dev/ci/prod)`, `Yes (prod only)`, `No`,
`Deprecated`, `Override pattern`.

### Step 2 — Add a line to `.env.example`

Open `.env.example` and append:

```bash
KOSMOS_MY_NEW_VAR=<redacted>  # kosmos.my_module — where to get this value
```

Use `<redacted>` exclusively. Never use a plausible-looking value (hex string, bearer format, UUID).

### Step 3 — Add the consumer in source

Add the field to the relevant `BaseSettings` subclass or read it with `os.environ.get()` in the
consuming module. Reference the exact `module.Class.attribute` path in the registry row's
`Consumed by` column.

**Optionally — add to the startup guard**

If the variable must be non-empty at process start in one or more environments, add a `RequiredVar`
entry to `_REQUIRED_VARS` in `src/kosmos/config/guard.py`:

```python
RequiredVar(
    name="KOSMOS_MY_NEW_VAR",
    consumer="kosmos.my_module.MyClass.field",
    required_in=frozenset({"dev", "ci", "prod"}),
    doc_anchor="#kosmos_my_new_var",
),
```

### Step 4 — Verify locally

```bash
uv run python scripts/audit-env-registry.py
```

Exit code `0` means code and registry agree. Non-zero prints a diff-style report.

---

## Infisical Operator Runbook

This section documents how to configure Infisical Cloud Free as the secrets provider for CI.
Perform these steps once per repository setup. No secret value appears here; all token fields are
`<redacted>`.

### Prerequisites

- Infisical Cloud Free account at [app.infisical.com](https://app.infisical.com)
- GitHub repository admin access to `umyunsang/KOSMOS`
- `gh` CLI authenticated

### Step 1 — Create the Infisical project

1. Log in to Infisical Cloud.
2. Create a new project named `kosmos`.
3. Note the project UUID shown in the project settings URL (e.g.,
   `app.infisical.com/project/<UUID>/settings`). This is your `project-id` for
   `Infisical/secrets-action@v1`.
4. Create two environments inside the project: `dev` and `test` (and `prod` when needed).

### Step 2 — Add secrets

In the Infisical dashboard, navigate to the `test` environment and add each required variable from
the [Quick Reference Table](#quick-reference-table) whose `Required` column is `Yes (dev/ci/prod)`.
Use the real credential values retrieved from the respective source portals. Never paste these
values into any file committed to the repository.

At minimum, the `test` environment must contain the guard-required variables:

- `KOSMOS_FRIENDLI_TOKEN`
- `KOSMOS_KAKAO_API_KEY`
- `KOSMOS_DATA_GO_KR_API_KEY`

Optional fallback variables (if unset, the corresponding geocoding branch logs-and-skips):

- `KOSMOS_JUSO_CONFM_KEY`
- `KOSMOS_SGIS_KEY`
- `KOSMOS_SGIS_SECRET`

### Step 3 — Register a Machine Identity with OIDC auth

1. In Infisical: **Access Control** → **Machine Identities** → **Create identity**.
   Name: `kosmos-github-actions`. Role: `member` scoped to the `kosmos` project.
2. Under the identity's **Auth methods**, select **OIDC Auth** and configure:

```
Issuer URL:    https://token.actions.githubusercontent.com
Audience:      https://github.com/umyunsang
```

3. Add a claim binding (trust rule):

| Claim | Operator | Value |
|-------|----------|-------|
| `repository` | `=` | `umyunsang/KOSMOS` |
| `workflow_ref` | contains | `umyunsang/KOSMOS/.github/workflows/ci.yml` |

4. Save the identity. Note the **Client ID** (a public UUID).

### Step 4 — Bind the machine identity to the repository

No GitHub secret is required when using pure OIDC federation. Store the Client ID as a GitHub
Actions **variable** (not a secret):

```
Settings → Secrets and variables → Actions → Variables → New repository variable
Name:  INFISICAL_CLIENT_ID
Value: <the Client ID UUID from Step 3>
```

This value is a public identifier and does not need secret protection.

### Step 5 — Environment slug mapping

| CI context | Infisical env slug |
|------------|--------------------|
| Unit tests (no live APIs) | `dev` |
| Live-suite tests | `dev` |
| Release builds | `prod` (when applicable) |

The `env-slug: dev` value in `.github/workflows/ci.yml` pulls from the Infisical `dev`
environment (the default environment created by Infisical Cloud for every new project).

### Step 6 — Verify the OIDC trust

Trigger a CI run on any branch. Inspect the "Fetch secrets from Infisical" step. A successful
output looks like:

```
✓ Authenticated with Infisical using OIDC
✓ Fetched 6 secrets from project kosmos / environment dev
```

If you see a `401 Unauthorized` error, the claim binding is misconfigured. Re-check the
`repository` and `workflow_ref` claim values in Step 3.

### Step 7 — Secret rotation

To rotate any credential (e.g., `KOSMOS_FRIENDLI_TOKEN`):

1. In Infisical dashboard: `kosmos` project → `test` environment → edit the secret value.
2. Re-run CI: `gh run rerun <run-id>` or push a trivial commit.
3. The next CI run picks up the new value. **Zero code changes required.**

### Known Failure Modes

<a id="infisical-rate-limit"></a>

**Infisical service unavailable or rate-limited (HTTP 503 / 429)**

The `Infisical/secrets-action@v1` step retries once with a 5-second backoff. On persistent
failure the job fails immediately with a log message naming Infisical as the blocker. The CI
workflow never falls back to stub values or empty variables on a secrets-fetch failure (FR-034).

If your CI run fails at the secrets-fetch step with a 503 or connection error:

1. Check [Infisical status](https://status.infisical.com) for active incidents.
2. Re-run the failed CI job (`gh run rerun <run-id> --failed`).
3. If the failure persists for more than 30 minutes, follow the [Rollback Procedure](#rollback-procedure)
   to restore GitHub Encrypted Secrets temporarily.

The CI workflow posts a GitHub annotation citing
`docs/configuration.md#infisical-rate-limit` when this failure mode is detected.

**OIDC token exchange rejected**

Infisical returns `401`. Cause: the GitHub Actions OIDC token claims do not match the trust
policy. Fix: update the claim binding in Infisical (Step 3 above). Do not add a fallback secret.

**Infisical Free tier capacity**

The Free tier supports up to 5 projects and an unlimited number of secrets per project. If the
project count or audit-log retention becomes a constraint, surface it as a blocker before
splitting secrets across two platforms.

---

## Rollback Procedure

**Target**: restore CI to a working state within 15 minutes when the Infisical migration is
broken (FR-036, SC-008).

### Step 1 — Identify the pre-migration `ci.yml` commit

```bash
git log --oneline .github/workflows/ci.yml
```

Note the commit SHA immediately before the Infisical migration commit.

### Step 2 — Revert the workflow file

```bash
git revert <ci.yml-infisical-migration-commit-sha>
git push origin feat/468-secrets-config
```

This restores `ci.yml` to its pre-Infisical state, which references GitHub Encrypted Secrets.

### Step 3 — Re-populate GitHub Encrypted Secrets

Export the current secret values from Infisical (dashboard → project → export) and re-enter them
as GitHub Encrypted Secrets at:

```
Settings → Secrets and variables → Actions → New repository secret
```

Minimum set required for CI to pass (guard-required; missing = startup EX_CONFIG):

| Secret name | Source |
|-------------|--------|
| `KOSMOS_FRIENDLI_TOKEN` | Infisical export |
| `KOSMOS_KAKAO_API_KEY` | Infisical export |
| `KOSMOS_DATA_GO_KR_API_KEY` | Infisical export |

Optional fallbacks (add only if the live geocoding suite needs them):

| Secret name | Source |
|-------------|--------|
| `KOSMOS_JUSO_CONFM_KEY` | Infisical export |
| `KOSMOS_SGIS_KEY` | Infisical export |
| `KOSMOS_SGIS_SECRET` | Infisical export |

### Step 4 — Verify

Trigger a CI run and confirm the test suite passes. Once stabilised, open a new PR to re-apply
the Infisical migration after the root cause is resolved.

> The 15-minute SLO assumes the operator has Infisical dashboard access and GitHub admin rights.
> Pre-stage these access tokens in a password manager before beginning the migration.

---

## Test-only Variables

The following variables appear exclusively in test fixtures and are never read by production code.
They do not need to be populated in production or developer `.env` files.

| Variable | Purpose | Required |
|----------|---------|----------|
| `KOSMOS_AUTH_TEST_TOOL_API_KEY` | Credential fixture for permission-pipeline unit tests | No (test only) |
| `KOSMOS_SKIP_PERF` | Skip performance-sensitive assertions in slow CI environments | No (test only) |

---

## Related Documents

- `AGENTS.md` § Hard rules — prefix rule and `.env` no-write constraint
- `docs/vision.md` — six-layer architecture; this registry maps to Layer 2 (Config)
- `src/kosmos/config/guard.py` — startup guard implementation; `_REQUIRED_VARS` must stay
  in sync with the `Yes (dev/ci/prod)` and `Yes (prod only)` rows in this table
- `specs/026-secrets-infisical-oidc/spec.md` — full FR/NFR specification for Epic #468
- `scripts/audit-env-registry.py` — CI enforcement script that parses this table
