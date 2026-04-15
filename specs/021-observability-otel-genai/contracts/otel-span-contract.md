# OTel Span Wire Contract

**Feature**: `021-observability-otel-genai`
**Version**: v1.0 (aligns with OTel GenAI semconv v1.40)
**Stability**: Development (requires `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`)

This contract is the **observable agreement** between KOSMOS and any OTLP-compatible backend (Langfuse v3, Datadog, Phoenix, Uptrace). Changing any name, attribute key, or status mapping in this document is a breaking change to downstream dashboards and requires a new spec.

## Transport

| Property | Value |
|---|---|
| Protocol | `http/protobuf` (gRPC not supported) |
| Endpoint (local) | `http://localhost:3000/api/public/otel` |
| Authentication | HTTP Basic `base64(public_key:secret_key)` via `OTEL_EXPORTER_OTLP_HEADERS` |
| Processor | `BatchSpanProcessor` (default queue 2048, export timeout 30s, scheduled delay 5s) |
| Compression | Not enforced (Langfuse handles gzip transparently) |

## Resource attributes (all spans)

| Attribute | Type | Value |
|---|---|---|
| `service.name` | str | `kosmos` |
| `service.version` | str | `pyproject.toml[project.version]` (read at boot) |
| `deployment.environment.name` | str | `OTEL_DEPLOYMENT_ENVIRONMENT` env (default `dev`) |

## Span 1 — `invoke_agent kosmos-query`

Parent span opened at `engine.query.query()` entry, closed at generator exhaustion or exception.

**Required attributes**

| Key | Type | Value |
|---|---|---|
| `gen_ai.operation.name` | str | `invoke_agent` |
| `gen_ai.agent.name` | str | `kosmos-query` |

**Conditional attributes**

| Key | Type | Condition |
|---|---|---|
| `gen_ai.conversation.id` | str | Attach iff `QueryContext.session_context is not None`. Value = `session_context.session_id`. |
| `error.type` | str | Attach iff terminated by exception. Value = `exc.__class__.__name__`. |

**Status mapping**

| Outcome | OTel Status |
|---|---|
| Normal completion | `Status(UNSET)` |
| Exception propagated | `Status(ERROR)` + `span.record_exception(exc)` |

**Parent relationship**: Root in its trace (no upstream parent). All `chat` and `execute_tool` spans produced during the same query become children via OTel context propagation.

## Span 2 — `chat`

Created per LLM call in `LLMClient.generate_stream`. Closed when the stream finalizes (normal or error).

**Required attributes**

| Key | Type | Value source |
|---|---|---|
| `gen_ai.operation.name` | str | `chat` |
| `gen_ai.provider.name` | str | `friendliai` (**never** `gen_ai.system` — deprecated since v1.37) |
| `gen_ai.request.model` | str | Request payload `model` |
| `gen_ai.response.model` | str | Response frame `model` (fallback: request model) |
| `gen_ai.usage.input_tokens` | int | Aggregated at stream end (single write) |
| `gen_ai.usage.output_tokens` | int | Aggregated at stream end (single write) |
| `gen_ai.response.finish_reasons` | list[str] | e.g., `["stop"]`, `["tool_calls"]`, `["length"]` |

**Optional attributes** (attach only if present in request)

| Key | Type | Source |
|---|---|---|
| `gen_ai.request.temperature` | float | Request `temperature` |
| `gen_ai.request.max_tokens` | int | Request `max_tokens` |
| `gen_ai.request.top_p` | float | Request `top_p` |

**Error attribute**

| Key | Type | Condition |
|---|---|---|
| `error.type` | str | Failure path. Value = exception class name. |

**Status mapping**

| Outcome | OTel Status |
|---|---|
| Stream finalized normally | `Status(UNSET)` |
| Upstream error / truncation | `Status(ERROR)` + `span.record_exception(exc)` |

**Streaming usage rule**: Token counters MUST be written exactly once, at stream end. Per-chunk updates are a contract violation (Langfuse sums attribute overwrites).

**Retry rule**: HTTP 429 retries inside a single logical call remain within the **same** `chat` span. Do not create per-attempt spans. Each retry increments `kosmos_llm_rate_limit_retries_total{provider, model}` (see Metrics).

## Span 3 — `execute_tool {tool_id}`

Created per tool dispatch in `ToolExecutor.dispatch`.

**Required attributes**

| Key | Type | Value source |
|---|---|---|
| `gen_ai.operation.name` | str | `execute_tool` |
| `gen_ai.tool.name` | str | `tool_id` |
| `gen_ai.tool.type` | str | `function` (all KOSMOS tools are function-call) |

**Optional attributes**

| Key | Type | Source |
|---|---|---|
| `gen_ai.tool.call.id` | str | LLM-provided `tool_call_id`, if available |

**Error attribute**

| Key | Type | Condition |
|---|---|---|
| `error.type` | str | `ToolResult.success is False`. Value = `ToolResult.error_class` (whitelist-filtered). |

**Status mapping**

| Outcome | OTel Status |
|---|---|
| `ToolResult.success = True` | `Status(UNSET)` |
| `ToolResult.success = False` | `Status(ERROR)` + `span.record_exception` (if exception bubbled) |

**PII rule**: Tool input payloads, tool output payloads, and API response bodies MUST NOT be attached as span attributes. Only whitelist-approved metadata keys (`tool_id`, `step`, `decision`, `error_class`, `model`) pass through.

## Metric — `kosmos_llm_rate_limit_retries_total`

| Property | Value |
|---|---|
| Instrument | Counter |
| Unit | `1` (count) |
| Description | `Number of HTTP 429 retries emitted by LLM provider, per retry attempt` |
| Labels | `provider` (str), `model` (str) |
| Increment site | `LLMClient.generate_stream`, just before issuing the retried request (after honoring `Retry-After`) |

## Attribute whitelist (PII prefilter)

Any `dict`-shaped metadata passing through `otel_bridge.filter_metadata` is prefiltered against the canonical frozenset imported from `src/kosmos/observability/event_logger.py`:

```
{"tool_id", "step", "decision", "error_class", "model"}
```

Keys outside this set are dropped silently. Values that are not `str | bool | int | float | list[primitive]` are dropped. This is the **single source of truth**; the OTel path must not maintain a second whitelist.

## No-op contract

When `OTEL_SDK_DISABLED=true` or the endpoint is unset:

- `TracerProvider` = `NoOpTracerProvider`
- All `start_as_current_span` calls return no-op spans
- `BatchSpanProcessor` is **not** instantiated (no background thread)
- All attribute writes are no-ops
- **No network activity** occurs
- Application behavior is identical to the pre-OTel baseline

Any test run under this mode that measures a non-zero delta from the pre-OTel baseline (wall time, memory, network) is a contract violation.

## Versioning

Changes to this contract follow:

1. **Additive** (new optional attribute, new resource attribute, new span kind) — minor bump, no spec required.
2. **Breaking** (rename, remove, change required→optional, change status mapping) — new spec + migration plan. Always tag the deprecated name for at least one release.
3. **Semconv upgrade** (e.g., GenAI v1.40 → Stable) — flip `OTEL_SEMCONV_STABILITY_OPT_IN` default, announce in CHANGELOG.
