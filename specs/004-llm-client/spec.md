# Feature Specification: LLM Client Integration (FriendliAI EXAONE)

**Epic**: #4
**Created**: 2026-04-12
**Status**: Draft
**Layer**: Cross-cutting (LLM infrastructure)
**Input**: Async LLM client for FriendliAI Serverless endpoint serving EXAONE model, with streaming, token tracking, budget enforcement, and retry logic.

## User Scenarios & Testing

### User Story 1 - Single-turn Query Resolution (Priority: P1)

A citizen asks a natural-language question through the CLI. The system sends the query to EXAONE via FriendliAI Serverless and streams the response back in real time, so the citizen sees progressive output rather than waiting for the entire response.

**Why this priority**: This is the fundamental interaction loop. Without a working LLM client, no other layer functions.

**Independent Test**: Can be fully tested by sending a prompt string and verifying that a streamed response is received with correct content and token usage metadata.

**Acceptance Scenarios**:

1. **Given** a valid KOSMOS_FRIENDLI_TOKEN is configured, **When** the system sends a prompt to EXAONE, **Then** a streamed response is received with content and token usage counts (input tokens, output tokens).
2. **Given** a valid configuration, **When** a prompt is sent, **Then** the response streams incrementally (chunk by chunk) rather than arriving as a single block.

---

### User Story 2 - Session Budget Enforcement (Priority: P2)

During a conversation session, each LLM call is debited against a session token budget. When the budget is exhausted, the system stops making LLM calls and informs the citizen that the session limit has been reached.

**Why this priority**: Cost control is essential for a taxpayer-funded service. Without budget enforcement, a single session could consume disproportionate resources.

**Independent Test**: Can be tested by configuring a low token budget, making calls until the budget is exhausted, and verifying the system refuses further calls with an appropriate message.

**Acceptance Scenarios**:

1. **Given** a session budget of 1000 tokens, **When** cumulative usage reaches 1000 tokens, **Then** the next LLM call is rejected with a budget-exceeded error.
2. **Given** a session budget, **When** each LLM call completes, **Then** the usage tracker reflects the updated remaining budget.

---

### User Story 3 - Transient Failure Recovery (Priority: P2)

When the FriendliAI endpoint returns a transient error (429 rate limit or 503 service unavailable), the client automatically retries with exponential backoff. Permanent errors (401 unauthorized, 400 bad request) are not retried.

**Why this priority**: Public API reliability is critical for citizen trust. Transient failures should be invisible to the citizen.

**Independent Test**: Can be tested by simulating 429/503 responses and verifying automatic retry with backoff, and simulating 401/400 responses and verifying immediate failure.

**Acceptance Scenarios**:

1. **Given** the endpoint returns 429, **When** the client retries, **Then** it uses exponential backoff (base 1s, cap 60s) and succeeds when the endpoint recovers.
2. **Given** the endpoint returns 503 three times then succeeds, **When** the client retries, **Then** it delivers the successful response to the caller.
3. **Given** the endpoint returns 401, **When** the client processes the error, **Then** it raises an authentication error immediately without retrying.

---

### User Story 4 - Tool Use Message Assembly (Priority: P3)

The LLM client supports assembling messages with tool definitions and tool results in the OpenAI-compatible format, enabling the query engine to run a tool loop where the model can request tool calls and receive results.

**Why this priority**: The tool loop is Layer 1's core mechanism, but initial client functionality (stories 1-3) can work without tool use.

**Independent Test**: Can be tested by sending a message sequence that includes tool definitions and verifying the model's response includes tool_calls in the expected format.

**Acceptance Scenarios**:

1. **Given** a message list with tool definitions, **When** sent to the model, **Then** the response may contain tool_calls with function name and arguments.
2. **Given** a prior tool_call response and a tool result message, **When** the continuation is sent, **Then** the model incorporates the tool result in its next response.

---

### Edge Cases

- What happens when KOSMOS_FRIENDLI_TOKEN is not set or empty? System raises a configuration error at startup.
- What happens when the endpoint is completely unreachable (network down)? Client raises a connection error after retry exhaustion.
- What happens when the response stream is interrupted mid-chunk? Client raises a stream error; the caller can retry the full call.
- What happens when the model returns an empty response? Client returns an empty content string with zero output tokens; caller decides how to handle.
- What happens when token counts in the response are missing? Client treats missing counts as zero and logs a warning.

## Requirements

### Functional Requirements

- **FR-001**: System MUST connect to FriendliAI Serverless endpoint using the OpenAI-compatible chat completions API.
- **FR-002**: System MUST support streaming responses via Server-Sent Events (SSE), yielding chunks as they arrive.
- **FR-003**: System MUST track token usage per call: input tokens, output tokens, and cache read/write tokens (if available).
- **FR-004**: System MUST enforce a configurable per-session token budget. Calls that would exceed the budget MUST be rejected before sending.
- **FR-005**: System MUST retry transient errors (HTTP 429, 503) with exponential backoff (base 1s, multiplier 2x, jitter, cap 60s, max 3 retries).
- **FR-006**: System MUST NOT retry permanent errors (HTTP 400, 401, 403, 404).
- **FR-007**: System MUST read the API endpoint URL and authentication token from environment variables (KOSMOS_FRIENDLI_TOKEN).
- **FR-008**: System MUST support sending tool definitions and receiving tool_calls in the OpenAI function-calling format.
- **FR-009**: System MUST support configurable model parameters: model name, temperature, max_tokens, top_p, stop sequences.
- **FR-010**: System MUST provide an async interface (async/await) for all LLM operations.
- **FR-011**: System MUST raise a clear configuration error if required environment variables are missing at initialization.
- **FR-012**: System MUST log all LLM calls with request metadata (model, token counts, latency, status) using stdlib logging.

### Key Entities

- **LLMClient**: The async client that manages connections to the FriendliAI endpoint.
- **ChatMessage**: A message in the conversation (system, user, assistant, tool roles).
- **ChatCompletionResponse**: The model's response including content, tool_calls, and usage statistics.
- **UsageTracker**: Tracks cumulative token usage against a session budget.
- **RetryPolicy**: Configuration for retry behavior (max retries, backoff parameters, retryable status codes).

## Success Criteria

### Measurable Outcomes

- **SC-001**: A single-turn query receives a complete streamed response within the model's generation time plus network overhead (no artificial delays from client-side processing).
- **SC-002**: Token usage tracking is accurate to within the precision reported by the FriendliAI API response.
- **SC-003**: Session budget enforcement prevents any call from exceeding the configured token limit.
- **SC-004**: Transient failures (429, 503) are recovered automatically in 95%+ of cases where the endpoint recovers within the retry window.
- **SC-005**: All unit tests pass using recorded fixtures without requiring live API access.

## Assumptions

- FriendliAI Serverless endpoint is OpenAI-compatible (chat/completions API with tool support).
- The EXAONE model supports function calling / tool use in the OpenAI format.
- The FriendliAI API returns token usage statistics (input_tokens, output_tokens) in each response.
- Network connectivity to FriendliAI Serverless is generally stable; transient errors are the exception, not the norm.
- Session budget is configured per-session at initialization; dynamic budget adjustment mid-session is out of scope for Phase 1.
- The client does not manage conversation history — that is the Query Engine's responsibility (Layer 1, Epic #5).
