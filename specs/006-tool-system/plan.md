# Implementation Plan: Tool System & Registry (Layer 2)

**Branch**: `spec/wave-1` | **Date**: 2026-04-12 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/006-tool-system/spec.md`

## Summary

Implement the schema-driven tool registry for KOSMOS Layer 2 with fail-closed defaults, bilingual keyword search, prompt cache partitioning (core vs. situational), sliding-window rate limiting, and tool execution dispatch with Pydantic v2 input/output validation. The registry exports tool definitions in OpenAI function-calling format for consumption by the LLM client (Epic #4).

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: pydantic >=2.0 (models + validation)
**Storage**: N/A (in-memory registry)
**Testing**: pytest + pytest-asyncio
**Target Platform**: Cross-platform (macOS, Linux) CLI
**Project Type**: Library module within KOSMOS (`src/kosmos/tools/`)
**Performance Goals**: Tool search < 10ms for 100 tools; registry export deterministic (byte-for-byte identical)
**Constraints**: Fail-closed defaults (Constitution § II); Pydantic v2 for all I/O; no `Any` in I/O schemas; bilingual search_hint
**Scale/Scope**: ~10 tools in Phase 1; design for hundreds

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Notes |
|-----------|--------|-------|
| I. Reference-Driven Development | PASS | Design mapped to Pydantic AI (registry), Claude Agent SDK (tool definitions), Claude Code reconstructed (tool discovery) |
| II. Fail-Closed Security | PASS | All security-sensitive fields default to restrictive values via Pydantic `Field(default=...)` |
| III. Pydantic v2 Strict Typing | PASS | `GovAPITool`, `ToolResult`, `SearchToolsInput/Output` all use Pydantic v2. No `Any` in I/O. |
| IV. Government API Compliance | PASS | Registry does not call APIs directly. Rate limiter enforces per-tool limits. |
| V. Policy Alignment | PASS | Fail-closed defaults protect citizen PII by default. |

**Post-Phase 1 re-check**: PASS. `GovAPITool.input_schema` and `output_schema` fields hold `type[BaseModel]` references (not `Any`). The `to_openai_tool()` method generates JSON Schema via Pydantic's `model_json_schema()`, which internally uses `Any` in the generated schema dict — this is acceptable because it's an export format, not KOSMOS I/O.

## Project Structure

### Documentation (this feature)

```text
specs/006-tool-system/
├── plan.md              # This file
├── research.md          # Phase 0 output — 7 research tasks resolved
├── data-model.md        # Phase 1 output — 9 entities defined
├── quickstart.md        # Phase 1 output — usage examples
├── contracts/
│   └── tool-registry-api.md  # Public API contract
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
src/kosmos/
├── __init__.py           # Existing
└── tools/
    ├── __init__.py       # Public exports
    ├── models.py         # GovAPITool, ToolResult, ToolSearchResult, SearchTools I/O
    ├── registry.py       # ToolRegistry (register, lookup, search, partition)
    ├── executor.py       # ToolExecutor (dispatch with validation)
    ├── rate_limiter.py   # RateLimiter (sliding window)
    ├── errors.py         # Error hierarchy
    └── search.py         # search_tools meta-tool, bilingual search logic

tests/
└── tools/
    ├── __init__.py
    ├── conftest.py       # Mock tools, sample registries
    ├── test_models.py    # GovAPITool validation, fail-closed defaults
    ├── test_registry.py  # Registration, lookup, search, partitioning
    ├── test_executor.py  # Dispatch, validation, error handling
    ├── test_rate_limiter.py  # Sliding window, reset, edge cases
    └── test_search.py    # Bilingual search, ranking, edge cases
```

**Structure Decision**: Single project layout. The tool system is a library module (`kosmos.tools`) within the KOSMOS package, parallel to `kosmos.llm` (Epic #4).

## Reference Mapping

| Design Decision | Primary Reference | Secondary Reference |
|----------------|-------------------|---------------------|
| Schema-driven tool registry | Pydantic AI — schema-driven tool modules | vision.md Layer 2 — "Each API wrapped as a tool module" |
| Fail-closed defaults | Constitution § II — non-negotiable security | vision.md Layer 2 — "Fail-closed posture" |
| Bilingual keyword search | Claude Code reconstructed — tool discovery | vision.md Layer 2 — lazy tool discovery |
| Prompt cache partitioning | Anthropic docs — prompt caching | vision.md Layer 2 — core vs. situational |
| Rate limiting (sliding window) | OpenAI Agents SDK — rate limit handling | vision.md Layer 1 — usage tracker |
| OpenAI tool format export | Claude Agent SDK — tool definitions | FriendliAI OpenAI-compatible API |
| Tool execution dispatch | Pydantic AI — schema validation | Claude Code reconstructed — tool execution flow |

## Complexity Tracking

No constitution violations. No complexity justifications needed.
