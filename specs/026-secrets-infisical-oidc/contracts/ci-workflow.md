# Contract — `.github/workflows/ci.yml` (Infisical Migration)

**Purpose**: Specify how `Infisical/secrets-action@v1` is integrated into `ci.yml` so that (a) no long-lived GitHub Encrypted Secret is required, (b) every `KOSMOS_*` env var needed by CI tests is injected via OIDC-fetched Infisical secrets, (c) the `KOSMOS_DATA_GO_KR_KEY` typo is fixed.

**Related FR**: FR-030..FR-036 · **SC**: SC-001, SC-002, SC-004

---

## Job-level permissions

Every job that invokes `Infisical/secrets-action@v1` MUST declare:

```yaml
permissions:
  id-token: write    # required to mint an OIDC JWT
  contents: read     # default; read-only checkout
```

No other permission bits are needed for this Epic. Jobs that don't invoke Infisical retain their current minimal permissions.

## OIDC trust policy (Infisical side — not in repo)

Configured in Infisical dashboard → Machine Identities → OIDC Auth. Documented here for traceability; not code.

```
Issuer URL:        https://token.actions.githubusercontent.com
Audience:          https://github.com/umyunsang
Claim pins:
  repository       = umyunsang/KOSMOS
  workflow_ref     = umyunsang/KOSMOS/.github/workflows/ci.yml@*
  actor_type       = User
  ref              = * (unpinned — PR CI requires arbitrary branches)
```

Rationale: see `research.md §R4`.

## Repository-variable requirement

```
Settings → Secrets and variables → Actions → Variables (not Secrets):
  INFISICAL_CLIENT_ID = <Infisical machine-identity ID>
```

This is a **variable**, not a secret. Storing as a secret is harmless but semantically wrong (it's a public identifier). Workflow references via `${{ vars.INFISICAL_CLIENT_ID }}`.

**Note on naming**: the variable is kept named `INFISICAL_CLIENT_ID` for backward compatibility with earlier drafts, but its value is passed to the action's `identity-id` input (the authoritative name per the `Infisical/secrets-action@v1` `action.yaml` schema — the action does not expose a `client-id` input for the OIDC flow in the current published version).

## Required workflow block

In every CI job that needs KOSMOS secrets, insert the following step **before** any step that imports application code or runs tests:

```yaml
- name: Fetch secrets from Infisical
  uses: Infisical/secrets-action@v1
  with:
    method: oidc
    identity-id: ${{ vars.INFISICAL_CLIENT_ID }}
    project-slug: kosmos-3f-zs
    env-slug: dev    # or 'prod' for release jobs
    secret-path: '/'
    export-type: env  # inject into job env
```

Inputs (authoritative schema — `Infisical/secrets-action@v1` `action.yaml`):
- `method: oidc` — use OIDC federation (no bootstrap secret).
- `identity-id` — the Infisical machine-identity ID, from repo variable.
- `project-slug` — **required**: human-readable Infisical project slug (`kosmos-3f-zs` for this repo). The action does not accept a `project-id` / UUID input.
- `env-slug` — **required**: which Infisical environment to pull from. CI test runs use `dev` (the default env created by Infisical Cloud for every new project).
- `secret-path` — path within the env tree; `/` pulls everything at project root.
- `export-type: env` — injects fetched secrets as environment variables for subsequent steps in the same job.

## Env injection surface

After the Infisical step runs, the following env vars MUST be available to subsequent steps:

| Var | Required for |
|-----|--------------|
| `KOSMOS_FRIENDLI_TOKEN` | LLM live suite (SC-004) |
| `KOSMOS_KAKAO_API_KEY` | Kakao Local tool tests |
| `KOSMOS_DATA_GO_KR_API_KEY` | data.go.kr tool tests — **NOTE** this is the correct name; prior typo `KOSMOS_DATA_GO_KR_KEY` (FR-050) MUST be eliminated |
| `KOSMOS_JUSO_CONFM_KEY` | JUSO geocoding live tests |
| `KOSMOS_SGIS_KEY` / `KOSMOS_SGIS_SECRET` | SGIS live tests |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` | Langfuse smoke (#501, conditional) |
| `KOSMOS_OTEL_ENDPOINT` | OTLP dry-run (#501, conditional) |

Jobs that need only a subset (e.g., unit tests with no live API) MAY skip the Infisical step and set empty placeholders via `env:` block at step level. Prefer not to: contract consistency matters more than 0.5 s of CI time.

## Typo-fix checklist (FR-050)

In `.github/workflows/ci.yml`:
1. Locate any occurrence of `KOSMOS_DATA_GO_KR_KEY` (line 53 at time of spec).
2. Replace with `KOSMOS_DATA_GO_KR_API_KEY`.
3. Remove the fallback hardcoded `test-placeholder` value once the Infisical step injects the real (test-env) value.

## Pre-test gates

Before any test invocation, the CI job MUST run:

```yaml
- name: Secrets audit
  run: ./scripts/audit-secrets.sh

- name: Env registry drift check
  run: uv run python scripts/audit-env-registry.py
```

Non-zero exit from either gate fails the job (FR-025, SC-005).

## Failure handling

- **Infisical action fails** (network, auth, rate-limit): job fails. No silent fallback to stub values. Error surfaced in CI logs.
- **OIDC trust mismatch** (wrong repo/workflow): Infisical returns 401. Remediation: update Infisical machine-identity trust policy. Do **not** add a fallback secret.
- **Infisical Free tier rate limit**: spec Edge Case #6 — retry once with 5 s backoff; on persistent failure, fail the job and post a GitHub annotation citing `docs/configuration.md#infisical-rate-limit`.

## Rotation workflow (SC-002)

Operator rotates FriendliAI token:
1. Edit secret in Infisical dashboard (`KOSMOS` project → `test` env → `KOSMOS_FRIENDLI_TOKEN`).
2. Re-run last CI workflow (`gh run rerun <ID>`) or push a trivial commit.
3. Expected: next CI run green with new token. **Zero code changes.**

This flow is verified by the `/speckit-implement` closing validation step.

## Non-goals

- Does not specify workflow triggers (`on: push`, `on: pull_request`), concurrency, or matrix — those are preserved from the current `ci.yml`.
- Does not specify `docker.yml` / `shadow-eval.yml` migration — owned by #467.
- Does not specify rotation scheduling / alerting — Deferred (see `research.md` deferred table).

## Full minimal ci.yml patch shape (illustrative; final text in implementation PR)

```yaml
jobs:
  test:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3

      - name: Secrets audit
        run: ./scripts/audit-secrets.sh

      - name: Env registry drift check
        run: uv run python scripts/audit-env-registry.py

      - name: Fetch secrets from Infisical
        uses: Infisical/secrets-action@v1
        with:
          method: oidc
          identity-id: ${{ vars.INFISICAL_CLIENT_ID }}
          project-slug: kosmos-3f-zs
          env-slug: dev
          secret-path: '/'
          export-type: env

      - name: Run pytest
        run: uv run pytest
        # No env: block needed — Infisical injected everything.
```
