# Feature Specification: CI/CD & Prompt Registry — Manifest + Shadow + uv Docker + Devcontainer

**Feature Branch**: `feat/467-cicd-prompt-registry`
**Created**: 2026-04-17
**Status**: Draft
**Input**: Epic #467 — translate sections A–F (uv Dockerfile, Devcontainer, Prompt Registry, Shadow-eval workflow, CI release manifest, Unified CI matrix) into a behaviour-preserving spec that externalises hard-coded LLM prompts, reproducibly builds and ships the platform image, and adds a CI-only shadow evaluation lane for prompt changes. First release milestone of the Claude Code harness migration that makes every deployment signed, reproducible, and shadow-tested before reaching citizens.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Reproducible platform image for release (Priority: P1)

A release engineer (currently the maintainer) needs to ship a KOSMOS build to a citizen-facing environment. They push a git tag, the CI pipeline builds a multi-stage image from `docker/Dockerfile`, publishes a machine-readable release manifest that pins the commit, lockfile hash, image digest, prompt hashes, LLM model id, and gateway proxy version, and the same image runs identically on the engineer's laptop and the deployment target.

**Why this priority**: Without a reproducible image and a release manifest, every claim about "what was deployed" is folklore. This user story is the minimum viable unit that makes a release auditable, and every later story (shadow-eval, prompt registry) depends on being able to point at a specific manifest row.

**Independent Test**: A test tag push on a throw-away branch produces a `docs/release-manifests/<sha>.yaml` with all six required fields populated, and `docker build -f docker/Dockerfile .` on a clean checkout produces an image whose digest matches the manifest entry.

**Acceptance Scenarios**:

1. **Given** a clean checkout on `main` at commit `<sha>`, **When** the release engineer runs `docker build -f docker/Dockerfile .`, **Then** the resulting image is ≤ 2 GB, its default user id is `1000` (non-root), and `uv sync --frozen` has been executed in the builder stage with no dev dependencies leaking into the runtime stage.
2. **Given** the release engineer pushes git tag `v0.X.Y`, **When** the release-manifest CI job completes, **Then** `docs/release-manifests/<commit_sha>.yaml` is committed on `main` with fields `commit_sha`, `uv_lock_hash`, `docker_digest`, `prompt_hashes` (keyed by `prompt_id`), `friendli_model_id`, and `litellm_proxy_version`.
3. **Given** a second engineer pulls the same commit and runs the same `docker build`, **When** they inspect the resulting image digest, **Then** it matches the `docker_digest` field in the manifest for that commit.

---

### User Story 2 — Externalise prompts so prompt changes are auditable (Priority: P1)

A prompt author (maintainer acting in that role) needs to update the LLM-facing system prompt, session guidance, or compaction template without touching Python source. They edit a markdown file under `prompts/`, regenerate `prompts/manifest.yaml`, and at startup the platform loads exactly those strings through a Prompt Registry. Every LLM call emits a span attribute that identifies which prompt version was used, so every log line is traceable back to a specific prompt file in the repo.

**Why this priority**: The current inline prompts in `src/kosmos/context/system_prompt.py` and `src/kosmos/context/session_compact.py` make it impossible to diff or attribute prompt changes. Externalising them is a prerequisite for the shadow-eval lane (Story 3) and for the observability contract with Epic #501.

**Independent Test**: A unit test loads all three prompts via the Prompt Registry, computes SHA-256 over each file, and asserts the hashes in `manifest.yaml` match. Tampering a single byte in any prompt file makes the test fail at load time (fail-closed). A second test verifies that current `SystemPromptAssembler` and `session_compact` output is byte-identical before and after the refactor when the content of `system_v1.md` / `session_guidance_v1.md` / `compact_v1.md` reproduces today's inline text.

**Acceptance Scenarios**:

1. **Given** the platform starts up, **When** the Prompt Registry boots, **Then** it reads `prompts/manifest.yaml`, opens each listed prompt file, computes SHA-256 over the file bytes, and refuses to start if any computed hash disagrees with the manifest entry.
2. **Given** a tester opens `prompts/system_v1.md` and inserts one extra character, **When** the platform starts, **Then** it fails to start with a clear error identifying the mismatching `prompt_id` and leaves no LLM call spans.
3. **Given** the platform makes any LLM call from the Context Assembly layer, **When** the span is emitted, **Then** it carries the attribute `kosmos.prompt.hash` whose value is the SHA-256 hex digest of the system prompt bytes actually sent to the model.
4. **Given** the operator sets `KOSMOS_PROMPT_REGISTRY_LANGFUSE=true` and provides Langfuse host + keys, **When** the Prompt Registry boots, **Then** it may additionally resolve prompts through Langfuse Prompt Management; **Given** the flag is unset or `false`, **When** the Prompt Registry boots, **Then** it reads exclusively from repository files with no network call.

