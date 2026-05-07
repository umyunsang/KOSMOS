# ADR-008: kosax-plugin-store GitHub Organization + Vendored slsa-verifier

**Status**: Accepted
**Date**: 2026-04-26
**Epic**: #1636 (P5 Plugin DX 5-tier)
**Affected**: External GitHub repos (`kosax-plugin-store/*`) · `~/.kosax/vendor/slsa-verifier/` · `scripts/bootstrap_slsa_verifier.sh` · `src/kosax/plugins/slsa.py` · `src/kosax/plugins/installer.py`

## Context

Spec 1636 P5 ships a 5-tier plugin DX. Two architectural decisions
required dedicated ADR coverage because they affect external repos
+ host-side filesystem vendor paths:

1. **Where do example plugin repos live?** Migration tree § B8 mandates
   "Tier 3 examples" but does not specify the GitHub home. Options:
   `umyunsang/<name>` (lead's personal namespace), `umyunsang/kosax-plugin-<name>`
   (subdir convention in lead's namespace), or a dedicated org.
2. **How does the host verify SLSA v1.0 provenance?** Spec 1636 R-3
   pins `slsa-framework/slsa-verifier` for verification; the Go binary
   is ~10 MB and not part of any pip-installable package.

These two decisions land together because the slsa-verifier's
`--source-uri` flag asserts a GitHub-org-level prefix — the org name
is part of the verification contract, not just packaging.

## Decision

### R-2 → standalone repos under `kosax-plugin-store/`

Plugin repos live in a dedicated GitHub organization
`kosax-plugin-store` (free public org, created 2026-04-26 via web UI).
Naming convention: `kosax-plugin-store/kosax-plugin-<name>` where
`<name>` matches `^[a-z][a-z0-9-]*$`.

Six initial repos:

| Repo | Role |
|---|---|
| `kosax-plugin-store/kosax-plugin-template` | Tier 1 scaffold (`is_template: true`) |
| `kosax-plugin-store/kosax-plugin-seoul-subway` | Tier 3 Live example |
| `kosax-plugin-store/kosax-plugin-post-office` | Tier 3 Live example |
| `kosax-plugin-store/kosax-plugin-nts-homtax` | Tier 3 Mock example |
| `kosax-plugin-store/kosax-plugin-nhis-check` | Tier 3 Mock example |
| `kosax-plugin-store/index` | Tier 5 catalog index |

### R-3 → vendored slsa-verifier under `~/.kosax/vendor/`

`slsa-verifier` Go binary is downloaded on first install via
`scripts/bootstrap_slsa_verifier.sh` into
`$KOSAX_PLUGIN_VENDOR_ROOT/slsa-verifier/<platform>-<arch>/slsa-verifier`
(default `~/.kosax/vendor/`). Platform matrix supported:
darwin-amd64, darwin-arm64, linux-amd64, linux-arm64. Pin: v2.6.0
(latest stable as of 2026-04-26).

The host's `kosax.plugins.slsa.verify_artifact()` shells out via
`subprocess.run([str(binary), "verify-artifact", ...])` with:

- argv list (no shell, no string interpolation).
- 60-second bounded timeout.
- structured `SLSAFailureKind` enum classification of failure modes
  (PROVENANCE_NOT_SIGNED / SOURCE_URI_MISMATCH / BINARY_NOT_FOUND /
  TIMEOUT / UNKNOWN).

`KOSAX_PLUGIN_SLSA_SKIP=1` environment variable opt-in dev override
(per Spec 1636 contract); production CI rejects this flag (deferred
enforcement).

## Rationale

### R-2 standalone repos

- **Source-URI semantics**: SLSA v1.0 provenance attestations bind
  to a single GitHub-org-level source URI. A dedicated org gives a
  predictable URI prefix `github.com/kosax-plugin-store/kosax-plugin-<name>`
  that the verifier asserts against. Mixing plugins into
  `umyunsang/*` would force per-plugin source URI patterns and
  weaken the trust anchor.

- **Discoverability**: GitHub's "Use this template" button + repo
  naming convention makes new contributors clone a known-good
  template under a known-good org.

- **Future delegation**: When KOSAX scales to multiple maintainers,
  org-level access controls (admin / maintainer / read) become the
  natural delegation surface. Personal namespace would require
  org-conversion later (lossy).

- **Cost**: GitHub free orgs allow unlimited public repos. Zero
  monetary cost. Org creation is one-time + web-UI only (CLI
  cannot create free orgs).

### R-3 vendored slsa-verifier

- **No-pip constraint**: AGENTS.md hard rule "Never add a runtime
  dependency outside a spec-driven PR" + "no Go" — but slsa-verifier
  IS Go. Vendoring resolves this: the binary is downloaded at
  install-time, not bundled with KOSAX source.

- **Platform safety**: Bootstrap script downloads the matching binary
  on first plugin install. Host code in `kosax.plugins.slsa` returns
  a structured `BINARY_NOT_FOUND` failure pointing the citizen at
  the bootstrap script — no silent fallback.

- **Reproducibility**: Pinned version (v2.6.0) keeps verification
  semantics stable. Bootstrap script accepts `--version` override
  for future upgrades; binary path is platform-prefixed so multiple
  versions can co-exist.

- **Audit trail**: Each install writes the slsa-verifier exit code
  + stderr_tail to the consent receipt's `slsa_verification` field
  (`passed` / `failed` / `skipped`). Forensic reconstruction works
  even after the bundle cache is cleared.

## Alternatives considered

### R-2 alternatives

- **`umyunsang/kosax-plugin-<name>` (personal namespace)** —
  Rejected. SLSA source URI semantics + future delegation.
- **Monorepo `umyunsang/kosax-plugins/<name>`** — Rejected. SLSA
  provenance is per-repo; monorepo would attach a single attestation
  to the entire tree, weakening per-plugin trust. Independent
  versioning + release cadence per plugin also become painful.
- **Pure registry (no GitHub repos)** — Rejected. Loses GitHub's
  "Use this template" UX + the audit trail of plugin source code
  alongside its provenance.

### R-3 alternatives

- **Pure-Python SLSA verifier** — Rejected. No mature
  Python-native implementation as of 2026-04. `python-tuf` exists
  but does not cover the slsa-framework provenance schema.
- **JavaScript verifier (`@slsa-framework/slsa-verifier-action`)** —
  Rejected. Couples KOSAX install path to Node.js, which the host
  does not require for non-TUI usage.
- **Skip SLSA verification entirely** — Rejected. Plugin install is
  a citizen-trust decision; cryptographic provenance is the only
  defense against typo-squatting + supply-chain attacks. The
  `KOSAX_PLUGIN_SLSA_SKIP=1` dev escape hatch documents itself
  in the consent receipt.
- **Bundle slsa-verifier into the KOSAX wheel** — Rejected. ~10 MB
  per-platform Go binary inflates the Python package; vendoring
  on first-install matches the 「no Go」 spirit while keeping the
  binary available where needed.

## Consequences

### Positive

- Each `kosax-plugin-store/<repo>` has a SLSA-verifiable source
  URI baked into the verifier's `--source-uri` flag.
- New contributors clone via "Use this template" button + 일관된 naming.
- Org admin (lead) can grant write access to maintainers without
  exposing the lead's personal namespace.
- Vendored verifier path is overridable via `KOSAX_PLUGIN_VENDOR_ROOT`
  for dev / CI scenarios.

### Negative

- Free org cannot be created via `gh` CLI (`user` OAuth scope
  required and not in our token). One-time web-UI step blocks
  initial bootstrap until done.
- Future fork of KOSAX must create their own org or fork the
  plugin-store org — coupling between fork and plugin ecosystem.
- Bootstrap script downloads binary on first run — first install is
  slower than subsequent. CI runners cache the binary across jobs
  via `actions/cache` (deferred — currently re-download per run).

### Neutral

- `kosax-plugin-store` namespace is reserved on GitHub but does
  not affect other namespaces. Naming collision risk: 0 (검색 결과
  본 epic 시점에 다른 점유자 없음).

## Implementation evidence

- **R-2 created** (2026-04-26):
  - <https://github.com/kosax-plugin-store/kosax-plugin-template>
  - <https://github.com/kosax-plugin-store/kosax-plugin-seoul-subway>
  - <https://github.com/kosax-plugin-store/kosax-plugin-post-office>
  - <https://github.com/kosax-plugin-store/kosax-plugin-nts-homtax>
  - <https://github.com/kosax-plugin-store/kosax-plugin-nhis-check>
  - <https://github.com/kosax-plugin-store/index>

- **R-3 implemented**:
  - `scripts/bootstrap_slsa_verifier.sh` (T063) — vendor download.
  - `src/kosax/plugins/slsa.py` (T011) — verify_artifact wrapper.
  - `src/kosax/plugins/installer.py` (T014) — phase 3 SLSA.
  - `src/kosax/plugins/tests/test_installer_slsa.py` (T011) — 8 tests
    covering all 5 SLSAFailureKind branches via shell stub.

## Future work (not in scope)

- **Org transfer**: If the lead transfers maintenance, the org is
  transferable via GitHub's org-admin flow. SLSA source URIs may
  need re-issuing (deferred — first transfer triggers).
- **Drift audit**: Workflow that walks every published plugin's
  manifest hash + verifies `acknowledgment_sha256` against the
  current canonical hash (#1926, deferred).
- **CI cache**: GitHub Actions cache slsa-verifier binary between
  jobs (currently re-downloads) — minor optimization.
