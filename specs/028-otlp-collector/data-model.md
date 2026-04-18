# Phase 1 Data Model: OTLP Collector + Local Langfuse Stack

**Spec**: 028-otlp-collector | **Date**: 2026-04-18

This spec introduces **no new Python models**. "Data model" here refers to the **declarative config schemas** that govern the collector pipeline and the environment variable contract. These are configuration entities, not runtime domain objects; validation is performed by the OTel Collector binary at container startup (Go-side schema) and by Docker Compose's own schema validator.

---

## E1. OtelcolService (docker-compose service entity)

Represents the new `otelcol` entry added to `docker-compose.dev.yml`.

**Fields**:

| Field | Type | Value / Source | Validation |
|---|---|---|---|
| `image` | string (image-ref@digest) | `otel/opentelemetry-collector-contrib@sha256:3ff721e65733a9c2d94e81cfb350e76f1cd218964d5608848e2e73293ea88114` | Must be manifest-list digest (multi-arch); per-arch digests captured in inline comment per research.md §1 |
| `restart` | enum | `unless-stopped` | Matches sibling Langfuse services |
| `depends_on.langfuse-web.condition` | enum | `service_healthy` | Blocks collector start until Langfuse web is responsive |
| `volumes` | list[VolumeMount] | `["./infra/otel-collector/config.yaml:/etc/otelcol-contrib/config.yaml:ro"]` | Read-only mount (`:ro` required by FR-002) |
| `ports` | list[PortMap] | `["${KOSMOS_OTEL_COLLECTOR_PORT:-4318}:4318"]` | Only OTLP HTTP exposed; gRPC port 4317 intentionally unexposed (FR-003) |
| `environment` | map[string, string] | See E3 EnvironmentContract | All keys `KOSMOS_`-prefixed |
| `healthcheck.test` | list[string] | `["CMD", "wget", "--spider", "-q", "http://localhost:13133/"]` | Hits health_check extension endpoint |
| `healthcheck.interval` | duration | `5s` | |
| `healthcheck.retries` | int | `10` | Matches FR-004 "10 times at 5-second intervals" |

**Relationships**:
- Depends on `langfuse-web` (healthcheck-gated).
- Consumed by external KOSMOS app process (outside compose network) via host port `:4318`.

**Invariants**:
- The `:ro` flag on the config volume is a **fail-closed invariant** — a compose file without it must fail `/speckit-analyze`.
- `depends_on.langfuse-web.condition: service_healthy` ensures the exporter never attempts to write before Langfuse web is ready; otherwise spans would be dropped by the collector's retry logic.

---

## E2. CollectorPipelineConfig (`infra/otel-collector/config.yaml`)

Represents the collector's declarative YAML pipeline. Schema is owned by the OTel Collector binary (Go-side). Full concrete instance lives in `contracts/collector-config.yaml`.

**Top-level sections**:

| Section | Presence | Sub-entities |
|---|---|---|
| `extensions` | required | `health_check` |
| `receivers` | required | `otlp` (HTTP sub-protocol only) |
| `processors` | required | `attributes/pii_redact`, `batch` |
| `exporters` | required | `otlphttp` |
| `service.pipelines.traces` | required | wires the above in single-pipeline form |
| `service.telemetry` | optional | (not enabled at this scope) |

### E2.1 Receivers — `otlp`

| Field | Value | Note |
|---|---|---|
| `protocols.http.endpoint` | `0.0.0.0:4318` | Binds all interfaces inside container |
| `protocols.http.include_metadata` | `false` | No HTTP metadata propagation (PII concern) |
| `protocols.grpc` | _(omitted)_ | Explicit non-presence is the FR-003 contract |

### E2.2 Processors

**`attributes/pii_redact`** (FR-006):

| Action | Key pattern | Op | Rationale |
|---|---|---|---|
| `delete` | `patient.name` | delete | PIPA §26 — personal identifier |
| `delete` | `patient.phone` | delete | PIPA §26 |
| `delete` | `patient.rrn` | delete | PIPA §26 — resident registration number |
| `delete` | `patient.address` | delete | PIPA §26 |
| `hash` | `kosmos.location.query` | SHA-256 | Preserves cardinality for analytics while redacting raw query text |

Note: The OTel Collector `attributes` processor does **not support wildcard matching** in `actions[].key`. The spec.md phrasing "Delete `patient.*` (wildcard pattern)" is therefore realised as an **explicit enumeration** of the four known `patient.*` keys used by KOSMOS tool adapters. New `patient.*` keys must be added here. This is documented at the top of `infra/otel-collector/config.yaml` and cross-linked from the adapter authoring guide.

**`batch`** (FR-007):

