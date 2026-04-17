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
- Python 3.12+ (existing project baseline; no version bump required for this spec). + Pydantic v2 (existing), `httpx >=0.27` (existing, not exercised by this spec's code seed), `pytest` + `pytest-asyncio` (existing). No new runtime dependencies introduced. JSON Schema Draft 2020-12 and OpenAPI 3.0 are specification targets, not dependencies; they are validated externally. (024-tool-security-v1)
- N/A at this layer. `ToolCallAuditRecord` is a schema contract. Actual append-only audit storage and Merkle chain construction are explicitly deferred. (024-tool-security-v1)
- Python 3.12+ (existing project baseline; no version bump). + `pydantic >= 2.13` (existing — V1–V5 use `@model_validator(mode="after")`), `pytest` + `pytest-asyncio` (existing). **No new runtime dependencies** (AGENTS.md hard rule). (025-tool-security-v6)
- N/A — this is a validator + backstop spec; no persistent state. The canonical mapping lives as code (validator module-level constant) and as documentation (`docs/security/tool-template-security-spec-v1.md` v1.1 matrix). (025-tool-security-v6)
- Python 3.12+ (existing project baseline; no bump). + `pydantic >= 2.13` (existing, type validation), `pydantic-settings >= 2.0` (existing, `BaseSettings`), `pytest` + `pytest-asyncio` (existing, tests), stdlib `os`/`sys`/`time`/`pathlib`/`argparse`/`re`. **No new runtime dependencies** — AGENTS.md hard rule. (feat/468-secrets-config)
- N/A (in-memory configuration only; `.env` is source-of-truth on disk, read-only from the guard's perspective). (feat/468-secrets-config)
- N/A — in-memory vector matrix + in-memory BM25 doc vectors; HF hub cache at `~/.cache/huggingface/hub/` for weights (user-scoped, not repo-committed). (feat/585-retrieval-dense)

## Recent Changes
- 025-tool-security-v6: V6 `auth_type` ↔ `auth_level` consistency invariant (FR-039–FR-048) layered on V1–V5; canonical allow-list mapping `{public⇒{public,AAL1}, api_key⇒{AAL1,AAL2,AAL3}, oauth⇒{AAL1,AAL2,AAL3}}`; two-layer defense (pydantic `@model_validator` + `ToolRegistry.register()` backstop against `model_construct` bypass); registry-wide regression scan; `docs/security/tool-template-security-spec-v1.md` v1.1 worked examples; MVP meta-tool pattern `(public, AAL1) + requires_auth=True` documented as compliant (not an exemption)
- 024-tool-security-v1: Tool Template Security Spec v1 normative doc; ToolCallAuditRecord schema v1 + I1–I4 invariants; GovAPITool field extensions (auth_level, pipa_class, is_irreversible, dpa_reference); SBOM workflow scaffold (SPDX 2.3 + CycloneDX 1.6, FR-019 divergence gate); /agent-delegation OpenAPI 3.0 skeleton
- 019-phase1-hardening: LLM 429 resilience (Retry-After + exponential backoff + per-session semaphore) and KOROAD tool-input discipline (Field descriptions + session guidance)
- spec/wave-1: Added Python 3.12+ + httpx >=0.27 (async HTTP), pydantic >=2.0 (models), pydantic-settings >=2.0 (config)
