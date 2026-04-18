# Implementation Plan: OTLP Collector + Local Langfuse Stack

**Branch**: `feat/501-otlp-collector` (spec slug `028-otlp-collector`) | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/028-otlp-collector/spec.md`
**Parent Epic**: #501 — Production OTLP Collector & Centralized Langfuse Operations

## Summary

Add an `otel/opentelemetry-collector-contrib:0.105.0` sidecar to the existing `docker-compose.dev.yml` so that KOSMOS spans travel `KOSMOS app → otelcol → langfuse-web` instead of pointing the SDK directly at Langfuse. The collector runs a single pipeline — `otlphttp` receiver → `attributes/pii_redact` processor → `batch` processor → `otlphttp` exporter — with the exporter targeting `http://langfuse-web:3000/api/public/otel/v1/traces` (Langfuse v3's OTel ingest path, introduced in v3.22.0). The PII redaction gate deletes every `patient.*` attribute and SHA-256-hashes `kosmos.location.query`, giving KOSMOS a second PII boundary beyond `ObservabilityEventLogger` (spec 021 FR-011). Langfuse images are bumped from the floating `3` tag to an explicit `3.35.0` pin; the collector image is pinned by multi-arch digest so that Apple Silicon (`linux/arm64`) KSC 2026 demo laptops produce byte-identical container rootfs layers to the amd64 CI reference. Scope is **local developer workflow + KSC 2026 laptop demo only**; production deployment (Fly.io / Railway, TLS, Langfuse Cloud Hobby, CI OIDC) is carved out to a Phase 3 observability Epic.

**Zero new Python runtime dependencies** (FR-012). The collector is an external process; the KOSMOS Python app already emits OTLP via spec 021's three deps (`opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-semantic-conventions`). No `pyproject.toml` change, no `docker/Dockerfile` change, no `src/` change.

## Technical Context

