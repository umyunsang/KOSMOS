# Contract — `scripts/audit-secrets.sh`

**Purpose**: Block re-introduction of long-lived GitHub Encrypted Secrets into workflow files. Runs as a CI pre-step and locally via `make lint` / `uv run pytest`-adjacent hooks.
**Related FR**: FR-024, FR-025, FR-030 · **SC**: SC-001, SC-005

---

## CLI

```
usage: scripts/audit-secrets.sh [--workflow-dir .github/workflows]

POSIX-compliant bash (requires bash 4+); no dependencies beyond `grep`, `awk`,
`sed`, and `find` available on Ubuntu CI runners and macOS developer laptops.

Exit codes:
  0  no forbidden patterns found in scanned workflows.
  1  one or more forbidden patterns found (violation report on stderr).
  2  scan error (workflow dir missing, unreadable file).
```

POSIX-portable. Written to pass `shellcheck -x` with zero warnings.

## Scan scope

- **In-scope**: `.github/workflows/ci.yml` (and, by default, any sibling `.yml` explicitly listed in `_SCANNED_FILES` inside the script).
- **Out-of-scope** (owned by #467): `.github/workflows/docker.yml`, `.github/workflows/shadow-eval.yml`, `.github/workflows/build-manifest.yml`. Script MUST NOT scan these files even if present.

## Forbidden patterns (denylist)

A line in an in-scope workflow triggers a violation if it matches **any** of:

1. `\${{ *secrets\.[A-Z_]+_TOKEN *}}` — any GitHub Encrypted Secret named `*_TOKEN`.
2. `\${{ *secrets\.[A-Z_]+_API_KEY *}}` — any `*_API_KEY` secret.
3. `\${{ *secrets\.[A-Z_]+_SECRET *}}` — any `*_SECRET` secret.
4. `\${{ *secrets\.KOSMOS_[A-Z_]+ *}}` — any `KOSMOS_*` secret reference (long-lived token by definition).
5. `\${{ *secrets\.FRIENDLI[A-Z_]* *}}` — legacy `FRIENDLI_*` token references.
6. `\${{ *secrets\.LANGFUSE_[A-Z_]+ *}}` — Langfuse secrets (must come via Infisical, not GH Secrets).

## Allowed exceptions (allowlist)

The following `${{ secrets.* }}` references are permitted in in-scope workflows:

1. `${{ secrets.GITHUB_TOKEN }}` — GitHub-issued, short-lived, scoped-to-workflow. Not a long-lived token.
2. `${{ secrets.INFISICAL_CLIENT_ID }}` — **ONLY if** paired with `oidc-audience` and no `INFISICAL_CLIENT_SECRET`; this is a public identifier, not a secret. Prefer `vars.INFISICAL_CLIENT_ID` (see `contracts/ci-workflow.md`).

The allowlist is encoded as literal string checks; any addition requires a PR that updates this contract.

## False-positive suppression

- Lines inside YAML block comments (starting with `#`) are skipped.
- Lines inside `uses:` entries (action references) are skipped — action names can contain the substring `token` without being secret references.

## Output format (violation report, stderr)

```
audit-secrets: FORBIDDEN pattern in .github/workflows/ci.yml:42:
  ${{ secrets.FRIENDLI_TOKEN }}
  → Long-lived GH Encrypted Secret. Move to Infisical + OIDC. See
    docs/configuration.md#infisical-migration
audit-secrets: 1 violation(s) found.
```

Multiple violations → one block per violation, summary count last.

## Exit codes

| Code | Meaning |
|------|---------|
| `0` | Clean. |
| `1` | One or more denylist matches (not allowlisted). |
| `2` | Scan error (e.g., `.github/workflows/` missing, unreadable file). |

## Determinism

- Violation lines MUST be sorted by `(file, line_number)` ascending.
- Same input workflow → identical output byte-for-byte.
- No timestamps in the output (no `generated_at`).

## Test matrix

| Test ID | Input (workflow content) | Expected |
|---------|--------------------------|----------|
| T-AS01 | Contains `${{ secrets.GITHUB_TOKEN }}` only | exit 0 |
| T-AS02 | Contains `${{ secrets.FRIENDLI_TOKEN }}` | exit 1, violation reported |
| T-AS03 | Contains `${{ secrets.KOSMOS_KAKAO_API_KEY }}` | exit 1 |
| T-AS04 | Contains YAML comment `# secrets.FOO_TOKEN` | exit 0 (comment suppression) |
| T-AS05 | Contains `uses: some/action@v1-token-helper` | exit 0 (uses-line suppression) |
| T-AS06 | `.github/workflows/` missing | exit 2 |
| T-AS07 | Contains only `${{ vars.INFISICAL_CLIENT_ID }}` | exit 0 (not a `secrets.` reference) |
| T-AS08 | Contains `${{ secrets.INFISICAL_CLIENT_SECRET }}` | exit 1 (denied — retains bootstrap secret) |

## CI integration

Invoked as a pre-test gate (see `contracts/ci-workflow.md`):

```yaml
- name: Secrets audit
  run: ./scripts/audit-secrets.sh
```

Non-zero exit fails the CI job before any test runs.

## Maintenance

- Additions to the denylist = spec change + PR.
- Additions to the allowlist = spec change + PR + security review (cite justification in PR body).
- Script header MUST include `# SPDX-License-Identifier: Apache-2.0` and a one-sentence purpose comment.

## Non-goals

- Not a git-history scanner (TruffleHog/Gitleaks territory).
- Not a generic secret-entropy detector. Denylist is pattern-based and deliberate.
- Doesn't scan `src/` or `docs/` — those are the env-registry audit's job.
