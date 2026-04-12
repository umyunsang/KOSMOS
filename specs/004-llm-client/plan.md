# Implementation Plan: LLM Client Integration (FriendliAI K-EXAONE)

**Branch**: `spec/wave-1` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/004-llm-client/spec.md`

## Summary

Implement an async LLM client for FriendliAI Serverless endpoint serving K-EXAONE, with streaming SSE support, token usage tracking, session budget enforcement, and exponential backoff retry logic. The client uses httpx for HTTP, Pydantic v2 for all I/O models, and async generators for streaming — following the Claude Agent SDK communication protocol pattern.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: httpx >=0.27 (async HTTP), pydantic >=2.0 (models), pydantic-settings >=2.0 (config)
**Storage**: N/A (in-memory session state only)
**Testing**: pytest + pytest-asyncio + respx (httpx mocking)
**Target Platform**: Cross-platform (macOS, Linux) CLI
**Project Type**: Library module within KOSMOS (`src/kosmos/llm/`)
**Performance Goals**: Streaming TTFT overhead < 50ms (client-side processing only); non-streaming latency bound by model generation time
**Constraints**: No hardcoded API keys; session budget enforcement; KOSMOS_ env var prefix; fail-closed security posture
**Scale/Scope**: Single concurrent session for Phase 1; design for future multi-session support

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | All design decisions mapped to Claude Agent SDK (async generator), OpenAI Agents SDK (retry matrix), vision.md Layer 1/6 |
| II. Fail-Closed Security | PASS | N/A for LLM client (no citizen PII). Config requires explicit token. |
| III. Pydantic v2 Strict Typing | PASS | All models use Pydantic v2. `Any` only in JSON Schema parameters (external format). |
| IV. Government API Compliance | N/A | LLM client does not call data.go.kr APIs |
| V. Policy Alignment | PASS | Budget enforcement supports taxpayer-funded cost control |

**Post-Phase 1 re-check**: PASS. Data model uses Pydantic v2 throughout. No `Any` in I/O schemas (JSON Schema `parameters` field uses `dict[str, Any]` which represents an external schema definition, not internal KOSMOS I/O). All config via `KOSMOS_`-prefixed env vars.

## Project Structure

### Documentation (this feature)

```text
specs/004-llm-client/
├── plan.md              # This file
├── research.md          # Phase 0 output — 6 research tasks resolved
├── data-model.md        # Phase 1 output — 11 entities defined
├── quickstart.md        # Phase 1 output — usage examples
├── contracts/
│   └── llm-client-api.md  # Public API contract
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
src/kosmos/
├── __init__.py           # Existing
└── llm/
    ├── __init__.py       # Public exports
    ├── client.py         # LLMClient (complete + stream methods)
    ├── models.py         # Pydantic v2 models (ChatMessage, StreamEvent, etc.)
    ├── config.py         # LLMClientConfig (pydantic-settings)
    ├── errors.py         # Error hierarchy (KosmosLLMError and subclasses)
    ├── retry.py          # RetryPolicy and exponential backoff logic
    └── usage.py          # UsageTracker with budget enforcement

tests/
└── llm/
    ├── __init__.py
    ├── conftest.py       # Shared fixtures (mock client, respx routes)
    ├── test_client.py    # LLMClient unit tests
    ├── test_models.py    # Pydantic model validation tests
    ├── test_config.py    # Configuration loading tests
    ├── test_retry.py     # Retry logic tests
    ├── test_usage.py     # UsageTracker tests
    └── test_streaming.py # SSE streaming tests
```

**Structure Decision**: Single project layout. The LLM client is a library module (`kosmos.llm`) within the KOSMOS package, not a standalone service.

## Reference Mapping

| Design Decision | Primary Reference | Secondary Reference |
|----------------|-------------------|---------------------|
| Async generator streaming | Claude Agent SDK — async generator communication protocol | vision.md Layer 1 — "No callbacks, no event buses" |
| Mutable history + immutable snapshots | vision.md Layer 1 — prompt cache trick | Claude Code reconstructed (tool loop internals) |
| Exponential backoff with jitter | vision.md Layer 6 — error recovery matrix | OpenAI Agents SDK — retry matrix with composable policies |
| Token budget enforcement | vision.md Layer 1 — cost accounting as first-class | Claude Agent SDK — usage tracking |
| Pydantic v2 models for all I/O | Constitution § III — strict typing | Pydantic AI — schema-driven tool registry |
| Environment-based config | Constitution § IV — no hardcoded keys | AGENTS.md — KOSMOS_ prefix |

## Dependency Note

`pydantic-settings` (separate from `pydantic`) must be added to `pyproject.toml` dependencies for `LLMClientConfig`. This is the only new dependency beyond what's already declared.

## Complexity Tracking

No constitution violations. No complexity justifications needed.
