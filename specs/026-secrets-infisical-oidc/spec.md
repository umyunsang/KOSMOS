# Feature Specification: Secrets & Config — Infisical OIDC + 12-Factor + KOSMOS_* Registry

**Feature Branch**: `feat/468-secrets-config`
**Created**: 2026-04-17
**Status**: Draft
**Input**: User description: Epic #468 — Secrets & Config: Infisical OIDC + 12-Factor + KOSMOS_* registry. Two converging failure modes motivate this work: (1) secret hygiene — long-lived GitHub Encrypted Secrets are the retired 2025 pattern; 2026 standard is short-lived OIDC federation; (2) env-var registry drift — Epic #458 (closed 2026-04-16) burned a day misdiagnosing a missing `KOSMOS_KAKAO_API_KEY` as an external FriendliAI CJK-decoder defect. KOSMOS has no authoritative registry, no fail-fast startup guard, and no `.env.example`. Scope: (A) Infisical Cloud Free OIDC migration; (B) canonical `docs/configuration.md` registry; (C) fail-fast startup guard `src/kosmos/config/guard.py`; (D) 12-Factor cleanup + audit scripts.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Fail-fast startup guard prevents silent mis-configuration (Priority: P1)

A contributor clones KOSMOS for the first time, runs the CLI without populating `.env`, or loses a secret during a rotation window. Today, the process boots, the LLM accepts the session, and only downstream tool calls silently degrade — which is exactly how Epic #458 (closed 2026-04-16) consumed a day of wrong-root-cause investigation before the root cause (missing `KOSMOS_KAKAO_API_KEY`) was found. With the guard in place, the CLI exits within 100 ms and prints a single-line message listing every missing required variable plus a stable pointer to `docs/configuration.md`.

**Why this priority**: Direct regression guard for the incident that motivated the Epic. Delivers the full user-visible value of faster, cheaper mis-config diagnosis with zero dependency on Infisical migration or registry rollout. The guard works whether secrets come from `.env`, the shell, CI injection, or a future secret manager — it only validates presence at the boundary.

**Independent Test**: With an empty `.env` and no shell exports, invoke the CLI. Observe a non-zero exit within 100 ms whose single-line message names every missing required variable and includes the remediation URL `docs/configuration.md`. Confirmed green by `tests/config/test_guard.py` without needing the registry file to exist yet (test uses an in-memory registry fixture).

**Acceptance Scenarios**:

1. **Given** a fresh clone with no `.env` and no shell `KOSMOS_*` exports, **When** the contributor runs the CLI entry point, **Then** the process exits with a non-zero status within 100 ms and `stderr` contains exactly one line naming every missing required variable plus the path `docs/configuration.md`.
2. **Given** `.env` populated with every required variable, **When** the CLI starts, **Then** the guard emits nothing and the tool loop proceeds normally.
3. **Given** a single required variable is unset (e.g., `KOSMOS_KAKAO_API_KEY`), **When** the CLI starts, **Then** the single-line message names exactly that variable and no other.
4. **Given** a conditional-required variable is unset but its activation flag (`KOSMOS_ENV=prod`) is absent, **When** the CLI starts in `dev` mode, **Then** the guard does not treat the conditional variable as missing.
5. **Given** a live-suite test fixture runs, **When** the fixture boots KOSMOS, **Then** the guard is invoked and fails the suite with the same single-line message if any live-suite-required variable is missing.

---

### User Story 2 — Canonical env-var registry replaces scattered defaults (Priority: P2)

A contributor adding a new tool adapter — or a reviewer auditing a PR — needs a single authoritative answer to "what `KOSMOS_*` variables exist, which are required, what the default is, which module consumes them, and where to get the credential." Today, the answer is split across `src/kosmos/settings.py` (7 fields), `src/kosmos/llm/config.py` (6 fields with their own alias pattern), `src/kosmos/cli/config.py` (3 fields plus `KOSMOS_THEME`), `src/kosmos/permissions/credentials.py` (per-tool override pattern + legacy `KOSMOS_API_KEY` fallback), and scattered `os.environ.get()` calls. The Epic body's nine-row table is a subset of the actual surface — discovered during spec research, `grep -rhoE "KOSMOS_[A-Z_]+"` returned 17 distinct names in `src/` alone and another eight test-only variables. The new `docs/configuration.md` enumerates every variable with columns `Variable | Required | Default | Range | Consumed by | Source doc`, and a CI-enforced audit script fails the build the moment code and registry diverge.