---

### User Story 3 — Shadow-evaluate prompt changes before merge (Priority: P2)

A prompt author opens a pull request that modifies any file under `prompts/**`. The CI pipeline detects the path change, runs a small scripted prompt battery twice — once against the prompts in `main` and once against the prompts in the PR — records both result sets as OpenTelemetry spans tagged with `deployment.environment=main` and `deployment.environment=shadow` respectively, and attaches a JSON evaluation report as a PR artifact. No call reaches a live `data.go.kr` API.

**Why this priority**: Without a shadow lane, every prompt change is reviewed by eyeball only. This story makes prompt regressions visible as a structured diff rather than a vibes check, but it depends on Stories 1 (reproducible build) and 2 (prompt registry) being in place, so it is P2.

**Independent Test**: A PR that flips one phrase in `prompts/system_v1.md` triggers the `shadow-eval` workflow, which produces a workflow artifact containing both `deployment.environment=main` and `deployment.environment=shadow` span batches with identical battery inputs. The artifact is inspectable from the PR page.

**Acceptance Scenarios**:

1. **Given** a PR that touches no file under `prompts/**`, **When** CI runs, **Then** the `shadow-eval` job is skipped (path-filtered out).
2. **Given** a PR that modifies `prompts/system_v1.md`, **When** the `shadow-eval` job runs, **Then** it executes the fixed battery under both the merge-base prompts and the PR-head prompts, emits two OTEL span sets distinguished by `deployment.environment`, and uploads the evaluation JSON as a PR artifact.
3. **Given** the battery runs, **When** any tool call would hit a live `data.go.kr` endpoint, **Then** the run fails — the battery is restricted to fixtures and mocks under `tests/fixtures/` and MUST NOT make outbound calls outside the test network.

---

### User Story 4 — Reproducible development environment on first clone (Priority: P2)

A new contributor clones KOSMOS, opens it in VS Code with the Dev Containers extension, and the environment comes up with Python 3.12, `uv`, all dependencies synced, and the LiteLLM proxy + OTEL collector ports forwarded — no laptop-specific setup. Running `uv run pytest` succeeds on the first attempt.

**Why this priority**: Valuable for contributor onboarding and for guaranteeing that CI / local / devcontainer all execute against the same dependency tree, but not blocking for release (Story 1) or auditability (Story 2).

**Independent Test**: A devcontainer CI smoke job opens the repo inside a devcontainer image, runs `uv sync` and `uv run pytest --collect-only`, and completes green on first run without manual intervention.

**Acceptance Scenarios**:

1. **Given** a clean clone on a machine with Docker + Dev Containers extension, **When** the contributor selects "Reopen in Container", **Then** the container builds from `.devcontainer/devcontainer.json`, the `postCreateCommand` runs `uv sync`, and a shell lands in a working Python 3.12 + uv environment.
2. **Given** the devcontainer is running, **When** the contributor runs `uv run pytest -q`, **Then** the test suite collects and executes with no missing-dependency errors.
3. **Given** the contributor needs to reach the local LiteLLM proxy or OTEL collector, **When** those services run on their documented default ports, **Then** those ports are forwarded through the devcontainer configuration so the host IDE can attach.

---

### Edge Cases

- A prompt file exists on disk but is missing from `manifest.yaml` — the Prompt Registry MUST refuse to start with a clear error naming the orphan file (fail-closed on drift).
- `manifest.yaml` lists a `prompt_id` whose file is missing — MUST refuse to start naming the missing file.
- Two prompt entries share the same `prompt_id` — MUST refuse to start with a duplicate-id error.
- `KOSMOS_PROMPT_REGISTRY_LANGFUSE=true` is set but Langfuse host/keys are missing or unreachable — MUST fall back to repository files when the flag is unset; when the flag is set but Langfuse is unreachable, MUST fail-closed at startup, never silently serve stale or wrong prompts.
- Docker build produces an image > 2 GB — CI MUST fail with a clear size-budget violation rather than publishing the oversize image.
- Release tag pushed on a commit whose `uv.lock` has drifted from `pyproject.toml` — manifest job MUST fail before the manifest file is committed.
- Shadow-eval battery run hangs or exceeds its time budget — the workflow MUST time out and mark the shadow-eval as failed, but MUST NOT block unrelated CI jobs on the same PR.
- A PR modifies `prompts/manifest.yaml` without modifying any underlying prompt file — the Prompt Registry load test MUST still pass, confirming hashes in the manifest match the unchanged files.

## Requirements *(mandatory)*

<!-- Organised by Epic #467 section letter for traceability. -->

### Functional Requirements — Section A: uv multi-stage Dockerfile

- **FR-A01**: The repository MUST provide `docker/Dockerfile` that builds the runtime image in two stages: a builder stage that installs all Python dependencies via `uv sync --frozen`, and a runtime stage that receives only the resolved virtual environment and the application source.
- **FR-A02**: The runtime stage MUST run as a non-root user with UID `1000` by default (verifiable via `docker run --rm <image> id -u`).
- **FR-A03**: The base image MUST carry a licence compatible with Apache-2.0 redistribution (python:3.12-slim is maintained under the Python Software Foundation licence; if a distroless runtime is chosen it MUST be the Google `distroless/python3` image whose licence terms are documented in the Dockerfile header).
- **FR-A04**: The final runtime image size MUST be ≤ 2 GB, measured by `docker inspect -f '{{.Size}}'` on the final tag.
- **FR-A05**: The Dockerfile MUST NOT copy `.git`, `.venv`, `.pytest_cache`, `tests/`, `specs/`, `docs/`, or any file or directory listed in `.dockerignore` into the runtime stage.
- **FR-A06**: The Dockerfile MUST pin the uv version used in the builder stage by digest or version tag (not `latest`).

### Functional Requirements — Section B: Devcontainer

- **FR-B01**: The repository MUST provide `.devcontainer/devcontainer.json` that declares a Python 3.12 base (`mcr.microsoft.com/devcontainers/python:3.12`) and explicitly pulls in a uv feature (`ghcr.io/astral-sh/uv-devcontainer-feature` or equivalent).
- **FR-B02**: The devcontainer MUST run `uv sync` as its `postCreateCommand`, producing a ready-to-use `.venv`.
- **FR-B03**: The devcontainer MUST forward the ports used by the local LiteLLM proxy and the local OTEL collector (defaults documented in `docs/` alongside this Epic).
- **FR-B04**: The devcontainer MUST NOT require any host-side environment variable beyond those documented as standard in `.env.example`; secrets for Langfuse or FriendliAI remain user-supplied and never checked in.

### Functional Requirements — Section C: Prompt Registry

- **FR-C01**: The repository MUST contain, at the time of the first release following this Epic, the prompt files `prompts/system_v1.md`, `prompts/session_guidance_v1.md`, and `prompts/compact_v1.md`.
- **FR-C02**: The repository MUST contain `prompts/manifest.yaml` whose entries list, for each prompt, at minimum: `prompt_id` (stable string identifier), `version` (monotonically increasing integer), `sha256` (hex digest of file bytes), and `path` (relative to repository root).
- **FR-C03**: The platform MUST provide a Prompt Registry component (`PromptLoader`) that reads `manifest.yaml`, opens each referenced file, recomputes SHA-256 over the file bytes, and refuses to continue startup if any computed hash disagrees with the manifest entry.
- **FR-C04**: The Prompt Registry MUST return prompt strings as immutable values to callers; callers MUST NOT be able to mutate the loaded prompt text at runtime.
- **FR-C05**: `SystemPromptAssembler.assemble()` MUST obtain its system-identity, language-policy, tool-use-policy, personal-data-reminder, and session-guidance section text from the Prompt Registry, not from inline Python string literals.
- **FR-C06**: `session_compact` MUST obtain its summary header and section scaffolding from the Prompt Registry, not from inline Python string literals.
- **FR-C07**: The platform MUST emit the span attribute `kosmos.prompt.hash` on every LLM call made from the Context Assembly layer, whose value is the SHA-256 hex digest of the system prompt bytes actually sent to the model in that call.
- **FR-C08**: When the environment variable `KOSMOS_PROMPT_REGISTRY_LANGFUSE` is unset or equal to `false`, the Prompt Registry MUST resolve prompts exclusively from repository files and MUST NOT initiate any outbound network call.
- **FR-C09**: When `KOSMOS_PROMPT_REGISTRY_LANGFUSE=true`, the Prompt Registry MAY additionally resolve prompts through Langfuse Prompt Management using the supplied host and keys; if Langfuse is unreachable or returns an unknown `prompt_id`, the registry MUST fail-closed at startup rather than falling back to a possibly-stale repository copy without the operator's knowledge.
- **FR-C10**: The Prompt Registry MUST log an `INFO` record per resolved prompt listing `prompt_id`, `version`, and computed `sha256` at startup, using the stdlib `logging` module (no `print()`).

