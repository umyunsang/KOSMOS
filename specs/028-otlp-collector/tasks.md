---

description: "Actionable task list for spec 028 — OTLP Collector + Local Langfuse Stack"
---

# Tasks: OTLP Collector + Local Langfuse Stack

**Input**: Design documents from `/Users/um-yunsang/KOSMOS-501/specs/028-otlp-collector/`
**Prerequisites**: plan.md (loaded), spec.md (loaded, 2 user stories), research.md, data-model.md, contracts/collector-config.yaml, contracts/env-reference.md, quickstart.md
**Feature branch**: `feat/501-otlp-collector`
**Parent Epic**: #501 — Production OTLP Collector & Centralized Langfuse Operations

**Tests**: INCLUDED — spec §Testing explicitly requires (a) YAML schema validation of collector config, (b) docker-compose `config` validation, (c) `@pytest.mark.live`-gated PII redaction smoke test backing SC-003.

**Organization**: Tasks are grouped by user story so that US1 (stack bring-up) and US2 (PII redaction gate) can be implemented and demo-validated independently. US2 depends only on the Foundational phase.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: `US1` = KSC demo operator brings up the stack; `US2` = PII redaction verification
- File paths are **absolute** (reside inside the worktree at `/Users/um-yunsang/KOSMOS-501/`)

## Path Conventions

- Infrastructure spec — **no `src/` changes**, **no `pyproject.toml` changes** (FR-012, FR-013).
- New files live at repository root under `infra/otel-collector/` and `docs/`.
- New tests live under `tests/live/` (marker-gated) and `tests/infra/` (CI-safe config lint).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the directory scaffold for the new external infra component. Parallels the existing `infra/copilot-gate-app/` convention.

- [ ] T001 Create directory `/Users/um-yunsang/KOSMOS-501/infra/otel-collector/` with a `.gitkeep` or the config file from T004 populating it (no standalone README needed; `docs/observability.md` is authoritative).

**Checkpoint**: `infra/otel-collector/` directory exists in the worktree.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Produce the two artefacts every downstream task (US1 compose wiring, US2 PII test) reads from — the collector config YAML and the `.env.example` contract update. No user story work can begin until both exist and are schema-valid.

**CRITICAL**: No user story tasks may start until Phase 2 is complete.

- [ ] T002 [P] Copy the authoritative contract file `/Users/um-yunsang/KOSMOS-501/specs/028-otlp-collector/contracts/collector-config.yaml` to `/Users/um-yunsang/KOSMOS-501/infra/otel-collector/config.yaml` byte-for-byte (the contract IS the runtime config; edits must happen in the contract first and be re-copied). Preserve the SPDX-License-Identifier header and the inline "rules mirror spec 021 whitelist" comment.
- [ ] T003 [P] Append three new `KOSMOS_`-prefixed variables to `/Users/um-yunsang/KOSMOS-501/.env.example` under a new `# OTLP Collector (spec 028)` section, matching the env-reference contract at `/Users/um-yunsang/KOSMOS-501/specs/028-otlp-collector/contracts/env-reference.md`: `KOSMOS_OTEL_COLLECTOR_PORT=4318`, `KOSMOS_LANGFUSE_OTLP_ENDPOINT=http://langfuse-web:3000/api/public/otel/v1/traces`, `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER=` (empty, sensitive). Include one-line inline comments describing the consumer per contract invariant 1.
- [ ] T004 Validate `/Users/um-yunsang/KOSMOS-501/infra/otel-collector/config.yaml` schema by running the collector binary's own dry-run inside a throwaway container: `docker run --rm -v /Users/um-yunsang/KOSMOS-501/infra/otel-collector/config.yaml:/etc/otelcol-contrib/config.yaml:ro otel/opentelemetry-collector-contrib@sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114 --config=/etc/otelcol-contrib/config.yaml --dry-run`. Exit code MUST be 0. Record the command and output in the task-completion note (no file created).

**Checkpoint**: `infra/otel-collector/config.yaml` is on disk and schema-valid; `.env.example` carries the three new contract variables. US1 and US2 may now begin in parallel.

---

## Phase 3: User Story 1 — KSC demo operator brings up the full observability stack in one command (Priority: P1) — MVP

**Goal**: `docker compose -f docker-compose.dev.yml up -d` on a fresh clone stands up the full stack (Langfuse + otelcol) healthy within 120 s, and a KOSMOS agent call produces a three-level trace (`invoke_agent` → `chat` → `execute_tool`) visible in the Langfuse UI at `http://localhost:3000` within 10 s (SC-001, SC-002).

