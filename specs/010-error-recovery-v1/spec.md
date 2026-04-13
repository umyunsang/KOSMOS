# Feature Specification: Error Recovery v1 (Layer 6)

**Feature Branch**: `feat/010-error-recovery-v1`
**Created**: 2026-04-13
**Status**: Draft
**Input**: Epic #10 — Error Recovery v1 (Layer 6)

---

## Overview & Context

Layer 6, Error Recovery, owns the resilience strategy for all outbound
`data.go.kr` API calls. Korean government APIs fail in predictable ways —
rate limits, maintenance windows, expired auth tokens, timeouts, and gateway
errors that return XML with HTTP 200 even when JSON was requested. The engine
must route each failure class to a specific recovery strategy rather than
surfacing raw errors to the citizen.

Today the codebase has retry logic only at the LLM client level
(`src/kosmos/llm/retry.py`). Tool adapters have no retry, no circuit
breakers, and no error classification. The `ToolExecutor` captures errors as
`ToolResult(success=False)` but makes no attempt at recovery. The
`cache_ttl_seconds` field on `GovAPITool` exists but is unused.
`StreamInterruptedError` is terminal with no retry path.

V1 introduces a new `src/kosmos/recovery/` package that provides:

- A **retry matrix** for tool adapter calls (the `data.go.kr` counterpart of
  the existing LLM `RetryPolicy`)
- A **circuit breaker** per API endpoint
- A **data.go.kr error classifier** that parses both HTTP-level and
  application-level error codes (including XML-in-JSON gateway errors)
- A **foreground/background retry distinction** so background batch work
  fails fast instead of extending outages
- A **cached fallback** mechanism that uses the already-declared
  `cache_ttl_seconds` field
- **Structured error context** (retry count, elapsed time, error
  classification) attached to `ToolResult` on failure

### Integration surface

The recovery layer wraps the adapter execution step inside `ToolExecutor`.
Today, step 5 of the dispatch pipeline (`executor.py` line 122-133) calls
the adapter directly and catches bare `Exception`. V1 replaces that with a
call through `RecoveryExecutor.execute()`, which applies the retry matrix,
circuit breaker check, error classification, and cached fallback before
returning either a successful result or a classified `ToolResult` failure.

`ToolExecutor` remains the entry point; `RecoveryExecutor` is an internal
collaborator. The query loop (`query.py`) is unmodified — it continues to
receive `ToolResult` objects from the executor. The only visible change from
the engine's perspective is that failed `ToolResult` objects now carry richer
error information via extended `error_type` values and an optional
`error_context` field.

The existing `RetryPolicy` in `src/kosmos/llm/retry.py` is NOT reused. It is
tightly coupled to LLM-specific exception types (`AuthenticationError`,
`LLMConnectionError`). The recovery layer defines its own
`ToolRetryPolicy` with `data.go.kr`-specific classification.

---

## User Stories

### User Story 1 — Tool Adapter Retry Matrix (Priority: P1)

A citizen queries a government API that returns HTTP 429 (rate limited) or
times out. The system must automatically retry the call with exponential
backoff and jitter rather than immediately reporting failure, so that
transient errors are invisible to the citizen.

**Why P1**: Without retry at the tool adapter level, every transient
`data.go.kr` error surfaces to the citizen as a hard failure, even though
the error is recoverable within seconds.

**Independent Test**: Unit test configures a `ToolRetryPolicy` with
`max_retries=3`, mocks an adapter that fails twice with HTTP 429 then
succeeds on the third call, and asserts the successful result is returned
with `retry_context.attempt_count == 3`.

**Acceptance Scenarios**:

1. **Given** an adapter that returns HTTP 429, **When** the retry matrix processes the call, **Then** it retries up to `max_retries` times with exponential backoff (base 1s, multiplier 2, cap 60s) plus full jitter.
2. **Given** an adapter that raises `httpx.ConnectTimeout`, **When** the retry matrix processes the call, **Then** it retries up to `max_retries` times. On exhaustion, a `ToolResult(success=False, error_type="timeout")` is returned.
3. **Given** an adapter that returns HTTP 400 (bad request), **When** the retry matrix processes the call, **Then** it does NOT retry and immediately returns a failure `ToolResult`.
4. **Given** a `ToolRetryPolicy` with `max_retries=0`, **When** any error occurs, **Then** no retry is attempted and the original error is returned.
5. **Given** a foreground call (`RetryContext.is_foreground=True`) and `max_retries=3`, **When** the adapter fails on all attempts, **Then** all 3 retries are attempted before failure.
6. **Given** a background call (`RetryContext.is_foreground=False`) and `max_retries=3`, **When** the adapter fails on the first attempt with a retryable error, **Then** at most 1 retry is attempted (background calls use `min(1, max_retries)` to fail fast).

---

### User Story 2 — Circuit Breaker per API Endpoint (Priority: P1)

When a government API is consistently failing (e.g., under maintenance), the
system must stop sending requests to that endpoint after a threshold of
consecutive failures, preventing wasted retries and allowing the API to
recover.

**Why P1**: Without a circuit breaker, the system hammers a failing API on
every citizen query, wasting time and rate limit quota while the citizen
waits.

**Independent Test**: Unit test creates a `CircuitBreaker` with
`failure_threshold=5` and `recovery_timeout=30.0`, triggers 5 consecutive
failures, asserts the breaker transitions to OPEN state, then advances time
by 30 seconds and asserts it transitions to HALF_OPEN.

**Acceptance Scenarios**:

1. **Given** a `CircuitBreaker` in CLOSED state, **When** 5 consecutive failures occur (matching `failure_threshold`), **Then** the breaker transitions to OPEN and subsequent calls are rejected immediately with `ToolResult(success=False, error_type="circuit_open")`.
2. **Given** a `CircuitBreaker` in OPEN state, **When** `recovery_timeout` seconds elapse, **Then** the breaker transitions to HALF_OPEN and allows one probe call.
3. **Given** a `CircuitBreaker` in HALF_OPEN state, **When** the probe call succeeds, **Then** the breaker transitions to CLOSED and resets the failure counter.
4. **Given** a `CircuitBreaker` in HALF_OPEN state, **When** the probe call fails, **Then** the breaker transitions back to OPEN and resets the recovery timer.
5. **Given** a `CircuitBreaker` in CLOSED state, **When** a success occurs after 3 consecutive failures, **Then** the failure counter resets to 0.
6. **Given** a `CircuitBreaker` in OPEN state and a cached result available, **When** a call arrives, **Then** the cached result is returned instead of rejecting the call (see User Story 5).

---

### User Story 3 — data.go.kr Error Code Classification (Priority: P1)

Government APIs return application-level error codes inside a JSON/XML
response body even when the HTTP status is 200. The system must parse these
error codes and classify them into retryable vs. non-retryable categories so
that the retry matrix and circuit breaker make correct decisions.

**Why P1**: Without error classification, an HTTP 200 response containing
`resultCode=22` (rate limit) would be treated as a successful call, and an
HTTP 200 containing `resultCode=12` (service deprecated) would be retried
forever. Both are incorrect.

**Independent Test**: Unit test passes a raw response body containing
`<OpenAPI_ServiceResponse><returnAuthMsg>...</returnAuthMsg><returnReasonCode>22</returnReasonCode></OpenAPI_ServiceResponse>`
to `DataGoKrErrorClassifier.classify()` and asserts it returns
`ErrorClass.RATE_LIMIT` with `is_retryable=True`.

**Acceptance Scenarios**:

