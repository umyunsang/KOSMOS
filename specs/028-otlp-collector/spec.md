# Feature Specification: OTLP Collector + Local Langfuse Stack

**Spec number**: 028
**Feature branch**: `feat/501-otlp-collector`
**Parent epic**: #501 — Production OTLP Collector & Centralized Langfuse Operations
**Created**: 2026-04-18
**Status**: Draft

---

## Scope Statement

This spec covers the **local developer workflow only**: running OTel Collector Contrib + the existing Langfuse v3 stack from `docker-compose.dev.yml` to visualize KOSMOS span trees during KSC 2026 demo sessions. It does **not** cover the production deployment scenario described in the Epic body (Fly.io/Railway, Langfuse Cloud Hobby, TLS, CI integration). Those are deferred — see the Deferred Items table.

The two goals of this spec are:

1. Add an `otelcol-contrib` sidecar to the existing `docker-compose.dev.yml` so that KOSMOS spans travel `KOSMOS app → Collector → Langfuse` instead of `KOSMOS app → Langfuse` directly. This layer allows PII attribute redaction and batch buffering before traces reach Langfuse.

2. Pin all container image versions and validate that `docker compose -f docker-compose.dev.yml up -d` still starts a healthy Langfuse UI at `:3000` with traces visible within 10 seconds of a test agent call.

The existing `docker-compose.dev.yml` (shipped by spec 021) already contains all Langfuse backend services (Postgres 16-alpine, Redis 7-alpine, ClickHouse 24.8-alpine, MinIO). This spec extends that file; it does not replace it.

---

## User Scenarios and Testing

### User Story 1 — KSC demo operator brings up the full observability stack in one command (Priority: P1)

A student demonstrator running KOSMOS on a MacBook opens one terminal, runs `docker compose -f docker-compose.dev.yml up -d`, then starts the KOSMOS CLI in another terminal. Within 10 seconds of an agent call, the Langfuse UI at `http://localhost:3000` shows the trace with a three-level span tree: `invoke_agent kosmos-query` → `chat` → `execute_tool <tool_id>`.

**Why this priority**: The KSC 2026 demo is the primary acceptance test for this spec. Without a working local trace visualization, the observability thesis ("tool loop trace visualization") cannot be demonstrated live.

**Independent test**: On a fresh clone, run `docker compose -f docker-compose.dev.yml up -d`. After all containers reach `healthy`, execute a single-turn agent call (captured fixture, no live API call). Open Langfuse at `http://localhost:3000` and verify the trace tree appears.

**Acceptance scenarios**:

1. **Given** Docker Desktop is running and no previous volumes exist, **When** `docker compose -f docker-compose.dev.yml up -d` is executed, **Then** within 120 seconds all containers (`langfuse-web`, `langfuse-worker`, `otelcol`, `postgres`, `redis`, `clickhouse`, `minio`) report `healthy` and Langfuse UI at `:3000` returns HTTP 200.
2. **Given** the full stack is running, **When** a KOSMOS agent session emits a trace (one `invoke_agent` + one `chat` + one `execute_tool`), **Then** the `invoke_agent` span and its two children appear under the same trace ID in Langfuse within 10 seconds.
3. **Given** `OTEL_SDK_DISABLED=true` is set in the host environment, **When** the agent session runs, **Then** no spans are exported and all pytest unit tests still pass.

---

### User Story 2 — Developer verifies PII is redacted before reaching Langfuse (Priority: P2)

A developer runs a test that deliberately includes a `patient.name` attribute in a span. They confirm via Langfuse UI that the attribute is absent from the stored trace, while the span itself and all non-PII attributes are intact.

**Why this priority**: Spec 021 FR-011 established the `ObservabilityEventLogger` PII whitelist at the Python layer. This spec adds a second redaction gate at the collector level, satisfying the PIPA §26 data processor duty.

**Acceptance scenarios**:

1. **Given** a test span includes a `patient.name` attribute, **When** the span is exported via the collector, **Then** the span in Langfuse has no `patient.name` attribute (verified by Langfuse API, not UI screenshot).
2. **Given** a `resolve_location` span includes a raw `kosmos.location.query` string, **When** the span passes through the collector, **Then** the stored attribute is the SHA-256 hash of the query, not the raw string.

---

### Edge Cases

- **Collector container not running**: KOSMOS app falls back to warning-only log (inherited from spec 021 FR-010). No user-visible error.
- **Langfuse ClickHouse startup slow**: Collector buffers spans in the `batch` processor queue (up to 512 spans, 5 second timeout). Spans are not lost during the typical 30–60 second ClickHouse cold-start.
- **Image digest mismatch on air-gapped machine**: Compose file pins images by digest. If the machine cannot pull, the operator must pre-pull and load the images manually. This is documented in `docs/observability.md`.
- **Port 4318 (OTLP HTTP) in use**: The collector exposes OTLP HTTP on port 4318 by default. If the port is occupied, the operator sets `KOSMOS_OTEL_COLLECTOR_PORT` to override.

---

## Requirements

### Functional Requirements

#### Docker Compose changes

- **FR-001**: `docker-compose.dev.yml` adds one new service `otelcol` running `otel/opentelemetry-collector-contrib:0.105.0` (pinned by digest; see image pinning table in the Deferred Items section). The service starts after `langfuse-web` reaches `healthy` and depends on `langfuse-web`.
- **FR-002**: The `otelcol` service mounts a read-only config volume: `./infra/otel-collector/config.yaml:/etc/otelcol-contrib/config.yaml:ro`. No runtime mutation of collector config.
- **FR-003**: The `otelcol` service exposes OTLP HTTP on port 4318 (`${KOSMOS_OTEL_COLLECTOR_PORT:-4318}:4318`). gRPC port 4317 is not exposed.
- **FR-004**: The `otelcol` service has a `healthcheck` that hits `http://localhost:13133/` (pprof extension disabled; health_check extension enabled). Retry: 10 times at 5-second intervals.

#### Collector pipeline (`infra/otel-collector/config.yaml`)

- **FR-005**: The collector pipeline is `otlphttp` receiver → `attributes/pii_redact` processor → `batch` processor → `otlphttp` exporter. No other processors or exporters.
- **FR-006**: The `attributes/pii_redact` processor applies the following rules via the OTel Collector `attributes` processor `delete` action:
  - Delete `patient.*` (wildcard pattern)
  - Hash `kosmos.location.query` via `hash` action (SHA-256 output stored back in the same key)
- **FR-007**: The `batch` processor is configured with `timeout: 5s` and `send_batch_size: 512`.
- **FR-008**: The `otlphttp` exporter sends spans to the Langfuse OTLP ingest endpoint. The URL is `${KOSMOS_LANGFUSE_OTLP_ENDPOINT:-http://langfuse-web:3000/api/public/otel/v1/traces}`. The exporter sets the `Authorization` header to `Basic <base64(pk-xxx:sk-xxx)>` sourced from `${KOSMOS_LANGFUSE_OTLP_AUTH_HEADER:-}`. The header `x-langfuse-ingestion-version: 4` is also set for real-time preview. If `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` is empty, the exporter sends without auth (acceptable for local dev with anonymous project).
- **FR-008a**: The Langfuse version requirement is `langfuse/langfuse:3.22.0` or later (OTel OTLP endpoint was introduced in v3.22.0). For KSC 2026 demo reproducibility, the `docker-compose.dev.yml` pins `langfuse/langfuse:3.35.0` and `langfuse/langfuse-worker:3.35.0` (explicit minor pin). Alpine variant availability (`3.35.0-alpine`) is confirmed during plan Phase 0 research.
- **FR-008b**: First-run API key setup is manual via the Langfuse UI. `docker-compose.dev.yml` does not auto-seed a project or keys (Langfuse v3 does not support env-var-based project seeding). `docs/observability.md` documents the 5-step first-run procedure (navigate to `http://localhost:3000` → create organization → create project → copy public key + secret key → paste into `.env`).

#### KOSMOS app configuration

