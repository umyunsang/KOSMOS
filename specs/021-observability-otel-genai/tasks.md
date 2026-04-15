# Tasks — Observability (OpenTelemetry GenAI + Langfuse)

**Feature**: `021-observability-otel-genai`
**Branch**: `main` (feature dir only)
**Input**: `specs/021-observability-otel-genai/` (spec.md, plan.md, research.md, data-model.md, contracts/otel-span-contract.md, quickstart.md)

All paths are absolute from repository root `/Users/um-yunsang/KOSMOS/`.

## Phase 1 — Setup

- [ ] T001 Add exactly 3 runtime dependencies to `pyproject.toml` (`opentelemetry-sdk`, `opentelemetry-exporter-otlp-proto-http`, `opentelemetry-semantic-conventions`) under `[project].dependencies`; run `uv sync` to materialize `uv.lock`. Verify `grep -E 'opentelemetry-instrumentation|openllmetry|traceloop' pyproject.toml` returns nothing (FR-016, SC-006).
- [ ] T002 [P] Append the Observability env block (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SEMCONV_STABILITY_OPT_IN=gen_ai_latest_experimental`, commented `OTEL_SDK_DISABLED`) to `.env.example` per research.md § D10 (FR-015).
- [ ] T003 [P] Create empty package marker `tests/observability/__init__.py` to host the new test module.

## Phase 2 — Foundational (blocking prerequisites)

**No user story work may begin until this phase is green.**

- [ ] T004 [P] Create `src/kosmos/observability/semconv.py` exporting GenAI attribute-name constants (`GEN_AI_OPERATION_NAME`, `GEN_AI_AGENT_NAME`, `GEN_AI_PROVIDER_NAME`, `GEN_AI_CONVERSATION_ID`, `GEN_AI_REQUEST_MODEL`, `GEN_AI_RESPONSE_MODEL`, `GEN_AI_USAGE_INPUT_TOKENS`, `GEN_AI_USAGE_OUTPUT_TOKENS`, `GEN_AI_RESPONSE_FINISH_REASONS`, `GEN_AI_TOOL_NAME`, `GEN_AI_TOOL_TYPE`, `GEN_AI_TOOL_CALL_ID`, `ERROR_TYPE`) as a single source of truth; prefer `opentelemetry.semconv.attributes.gen_ai_attributes` re-exports where available, otherwise define string literals per OTel GenAI semconv v1.40 (FR-004, research.md § D2).
- [ ] T005 [P] Create `src/kosmos/observability/otel_bridge.py` with `filter_metadata(raw: dict) -> dict` that imports `_ALLOWED_METADATA_KEYS` from `src/kosmos/observability/event_logger.py` (no duplicate whitelist) and drops non-primitive values per data-model.md § E5 (FR-011, research.md § D8).
- [ ] T006 Create `src/kosmos/observability/tracing.py` with `TracingSettings` Pydantic v2 model (`frozen=True`, `extra="forbid"`) per data-model.md § E1, plus `setup_tracing(settings: TracingSettings | None = None) -> TracerProvider` that:
  - reads env vars (`OTEL_SDK_DISABLED`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_PROTOCOL`, `OTEL_EXPORTER_OTLP_HEADERS`, `OTEL_SEMCONV_STABILITY_OPT_IN`, `OTEL_DEPLOYMENT_ENVIRONMENT`) when `settings is None`
  - returns `NoOpTracerProvider` if `OTEL_SDK_DISABLED=true` or endpoint missing
  - otherwise configures `TracerProvider` with `Resource({service.name: "kosmos", service.version, deployment.environment.name})`, `BatchSpanProcessor(OTLPSpanExporter(endpoint, protocol="http/protobuf"))` (FR-007, FR-008, FR-009, FR-010, research.md § D3, D4, D5).
- [ ] T007 [P] Update `src/kosmos/observability/__init__.py` to re-export `setup_tracing`, `TracingSettings`, `filter_metadata`, and the semconv constants.

**Checkpoint**: `uv run python -c "from kosmos.observability import setup_tracing; setup_tracing()"` must succeed in a fresh shell with only `OTEL_SDK_DISABLED=true` set (no-op) and exit without network activity.

## Phase 3 — User Story 1: Developer traces a production agent failure end-to-end (P1) 🎯 MVP

**Story goal**: One user query produces one trace in Langfuse with three-tier hierarchy (`invoke_agent` → `chat` → `execute_tool`), each span carrying the required GenAI attributes; PII stays out.

**Independent test**: With Langfuse running and `OTEL_SDK_DISABLED` unset, run `uv run python -m kosmos.cli "..."` and verify in Langfuse UI: one trace, parent `invoke_agent kosmos-query` with `gen_ai.conversation.id=<uuid>`, child `chat` with `gen_ai.provider.name=friendliai`, child `execute_tool <tool>` with correct `gen_ai.tool.name`; no raw payloads in attributes.