### Functional Requirements — Section D: Shadow-eval workflow

- **FR-D01**: The repository MUST provide `.github/workflows/shadow-eval.yml` triggered on `pull_request` events whose changed files include any path under `prompts/**`.
- **FR-D02**: The workflow MUST check out both the PR head and the merge-base, and run a fixed scripted battery — defined under `tests/shadow_eval/` or equivalent — once against each prompt set.
- **FR-D03**: The run against the merge-base prompts MUST emit OTEL spans carrying the attribute `deployment.environment=main`; the run against the PR-head prompts MUST emit spans carrying `deployment.environment=shadow`.
- **FR-D04**: The workflow MUST upload an aggregated evaluation artifact (JSON) attached to the workflow run, inspectable from the PR page, containing both span batches and any deterministic per-case scores the battery emits.
- **FR-D05**: The battery MUST NOT make any network call to `*.data.go.kr` or any other live government API; mock or fixture responses are mandatory (AGENTS.md hard rule).
- **FR-D06**: The workflow MUST complete or time out within a budget documented in the workflow YAML (default 15 minutes); on timeout the job MUST fail without blocking unrelated lint/test jobs.

### Functional Requirements — Section E: CI release manifest

- **FR-E01**: The repository MUST have a CI lane (job inside `ci.yml` or a dedicated `.github/workflows/release-manifest.yml`) triggered on release tag pushes matching the pattern `v*.*.*`.
- **FR-E02**: The lane MUST produce `docs/release-manifests/<commit_sha>.yaml` containing at minimum the fields: `commit_sha`, `uv_lock_hash` (SHA-256 of `uv.lock`), `docker_digest` (the digest of the image built from `docker/Dockerfile` for this commit), `prompt_hashes` (mapping from `prompt_id` to sha256 hex, covering every entry in `prompts/manifest.yaml`), `friendli_model_id` (the pinned model identifier in use), and `litellm_proxy_version` (the gateway proxy version).
- **FR-E03**: The lane MUST commit the generated manifest back to `main` in a machine-authored commit whose message identifies the release tag and the commit sha.
- **FR-E04**: If `uv.lock` has drifted from `pyproject.toml` at manifest time (i.e., `uv sync --frozen` would produce a different set of packages), the lane MUST fail before writing any manifest file.
- **FR-E05**: The manifest file MUST be valid YAML conforming to a schema documented alongside this Epic; `/speckit.plan` Phase 1 will produce `specs/026-cicd-prompt-registry/contracts/release-manifest.schema.json`.

### Functional Requirements — Section F: Unified CI matrix

- **FR-F01**: `.github/workflows/ci.yml` MUST continue to run the existing lint (ruff + mypy), test (Python 3.12 + 3.13 matrix with coverage), and dead-code (vulture) jobs unchanged, preserving the current coverage gate (≥ 80 %).
- **FR-F02**: `.github/workflows/ci.yml` MUST additionally orchestrate a `docker-build` job that runs `docker build -f docker/Dockerfile .` on pushes to `main` and on pull requests modifying `docker/**`, `pyproject.toml`, or `uv.lock`.
- **FR-F03**: The `shadow-eval` job (FR-D01…D06) MUST be wired into the unified workflow graph so its status is visible on the PR checks panel but does not block unrelated lint/test jobs when it fails due to infrastructure rather than evaluation regression.
- **FR-F04**: The `build-manifest` job (FR-E01…E05) MUST only run on tag pushes matching `v*.*.*`.
- **FR-F05**: All new jobs MUST follow AGENTS.md rules: no live `data.go.kr` calls, stdlib `logging` only in any Python helpers, no `print()` outside CLI layer helpers, no new top-level runtime dependency introduced without a spec-driven PR.