1. **Given** a response body with `resultCode="00"`, **When** the classifier processes it, **Then** it returns `ErrorClass.SUCCESS`.
2. **Given** a response body with `resultCode="22"` (RATE_LIMIT), **When** the classifier processes it, **Then** it returns `ErrorClass.RATE_LIMIT` with `is_retryable=True`.
3. **Given** a response body with `resultCode="4"` (HTTP_ERROR), **When** the classifier processes it, **Then** it returns `ErrorClass.TRANSIENT` with `is_retryable=True`.
4. **Given** a response body with `resultCode="12"` (NO_SERVICE), **When** the classifier processes it, **Then** it returns `ErrorClass.SERVICE_DEPRECATED` with `is_retryable=False`.
5. **Given** a response body with `resultCode="20"` (ACCESS_DENIED), **When** the classifier processes it, **Then** it returns `ErrorClass.AUTH_FAILURE` with `is_retryable=False`.
6. **Given** a response body with `resultCode="30"` (KEY_NOT_REGISTERED) or `"32"` (UNREGISTERED_IP), **When** the classifier processes it, **Then** it returns `ErrorClass.AUTH_FAILURE` with `is_retryable=False`.
7. **Given** a response body with `resultCode="31"` (DEADLINE_EXPIRED), **When** the classifier processes it, **Then** it returns `ErrorClass.AUTH_EXPIRED` with `is_retryable=False` (token refresh is a separate path, not a blind retry).
8. **Given** a response body that starts with `<OpenAPI_ServiceResponse>` (XML gateway error delivered with HTTP 200 and `Content-Type: application/json`), **When** the classifier processes it, **Then** it detects the XML prefix, parses `returnReasonCode`, and classifies accordingly.
9. **Given** a response body with an unknown `resultCode="99"`, **When** the classifier processes it, **Then** it returns `ErrorClass.UNKNOWN` with `is_retryable=False` (fail-closed: unknown errors are not retried).

---

### User Story 4 — Foreground vs Background Retry Distinction (Priority: P2)

A citizen actively waiting for a response (foreground query) should see
aggressive retry with up to the full retry budget. A background task
(statistics refresh, auto-memory cleanup) should fail fast to avoid
prolonging an API outage.

**Why P2**: The foreground/background distinction is an optimization. V1
works without it (all calls are foreground by default), but it prevents
background work from blocking shutdown or extending outages.

**Independent Test**: Unit test calls `RecoveryExecutor.execute()` with
`is_foreground=False`, mocks an adapter that always returns HTTP 503,
and asserts that at most 1 retry is attempted.

**Acceptance Scenarios**:

1. **Given** a foreground call with `max_retries=3`, **When** the adapter fails on all attempts, **Then** exactly 3 retries occur (4 total attempts).
2. **Given** a background call with `max_retries=3`, **When** the adapter fails on all attempts, **Then** at most 1 retry occurs (2 total attempts).
3. **Given** a background call where the circuit breaker is OPEN, **When** a cached fallback exists, **Then** the cached result is returned immediately without any retry attempt.
4. **Given** a call where `is_foreground` is not specified, **When** `RecoveryExecutor.execute()` is called, **Then** it defaults to foreground (`is_foreground=True`).

---

### User Story 5 — Cached Fallback on Failure (Priority: P2)

When a tool adapter call fails and the circuit breaker is open (or retries
are exhausted), the system should return a previously cached successful
result if the tool's `cache_ttl_seconds` field indicates the data is still
valid. This activates the currently unused `cache_ttl_seconds` field on
`GovAPITool`.

**Why P2**: Returning stale-but-valid data is better than returning an error
for read-only government data that changes infrequently (e.g., accident
hotspot zones with `cache_ttl_seconds=3600`).

**Independent Test**: Unit test populates the `ResponseCache` with a result
for tool `koroad_accident_search` (which has `cache_ttl_seconds=3600`), then
calls `RecoveryExecutor.execute()` with a mock adapter that always fails,
and asserts the cached result is returned with a `is_cached_fallback=True`
flag.

**Acceptance Scenarios**:

1. **Given** a tool with `cache_ttl_seconds=3600` and a cached result from 30 minutes ago, **When** the adapter fails and retries are exhausted, **Then** the cached result is returned with `is_cached_fallback=True` in the `ToolResult`.
2. **Given** a tool with `cache_ttl_seconds=3600` and a cached result from 2 hours ago (expired), **When** the adapter fails, **Then** the cached result is NOT returned; a failure `ToolResult` is returned instead.
3. **Given** a tool with `cache_ttl_seconds=0` (no caching), **When** the adapter fails, **Then** no cache lookup is attempted and a failure `ToolResult` is returned.
4. **Given** a successful adapter call for a tool with `cache_ttl_seconds > 0`, **When** the call succeeds, **Then** the result is stored in the `ResponseCache` for future fallback use.
5. **Given** a cached result returned as fallback, **When** the `ToolResult` is yielded to the query loop, **Then** the `error_context.is_cached_fallback` field is `True` and the result `data` field contains the cached payload.

---

### User Story 6 — Graceful Degradation Messages (Priority: P2)

When all recovery strategies are exhausted (retries failed, circuit breaker
open, no cached fallback), the system must produce a citizen-friendly error
message that includes actionable guidance (e.g., in-person service
directions) rather than a raw exception trace.

**Why P2**: The vision document specifies "graceful message + in-person
service guidance" as the terminal failure path. Without this, citizens see
opaque error strings from `httpx`.

**Independent Test**: Unit test calls `RecoveryExecutor.execute()` with an
always-failing adapter, no cached fallback, circuit breaker open, and
asserts the returned `ToolResult.error` contains a structured Korean-language
message with the tool's `name_ko` and a guidance hint.

**Acceptance Scenarios**:

1. **Given** a total failure with no cached fallback, **When** the `ToolResult` is constructed, **Then** the `error` field contains a message that includes the tool's `name_ko` and a guidance string mentioning alternative contact channels.
2. **Given** a circuit breaker in OPEN state for a tool, **When** the error message is constructed, **Then** it mentions that the service is currently under maintenance or experiencing issues and suggests trying again later.
3. **Given** a `resultCode="12"` (NO_SERVICE / deprecated API), **When** the error message is constructed, **Then** it explicitly states that the service endpoint has been retired.

---

### User Story 7 — Streaming Retry on Interruption (Priority: P3)

When an LLM streaming response is interrupted mid-delivery
(`StreamInterruptedError`), the system should attempt one transparent
retry of the LLM call instead of immediately terminating the query.

**Why P3**: Today `StreamInterruptedError` is terminal. A single retry
covers transient network blips during long streaming responses. This is
lower priority because it affects the LLM path (already partially covered
by `retry_with_backoff`), not the `data.go.kr` path.

**Independent Test**: Unit test mocks `LLMClient.stream()` to raise
`StreamInterruptedError` on the first call and succeed on the second,
then asserts that `query()` completes normally with a `stop` event.

**Acceptance Scenarios**:

1. **Given** a streaming response that raises `StreamInterruptedError`, **When** the query loop catches the error, **Then** it retries the LLM call once from the same snapshot.
2. **Given** a streaming response that raises `StreamInterruptedError` on both the original and the retry, **When** the retry also fails, **Then** the query loop yields `StopReason.error_unrecoverable`.
3. **Given** a streaming response that raises `StreamInterruptedError` after partial content has been yielded, **When** the retry succeeds, **Then** the partial content from the failed attempt is discarded and the retry starts fresh.

---

## Functional Requirements