- [ ] T008 [P] [US1] Instrument `src/kosmos/engine/query.py` `query()` entry: open `tracer.start_as_current_span("invoke_agent kosmos-query")`, set `gen_ai.operation.name=invoke_agent`, `gen_ai.agent.name=kosmos-query`, and `gen_ai.conversation.id=session_context.session_id` (attach only if `session_context is not None`). On exception propagation: `Status(ERROR)` + `span.record_exception(exc)` + `error.type` (contracts § Span 1, FR-001).
- [ ] T009 [P] [US1] Instrument `src/kosmos/tools/executor.py` `ToolExecutor.dispatch`: wrap each tool call in `tracer.start_as_current_span(f"execute_tool {tool_id}")`, set `gen_ai.operation.name=execute_tool`, `gen_ai.tool.name=<tool_id>`, `gen_ai.tool.type="function"`, `gen_ai.tool.call.id` when available. Map `ToolResult.success=False` → `Status(ERROR)` + `error.type=<filter_metadata({"error_class": ...})["error_class"]>`. NO payloads as attributes (contracts § Span 3, FR-003, FR-011).
- [ ] T010 [P] [US1] Instrument `src/kosmos/llm/client.py` `LLMClient.generate_stream`: open `tracer.start_as_current_span("chat")`, set `gen_ai.operation.name=chat`, `gen_ai.provider.name="friendliai"`, `gen_ai.request.model=<req.model>`, and optional `gen_ai.request.temperature`/`max_tokens`/`top_p` when present (contracts § Span 2; token aggregation + finish_reasons deferred to Phase 5/US2).
- [ ] T011 [US1] Wire `setup_tracing()` invocation into CLI bootstrap (`src/kosmos/cli/*` main entry — locate current bootstrap module and call once before first query). Ensure tracer acquisition uses module-level `trace.get_tracer(__name__)` (research.md § IP1) in `query.py`, `client.py`, `executor.py`. Depends on: T008, T009, T010.
- [ ] T012 [P] [US1] Add `tests/observability/test_tracing_init.py`: set `OTEL_SDK_DISABLED=true` → `setup_tracing()` returns a `NoOpTracerProvider` and no `BatchSpanProcessor` is registered; set endpoint+headers → returns real `TracerProvider`.
- [ ] T013 [P] [US1] Add `tests/observability/test_query_parent_span.py`: use `InMemorySpanExporter` + `SimpleSpanProcessor`, run a mocked `query()` end-to-end, assert trace has exactly one `invoke_agent kosmos-query` root with `gen_ai.conversation.id` attached and at least one child per `chat` + `execute_tool` kind (FR-001, SC-001).
- [ ] T014 [P] [US1] Add `tests/observability/test_tool_execute_span.py`: assert `execute_tool <id>` span captures `gen_ai.tool.name`, `gen_ai.tool.type="function"`, and that a raised `ToolError` yields `Status.ERROR` + `error.type` attribute; verify tool-arg dict is NOT a span attribute (FR-003, FR-011).
- [ ] T015 [P] [US1] Add `tests/observability/test_otel_bridge_pii.py`: feed `filter_metadata` with `{"tool_id": "x", "step": 1, "user_input": "홍길동", "pii_email": "a@b"}` and assert only `tool_id` + `step` remain; assert the key set exactly matches `event_logger._ALLOWED_METADATA_KEYS` ∩ input-keys (FR-011, data-model.md § E5 invariant).

**Checkpoint**: US1 tests green with `uv run pytest tests/observability/`. MVP deliverable complete.

## Phase 4 — User Story 3: CI runs without an OTLP collector (P1)

**Story goal**: `OTEL_SDK_DISABLED=true` yields zero network activity and zero behavioral drift from the pre-OTel baseline.

**Independent test**: With `OTEL_SDK_DISABLED=true`, `uv run pytest` passes end-to-end; no HTTP calls to any OTLP endpoint are made (verified by a test that monkeypatches `httpx` and asserts zero OTLP-shaped requests).

- [ ] T016 [US3] Verify `src/kosmos/observability/tracing.py` `setup_tracing()` short-circuits BEFORE any `OTLPSpanExporter` / `BatchSpanProcessor` construction when `OTEL_SDK_DISABLED=true` (guard at the top of the function); add a warn-once log when endpoint is missing but `OTEL_SDK_DISABLED` is unset (FR-009, FR-010).
- [ ] T017 [P] [US3] Add `tests/observability/test_otel_sdk_disabled.py`: set `OTEL_SDK_DISABLED=true` via `monkeypatch.setenv`, run a mocked `query()` call; assert (a) all spans returned are no-op (`span.is_recording() is False`), (b) no `BatchSpanProcessor` instance exists on the tracer provider, (c) module-level counter of OTLP HTTP calls remains 0 (FR-009, SC-003).
- [ ] T018 [US3] Update `.github/workflows/*.yml` (whichever runs `pytest`) to inject `OTEL_SDK_DISABLED=true` as a job-level env; locate the file via `grep -l "uv run pytest" .github/workflows/` and add the env. Document in `docs/testing.md` if that file exists (FR-009, SC-003).