**Independent Test**: Fresh clone, run the one-command bring-up per `quickstart.md §1`, then follow `quickstart.md §3–§4`. Verify the three-level span tree appears under a single trace ID in Langfuse.

### Tests for User Story 1

> Tests verify infrastructure correctness without live Langfuse or live `data.go.kr` (AGENTS.md hard rule).

- [ ] T005 [P] [US1] Add CI-safe compose-schema test at `/Users/um-yunsang/KOSMOS-501/tests/infra/test_docker_compose_dev.py` that shells out to `docker compose -f docker-compose.dev.yml config --quiet` and asserts exit code 0. Gate the test with `pytest.importorskip`-style skip if the `docker` binary is absent on the runner; mark non-live so it runs in CI where Docker is available (GitHub-hosted runners have Docker pre-installed).
- [ ] T006 [P] [US1] Add compose-service assertion test at `/Users/um-yunsang/KOSMOS-501/tests/infra/test_compose_services.py` that parses `docker-compose.dev.yml` as YAML (stdlib-only, no new dep — use `yaml` already transitively available via existing dev deps; if absent, fall back to `tomllib`-style minimal parser) and asserts: (a) service `otelcol` exists, (b) its `image` field is the manifest-list digest `otel/opentelemetry-collector-contrib@sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114`, (c) `depends_on.langfuse-web.condition == "service_healthy"`, (d) the config volume mount ends with `:ro`, (e) only port 4318 is exposed (no 4317), (f) `langfuse/langfuse` image tag is pinned to `3.35.0` (or digest form), (g) `langfuse/langfuse-worker` tag is pinned to `3.35.0` (or digest form).

### Implementation for User Story 1

- [ ] T007 [US1] Modify `/Users/um-yunsang/KOSMOS-501/docker-compose.dev.yml` to add the `otelcol` service with the E1 OtelcolService schema from data-model.md: manifest-list digest pin (`otel/opentelemetry-collector-contrib@sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114`) with inline multi-arch digest comment from `research.md §1`, `restart: unless-stopped`, `depends_on.langfuse-web.condition: service_healthy`, volume `./infra/otel-collector/config.yaml:/etc/otelcol-contrib/config.yaml:ro`, port `${KOSMOS_OTEL_COLLECTOR_PORT:-4318}:4318`, healthcheck against `http://localhost:13133/` with interval 5 s retries 10, and `environment:` pass-through for the three new `KOSMOS_` vars so the collector's `${env:…}` expansion works.
- [ ] T008 [US1] In the same `/Users/um-yunsang/KOSMOS-501/docker-compose.dev.yml`, re-pin the `langfuse/langfuse` and `langfuse/langfuse-worker` images from the floating `3` tag to explicit `3.35.0` pins (use digest form from `research.md §1` for KSC reproducibility). Cross-check that no other occurrence of the floating `3` tag remains (git grep inside the file).
- [ ] T009 [P] [US1] Create `/Users/um-yunsang/KOSMOS-501/docs/observability.md` with sections per spec FR-011: (1) stack overview diagram matching data-model.md §Relationships ASCII, (2) span tree reference (`invoke_agent` → `chat` → `execute_tool`), (3) one-command bootstrap steps mirroring `quickstart.md §1`, (4) environment variable reference table (inline contents of `contracts/env-reference.md § New variables`), (5) Langfuse first-run 5-step procedure (FR-008b) mirroring `quickstart.md §2`, (6) troubleshooting for the three common failure modes from `quickstart.md § Troubleshooting`.
- [ ] T010 [US1] Run `quickstart.md §1` locally in the worktree: `docker compose -f docker-compose.dev.yml up -d`, wait for all services `healthy`, then `docker compose -f docker-compose.dev.yml ps` — every row must show `healthy` (or `exited 0` for `minio-init`). Tear down with `docker compose -f docker-compose.dev.yml down` before moving on. Record pass/fail in the PR description.

**Checkpoint**: US1 MVP complete. A KSC demo operator can bring up the full stack in one command; traces appear in Langfuse UI within seconds of an agent call.

---

## Phase 4: User Story 2 — Developer verifies PII is redacted before reaching Langfuse (Priority: P2)

