# Environment Variable Contract — Spec 028

**Spec**: 028-otlp-collector | **Date**: 2026-04-18

This contract is the authoritative list of environment variables introduced or consumed by spec 028. All new variables follow the `KOSMOS_` prefix rule (AGENTS.md hard rule). Values documented here are the **contract**; implementers MUST NOT silently diverge.

---

## New variables (three — added by FR-010)

### `KOSMOS_OTEL_COLLECTOR_PORT`

| Attribute | Value |
|---|---|
| Default | `4318` |
| Type | integer (TCP port) |
| Range | 1024–65535 (unprivileged) |
| Consumer | `docker-compose.dev.yml` — host port of `otelcol.ports[0]` |
| Scope | Host ↔ collector container |
| Sensitive | No |
| Change semantics | Operator override only. Changing requires restarting the `otelcol` service and updating the KOSMOS app's `OTEL_EXPORTER_OTLP_ENDPOINT` accordingly. |

### `KOSMOS_LANGFUSE_OTLP_ENDPOINT`

| Attribute | Value |
|---|---|
| Default | `http://langfuse-web:3000/api/public/otel/v1/traces` |
| Type | URL |
| Scheme | `http` (local dev); `https` in Phase 3 |
| Consumer | `infra/otel-collector/config.yaml` — exporter `endpoint` |
| Scope | Collector ↔ Langfuse (compose-internal) |
| Sensitive | No |
| Change semantics | Used when the operator points the collector at a different Langfuse instance (e.g., a pre-prod staging host). Compose does not validate URL format; malformed values surface as exporter errors at first span. |

### `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER`

| Attribute | Value |
|---|---|
| Default | `` (empty — anonymous) |
| Type | string |
| Format | `Basic <base64(public_key:secret_key)>` per RFC 7617 |
| Consumer | `infra/otel-collector/config.yaml` — exporter `headers.Authorization` |
| Scope | Collector → Langfuse ingest |
| Sensitive | **YES** — contains Langfuse secret key |
| Source | After first-run Langfuse UI bootstrap (see FR-008b and `docs/observability.md § First-run`) |
| Change semantics | Must be rotated if the Langfuse project's secret key is regenerated. Empty value disables auth (acceptable only for anonymous local dev projects). |

---

## Inherited from spec 021 (unchanged; listed for cross-reference)

### `OTEL_EXPORTER_OTLP_ENDPOINT`

| Attribute | Value |
|---|---|
| Role in 028 | KOSMOS Python app points here; for this spec's local-dev setup operators set `http://localhost:4318` |
| Default | unset (SDK warn-and-skip per spec 021 FR-010) |
| Sensitive | No |

### `OTEL_SDK_DISABLED`

| Attribute | Value |
|---|---|
| Role in 028 | SC-004 — must remain effective. When `true`, the KOSMOS app performs zero OTLP export attempts even if the collector is running. |
| Default | unset (= enabled when endpoint is set) |
| Sensitive | No |

---

## Contract invariants

1. All three new variables MUST appear in `.env.example` with inline comments describing the consumer (format matches existing `.env.example` convention — "consumed by ..." preamble).
2. `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` MUST NOT appear in any committed file with a real value. `.env.example` value MUST be empty.
3. `docker-compose.dev.yml` MUST use `${KOSMOS_*:-default}` substitution syntax for all three variables — no hardcoded values.
4. The collector config MUST reference these variables via `${env:NAME}` (OTel Collector env-expansion syntax), not via Compose-level `environment:` injection — this keeps the config self-documenting.
