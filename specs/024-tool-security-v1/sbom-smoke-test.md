# SBOM Workflow Smoke-Test Procedure

**Spec**: 024-tool-security-v1  
**Workflow file**: `.github/workflows/sbom.yml`  
**FR reference**: FR-017 (dual-format SBOM), FR-019 (build-gate-on-divergence)  
**SC reference**: SC-005 (zero-manual-step reproducibility)

---

## 1. Prerequisites

### 1.1 Install syft

Option A — Homebrew (macOS):

```bash
brew install syft
syft version  # expect: Application:          syft
               #          Version:             0.x.x
```

Option B — upstream install script (Linux / macOS):

```bash
curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin
syft version
```

### 1.2 Python + uv

Confirm the repo baseline is satisfied:

```bash
python3 --version  # must be 3.12+
uv --version       # any recent version
uv sync --frozen --all-extras --dev
```

### 1.3 jq

Required for the divergence gate normalization:

```bash
jq --version  # 1.6+; install via brew install jq or apt-get install jq
```

---

## 2. Happy-Path Procedure

Run syft once per format against the repository root, then inspect schema markers
to confirm correct format versions.

### 2.1 Generate SPDX 2.3 JSON

```bash
cd /path/to/KOSMOS  # substitute the actual clone path

syft . \
  --output spdx-json=sbom-spdx-smoke.json \
  --source-name kosmos
```

Verify SPDX 2.3 schema markers:

```bash
# spdxVersion must be "SPDX-2.3"
jq -r '.spdxVersion' sbom-spdx-smoke.json
# expected: SPDX-2.3

# documentNamespace must be a non-empty URI
jq -r '.documentNamespace' sbom-spdx-smoke.json
# expected: https://... (non-empty)

# package count
jq '.packages | length' sbom-spdx-smoke.json
# expected: >= 1 (pyproject.toml dependencies present)

# byte count (record for divergence baseline)
wc -c sbom-spdx-smoke.json
```

### 2.2 Generate CycloneDX 1.6 JSON

```bash
syft . \
  --output cyclonedx-json=sbom-cdx-smoke.json \
  --source-name kosmos
```

Verify CycloneDX 1.6 schema markers:

```bash
# specVersion must be "1.6"
jq -r '.specVersion' sbom-cdx-smoke.json
# expected: 1.6

# serialNumber must be a non-empty urn:uuid:
jq -r '.serialNumber' sbom-cdx-smoke.json
# expected: urn:uuid:...

# component count
jq '.components | length' sbom-cdx-smoke.json
# expected: >= 1

# byte count
wc -c sbom-cdx-smoke.json
```

---

## 3. Divergence-Injection Procedure

This procedure confirms that the FR-019 gate would fail when the SBOM content
differs between runs. Two injection methods are provided.

### Method A — Different --source-name (lightest)

Run syft a second time with a modified `--source-name` to force a change in the
SBOM document metadata:

```bash
syft . \
  --output spdx-json=sbom-spdx-injected.json \
  --source-name kosmos-MODIFIED
```

Now simulate the gate normalization and diff:

```bash
strip_spdx() {
  jq 'del(
    .creationInfo.created,
    .documentNamespace,
    .SPDXID
  )' "$1"
}

diff \
  <(strip_spdx sbom-spdx-smoke.json) \
  <(strip_spdx sbom-spdx-injected.json)
```

Expected outcome: `diff` exits non-zero because `--source-name` affects the
`name` field in the SPDX document, which is NOT stripped by the normalization.
The gate script would print:

```
ERROR: SPDX 2.3 SBOM diverged between runs (FR-019).
       Regenerate with a deliberate lockfile change and a reviewer note.
```

and exit with code 1.

### Method B — Temporary file injection (stronger)

Add a temporary Python file to force a new package entry in the SBOM, then
re-run syft:

```bash
echo "# divergence-probe" > src/kosmos/_divergence_probe_tmp.py

syft . \
  --output spdx-json=sbom-spdx-injected.json \
  --source-name kosmos

# Clean up immediately
rm src/kosmos/_divergence_probe_tmp.py
```

Run the normalized diff as shown in Method A. The new file path will appear in
run 2's package list but not run 1's, producing a non-empty diff and a non-zero
exit.

### 3.1 CycloneDX divergence injection

Apply the same `--source-name kosmos-MODIFIED` approach for CycloneDX:

```bash
syft . \
  --output cyclonedx-json=sbom-cdx-injected.json \
  --source-name kosmos-MODIFIED

strip_cdx() {
  jq 'del(
    .metadata.timestamp,
    .serialNumber,
    .metadata.tools
  )' "$1"
}

diff \
  <(strip_cdx sbom-cdx-smoke.json) \
  <(strip_cdx sbom-cdx-injected.json)
```

