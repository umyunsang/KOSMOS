# Quickstart — Observability (OTel GenAI + Langfuse)

**Feature**: `021-observability-otel-genai`
**Audience**: developer running KOSMOS locally who wants to see LLM/tool traces in Langfuse.

Three environments are supported:

1. **Local dev with Langfuse** — see full traces in a browser UI
2. **Local dev without Langfuse** — set `OTEL_SDK_DISABLED=true`, everything is a no-op
3. **CI** — always no-op (CI injects `OTEL_SDK_DISABLED=true`)

## A. Local dev with Langfuse (full flow)

### A.1. Boot the Langfuse v3 stack

```bash
docker compose -f docker-compose.dev.yml up -d
```

Services brought up: `langfuse-web` (UI), `langfuse-worker`, `postgres`, `redis`, `clickhouse`, `minio`. First boot takes 30–60s for schema migration.

Check health:

```bash
docker compose -f docker-compose.dev.yml ps
curl -sf http://localhost:3000/api/public/health | jq
```

### A.2. Create a Langfuse project and get API keys

1. Open <http://localhost:3000>
2. Sign up (first user becomes admin)
3. Create a project (e.g., `kosmos-dev`)
4. Settings → **API Keys** → Create → copy `Public Key` (`pk-lf-...`) and `Secret Key` (`sk-lf-...`)

### A.3. Wire `.env`

Copy the observability block from `.env.example` to `.env` and fill the key pair:

```bash
# Observability (OTel + Langfuse)
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:3000/api/public/otel
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic%20<base64-of-public_key:secret_key>
OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental
# OTEL_SDK_DISABLED=true   # leave commented
```

Generate the base64 string:

```bash
echo -n "pk-lf-xxxx:sk-lf-xxxx" | base64
```

URL-encode the space after `Basic` as `%20` (`OTEL_EXPORTER_OTLP_HEADERS` is a URL-encoded string).

### A.4. Run any KOSMOS query

```bash
uv run python -m kosmos.cli "서울 강남구 교통사고 현황 알려줘"
```

### A.5. Verify in Langfuse UI

1. Open <http://localhost:3000/project/kosmos-dev/traces>
2. You should see **one trace** with three levels:
   - Root span: `invoke_agent kosmos-query` with `gen_ai.conversation.id = <session uuid>`
   - Child span(s): `chat` with `gen_ai.provider.name=friendliai`, `gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`
   - Child span(s): `execute_tool koroad_accident_search` (or similar tool name)
3. Metrics view: `kosmos_llm_rate_limit_retries_total` (0 if no 429s occurred)

If traces are missing, see **Troubleshooting** below.

## B. Local dev without Langfuse (fast path)

If Langfuse isn't running, or you want no overhead:

```bash
export OTEL_SDK_DISABLED=true
uv run python -m kosmos.cli "..."
```

Expected behavior: **identical to pre-OTel baseline**. No network calls, no background threads, no log output from the tracing layer.

## C. CI (automatic)

CI runs inject `OTEL_SDK_DISABLED=true` via the workflow env. Nothing needs to be configured per-job. If you see any OTel-related noise in CI logs, that's a bug — file it.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| No trace appears in Langfuse, no error in app logs | Endpoint unreachable; BatchSpanProcessor swallows export errors | `curl -v http://localhost:3000/api/public/health`; check `docker compose ps` |
| `Exporter returned status code 401` in app warnings | Wrong base64 auth header | Re-generate with `echo -n "pk:sk" \| base64`; ensure `Basic%20` prefix in URL-encoded form |
| `Exporter returned status code 404` | Wrong endpoint path | Endpoint must be `http://localhost:3000/api/public/otel` (NOT `/v1/traces`) |
| Trace appears but no `gen_ai.*` attributes | Missing opt-in | Set `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental` |
| gRPC connection errors | Wrong protocol | Langfuse does not accept gRPC; set `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf` |
| Tests fail with "no OTel endpoint" | CI env leaked into local pytest | `unset OTEL_SDK_DISABLED` or use `OTEL_SDK_DISABLED=true` — both work, but don't leave it half-set |
| High p99 latency on first request after boot | BatchSpanProcessor warmup | Expected; subsequent requests see <1ms p95 overhead |

## Validation checklist (for PR reviewers)

- [ ] `docker compose -f docker-compose.dev.yml up -d` boots without error
- [ ] A single CLI query produces one trace with three span kinds in Langfuse
- [ ] `chat` span shows non-zero `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`
- [ ] `execute_tool` span status = `UNSET` on success, `ERROR` on tool failure
- [ ] With `OTEL_SDK_DISABLED=true`, the full test suite (`uv run pytest`) passes
- [ ] No span attribute contains raw user input or API response bodies (PII check)
- [ ] `pyproject.toml` adds exactly 3 new runtime deps (sdk, exporter, semconv)

## References

- OTel GenAI semconv v1.40: <https://opentelemetry.io/docs/specs/semconv/gen-ai/>
- Langfuse self-hosting (docker-compose): <https://langfuse.com/self-hosting/docker-compose>
- Langfuse OTel ingestion: <https://langfuse.com/docs/opentelemetry>
- OTel Configuration env vars: <https://opentelemetry.io/docs/specs/otel/configuration/sdk-environment-variables/>
