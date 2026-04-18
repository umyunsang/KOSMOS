# KOSMOS Observability — Local Stack Guide

**Spec**: 028-otlp-collector | **Epic**: #501 | **Updated**: 2026-04-18

This document is the authoritative guide for running the KOSMOS observability
stack locally during development and KSC 2026 demo sessions. It covers the
full pipeline from KOSMOS app to Langfuse UI and the PII redaction gate in
between.

---

## 1. Stack Overview

The local observability stack has three tiers:

```text
┌─────────────┐     OTLP HTTP      ┌──────────────┐     OTLP HTTP      ┌──────────────┐
│ KOSMOS app  │ ─────────────────▶ │   otelcol    │ ─────────────────▶ │ langfuse-web │
│ (host proc) │   :4318 (host)     │  (container) │   :3000/api/...    │  (container) │
└─────────────┘                    └──────────────┘                    └──────────────┘
                                          │                                   │
                                          │ reads (read-only)                 │ persists
                                          ▼                                   ▼
                                   config.yaml (:ro)              Postgres / ClickHouse / MinIO
```

- **KOSMOS app** (host process): emits OTLP/HTTP spans to `http://localhost:4318`.
- **otelcol** (OTel Collector Contrib container): receives spans, applies PII
  redaction rules, batches, and forwards to Langfuse.
- **langfuse-web** (Langfuse v3 container): ingests spans via the OTLP HTTP
  endpoint and persists them to Postgres + ClickHouse + MinIO.

The full Langfuse backend (Postgres 16, Redis 7, ClickHouse 24.8, MinIO) is
defined in `docker-compose.dev.yml` (originally from spec 021). Spec 028
extends that file by adding the `otelcol` service and pinning Langfuse images
to version `3.35.0`.

---

## 2. Span Tree Reference

A single KOSMOS agent session emits the following three-level span tree
(SC-002):

```
invoke_agent kosmos-query       ← root span
├── chat                        ← LLM call (gen_ai.request.model=EXAONE-...)
└── execute_tool <tool_id>      ← tool invocation
```

Each span carries:
- `gen_ai.system` / `gen_ai.request.model` — model identity
- `kosmos.tool.id` — tool adapter identifier (on `execute_tool` spans)
- `kosmos.location.query` — **hashed** by the collector before Langfuse
  ingestion (SHA-256, see PII Redaction Gate below)

---

## 3. One-Command Bootstrap

From a fresh clone or after `docker compose down -v`:

```bash
cd <kosmos-checkout>
docker compose -f docker-compose.dev.yml up -d
```

Expected bring-up sequence (first run pulls images, ~5 min):

1. `postgres`, `redis`, `minio` → `healthy` (~10 s).
2. `clickhouse` → `healthy` (~30–60 s cold start).
3. `minio-init` → creates default bucket and exits `0`.
4. `langfuse-web`, `langfuse-worker` → `healthy` (~30 s after their deps).
5. `otelcol` → `healthy` (~5 s after `langfuse-web`).

Verify all services:

```bash
docker compose -f docker-compose.dev.yml ps
```

All rows should show `healthy` (or the minio-init exit 0).

---

## 4. Environment Variable Reference

All variables follow the `KOSMOS_` prefix rule (AGENTS.md hard rule).

### New variables (spec 028)

| Variable | Default | Description |
|---|---|---|
| `KOSMOS_OTEL_COLLECTOR_PORT` | `4318` | Host port for the `otelcol` OTLP HTTP receiver. Consumed by `docker-compose.dev.yml`. |
| `KOSMOS_LANGFUSE_OTLP_ENDPOINT` | `http://langfuse-web:3000/api/public/otel/v1/traces` | Langfuse OTLP ingest URL used by the collector exporter (compose-internal). Consumed by `infra/otel-collector/config.yaml`. |
| `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` | `` (empty) | `Basic <base64(pk-xxx:sk-xxx)>` for Langfuse OTLP auth. Empty = anonymous. **Sensitive** — do not commit. Consumed by `infra/otel-collector/config.yaml`. |

### Inherited from spec 021 (unchanged)

| Variable | Role in 028 |
|---|---|
| `OTEL_EXPORTER_OTLP_ENDPOINT` | KOSMOS Python app points here. For local dev: `http://localhost:4318`. |
| `OTEL_SDK_DISABLED` | Set to `true` to disable all OTLP export (SC-004 — CI passthrough). |

See `.env.example` for the full list of variables.

---

## 5. First-Run Langfuse Project Bootstrap

Langfuse v3 does **not** support env-var-based project or API key seeding.
Follow this one-time procedure (approximately 2 min):

1. Open `http://localhost:3000` in a browser.
2. Sign up as the first user (any email; stored locally in Postgres only).
3. Click "New organization" and enter a name (e.g., `kosmos-local`).
4. Click "New project" and enter a name (e.g., `kosmos-dev`).
5. Go to **Settings → API Keys** → click "Create new API keys".
6. Copy the **public key** (`pk-lf-...`) and **secret key** (`sk-lf-...`).