**Language/Version**: N/A for Python (no Python change). Infrastructure spec only. Container runtime: Docker Engine 24+ with Compose v2 (declared in `docker-compose.dev.yml` v3.8 schema via implicit default). Collector binary: `otel/opentelemetry-collector-contrib:0.105.0` (Go 1.22 compiled, Apache-2.0).
**Primary Dependencies**: **One new container image** — `otel/opentelemetry-collector-contrib:0.105.0` (Apache-2.0). **Two re-pinned images** — `langfuse/langfuse:3.35.0` + `langfuse/langfuse-worker:3.35.0` (replacing floating `3` tag). No Python runtime deps added (FR-012).
**Storage**: N/A — the collector's `batch` processor is an in-memory queue (512-span max, 5 s timeout). All persistence is delegated to the existing Langfuse backend (Postgres 16-alpine metadata, ClickHouse 24.8-alpine span analytics, MinIO blob store). No new volumes.
**Testing**: `pytest` + `pytest-asyncio` (existing). New tests are config-validation and bring-up smoke tests: (a) YAML schema lint of `infra/otel-collector/config.yaml` via the collector's own `--dry-run` / `validate` flag run inside a throwaway container, (b) docker-compose `config` validation in CI, (c) marker-gated `@pytest.mark.live` test that asserts a SHA-256 hash replaced `kosmos.location.query` when traversing the collector — skipped by default per AGENTS.md hard rule "Never call live `data.go.kr` APIs from CI tests" and extended here to "never require a live Langfuse in CI".
**Target Platform**: macOS (Apple Silicon `linux/arm64` via Docker Desktop) and Linux (`linux/amd64`) developer workstations. KSC 2026 demo machines are MacBook Pro (M-series) — `linux/arm64` digest correctness is a pre-demo blocker.
**Project Type**: Infrastructure — changes are confined to `docker-compose.dev.yml`, a new `infra/otel-collector/` directory, `.env.example`, and `docs/observability.md`. No application source change.
**Performance Goals**: Bootstrap budget SC-001 — `docker compose up -d` → first trace visible in Langfuse UI ≤ 10 minutes (includes first-run image pulls). End-to-end span latency budget — ≤ 10 seconds from agent emit to Langfuse visibility (SC-002).
**Constraints**: (a) No new Python runtime dependency (FR-012, AGENTS.md hard rule). (b) `docker/Dockerfile` untouched (FR-013). (c) `src/` untouched. (d) All new env vars `KOSMOS_`-prefixed (AGENTS.md). (e) Only `langfuse/langfuse:3.35.0+` (OTel endpoint was introduced in v3.22.0; FR-008a pins `3.35.0` for KSC reproducibility). (f) Collector config is read-only (`:ro` mount, FR-002). (g) gRPC receiver not exposed (only OTLP HTTP :4318, FR-003). (h) `OTEL_SDK_DISABLED=true` must still green-bar every pytest (SC-004, spec 021 FR-014 inheritance).
**Scale/Scope**: Single-operator local workstation, one KOSMOS CLI session at a time. Span volume budget ~200 spans per demo scenario (~3 minute session, ~10 agent turns × ~20 spans/turn). Zero multi-tenant isolation concerns at this scope (carved out to Phase 3).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
|---|---|---|
| I. Reference-Driven Development | Every design decision maps to OTel Collector upstream docs, Langfuse self-host docs, or spec 021's observability foundation. Concrete reference citations are enumerated in `research.md § References`. Claude Code parallel: this is an **infrastructure-layer** change outside the six-layer map, but the overall observability philosophy (trace the tool loop so the operator can see what the model did) is Claude Code's debugging-first reference. | PASS |
| II. Fail-Closed Security (NON-NEGOTIABLE) | (a) PII redaction is **additive** — span data passes *first* through `ObservabilityEventLogger` whitelist (spec 021 FR-011, Python layer), *then* through the collector's `attributes/pii_redact` processor. Failure of either gate still blocks `patient.*` leakage. (b) Collector config is mounted read-only (`:ro`). (c) Auth header is environment-sourced, empty default; no hardcoded keys. (d) When `OTEL_EXPORTER_OTLP_ENDPOINT` is unset the KOSMOS app **warn-and-skips** (spec 021 FR-010) — observability failure never breaks the app. | PASS |
| III. Pydantic v2 Strict Typing (NON-NEGOTIABLE) | No new Python models added (FR-012). YAML config at `infra/otel-collector/config.yaml` is validated at container startup by the Collector binary's own schema; no `Any`-typed Python code is introduced. | PASS (N/A for new code) |
| IV. Government API Compliance | No `data.go.kr` calls added, modified, or CI-enabled. Observability layer wraps existing adapter spans emitted by spec 021; the collector is transport-only. Smoke tests requiring a running Langfuse are `@pytest.mark.live` gated (skipped in CI). | PASS |
| V. Policy Alignment (PIPA §26 carve-out) | The `attributes/pii_redact` processor is the **controller-level second gate**. `patient.*` wildcard delete + `kosmos.location.query` SHA-256 hash reduces the data-processor attack surface one hop before traces hit the Langfuse backend. Defence-in-depth alignment with project PIPA role (controller-level carve-out at synthesis layer only; everywhere else KOSMOS acts as processor). | PASS |
| VI. Deferred Work Accountability | spec.md § Scope Boundaries enumerates 10 deferred items with the Phase 3 observability Epic placeholder (`[NEEDS TRACKING]`) or concrete tracking issue (#502, #503, #507). Phase 0 research.md validates: (a) no unregistered "future/phase 2+" prose outside the Deferred table, (b) `NEEDS TRACKING` markers are back-fillable by `/speckit-taskstoissues`. | PASS |

**Gate result**: PASS (no violations; Complexity Tracking intentionally empty).

### Post-Design Re-check (after Phase 1)

After writing `research.md`, `data-model.md`, `contracts/collector-config.yaml`, `contracts/env-reference.md`, and `quickstart.md`, all six principles re-evaluate to PASS with the same rationale. The Phase 1 artefacts add **no new deferrals** and **no new dependencies** beyond what's declared in spec.md. `Complexity Tracking` remains empty.

## Project Structure

### Documentation (this feature)

```text
specs/028-otlp-collector/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # Feature specification
├── research.md          # Phase 0 output — ref citations + Clarification #3 digest resolution
├── data-model.md        # Phase 1 output — config entities + redaction rule schema
├── quickstart.md        # Phase 1 output — one-command bootstrap walkthrough
├── contracts/
│   ├── collector-config.yaml    # Phase 1 — authoritative collector pipeline config
│   └── env-reference.md         # Phase 1 — KOSMOS_OTEL_* env var contract
└── tasks.md             # (/speckit-tasks output — NOT created by /speckit-plan)
```

### Infrastructure and config (repository root)

```text
docker-compose.dev.yml        # MODIFY — add `otelcol` service; re-pin langfuse images to 3.35.0
infra/
└── otel-collector/
    └── config.yaml           # NEW — collector pipeline: receiver → pii_redact → batch → exporter
.env.example                  # MODIFY — add KOSMOS_OTEL_COLLECTOR_PORT, KOSMOS_LANGFUSE_OTLP_ENDPOINT, KOSMOS_LANGFUSE_OTLP_AUTH_HEADER
docs/
└── observability.md          # NEW — local stack guide, span tree diagram, env ref, troubleshooting

# EXPLICITLY NOT TOUCHED (spec § File Inventory):
docker/Dockerfile             # unchanged — no Python app change
pyproject.toml                # unchanged — no new Python deps (FR-012)
src/                          # unchanged
specs/021-observability-otel-genai/  # read-only predecessor reference
```

**Structure Decision**: Pure **infrastructure spec** — three file creations (`infra/otel-collector/config.yaml`, `docs/observability.md`, `specs/028-otlp-collector/*`), two file modifications (`docker-compose.dev.yml`, `.env.example`). No Python package layout change. No new module. No new test directory. The `infra/otel-collector/` directory parallels the existing `infra/copilot-gate-app/` convention (one subdirectory per external infra component).

## Complexity Tracking

> No constitution violations. Complexity Tracking intentionally empty.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | — | — |
