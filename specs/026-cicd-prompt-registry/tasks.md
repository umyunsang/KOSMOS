# Tasks: CI/CD & Prompt Registry (Spec 026 — Epic #467)

**Feature directory**: `specs/026-cicd-prompt-registry/`
**Branch**: `feat/467-cicd-prompt-registry`
**Worktree**: `/Users/um-yunsang/KOSMOS-467`
**Generated from**: spec.md (FR-A01..F05, NFR-01..07, SC-001..007), plan.md, research.md, data-model.md, contracts/*.schema.json, quickstart.md.

## Conventions

- `[P]` = parallelisable within the same phase (touches a file no other `[P]` task in the phase touches).
- `[USn]` = maps to User Story `n` in spec.md (US1 release image, US2 externalised prompts, US3 shadow-eval, US4 devcontainer). Absent = cross-cutting.
- Every implementation task is blocked by its matching Phase 3.2 test task (TDD mandatory).
- All source text English. Korean permitted only inside prompt body content (`prompts/*.md`).
- `uv` only — no `requirements.txt`, `setup.py`, or `Pipfile`.
- Stdlib `logging` only in any new Python module.

---

## Phase 3.1: Setup

- [X] T001 [P] Add `[project.optional-dependencies] langfuse = ["langfuse>=2.60,<3"]` block to `/Users/um-yunsang/KOSMOS-467/pyproject.toml`; leave core runtime dependencies untouched; confirm `PyYAML` and `jsonschema` are already present under dev extras and, if absent, add them to `[project.optional-dependencies] dev`. Run `uv lock` and commit the refreshed `/Users/um-yunsang/KOSMOS-467/uv.lock`.
- [X] T002 [P] Create empty scaffold directories with a `.gitkeep` in each: `/Users/um-yunsang/KOSMOS-467/prompts/`, `/Users/um-yunsang/KOSMOS-467/docker/`, `/Users/um-yunsang/KOSMOS-467/.devcontainer/`, `/Users/um-yunsang/KOSMOS-467/tools/release_manifest/`, `/Users/um-yunsang/KOSMOS-467/tests/shadow_eval/`, `/Users/um-yunsang/KOSMOS-467/docs/release-manifests/`.
- [X] T003 [P] Create `/Users/um-yunsang/KOSMOS-467/.dockerignore` populated per FR-A05 (excluding `.git`, `.venv`, `.pytest_cache`, `tests/`, `specs/`, `docs/`, `.github/`, `node_modules/`, `__pycache__/`, `.mypy_cache/`, `*.log`). English-only comments at the head of the file.
- [X] T004 [P] Capture baseline golden fixtures for the refactor-invariance tests: create `/Users/um-yunsang/KOSMOS-467/tests/context/fixtures/system_prompt_pre_refactor.txt` and `/Users/um-yunsang/KOSMOS-467/tests/context/fixtures/session_compact_pre_refactor.txt` by running the CURRENT `SystemPromptAssembler.assemble()` and `session_compact()` helper paths against a frozen config, then write the exact byte stream to the fixture files. These fixtures underpin FR-X01 and FR-X02 and MUST be committed before any refactor touches `src/kosmos/context/system_prompt.py` or `src/kosmos/context/session_compact.py`.

---

## Phase 3.2: Tests First (TDD) — MUST FAIL BEFORE IMPLEMENTATION

> Rule: every test below MUST be authored and MUST FAIL (red) before the corresponding Phase 3.3 implementation task is started. Any task that modifies the SAME test file as another `[P]` task is sequential.

### Prompt Registry — Schema & Model Invariants (FR-C01, C02, C03, C04)

- [ ] T005 [P] [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_manifest_schema.py` asserting that a hand-crafted valid manifest dict matches `/Users/um-yunsang/KOSMOS-467/specs/026-cicd-prompt-registry/contracts/prompts-manifest.schema.json` via `jsonschema.validate`, and a malformed manifest (bad `prompt_id` pattern, missing `sha256`, extra field) raises `jsonschema.ValidationError`.
- [ ] T006 [P] [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_manifest_entry_model.py` asserting invariants I1–I4: (a) `PromptManifestEntry(prompt_id="system_v1", version=2, ...)` raises `ValidationError` because suffix disagrees with `version`; (b) `path="../x.md"` raises `ValidationError`; (c) `sha256="Z"*64` raises `ValidationError`; (d) valid construction yields a frozen instance (`model_config.frozen is True`) and mutation raises.
- [ ] T007 [P] [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_manifest_model.py` asserting invariants M1 (duplicate `prompt_id` across entries raises) and M2 (prompt family versions are a dense 1..N sequence; a `[v1, v3]` family raises).

### Prompt Registry — Runtime Loader Fail-Closed (FR-C03, FR-C05, FR-C06, FR-C10, Edge Cases)

- [ ] T008 [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_loader_happy_path.py` asserting that a temporary directory containing three valid prompt files plus a matching `manifest.yaml` is loaded by `PromptLoader`; `.load("system_v1")` returns a `str`, `.get_hash("system_v1")` returns the expected 64-hex digest, and `.all_hashes()` returns a `dict[str, str]` with exactly three entries. Assert an INFO log record was emitted per resolved prompt (FR-C10) via `caplog` on the `kosmos.context.prompt_loader` logger.
- [ ] T009 [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_loader_fail_closed.py` covering invariants R1, R2, R3: (a) manifest lists a path whose file is missing → `PromptRegistryError`; (b) manifest `sha256` does not match file bytes (tamper one byte) → `PromptRegistryError` naming the mismatching `prompt_id`; (c) an orphan `.md` file exists under `prompts/` that is not listed in `manifest.yaml` → `PromptRegistryError` naming the orphan file.
- [ ] T010 [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_loader_immutability.py` asserting that `PromptLoader.load("system_v1")` returns a `str` (immutable) and that the loader caches a single instance — two calls return identical object identity (`is`) for the same prompt_id; also assert no public setter exists for the internal cache (FR-C04).

### Prompt Registry — Langfuse Opt-in (FR-C08, FR-C09)

- [ ] T011 [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_prompt_loader_langfuse_flag.py` asserting: (a) with `KOSMOS_PROMPT_REGISTRY_LANGFUSE` unset the loader never imports `langfuse` (use `sys.modules` introspection after boot); (b) with the flag `true` but the `langfuse` extras not installed the loader raises `PromptRegistryError` at startup with a message pointing at `uv sync --extra langfuse`; (c) with the flag `true` and a mock `langfuse` client returning a hash that disagrees with the repo hash, startup fails-closed (FR-C09).

### `kosmos.prompt.hash` OTEL attribute (FR-C07)

- [ ] T012 [P] [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/observability/test_prompt_hash_attribute.py` that drives a minimal Context Assembly → `LLMClient` call through a `httpx.MockTransport` + in-memory OTEL span exporter, then asserts every recorded span from the Context Assembly layer carries the attribute `kosmos.prompt.hash` whose value equals the SHA-256 hex digest of the system prompt bytes actually sent in the call body.

### Refactor Invariance (FR-X01, FR-X02, FR-X03)

- [ ] T013 [P] [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_system_prompt_refactor_equivalence.py` asserting that `SystemPromptAssembler.assemble(config=<frozen>)` returns a string byte-identical to `tests/context/fixtures/system_prompt_pre_refactor.txt` when `prompts/system_v1.md` and `prompts/session_guidance_v1.md` exactly reproduce today's inline strings (FR-X01). Provide a SEPARATE fixture `/Users/um-yunsang/KOSMOS-467/tests/context/fixtures/session_guidance_v1_expected.txt` that captures the v1 text WITH the `address_to_region` → `resolve_location` correction from FR-X03; assert the loaded session-guidance bytes equal that fixture.
- [ ] T014 [P] [US2] Write `/Users/um-yunsang/KOSMOS-467/tests/context/test_session_compact_refactor_equivalence.py` asserting that `session_compact(...)` output against a frozen input transcript is byte-identical to `tests/context/fixtures/session_compact_pre_refactor.txt` once `prompts/compact_v1.md` reproduces the current inline `_SUMMARY_HEADER` + section scaffolding (FR-X02).

### Release Manifest — Schema & Model (FR-E02, FR-E05)

- [ ] T015 [P] [US1] Write `/Users/um-yunsang/KOSMOS-467/tests/release_manifest/test_release_manifest_schema.py` asserting a valid dict from the `examples[0]` of `/Users/um-yunsang/KOSMOS-467/specs/026-cicd-prompt-registry/contracts/release-manifest.schema.json` validates; and each of the following malformed variants raises `ValidationError`: missing `prompt_hashes.system_v1`, `commit_sha` of length 39, `docker_digest` without `sha256:` prefix, extra top-level field `api_key`.
- [ ] T016 [P] [US1] Write `/Users/um-yunsang/KOSMOS-467/tests/release_manifest/test_release_manifest_model.py` asserting invariants RM1–RM4 on the `ReleaseManifest` Pydantic model: (a) `prompt_hashes` missing any of `system_v1`/`session_guidance_v1`/`compact_v1` raises; (b) malformed `commit_sha` raises; (c) `docker_digest` without `sha256:` prefix raises; (d) adding an extra field (e.g. `slack_webhook`) at construction raises (`extra="forbid"`, NFR-03 enforcement).

### Release Manifest — CLI (`tools/release_manifest/render.py`)

- [ ] T017 [US1] Write `/Users/um-yunsang/KOSMOS-467/tests/release_manifest/test_render_cli.py` asserting: (a) happy path — passing all six CLI args produces a YAML file that validates against the release-manifest JSON Schema; (b) `--uv-lock-hash` without `sha256:` prefix causes non-zero exit with a diagnostic; (c) omitting `--prompt-hashes-file` causes non-zero exit; (d) `uv.lock` drift (pass two mismatching lock hashes between `--uv-lock-hash` and a computed file) surfaces as non-zero exit (FR-E04 surrogate — CLI-level check; full `uv sync --frozen` drift check lives in the CI workflow).

### Shadow-eval workflow (FR-D01..D06)

- [ ] T018 [P] [US3] Write `/Users/um-yunsang/KOSMOS-467/tests/shadow_eval/test_battery_emits_two_environments.py` running `tests/shadow_eval/battery.py` twice — once tagged `deployment.environment=main`, once `shadow` — against an in-memory span exporter, and asserting both batches exist in the exporter's captured spans with identical battery input ids (FR-D03).
- [ ] T019 [P] [US3] Write `/Users/um-yunsang/KOSMOS-467/tests/shadow_eval/test_battery_no_live_network.py` asserting that the battery is constructed with an `httpx.MockTransport` and that ANY attempt to reach a real `*.data.go.kr` endpoint (monkeypatch the transport to record outbound hosts; assert zero records matching `data.go.kr`) causes the test to fail (FR-D05, NFR-04).
- [ ] T020 [P] [US3] Write `/Users/um-yunsang/KOSMOS-467/tests/shadow_eval/test_artifact_shape.py` asserting that the battery's JSON artifact at `tests/shadow_eval/out/eval-report.json` matches the expected shape: top-level `spans: list`, each span carrying `attributes.deployment.environment ∈ {main, shadow}`; the grouped-by-environment counts match (FR-D04).

### Docker & Devcontainer smoke (FR-A01..A06, FR-B01..B04)

- [ ] T021 [P] [US1] Write `/Users/um-yunsang/KOSMOS-467/tests/docker/test_dockerfile_lint.py` as a dockerfile-grep test (no real `docker build` in the unit phase): parse `docker/Dockerfile` and assert it contains (a) `FROM python:3.12-slim AS builder` and a distinct runtime `FROM ... AS runtime` stage, (b) `uv sync --frozen`, (c) `USER 1000`, (d) `ENV UV_LINK_MODE=copy` and `ENV UV_COMPILE_BYTECODE=1`, (e) a comment header listing the base image licence (PSF for `python:3.12-slim`), (f) a pinned uv version — not `uv:latest`.
- [ ] T022 [P] [US4] Write `/Users/um-yunsang/KOSMOS-467/tests/devcontainer/test_devcontainer_json.py` parsing `.devcontainer/devcontainer.json` as JSON-with-comments and asserting: (a) `image` starts with `mcr.microsoft.com/devcontainers/python:3.12`; (b) `features` includes a uv feature reference; (c) `postCreateCommand` equals `uv sync`; (d) `forwardPorts` contains `4000` and `4318`; (e) no host-required env vars beyond those in `.env.example` (FR-B04).

### CI workflow wiring tests (FR-D01, FR-F01..F05)

- [ ] T023 [US1] [US3] Write `/Users/um-yunsang/KOSMOS-467/tests/ci/test_workflows_yaml.py` parsing `.github/workflows/ci.yml`, `.github/workflows/shadow-eval.yml`, `.github/workflows/release-manifest.yml` with PyYAML and asserting: (a) `shadow-eval.yml` `on.pull_request.paths` includes `prompts/**`; (b) `shadow-eval.yml` has a top-level `timeout-minutes: 15` on the eval job (FR-D06); (c) `release-manifest.yml` triggers only on `push.tags: v*.*.*` (FR-F04); (d) `ci.yml` now defines a `docker-build` job whose `on.pull_request.paths` includes `docker/**`, `pyproject.toml`, `uv.lock` (FR-F02); (e) the existing lint/test/dead-code job names and their coverage gate reference are preserved unchanged (FR-F01).

---

## Phase 3.3: Core Implementation (only after matching Phase 3.2 tests are red)

### Prompt Registry — Data Models

- [ ] T024 [US2] Create `/Users/um-yunsang/KOSMOS-467/src/kosmos/context/prompt_models.py` implementing `PromptManifestEntry`, `PromptManifest`, and the typed aliases `Sha256Hex`, `PromptId`, `RelPath` exactly as specified in `specs/026-cicd-prompt-registry/data-model.md` §§ 1–2 (frozen, `extra="forbid"`, invariants I1–I4 and M1–M2 enforced via `@model_validator(mode="after")`). Makes T006 and T007 green.

### Prompt Registry — Loader

- [ ] T025 [US2] Create `/Users/um-yunsang/KOSMOS-467/src/kosmos/context/prompt_loader.py` implementing `PromptLoader` with the public API documented in `specs/026-cicd-prompt-registry/research.md § Architectural Sketch`: `load(prompt_id: str) -> str`, `get_hash(prompt_id: str) -> str`, `all_hashes() -> Mapping[str, str]`, plus a `python -m` CLI exposing `--regenerate-manifest` and `--emit-hashes`. Uses stdlib `hashlib`, `logging`, `pathlib`, and PyYAML. Raises `PromptRegistryError` on R1/R2/R3 violations. Langfuse path is conditional on `KOSMOS_PROMPT_REGISTRY_LANGFUSE` env; no `import langfuse` at module load time — imported lazily inside the flag-true branch. Makes T008, T009, T010, T011 green. Blocked by T024.

### Prompt Registry — v1 Prompt Bodies

- [ ] T026 [P] [US2] Author `/Users/um-yunsang/KOSMOS-467/prompts/system_v1.md` carrying today's inline system-identity + language + tool-use-policy + personal-data reminder text from `src/kosmos/context/system_prompt.py` reproduced byte-for-byte. Korean content permitted (domain data exception, NFR-05).
- [ ] T027 [P] [US2] Author `/Users/um-yunsang/KOSMOS-467/prompts/session_guidance_v1.md` carrying today's inline session-guidance text but WITH the `address_to_region` → `resolve_location` correction from FR-X03 applied; the expected output is captured by fixture `tests/context/fixtures/session_guidance_v1_expected.txt` written in T013.
- [ ] T028 [P] [US2] Author `/Users/um-yunsang/KOSMOS-467/prompts/compact_v1.md` carrying today's inline `_SUMMARY_HEADER` + section scaffolding from `src/kosmos/context/session_compact.py` reproduced byte-for-byte.
- [ ] T029 [US2] Generate `/Users/um-yunsang/KOSMOS-467/prompts/manifest.yaml` by running `uv run python -m kosmos.context.prompt_loader --regenerate-manifest`; commit the resulting file with the three v1 entries and their real SHA-256 digests. Blocked by T025, T026, T027, T028.

### Context Assembly Refactor

- [ ] T030 [US2] Refactor `/Users/um-yunsang/KOSMOS-467/src/kosmos/context/system_prompt.py` to replace the inline system-identity / language / tool-use / personal-data / session-guidance string literals with `PromptLoader.load("system_v1")` and `PromptLoader.load("session_guidance_v1")`. Preserve `SystemPromptAssembler.assemble()`'s public signature. Must keep T013 green (byte-identical modulo the documented FR-X03 correction). Blocked by T025, T026, T027, T029.
- [ ] T031 [US2] Refactor `/Users/um-yunsang/KOSMOS-467/src/kosmos/context/session_compact.py` to obtain `_SUMMARY_HEADER` and section labels from `PromptLoader.load("compact_v1")`. Preserve rule-based summary structure unchanged (FR-X02). Must keep T014 green. Blocked by T025, T028, T029.

### OTEL attribute stamping

- [ ] T032 [US2] Hook `kosmos.prompt.hash` attribute emission into the Context Assembly LLM-call path. Edit `/Users/um-yunsang/KOSMOS-467/src/kosmos/context/system_prompt.py` (or the adjacent span-stamping module — identify the exact location during implementation) so that every span covering an LLM call initiated from Context Assembly carries `kosmos.prompt.hash = sha256(bytes_actually_sent)`. Respects OTEL GenAI v1.40 conventions (KOSMOS extension namespace per Spec 021). Must make T012 green. Blocked by T025, T030.

### Release Manifest — Data Model & CLI

- [ ] T033 [P] [US1] Create `/Users/um-yunsang/KOSMOS-467/tools/release_manifest/__init__.py` (empty package marker) and `/Users/um-yunsang/KOSMOS-467/tools/release_manifest/models.py` implementing the `ReleaseManifest` Pydantic model and typed aliases (`CommitSha`, `Sha256Prefixed`, `FriendliModelId`, `LiteLlmProxyVersion`) exactly as specified in `data-model.md § 3`, enforcing RM1–RM4. Makes T016 green.
- [ ] T034 [US1] Create `/Users/um-yunsang/KOSMOS-467/tools/release_manifest/render.py` exposing a `python -m tools.release_manifest.render` CLI with the arguments documented in `quickstart.md § C.2`: `--commit-sha`, `--uv-lock-hash`, `--docker-digest`, `--prompt-hashes-file`, `--friendli-model-id`, `--litellm-proxy-version`, `--out`. Validates inputs via the model (T033), serialises as canonical YAML, writes to `--out`. Uses stdlib `logging`. Makes T017 green. Blocked by T033.

---

## Phase 3.4: Integration

### Docker & Devcontainer

- [ ] T035 [P] [US1] Create `/Users/um-yunsang/KOSMOS-467/docker/Dockerfile` implementing the two-stage uv build per `research.md § Reference Mapping Table` rows 1–2 (Astral + Hynek). Builder: `FROM python:3.12-slim AS builder` + `COPY --from=ghcr.io/astral-sh/uv:<pinned-version> /uv /usr/local/bin/uv` + `ENV UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1` + `uv sync --frozen --no-install-project` then `uv sync --frozen`. Runtime: `FROM python:3.12-slim AS runtime` + copy only `/app/.venv` and application source + `USER 1000`. File header comment documents PSF licence of `python:3.12-slim` (NFR-02). Satisfies FR-A01..A06. Makes T021 green.
- [ ] T036 [P] [US4] Create `/Users/um-yunsang/KOSMOS-467/.devcontainer/devcontainer.json` with `image: mcr.microsoft.com/devcontainers/python:3.12`, `features: { "ghcr.io/astral-sh/uv-devcontainer-feature/uv:1": {} }`, `postCreateCommand: uv sync`, `forwardPorts: [4000, 4318]`, and customizations block pinning VS Code Python + Pylance extensions. Satisfies FR-B01..B04. Makes T022 green.

### GitHub Actions workflows

- [ ] T037 [P] [US3] Create `/Users/um-yunsang/KOSMOS-467/.github/workflows/shadow-eval.yml` triggered on `pull_request` with `paths: ["prompts/**"]`; checks out both merge-base and PR head, runs `uv run python -m tests.shadow_eval.battery --environment main --out /tmp/main.json` then `--environment shadow --out /tmp/shadow.json`, merges into `eval-report.json`, uploads via `actions/upload-artifact@v4`, `timeout-minutes: 15`. Satisfies FR-D01..D06.
- [ ] T038 [P] [US1] Create `/Users/um-yunsang/KOSMOS-467/.github/workflows/release-manifest.yml` triggered on `push.tags: v*.*.*`; runs `uv sync --frozen` (fails on drift per FR-E04), computes `uv_lock_hash`, pulls the image digest from GHCR build output, calls `python -m tools.release_manifest.render`, commits the result to `docs/release-manifests/<sha>.yaml` on `main` via a machine-authored commit referencing the release tag. Satisfies FR-E01..E05.
- [ ] T039 [US1] [US3] Edit `/Users/um-yunsang/KOSMOS-467/.github/workflows/ci.yml` to add a `docker-build` job alongside existing lint/test/dead-code lanes: triggered on `push` to `main` and on `pull_request` with `paths: [docker/**, pyproject.toml, uv.lock]`; runs `docker build -f docker/Dockerfile -t kosmos:ci .` + `docker inspect` size ≤ 2 GB gate + `docker run --rm kosmos:ci id -u` == `1000` gate. Preserves all existing job names, Python 3.12 + 3.13 matrix, coverage gate ≥ 80 %. Also wires the `shadow-eval` workflow's completion status into the PR checks panel without making it a required check. Satisfies FR-F01..F05. Makes T023 green. Blocked by T035.

### Shadow-eval battery module

- [ ] T040 [US3] Create `/Users/um-yunsang/KOSMOS-467/tests/shadow_eval/battery.py` exposing a `python -m tests.shadow_eval.battery` CLI accepting `--environment {main|shadow}` and `--out <path>`. Uses fixtures under `tests/fixtures/` exclusively; constructs every HTTP call through an `httpx.MockTransport`; emits spans stamped with `deployment.environment=<value>`; writes JSON to `--out`. Makes T018, T019, T020 green.

---

## Phase 3.5: Polish

- [ ] T041 [P] Add a `schema-validate` job step inside `.github/workflows/ci.yml`'s existing lint lane that runs `uv run python -m jsonschema -i prompts/manifest.yaml specs/026-cicd-prompt-registry/contracts/prompts-manifest.schema.json` on every PR; non-zero exit fails the lint lane.
- [ ] T042 [P] Extend `/Users/um-yunsang/KOSMOS-467/docs/conventions.md` (or add a new `docs/prompt-registry.md` if `conventions.md` lacks an appropriate section) with a short contributor pointer: "Every prompt change = edit under `prompts/` + regenerate `manifest.yaml` + PR triggers `shadow-eval`." English source text only.
- [ ] T043 [P] Add a release-notes entry for Epic #467 at `/Users/um-yunsang/KOSMOS-467/docs/release-notes/epic-467.md` summarising the six artefacts delivered (Dockerfile, devcontainer, prompts/v1, PromptLoader, shadow-eval workflow, release-manifest workflow) and the cross-Epic contracts (`kosmos.prompt.hash` → #501, env keys proposed → #468, `litellm_proxy_version` placeholder → #465).
- [ ] T044 Run `uv run pytest -q` end-to-end and confirm zero failures; append the green summary line to the Epic PR description as evidence for SC-001..SC-007. (No file edit — verification step.)

---

## Dependency Graph (critical edges)

```
T001,T002,T003,T004            (Setup — parallel)
        │
        ▼
T005..T023                     (Phase 3.2 tests — mostly [P]; T023 touches workflows, sequential with T017/T039)
        │
        ▼
T024 ──► T025 ──► T029 ──► T030, T031, T032
                │                   ▲
T026, T027, T028 ────────────────────┘
        │
        ▼
T033 ──► T034
        │
        ▼
T035, T036, T037, T038 (Integration — mostly [P])
        │
        ▼
T039  (edits ci.yml — sequential with T041)
        │
        ▼
T040  (battery module — makes shadow tests green)
        │
        ▼
T041, T042, T043 (Polish — parallel)
        │
        ▼
T044  (end-to-end verification)
```

## Parallel Execution Groups

### Phase 3.1 — all four tasks parallel

- Group A (all `[P]`): {T001, T002, T003, T004} — each touches a unique file / directory set.

### Phase 3.2 — test-authoring parallelism

- Group A (unique test files under `tests/context/`): {T005, T006, T007, T013, T014} — all `[P]`.
- Group B (unique test files under `tests/observability/`, `tests/release_manifest/`, `tests/shadow_eval/`, `tests/docker/`, `tests/devcontainer/`): {T012, T015, T016, T018, T019, T020, T021, T022} — all `[P]`.
- Sequential within Phase 3.2: {T008, T009, T010, T011} all share the `tests/context/test_prompt_loader*.py` family and the shared `PromptLoader` fixture scaffold — keep sequential; {T017} depends on models authored in Phase 3.3 — keep unblocked from other Phase 3.2 [P] tests but serialised against T016 which defines the model contract first; {T023} touches multiple workflow YAML files and must be sequential with T039/T041.

### Phase 3.3 — core-implementation parallelism

- Group A — prompt bodies: {T026, T027, T028} — all `[P]`, distinct markdown files.
- Group B — release-manifest module: {T033} `[P]` (separate package).
- Sequential: {T024 → T025 → T029 → T030, T031, T032} — the refactor depends on loader + manifest existing.

### Phase 3.4 — integration parallelism

- Group A: {T035, T036, T037, T038} — `[P]` on distinct files (Dockerfile, devcontainer.json, two workflow YAMLs).
- Sequential: {T039} — edits `ci.yml` which is shared with T041's polish edit; run T039 before T041.
- Sequential: {T040} — depends on the battery being runnable once prompts and models exist.

### Phase 3.5

- Group A: {T041, T042, T043} — parallel (ci.yml vs. conventions.md vs. release-notes file). T041 and T039 BOTH edit ci.yml — keep them sequential in ID order.

---

## Traceability matrix (FR → task)

| FR / NFR / SC | Primary task(s) | Verification task(s) |
|---|---|---|
| FR-A01..A06 | T035 | T021 |
| FR-B01..B04 | T036 | T022 |
| FR-C01 | T026, T027, T028, T029 | T008 |
| FR-C02 | T024, T029 | T005, T006, T007 |
| FR-C03 | T025 | T008, T009 |
| FR-C04 | T025 | T010 |
| FR-C05 | T030 | T013 |
| FR-C06 | T031 | T014 |
| FR-C07 | T032 | T012 |
| FR-C08 | T025 | T011 |
| FR-C09 | T025 | T011 |
| FR-C10 | T025 | T008 |
| FR-D01..D06 | T037, T040 | T018, T019, T020, T023 |
| FR-E01..E05 | T033, T034, T038 | T015, T016, T017 |
| FR-F01..F05 | T039, T041 | T023 |
| FR-X01 | T030 | T013 |
| FR-X02 | T031 | T014 |
| FR-X03 | T027 | T013 |
| NFR-01..07 | Cross-cutting (T035 licence header, T025 stdlib logging, T033 frozen Pydantic v2, T039 Docker size gate) | T021, T039, T044 |
| SC-001 | T035, T039 | T039, T044 |
| SC-002 | T036 | T022, T044 |
| SC-003 | T025 | T009 |
| SC-004 | T030, T031 | T013, T014 |
| SC-005 | T037, T040 | T018, T020 |
| SC-006 | T034, T038 | T015, T017 |
| SC-007 | T032 | T012 |

---

## Completion gate

Before declaring Epic #467 done:

1. All 44 tasks checked off.
2. `uv run pytest -q` green (T044).
3. `gh run list --branch feat/467-cicd-prompt-registry` shows all CI lanes green.
4. Release-manifest dry-run (`quickstart.md § C.2`) produces a schema-valid YAML locally.
5. Shadow-eval dry-run on a fixture-only PR produces both `deployment.environment` span batches.