- **FR-001**: `ToolRetryPolicy` MUST be a frozen Pydantic v2 model with fields: `max_retries` (default 3, >=0), `base_delay` (default 1.0, >0), `multiplier` (default 2.0, >=1.0), `max_delay` (default 60.0, >0), `retryable_error_classes` (default: `{RATE_LIMIT, TRANSIENT, TIMEOUT}`).
- **FR-002**: `retry_tool_call()` MUST implement exponential backoff with full jitter: `delay = random.uniform(0, min(max_delay, base_delay * multiplier^attempt))`. This matches the formula already used in `src/kosmos/llm/retry.py`.
- **FR-003**: `retry_tool_call()` MUST respect the foreground/background distinction by capping effective `max_retries` to `min(1, policy.max_retries)` for background calls.
- **FR-004**: `CircuitBreaker` MUST implement the standard three-state machine (CLOSED, OPEN, HALF_OPEN) with configurable `failure_threshold` (default 5) and `recovery_timeout` (default 30.0 seconds).
- **FR-005**: `CircuitBreaker` MUST track per-tool-id state. Each tool ID gets its own breaker instance, created lazily.
- **FR-006**: `DataGoKrErrorClassifier` MUST handle all known `data.go.kr` error codes: 1 (APP_ERROR), 4 (HTTP_ERROR, retryable), 12 (NO_SERVICE), 20 (ACCESS_DENIED), 22 (RATE_LIMIT, retryable), 30 (KEY_NOT_REGISTERED), 31 (DEADLINE_EXPIRED), 32 (UNREGISTERED_IP), 99 (UNKNOWN).
- **FR-007**: `DataGoKrErrorClassifier` MUST detect XML gateway responses by checking for the `<OpenAPI_ServiceResponse>` prefix in the response body text, parse `returnReasonCode` from the XML, and classify accordingly.
- **FR-008**: `ResponseCache` MUST be an in-memory LRU cache keyed by `(tool_id, arguments_hash)` with TTL enforcement using the tool's `cache_ttl_seconds`.
- **FR-009**: `ResponseCache` MUST NOT cache results for tools with `cache_ttl_seconds=0`.
- **FR-010**: `RecoveryExecutor` MUST orchestrate: circuit breaker check, retry loop, error classification, cache lookup on failure, and graceful degradation message construction.
- **FR-011**: `RecoveryExecutor.execute()` MUST return `ToolResult` (never raise). All error paths produce a classified `ToolResult(success=False)` with an appropriate `error_type`.
- **FR-012**: The `ToolResult.error_type` literal MUST be extended with new values: `"timeout"`, `"circuit_open"`, `"api_error"`, `"auth_expired"`. These are added alongside the existing 6 values.
- **FR-013**: A new `ErrorContext` frozen Pydantic model MUST carry structured metadata: `attempt_count`, `elapsed_seconds`, `error_class`, `is_cached_fallback`, `circuit_state`. This model is NOT embedded in `ToolResult` (which is frozen and cannot be extended without a breaking change). Instead, `RecoveryExecutor.execute()` returns a `RecoveryResult` wrapper that pairs a `ToolResult` with an optional `ErrorContext`.
- **FR-014**: `RecoveryExecutor` MUST log at `WARNING` level for each retry attempt and at `ERROR` level when all recovery paths are exhausted.
- **FR-015**: `RecoveryExecutor` integration into `ToolExecutor` MUST be additive: `ToolExecutor` gains an optional `recovery_executor: RecoveryExecutor | None` constructor parameter. When present, step 5 of the dispatch pipeline delegates to `RecoveryExecutor.execute()` instead of calling the adapter directly. When absent, behavior is unchanged (backward-compatible).
- **FR-016**: Streaming retry MUST be handled in `query.py` by catching `StreamInterruptedError` inside the existing `try/except` block around the LLM stream, retrying once, and falling through to `error_unrecoverable` if the retry also fails.
- **FR-017**: `DataGoKrErrorClassifier` MUST also classify HTTP-level errors: 429 as `RATE_LIMIT`, 401/403 as `AUTH_FAILURE`, 503/502/504 as `TRANSIENT`, timeout exceptions as `TIMEOUT`.
- **FR-018**: Graceful degradation messages MUST be in Korean (domain data exception to the English source text rule) and include the tool's `name_ko`.

---

## Pydantic v2 Models

### `ErrorClass`

