# Phase 0 Research: Tool System & Registry (Layer 2)

**Feature**: Epic #6 — Tool System & Registry
**Date**: 2026-04-12
**Status**: Complete

## Research Tasks

### RT-1: Tool Registry Architecture Pattern

**Question**: What registry pattern best fits KOSMOS's tool system?

**Decision**: In-memory registry with decorator-based registration, similar to Pydantic AI's schema-driven approach. Tools register at import time via a `@register_tool` decorator or explicit `registry.register(tool)` call.

**Rationale**: From `docs/vision.md` Layer 2 — "Each public API is wrapped as a tool module with a schema-driven registration and fail-closed defaults." Pydantic AI uses schema-driven tool definitions with Pydantic models for input/output validation. This pattern fits naturally since KOSMOS already mandates Pydantic v2 for all I/O.

**Reference**: Pydantic AI (`pydantic/pydantic-ai`) — schema-driven tool registry. Claude Agent SDK (`anthropics/claude-agent-sdk-python`) — tool definitions and execution.

**Alternatives considered**:
- Plugin-based discovery (entry_points): over-engineered for Phase 1 with ~10 tools
- YAML/JSON manifest: rejected — Pydantic models already describe schemas; a separate manifest would be redundant
- Auto-discovery (importlib scanning): fragile and implicit; explicit registration is clearer

---

### RT-2: Fail-Closed Default Mechanism

**Question**: How to enforce that omitted fields default to the most restrictive setting?

**Decision**: Use Pydantic v2 `Field(default=...)` with conservative values. The `GovAPITool` model defines all security-sensitive fields with fail-closed defaults directly in the model definition.

**Rationale**: From Constitution § II — "Every tool adapter and API integration MUST default to the most restrictive setting." Pydantic v2's `Field()` with explicit defaults ensures that any tool registered without specifying these fields automatically gets the conservative value. No additional enforcement layer is needed — the type system handles it.

**Key defaults**:
- `requires_auth: bool = True`
- `is_personal_data: bool = True`
- `is_concurrency_safe: bool = False`
- `cache_ttl_seconds: int = 0`
- `rate_limit_per_minute: int = 10`

**Reference**: Constitution § II (Fail-Closed Security).

**Alternatives considered**:
- Post-registration validation hook: unnecessary when Pydantic defaults handle it
- Separate SecurityPolicy model: over-engineering; the flags belong on the tool definition itself

---

### RT-3: Bilingual Search Strategy

**Question**: How should `search_tools()` match Korean and English keywords?

**Decision**: Token-based matching with case-insensitive substring search. Split the query into tokens (whitespace-separated), split each tool's `search_hint` into tokens, and compute a relevance score based on token overlap count.

**Rationale**: Phase 1 targets ~10 tools. A simple token-overlap approach is sufficient and avoids adding NLP dependencies. Korean morphological analysis (e.g., KoNLPy) would add significant complexity and a non-trivial dependency chain for minimal benefit at this scale.

**Scoring algorithm**:
```python
score = sum(1 for query_token in query_tokens
            if any(query_token in hint_token or hint_token in query_token
                   for hint_token in hint_tokens))
```

**Reference**: Claude Code reconstructed (`ChinaSiro/claude-code-sourcemap`) — tool discovery patterns, keyword-based tool matching.

**Alternatives considered**:
- Full-text search (SQLite FTS5): over-engineered for in-memory with ~10 tools
- Embedding-based semantic search: Phase 2+ enhancement; requires embedding model
- Regex matching: fragile for Korean text with agglutinative morphology
- KoNLPy morphological analysis: adds ~200MB dependency (Java/JVM) for minimal benefit at Phase 1 scale

---

### RT-4: Prompt Cache Partitioning Design

**Question**: How to partition tools for optimal prompt caching?

**Decision**: Static core/situational partition defined by a `is_core: bool` field on `GovAPITool`. Core tools are exported as a deterministic, sorted list. Situational tools are discovered via `search_tools()`.