### Cross-cutting Functional Requirements — Refactor surface

- **FR-X01**: After the refactor, `SystemPromptAssembler.assemble()` MUST return a string that is byte-identical to the current (pre-refactor) output when `system_v1.md` and `session_guidance_v1.md` contain the current inline text. Golden-file tests MUST cover this invariant.
- **FR-X02**: After the refactor, `session_compact` MUST preserve its current rule-based summary structure (user intents, tool calls, tool results, assistant decisions sections) unchanged; only the header and fixed section labels come from `compact_v1.md`.
- **FR-X03**: The session-guidance prompt (`session_guidance_v1.md`) MUST update the concrete worked example to reference the frozen MVP facade (`resolve_location`) rather than the legacy `address_to_region` currently embedded at `src/kosmos/context/system_prompt.py:124-128`. This is an intentional content change delivered as part of v1 and is therefore NOT covered by the byte-identical invariant in FR-X01; a separate fixture captures the v1 expected text.

### Non-Functional Requirements

- **NFR-01 (Reproducibility)**: Given identical commit sha and clean build environment, `docker build` MUST produce an image with the same digest across two independent CI runs (after accounting for documented non-determinism sources — e.g., mtime — which the Dockerfile MUST neutralise with `SOURCE_DATE_EPOCH` or equivalent where applicable).
- **NFR-02 (Licence)**: Every image layer's base MUST be Apache-2.0-compatible; the Dockerfile MUST include a comment header listing the base image's upstream licence (e.g., PSF licence for `python:3.12-slim`).
- **NFR-03 (Secrets hygiene)**: No secret value, API key, JWT, or credential MUST ever be baked into a published image layer or committed to `docs/release-manifests/`. All secret-bearing values enter at runtime through environment variables.
- **NFR-04 (CI isolation)**: CI jobs MUST NOT reach `*.data.go.kr` or any external public API. Tests marked `@pytest.mark.live` MUST remain deselected in CI (existing rule in `pyproject.toml`).
- **NFR-05 (Source-text language)**: All source-file text (Python, YAML, Dockerfile, docs) MUST be in English; Korean text is allowed only inside prompt body content (`prompts/*.md`) and inside Korean domain fixture data (existing exception).
- **NFR-06 (Logging)**: Any new Python module (Prompt Registry, shadow-eval helpers) MUST use the stdlib `logging` module only; no `print()` calls outside `src/kosmos/cli/**`.
- **NFR-07 (Pydantic v2)**: Any new Python model for manifest parsing or prompt metadata MUST use Pydantic v2 with `frozen=True`; no `typing.Any`.

### Key Entities

- **Dockerfile (`docker/Dockerfile`)**: The two-stage build description that produces the runtime image; referenced by `docker_digest` in the release manifest.
- **Devcontainer config (`.devcontainer/devcontainer.json`)**: The VS Code Dev Containers configuration that defines the contributor environment.
- **Prompt file (`prompts/<id>_v<N>.md`)**: Plain markdown holding LLM-facing prompt text. Versioned by suffix; immutable once released.
- **Prompt manifest (`prompts/manifest.yaml`)**: Registry of prompt entries. Each entry: `prompt_id`, `version`, `sha256`, `path`.
- **PromptLoader**: Runtime component that reads the manifest, verifies SHA-256 integrity, and serves immutable prompt strings to the Context Assembly layer.
- **Release manifest (`docs/release-manifests/<sha>.yaml`)**: One file per release commit, carrying `commit_sha`, `uv_lock_hash`, `docker_digest`, `prompt_hashes`, `friendli_model_id`, `litellm_proxy_version`.
- **Shadow-eval battery (`tests/shadow_eval/`)**: Fixed set of fixture-backed scenarios that exercise the platform twice per PR — once with `main` prompts, once with PR-head prompts — and compare results.
- **Span attribute `kosmos.prompt.hash`**: Observability contract produced by this Epic and consumed by Epic #501.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `docker build -f docker/Dockerfile .` on a clean checkout at the tip of `main` produces an image whose size reported by `docker inspect` is ≤ 2 GB and whose default user id reported by `docker run --rm <image> id -u` equals `1000`. Verification: one-shot command sequence run in CI and documented in `docs/` alongside this Epic.
- **SC-002**: A new contributor opening the repository in VS Code with the Dev Containers extension and issuing `uv run pytest -q` succeeds on the first attempt with no manual environment setup. Verification: a devcontainer CI smoke job executes this flow non-interactively and completes green.
- **SC-003**: All three runtime prompts (`system_v1`, `session_guidance_v1`, `compact_v1`) are loaded by the Prompt Registry at startup with SHA-256 integrity verification. Verification: a unit test that flips one byte in any of the three files and asserts the Prompt Registry refuses to start with a clear error message naming the tampered file.
- **SC-004**: `SystemPromptAssembler.assemble()` and `session_compact()` produce byte-identical output before and after the refactor when called with the same config, assuming the v1 prompt files reproduce current inline text (except for the documented session-guidance facade correction in FR-X03, which is captured by a separate v1 fixture). Verification: golden-file equivalence tests in `tests/context/`.
- **SC-005**: The shadow-eval workflow runs on pull requests that modify `prompts/**` and emits both `deployment.environment=main` and `deployment.environment=shadow` span batches. Verification: a dry-run PR that nudges a prompt file triggers the workflow; the uploaded JSON artifact shows two span sets with the required `deployment.environment` values and identical battery input ids.
- **SC-006**: A release tag push generates `docs/release-manifests/<sha>.yaml` containing all six required fields (`commit_sha`, `uv_lock_hash`, `docker_digest`, `prompt_hashes`, `friendli_model_id`, `litellm_proxy_version`). Verification: a dry-run tag push triggers the workflow; the generated YAML validates against the schema produced in `/speckit.plan` Phase 1.
- **SC-007**: The span attribute `kosmos.prompt.hash` is emitted on every LLM call originating from the Context Assembly layer. Verification: an OTEL span-inspection test under `tests/observability/` that runs a minimal Context Assembly → LLMClient path with a mock transport and asserts the attribute presence and correctness on every recorded span.

