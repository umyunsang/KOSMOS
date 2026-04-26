# Phase 0 Research: LLM Client Integration (FriendliAI EXAONE)

**Feature**: Epic #4 — LLM Client Integration
**Date**: 2026-04-12
**Status**: Complete

## Research Tasks

### RT-1: FriendliAI Serverless API Compatibility

**Question**: What is the exact API contract for FriendliAI Serverless with EXAONE?

**Decision**: Use the OpenAI-compatible chat completions API (`/v1/chat/completions`) exposed by FriendliAI Serverless.

**Rationale**: FriendliAI Serverless provides an OpenAI-compatible endpoint. This means standard `POST /v1/chat/completions` with `model`, `messages`, `tools`, `stream`, `temperature`, `max_tokens`, `top_p`, and `stop` parameters. The response format mirrors OpenAI's `ChatCompletion` object with `choices[].message.content`, `choices[].message.tool_calls`, and `usage` (prompt_tokens, completion_tokens, total_tokens). Streaming uses SSE with `data: {...}` lines and `data: [DONE]` terminator.

**Alternatives considered**:
- Native FriendliAI SDK: rejected — adds an unnecessary dependency when httpx can call the OpenAI-compatible endpoint directly.
- OpenAI Python SDK with custom base_url: viable but adds ~15MB dependency for functionality we can implement in ~200 lines of httpx.
- LiteLLM: rejected — too heavy for a focused integration; we need precise control over streaming and retry behavior.

**Key findings**:
- Auth header: `Authorization: Bearer $KOSMOS_FRIENDLI_TOKEN`
- Base URL: configurable via `KOSMOS_FRIENDLI_BASE_URL` (default: `https://api.friendli.ai/v1`)
- Model identifier: configurable via `KOSMOS_FRIENDLI_MODEL` (default: `dep89a2fde0e09`)
- Streaming: `stream: true` returns SSE chunks with `delta.content` and `delta.tool_calls`
- Tool calling: OpenAI function-calling format (`tools` parameter with `type: "function"`)
- Token usage: returned in final chunk when streaming, or in response body for non-streaming

---

### RT-2: Async Streaming Pattern Selection

**Question**: How should the LLM client yield streaming responses?

**Decision**: Use async generators (`AsyncIterator[StreamEvent]`) as the communication protocol, following Claude Agent SDK patterns.

**Rationale**: From `docs/vision.md` Layer 1 — "Async generators as the communication protocol. No callbacks, no event buses." The loop yields progress events; the caller applies backpressure by consuming at its own rate; cancellation propagates naturally when the consumer stops. This maps directly to Python's `async for chunk in client.stream(...)` pattern.

**Reference**: Claude Agent SDK (`anthropics/claude-agent-sdk-python`) — async generator tool loop, context management.

**Alternatives considered**:
- Callback-based: rejected per vision.md — "No callbacks, no event buses"
- Queue-based (asyncio.Queue): viable but async generators are simpler and cancellation is automatic
- Observable/RxPY: rejected — over-engineered for this use case

**Implementation pattern**:
```python
async def stream_chat(self, messages: list[ChatMessage], **kwargs) -> AsyncIterator[StreamEvent]:
    async with self._client.stream("POST", "/chat/completions", json=payload) as response:
        async for line in response.aiter_lines():
            if line.startswith("data: ") and line != "data: [DONE]":
                chunk = json.loads(line[6:])
                yield StreamEvent.from_chunk(chunk)
```

---

### RT-3: Retry Strategy for Transient Failures

**Question**: What retry strategy should be used for transient API failures?

**Decision**: Exponential backoff with full jitter, base 1s, multiplier 2x, cap 60s, max 3 retries. Only retry 429 and 503.

**Rationale**: From `docs/vision.md` Layer 6 — "429 Rate limited → exponential backoff (base 1s, cap 60s)". From spec FR-005: "exponential backoff (base 1s, multiplier 2x, jitter, cap 60s, max 3 retries)". Full jitter (random between 0 and calculated delay) prevents thundering herd across concurrent sessions.

