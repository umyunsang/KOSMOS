# Implementation Plan: Secrets & Config — Infisical OIDC + 12-Factor + KOSMOS_* Registry

**Branch**: `feat/468-secrets-config` | **Date**: 2026-04-17 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/026-secrets-infisical-oidc/spec.md`

## Summary

Close Epic #468 by (a) **replacing long-lived GitHub Encrypted Secrets** with Infisical Cloud Free via `Infisical/secrets-action@v1` + GitHub Actions OIDC federation in `.github/workflows/ci.yml`, (b) **publishing the canonical `KOSMOS_*` env-var registry** at `docs/configuration.md` covering all 17 variables currently consumed by `src/`, (c) **adding a fail-fast startup guard** at `src/kosmos/config/guard.py` wired into the CLI entry point that exits <100 ms with a single-line remediation message, and (d) **eliminating drift** via `scripts/audit-secrets.sh` (workflow-grep gate) + `scripts/audit-env-registry.py` (registry ↔ code cross-check). Regression-guards #458. No new runtime dependencies (AGENTS.md hard rule) — guard uses stdlib only; registry/audit scripts use stdlib + pydantic-settings that are already in the dep graph.

Reference anchor: Claude Code's **permission gauntlet** — `src/kosmos/config/guard.py` mirrors Claude Code's discipline of running a fail-fast boundary validator **before** any network-bound tool loop begins. Constitution Principle I maps "Permission Pipeline → `src/kosmos/permissions/` (Claude Code)"; this Epic extends that doctrine to the *startup* phase.

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no bump).
**Primary Dependencies**: `pydantic >= 2.13` (existing, type validation), `pydantic-settings >= 2.0` (existing, `BaseSettings`), `pytest` + `pytest-asyncio` (existing, tests), stdlib `os`/`sys`/`time`/`pathlib`/`argparse`/`re`. **No new runtime dependencies** — AGENTS.md hard rule.
**Storage**: N/A (in-memory configuration only; `.env` is source-of-truth on disk, read-only from the guard's perspective).
**Testing**: `pytest` + `pytest-asyncio`. `tests/config/test_guard.py` for guard unit tests; `scripts/audit-env-registry.py` self-tests its own parser on fixtures.
**Target Platform**: Linux server (CI) + macOS developer laptop. No platform-specific code.
**Project Type**: Library + CLI (`kosmos.cli`). Guard is a library function invoked by CLI entry point.
**Performance Goals**: Guard `verify_startup()` must return within **100 ms** wall-clock on a cold import path (NFR-001, FR-001). `scripts/audit-env-registry.py` must complete within **10 seconds** on the full `src/` tree (NFR-006).
**Constraints**:
- `.env` is a symlink to a user-managed file — guard and scripts **must never write** to it (spec Edge Case #2).
- "Shell wins over `.env`" invariant preserved from `src/kosmos/_dotenv.py:40` (FR-041).
- Forbidden file surface: `.env`, `docker/`, `.devcontainer/`, `prompts/`, `src/kosmos/safety/`, `.github/workflows/docker.yml`, `.github/workflows/shadow-eval.yml`.
- Korean domain data only; all spec prose and source code in English (AGENTS.md hard rule).
**Scale/Scope**: 17 KOSMOS_* variables + 2 LANGFUSE_* (conditional-required, #501-owned) + 6 future LiteLLM variables (catalogued schema-extensibly for #465). Registry grows by ≤ 2 vars/quarter at current velocity.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Reference-Driven Architecture** | ✅ PASS | Guard mirrors Claude Code's permission gauntlet (see Summary). Registry pattern mirrors 12-Factor Config (§III) + Doppler/Infisical canonical schema. Each design decision in `research.md` cites a concrete reference. |
| **II. Fail-Closed at API Boundaries** | ✅ PASS | Guard is *literally* a fail-closed boundary validator: missing required var → non-zero exit before any tool loop. No ambient authority, no partial start-up. |
| **III. Stdlib logging / no print()** | ✅ PASS | Guard emits to `sys.stderr` via the CLI boundary (FR-003); library code in `kosmos.config.guard` returns structured diagnostics, never `print()`s. |
| **IV. Pydantic v2, no `Any`** | ✅ PASS | Existing `KosmosSettings`/`LLMClientConfig`/`CLIConfig` preserved unchanged. Guard consumes typed `list[RequiredVar]` dataclasses — no `Any` anywhere. |
| **V. Reference-driven design in specs** | ✅ PASS | Spec Assumptions + this plan cite Infisical docs, GitHub Actions OIDC spec, 12-Factor App, Claude Code reference. |
| **VI. Deferred Work Accountability** | ✅ PASS | Spec `§Scope Boundaries & Deferred Items` lists 5 Permanent + 7 Deferred. All deferred items tagged to #465 (LiteLLM), #501 (observability), #467 (CI/CD & Prompts), or `NEEDS TRACKING`. No free-text "future epic" phrases. |

**AGENTS.md hard-rule check**:
- ✅ No new runtime dependency.
- ✅ No `.env` write path.
- ✅ `KOSMOS_` prefix enforced; `LANGFUSE_*` sole documented exception.
- ✅ No `print()` in library code.
- ✅ No file >1 MB committed.
- ✅ No Go/Rust; TypeScript absent from this Epic.

**Result**: All gates pass. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this feature)

```text
specs/026-secrets-infisical-oidc/
├── plan.md                      # This file
├── spec.md                      # /speckit-specify output
├── research.md                  # Phase 0 output
├── data-model.md                # Phase 1 output — registry entity schemas
├── quickstart.md                # Phase 1 output — contributor onboarding
├── checklists/
│   └── requirements.md          # Spec quality checklist (existing)
├── contracts/
│   ├── guard.md                 # Phase 1 — guard function contract
│   ├── audit-env-registry.md    # Phase 1 — Python audit script CLI
│   ├── audit-secrets.md         # Phase 1 — bash audit script CLI
│   └── ci-workflow.md           # Phase 1 — Infisical action integration
└── tasks.md                     # Phase 2 output (/speckit-tasks)
```

### Source Code (repository root)

```text
src/kosmos/config/               # NEW — fail-fast startup guard package
├── __init__.py
└── guard.py                     # verify_startup() + required-names registry

