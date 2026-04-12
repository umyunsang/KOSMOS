# Feature Specification: Tool System & Registry (Layer 2)

**Epic**: #6
**Created**: 2026-04-12
**Status**: Draft
**Layer**: Layer 2 — Tool System
**Input**: Schema-driven tool registry with fail-closed defaults, prompt cache partitioning, lazy tool discovery, and rate limit tracking for government API adapters.

## User Scenarios & Testing

### User Story 1 - Tool Registration with Fail-Closed Defaults (Priority: P1)

A developer adds a new government API adapter to KOSMOS by declaring a tool definition with only the fields that deviate from the conservative defaults. The system ensures that any omitted fields default to the most restrictive settings (requires_auth=True, is_personal_data=True, is_concurrency_safe=False, cache_ttl=0).

**Why this priority**: This is the foundation of the entire tool system. Without fail-closed registration, a contributor could accidentally expose personal data APIs as public.

**Independent Test**: Can be tested by registering a tool with minimal fields and verifying all defaults are fail-closed, then registering with explicit overrides and verifying overrides are respected.

**Acceptance Scenarios**:

1. **Given** a tool definition with only id, name_ko, provider, category, endpoint, auth_type, input_schema, output_schema, and search_hint, **When** it is registered, **Then** requires_auth=True, is_personal_data=True, is_concurrency_safe=False, cache_ttl_seconds=0, rate_limit_per_minute=10.
2. **Given** a tool definition with explicit `is_personal_data=False`, **When** it is registered, **Then** only that specific default is overridden; all other defaults remain fail-closed.
3. **Given** a tool definition missing a required field (e.g., no input_schema), **When** registration is attempted, **Then** the system rejects it with a validation error.

---

### User Story 2 - Lazy Tool Discovery via search_tools (Priority: P1)

A citizen asks about a topic (e.g., childbirth subsidies). The LLM invokes `search_tools("birth subsidy welfare")` and receives a list of matching tools ranked by relevance. The citizen does not need to know which ministry runs which API.

**Why this priority**: With 5,000+ potential APIs, preloading all schemas is infeasible. Lazy discovery is the only scalable path. This is equally important as registration since neither works without the other.

**Independent Test**: Can be tested by registering multiple tools with varied search_hint values, querying with Korean and English keywords, and verifying relevant tools are returned and irrelevant tools are excluded.

**Acceptance Scenarios**:

1. **Given** 10 registered tools with various search_hints, **When** `search_tools("교통사고 traffic accident")` is called, **Then** tools with matching Korean or English keywords in search_hint are returned, ranked by relevance.
2. **Given** the same registry, **When** `search_tools("날씨 weather forecast")` is called, **Then** only weather-related tools are returned; traffic tools are excluded.
3. **Given** an empty query string, **When** `search_tools("")` is called, **Then** the system returns an empty result set rather than all tools.

---

### User Story 3 - Prompt Cache Partitioning (Priority: P2)

The tool registry separates tools into core tools (always loaded, stable across sessions) and situational tools (discovered on demand). Core tool schemas form the prompt prefix for LLM calls, enabling prompt cache hits across sessions.

**Why this priority**: Cost efficiency is critical for a government-funded service. Cache partitioning can dramatically reduce per-session LLM costs.

**Independent Test**: Can be tested by requesting the core tool list and situational tool list, verifying they are disjoint, and verifying the core list is stable across multiple calls.

**Acceptance Scenarios**:

1. **Given** a registry with tools marked as core and situational, **When** the core tool schemas are requested, **Then** the same ordered list is returned every time (stable for caching).
2. **Given** a citizen switches topics (transport to welfare), **When** the situational tools change, **Then** the core tool schemas remain unchanged.
3. **Given** the core tool list, **When** exported as tool definitions for an LLM call, **Then** the output is a deterministic JSON string suitable for prompt prefix caching.

---

### User Story 4 - Rate Limit Tracking (Priority: P2)

Each tool has a declared rate_limit_per_minute. The registry tracks call counts per tool per time window. When a tool approaches its rate limit, the system warns before blocking; when the limit is hit, calls are queued or rejected.

**Why this priority**: Government APIs have strict quotas. Exceeding them causes 429 errors and potential key suspension.

**Independent Test**: Can be tested by simulating rapid calls to a tool with a low rate limit and verifying calls are rejected after the limit is reached, then verifying the counter resets after the time window.

**Acceptance Scenarios**:

1. **Given** a tool with rate_limit_per_minute=5, **When** 5 calls are made within one minute, **Then** the 6th call is rejected with a rate-limit-exceeded error.
2. **Given** a rate-limited tool, **When** the one-minute window expires, **Then** the call counter resets and new calls are allowed.
3. **Given** multiple tools, **When** rate limits are tracked, **Then** each tool's counter is independent.

---

