# Release Packaging Deep Research

Date: 2026-05-07

Status: Evidence package for the npm + Homebrew release path. PyPI research was
completed earlier, but PyPI/backend publication is removed from the active
v0.1.0 plan.

Scope:

- TypeScript/Bun TUI plus Python backend source distribution through npm.
- Homebrew tap packaging based on the npm tarball.
- CI/CD, provenance, SBOM, package-size, install-smoke, and LLMOps release
  evidence.

## Executive Findings

1. UMMAYA should not use long-lived npm tokens for normal final release. npm and
   OpenSSF guidance now converge on OIDC-based Trusted Publishing. UMMAYA
   already uses Infisical OIDC federation as a CI secret broker, so Infisical
   should be reused for Homebrew tap credentials and break-glass fallback only.
2. The npm package must be a deliberate CLI package, not an accidental publish
   of `tui/`. A root package with `bin/ummaya`, `files`, package-content gates,
   provenance, and clean global install smoke matches current agentic CLI
   practice better than publishing a private workspace package.
3. UMMAYA currently needs a source-distributed Bun package because bundling the
   TUI still exposes stale dead imports from the reconstructed Claude Code tree.
   The npm package therefore includes the TUI source, backend source,
   `pyproject.toml`, and `uv.lock`, and the wrapper launches the backend with
   `uv --directory <package-root>`.
4. Homebrew should follow the npm artifact. The tap repository exists, but
   Homebrew has no central reservation mechanism for third-party formula names.
   The formula should install from a stable npm registry tarball and pass
   formula syntax, audit, install, and `test do` checks after the tap update.
5. LLMOps packaging evidence should be release metadata, not another runtime
   framework. UMMAYA already has prompt hashes, eval scenarios, OpenTelemetry,
   optional Langfuse integration, and release manifests. Packaging should bind
   these into release notes and artifact evidence.

## Local Baseline

Name and registry checks as of 2026-05-07:

| Surface | Result |
|---|---|
| npm `ummaya` | `npm view ummaya version` returned 404. |
| Homebrew core formula/cask `ummaya` | API checks returned 404. |
| GitHub tap | `umyunsang/homebrew-ummaya` exists. This secures the tap path, not Homebrew core. |

npm package state after implementation:

- Root `package.json` is named `ummaya`, version `0.1.0`.
- `bin/ummaya` is executable and requires Bun `>=1.3.0`.
- `files` allowlist includes only the npm wrapper, TUI runtime source, Python
  backend source, prompts, and canonical plugin-validation runtime files.
- `scripts/check-npm-package.mjs` enforces content, size, and entry-count gates.
- Local dry-run result:
  - compressed size: 9,938,016 bytes
  - unpacked size: 34,545,264 bytes
  - entry count: 2,331
- Clean global install smoke passed for `ummaya --version`.

Homebrew state after implementation:

- `scripts/render-homebrew-formula.mjs` renders `Formula/ummaya.rb` from version
  and npm tarball SHA-256.
- `ruby -c Formula/ummaya.rb` passed locally.
- Local Homebrew 5.1.9 disallows path-based `brew audit [path]`; full audit/test
  must run after the formula is committed to the tap.
- Bun is not available as a Homebrew core formula on this machine, so the
  formula depends on `oven-sh/bun/bun` and docs instruct users to tap
  `oven-sh/bun` first.

Existing CI/release infrastructure:

- `.github/workflows/ci.yml` covers uv sync, Python checks, tests, Docker build,
  and related gates.
- `.github/workflows/ci.yml` already fetches CI secrets from Infisical through
  GitHub OIDC federation (`Infisical/secrets-action` plus
  `vars.INFISICAL_CLIENT_ID`).
- `.github/workflows/release-manifest.yml` emits prompt hashes and a release
  manifest on `v*.*.*` tags.
- `.github/workflows/security.yml` runs CodeQL, TruffleHog, pip-audit, and
  license checks.

## Ecosystem Benchmarks

Agentic npm CLI packages checked on 2026-05-07:

| Package | Version | CLI bin | Unpacked size |
|---|---:|---|---:|
| `@openai/codex` | `0.128.0` | `codex -> bin/codex.js` | 12,855 bytes |
| `@anthropic-ai/claude-code` | `2.1.132` | `claude -> bin/claude.exe` | 131,959 bytes |
| `@google/gemini-cli` | `0.41.2` | `gemini -> bundle/gemini.js` | 112,783,793 bytes |
| `opencode-ai` | `1.14.40` | `opencode -> bin/opencode` | 8,961 bytes |
| local UMMAYA npm tarball | `0.1.0` | `ummaya -> bin/ummaya` | 34,545,264 bytes |