**Reference**: OpenAI Agents SDK (`openai/openai-agents-python`) — retry matrix with composable policies. AWS architecture blog exponential backoff pattern.

**Alternatives considered**:
- Fixed delay: rejected — causes thundering herd
- Decorrelated jitter: viable but full jitter is simpler and sufficient for our scale
- tenacity library: rejected — adds dependency for ~30 lines of retry logic
- httpx built-in retry: httpx does not have built-in retry; transport-level retry via httpx.AsyncHTTPTransport has limited control

**Implementation**:
```python
# Full jitter: random between 0 and exponential ceiling
exp_delay = min(max_delay, base_delay * (multiplier ** attempt))
delay = random.uniform(0, exp_delay)
```

---

### RT-4: Token Usage Tracking Architecture

**Question**: How should token usage be tracked across a session?

**Decision**: In-memory `UsageTracker` with per-call debit and session budget enforcement. Pre-flight check verifies remaining budget can cover `max_tokens` (or 1 token minimum) before each call.

**Rationale**: From `docs/vision.md` Layer 1 — "Every LLM call and every public API call is debited against a session budget." The tracker maintains cumulative input/output token counts and compares against a configurable budget. Pre-flight check uses `can_afford(max_tokens or 1)` to reject calls when budget is exhausted. Input-token estimation via message size heuristics (1 token ≈ 4 chars for English, ≈ 2 chars for Korean) is deferred to Phase 2 pending EXAONE tokenizer validation.

**Reference**: Claude Agent SDK — usage tracking and cost accounting.

**Alternatives considered**:
- Post-flight only: rejected — a single large call could blow the entire budget before we know the cost
- Persistent tracker (DB/file): rejected for Phase 1 — in-memory is sufficient for single-session CLI
- Token counting library (tiktoken): rejected — EXAONE tokenizer is not publicly available; heuristic is sufficient for budget guardrails

---

### RT-5: httpx SSE Parsing Strategy

**Question**: How to parse Server-Sent Events from httpx streaming response?

**Decision**: Manual SSE line parsing from `response.aiter_lines()`. Parse `data:` prefix, skip empty lines and `[DONE]` sentinel.

**Rationale**: httpx does not have built-in SSE support. The SSE format is simple enough (each event is `data: {json}\n\n` with `data: [DONE]` terminator) that manual parsing is reliable and avoids adding an SSE library dependency.

**Alternatives considered**:
- httpx-sse library: viable but adds a dependency for trivial parsing logic
- aiohttp with SSE: rejected — we standardize on httpx per AGENTS.md
- Custom SSE transport: over-engineered for a single endpoint

---

### RT-6: Configuration Management

**Question**: How should the LLM client be configured?

**Decision**: Environment variables with Pydantic Settings model. All env vars use `KOSMOS_` prefix per AGENTS.md.

**Rationale**: Constitution requires `KOSMOS_` prefix for all env vars. Pydantic Settings (`pydantic-settings`) integrates naturally with Pydantic v2 validation and provides type-safe configuration with clear error messages for missing required fields.

**Key env vars**:
- `KOSMOS_FRIENDLI_TOKEN` (required): API authentication token
- `KOSMOS_FRIENDLI_BASE_URL` (optional, default: `https://api.friendli.ai/v1`): API base URL
- `KOSMOS_FRIENDLI_MODEL` (optional, default: `dep89a2fde0e09`): Model identifier
- `KOSMOS_LLM_SESSION_BUDGET` (optional, default: `100000`): Max tokens per session

**Alternatives considered**:
- YAML/JSON config file: rejected for Phase 1 — env vars are simpler and more secure
- python-dotenv: rejected — pydantic-settings handles .env files natively if needed
- dataclasses: rejected — Pydantic v2 provides validation that dataclasses lack

**Note**: `pydantic-settings` is a separate package from `pydantic`. It must be added to `pyproject.toml` dependencies.