## Assumptions

- `uv` is the sole Python dependency manager; `requirements.txt`, `setup.py`, and `Pipfile` are explicitly forbidden by AGENTS.md and are not introduced by this Epic.
- Python 3.12 is the baseline runtime; the CI test matrix additionally covers 3.13 for forward compatibility, but the published Docker image targets 3.12 exclusively.
- The release engineer and the prompt author are (for this Epic) the same maintainer; no multi-tenant secrets model is required.
- `ghcr.io/umyunsang` is assumed to be the container image registry; GHCR access from GitHub Actions is expected to use the built-in `GITHUB_TOKEN` / OIDC path unless clarification resolves otherwise.
- FriendliAI Serverless remains the LLM provider and K-EXAONE the primary model; the model identifier string travels in the manifest as `friendli_model_id`.
- The LiteLLM Proxy image digest becomes authoritative only after Epic #465 ships; until then, `litellm_proxy_version` carries the placeholder string `"unknown"` and downstream consumers treat this as explicitly unpinned.
- Epic #507 is merged; the MVP facade (`lookup`, `resolve_location`) is frozen and referenced by the v1 session-guidance prompt.
- The maintainer runs Docker Desktop (or equivalent) locally for Story 1 and Story 4 verification.
- No secrets ever enter `docs/release-manifests/`; every field in the manifest is non-sensitive metadata suitable for public commit history.

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- Multi-registry publishing (e.g., Docker Hub + GHCR + ECR) — KOSMOS targets a single registry for the foreseeable future.
- Mobile or native desktop packaging — KOSMOS is a terminal platform; there is no desktop app artifact to sign.
- SLSA Level 3+ provenance generation — this Epic provides commit-sha / lock-hash / digest pinning sufficient for student-portfolio auditability; full SLSA provenance is not a KOSMOS goal.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Cosign keyless image signing and verification gate | Not listed in Epic #467 scope; signing infrastructure adds complexity (Fulcio, Rekor) that is not required for the first reproducible-build milestone | Follow-up Security/Supply-chain Epic | #723 |
| Langfuse rate-limit-aware throttling for shadow-eval workflow | Depends on observed free-tier rate-limit semantics once Langfuse integration is enabled; premature to design throttling before real usage data exists | Future Observability hardening Epic | #724 |
| Automated SBOM generation (SPDX 2.3 / CycloneDX 1.6) and divergence gate integration into the release manifest | Spec 024 introduced the SBOM workflow scaffold; wiring the SBOM hash into `docs/release-manifests/<sha>.yaml` is complementary but not required for SC-006 | Epic #524 (SBOM automation) or successor | #725 |
| Prompt A/B rollout controller (serve N % of traffic with prompt version X) | Requires runtime traffic-split infrastructure that does not yet exist; shadow-eval covers pre-merge validation only | Future Context Assembly Epic | #726 |
| Devcontainer-as-CI-runner (running the full CI matrix inside the devcontainer image to guarantee parity) | Nice-to-have parity check; adds CI minutes without proportional value at current scale | Future DX Epic | #727 |
| Canary deployment harness (progressive rollout from shadow → 1 % → 100 %) | Out of scope for a student-portfolio single-environment deployment; no second production surface exists yet | Phase 2+ deployment Epic | #728 |