src/kosmos/cli/app.py            # EDIT — wire guard into main() between
                                 #        load_repo_dotenv() and setup_tracing()

tests/config/                    # NEW
├── __init__.py
└── test_guard.py                # guard unit tests (FR-001..008, NFR-001)

docs/configuration.md            # NEW — human-readable KOSMOS_* registry
docs/design/mvp-tools.md         # EDIT (typo fix line 642: REST_KEY→API_KEY)

scripts/audit-env-registry.py    # NEW — registry↔code drift audit
scripts/audit-secrets.sh         # NEW — workflow long-lived-secret grep gate

.env.example                     # REGENERATE — dotenv-format, <redacted> values
.github/workflows/ci.yml         # EDIT — Infisical action + typo fix
                                 #        (KOSMOS_DATA_GO_KR_KEY → _API_KEY)
```

**Structure Decision**: Single-project layout (Option 1). The guard is a new cohesive package (`kosmos.config`) inside the existing `src/kosmos/` library root; scripts live outside the package at `scripts/` per AGENTS.md convention. Tests mirror source at `tests/config/`. Preserves existing pydantic-settings modules (`settings.py`, `llm/config.py`, `cli/config.py`) — guard complements, does not replace.

## Phase 0: Outline & Research

See [research.md](./research.md). Seven research topics all resolved; zero `NEEDS CLARIFICATION` markers remaining. Key decisions:

1. **Guard invocation site**: `src/kosmos/cli/app.py:main()`, *after* `load_repo_dotenv()` and *before* `setup_tracing()`. Guard must see the loaded env; tracing must not spin up before the guard validates config. Cite: `_dotenv.py` docstring + Claude Code permission-pipeline doctrine.
2. **Required-name source of truth**: In-code Python list (`_REQUIRED_VARS` in `kosmos.config.guard`). Registry markdown is the human-facing mirror; the code is machine truth. `scripts/audit-env-registry.py` reconciles them.
3. **Activation flag**: `KOSMOS_ENV ∈ {dev, ci, prod}`; unknown values fall through to `dev`. Cite: 12-Factor App §III "strict separation".
4. **Infisical OIDC trust pinning**: `repository=umyunsang/KOSMOS` + `workflow=.github/workflows/ci.yml`; `ref` **not** pinned (required for PR-CI). Cite: Infisical GitHub Actions + OIDC docs.
5. **Audit parsing**: Regex `KOSMOS_[A-Z_]+` over `*.py` / `*.yml` / `*.md`; markdown table parse for the registry section. Stdlib-only (`re`, `argparse`, `pathlib`).
6. **`.env.example` format**: Dotenv (`KOSMOS_X=<redacted>`), matches `_dotenv.py` parser semantics. No `export` prefix.
7. **Bootstrap-secret elimination**: Infisical OIDC federation supports **zero** long-lived secret in the workflow; `INFISICAL_CLIENT_ID` allowed as a public identifier var only (not a secret), mapped via `vars.*` not `secrets.*`.

## Phase 1: Design & Contracts

See:
- [data-model.md](./data-model.md) — `RequiredVar`, `ConditionalVar`, `DeprecatedVar`, `OverrideFamily` entities + registry table schema + audit drift-report shape.
- [contracts/guard.md](./contracts/guard.md) — `verify_startup() -> None` contract, exit codes, stderr grammar.
- [contracts/audit-env-registry.md](./contracts/audit-env-registry.md) — `scripts/audit-env-registry.py` CLI, drift-report JSON, exit codes.
- [contracts/audit-secrets.md](./contracts/audit-secrets.md) — `scripts/audit-secrets.sh` pattern allow/deny list, exit codes.
- [contracts/ci-workflow.md](./contracts/ci-workflow.md) — Infisical action inputs, env injection surface, failure handling.
- [quickstart.md](./quickstart.md) — new-contributor onboarding path.

### Post-design Constitution re-check

All six principles still pass after Phase 1 design. No violation introduced by contracts; no dependency added; guard remains library-pure with a thin CLI wrapper. AGENTS.md rules unchanged.

## Phase 2: Task Generation Preview (for `/speckit-tasks`)

Tasks will be generated from Phase 1 artefacts in this order (TDD flow):

1. **T001–T002**: Skeleton package — `src/kosmos/config/__init__.py`, `tests/config/__init__.py`.
2. **T003**: `tests/config/test_guard.py` — write failing tests first for FR-001..008 + NFR-001 (100 ms budget).
3. **T004**: Implement `src/kosmos/config/guard.py` to satisfy T003.
4. **T005**: Wire guard into `src/kosmos/cli/app.py:main()` + dedicated test verifying invocation order.
5. **T006**: `docs/configuration.md` — publish the registry (all 17 vars + cross-Epic vars).
6. **T007**: `scripts/audit-env-registry.py` + self-test fixture.
7. **T008**: `scripts/audit-secrets.sh` + shellcheck-clean + test invocation.
8. **T009**: `.env.example` regeneration from registry (script-generated, deterministic).
9. **T010**: `.github/workflows/ci.yml` — Infisical action migration + typo fix (`KOSMOS_DATA_GO_KR_KEY` → `_API_KEY`).
10. **T011**: `docs/design/mvp-tools.md:642` — one-line typo fix (`KOSMOS_KAKAO_REST_KEY` → `KOSMOS_KAKAO_API_KEY`).
11. **T012**: Wire both audit scripts into CI as pre-test steps.
12. **T013**: End-to-end validation — empty-env smoke (SC-006), rotation dry-run (SC-002), live suite via OIDC (SC-004).

Parallelisable groups (for `/speckit-implement` Agent Teams):
- **Group A** (P1 guard, independent): T001→T003→T004→T005.
- **Group B** (P2 registry + audits, depends only on registry fields known): T006, T007, T008, T009 — all four can proceed after registry schema agreed.
- **Group C** (P3 Infisical + CI wiring, depends on Group B for audit scripts): T010→T012.
- **Group D** (typo fixes + e2e, depends on all): T011, T013.

Expected Task issue count: ~13 (Sonnet-sized). No single task should exceed `size/M`.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table intentionally empty.