**Goal**: A span emitted with `patient.name` has that attribute stripped by the collector before Langfuse ingests it. A span emitted with `kosmos.location.query="서울역"` arrives at Langfuse with the attribute value replaced by the SHA-256 hex hash of the UTF-8 bytes of `"서울역"` (SC-003).

**Independent Test**: `uv run pytest -m live tests/live/test_collector_pii_redaction.py` passes against a running local stack. CI runs this test with `OTEL_SDK_DISABLED=true` and it is skipped per `@pytest.mark.live` gating (AGENTS.md hard rule).

### Tests for User Story 2

- [ ] T011 [P] [US2] Create `/Users/um-yunsang/KOSMOS-501/tests/live/test_collector_pii_redaction.py` marked with `@pytest.mark.live` that: (a) uses `opentelemetry-sdk` (existing dep from spec 021) to emit one span to `http://localhost:${KOSMOS_OTEL_COLLECTOR_PORT:-4318}` with attributes `patient.name="TEST_OPERATOR"`, `patient.phone="010-0000-0000"`, and `kosmos.location.query="서울역"`; (b) after a short await (respecting `batch` processor's 5 s timeout) fetches the trace from the Langfuse public API (`/api/public/traces`) using the same `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` credential; (c) asserts `patient.name` and `patient.phone` are absent from the returned span's attributes; (d) asserts the `kosmos.location.query` attribute equals `hashlib.sha256("서울역".encode()).hexdigest()` (64 hex chars). Use `pytest.skip` if `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` is unset or the Langfuse health endpoint is unreachable.

### Implementation for User Story 2

- [ ] T012 [US2] No new redaction implementation is required — the redaction rules already live in the authoritative `config.yaml` produced in Phase 2. This task is the **verification** step: execute T011 locally against a running stack and confirm both assertions pass. If either fails, the regression is in the config.yaml (not the test) — open a follow-up to correct the `attributes/pii_redact` rule set before proceeding.
- [ ] T013 [US2] Update `/Users/um-yunsang/KOSMOS-501/docs/observability.md` with a new "PII Redaction Gate" subsection that: (a) lists the four enumerated `patient.*` keys currently covered (reference data-model.md §E2.2 note about no-wildcard-support), (b) documents the additive relationship to spec 021's `_ALLOWED_METADATA_KEYS` whitelist, (c) links to `src/kosmos/observability/event_logger.py` as the single source of truth hierarchy (data-model.md §E4), (d) states that new `patient.*` keys require a dual-edit (Python whitelist first, collector rules second). Depends on T009 creating the file.

**Checkpoint**: US2 complete. Both US1 and US2 are independently functional; stack bring-up works without the PII test passing, and the PII test can be run against any correctly-configured collector.

---

## Phase 5: Polish and Cross-Cutting Concerns

**Purpose**: Cross-story documentation reconciliation, deferred-item placeholder back-fill, and quickstart end-to-end walkthrough validation.

- [ ] T014 [P] Cross-check `/Users/um-yunsang/KOSMOS-501/specs/028-otlp-collector/spec.md` and `/Users/um-yunsang/KOSMOS-501/specs/028-otlp-collector/plan.md` for any remaining `[NEEDS TRACKING — Phase 3 observability epic (TBD issue #)]` placeholders. Leave as-is (they are back-filled by `/speckit-taskstoissues`) but confirm count matches research.md § 2 audit (expected: 7 distinct rows).
- [ ] T015 [P] Verify `/Users/um-yunsang/KOSMOS-501/pyproject.toml` has **zero** new entries under `[project.dependencies]` and `[project.optional-dependencies]` vs. the commit before this feature branch. Command: `git -C /Users/um-yunsang/KOSMOS-501 diff main..HEAD -- pyproject.toml` — output must be empty. Satisfies SC-005 + FR-012.
- [ ] T016 [P] Verify `/Users/um-yunsang/KOSMOS-501/docker/Dockerfile` is untouched vs. `main`. Command: `git -C /Users/um-yunsang/KOSMOS-501 diff main..HEAD -- docker/Dockerfile` — output must be empty. Satisfies FR-013.
- [ ] T017 Run `uv run pytest` from the worktree root with `OTEL_SDK_DISABLED=true` and `OTEL_EXPORTER_OTLP_ENDPOINT` unset. All tests MUST pass, zero OTLP network attempts. Satisfies SC-004.
- [ ] T018 Execute `quickstart.md` end-to-end (all six sections, including teardown) on a fresh worktree checkout. Capture timings for SC-001 (bootstrap < 10 min) and SC-002 (trace visible < 10 s). Record in PR description.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: no dependencies, starts immediately.
- **Phase 2 (Foundational)**: depends on Phase 1 (T001). T002 + T003 are parallel; T004 depends on T002.
- **Phase 3 (US1)**: depends on Phase 2 completion (T002, T003, T004 all done).
- **Phase 4 (US2)**: depends on Phase 2 completion AND a running local stack for T011 verification. Can run fully in parallel with Phase 3 once Phase 2 is done.
- **Phase 5 (Polish)**: depends on Phases 3 and 4 complete.

### User Story Dependencies

- **US1 (P1)**: After Phase 2. No dependency on US2.
- **US2 (P2)**: After Phase 2. T011 + T012 require a running stack, which means US1's T007+T008 must be mergeable-valid for the stack to come up. In practice: US2 tests the same `config.yaml` that US1 ships, so they share Phase 2 but not Phase 3.

### Within Each User Story

- Tests (T005, T006, T011) are CI-safe or `@pytest.mark.live`-gated; they may be written before or after implementation without breaking AGENTS.md.
- US1 implementation order: T007 (compose `otelcol` service) → T008 (re-pin Langfuse) → T009 (docs) → T010 (local smoke). T007 + T008 touch the same file, so they are sequential.
- US2 order: T011 (test) → T012 (verify) → T013 (docs).

### Parallel Opportunities

Across the whole spec:

- T002, T003 parallel (different files).
- T005, T006 parallel (different test files).
- T009 parallel with T007 + T008 (docs file is orthogonal to compose file).
- T011 parallel with all of Phase 3 (different files).
- T014, T015, T016 parallel (three independent verifications).

---

## Parallel Example: Phase 2 Foundational

```bash
# Foundational parallel-safe pair:
Task: "T002 Copy contracts/collector-config.yaml to infra/otel-collector/config.yaml"
Task: "T003 Append three KOSMOS_ vars to .env.example"
```

## Parallel Example: Phase 3 User Story 1

```bash
# Test scaffolding in parallel:
Task: "T005 Add tests/infra/test_docker_compose_dev.py (compose config lint)"
Task: "T006 Add tests/infra/test_compose_services.py (service-field assertions)"

# Docs in parallel with compose edits (different files):
Task: "T009 Create docs/observability.md"
# runs alongside:
Task: "T007 Modify docker-compose.dev.yml to add otelcol service"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 (T001).
2. Complete Phase 2 (T002 → T003 → T004) — blocks all stories.
3. Complete Phase 3 US1 (T005–T010) — KSC demo operator bring-up path is live.
4. **STOP + DEMO**: run `quickstart.md §1–§4`, verify the three-level span tree.
5. Optionally ship US1 as a standalone PR before picking up US2.

### Incremental Delivery

1. Phase 1 + Phase 2 → foundation ready.
2. Phase 3 US1 → MVP demo-ready.
3. Phase 4 US2 → PII second-gate verified; full PIPA §26 defence-in-depth.
4. Phase 5 polish → reconcile docs, confirm zero-deps invariants, close Epic #501 (local-dev scope).

### Parallel Team Strategy

This spec is **infrastructure-only**; most tasks are parallel-safe across story boundaries. Two Sonnet Teammates can staff:

- Teammate A: T002, T007, T008 (compose + runtime config wiring).
- Teammate B: T003, T009, T011, T013 (env + docs + live test).

Lead synthesises T004, T010, T014–T018 after Teammates hand off.

---

## Notes

- [P] tasks touch different files and have no dependency on incomplete tasks.
- [Story] label maps to `spec.md` user stories (US1 = P1, US2 = P2).
- **No `src/` changes** — this is a pure infrastructure spec (FR-012, FR-013).
- **No new Python runtime deps** — verified by T015 (SC-005).
- All absolute paths assume the worktree at `/Users/um-yunsang/KOSMOS-501/`. The identical path layout applies to the eventual merge target at `/Users/um-yunsang/KOSMOS/`.
- Commit boundaries should fall on phase boundaries (one commit per phase) or on US boundaries for easier revert; do not mix US1 compose edits with US2 test scaffolding in a single commit.
- The collector image digest `sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114` is the manifest-list digest resolved in `research.md §1`; air-gapped operators pre-pull the per-arch digests documented in the same section.
