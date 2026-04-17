# Implementation Plan: CI/CD & Prompt Registry — Manifest + Shadow + uv Docker + Devcontainer

**Branch**: `feat/467-cicd-prompt-registry` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification at `specs/026-cicd-prompt-registry/spec.md`

## Summary

Externalise the three LLM-facing prompts currently embedded in `src/kosmos/context/system_prompt.py` and `src/kosmos/context/session_compact.py` into a manifest-backed `prompts/` registry, ship the platform through a reproducible uv-based multi-stage Docker image plus a devcontainer, add a CI shadow-eval lane that runs a fixture-only battery against both merge-base and PR-head prompts on every `prompts/**` change, and emit a tag-triggered release manifest (`docs/release-manifests/<sha>.yaml`) that pins commit sha, lockfile hash, image digest, prompt hashes, LLM model id, and gateway version. All LLM call spans emitted from Layer 5 carry a new `kosmos.prompt.hash` attribute that Epic #501 will consume.

Technical approach: the Prompt Registry is a small stdlib-only component (Pydantic v2 frozen models + `hashlib.sha256` integrity verification) backed by a YAML manifest; the Docker image follows the Astral + Hynek two-stage uv pattern with `UV_LINK_MODE=copy` + `UV_COMPILE_BYTECODE=1`; the shadow-eval workflow uses the Eugene Yan shadow-deployment pattern (twin runs against merge-base vs PR head, no live traffic) and tags spans with the existing `deployment.environment` attribute from Spec 021. Langfuse Prompt Management is an opt-in integration gated by `KOSMOS_PROMPT_REGISTRY_LANGFUSE=true` and enters as an optional extras dependency.

## Technical Context

**Language/Version**: Python 3.12 (runtime image); 3.12 + 3.13 matrix preserved for CI tests (existing rule; no bump required for this spec).
**Primary Dependencies**: `pydantic >= 2.13` (manifest + prompt metadata models, existing), `PyYAML` (already transitively present via `pydantic-settings` — verify before counting as "no new dep"), stdlib `hashlib` + `logging` + `pathlib`, `uv >= 0.5` (builder stage, pinned by version tag), optional `langfuse` Python SDK (entered as `[project.optional-dependencies] langfuse` — opt-in only).
**Storage**: Filesystem only — `prompts/*.md`, `prompts/manifest.yaml`, and `docs/release-manifests/<sha>.yaml`. No persistent runtime state.
**Testing**: `pytest` + `pytest-asyncio` (existing); new test packages `tests/context/test_prompt_loader.py`, `tests/context/test_prompt_registry_integrity.py`, `tests/observability/test_prompt_hash_attribute.py`, `tests/shadow_eval/test_battery_runs_fixture_only.py`. Golden-file fixtures for FR-X01 byte-identical invariant live under `tests/context/fixtures/`.
**Target Platform**: Linux server containers (Docker/OCI, amd64 primary; arm64 not a Phase 1 goal). Devcontainer runs on macOS / Linux / Windows-WSL2.
**Project Type**: Backend Python library + Docker image + GitHub Actions workflows. No frontend changes in this Epic.
**Performance Goals**: Prompt Registry startup MUST add ≤ 100 ms wall time to cold platform boot (three files, three SHA-256 computations over < 10 KB each). Shadow-eval battery MUST complete within 15 min CI budget (FR-D06).
**Constraints**: Runtime image ≤ 2 GB (SC-001); no live `data.go.kr` calls anywhere in CI (AGENTS.md hard rule, NFR-04); stdlib `logging` only (NFR-06); Pydantic v2 `frozen=True`, no `typing.Any` (NFR-07, Constitution III); source-text English only (NFR-05, Constitution Development Standards); no new top-level runtime dependency (AGENTS.md hard rule — Langfuse stays behind an optional extra).
**Scale/Scope**: 3 prompt files + 1 manifest at first release; ~450 LOC for Prompt Registry + models + tests; 1 Dockerfile (~60 lines), 1 devcontainer.json, 3 new / extended workflow YAMLs; 1 release manifest file per release tag.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Plan alignment |
|---|---|---|
| **I. Reference-Driven Development** | Every design decision traces to a `docs/vision.md § Reference materials` source. | `research.md` Phase 0 table maps 5 external references (Astral uv-Docker, Hynek uv-Docker, Langfuse Prompt Mgmt, Dev Containers spec, Eugene Yan shadow-mode) + 4 internal mappings (Claude Code harness, OTEL GenAI v1.40, Spec 021, Spec 025). **PASS**. |
| **II. Fail-Closed Security** | Conservative defaults; bypass-immune checks. | Prompt Registry refuses to start on any hash mismatch, orphan file, duplicate `prompt_id`, or Langfuse unreachable with flag on (FR-C03, Edge Cases, FR-C09). **PASS**. |
| **III. Pydantic v2 Strict Typing** | All I/O uses Pydantic v2; no `Any`. | `PromptManifestEntry`, `PromptManifest`, `ReleaseManifest` are all `frozen=True` Pydantic v2 models; `@model_validator(mode="after")` used for invariants (Spec 025 pattern). **PASS**. |
| **IV. Government API Compliance** | No live `data.go.kr` calls in CI; fixtures only. | Explicit FR-D05 + NFR-04; shadow-eval battery runs from `tests/fixtures/`; no network egress allowed. **PASS**. |
| **V. Policy Alignment** | Korea AI Action Plan Principles 5/8/9 alignment. | This Epic is infrastructure/observability; it does not change the citizen-facing surface. Principle 8 (single conversational window) is preserved because no new entrypoint is added. Permission pipeline is untouched. **PASS (no regression)**. |
| **VI. Deferred Work Accountability** | Every deferral tracked in Deferred Items table with issue reference. | spec.md contains a 6-row Deferred Items table; each row has `NEEDS TRACKING` markers that `/speckit-taskstoissues` will resolve into real issues. No free-text "future epic" or "v2" references exist outside the table. **PASS**. |

