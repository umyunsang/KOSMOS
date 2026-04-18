# Quickstart: OTLP Collector + Local Langfuse Stack

**Spec**: 028-otlp-collector | **Audience**: KSC 2026 demo operator, KOSMOS developer

This quickstart walks one operator from a fresh clone to "agent trace visible in Langfuse UI" in under 10 minutes.

---

## Prerequisites

- Docker Desktop 4.30+ (Compose v2 built-in). Confirm: `docker compose version` prints `v2.x`.
- A KOSMOS checkout at the branch containing spec 028 changes.
- No prior `docker compose -f docker-compose.dev.yml` stack running (`docker compose -f docker-compose.dev.yml down -v` to reset).
- At least 8 GB free RAM (Langfuse stack ~4 GB + collector ~256 MB + headroom).

---

## 1. One-command bring-up (~5 min first run, ~30 s subsequent)

```bash
cd <kosmos-checkout>
docker compose -f docker-compose.dev.yml up -d
```

Expected sequence (first run pulls images):

1. `postgres`, `redis`, `minio` → `healthy` (~10 s).
2. `clickhouse` → `healthy` (~30–60 s cold start).
3. `minio-init` → creates default bucket and exits `0`.
4. `langfuse-web`, `langfuse-worker` → `healthy` (~30 s after their deps).
5. **`otelcol`** → `healthy` (~5 s after `langfuse-web`).

Verify all services are healthy:

```bash
docker compose -f docker-compose.dev.yml ps
```

All rows should show `healthy` (or `running` for `minio-init` which is expected to have exited).

---

## 2. First-run Langfuse project bootstrap (one-time, ~2 min)

Langfuse v3 does **not** support env-var-based project or API key seeding (confirmed in Clarification #4). Follow this one-time procedure:

1. Open `http://localhost:3000` in a browser.
2. Sign up as the first user (any email; stored locally in Postgres).
3. Click "New organization" → enter a name (e.g., `kosmos-local`).
4. Click "New project" → enter a name (e.g., `kosmos-dev`).
5. Go to **Settings → API Keys** → click "Create new API keys".
6. Copy the **public key** (`pk-lf-...`) and **secret key** (`sk-lf-...`).

Construct the Basic auth header and add to `.env`:

```bash
AUTH=$(printf '%s' "pk-lf-xxxx:sk-lf-xxxx" | base64)
echo "KOSMOS_LANGFUSE_OTLP_AUTH_HEADER=Basic $AUTH" >> .env
```

Restart the collector to pick up the new header:

```bash
docker compose -f docker-compose.dev.yml restart otelcol
```

---

## 3. Point the KOSMOS app at the collector

In your KOSMOS app shell (not inside a compose container):

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
# Optionally also:
# export KOSMOS_OTEL_SERVICE_NAME=kosmos
```

Start a KOSMOS CLI session and make a single agent call:

```bash
uv run kosmos chat "서울 강남역 근처 소아과 찾아줘"
```

---

## 4. Verify a trace appears (end-to-end success)

Within 10 seconds of the CLI call completing, open the Langfuse UI:

```
http://localhost:3000  →  Traces
```

You should see one new trace whose root span is `invoke_agent kosmos-query`. Expanding it reveals at minimum:

```
invoke_agent kosmos-query
├── chat (gen_ai.request.model=EXAONE-...)
└── execute_tool <tool_id>
```

SC-002 is satisfied when this three-level tree is visible.

---

## 5. Verify PII redaction (SC-003 smoke test)

Run the redaction smoke test (marker-gated, skipped in CI per AGENTS.md):

```bash
uv run pytest -m live tests/live/test_collector_pii_redaction.py
```

This test (delivered by `/speckit-implement`) emits a fixture span carrying `patient.name="TEST_OPERATOR"` and `kosmos.location.query="서울역"`, then queries the Langfuse public API for the resulting trace. Assertions:

- `patient.name` attribute MUST NOT be present on the stored span.
- `kosmos.location.query` value MUST be the 64-char SHA-256 hex hash of `"서울역"`, not the raw string.

---

## 6. Verify CI passthrough (SC-004)

With the stack torn down:

```bash
docker compose -f docker-compose.dev.yml down
export OTEL_SDK_DISABLED=true
unset OTEL_EXPORTER_OTLP_ENDPOINT
uv run pytest
```

All tests must pass, and the KOSMOS process must produce zero OTLP network attempts (spec 021 FR-014 inheritance).

---

## Troubleshooting — three most common failures

### A. Port 4318 already in use

Symptom: `docker compose up` logs `bind: address already in use` on the `otelcol` service.

Fix: Set a different host port:

```bash
echo "KOSMOS_OTEL_COLLECTOR_PORT=14318" >> .env
docker compose -f docker-compose.dev.yml up -d otelcol
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:14318
```

### B. No traces appear in Langfuse UI after 30 s

Check the collector logs:

```bash
docker compose -f docker-compose.dev.yml logs otelcol --tail=50
```

Most common causes:
- `401 Unauthorized` → `KOSMOS_LANGFUSE_OTLP_AUTH_HEADER` missing or malformed. Re-run step 2.
- `connection refused` → `langfuse-web` not healthy yet. `docker compose ps` to confirm.
- KOSMOS app `OTEL_EXPORTER_OTLP_ENDPOINT` still points at Langfuse directly (legacy spec 021 config). Update to `http://localhost:4318`.

### C. ClickHouse slow cold-start drops early spans

Symptom: First trace after `up -d` is missing some child spans.

Fix: The collector's `batch` processor retains up to 512 spans for 5 s. If ClickHouse is still booting, wait for `langfuse-worker` logs to show `ClickHouse migration complete` before running the first agent call.

---

## Tear-down

```bash
docker compose -f docker-compose.dev.yml down
# To also wipe persisted Langfuse data:
docker compose -f docker-compose.dev.yml down -v
```