## Dependencies / Integration

### Upstream (this Epic depends on)

- **Epic #507 (CLOSED)**: The MVP facade (`lookup` + `resolve_location`) is frozen; `prompts/session_guidance_v1.md` references it directly in the worked example (FR-X03).
- **Epic #021 (merged)**: OpenTelemetry GenAI v1.40 semantic conventions are in place; `kosmos.prompt.hash` extends the existing span schema without reshaping it.
- **Current `pyproject.toml`**: The Python 3.12+ / uv / pydantic v2 stack is already established — no new top-level runtime dependencies are added by this Epic (Langfuse client integration is gated behind the optional flag `KOSMOS_PROMPT_REGISTRY_LANGFUSE` and, if required, enters as an optional extras dependency in the `dev` or a new `langfuse` extra, never as a default runtime dep).

### Downstream (this Epic produces)

- **Epic #501 (OPEN)**: This Epic emits the span attribute `kosmos.prompt.hash` that #501 consumes. The attribute key and its semantic (SHA-256 hex of the system prompt bytes actually sent to the model) are the normative contract; #501 MUST NOT require a different key or a different hashing algorithm.
- **Epic #468 (OPEN)**: The env registry does not yet exist. This Epic **proposes** the following candidate env keys for #468 to formalise in its canonical registry:
  - `KOSMOS_PROMPT_REGISTRY_LANGFUSE` — boolean, default `false`.
  - `KOSMOS_LANGFUSE_HOST` — URL, required when the flag is `true`.
  - `KOSMOS_LANGFUSE_PUBLIC_KEY` — string, required when the flag is `true`.
  - `KOSMOS_LANGFUSE_SECRET_KEY` — secret, required when the flag is `true`.
  - `GHCR_TOKEN` — token, supplied by GitHub Actions OIDC at CI time, never at runtime.
  Until #468 merges, these keys are considered tentative and MAY be renamed by #468 without breaking the observable behaviour described above.
- **Epic #465 (OPEN)**: The release manifest carries a `litellm_proxy_version` field. Until #465 provides the canonical LiteLLM Proxy image digest, this field carries the placeholder string `"unknown"`. Once #465 merges, the `build-manifest` job will populate it from a documented source; the manifest schema remains stable.

### Cross-worktree boundary

- This Epic's spec, plan, tasks, and implementation MUST stay inside the worktree at `/Users/um-yunsang/KOSMOS-467`. It MUST NOT edit files tracked by the parallel worktrees `KOSMOS-468`, `KOSMOS-585`, or `KOSMOS-466`.

## Open Clarifications

The following three points are the only [NEEDS CLARIFICATION] markers allowed by the Epic #467 brief; every other ambiguous decision has been resolved with an informed default documented in Assumptions.

- [NEEDS CLARIFICATION: Langfuse free-tier rate-limit semantics — when shadow-eval fires on many PRs in the same hour against the same Langfuse project, does the free tier throttle or reject requests, and if so does the workflow need explicit client-side throttling to avoid failing the shadow-eval lane on busy days?]
- [NEEDS CLARIFICATION: ghcr.io/umyunsang organisation permissions — does the repository's default `GITHUB_TOKEN` + OIDC path grant write access to the `ghcr.io/umyunsang/*` namespace, or is an explicit organisation-level permission grant / PAT required? This determines whether `GHCR_TOKEN` is needed as a separate secret or whether `GITHUB_TOKEN` suffices.]
- [NEEDS CLARIFICATION — deferred, not blocking: Cosign keyless image signing. The Epic scope does not list cosign; this marker records that the question was considered and explicitly deferred to a follow-up Security/Supply-chain Epic per the Deferred Items table. Treat as informational; it does NOT block `/speckit.clarify` or `/speckit.plan`.]