**Gate result**: PASS — no violations, no Complexity Tracking entries required.

**Re-check after Phase 1**: Re-verify above table after data-model.md and contracts/*.schema.json are authored. See "Post-Design Constitution Re-Check" at the end of this document.

## Project Structure

### Documentation (this feature)

```text
specs/026-cicd-prompt-registry/
├── plan.md                              # This file (/speckit.plan output)
├── research.md                          # Phase 0: reference mappings + resolved assumptions
├── data-model.md                        # Phase 1: Pydantic v2 models
├── quickstart.md                        # Phase 1: contributor onboarding
├── contracts/
│   ├── prompts-manifest.schema.json     # JSON Schema Draft 2020-12 for prompts/manifest.yaml
│   └── release-manifest.schema.json     # JSON Schema Draft 2020-12 for docs/release-manifests/*.yaml
├── checklists/
│   └── requirements.md                  # /speckit.checklist output (already exists)
├── spec.md                              # /speckit.specify output (already exists)
└── tasks.md                             # /speckit.tasks output (NOT created by /speckit.plan)
```

### Source code (repository root, files this Epic adds or modifies)

```text
# New files
docker/
└── Dockerfile                           # Two-stage uv build (FR-A01..A06)
.devcontainer/
└── devcontainer.json                    # Python 3.12 + uv feature (FR-B01..B04)
prompts/
├── manifest.yaml                        # Prompt registry manifest (FR-C02)
├── system_v1.md                         # System identity + language + tool-use + personal-data reminder
├── session_guidance_v1.md               # Session guidance (geocoding-first + no-memory-fill)
└── compact_v1.md                        # session_compact header + section scaffolding
src/kosmos/context/
└── prompt_loader.py                     # New — PromptLoader + Pydantic v2 models (FR-C03..C10)
tests/context/
├── test_prompt_loader.py                # Load + SHA-256 + fail-closed (SC-003)
├── test_system_prompt_golden.py         # Byte-identical invariant (SC-004, FR-X01)
├── test_session_compact_golden.py       # Byte-identical invariant (SC-004, FR-X02)
└── fixtures/
    ├── system_v1_current_text.md        # Current inline text for golden comparison
    └── session_guidance_v1_fixture.md   # v1 text with resolve_location correction (FR-X03)
tests/observability/
└── test_prompt_hash_attribute.py        # SC-007 — kosmos.prompt.hash on every LLM span
tests/shadow_eval/
├── __init__.py
├── battery.py                           # Fixed scenario battery (FR-D02)
└── test_battery_runs_fixture_only.py    # Asserts no live API calls possible (FR-D05)
docs/release-manifests/
└── .gitkeep                             # Directory seed; real files authored by build-manifest job
.github/workflows/
├── shadow-eval.yml                      # PR-triggered prompts/** shadow lane (FR-D01..D06)
└── release-manifest.yml                 # Tag-triggered manifest generator (FR-E01..E05)

# Modified files
.github/workflows/ci.yml                 # Add docker-build job (FR-F02); wire shadow-eval + build-manifest (FR-F03/F04)
src/kosmos/context/system_prompt.py      # Refactor — read sections from PromptLoader (FR-C05)
src/kosmos/context/session_compact.py    # Refactor — read header + labels from PromptLoader (FR-C06)
src/kosmos/engine/*.py                   # Add kosmos.prompt.hash span attribute emission (FR-C07, SC-007)
pyproject.toml                           # Add [project.optional-dependencies] langfuse = ["langfuse>=2.0"]
.dockerignore                            # Exclude .git/.venv/.pytest_cache/tests/specs/docs from build context
CLAUDE.md                                # Active Technologies line + Recent Changes entry
```

**Structure Decision**: Single-project Python library + workflow tooling. No `backend/` vs `frontend/` split; KOSMOS has no web frontend in Phase 1. Dockerfile lives under `docker/` to keep the build context surface separate from repo documentation. Workflows live under `.github/workflows/`. Prompt assets live under `prompts/` at repo root so they are visible from every sub-tree and are covered by a single path filter (`prompts/**`) for shadow-eval.

## Complexity Tracking

No Constitution violations. No simpler-alternative-rejected table entries required.

## Post-Design Constitution Re-Check

After Phase 1 artifacts are on disk (`data-model.md`, `contracts/prompts-manifest.schema.json`, `contracts/release-manifest.schema.json`, `quickstart.md`):

| Principle | Re-check result |
|---|---|
| **I. Reference-Driven Development** | All 5 external + 4 internal references are mapped in `research.md` Reference Mapping table, one row per reference → design decision. **PASS**. |
| **II. Fail-Closed Security** | `PromptManifest` model includes `@model_validator(mode="after")` enforcing unique `prompt_id`, strict monotonic `version` per id, and mandatory `sha256` format (64 lowercase hex). **PASS**. |
| **III. Pydantic v2 Strict Typing** | Every model in `data-model.md` declares `model_config = ConfigDict(frozen=True, extra="forbid")`; no `Any`, no `dict[str, object]`; all field types are concrete. **PASS**. |
| **IV. Government API Compliance** | Shadow-eval workflow pins `tests/shadow_eval/battery.py` to fixture-only transport; a test asserts that the battery module imports raise on any `httpx` client construction without a mock transport. **PASS**. |
| **V. Policy Alignment** | No behaviour visible to citizens changes; Layer 3 Permission Pipeline untouched. **PASS (no regression)**. |
| **VI. Deferred Work Accountability** | Deferred Items table in spec.md carries 6 items, all `NEEDS TRACKING` — `/speckit-taskstoissues` will back-fill issue numbers before `/speckit-implement`. **PASS**. |

**Post-Design gate result**: PASS. Ready for `/speckit.tasks`.