| Field | Value |
|---|---|
| `timeout` | `5s` |
| `send_batch_size` | `512` |
| `send_batch_max_size` | `512` |

### E2.3 Exporters — `otlphttp`

| Field | Value / Source |
|---|---|
| `endpoint` | `${KOSMOS_LANGFUSE_OTLP_ENDPOINT:-http://langfuse-web:3000/api/public/otel/v1/traces}` |
| `headers.Authorization` | `${KOSMOS_LANGFUSE_OTLP_AUTH_HEADER}` (empty = anonymous) |
| `headers.x-langfuse-ingestion-version` | `"4"` |
| `tls.insecure` | `true` (local only; Phase 3 flips to TLS) |
| `compression` | `gzip` |

### E2.4 Pipeline wiring

```yaml
service:
  extensions: [health_check]
  pipelines:
    traces:
      receivers: [otlp]
      processors: [attributes/pii_redact, batch]
      exporters: [otlphttp]
```

**Invariants**:
- Exactly one `traces` pipeline.
- Processor order is **fixed**: `attributes/pii_redact` MUST precede `batch`. Reversing leaks raw PII into the batch queue.

---

## E3. EnvironmentContract (three new `KOSMOS_` vars + inherited)

Represents the new rows appended to `.env.example` (FR-010).

| Key | Default | Consumer | Sensitivity |
|---|---|---|---|
| `KOSMOS_OTEL_COLLECTOR_PORT` | `4318` | `docker-compose.dev.yml` — host port map | Non-sensitive |
| `KOSMOS_LANGFUSE_OTLP_ENDPOINT` | `http://langfuse-web:3000/api/public/otel/v1/traces` | `infra/otel-collector/config.yaml` — exporter `endpoint` | Non-sensitive |
| `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` | `` (empty) | `infra/otel-collector/config.yaml` — exporter `headers.Authorization` | **SENSITIVE** — base64 of `pk-xxx:sk-xxx` |

**Inherited from spec 021** (unchanged, listed for completeness):

| Key | Role in 028 |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | KOSMOS Python app points here; set to `http://localhost:4318` in dev |
| `OTEL_SDK_DISABLED` | Must remain effective — SC-004 |

**Validation rules**:
- `KOSMOS_OTEL_COLLECTOR_PORT` must be a valid TCP port (1024 ≤ n ≤ 65535 for unprivileged). Compose rejects malformed values at `config` time.
- `KOSMOS_LANGFUSE_OTLP_ENDPOINT` must be a URL with scheme `http` or `https`. The `:ro` collector config does not validate the URL format; malformed URLs surface as exporter errors at first span.
- `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER`, when set, must begin with `Basic ` (RFC 7617 token prefix). Empty string disables auth.

---

## E4. PiiRedactionRule (value object)

For Phase 1 documentation of the redaction contract — not a Python object.

```
PiiRedactionRule = {
    "key": str,              # exact attribute key (no wildcards — see E2.2 note)
    "action": "delete" | "hash",
    "algorithm"?: "sha256",  # required iff action == "hash"
    "rationale": str,        # one-line reason (audit trail)
}
```

**Single source of truth hierarchy**:
1. `ObservabilityEventLogger._ALLOWED_METADATA_KEYS` (spec 021, Python layer) — whitelist of what may be emitted at all.
2. `infra/otel-collector/config.yaml` — redaction of any leakage that slipped past layer 1.

Rule additions MUST happen at layer 1 first; layer 2 is a backstop.

---

## E5. HealthcheckContract

Collector health signalling into the compose healthcheck chain.

| Probe | Endpoint | Expected |
|---|---|---|
| Collector self-health | `http://localhost:13133/` | HTTP 200, body `{"status":"Server available"}` |
| Langfuse ingest reachability | `http://langfuse-web:3000/api/public/health` (sibling service check) | HTTP 200 |

The collector does not probe Langfuse's ingest path from inside its own healthcheck — that coupling would cascade failures. Compose's `depends_on.langfuse-web.condition: service_healthy` covers the dependency gate.

---

## Relationships summary

```text
┌─────────────┐     OTLP HTTP      ┌──────────────┐     OTLP HTTP      ┌──────────────┐
│ KOSMOS app  │ ─────────────────▶ │   otelcol    │ ─────────────────▶ │ langfuse-web │
│ (host proc) │   :4318 (host)     │  (container) │   :3000/api/...    │  (container) │
└─────────────┘                    └──────────────┘                    └──────────────┘
                                          │                                   │
                                          │ reads                             │ persists
                                          ▼                                   ▼
                                   config.yaml (:ro)              Postgres / ClickHouse / MinIO
```

No database, no persistent state at the collector layer. All durable trace data lives in the Langfuse backend (inherited from spec 021).