```
ErrorClass (StrEnum):
    SUCCESS               = "success"
    RATE_LIMIT            = "rate_limit"       # retryable
    TRANSIENT             = "transient"        # retryable (HTTP 502/503/504, code 4)
    TIMEOUT               = "timeout"          # retryable
    AUTH_FAILURE           = "auth_failure"     # not retryable (code 20, 30, 32)
    AUTH_EXPIRED           = "auth_expired"     # not retryable (code 31; future: token refresh)
    SERVICE_DEPRECATED     = "service_deprecated"  # not retryable (code 12)
    APP_ERROR              = "app_error"        # not retryable (code 1)
    UNKNOWN                = "unknown"          # not retryable (fail-closed)
```

### `DataGoKrErrorCode`

```
DataGoKrErrorCode (IntEnum):
    APP_ERROR           = 1
    HTTP_ERROR          = 4
    NO_SERVICE          = 12
    ACCESS_DENIED       = 20
    RATE_LIMIT          = 22
    KEY_NOT_REGISTERED  = 30
    DEADLINE_EXPIRED    = 31
    UNREGISTERED_IP     = 32
    UNKNOWN             = 99
```

### `ClassifiedError`

```
ClassifiedError (frozen):
    error_class: ErrorClass
    is_retryable: bool
    raw_code: int | None          # data.go.kr returnReasonCode if available
    raw_message: str              # original error message
    source: Literal["http", "application", "transport"]
```

### `ToolRetryPolicy`

```
ToolRetryPolicy (frozen):
    max_retries: int              # default 3, >= 0
    base_delay: float             # default 1.0, > 0
    multiplier: float             # default 2.0, >= 1.0
    max_delay: float              # default 60.0, > 0
    retryable_classes: frozenset[ErrorClass]
        # default {RATE_LIMIT, TRANSIENT, TIMEOUT}
```

### `CircuitBreakerConfig`

```
CircuitBreakerConfig (frozen):
    failure_threshold: int        # default 5, >= 1
    recovery_timeout: float       # default 30.0, > 0
    half_open_max_calls: int      # default 1, >= 1
```

### `CircuitState`

```
CircuitState (StrEnum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"
```

### `ErrorContext`

```
ErrorContext (frozen):
    attempt_count: int            # total attempts made (1 = no retry)
    elapsed_seconds: float        # wall-clock time from first attempt to final result
    error_class: ErrorClass       # classified error
    is_cached_fallback: bool      # True if result came from cache
    circuit_state: CircuitState   # breaker state at time of return
    tool_id: str                  # which tool this context belongs to
```

### `RecoveryResult`

```
RecoveryResult (frozen):
    tool_result: ToolResult       # the standard result object for the query loop
    error_context: ErrorContext | None  # structured metadata; None on first-attempt success
```

### `CacheEntry`

```
CacheEntry (frozen):
    tool_id: str
    arguments_hash: str           # SHA-256 of canonical JSON arguments
    data: dict[str, object]       # cached successful response payload
    cached_at: float              # time.monotonic() timestamp
    ttl_seconds: int              # from GovAPITool.cache_ttl_seconds
```

---

## Module Layout

```
src/kosmos/recovery/
    __init__.py
    classifier.py       # DataGoKrErrorClassifier, ErrorClass, ClassifiedError, DataGoKrErrorCode
    retry.py            # ToolRetryPolicy, retry_tool_call()
    circuit_breaker.py  # CircuitBreaker, CircuitBreakerConfig, CircuitState, CircuitBreakerRegistry
    cache.py            # ResponseCache, CacheEntry
    executor.py         # RecoveryExecutor, RecoveryResult, ErrorContext
    messages.py         # Graceful degradation message templates (Korean)
```

---

## Non-Functional Requirements