**Checkpoint**: Full `uv run pytest` passes locally with `OTEL_SDK_DISABLED=true`; CI workflow reflects the env.

## Phase 5 — User Story 2: SRE monitors token spend and streaming throughput (P2)

**Story goal**: Every completed streaming chat writes one set of usage attributes (`gen_ai.usage.input_tokens`, `gen_ai.usage.output_tokens`, `gen_ai.response.model`, `gen_ai.response.finish_reasons`) exactly once at stream end; 429 retries increment a labeled counter without cloning the span.

**Independent test**: Run 100 mocked streaming calls; assert 100/100 spans carry all four usage attributes and each attribute appears at most once per span. Simulate a 429 with `Retry-After: 2` → one `chat` span, one increment on `kosmos_llm_rate_limit_retries_total{provider=friendliai, model=<m>}`.

- [ ] T019 [US2] In `src/kosmos/llm/client.py` `generate_stream`, accumulate usage/finish_reasons internally (reuse existing pattern in `src/kosmos/llm/usage.py`); at stream finalize (success OR clean EOF), call `span.set_attributes({GEN_AI_USAGE_INPUT_TOKENS: i, GEN_AI_USAGE_OUTPUT_TOKENS: o, GEN_AI_RESPONSE_MODEL: m, GEN_AI_RESPONSE_FINISH_REASONS: [...]})` exactly once. Extend T010 — do NOT write per chunk (FR-002, FR-005, research.md § D6).
- [ ] T020 [US2] In `src/kosmos/llm/client.py` retry loop (from spec 019), increment metric `kosmos_llm_rate_limit_retries_total` via the existing `MetricsCollector` API with labels `{provider: "friendliai", model: <req.model>}` each time a 429 is received and a retry is about to be issued (after `Retry-After` honor). Do NOT create per-attempt spans (FR-006, research.md § D7).
- [ ] T021 [P] [US2] Add `tests/observability/test_llm_chat_span.py`: drive `LLMClient.generate_stream` against a mocked streaming source that emits N token chunks + usage; assert the resulting `chat` span has the four required usage attributes set exactly once (count attribute writes via a custom span recorder) (FR-002, FR-005, SC-002).
- [ ] T022 [P] [US2] Add `tests/observability/test_retry_429_counter.py`: mock httpx to return `429` with `Retry-After: 0` twice then succeed; assert (a) metric counter incremented by 2 with correct labels, (b) exactly one `chat` span is emitted (FR-006).

**Checkpoint**: US1 + US2 + US3 tests all green; 100-call stress test confirms SC-002 100/100.

## Phase 6 — User Story 4: Operator brings up the local Langfuse stack with one command (P2)

**Story goal**: `docker compose -f docker-compose.dev.yml up -d` brings Langfuse v3 online locally so a developer can see their first trace within 10 minutes of clone.

**Independent test**: From a fresh clone on a machine with Docker: follow `quickstart.md § A` → first trace visible in Langfuse UI in ≤10 min (SC-005).

- [ ] T023 [US4] Create `docker-compose.dev.yml` with the Langfuse v3 stack (`langfuse-web`, `langfuse-worker`, `postgres`, `redis`, `clickhouse`, `minio`) based on the official reference in research.md § D9; expose port 3000 for the web UI + OTLP ingest. Include named volumes for postgres/clickhouse/minio; do NOT commit any secrets (FR-014, SC-005).
- [ ] T024 [US4] Manual validation walkthrough using `quickstart.md § A` on the current dev machine; record observed boot time and first-trace time in the PR description (not a checked-in artifact). Confirms SC-005 ≤10 min.

## Phase 7 — Polish & cross-cutting