**Why this priority**: The registry is the long-term leverage of the Epic — it stops future instances of the #458 class of bug before they happen and gives new contributors a one-screen onboarding surface. Independent of Infisical migration: the registry catalogues names, not storage mechanisms.

**Independent Test**: Review `docs/configuration.md` and confirm every variable returned by `grep -rhoE "KOSMOS_[A-Z_]+" src/ --include="*.py"` is present with all six schema columns filled. Invoke `scripts/audit-env-registry.py`; exit code is `0` when code and registry agree, non-zero with a diff-style report when they disagree.

**Acceptance Scenarios**:

1. **Given** the current `src/` tree, **When** `scripts/audit-env-registry.py` is run, **Then** the script exits `0` and prints no drift.
2. **Given** a contributor adds `os.environ.get("KOSMOS_NEW_THING")` to a source file without updating `docs/configuration.md`, **When** CI runs the audit, **Then** CI fails and the report names `KOSMOS_NEW_THING` as present in code but absent from registry.
3. **Given** `docs/configuration.md` lists a variable no longer consumed by code, **When** the audit runs, **Then** CI fails and the report names the stale entry.
4. **Given** a reviewer opens `docs/configuration.md`, **When** they search for the canonical source of any `KOSMOS_*` name referenced in any PR, **Then** the registry returns exactly one row with all six schema columns.
5. **Given** the registry schema is extended (e.g., `#465` LiteLLM adds six new variables), **When** those rows are appended, **Then** no existing row is modified and the audit remains green.

---

### User Story 3 — OIDC-federated CI replaces long-lived GitHub Secrets (Priority: P3)

The CI operator (today, the project owner; tomorrow, any collaborator) needs to run the test suite — including the 33-test live suite — without storing any long-lived API token as a GitHub Encrypted Secret. Today, `.github/workflows/ci.yml` injects `KOSMOS_DATA_GO_KR_KEY`, `KOSMOS_KOROAD_API_KEY`, `KOSMOS_FRIENDLI_TOKEN` as hard-coded placeholder strings for mocked tests, while the real live-suite keys would need to live as Encrypted Secrets. After migration, `Infisical/secrets-action@v1` exchanges the GitHub Actions OIDC token for a short-lived Infisical service identity token at job start, fetches the current `KOSMOS_*` values from Infisical project `kosmos-ci`, and injects them as environment variables scoped to the job. No secret material ever lives in `.github/workflows/*.yml` or in the GitHub repository Settings → Secrets page.

**Why this priority**: Highest operational setup cost (Infisical project creation, OIDC identity registration, GitHub repo trust binding, manual token rotation into Infisical) and depends on the guard (Story 1) and registry (Story 2) to be usefully testable — the guard tells us whether OIDC injected the right names; the registry tells us which names need injecting. Once done, rotating any token is a one-click Infisical operation with zero code change.

**Independent Test**: On a CI run triggered after a fresh FriendliAI token rotation inside Infisical (with no source-code changes since the previous run), the test job succeeds and the 33-test live suite passes. Grep of `.github/workflows/ci.yml` shows no raw secret values and no GitHub Secret references other than the bootstrap identity (or none at all, if pure OIDC is used).

**Acceptance Scenarios**:

1. **Given** Infisical holds the current live-suite tokens and `.github/workflows/ci.yml` uses `Infisical/secrets-action@v1`, **When** CI runs on a clean commit, **Then** the live suite passes and `jobs.<id>.env` contains no hard-coded secret values.
2. **Given** the operator rotates `KOSMOS_FRIENDLI_TOKEN` inside Infisical only, **When** the next CI run is triggered, **Then** the run succeeds with no source or workflow file change in git.
3. **Given** a commit adds a raw token pattern (`ghp_…`, `sk-…`, bearer-token string) anywhere under `.github/workflows/`, **When** CI runs `scripts/audit-secrets.sh`, **Then** CI fails before any test job starts.
4. **Given** Infisical's OIDC endpoint is unreachable, **When** CI starts, **Then** the job fails fast with an explicit message naming Infisical as the blocker — never silently falls back to an empty token.
5. **Given** the GitHub repository `Settings → Secrets and variables → Actions` page, **When** an auditor inspects it after migration, **Then** no `KOSMOS_*` token is stored there; at most a bootstrap `INFISICAL_CLIENT_ID` exists, and preferably nothing at all if pure OIDC federation is used.