- **FR-009**: When `OTEL_EXPORTER_OTLP_ENDPOINT` is not set in the KOSMOS app environment, the app logs a warning and disables export (inherited from spec 021 FR-010). For local dev, the operator sets `OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318`.
- **FR-010**: The `.env.example` file is updated with the following new variables and their descriptions:
  - `KOSMOS_OTEL_COLLECTOR_PORT` — host port for OTLP HTTP receiver (default 4318)
  - `KOSMOS_LANGFUSE_OTLP_ENDPOINT` — Langfuse OTLP ingest URL for the collector exporter (default `http://langfuse-web:3000/api/public/otel/v1/traces`)
  - `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` — `Basic <base64(pk-xxx:sk-xxx)>` for Langfuse OTLP auth (empty = anonymous)

#### Documentation

- **FR-011**: `docs/observability.md` is created (or updated if it exists) with sections: stack overview, span tree diagram (ASCII), one-command bootstrap steps, environment variable reference, and a troubleshooting section covering the three most common failure modes (collector not starting, no traces in Langfuse, port conflict).

#### No new Python runtime dependencies

- **FR-012**: This spec introduces zero new Python runtime dependencies. The collector is an external process; the Python app already emits OTLP via spec 021's three dependencies. No new entry in `pyproject.toml` `[project.dependencies]`.

#### No new Docker infrastructure services (Python app)

- **FR-013**: The `docker/Dockerfile` and `pyproject.toml` are not modified by this spec.

### Key Entities