### User Story 5 - Tool Execution Dispatch (Priority: P3)

When the query engine resolves a tool_call from the LLM, it passes the tool name and arguments to the registry. The registry looks up the tool, validates the input against the Pydantic schema, executes the API call, and validates the output.

**Why this priority**: Execution dispatch connects the registry to the query engine, but the registry's core value (registration, search, rate limiting) works without it.

**Independent Test**: Can be tested by registering a mock tool, dispatching a call with valid arguments and verifying a validated response, then dispatching with invalid arguments and verifying a validation error.

**Acceptance Scenarios**:

1. **Given** a registered tool, **When** dispatched with valid arguments matching the input_schema, **Then** the tool executes and returns output validated against the output_schema.
2. **Given** a registered tool, **When** dispatched with invalid arguments, **Then** a validation error is returned without calling the API.
3. **Given** a tool_call with an unknown tool name, **When** dispatched, **Then** a tool-not-found error is returned.

---

### Edge Cases

- What happens when two tools are registered with the same id? The system rejects the duplicate with a registration error.
- What happens when search_hint is empty or whitespace-only? The system rejects registration with a validation error.
- What happens when a tool's API endpoint is unreachable during execution? The executor raises a connection error; error recovery (Layer 6) handles retry.
- What happens when the rate limit counter overflows (e.g., clock skew)? The counter resets gracefully; stale entries are pruned.
- What happens when a tool's output does not match the output_schema? The system logs a validation warning and returns a schema-mismatch error result; raw output is not returned.

## Requirements

### Functional Requirements

- **FR-001**: System MUST define a GovAPITool model using Pydantic v2 with all fields specified in vision.md Layer 2 (id, name_ko, provider, category, endpoint, auth_type, input_schema, output_schema, requires_auth, is_concurrency_safe, is_personal_data, cache_ttl_seconds, rate_limit_per_minute, search_hint).
- **FR-002**: System MUST enforce fail-closed defaults: requires_auth=True, is_personal_data=True, is_concurrency_safe=False, cache_ttl_seconds=0, rate_limit_per_minute=10.
- **FR-003**: System MUST provide a ToolRegistry with register, lookup (by id), and search (by keyword) operations.
- **FR-004**: System MUST implement `search_tools(query: str)` that matches against search_hint using bilingual (Korean + English) keyword matching.
- **FR-005**: System MUST partition tools into core (always loaded) and situational (on-demand) categories.
- **FR-006**: System MUST export core tool schemas as a deterministic, ordered list suitable for prompt prefix caching.
- **FR-007**: System MUST track per-tool call counts within sliding time windows and reject calls exceeding rate_limit_per_minute.
- **FR-008**: System MUST validate tool call arguments against the tool's input_schema before execution.
- **FR-009**: System MUST validate tool execution results against the tool's output_schema after execution.
- **FR-010**: System MUST reject duplicate tool registrations (same id) with a clear error.
- **FR-011**: System MUST support the `search_tools` meta-tool as a tool itself, registrable in the registry for LLM discovery.
- **FR-012**: System MUST expose tool definitions in OpenAI function-calling format for LLM consumption.

### Key Entities

- **GovAPITool**: The Pydantic v2 model defining a government API tool's metadata, schemas, and operational constraints.
- **ToolRegistry**: The central registry managing tool registration, lookup, search, and partitioning.
- **ToolExecutor**: Dispatches tool calls with input validation, API invocation, and output validation.
- **RateLimiter**: Tracks per-tool call frequency and enforces rate limits.
- **ToolPartition**: Enum or flag distinguishing core tools from situational tools.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A new tool can be registered with only required fields, and all security-sensitive defaults are fail-closed without any developer intervention.
- **SC-002**: Bilingual tool search returns relevant results for both Korean and English queries, with zero false negatives for exact keyword matches.
- **SC-003**: Core tool schema export produces identical output across invocations (byte-for-byte deterministic) for prompt caching effectiveness.
- **SC-004**: Rate limiting correctly prevents calls beyond the configured threshold with zero false positives (legitimate calls within limits are never rejected).
- **SC-005**: All unit tests pass using mock tools and recorded fixtures without requiring live API access.

## Assumptions

- Phase 1 targets approximately 10 high-value tools; the registry design must support scaling to hundreds but does not need to demonstrate 5,000+ tool performance in Phase 1.
- Bilingual search uses simple keyword matching (substring/token overlap) in Phase 1; semantic search is a Phase 2+ enhancement.
- Core tools for Phase 1 are a static list defined in configuration; dynamic core tool promotion is out of scope.
- Tool execution is the adapter's responsibility; the registry dispatches but does not implement API-specific logic.
- The rate limiter uses in-memory counters; persistence across process restarts is not required for Phase 1.
- Tool definitions are registered at application startup; hot-reload of tool definitions at runtime is out of scope for Phase 1.