**Rationale**: From `docs/vision.md` Layer 2 — "The tool registry orders tools into two partitions: core tools (always loaded, stable across sessions) form the prompt prefix, and situational tools (discovered on demand via tool search) form the suffix." Deterministic ordering (sorted by `id`) ensures byte-for-byte identical output across invocations, maximizing cache hits.

**Reference**: Anthropic docs — prompt caching. Vision.md Layer 2 — prompt cache partitioning.

**Phase 1 core tools**: The ~10 Phase 1 tools (KOROAD, KMA adapters) plus `search_tools` meta-tool. Dynamic promotion is deferred to Phase 2.

**Alternatives considered**:
- LRU-based dynamic partitioning: Phase 2+ complexity; requires usage analytics
- Frequency-based auto-promotion: requires call counting infrastructure beyond rate limiting
- No partitioning: wastes prompt tokens and cache budget

---

### RT-5: Rate Limiter Implementation

**Question**: What rate limiting algorithm to use?

**Decision**: Sliding window counter using `collections.deque` with timestamps. Each tool maintains a deque of call timestamps. On each call, expired entries (older than 1 minute) are pruned, and the call is allowed if `len(deque) < rate_limit_per_minute`.

**Rationale**: Simple, memory-efficient, and accurate for Phase 1's single-process scope. No external dependencies needed. The deque naturally handles clock progression — old entries fall off as new ones are added.

**Reference**: OpenAI Agents SDK — rate limit handling patterns.

**Alternatives considered**:
- Token bucket: more complex, designed for bursty traffic; government APIs have strict per-minute limits, not burst allowances
- Fixed window: inaccurate at window boundaries (2x burst possible)
- Redis-based distributed limiter: over-engineered for Phase 1 single-process CLI
- leaky bucket: designed for smoothing output rate, not input throttling

---

### RT-6: Tool Execution Dispatch Pattern

**Question**: How should the registry dispatch tool calls from the LLM?

**Decision**: The `ToolExecutor` looks up the tool by name in the registry, validates input against the tool's `input_schema` using Pydantic, calls the tool's `execute()` method, and validates output against `output_schema`. The executor is a thin dispatch layer — actual API logic lives in each adapter.

**Rationale**: Separation of concerns: the registry knows about tools, the executor handles dispatch + validation, and each adapter implements the API-specific logic. This maps to vision.md's statement that "tool execution is the adapter's responsibility; the registry dispatches but does not implement API-specific logic."

**Reference**: Pydantic AI — schema-driven validation. Claude Agent SDK — tool execution flow.

**Executor flow**:
```
LLM tool_call → ToolExecutor.dispatch(name, args_json)
  → Registry.lookup(name)
  → input_schema.model_validate_json(args_json)
  → rate_limiter.check(tool_id)
  → adapter.execute(validated_input)
  → output_schema.model_validate(raw_output)
  → return validated_output
```

**Alternatives considered**:
- Direct registry execution (no separate executor): conflates concerns; harder to add cross-cutting logic (rate limiting, logging, permission checks)
- Middleware chain: over-engineered for Phase 1; executor methods handle the sequential flow

---

### RT-7: OpenAI Function-Calling Format Export

**Question**: How to export tool definitions for LLM consumption?

**Decision**: Each `GovAPITool` exports to the OpenAI function-calling format via a `.to_openai_tool()` method that produces a dict matching the `ToolDefinition` schema from Epic #4.

**Rationale**: The LLM client (Epic #4) sends tool definitions in OpenAI format. The registry must produce this format. Generating the JSON Schema from Pydantic models is straightforward via `model.model_json_schema()`.

**Export format**:
```python
{
    "type": "function",
    "function": {
        "name": tool.id,
        "description": f"{tool.name_ko} — {tool.provider}",
        "parameters": tool.input_schema.model_json_schema()
    }
}
```

**Reference**: Claude Agent SDK — tool definitions. FriendliAI OpenAI-compatible API.

**Alternatives considered**:
- Custom format: rejected — no reason to diverge from the OpenAI standard that the LLM client already supports
- Anthropic tool format: rejected — FriendliAI uses OpenAI-compatible format