Construct the Basic auth header and add it to your `.env` file:

```bash
AUTH=$(printf '%s' "pk-lf-xxxx:sk-lf-xxxx" | base64)
echo "KOSMOS_LANGFUSE_OTLP_AUTH_HEADER=Basic $AUTH" >> .env
```

Restart the collector to pick up the new header:

```bash
docker compose -f docker-compose.dev.yml restart otelcol
```

---

## 6. PII Redaction Gate

The `otelcol` service applies a second-layer PII redaction gate **before**
spans reach Langfuse. This complements the first gate in the KOSMOS Python
layer (`ObservabilityEventLogger._ALLOWED_METADATA_KEYS` in
`src/kosmos/observability/event_logger.py`).

### Covered keys (explicit enumeration — no wildcard support)

The OTel Collector `attributes` processor does **not** support wildcard
matching. The following four `patient.*` keys are explicitly enumerated:

| Key | Action | Rationale |
|---|---|---|
| `patient.name` | `delete` | PIPA §26 — personal identifier |
| `patient.phone` | `delete` | PIPA §26 — personal identifier |
| `patient.rrn` | `delete` | PIPA §26 — resident registration number |
| `patient.address` | `delete` | PIPA §26 — address |
| `kosmos.location.query` | `hash` (SHA-256) | Preserves cardinality for analytics while redacting raw query text |

### Relationship to spec 021 whitelist

The Python-layer whitelist (`_ALLOWED_METADATA_KEYS`) is the **first** gate —
it controls which attributes may be emitted at all. The collector config is the
**second** gate — it catches any leakage that slipped past layer 1.

### Single source of truth hierarchy

1. `src/kosmos/observability/event_logger.py` — `_ALLOWED_METADATA_KEYS`
   whitelist (Python layer, first gate).
2. `infra/otel-collector/config.yaml` — `attributes/pii_redact` processor
   rules (collector layer, second gate).

**Adding a new `patient.*` key** requires a **dual-edit**:
1. Add the key to `_ALLOWED_METADATA_KEYS` in `event_logger.py` first.
2. Add a `delete` rule for the key in `infra/otel-collector/config.yaml`.

### Smoke test

```bash
uv run pytest -m live tests/live/test_collector_pii_redaction.py
```

This test emits a fixture span with `patient.name="TEST_OPERATOR"` and
`kosmos.location.query="서울역"`, then queries the Langfuse public API to
verify:
- `patient.name` is **absent** from the stored span.
- `kosmos.location.query` equals the SHA-256 hex hash of `"서울역"`.

CI skips this test automatically (`@pytest.mark.live`).

---

## 7. Troubleshooting

### A. Port 4318 already in use

**Symptom**: `docker compose up` logs `bind: address already in use` on the
`otelcol` service.

**Fix**: Override the host port:

```bash
echo "KOSMOS_OTEL_COLLECTOR_PORT=14318" >> .env
docker compose -f docker-compose.dev.yml up -d otelcol
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318
```

### B. No traces appear in Langfuse UI after 30 s

**Check collector logs**:

```bash
docker compose -f docker-compose.dev.yml logs otelcol --tail=50
```

**Most common causes**:
- `401 Unauthorized` — `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` is missing or
  malformed. Re-run the first-run bootstrap in Section 5.
- `connection refused` — `langfuse-web` is not healthy yet. Run
  `docker compose -f docker-compose.dev.yml ps` to confirm.
- KOSMOS app `OTEL_EXPORTER_OTLP_ENDPOINT` still points at Langfuse directly
  (legacy spec 021 config). Update to `http://localhost:4318`.

### C. ClickHouse slow cold-start drops early spans

**Symptom**: First trace after `up -d` is missing some child spans.

**Fix**: The collector's `batch` processor retains up to 512 spans for 5 s.
Wait for `langfuse-worker` logs to show `ClickHouse migration complete` before
running the first agent call.

```bash
docker compose -f docker-compose.dev.yml logs langfuse-worker --follow
# Wait for: "ClickHouse migration complete"
```

---

## 8. Tear-down

```bash
docker compose -f docker-compose.dev.yml down
# To also wipe persisted Langfuse data (traces, users, projects):
docker compose -f docker-compose.dev.yml down -v
```

---

## References

- Spec: `specs/028-otlp-collector/spec.md`
- Collector config: `infra/otel-collector/config.yaml`
- Env contract: `specs/028-otlp-collector/contracts/env-reference.md`
- Quickstart: `specs/028-otlp-collector/quickstart.md`
- Spec 021 (observability foundation): `specs/021-observability-otel-genai/`
- Epic: GitHub issue #501