- **OTel Collector Contrib service** (`otelcol`): the new docker-compose service that receives, processes, and forwards spans.
- **Collector config** (`infra/otel-collector/config.yaml`): declarative YAML defining the pipeline. Single source of truth for PII redaction rules.
- **OTLP ingest endpoint**: the URL the KOSMOS Python app points `OTEL_EXPORTER_OTLP_ENDPOINT` to — `http://localhost:4318` in dev (the collector's exposed port).
- **Langfuse OTLP endpoint**: the URL the collector exporter points to — `http://langfuse-web:3000/api/public/otel/v1/traces` inside the compose network (host-accessible at `http://localhost:3000/api/public/otel/v1/traces`). Protocol: HTTP/JSON or HTTP/protobuf; gRPC is not supported by Langfuse v3.

---

## Success Criteria

- **SC-001** (bootstrap time): From `docker compose up -d` to first trace visible in Langfuse UI — under 10 minutes, including Docker image pulls.
- **SC-002** (span tree): A single agent session emitting `invoke_agent` + `chat` + `execute_tool` appears as a three-level span tree in a single Langfuse trace.
- **SC-003** (PII redaction): A test span injected with `patient.name` has that attribute absent in Langfuse (verified via Langfuse public API response body, not UI screenshot).
- **SC-004** (CI passthrough): `OTEL_SDK_DISABLED=true` + no collector running: 100% pytest pass, zero OTLP export attempts.
- **SC-005** (zero new Python deps): `pyproject.toml` diff shows no new entries under `[project.dependencies]`.
- **SC-006** (image pins): All four new or re-pinned container images in `docker-compose.dev.yml` have explicit digest pins in a comment field (for reproducibility).

---

## Assumptions

- Langfuse v3.22.0+ accepts OTLP/HTTP on `/api/public/otel/v1/traces` (confirmed in Langfuse official docs "opentelemetry/get-started"; HTTP/JSON and HTTP/protobuf are supported; gRPC is not supported).
- The KSC demo machine has at least 8 GB RAM free: Langfuse stack (from spec 021) requires ~4 GB; the `otelcol-contrib` container adds ~256 MB.
- The `otel/opentelemetry-collector-contrib:0.105.0` image supports the `attributes` processor with `hash` action. This was introduced in Collector Contrib v0.92.0.
- Langfuse project creation and API key generation (public + secret) are done manually in the UI after first boot (Langfuse v3 does not support env-var-based project seeding). The `.env.example` and `docs/observability.md` document the 5-step first-run procedure.

---

## Scope Boundaries and Deferred Items

### Out of scope (this spec)

Spec 028 is **local dev + KSC 2026 laptop demo only**. The following items are explicitly carved out into the **Phase 3 observability Epic** (placeholder: `[NEEDS TRACKING — Phase 3 observability epic (TBD issue #)]`; real issue number will be back-filled at `/speckit-taskstoissues` time):

- **Production OTLP collector deployment** — Fly.io / Railway hosting, TLS termination (`otel.kosmos.<domain>`), public collector endpoint.
- **Langfuse Cloud Hobby integration** — External SaaS Langfuse Cloud as alternative to self-hosted; cost/quota analysis vs self-hosted.
- **TLS configuration** for both OTLP receiver and Langfuse OTLP exporter.
- **CI OIDC injection** of `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` via Infisical (depends on #468 being stable).
- **Per-environment Langfuse project isolation** (`kosmos-dev`, `kosmos-ci`, `kosmos-prod`).
- **Live CI smoke test** (`tests/live/test_trace_emission.py`) against the production collector endpoint.
- **Metrics pipeline**: `otelcol` is configured for traces only. Metrics and logs pipelines remain out of scope (consistent with spec 021).
- **OTel Logs signal**: deferred per spec 021 Deferred Items (tracking issue #502).
- **Span sampling / filtering policy**: deferred per spec 021 (tracking issue #503).
- **Span-attribute boundary lock** (Section C of Epic #501): coordinated with #507; boundary contracts are documented in `docs/observability.md` as informational only in this spec. Normative lock depends on #507.

### Deferred Items Table

| Item | Reason | Target Epic / Issue |
|---|---|---|
| Production OTLP collector deployment (Fly.io / Railway, TLS, `otel.kosmos.<domain>`) | Cost-constrained; local dev is the KSC demo target. Production infra requires #468 Infisical OIDC to be stable first. | #897 |
| Langfuse Cloud Hobby integration | External SaaS dependency; cost/quota analysis pending. Revisit if self-hosted quota becomes a constraint. | #899 |
| TLS configuration (receiver + exporter) | Not required for local dev or KSC demo LAN. Required for production. | #901 |
| CI pipeline `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` injection via Infisical OIDC | Depends on #468 (OIDC) being stable. | #903 |
| Per-environment Langfuse project isolation (`kosmos-dev`, `kosmos-ci`, `kosmos-prod`) | Not meaningful until CI integration is in scope. | #907 |
| Live CI smoke test (`tests/live/test_trace_emission.py`) | Requires production collector endpoint. | #910 |
| `redaction.yaml` split (separate file for redaction rules) | Epic body mentions this file; current spec inlines rules in `config.yaml` for simplicity. Extract when rule count exceeds 10. | #912 |
| Span-attribute normative lock (Section C of Epic #501) | Depends on #507 facade + adapter span-name stabilization. | #507 |
| OTel Logs signal integration | Spec 021 explicit deferral. | #502 |
| Span sampling / filtering | Spec 021 explicit deferral. | #503 |

---

## New Dependencies

### Container images (not Python runtime dependencies)

| Image | Version | Purpose | License |
|---|---|---|---|
| `otel/opentelemetry-collector-contrib` | `0.105.0` | OTLP receiver, PII processor, batch processor, OTLP exporter | Apache-2.0 |

No new Python runtime dependencies (FR-012).

The following images are updated to explicit minor pins by this spec (required for KSC 2026 demo reproducibility):

| Image | Previous tag | New pinned version | Note |
|---|---|---|---|
| `langfuse/langfuse` | `3` (floating) | `3.35.0` | OTel endpoint requires >= v3.22.0; `3.35.0` is the KSC pin |
| `langfuse/langfuse-worker` | `3` (floating) | `3.35.0` | Must match `langfuse/langfuse` minor version |

Alpine variant availability (`3.35.0-alpine`) is to be confirmed during plan Phase 0 research via `docker buildx imagetools inspect langfuse/langfuse:3.35.0`. If the alpine variant exists, prefer it for image size.

The remaining existing images are unchanged:

| Image | Version |
|---|---|
| `postgres` | `16-alpine` |
| `redis` | `7-alpine` |
| `clickhouse/clickhouse-server` | `24.8-alpine` |
| `minio/minio` | `RELEASE.2024-11-07T00-52-20Z` |

---

## Environment Variables Reference

All variables follow the `KOSMOS_` prefix rule (AGENTS.md hard rule).

| Variable | Default | Description |
|---|---|---|
| `KOSMOS_OTEL_COLLECTOR_PORT` | `4318` | Host port for the `otelcol` OTLP HTTP receiver |
| `KOSMOS_LANGFUSE_OTLP_ENDPOINT` | `http://langfuse-web:3000/api/public/otel/v1/traces` | URL the collector exporter sends spans to (inside compose network) |
| `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` | `` (empty) | `Basic <base64(pk-xxx:sk-xxx)>` for Langfuse OTLP auth |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | (not set) | Python app: OTLP endpoint — set to `http://localhost:4318` for local dev |

Existing variables (from spec 021) are unchanged.

---

## File Inventory

Files created or modified by this spec:

| Path | Change |
|---|---|
| `docker-compose.dev.yml` | Add `otelcol` service; add `otelcol` to healthcheck dependency chain |
| `infra/otel-collector/config.yaml` | New file — collector pipeline definition |
| `.env.example` | Add three new `KOSMOS_` variables with inline comments |
| `docs/observability.md` | New file — local stack guide, span tree diagram, env reference, troubleshooting |

Files explicitly not touched:

| Path | Reason |
|---|---|
| `docker/Dockerfile` | No Python app change |
| `pyproject.toml` | No new Python deps |
| `src/` | No Python app change |
| `specs/021-observability-otel-genai/` | Predecessor spec; read-only reference |

---

## Clarifications

[RESOLVED 2026-04-18] **#1 — Langfuse OTLP ingest path**: Confirmed from Langfuse official docs ("opentelemetry/get-started"). Ingest URL is `http://langfuse-web:3000/api/public/otel/v1/traces` (compose-internal); `http://localhost:3000/api/public/otel/v1/traces` from host. Protocol: HTTP/JSON or HTTP/protobuf; gRPC is not supported. Auth header: `Authorization: Basic <base64(pk-xxx:sk-xxx)>` + `x-langfuse-ingestion-version: 4`.

[RESOLVED 2026-04-18] **#2 — Image version pin**: `langfuse/langfuse:3` floating tag replaced by explicit minor pin `3.35.0` in this spec (minimum required: `3.22.0` — that is when the OTel endpoint was introduced). KSC demo uses `3.35.0`. Alpine variant (`3.35.0-alpine`) to be confirmed in plan Phase 0 via `docker buildx imagetools inspect`.

[NEEDS CLARIFICATION] **#3 — `otel/opentelemetry-collector-contrib:0.105.0` image digest for `linux/arm64`**: For air-gapped or fully reproducible builds, SHA-256 digest pins are preferred for both `linux/amd64` and `linux/arm64` (Apple Silicon KSC demo machines). Confirm digests in plan Phase 0 research via `docker buildx imagetools inspect otel/opentelemetry-collector-contrib:0.105.0`. Spec records "TBD in plan Phase 0 research".

[RESOLVED 2026-04-18] **#4 — Langfuse API key auto-seeding**: Langfuse v3 does not support env-var-based initial project or API key seeding. First-run API key setup is manual via the Langfuse UI. This is the confirmed behavior; `docs/observability.md` will document the 5-step procedure (see FR-008b).

[RESOLVED 2026-04-18] **#5 — Scope alignment with Epic #501 body**: Spec 028 covers local dev + KSC 2026 laptop demo only. Production deployment (Fly.io/Railway, Langfuse Cloud Hobby, TLS, CI OIDC) is explicitly carved out to a Phase 3 observability Epic (see Out of Scope section). No spec split needed; the Phase 3 Epic is tracked as `[NEEDS TRACKING — Phase 3 observability epic (TBD issue #)]` until `/speckit-taskstoissues` back-fills the real issue number.