Insight: agentic CLIs split into two patterns. Some packages publish tiny
launcher shims that fetch or execute a platform binary. Others publish a large,
bundled JavaScript CLI. UMMAYA is currently between those patterns: source
distributed for v0.1.0, with a future bundled/native TUI artifact as the likely
next packaging hardening step.

## Official Guidance Digest

npm:

- npm refuses to publish when `private` is true.
- npm recommends `npm pack --dry-run` to inspect package contents.
- `files` is the correct allowlist mechanism for publish content.
- `bin` is the correct field for globally installed CLI commands.
- npm Trusted Publishing uses OIDC, requires npm CLI 11.5.1+ and Node 22.14.0+,
  and automatically generates provenance for public packages from public
  repositories.

Homebrew:

- A tap maps `brew tap owner/name` to
  `https://github.com/owner/homebrew-name`.
- New Homebrew formulae should use stable, tagged versions and pass
  `brew audit --new --formula` or the current equivalent for a tapped formula.
- Formula tests should exercise deterministic basic behavior. If credentials
  are needed, the preferred pattern is to verify controlled unauthenticated
  behavior rather than calling live APIs.

Supply chain:

- GitHub artifact attestations can establish where and how release artifacts
  were built and can also attest SBOMs.
- GitHub's current attestation action for new workflows is `actions/attest`,
  which generates SLSA provenance by default when given `subject-path`.
- SLSA provenance and `slsa-verifier` remain relevant for tamper-evident
  artifacts, but GitHub artifact attestations are the simplest first step for
  npm tarballs and release SBOMs.

LLMOps:

- OpenTelemetry GenAI semantic conventions are still marked Development, so
  UMMAYA should record the exact convention version or opt-in mode it emits.
- Langfuse, MLflow GenAI, W&B Weave, and Arize Phoenix all converge on release
  evidence needs: traces, prompt management, evaluations, datasets,
  experiments, and OpenTelemetry interoperability.
- For UMMAYA, release evidence should include prompt manifest hashes, scenario
  dataset checksums, eval scorecard paths, and trace correlation keys.

## UMMAYA Packaging Direction

Recommended order:

1. npm package first.
2. Homebrew formula second, generated from the npm tarball.
3. PyPI/backend package later only if the product surface requires standalone
   Python distribution.

Recommended install story:

| User need | Preferred install |
|---|---|
| General CLI | `npm install -g ummaya` |
| macOS one-command install | `brew tap oven-sh/bun && brew tap umyunsang/ummaya && brew install ummaya` |
| Source checkout | `uv sync --frozen --all-extras --dev`, then `cd tui && bun install --frozen-lockfile` |

Recommended release gates:

- Token gate: no npm/PyPI token in repo, workflow, logs, or local publish path.
- Secret-broker gate: reuse Infisical OIDC for Homebrew tap token and
  break-glass fallback; do not add GitHub encrypted registry tokens.
- npm gate: `npm pack --dry-run --json`, `bin` smoke, content allowlist,
  package-size budgets, no test/source-only files unless explicitly accepted.
- Homebrew gate: formula syntax, formula audit, formula test, stable URL,
  SHA-256, and no live government API calls.
- Supply-chain gate: SBOM upload, artifact attestation, release manifest,
  prompt hash emission, and optional SLSA provenance verification.
- LLMOps gate: eval scenario checksum and trace/eval scorecard attached to the
  release notes.

## Source Links

- npm package.json: <https://docs.npmjs.com/cli/v11/configuring-npm/package-json/>
- npm publish and package files: <https://docs.npmjs.com/cli/v11/commands/npm-publish/>
- npm Trusted Publishing: <https://docs.npmjs.com/trusted-publishers/>
- npm provenance: <https://docs.npmjs.com/generating-provenance-statements/>
- Homebrew taps: <https://docs.brew.sh/Taps>
- Homebrew Formula Cookbook: <https://docs.brew.sh/Formula-Cookbook>
- Homebrew Node formula guidance: <https://docs.brew.sh/Node-for-Formula-Authors>
- GitHub artifact attestations: <https://docs.github.com/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds>
- OpenSSF Trusted Publishers: <https://repos.openssf.org/trusted-publishers-for-all-package-repositories.html>
- OpenTelemetry GenAI semantic conventions: <https://opentelemetry.io/docs/specs/semconv/gen-ai/>
- Langfuse docs: <https://langfuse.com/docs>
- MLflow GenAI docs: <https://mlflow.org/docs/latest/genai/>
- Arize Phoenix docs: <https://arize.com/docs/phoenix>
- W&B Weave docs: <https://docs.wandb.ai/weave>
- Local Infisical runbook: `docs/configuration.md#infisical-operator-runbook`
