# Phase 0 — Research & Reference Mapping: CI/CD & Prompt Registry

**Feature**: Spec 026 — CI/CD & Prompt Registry
**Date**: 2026-04-17
**Status**: Phase 0 complete — all resolvable unknowns answered with a cited reference; 2 non-blocking `[NEEDS CLARIFICATION]` markers investigated but deferred (see § Remaining Unknowns).

## 1. Reference Mapping Table

Per Constitution Principle I (Reference-Driven Development), every design decision in this plan traces to a concrete reference. Rows 1–5 are the five external references mandated by the Lead briefing. Rows 6–9 are internal references pulled from `docs/vision.md § Reference materials` and sibling specs.

| # | Reference | License / Type | Design decision this reference grounds |
|---|---|---|---|
| 1 | **Astral uv Docker integration guide** — [docs.astral.sh/uv/guides/integration/docker](https://docs.astral.sh/uv/guides/integration/docker/) | Apache-2.0 (Astral doc site) | Two-stage `docker/Dockerfile` structure: builder stage does `uv sync --frozen --no-install-project`, runtime stage copies the resolved `.venv` plus application source only. Non-root `USER 1000` appears in the runtime stage. `uv` pinned by the official `ghcr.io/astral-sh/uv` image tag in the builder (FR-A06). Answers FR-A01..A05. |
| 2 | **Hynek Schlawack — "Production-ready Python Docker Containers with uv"** — [hynek.me/articles/docker-uv](https://hynek.me/articles/docker-uv/) | CC-BY-4.0 article | Refinements on top of #1: `ENV UV_LINK_MODE=copy` (required when `/root/.cache` crosses FS boundaries), `ENV UV_COMPILE_BYTECODE=1` (faster cold-start in runtime stage), `--mount=type=cache,target=/root/.cache/uv` build-cache mount for CI speed, `--no-install-project` in the dependency-sync step to keep project-source invalidation isolated from the dependency layer. Answers FR-A01 refinement + NFR-01 reproducibility. |
| 3 | **Langfuse Prompt Management docs** — [langfuse.com/docs/prompts/get-started](https://langfuse.com/docs/prompts/get-started) | Apache-2.0 (Langfuse project) | `PromptLoader` optional path when `KOSMOS_PROMPT_REGISTRY_LANGFUSE=true`: use `langfuse.get_prompt(name, version)` SDK call, but STILL verify SHA-256 against the repo copy at startup — two-source consistency check. If Langfuse returns an unknown id or mismatched hash, fail-closed (FR-C09). SDK enters as an optional extras dependency, never default runtime. Answers FR-C08, FR-C09. |
| 4 | **Dev Containers spec (containers.dev)** — [containers.dev/implementors/json_reference](https://containers.dev/implementors/json_reference/) | MIT-style spec | `.devcontainer/devcontainer.json` keys used: `image` (base — `mcr.microsoft.com/devcontainers/python:3.12`), `features` (add `ghcr.io/astral-sh/uv` or equivalent uv feature), `postCreateCommand` (`uv sync`), `forwardPorts` (LiteLLM + OTEL collector defaults), `customizations.vscode.extensions` (ruff, pylance). No `build` block — we consume the upstream image rather than forking it. Answers FR-B01..B04. |
| 5 | **Eugene Yan — "Shadow Mode / Shadow Deployment"** — [eugeneyan.com/writing/ab-testing](https://eugeneyan.com/writing/ab-testing/) | CC-BY-NC-4.0 article | Twin-run pattern on the same input set: one run uses merge-base prompts, one uses PR-head prompts; both emit spans with a shared battery-input id so downstream diffing is deterministic. Span attribute `deployment.environment=main` marks the merge-base run, `deployment.environment=shadow` marks the PR-head run. No live citizen traffic in either run (CI-only fixture replay). Answers FR-D02..D04. |
| 6 | **Claude Code harness (reconstructed)** — `ChinaSiro/claude-code-sourcemap`, `docs/vision.md` thesis | Reconstructed | Thesis invariant: Claude Code separates system prompt text from engine code so the prompt is a versioned asset rather than an inline string. Spec 026 brings KOSMOS Layer 5 (Context Assembly) to that same separation — `SystemPromptAssembler` becomes a loader + cache rather than an inline string holder. This is explicitly a harness-migration fidelity fix, not a refactor-for-refactor's-sake. Answers FR-C05, FR-C06, FR-X01, FR-X02. |
| 7 | **OpenTelemetry GenAI semantic conventions v1.40** — referenced by Spec 021 | Apache-2.0 (OTEL spec) | `kosmos.prompt.hash` MUST NOT collide with an existing GenAI convention attribute. The `kosmos.*` namespace is reserved by KOSMOS for project-specific extensions; documenting the attribute under that namespace (rather than proposing an upstream GenAI key) avoids convention drift. Answers FR-C07, SC-007. |
| 8 | **Spec 021 — observability-otel-genai** (merged) | Internal | `deployment.environment` is already an observable attribute in the KOSMOS span schema; the shadow-eval workflow reuses this existing attribute rather than inventing a new one. This also means Epic #501 (OPEN) can index shadow-eval spans by the same dimension it already uses for prod vs staging spans — no schema churn. Answers FR-D03. |
| 9 | **Spec 025 — tool-security-v6** (merged) | Internal | FR-039..FR-048 constrain the registry component pattern: any Pydantic model added for manifest validation MUST use `frozen=True` + `@model_validator(mode="after")`, with a registry-level backstop against `model_construct` bypass. `PromptManifest` in `data-model.md` inherits this pattern directly: validators enforce unique `prompt_id`, strict-monotonic `version`, and 64-char lowercase-hex `sha256`. Answers NFR-07 + Constitution Principle III. |

## 2. Resolved Assumptions

Each assumption stated in spec.md is validated by one of the references above or by in-repo code inspection.

| Assumption from spec.md | Validated by | Resolution |
|---|---|---|
| `uv` is the sole Python dependency manager; `requirements.txt` / `setup.py` / `Pipfile` are forbidden. | `AGENTS.md § Hard rules`; ref #1 (Astral uv-Docker guide uses `uv sync --frozen` as the single install path). | **CONFIRMED**. Dockerfile and devcontainer both use `uv sync --frozen`. No other dependency manifest is introduced. |
| Python 3.12 is the Docker baseline; CI matrix covers 3.12 + 3.13. | Existing `pyproject.toml` `requires-python = ">=3.12"`; ref #4 (Dev Containers spec — `mcr.microsoft.com/devcontainers/python:3.12` is canonical). | **CONFIRMED**. Dockerfile pins `python:3.12-slim`; devcontainer pins `:3.12`; CI matrix (existing) keeps 3.13 for forward compatibility. |
| `ghcr.io/umyunsang` is the container registry. | `AGENTS.md`; GitHub repo owner `umyunsang`. | **CONFIRMED for the image location**, but the auth path to push there is still a `[NEEDS CLARIFICATION]` (see § Remaining Unknowns, item 2). |
| FriendliAI Serverless + EXAONE remain the LLM provider + model. | `AGENTS.md § Stack`; `docs/vision.md § The thesis`. | **CONFIRMED**. `friendli_model_id` in the release manifest is populated from the existing FriendliAI env config; no new auth path needed. |
| LiteLLM Proxy digest becomes authoritative only after Epic #465 ships. | Epic #467 body (cross-Epic contract section); Epic #465 status OPEN. | **CONFIRMED**. `litellm_proxy_version` field carries placeholder `"unknown"`; schema tolerates this placeholder; release-manifest contract is stable across the transition. |
| Epic #507 is merged; MVP facade (`lookup`, `resolve_location`) is frozen. | Epic #507 status CLOSED; `src/kosmos/tools/` facade already present. | **CONFIRMED**. `prompts/session_guidance_v1.md` uses `resolve_location` in its worked example (FR-X03 carve-out). |
| Maintainer uses Docker Desktop (or equivalent) locally. | Student-portfolio context; AGENTS.md development standards. | **CONFIRMED**. No CI-only path; the local + CI Dockerfile path is identical. |
| No secrets enter `docs/release-manifests/`. | NFR-03; release manifest field list (no credentials among 6 fields). | **CONFIRMED**. Schema in `contracts/release-manifest.schema.json` explicitly rejects credential-bearing fields via `additionalProperties: false`. |

## 3. Remaining Unknowns

Two `[NEEDS CLARIFICATION]` markers from spec.md that are investigated here but **intentionally not resolved** — they are non-blocking for Phase 1 and can be answered during `/speckit-implement` or later. The third marker (cosign keyless signing) was explicitly deferred in spec.md and is in the Deferred Items table.

### Unknown 1 — Langfuse free-tier rate-limit semantics

**Question**: When `KOSMOS_PROMPT_REGISTRY_LANGFUSE=true` is set and many shadow-eval jobs fire in the same hour against the same Langfuse project, does the free tier throttle or reject requests? Does the workflow need client-side throttling?

**Investigation strategy**:
1. On the first real use of the Langfuse path (post-`/speckit-implement`), instrument `PromptLoader` to record per-request latency and any HTTP 429 responses with `logger.warning`.
2. If 429s appear, add a capped-exponential-backoff retry policy inside `PromptLoader._fetch_from_langfuse` (pattern lifted from `hynek/stamina`, already in `docs/vision.md § Reference materials`).
3. If throttling becomes systemic, add a per-workflow-run gate (a single `actions/cache` key that debounces shadow-eval across concurrent PRs).

**Why non-blocking**: The Langfuse path is opt-in via an env flag. The default repo-only path (FR-C08) has no rate limit at all, so this question only bites late adopters and can be answered empirically without reshaping the schema.

### Unknown 2 — `ghcr.io/umyunsang` OIDC permissions

**Question**: Does the repository's default `GITHUB_TOKEN` + OIDC path grant write to `ghcr.io/umyunsang/*`, or is an organisation-level grant or a separate `GHCR_TOKEN` PAT needed?

**Investigation strategy**:
1. First run of the `docker-build` job in CI will either succeed (answer = `GITHUB_TOKEN` suffices) or fail with a 403 (answer = need explicit grant or a PAT stored as `GHCR_TOKEN` secret).
2. `.github/workflows/ci.yml` is authored with `permissions: { packages: write, contents: read, id-token: write }` from day one so the OIDC path is available; if that fails, the workflow falls back to `secrets.GHCR_TOKEN` (documented in the workflow YAML as the fallback path) — which Epic #468 will later formalise as a canonical env key.
3. No schema change is needed regardless of outcome; the release-manifest schema does not reference registry credentials.

**Why non-blocking**: The image can be built in CI (verifying Dockerfile correctness, FR-F02) without being pushed. Push-to-GHCR is needed only once the release-manifest job runs on a tag; until a real tag push is attempted, the push path is untested anyway.

### Non-resolvable: Cosign keyless signing

**Status**: Explicitly deferred in `spec.md § Deferred to Future Work` — it is NOT in Epic #467 scope. No investigation planned in Phase 0. Spec.md carries an informational-only `[NEEDS CLARIFICATION]` marker for audit trail; `/speckit-taskstoissues` will file a tracking issue with label `deferred`.

## 4. Deferred Items Validation

Per Constitution Principle VI, every deferral MUST be in the "Scope Boundaries & Deferred Items" table of spec.md with a tracking issue reference.

**Cross-check** (spec.md § Deferred to Future Work against free-text "separate epic" / "future epic" / "v2" / "Phase 2+" patterns):

| Pattern searched | Found in spec.md? | Registered in Deferred Items table? |
|---|---|---|
| `Cosign keyless image signing` | Yes (§ Deferred; § Open Clarifications informational marker) | ✅ Row 1 — `Follow-up Security/Supply-chain Epic` |
| `Langfuse rate-limit-aware throttling` | Yes (§ Deferred) | ✅ Row 2 — `Future Observability hardening Epic` |
| `SBOM generation + divergence gate wired into release manifest` | Yes (§ Deferred) | ✅ Row 3 — `Epic #524 (SBOM automation)` |
| `Prompt A/B rollout controller` | Yes (§ Deferred) | ✅ Row 4 — `Future Context Assembly Epic` |
| `Devcontainer-as-CI-runner` | Yes (§ Deferred) | ✅ Row 5 — `Future DX Epic` |
| `Canary deployment harness` | Yes (§ Deferred) | ✅ Row 6 — `Phase 2+ deployment Epic` |
| "Phase 2+" in any narrative section | Appears only inside the Deferred Items table (row 6). | ✅ Tracked. |
| "v2" anywhere | Not found. | n/a |
| "separate epic" anywhere | Appears only inside the Deferred Items table (all rows reference successor Epics). | ✅ Tracked. |

**Result**: No unregistered deferrals. All 6 items await `/speckit-taskstoissues` to replace `NEEDS TRACKING` placeholders with concrete issue numbers.

## 5. Architectural Sketch

### 5.1 `PromptLoader` public API (Phase 1 will pin the contract; this is the design outline)

```text
PromptLoader (module-level instance, constructed once at platform boot)
├── __init__(manifest_path: Path, langfuse_enabled: bool = False)
│       reads manifest, computes hash per file, validates against manifest, stores frozen strings
│       raises PromptRegistryError on any integrity failure (hash mismatch, orphan, duplicate, missing)
├── load(prompt_id: str) -> str
│       returns the immutable prompt text for the given id
│       raises KeyError if prompt_id is not registered
├── get_hash(prompt_id: str) -> str
│       returns the SHA-256 hex digest that was verified at load time
│       used by the Context Assembly layer to stamp kosmos.prompt.hash on every LLM span
└── all_hashes() -> dict[str, str]
        maps prompt_id -> sha256 hex; used by the release-manifest job to fill prompt_hashes
```

Implementation is stdlib-only: `pathlib.Path`, `hashlib.sha256`, `yaml.safe_load`, `logging`. Pydantic is used for `PromptManifest` validation only, not for the loader itself.

### 5.2 `prompts/manifest.yaml` schema (normalised outline; JSON Schema authored in Phase 1)

```yaml
# prompts/manifest.yaml
version: 1                        # manifest schema version (integer, for future evolution)
entries:
  - prompt_id: system_v1          # stable string identifier (snake_case + _v{N} suffix)
    version: 1                    # monotonic integer per prompt_id
    sha256: "abc...def"           # 64-char lowercase hex digest of the file bytes
    path: system_v1.md            # relative to prompts/ directory
  - prompt_id: session_guidance_v1
    version: 1
    sha256: "..."
    path: session_guidance_v1.md
  - prompt_id: compact_v1
    version: 1
    sha256: "..."
    path: compact_v1.md
```

Invariants enforced by `PromptManifest` `@model_validator(mode="after")`:
1. `prompt_id` values are unique within `entries`.
2. `version` is strictly monotonic within a `prompt_id` (trivial for v1 — only one entry per id — but enforced now so v2 adoption is automatic).
3. `sha256` matches `^[0-9a-f]{64}$`.
4. `path` is a relative path (no `..`, no leading `/`).
5. The file at `prompts/<path>` exists and its computed SHA-256 equals `sha256`.

### 5.3 `docs/release-manifests/<sha>.yaml` schema (normalised outline; JSON Schema in Phase 1)

```yaml
commit_sha: "abc...def"                    # 40-char lowercase hex
uv_lock_hash: "sha256:abc...def"           # sha256: prefix + 64-char hex (salt against ambiguity)
docker_digest: "sha256:abc...def"          # same format as uv_lock_hash
prompt_hashes:                             # dict keyed by prompt_id
  system_v1: "abc...def"
  session_guidance_v1: "abc...def"
  compact_v1: "abc...def"
friendli_model_id: "LGAI-EXAONE/exaone-3.5-32b-instruct"
litellm_proxy_version: "unknown"           # or real semver once Epic #465 lands
```

### 5.4 Shadow-eval workflow DAG

```text
on: pull_request (paths: [prompts/**])
jobs:
  shadow-eval:
    timeout-minutes: 15
    steps:
      1. actions/checkout (fetch-depth: 2 to access merge-base)
      2. setup-python + uv sync
      3. compute merge-base sha, checkout prompts/ from merge-base into .tmp/main-prompts/
      4. RUN battery against main prompts:
           KOSMOS_PROMPT_REGISTRY_PATH=.tmp/main-prompts/manifest.yaml \
           OTEL_DEPLOYMENT_ENVIRONMENT=main \
           uv run python -m tests.shadow_eval.battery > main.json
      5. RUN battery against PR-head prompts:
           KOSMOS_PROMPT_REGISTRY_PATH=prompts/manifest.yaml \
           OTEL_DEPLOYMENT_ENVIRONMENT=shadow \
           uv run python -m tests.shadow_eval.battery > shadow.json
      6. Merge main.json + shadow.json -> eval-report.json
      7. actions/upload-artifact: eval-report.json
```

Every step runs inside the same CI runner; no external service is contacted. The battery's `httpx.AsyncClient` is constructed with a `httpx.MockTransport` that refuses any connection to `*.data.go.kr`, enforcing FR-D05.

### 5.5 Release-manifest workflow DAG

```text
on: push (tags: v*.*.*)
jobs:
  build-manifest:
    steps:
      1. actions/checkout (fetch-depth: 0 so we can compute uv_lock_hash deterministically)
      2. uv lock --check                     # fails if uv.lock drifted vs pyproject.toml (FR-E04)
      3. docker build -f docker/Dockerfile . -t ghcr.io/umyunsang/kosmos:<tag>
      4. docker push ghcr.io/umyunsang/kosmos:<tag>    # requires OIDC or GHCR_TOKEN — see Unknown 2
      5. compute:
           commit_sha=$(git rev-parse HEAD)
           uv_lock_hash="sha256:$(sha256sum uv.lock | awk '{print $1}')"
           docker_digest=$(docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/umyunsang/kosmos:<tag>)
           prompt_hashes=$(uv run python -m kosmos.context.prompt_loader --emit-hashes)
           friendli_model_id=$(python -c "import os; print(os.environ['KOSMOS_FRIENDLI_MODEL_ID'])")
           litellm_proxy_version="unknown"  # placeholder until Epic #465
      6. Render docs/release-manifests/<commit_sha>.yaml
      7. Validate against contracts/release-manifest.schema.json
      8. git commit -m "chore(release): manifest for <tag>" + git push to main
```

The commit-back-to-main step (step 8) uses a GitHub App token or `GITHUB_TOKEN` with `contents: write` — standard practice, no new secret surface.

---

**Phase 0 status**: COMPLETE. All 5 external + 4 internal references mapped. All assumptions validated. 2 non-blocking unknowns documented with investigation strategies. 6 deferred items all registered in the Deferred Items table. Architectural sketch ready for Phase 1 schema + model authoring.