---

### Edge Cases

- **`.env` is a symlink**: The contributor's `.env` is a symlink into a secret-management tool (e.g., macOS Keychain-backed mount, 1Password CLI shim, a sibling worktree). The guard and the stdlib loader (`src/kosmos/_dotenv.py`) MUST read through the symlink without following, overwriting, rewriting, or warning about it. No code path in this Epic's scope may write to `.env`.
- **Variable with empty string value**: `KOSMOS_KAKAO_API_KEY=""` is semantically the same as "unset" and MUST be treated as missing by the guard.
- **Variable with whitespace-only value**: `KOSMOS_KAKAO_API_KEY="   "` MUST be treated as missing after `.strip()`.
- **Conditional-required variable activation**: When `KOSMOS_ENV=prod` or `KOSMOS_ENV=ci`, `KOSMOS_OTEL_ENDPOINT`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY` graduate from "optional" to "required". When `KOSMOS_ENV` is absent or equals `dev`, they stay optional.
- **Legacy `KOSMOS_API_KEY` fallback**: The permissions module's global fallback pattern is an existing escape hatch. The registry MUST document it as `deprecated` and forbid its use for newly added tools, without breaking current tool lookups.
- **Per-tool `KOSMOS_<TOOL_ID>_API_KEY` override**: An intentional escape hatch for per-tool credential isolation (e.g., the shared `data.go.kr` key being overridden by a KOROAD-specific key). The registry MUST document the pattern as a family with a single schema row, not enumerate every possible tool id.
- **Shell export wins over `.env`**: CI/CD, systemd, and Docker injection set variables in the process environment before Python starts. The loader MUST never overwrite a pre-existing `os.environ` entry — a property the current `src/kosmos/_dotenv.py` already guarantees and this Epic MUST preserve.
- **Infisical free-tier cap reached**: If the Infisical Cloud Free tier lacks capacity for the required project count, secret count, or audit-log retention, the Epic MUST surface that as a blocker before migration work starts rather than silently splitting secrets across two platforms.
- **OIDC identity misconfiguration**: If the Infisical OIDC trust rule rejects the GitHub Actions token (wrong `repository`, `ref`, or `workflow` claim), the job MUST fail at the secret-fetch step with a message naming the claim mismatch — never proceed with a partial environment.
- **`.env.example` drift**: A contributor may add a required variable to `docs/configuration.md` but forget `.env.example`. The audit script MUST also treat `.env.example` as a sink and flag missing rows.
- **Audit false positives from comments**: Words like `token` or `api_key` may legitimately appear in YAML comments (e.g., `# rotate this token quarterly`). `scripts/audit-secrets.sh` MUST distinguish assignment patterns from prose.

## Requirements *(mandatory)*

### Functional Requirements

#### A. Fail-fast startup guard

- **FR-001**: System MUST provide a `guard` entry point that, given an authoritative list of required variable names, exits the process with a non-zero status within 100 ms when any required name resolves to a missing, empty, or whitespace-only value.
- **FR-002**: The guard MUST emit a single `stderr` line containing (a) every missing required name in a stable order, (b) a human-readable delimiter, and (c) the exact remediation pointer `docs/configuration.md`. No partial, multi-line, or colour-coded output.
- **FR-003**: The guard MUST be invoked by the CLI entry point before any tool-loop, LLM-client, or network code executes; the check MUST be the first runtime side-effect after argument parsing.
- **FR-004**: The guard MUST be exposed as a reusable fixture for any `tests/live/**` or integration test that requires real credentials, so live-suite failures surface at setup rather than as ambiguous tool-call errors.
- **FR-005**: The guard MUST treat conditional-required variables as required only when their activation flag (`KOSMOS_ENV ∈ {prod, ci}` for observability variables) is set; otherwise they remain optional.
- **FR-006**: The guard MUST treat an empty string or whitespace-only string as equivalent to an unset variable.
- **FR-007**: The guard MUST NOT read, print, log, or emit any secret value; only variable **names** appear in output.
- **FR-008**: The guard MUST read its list of required names from a single in-process data structure (not from the filesystem at runtime), to eliminate a "registry moved" class of bug.