Expected outcome: non-zero diff exit; gate would block artifact upload.

---

## 4. Expected FR-019 Gate Outcome

When the normalized diff between run 1 and run 2 is non-empty:

- The `Divergence gate` step exits with code 1.
- The GitHub Actions job status becomes `failure`.
- The `Promote final SBOM artifacts`, `Upload SPDX 2.3 SBOM artifact`, and
  `Upload CycloneDX 1.6 SBOM artifact` steps are skipped (all are sequential
  after the gate step with no `if: always()` override).
- No artifacts are uploaded to the Actions run.
- The error message printed to the job log identifies the failing format and
  references FR-019.

Recovery path: update `uv.lock` via `uv sync`, re-run the workflow, and include
a reviewer note in the PR body citing the reason for the SBOM change.

---

## 5. CI Invocation Notes

### 5.1 Trigger the workflow manually after the PR lands on main

```bash
gh workflow run sbom.yml --repo umyunsang/KOSMOS
```

Or target a specific ref:

```bash
gh workflow run sbom.yml --repo umyunsang/KOSMOS --ref main
```

### 5.2 Watch the run live

```bash
gh run list --workflow=sbom.yml --repo umyunsang/KOSMOS --limit 5

# Get the run ID from the list, then:
gh run watch <RUN_ID> --repo umyunsang/KOSMOS
```

### 5.3 Expected green run shape

A passing run shows these steps in order under the `generate-sbom` job:

1. Checkout repository
2. Set up uv
3. Install dependencies (lockfile authoritative)
4. Generate SPDX 2.3 SBOM (run 1)
5. Generate CycloneDX 1.6 SBOM (run 1)
6. Generate SPDX 2.3 SBOM (run 2 - divergence detection)
7. Generate CycloneDX 1.6 SBOM (run 2 - divergence detection)
8. Divergence gate - SPDX (FR-019) -> prints "SPDX divergence gate: PASS"
9. Divergence gate - CycloneDX (FR-019) -> prints "CycloneDX divergence gate: PASS"
10. Promote final SBOM artifacts
11. Upload SPDX 2.3 SBOM artifact
12. Upload CycloneDX 1.6 SBOM artifact
13. Sign SBOM (stub) -> prints the TODO comment line

### 5.4 Locate artifacts

In the Actions tab, open the passing run. Under the "Artifacts" section at the
bottom of the summary page, two artifacts appear:

- `sbom-spdx.json` (retention: 90 days)
- `sbom-cyclonedx.json` (retention: 90 days)

Download via UI or CLI:

```bash
gh run download <RUN_ID> --repo umyunsang/KOSMOS --name sbom-spdx.json
gh run download <RUN_ID> --repo umyunsang/KOSMOS --name sbom-cyclonedx.json
```

### 5.5 Pull-request path filter

The workflow triggers on PRs that touch any of:

- `pyproject.toml`
- `uv.lock`
- `.github/workflows/sbom.yml`

It does NOT trigger on PRs touching only application source. This is by design
per T023: SBOM regeneration is dependency-change-gated.

---

## 6. Deferred Items

### 6.1 Signing (PS.3) — stub only

The final workflow step (`Sign SBOM (stub)`) is a documented placeholder only.
It echoes a `TODO(spec 024 §3.8)` message and performs no actual signing.

Full PS.3 signing via sigstore cosign and Rekor transparency-log attestation is
explicitly deferred to a follow-up epic. Per `research.md §3.8`:

> Sigstore/cosign integration requires a CI OIDC identity provider (GitHub Actions
> OIDC is available) and a Rekor instance (public or private). This is a separate
> infrastructure epic beyond the scope of spec 024.

The stub step is intentional: it serves as a reminder marker for the follow-up
epic and ensures the signing step appears in the correct sequence position in
the pipeline once the infrastructure lands.

Before any ministry-pilot launch, a follow-up issue must be opened under Epic
#612 to implement actual cosign sign-blob calls and Rekor attestation uploads.
The permissions block will require `id-token: write` once signing is activated.

### 6.2 SLSA L3 gap

FR-018 calls for a SLSA L3 gap analysis (current-to-target). That analysis is
documented in `docs/security/tool-template-security-spec-v1.md §Supply chain &
provenance` (T024), not enforced by this workflow. SLSA L3 provenance attestation
(via slsa-github-generator) is a separate effort.

### 6.3 SHA pinning for action versions

The workflow currently uses semver tag pins (`@v4`, `@v0`). For SLSA L3
compliance, every `uses:` line should be pinned to a full commit SHA with a
semver comment alongside it. This hardening is deferred to the signing epic.