- **NFR-001**: `retry_tool_call()` MUST NOT add latency on the happy path (first-attempt success): the only overhead is the circuit breaker state check, which MUST be O(1).
- **NFR-002**: `CircuitBreaker` state transitions MUST be thread-safe within a single event loop (no locking required for asyncio, but state mutations must be atomic with respect to concurrent coroutines).
- **NFR-003**: `ResponseCache` MUST use bounded memory: LRU eviction with a configurable `max_entries` (default 256).
- **NFR-004**: All logging MUST use `logging.getLogger(__name__)` at appropriate levels; no `print()` statements.
- **NFR-005**: The module MUST be located at `src/kosmos/recovery/` (new sub-package).
- **NFR-006**: `DataGoKrErrorClassifier` MUST NOT import `xml.etree.ElementTree` for parsing the XML gateway error. Use simple string operations (`str.find`, `str[start:end]`) to extract `returnReasonCode` from the XML prefix. This avoids XML parser overhead and XXE attack surface for what is a fixed-format 3-line error response.
- **NFR-007**: All tests MUST be CI-safe: no live `data.go.kr` API calls. Use recorded fixtures and mock adapters.

---

## Success Criteria

- **SC-001**: An adapter that returns HTTP 429 twice then succeeds produces a successful `ToolResult` with `error_context.attempt_count == 3`.
- **SC-002**: After `failure_threshold` consecutive failures, the circuit breaker rejects the next call in under 1 ms (no network I/O).
- **SC-003**: A response body starting with `<OpenAPI_ServiceResponse>` containing `returnReasonCode=22` is correctly classified as `ErrorClass.RATE_LIMIT`.
- **SC-004**: A background call (`is_foreground=False`) with `max_retries=3` attempts at most 2 calls total.
- **SC-005**: A tool with `cache_ttl_seconds=3600` and a 30-minute-old cached result returns the cached result when the live adapter fails.
- **SC-006**: The graceful degradation message for `koroad_accident_search` failure contains the string `"교통사고 위험지역 조회"` (the tool's `name_ko`).
- **SC-007**: `StreamInterruptedError` on the first LLM stream attempt results in one retry; success on the retry produces a normal `stop` event.
- **SC-008**: All unit tests pass with no live API calls (CI safe).

---

## Edge Cases

- **XML body with HTTP 200 and `Content-Type: application/json`**: The classifier MUST detect the `<OpenAPI_ServiceResponse>` prefix in the raw response text before attempting JSON parsing. Adapters that call `response.json()` will raise `json.JSONDecodeError` — the classifier handles this by falling back to raw text inspection.
- **Empty response body**: Classified as `ErrorClass.UNKNOWN`, not retried.
- **`resultCode` present but not in known map**: Classified as `ErrorClass.UNKNOWN` with `is_retryable=False` (fail-closed).
- **Circuit breaker for a tool that has never been called**: Lazily created in CLOSED state on first call. No pre-registration required.
- **Concurrent calls to the same tool while circuit breaker is HALF_OPEN**: Only one probe call is allowed; additional concurrent calls are rejected with `circuit_open`.
- **Cache entry with `cache_ttl_seconds` changed on tool re-registration**: The cache entry uses the TTL recorded at write time, not the current tool definition. This is correct because the cached data was valid under the old TTL.
- **Adapter returns `httpx.HTTPStatusError` with no response body**: Classified by HTTP status code alone (FR-017).
- **Adapter raises non-httpx exception (e.g., `ValueError` during response parsing)**: Classified as `ErrorClass.APP_ERROR`, not retried.

---

## Out of Scope (V1)

The following are explicitly deferred to v2 or later:

- **Cross-verification with a second ministry API**: The vision document mentions cross-verifying data inconsistencies with an alternative ministry API. This requires the Agent Swarm layer (Layer 4) to route to a different ministry worker and is deferred.
- **Full alternative API search**: The vision document mentions searching for alternative APIs when a service is under 503 maintenance. V1 does not implement alternative API discovery; it falls back to cached results or graceful degradation only.
- **Human-handoff trigger (refusal circuit breaker)**: The vision document describes routing to a human channel after consecutive refusals. This belongs to the Permission Pipeline (Layer 3) interaction and is deferred.
- **401 token refresh logic**: The classifier identifies `AUTH_EXPIRED` errors but V1 does not implement automatic token refresh. The error is surfaced to the engine as `StopReason.needs_authentication`.
- **Distributed circuit breaker state**: V1 uses in-memory per-process circuit breaker state. Distributed state (Redis-backed) is a production concern.
- **Persistent response cache**: V1 uses in-memory LRU cache. On-disk or Redis-backed persistence is deferred.
- **Per-adapter retry policy overrides**: V1 uses a single default `ToolRetryPolicy`. Per-tool policy customization (e.g., more aggressive retry for high-value tools) is deferred.
- **Metrics and observability**: OpenTelemetry counters for retry counts, circuit breaker state changes, and cache hit rates are deferred to the observability epic.

---

## Dependencies

| Dependency | Status | Notes |
|---|---|---|
| Epic #4 — LLM Client | Complete | `StreamInterruptedError`, `retry_with_backoff()` (reference only; not reused) |
| Epic #5 — Query Engine Core | Complete | `query()` loop, `StopReason`, `QueryEvent` |
| Epic #6 — Tool System | Complete | `ToolExecutor`, `ToolResult`, `GovAPITool.cache_ttl_seconds`, `error_type` literal |
| Epic #7 — API Adapters | Complete | Adapter `_call()` functions, `httpx` usage patterns |

### Integration contract with ToolExecutor

`ToolExecutor.__init__` currently accepts only a `ToolRegistry`. V1 adds an
optional `recovery_executor: RecoveryExecutor | None` parameter. When
present, step 5 of the dispatch pipeline changes from:

```python
# Current (no recovery)
result_dict = await adapter(validated_input)
```

to:

```python
# With recovery
recovery_result = await self._recovery_executor.execute(
    tool=tool,
    adapter=adapter,
    validated_input=validated_input,
    is_foreground=True,  # default; engine can override later
)
# recovery_result.tool_result replaces the manually-constructed ToolResult
```

When `recovery_executor` is `None`, the existing direct-call path is
preserved unchanged (backward-compatible).

### Integration contract with query.py

The `query()` function's `try/except` block around `ctx.llm_client.stream()`
(lines 236-277) gains a new `except StreamInterruptedError` clause before
the catch-all `except Exception`. On the first occurrence, the loop retries
the stream from the same snapshot. A second `StreamInterruptedError` falls
through to `error_unrecoverable`.

No other changes to `query.py` are required.

---

## Reference Mapping

Per constitution Section I, every design decision must trace to a source in
`docs/vision.md Section Reference materials`.

| Decision | Source |
|---|---|
| Exponential backoff with full jitter for tool retries | stamina (`hynek/stamina`) — enforced jitter as production best practice |
| Circuit breaker three-state machine | aiobreaker (`arlyon/aiobreaker`) — asyncio-native circuit breaker pattern |
| Error matrix: 429/503/401/timeout/hard-failure routing | `docs/vision.md Section Layer 6 — Error Recovery` error matrix |
| Foreground vs background retry distinction | `docs/vision.md Section Layer 6` — "aggressive retry" vs "fails fast" |
| Cached fallback using `cache_ttl_seconds` | `docs/vision.md Section Layer 2` — `cache_ttl_seconds` field on `GovAPITool` |
| Graceful message + in-person service guidance | `docs/vision.md Section Layer 6` — hard failure terminal path |
| `ToolRetryPolicy` as frozen Pydantic v2 model | Constitution Section III; `RetryPolicy` in `src/kosmos/llm/retry.py` as structural precedent |
| `data.go.kr` error code classification | PublicDataReader (`WooilJeong/PublicDataReader`) — wire format ground truth |
| XML gateway error detection (`<OpenAPI_ServiceResponse>` prefix) | PublicDataReader — XML/JSON response normalization |
| Fail-closed for unknown error codes | Constitution Section II — fail-closed defaults |
| Streaming retry for `StreamInterruptedError` | OpenAI Agents SDK — retry matrix pattern; Claude Agent SDK — error handling |
| `RecoveryExecutor` never raises, returns `ToolResult` | Existing `ToolExecutor` convention — executor never raises |
| `src/kosmos/recovery/` new sub-package | Layer separation principle — `docs/vision.md` six-layer architecture |