#### B. Canonical env-var registry

- **FR-010**: Project MUST ship a new file `docs/configuration.md` as the single authoritative registry of every `KOSMOS_*` variable and every explicitly allowlisted non-`KOSMOS_` variable (currently: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`).
- **FR-011**: Each registry row MUST carry six columns: `Variable`, `Required` (✅ / ⚠️ / ❌), `Default`, `Range`, `Consumed by` (module path), `Source doc` (where the credential is issued).
- **FR-012**: The registry MUST enumerate, at minimum, every variable discovered by `grep -rhoE "KOSMOS_[A-Z_]+" src/ --include="*.py"` at the time of merge. Test-only variables (`KOSMOS_AUTH_TEST_TOOL_API_KEY`, `KOSMOS_SKIP_PERF`, etc.) MAY be grouped under a dedicated "Test-only" subsection.
- **FR-013**: The registry MUST document the legacy fallback `KOSMOS_API_KEY` with `Required: ❌ (deprecated)` and a note forbidding its use for newly added tools.
- **FR-014**: The registry MUST document the per-tool override pattern `KOSMOS_<TOOL_ID>_API_KEY` as a single family row, not one row per tool id.
- **FR-015**: The registry MUST document conditional-required variables (`KOSMOS_OTEL_ENDPOINT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`) with `Required: ⚠️` and a note specifying the activation condition (`KOSMOS_ENV ∈ {prod, ci}`).
- **FR-016**: The registry schema MUST be append-only with respect to existing rows: adding a new row (e.g., the `#465` LiteLLM expansion) MUST NOT require editing any existing row's columns or ordering.
- **FR-017**: The registry MUST include a short "how to add a variable" runbook that instructs contributors to (1) update the registry, (2) update `.env.example`, (3) update the guard's required list if required, (4) run the audit script locally.
- **FR-018**: `.env.example` MUST be regenerated so that every required and conditional-required variable from the registry appears with a `<redacted>` placeholder and a trailing comment naming the consuming module.
- **FR-019**: `.env.example` MUST NOT contain any real secret value or any credential format that could be confused for a real value (e.g., prefer `<redacted>` over a plausible-looking hex string).

#### C. Registry-to-code audit

- **FR-020**: Project MUST ship `scripts/audit-env-registry.py` that (a) parses the `docs/configuration.md` registry table, (b) greps the `src/` tree for every `KOSMOS_*` string literal, (c) greps `.env.example` for every `KOSMOS_*` entry, and (d) exits non-zero with a diff-style report when code, registry, and example diverge.
- **FR-021**: The audit MUST report missing variables in both directions — "present in code, absent from registry" and "present in registry, absent from code" — with one line per offending name.
- **FR-022**: The audit MUST be invokable locally (`python scripts/audit-env-registry.py`) and from CI with identical exit semantics.
- **FR-023**: Project MUST ship `scripts/audit-secrets.sh` that greps `.github/workflows/ci.yml` for long-lived secret patterns (assignment of literal token strings, `secrets.KOSMOS_*` references that aren't the bootstrap identity) and exits non-zero on any match.
- **FR-024**: Both audit scripts MUST run as required steps of `.github/workflows/ci.yml` **before** any test or build job, so misconfiguration cannot waste runner time.
- **FR-025**: Audit failure messages MUST name the offending line, file, and the registry rule violated so a reader can fix the drift without re-running the script.

#### D. Infisical OIDC migration

- **FR-030**: `.github/workflows/ci.yml` MUST replace every long-lived `KOSMOS_*` secret reference with a single `Infisical/secrets-action@v1` step that exchanges the GitHub Actions OIDC token for a short-lived Infisical service-identity token and fetches the job's variables from the Infisical project `kosmos-ci`.
- **FR-031**: The migration MUST NOT retain any `KOSMOS_*` value as a GitHub Encrypted Secret. A bootstrap `INFISICAL_CLIENT_ID` (or equivalent non-secret identity identifier) is permitted only if pure OIDC federation cannot be configured.
- **FR-032**: The migration scope MUST be limited to `.github/workflows/ci.yml`. Other workflows (`security.yml`, `sbom.yml`, `eval.yml`, `pr-lint.yml`) MUST be left untouched in this Epic; `docker.yml` and `shadow-eval.yml` are owned by Epic #467 and MUST NOT be opened.
- **FR-033**: Infisical project configuration (project slugs, identity IDs, environment slugs, OIDC trust rules) MUST be documented in `docs/configuration.md` as a step-by-step runbook the operator can execute manually. No token value appears in the runbook.
- **FR-034**: When the Infisical secrets-fetch step fails, the workflow MUST surface the failure as the visible cause — never silently continue with empty variables.
- **FR-035**: After migration, rotating any secret MUST be a single Infisical-side operation with zero code, workflow, or GitHub Secrets change.
- **FR-036**: The migration runbook MUST include a rollback procedure (restore the previous `ci.yml` from git history, re-populate GH Encrypted Secrets from Infisical exports) executable within 15 minutes.

#### E. 12-Factor cleanup

- **FR-040**: Every environment variable read by `src/` code MUST start with the prefix `KOSMOS_`, with the single documented exception family `LANGFUSE_*` (owned by the observability vendor's SDK convention).
- **FR-041**: The `src/kosmos/_dotenv.py` loader MUST continue to honour the "shell wins over `.env`" rule; this Epic MUST NOT regress that property.
- **FR-042**: The `.env` file MUST NOT be written, rewritten, renamed, or touched by any code in this Epic's scope. `.env` is a symlink in the working tree and is owned by the contributor's local toolchain.
- **FR-043**: The registry MUST explicitly name `LANGFUSE_*` as the only permitted non-`KOSMOS_*` prefix and explain why (vendor SDK default).

#### F. Defects fixed (mandatory sub-scope)

- **FR-050**: `.github/workflows/ci.yml` currently injects `KOSMOS_DATA_GO_KR_KEY` as a job environment variable, but `src/kosmos/settings.py` and `src/kosmos/permissions/credentials.py` both read `KOSMOS_DATA_GO_KR_API_KEY`. This typo MUST be fixed in this Epic (rename the workflow env var to match the code).
- **FR-051**: Epic #468 body references `KOSMOS_KAKAO_REST_KEY` as living in `docs/tool-adapters.md`. The actual stale occurrence is at `docs/design/mvp-tools.md:642`. The spec MUST surface this location correction; `docs/design/mvp-tools.md:642` MUST be updated to the canonical name `KOSMOS_KAKAO_API_KEY` (FR-051 is in-scope file surface; other prose edits to `docs/tool-adapters.md` remain limited to typo fixes only, per the Lead constraint).
- **FR-052**: Any other documentation occurrence of `KOSMOS_KAKAO_REST_KEY` discovered during the registry audit MUST be rewritten to `KOSMOS_KAKAO_API_KEY` as a single atomic find-and-replace commit inside the allowed file surface.

### Non-Functional Requirements

- **NFR-001** (Performance): The guard's end-to-end wall-clock time from CLI entry to `stderr` emission MUST be under 100 ms on a 2020-era developer laptop, measured by `tests/config/test_guard.py` using `time.monotonic()`.
- **NFR-002** (Observability): The guard MUST NOT emit structured logs, metrics, or traces during a failure — only the single `stderr` line — to keep the failure readable on a narrow terminal.
- **NFR-003** (Security — no plaintext): Neither the guard, audit scripts, registry, `.env.example`, nor workflow files may contain any real secret value. Only `<redacted>` placeholders are permitted.
- **NFR-004** (Security — short-lived tokens): After Infisical migration, no CI token is valid for longer than the GitHub Actions job it was issued for (Infisical's identity token default is single-use; the migration MUST NOT extend that).
- **NFR-005** (Portability — stdlib-only loader): `src/kosmos/_dotenv.py` MUST NOT acquire a new third-party dependency; the AGENTS.md hard rule against unsolicited dependency additions applies.
- **NFR-006** (Extensibility): Adding a new `KOSMOS_*` variable MUST be a three-file change — registry, `.env.example`, and the consuming module — with no schema migration and no registry re-ordering.
- **NFR-007** (Backwards compatibility): Existing production invocations that populate `KOSMOS_*` via the shell or CI environment MUST continue to work without modification through this Epic's rollout.
- **NFR-008** (Documentation): `docs/configuration.md` MUST be reachable via `docs/vision.md` or `AGENTS.md` so a new contributor cannot miss it during onboarding.

### Key Entities

- **Environment Variable Registry**: The canonical table of every `KOSMOS_*` (and allowlisted `LANGFUSE_*`) variable. Each row has: variable name, required level (required / conditional / optional / deprecated), default value (or `—`), accepted range, consuming module path, and source-of-credential doc. Persisted as `docs/configuration.md`; machine-parsed by `scripts/audit-env-registry.py`.
- **Startup Guard**: A boundary validator invoked once per process at CLI entry (and per-fixture in live tests). Inputs: the in-process required-name list, the activation flag `KOSMOS_ENV`, and `os.environ`. Outputs: exit status 0 (quiet) or non-zero with a single `stderr` line.
- **Secrets Provider**: The system that materialises secret values at CI runtime. Before this Epic: GitHub Encrypted Secrets (long-lived, copy-pasted). After: Infisical Cloud Free, with the values fetched via OIDC-federated short-lived tokens at job start.
- **Audit Scripts**: Two boundary validators that run in CI before any test or build work — `scripts/audit-env-registry.py` (code ↔ registry ↔ `.env.example`) and `scripts/audit-secrets.sh` (workflow files ↔ no long-lived secret patterns).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001** (SC-1 from Epic): Running `grep -r "tokens\|api_key\|secret" .github/workflows/ci.yml | grep -v infisical` after the merge returns zero matches. All secret material enters CI via the Infisical action only.
- **SC-002** (SC-2 from Epic): The operator rotates the FriendliAI token inside Infisical and triggers the next CI run with zero source or workflow-file changes in git. The subsequent run is green.
- **SC-003** (SC-3 from Epic): `docs/configuration.md` documents every `KOSMOS_*` variable (and allowlisted `LANGFUSE_*`) present in `src/`. Running `scripts/audit-env-registry.py` returns exit `0` and no drift.
- **SC-004** (SC-4 from Epic): The live suite (currently 33 tests) is green on the first post-migration CI run, using only Infisical-injected tokens. No manual re-runs. No secret values present in `.github/workflows/ci.yml`.
- **SC-005** (SC-5 from Epic): `scripts/audit-secrets.sh` runs as a required CI pre-step; intentionally re-introducing a long-lived token literal into `.github/workflows/ci.yml` on a test branch causes the step to fail before any test job starts.
- **SC-006** (SC-6 from Epic — #458 regression guard): Starting KOSMOS with an empty `.env` fails within 100 ms with a single-line `stderr` message listing every missing required variable plus `docs/configuration.md`. Verified by `tests/config/test_guard.py` using `time.monotonic()`.
- **SC-007** (onboarding latency): A new contributor needs no more than one page of reading (`docs/configuration.md`) to know which variables to populate, where to source each credential, and what happens when they forget one. Verified by cold-reading the page during the Epic's code review.
- **SC-008** (rollback time): Reverting the Infisical migration to the prior GitHub Encrypted Secrets configuration takes no more than 15 minutes using the runbook in `docs/configuration.md`.

## Assumptions

- Infisical Cloud Free tier has sufficient headroom for (a) two projects (`kosmos-prod`, `kosmos-ci`), (b) the current ~10 `KOSMOS_*` and `LANGFUSE_*` secret count, and (c) the audit-log retention needed for a student portfolio project. If this assumption is violated during plan Phase 0, work halts per the stop conditions in the Lead prompt.
- The GitHub repository allows the Infisical OIDC provider to be registered as a trusted identity issuer (no GitHub-org-level policy blocks the `id-token: write` permission).
- The `.env` symlink in the working tree resolves to a readable file for local developers. CI does not use `.env` at all — secrets arrive exclusively via the Infisical action's environment injection.
- `KOSMOS_ENV` is the activation flag for conditional-required observability variables. Valid values: `dev` (default, observability optional), `ci` (observability required), `prod` (observability required). No other value is recognised; unknown values fall through to `dev` semantics.
- The 100 ms guard budget is a realistic soft SLO measured against Python 3.12 cold start; the guard itself is a pure-Python os.environ lookup with no I/O beyond the existing `.env` read.
- `pydantic-settings` remains the validation mechanism for typed config values. The guard is an additive boundary check, not a replacement for `pydantic-settings`.
- The canonical `KOSMOS_*` names defined by Epic #507 (`KOSMOS_KAKAO_API_KEY`, `KOSMOS_LOOKUP_TOPK`, `KOSMOS_NMC_FRESHNESS_MINUTES`) are authoritative for this registry. If #507 renames any of them before this Epic merges, the registry is updated in lockstep.
- The `LANGFUSE_*` prefix is the only permitted exception to the `KOSMOS_` hard rule. Any future vendor-SDK exception requires an explicit addition to the registry's exception list.
- Rotating credentials remains a manual operator action for this Epic; automated rotation is explicitly deferred.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Self-hosted Vault / 1Password Connect server** — over-engineering for a student-scale project; Infisical Cloud Free meets the need.
- **Production GitHub Environment with manual-approval gate** — the project has no production deployment surface at this phase; any future production gate is a separate infrastructure Epic.
- **Rewriting `src/kosmos/safety/`** — owned by a different Epic; the guard lives under `src/kosmos/config/` and must not reach into `safety/`.
- **Dockerfile / devcontainer secret wiring** — `docker/` and `.devcontainer/` are owned by Epic #467 (CI/CD & Prompt Registry) and are explicitly forbidden file surface for this Epic.
- **Log / trace-level secret redaction** — this Epic guarantees no secret value ever leaves the boundary; log-level redaction is an observability concern owned by Epic #501.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Automated secret rotation (Infisical-side scheduled rotation + alert on expiry) | Manual rotation is acceptable for a student project; automation adds non-trivial Infisical-plan cost and cron plumbing | Phase 3+ (post-MVP hardening) | #742 |
| LiteLLM-specific secrets (`KOSMOS_LITELLM_MASTER_KEY`, `KOSMOS_LLM_BASE_URL`, `KOSMOS_SESSION_TOKEN_BUDGET`, `KOSMOS_USER_DAILY_BUDGET_USD`, `KOSMOS_MAX_FAILED_TOOL_INVOCATIONS`, `KOSMOS_LLM_FALLBACK_ENABLED`) | Variables are not yet consumed by any `src/` code; adding rows now would violate the "registry mirrors reality" invariant | Epic #465 (LiteLLM proxy) | #465 |
| Observability secret wiring (`KOSMOS_OTEL_ENDPOINT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`) code paths | This Epic catalogues the names and marks them conditional-required; the actual observability code lives in #501 | Epic #501 (Observability) | #501 |
| `.github/workflows/docker.yml` and `shadow-eval.yml` Infisical migration | Explicit file-surface boundary set by the Lead; those workflows are owned by a parallel Epic | Epic #467 (CI/CD & Prompt Registry) | #467 |
| Conversion of `security.yml`, `sbom.yml`, `eval.yml`, `pr-lint.yml` to Infisical injection | Those workflows currently use no `KOSMOS_*` secrets, so migration is a no-op; revisit only if they acquire a secret need | Epic #467 follow-up | #743 |
| Deprecation removal of legacy `KOSMOS_API_KEY` global fallback | Removing the fallback requires a cross-tool refactor to eliminate any remaining caller; out of scope for a secrets/config Epic | Separate refactor Epic | #744 |
| Pre-commit hook (`gitleaks` / `ggshield`) for local secret scanning | Complements CI's `scripts/audit-secrets.sh` but requires installing and documenting a new developer tool | Phase 3+ (developer-experience Epic) | #745 |

## Defects Fixed in This Epic

Two pre-existing defects were discovered during spec research. They are explicitly in-scope because fixing them is cheaper than documenting a workaround, and leaving them would cause the post-merge audit to fail immediately.

| Defect | Current state | Correction | Covered by |
|--------|---------------|------------|------------|
| `.github/workflows/ci.yml` injects `KOSMOS_DATA_GO_KR_KEY`, but `src/kosmos/settings.py` and `src/kosmos/permissions/credentials.py` both read `KOSMOS_DATA_GO_KR_API_KEY` | Typo; placeholder value is never consumed by production code paths, so CI passed "by accident" | Rename the workflow env var to `KOSMOS_DATA_GO_KR_API_KEY` as part of the Infisical migration edit | FR-050, SC-001 |
| Epic #468 body claims a stale `KOSMOS_KAKAO_REST_KEY` reference lives in `docs/tool-adapters.md`, but `grep` finds the only hit at `docs/design/mvp-tools.md:642` | Registry body location error; the stale name survived because no audit existed | Rewrite `docs/design/mvp-tools.md:642` to the canonical `KOSMOS_KAKAO_API_KEY`; scan-and-replace any other documentation hit surfaced by the audit | FR-051, FR-052, SC-003 |

## Cross-Epic Contracts

| Epic | Relationship | Contract |
|------|--------------|----------|
| #458 (CLOSED, 2026-04-16) | Regression guard | User Story 1 + SC-006 exist specifically to prevent the "missing `KOSMOS_KAKAO_API_KEY` silently degrades tool calls" class of bug that consumed a day on #458 |
| #507 | Upstream name authority | Registry rows for `KOSMOS_KAKAO_API_KEY`, `KOSMOS_LOOKUP_TOPK`, `KOSMOS_NMC_FRESHNESS_MINUTES` MUST match the canonical names #507 defines. If #507 renames, this Epic updates in lockstep |
| #501 | Catalogue-only | This Epic catalogues `KOSMOS_OTEL_ENDPOINT`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY` as conditional-required; the consuming code and wiring live in #501 |
| #467 | File-surface boundary | `docker.yml`, `shadow-eval.yml`, `build-manifest` remain owned by #467. #468 touches only `ci.yml` |
| #465 | Forward extensibility | The registry schema (FR-016) MUST accommodate #465's six future LiteLLM variables by appending rows with no migration |

## Allowed and Forbidden File Surface

| Allowed (this Epic may create/edit) | Forbidden (owned by other Epics or not writable) |
|-------------------------------------|--------------------------------------------------|
| `src/kosmos/config/` (new module, including `guard.py`) | `.env` (symlink — absolute no-write) |
| `tests/config/` (new test package) | `docker/`, `.devcontainer/` (Epic #467) |
| `docs/configuration.md` (new) | `prompts/`, `src/kosmos/safety/` (other Epics) |
| `docs/tool-adapters.md` (typo fix only, if any `KOSMOS_KAKAO_REST_KEY` survives) | `.github/workflows/docker.yml`, `.github/workflows/shadow-eval.yml` (Epic #467) |
| `docs/design/mvp-tools.md:642` (FR-051 one-line rewrite) | Sibling worktrees `/Users/um-yunsang/KOSMOS-467`, `/Users/um-yunsang/KOSMOS-585`, `/Users/um-yunsang/KOSMOS-466` (parallel work) |
| `.env.example` (regenerate) | Any file containing a real secret value |
| `scripts/audit-secrets.sh` (new) | |
| `scripts/audit-env-registry.py` (new) | |
| `.github/workflows/ci.yml` (Infisical migration + FR-050 typo fix) | |

## References

- Infisical GitHub Actions docs: `https://infisical.com/docs/integrations/cicd/githubactions` — confirms OIDC federation with no bootstrap secret is supported.
- Doppler leak-remediation writeup: `https://www.doppler.com/blog/remove-hardcoded-secrets-github-actions` — argues for OIDC-style short-lived injection; aligns with FR-030.
- Snyk 2025 State of Secrets: `https://snyk.io/articles/state-of-secrets/` — 28.65 million new hardcoded secrets in public GitHub repos in 2025 (+34% YoY); 28% of leaks originate outside code repos (Slack, Jira, MCP configs). Motivates NFR-003 and FR-023.
- 12-Factor Config: `https://12factor.net/config` — "The twelve-factor app stores config in environment variables." Anchors FR-040.
- Memory: `feedback_env_check_first.md` (project memory file, 2026-04-16) — records the #458 root cause that motivates User Story 1.
- AGENTS.md § Hard rules — "Env vars prefixed `KOSMOS_`. Never commit `.env` or `secrets/`." — anchors FR-040, FR-042.
