# CLAUDE.md

This project's agent instructions live in [`AGENTS.md`](./AGENTS.md). Read that file first.

@AGENTS.md

## Claude Code-specific notes

- **Spec Kit skills**: `/speckit-*` slash commands under `.claude/skills/`. Use for every non-trivial feature.
- **Auto memory**: Observations go to `MEMORY.md` (auto-maintained). Do not hand-edit.
- **Model**: Opus (Lead/planning), Sonnet (Teammates/implementation). `effortLevel: high`.
- **Agent Teams**: Enabled. At `/speckit-implement`, spawn Teammates (Sonnet) for parallel task execution. See `AGENTS.md § Agent Teams` for rules.
- **TodoWrite**: In-session task tracking only during `/speckit-implement`. Do not persist to disk.

## Active Technologies
- Python 3.12+ + httpx >=0.27 (async HTTP), pydantic >=2.0 (models), pydantic-settings >=2.0 (config) (spec/wave-1)
- N/A (in-memory session state only) (spec/wave-1)
- Python 3.12+ + pydantic >=2.0 (models + validation) (spec/wave-1)
- N/A (in-memory registry) (spec/wave-1)
- Python 3.12+ + pytest, pytest-asyncio, httpx (mock targets), pydantic v2 (existing) (013-scenario1-e2e-route-safety)
- N/A (in-memory test state only) (013-scenario1-e2e-route-safety)
- Python 3.12+ + httpx >=0.27, pydantic >=2.0, pydantic-settings >=2.0 (014-phase1-live-validation)
- Python 3.12+ + httpx >=0.27, pydantic >=2.0, pytest, pytest-asyncio (018-phase1-live-extension)
- N/A (test-only; observability snapshots are in-memory test state) (018-phase1-live-extension)
- Python 3.12+ + `httpx >=0.27` (async HTTP + streaming 429 detection), `pydantic >=2.0` (tool I/O schemas with `Field(description=...)` exposed as JSON schema to the LLM), `pytest` + `pytest-asyncio` (unit + `@pytest.mark.live` gated E2E). No new runtime dependencies introduced. (019-phase1-hardening)
- N/A (no persistent state; rate-limit retry counters and semaphore live in `LLMClient` instance memory for the session's lifetime). (019-phase1-hardening)
- Python 3.12+ + `httpx>=0.27` (async HTTP, 기존), `pydantic>=2.13` (모델, 기존), `opentelemetry-sdk` (신규), `opentelemetry-exporter-otlp-proto-http` (신규), `opentelemetry-semantic-conventions` (신규, GenAI v1.40 experimental opt-in) (021-observability-otel-genai)
- N/A (span 메모리 버퍼 + OTLP 전송, 로컬 Langfuse는 Docker 스택의 Postgres/ClickHouse/MinIO가 담당) (021-observability-otel-genai)
- Python 3.12+ + `httpx>=0.27` (async HTTP, existing), `pydantic>=2.13` (schemas, existing), `pydantic-settings>=2.0` (env config, existing), `rank_bm25>=0.2.2` (NEW — Apache-2.0, BM25 retrieval), `kiwipiepy>=0.17` (NEW — MIT, Korean morpheme tokenizer); LLM-visible surface (FR-001): `resolve_location` (geocoding) + `lookup` (two modes: `search` = BM25 retrieval, `fetch` = adapter invocation); 4 seed adapters: koroad_accident_hazard_search, kma_forecast_fetch, hira_hospital_search, nmc_emergency_search (022-mvp-main-tool)
- N/A — in-memory registry; BM25 index rebuilt at registry boot and on registration; no persistent state (022-mvp-main-tool)
- Python 3.12+ + pydantic >= 2.13, httpx >= 0.27 (existing) (023-nmc-freshness-slo)
- N/A (in-memory validation only) (023-nmc-freshness-slo)

## Recent Changes
- 019-phase1-hardening: LLM 429 resilience (Retry-After + exponential backoff + per-session semaphore) and KOROAD tool-input discipline (Field descriptions + session guidance)
- spec/wave-1: Added Python 3.12+ + httpx >=0.27 (async HTTP), pydantic >=2.0 (models), pydantic-settings >=2.0 (config)