- [ ] T025 [P] Run `uv run pytest` twice — once with `OTEL_SDK_DISABLED=true`, once unset with a mocked OTLP sink — and confirm both pass with zero flakes (SC-003, SC-004).
- [ ] T026 [P] Audit span attributes with a grep over the three instrumented modules (`src/kosmos/engine/query.py`, `src/kosmos/llm/client.py`, `src/kosmos/tools/executor.py`): no `span.set_attribute` call passes raw tool arguments, response bodies, user message text, or any key outside `_ALLOWED_METADATA_KEYS` ∪ `gen_ai.*` semconv constants (FR-011, contracts § PII rule).
- [ ] T027 Confirm dependency budget: `grep -E '^\s*"opentelemetry' pyproject.toml` returns exactly 3 lines (sdk / exporter-otlp-proto-http / semantic-conventions); `grep -E 'instrumentation|openllmetry|traceloop' pyproject.toml uv.lock` returns zero matches (SC-006, FR-016).
- [ ] T028 [P] Verify Langfuse UI manually renders: `invoke_agent`-kind-aware view shows token usage, `execute_tool` child spans render, gen_ai dashboard auto-populates — this validates that attribute names match semconv exactly (SC-001).
- [ ] T029 [P] Add `tests/observability/test_metrics_collector_unchanged.py`: capture a snapshot of `MetricsCollector` public API output (counter/histogram/gauge method signatures + emitted metric names/labels) before and after `setup_tracing()` is invoked; assert equality. Guards FR-012 (existing MetricsCollector behavior unchanged).
- [ ] T030 [P] Add `tests/observability/test_observability_event_unchanged.py`: run a mocked agent loop with OTel enabled; assert every `ObservabilityEvent` emitted by the legacy `ObservabilityEventLogger` is byte-identical to the pre-OTel baseline (event name, metadata keys after whitelist, timestamps fields present). Guards FR-013 (parallel emission, no drift).

## Dependencies

```
T001 ──► T002 [P]
         T003 [P]
         │
         ▼
Phase 2: T004 [P] ──┐
         T005 [P] ──┤
         T006 ──────┤ (depends on T004, T005)
         T007 [P] ◄─┘
         │
         ▼ (checkpoint)
Phase 3 US1:
         T008 [P] ──┐
         T009 [P] ──┤
         T010 [P] ──┤
         T011 ◄─────┘ (wires T008+T009+T010 into bootstrap)
         T012 [P] ──┐
         T013 [P] ──┤ (tests can run after T011)
         T014 [P] ──┤
         T015 [P] ──┘
         │
         ▼ (MVP checkpoint)
Phase 4 US3 (independent of US1 tests but reuses T006):
         T016 ─► T017 [P]
         T018
         │
         ▼
Phase 5 US2 (extends T010):
         T019 ─► T021 [P]
         T020 ─► T022 [P]
         │
         ▼
Phase 6 US4 (independent, needs T002):
         T023 ─► T024
         │
         ▼
Phase 7 Polish:
         T025 [P], T026 [P], T027, T028 [P], T029 [P], T030 [P]
```

**User story independence**: US1 and US3 can proceed in parallel after Phase 2. US2 depends on US1's `chat` span existing (T010). US4 depends only on Phase 1 (T002).

## Parallel execution examples

**Within Phase 2** (foundational):
```
# Launch T004, T005, T007 in parallel; T006 follows (imports T004+T005)
[P] T004 semconv constants
[P] T005 otel_bridge filter_metadata
[P] T007 package re-exports
# then:
T006 tracing.py setup_tracing()
```

**Within Phase 3 (US1 MVP)**:
```
# After Phase 2 checkpoint, launch T008/T009/T010 in parallel (different files)
[P] T008 engine/query.py invoke_agent span
[P] T009 tools/executor.py execute_tool span
[P] T010 llm/client.py chat span (base)
# then serialize:
T011 CLI bootstrap wires setup_tracing
# then launch all US1 tests in parallel (separate files):
[P] T012 test_tracing_init
[P] T013 test_query_parent_span
[P] T014 test_tool_execute_span
[P] T015 test_otel_bridge_pii
```

**Phase 5 (US2)** — can launch T019 and T020 in parallel (different sections of client.py but non-overlapping edits: streaming finalize vs retry loop). Tests T021/T022 [P] after.

## Implementation strategy

1. **MVP = Phase 1 + Phase 2 + Phase 3 (US1)**. Stop here and validate one full trace in Langfuse UI — this delivers SC-001. Land as incremental PR if scope feels too large otherwise.
2. **Add P1 safety**: Phase 4 (US3) makes CI safe. Land together with MVP if possible; infra-level, small risk.
3. **Add P2 operational value**: Phase 5 (US2) gives SRE their token/retry data. Phase 6 (US4) lowers developer onboarding friction.
4. **Polish**: Phase 7 is audit + proof; never skip T026 (PII audit) and T027 (dependency budget) before merge.

## Validation checklist

- [ ] All tasks start with `- [ ]` checkbox, have `TNNN` ID, and cite concrete file paths
- [ ] Every user-story task carries a `[USn]` label
- [ ] Setup/Foundational/Polish tasks have no story label
- [ ] Parallelizable tasks marked `[P]` touch different files
- [ ] All 16 FRs map to at least one task; all 6 SCs map to at least one validation task
- [ ] Dependencies graph has no cycles
