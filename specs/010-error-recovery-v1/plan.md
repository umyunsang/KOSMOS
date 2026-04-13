# Implementation Plan: Error Recovery v1 (Layer 6)

**Branch**: `feat/010-error-recovery-v1` | **Date**: 2026-04-13 | **Spec**: [spec.md](./spec.md)
**Input**: Epic #10 — Error Recovery v1 (Layer 6)

---

## Summary

Layer 6, Error Recovery, owns the resilience strategy for all outbound `data.go.kr` API calls. V1 introduces a new `src/kosmos/recovery/` package that provides: a `data.go.kr` error classifier (including XML gateway response detection), an exponential-backoff retry loop with foreground/background distinction, a per-endpoint circuit breaker, an in-memory LRU response cache for fallback, a `RecoveryExecutor` that orchestrates all four strategies, and Korean-language graceful degradation messages when all recovery paths are exhausted.

The core design invariant is **never raise, always return**: `RecoveryExecutor.execute()` absorbs all exceptions and returns a `RecoveryResult` containing either a successful `ToolResult` or a classified failure `ToolResult` with structured `ErrorContext`. The executor integrates additively into the existing `ToolExecutor` dispatch pipeline (step 5) via an optional constructor parameter, preserving full backward compatibility.

A secondary integration point is `query.py`, where `StreamInterruptedError` gains a single transparent retry before falling through to `error_unrecoverable`.

No external dependencies are added. The retry loop and circuit breaker are implemented internally (~200 lines each), following patterns from stamina and aiobreaker respectively but avoiding dependency bloat. This is consistent with the constitution's minimal-dependency principle.

---

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: `pydantic >= 2.0` (frozen models, validators), `httpx >= 0.27` (exception types for classification), `pytest` + `pytest-asyncio` (tests)
**New Dependencies**: None. Retry and circuit breaker are implemented internally.
**Storage**: N/A -- in-memory only. `ResponseCache` uses `collections.OrderedDict` for LRU. `CircuitBreaker` state is per-process in-memory.
**Testing**: `uv run pytest` -- unit tests per module, integration tests for full recovery flow. No live API calls (`@pytest.mark.live` absent). All adapters mocked.
**Target Platform**: Linux server (CI) + developer macOS
**Project Type**: Library module (`src/kosmos/recovery/`) consumed by `ToolExecutor`
**Performance Goals**: Circuit breaker state check must be O(1). Happy-path overhead (first-attempt success) must be limited to one circuit breaker lookup and one cache store operation.
**Scale/Scope**: Single-process scope. All state is in-memory, non-persistent, non-distributed.

---

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Notes |
|---|---|---|
| I -- Reference-Driven Development | PASS | All design decisions mapped to sources in `docs/vision.md Section Reference materials`. See Reference Source Mapping section below. |
| II -- Fail-Closed Security | PASS | Unknown error codes classified as `ErrorClass.UNKNOWN` with `is_retryable=False` (fail-closed). `cache_ttl_seconds=0` default means no caching by default. Circuit breaker rejects calls when open (fail-closed). |
| III -- Pydantic v2 Strict Typing | PASS | All recovery models (`ErrorClass`, `ClassifiedError`, `ToolRetryPolicy`, `CircuitBreakerConfig`, `ErrorContext`, `RecoveryResult`, `CacheEntry`) are frozen Pydantic v2 models. No `Any` in I/O schemas. |
| IV -- Government API Compliance | PASS | No live `data.go.kr` calls in recovery package or tests. All tests use mock adapters and recorded fixtures. |
| V -- Policy Alignment | PASS | Graceful degradation messages guide citizens to alternative contact channels (Principle 8: single conversational window). Error classification handles all known `data.go.kr` error codes. |
| Dev Standards | PASS | `stdlib logging` only, `uv + pyproject.toml`, English source text (Korean only in `messages.py` for citizen-facing degradation text). |

**Complexity Justification**: No constitution violations. The `src/kosmos/recovery/` sub-package is the sixth Python package under `src/kosmos/`, joining `engine/`, `llm/`, `tools/`, `context/`, and `permissions/`. This follows the layer separation principle from `docs/vision.md` -- Layer 6 gets its own package.

---

## Phase 0 -- Research

### Primary references consulted

| Decision Area | Source | Finding Applied |
|---|---|---|
| Retry with enforced jitter | stamina (`hynek/stamina`) | Exponential backoff formula: `delay = random.uniform(0, min(max_delay, base_delay * multiplier^attempt))`. Full jitter prevents thundering herd. Matches the existing `_compute_delay()` in `src/kosmos/llm/retry.py`. |
| Circuit breaker three-state machine | aiobreaker (`arlyon/aiobreaker`) | Standard CLOSED -> OPEN -> HALF_OPEN cycle. Failure threshold triggers OPEN; recovery timeout triggers HALF_OPEN; probe success triggers CLOSED. Per-endpoint isolation via registry keyed by tool ID. |
| Error matrix routing | `docs/vision.md Section Layer 6 -- Error Recovery` | 429/503 -> retry, 401/403 -> auth failure, timeout -> retry, hard failure -> graceful degradation. Maps directly to `ErrorClass` enum. |
| `data.go.kr` wire format errors | PublicDataReader (`WooilJeong/PublicDataReader`) | XML gateway responses with `<OpenAPI_ServiceResponse>` prefix. `returnReasonCode` values: 1 (APP_ERROR), 4 (HTTP_ERROR), 12 (NO_SERVICE), 20 (ACCESS_DENIED), 22 (RATE_LIMIT), 30 (KEY_NOT_REGISTERED), 31 (DEADLINE_EXPIRED), 32 (UNREGISTERED_IP). |
| Foreground vs background retry | `docs/vision.md Section Layer 6` | Foreground (citizen-facing): full retry budget. Background (batch work): capped at `min(1, max_retries)` to fail fast. |
| Cached fallback using `cache_ttl_seconds` | `docs/vision.md Section Layer 2` | `GovAPITool.cache_ttl_seconds` field exists but is unused. V1 activates it for fallback on failure. |
| Graceful degradation terminal path | `docs/vision.md Section Layer 6` | Hard failure produces Korean-language message with tool's `name_ko` and in-person service guidance. |
| Executor never raises convention | Existing `ToolExecutor` pattern (`src/kosmos/tools/executor.py`) | `RecoveryExecutor.execute()` follows the same convention: all error paths produce a classified `ToolResult(success=False)`. Never raises. |
| Retry matrix pattern for `StreamInterruptedError` | OpenAI Agents SDK (retry matrix); Claude Agent SDK (error handling) | Single transparent retry on stream interruption before falling to `error_unrecoverable`. |
| Frozen Pydantic v2 models | Constitution Section III; `RetryPolicy` in `src/kosmos/llm/retry.py` | All recovery models use `ConfigDict(frozen=True)`. `ToolRetryPolicy` mirrors the structural pattern of the existing LLM `RetryPolicy`. |
| Fail-closed for unknown errors | Constitution Section II | `ErrorClass.UNKNOWN` with `is_retryable=False`. Unknown `resultCode` values are never retried. |
| Layer separation | `docs/vision.md` six-layer architecture; `AGENTS.md` | New sub-package `src/kosmos/recovery/` keeps error recovery isolated from `tools/` and `engine/`. |

### Existing code to reuse or extend

| Module | What to reuse | How |
|---|---|---|
| `src/kosmos/llm/retry.py` | Backoff formula pattern (`_compute_delay`) | Reference only. `ToolRetryPolicy` implements its own `_compute_delay()` with the same formula. No code sharing -- the LLM retry is tightly coupled to `httpx.HTTPStatusError` and `AuthenticationError`. |
| `src/kosmos/tools/models.py` | `ToolResult` model, `error_type` literal | Extend `error_type` with four new values: `"timeout"`, `"circuit_open"`, `"api_error"`, `"auth_expired"`. |
| `src/kosmos/tools/models.py` | `GovAPITool.cache_ttl_seconds` field | Read by `ResponseCache` to determine TTL for each tool's cached results. |
| `src/kosmos/tools/models.py` | `GovAPITool.name_ko` field | Used by `messages.py` to construct Korean degradation messages. |
| `src/kosmos/tools/executor.py` | `ToolExecutor.__init__`, `dispatch()` step 5 | Additive change: optional `recovery_executor` parameter. Step 5 delegates to `RecoveryExecutor.execute()` when present. |
| `src/kosmos/engine/query.py` | `try/except` block around `ctx.llm_client.stream()` (lines 235-277) | Add `except StreamInterruptedError` clause before the catch-all `except Exception`. |
| `src/kosmos/llm/errors.py` | `StreamInterruptedError` class | Caught in `query.py` for streaming retry. |

### Technical unknowns resolved

1. **`ToolResult.error_type` extension**: The `error_type` field uses a `Literal` union. Adding new values (`"timeout"`, `"circuit_open"`, `"api_error"`, `"auth_expired"`) is backward-compatible -- existing consumers that match on the old values will simply not match the new ones (they already handle `None` on success). The model validator checks `error is not None and error_type is not None` on failure, which remains satisfied.

2. **`RecoveryResult` vs embedding in `ToolResult`**: `ToolResult` is frozen and its schema is part of the LLM response contract. Adding an `error_context` field would change the serialization visible to the query loop. Instead, `RecoveryExecutor.execute()` returns a `RecoveryResult` wrapper. The query loop continues to receive `ToolResult` via `recovery_result.tool_result`; the `ErrorContext` is available for logging and observability but not serialized to the LLM.

3. **Circuit breaker concurrency in asyncio**: Python asyncio is single-threaded within an event loop. State transitions (CLOSED -> OPEN, OPEN -> HALF_OPEN, HALF_OPEN -> CLOSED/OPEN) are atomic with respect to coroutines because no `await` occurs between the state read and the state write. No locking is required.

4. **`ResponseCache` LRU implementation**: `collections.OrderedDict` with `move_to_end()` on access and `popitem(last=False)` when size exceeds `max_entries`. This is the standard Python LRU pattern. No external dependency needed.

5. **XML parsing without `xml.etree`**: The `<OpenAPI_ServiceResponse>` error format is a fixed 3-line XML block. Simple `str.find()` + `str[start:end]` extracts `returnReasonCode`. This avoids XML parser overhead and XXE attack surface (NFR-006).

6. **Adapter signature for `RecoveryExecutor`**: The existing adapter signature is `Callable[[BaseModel], Awaitable[dict[str, Any]]]`. `RecoveryExecutor.execute()` wraps this callable, catching all exceptions and `httpx` response errors. The adapter itself is unmodified.

---

## Architecture

### Module structure: `src/kosmos/recovery/`

```
src/kosmos/recovery/
    __init__.py           # Public exports: RecoveryExecutor, RecoveryResult,
                          #   ErrorContext, ToolRetryPolicy, CircuitBreaker,
                          #   CircuitBreakerConfig, DataGoKrErrorClassifier,
                          #   ErrorClass, ResponseCache
    classifier.py         # DataGoKrErrorClassifier, ErrorClass, ClassifiedError,
                          #   DataGoKrErrorCode
    retry.py              # ToolRetryPolicy, retry_tool_call()
    circuit_breaker.py    # CircuitBreaker, CircuitBreakerConfig, CircuitState,
                          #   CircuitBreakerRegistry
    cache.py              # ResponseCache, CacheEntry
    executor.py           # RecoveryExecutor, RecoveryResult, ErrorContext
    messages.py           # Graceful degradation message templates (Korean)
```

### Dependency graph (build order)

```
classifier.py          (no internal deps)
       |
       v
  retry.py             (depends on: classifier)
       |
       v
circuit_breaker.py     (depends on: classifier)
       |
       v
  cache.py             (no internal deps; depends on: tools.models.GovAPITool)
       |
       v
 messages.py           (depends on: classifier)
       |
       v
 executor.py           (depends on: classifier, retry, circuit_breaker, cache, messages)
```

### Class responsibilities

**`DataGoKrErrorClassifier`** (stateless):
- `classify_response(status_code: int, body: str, content_type: str) -> ClassifiedError`: Classifies HTTP-level and application-level errors from `data.go.kr` responses.
- `classify_exception(exc: Exception) -> ClassifiedError`: Classifies transport-level exceptions (`httpx.ConnectTimeout`, `httpx.ReadTimeout`, etc.) and adapter-raised exceptions.
- Detects XML gateway responses by checking for `<OpenAPI_ServiceResponse>` prefix before JSON parsing.
- Maps all known `data.go.kr` error codes to `ErrorClass` enum values.

**`retry_tool_call()`** (stateless async function):
- Wraps an adapter call with exponential backoff + full jitter.
- Respects foreground/background distinction: caps effective `max_retries` to `min(1, policy.max_retries)` for background calls.
- Returns `(ToolResult, ClassifiedError | None, int)` tuple: the result, the last error classification (if any), and the attempt count.
- Logs at `WARNING` level for each retry attempt.

**`CircuitBreaker`** (stateful per-tool):
- Implements the standard three-state machine: CLOSED, OPEN, HALF_OPEN.
- `allow_request() -> bool`: Returns True if the call should proceed.
- `record_success()`: Resets failure counter, transitions HALF_OPEN -> CLOSED.
- `record_failure()`: Increments failure counter, transitions CLOSED -> OPEN or HALF_OPEN -> OPEN.
- State transitions are atomic within the event loop (no locks needed).

**`CircuitBreakerRegistry`** (stateful):
- Lazily creates and caches `CircuitBreaker` instances keyed by tool ID.
- `get(tool_id: str) -> CircuitBreaker`: Returns existing or creates new (CLOSED state).

**`ResponseCache`** (stateful):
- In-memory LRU cache using `collections.OrderedDict`.
- Keyed by `(tool_id, arguments_hash)` where `arguments_hash` is SHA-256 of canonical JSON arguments.
- `get(tool_id: str, arguments_hash: str, ttl_seconds: int) -> CacheEntry | None`: Returns valid entry or None.
- `put(entry: CacheEntry) -> None`: Stores entry, evicts oldest if over `max_entries`.
- Respects `cache_ttl_seconds=0` (no caching).

**`RecoveryExecutor`** (orchestrator):
- Constructor accepts `ToolRetryPolicy`, `CircuitBreakerConfig`, `ResponseCache`, `CircuitBreakerRegistry`.
- `execute(tool, adapter, validated_input, *, is_foreground=True) -> RecoveryResult`: Orchestrates the full recovery pipeline:
  1. Circuit breaker check: if OPEN, try cache fallback, else reject.
  2. Retry loop with error classification on each failure.
  3. On success: cache the result (if `cache_ttl_seconds > 0`), return.
  4. On exhaustion: try cache fallback, else construct graceful degradation message.
- Never raises. All paths produce a `RecoveryResult`.

**`messages.py`** (stateless):
- `build_degradation_message(tool: GovAPITool, error: ClassifiedError) -> str`: Produces a Korean-language error message using the tool's `name_ko` and actionable guidance.
- Templates are string constants with `str.format()` placeholders for `name_ko`.

### Integration with `ToolExecutor`

One additive change to `src/kosmos/tools/executor.py`:

- `ToolExecutor.__init__` gains an optional `recovery_executor: RecoveryExecutor | None = None` parameter. When present, step 5 of the dispatch pipeline delegates to `RecoveryExecutor.execute()` instead of directly calling the adapter. When absent, behavior is unchanged.

The change to step 5 is isolated to lines 122-133 of the current `executor.py`:

```python
# Current (no recovery):
try:
    result_dict = await adapter(validated_input)
except Exception as exc:
    ...

# With recovery:
if self._recovery_executor is not None:
    recovery_result = await self._recovery_executor.execute(
        tool=tool,
        adapter=adapter,
        validated_input=validated_input,
        is_foreground=True,
    )
    if not recovery_result.tool_result.success:
        return recovery_result.tool_result
    result_dict = recovery_result.tool_result.data
    # Fall through to step 6 (output validation)
else:
    # Original path unchanged
    try:
        result_dict = await adapter(validated_input)
    except Exception as exc:
        ...
```

### Integration with `query.py`

One additive change to the `try/except` block around `ctx.llm_client.stream()` (lines 235-277):

```python
# Add before the catch-all `except Exception`:
except StreamInterruptedError:
    if _stream_retry_count == 0:
        _stream_retry_count += 1
        logger.warning("Stream interrupted, retrying once")
        continue  # re-enter the while loop from the snapshot
    logger.error("Stream interrupted on retry; unrecoverable")
    yield QueryEvent(
        type="stop",
        stop_reason=StopReason.error_unrecoverable,
        stop_message="LLM stream interrupted after retry",
    )
    return
```

The `_stream_retry_count` variable is initialized to 0 before the while loop and reset to 0 at the start of each iteration (after successful streaming).

### `ToolResult.error_type` extension

The `error_type` literal in `src/kosmos/tools/models.py` gains four new values:

```python
error_type: (
    Literal[
        "validation",
        "rate_limit",
        "not_found",
        "execution",
        "schema_mismatch",
        "permission_denied",
        "timeout",         # new: adapter timed out after retries
        "circuit_open",    # new: circuit breaker rejected the call
        "api_error",       # new: data.go.kr application-level error
        "auth_expired",    # new: API key/token expired
    ]
    | None
) = None
```

---

## Data Model

### Frozen Pydantic v2 models (`recovery/classifier.py`)

```python
class ErrorClass(StrEnum):
    SUCCESS            = "success"
    RATE_LIMIT         = "rate_limit"
    TRANSIENT          = "transient"
    TIMEOUT            = "timeout"
    AUTH_FAILURE        = "auth_failure"
    AUTH_EXPIRED        = "auth_expired"
    SERVICE_DEPRECATED  = "service_deprecated"
    APP_ERROR           = "app_error"
    UNKNOWN             = "unknown"

class DataGoKrErrorCode(IntEnum):
    APP_ERROR          = 1
    HTTP_ERROR         = 4
    NO_SERVICE         = 12
    ACCESS_DENIED      = 20
    RATE_LIMIT         = 22
    KEY_NOT_REGISTERED = 30
    DEADLINE_EXPIRED   = 31
    UNREGISTERED_IP    = 32
    UNKNOWN            = 99

class ClassifiedError(BaseModel):
    model_config = ConfigDict(frozen=True)
    error_class: ErrorClass
    is_retryable: bool
    raw_code: int | None
    raw_message: str
    source: Literal["http", "application", "transport"]
```

### Frozen Pydantic v2 models (`recovery/retry.py`)

```python
class ToolRetryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True)
    max_retries: int = Field(default=3, ge=0)
    base_delay: float = Field(default=1.0, gt=0)
    multiplier: float = Field(default=2.0, ge=1.0)
    max_delay: float = Field(default=60.0, gt=0)
    retryable_classes: frozenset[ErrorClass] = Field(
        default_factory=lambda: frozenset({
            ErrorClass.RATE_LIMIT,
            ErrorClass.TRANSIENT,
            ErrorClass.TIMEOUT,
        })
    )
```

### Frozen Pydantic v2 models (`recovery/circuit_breaker.py`)

```python
class CircuitState(StrEnum):
    CLOSED    = "closed"
    OPEN      = "open"
    HALF_OPEN = "half_open"

class CircuitBreakerConfig(BaseModel):
    model_config = ConfigDict(frozen=True)
    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout: float = Field(default=30.0, gt=0)
    half_open_max_calls: int = Field(default=1, ge=1)
```

### Frozen Pydantic v2 models (`recovery/cache.py`)

```python
class CacheEntry(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_id: str
    arguments_hash: str
    data: dict[str, object]
    cached_at: float              # time.monotonic()
    ttl_seconds: int
```

### Frozen Pydantic v2 models (`recovery/executor.py`)

```python
class ErrorContext(BaseModel):
    model_config = ConfigDict(frozen=True)
    attempt_count: int
    elapsed_seconds: float
    error_class: ErrorClass
    is_cached_fallback: bool
    circuit_state: CircuitState
    tool_id: str

class RecoveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    tool_result: ToolResult
    error_context: ErrorContext | None  # None on first-attempt success
```

---

## File Structure

### Documentation

```
specs/010-error-recovery-v1/
    spec.md           # Approved specification (input)
    plan.md           # This file
    tasks.md          # Generated by /speckit-tasks (not yet created)
```

### Source code

```
src/kosmos/recovery/
    __init__.py
    classifier.py
    retry.py
    circuit_breaker.py
    cache.py
    executor.py
    messages.py

src/kosmos/tools/
    models.py         # Modified: error_type literal extended with 4 new values
    executor.py       # Modified: optional recovery_executor parameter

src/kosmos/engine/
    query.py          # Modified: StreamInterruptedError retry clause

tests/recovery/
    __init__.py
    test_classifier.py
    test_retry.py
    test_circuit_breaker.py
    test_cache.py
    test_executor.py
    test_messages.py
    test_integration.py
    test_streaming_retry.py
```

---

## Implementation Phases

### Phase 1 -- Foundation (Models + Error Classification)

**Goal**: Lay down the complete data model layer, the error classifier, and the `ToolResult.error_type` extension. The classifier is the foundation of every other module -- retry, circuit breaker, and executor all depend on `ClassifiedError`.

**Files**:
- `src/kosmos/recovery/__init__.py` -- package init with public exports
- `src/kosmos/recovery/classifier.py` -- `ErrorClass` (StrEnum), `DataGoKrErrorCode` (IntEnum), `ClassifiedError` (frozen model), `DataGoKrErrorClassifier` class with `classify_response()` and `classify_exception()` methods
- `src/kosmos/tools/models.py` -- extend `ToolResult.error_type` literal with `"timeout"`, `"circuit_open"`, `"api_error"`, `"auth_expired"`
- `tests/recovery/__init__.py`
- `tests/recovery/test_classifier.py` -- tests for all 9 `data.go.kr` error codes, XML gateway detection, HTTP-level classification (429, 401/403, 502/503/504), transport exceptions (`ConnectTimeout`, `ReadTimeout`), empty response body, unknown `resultCode`, non-httpx exceptions

**Key implementation details**:
- `classify_response()` first checks for the `<OpenAPI_ServiceResponse>` XML prefix using `str.startswith()`. If found, extracts `returnReasonCode` via `str.find('<returnReasonCode>')` and `str.find('</returnReasonCode>')` -- no XML parser (NFR-006).
- `classify_response()` then tries JSON body parsing for `resultCode` in the standard `data.go.kr` envelope (`response.header.resultCode`).
- `classify_exception()` maps `httpx.ConnectTimeout` and `httpx.ReadTimeout` to `TIMEOUT`, `httpx.HTTPStatusError` to the appropriate class by status code, and all other exceptions to `APP_ERROR`.
- The `is_retryable` flag is computed from a static mapping: `{RATE_LIMIT: True, TRANSIENT: True, TIMEOUT: True}`, all others `False`.

**Completion gate**: `uv run pytest tests/recovery/test_classifier.py` passes. All 9 `data.go.kr` error codes are correctly classified. XML gateway detection works with the `<OpenAPI_ServiceResponse>` prefix. SC-003 passes.

### Phase 2 -- Retry + Circuit Breaker

**Goal**: Implement the retry loop and circuit breaker. These are independent modules that share only `ClassifiedError` as input.

**Files**:
- `src/kosmos/recovery/retry.py` -- `ToolRetryPolicy` (frozen model), `retry_tool_call()` async function
- `src/kosmos/recovery/circuit_breaker.py` -- `CircuitState` (StrEnum), `CircuitBreakerConfig` (frozen model), `CircuitBreaker` class, `CircuitBreakerRegistry` class
- `tests/recovery/test_retry.py` -- US1 acceptance scenarios: retry on 429, retry on timeout, no retry on 400, `max_retries=0`, foreground full budget, background `min(1, max_retries)` cap
- `tests/recovery/test_circuit_breaker.py` -- US2 acceptance scenarios: CLOSED -> OPEN transition at threshold, OPEN -> HALF_OPEN after recovery timeout, HALF_OPEN -> CLOSED on probe success, HALF_OPEN -> OPEN on probe failure, failure counter reset on success, lazy creation in CLOSED state, concurrent HALF_OPEN probe limiting

**Key implementation details**:

`retry_tool_call()`:
- Signature: `async def retry_tool_call(adapter, validated_input, policy, classifier, *, is_foreground=True) -> tuple[dict[str, Any] | None, ClassifiedError | None, int]`
- Returns `(result_dict, last_error, attempt_count)`. On success: `(dict, None, N)`. On exhaustion: `(None, classified_error, N)`.
- Computes effective max retries: `policy.max_retries` for foreground, `min(1, policy.max_retries)` for background.
- Delay formula: `random.uniform(0, min(max_delay, base_delay * multiplier^attempt))` (matches existing `_compute_delay` pattern in `llm/retry.py`).
- On each failure: calls `classifier.classify_exception()` or `classifier.classify_response()` depending on whether the adapter raised or returned. If `classified.is_retryable` is False, stops immediately.
- Logs at `WARNING` per retry attempt.

`CircuitBreaker`:
- Internal state: `_state: CircuitState`, `_failure_count: int`, `_last_failure_time: float`, `_half_open_calls: int`.
- `allow_request() -> bool`:
  - CLOSED: always True.
  - OPEN: if `time.monotonic() - _last_failure_time >= recovery_timeout`, transition to HALF_OPEN. If HALF_OPEN and `_half_open_calls < config.half_open_max_calls`, allow. Otherwise reject.
  - HALF_OPEN: allow if probe count < max; reject otherwise.
- `record_success()`: HALF_OPEN -> CLOSED, reset counters. CLOSED: reset failure count.
- `record_failure()`: increment failure count. CLOSED: if `failure_count >= threshold`, transition to OPEN. HALF_OPEN: transition to OPEN.
- Uses `time.monotonic()` for timing (not wall clock).

`CircuitBreakerRegistry`:
- `dict[str, CircuitBreaker]` with lazy creation.
- `get(tool_id) -> CircuitBreaker`: creates with default config if not present.

**Completion gate**: `uv run pytest tests/recovery/test_retry.py tests/recovery/test_circuit_breaker.py` passes. SC-001 (retry with attempt count), SC-002 (circuit breaker sub-1ms rejection), SC-004 (background max 2 attempts) pass.

### Phase 3 -- Cache + Messages

**Goal**: Implement the response cache and graceful degradation messages. These are the fallback layer when retries and circuit breaker are exhausted.

**Files**:
- `src/kosmos/recovery/cache.py` -- `CacheEntry` (frozen model), `ResponseCache` class
- `src/kosmos/recovery/messages.py` -- `build_degradation_message()` function with Korean templates
- `tests/recovery/test_cache.py` -- US5 acceptance scenarios: cache hit within TTL, cache miss after TTL expiry, no cache for `cache_ttl_seconds=0`, LRU eviction at `max_entries`, cache store on success, cache key is `(tool_id, SHA-256(args))`
- `tests/recovery/test_messages.py` -- US6 acceptance scenarios: message contains `name_ko`, circuit open message mentions maintenance, deprecated API message mentions retirement, message is in Korean

**Key implementation details**:

`ResponseCache`:
- Internal storage: `collections.OrderedDict[tuple[str, str], CacheEntry]` with `max_entries=256` default.
- `get(tool_id, arguments_hash, ttl_seconds) -> CacheEntry | None`: checks existence, checks TTL via `time.monotonic() - entry.cached_at < ttl_seconds`. If valid, calls `move_to_end()` and returns. If expired, deletes and returns None.
- `put(entry) -> None`: if `entry.ttl_seconds == 0`, no-op. Otherwise, stores and calls `move_to_end()`. If `len > max_entries`, calls `popitem(last=False)`.
- `_compute_hash(arguments: dict) -> str`: `hashlib.sha256(json.dumps(arguments, sort_keys=True, ensure_ascii=False).encode()).hexdigest()`.

`messages.py`:
- Korean-language templates (domain data exception per constitution):
  - General failure: `"{name_ko} 서비스에 일시적인 문제가 발생했습니다. 잠시 후 다시 시도해 주세요. 긴급한 경우 해당 기관에 직접 문의하시기 바랍니다."`
  - Circuit open: `"{name_ko} 서비스가 현재 점검 중이거나 일시적인 장애가 발생했습니다. 잠시 후 다시 시도해 주세요."`
  - Service deprecated: `"{name_ko} 서비스 연동이 종료되었습니다. 해당 기관 홈페이지를 직접 방문해 주세요."`
  - Auth expired: `"{name_ko} 서비스 인증이 만료되었습니다. 다시 인증해 주세요."`
- `build_degradation_message(tool: GovAPITool, error: ClassifiedError) -> str`: selects template based on `error.error_class`, formats with `tool.name_ko`.

**Completion gate**: `uv run pytest tests/recovery/test_cache.py tests/recovery/test_messages.py` passes. SC-005 (cached fallback with 30-min-old result) and SC-006 (Korean message with `name_ko`) pass.

### Phase 4 -- RecoveryExecutor + ToolExecutor Integration

**Goal**: Implement the `RecoveryExecutor` orchestrator and wire it into `ToolExecutor`. This is the integration phase that brings classifier, retry, circuit breaker, cache, and messages together.

**Files**:
- `src/kosmos/recovery/executor.py` -- `ErrorContext` (frozen model), `RecoveryResult` (frozen model), `RecoveryExecutor` class
- `src/kosmos/tools/executor.py` -- additive change: optional `recovery_executor` parameter, step 5 delegation
- `tests/recovery/test_executor.py` -- full orchestration tests: retry -> success, retry -> exhaustion -> cache hit, retry -> exhaustion -> cache miss -> degradation, circuit breaker open -> cache hit, circuit breaker open -> no cache -> reject, foreground vs background, first-attempt success (ErrorContext is None)
- `tests/recovery/test_integration.py` -- end-to-end through `ToolExecutor.dispatch()` with `RecoveryExecutor` wired in: mock adapter that fails twice then succeeds, verify `ToolResult.success=True` returned; mock adapter always failing with circuit breaker, verify `error_type="circuit_open"`; backward compatibility test with `recovery_executor=None`

**Key implementation details**:

`RecoveryExecutor.execute()` pipeline:
```
1. Start timer (time.monotonic())
2. Get circuit breaker for tool_id (lazy creation)
3. If circuit breaker rejects (OPEN, no probe allowed):
   a. Try cache fallback
   b. If cache hit: return RecoveryResult with is_cached_fallback=True
   c. If cache miss: return RecoveryResult with degradation message, error_type="circuit_open"
4. Run retry loop (retry_tool_call):
   a. On success:
      - Record circuit breaker success
      - Cache the result (if cache_ttl_seconds > 0)
      - Return RecoveryResult with ErrorContext (if retries > 1) or None (if first-attempt)
   b. On retryable failure: continue loop (handled internally by retry_tool_call)
   c. On non-retryable failure: stop loop immediately
5. After retry exhaustion:
   a. Record circuit breaker failure
   b. Try cache fallback
   c. If cache hit: return RecoveryResult with is_cached_fallback=True
   d. If cache miss: return RecoveryResult with degradation message
6. Log at ERROR level when all recovery paths exhausted
7. Stop timer, compute elapsed_seconds
```

`ToolExecutor` integration:
- `__init__` gains `recovery_executor: RecoveryExecutor | None = None` parameter, stored as `self._recovery_executor`.
- Step 5 becomes:
  ```python
  if self._recovery_executor is not None:
      recovery_result = await self._recovery_executor.execute(
          tool=tool,
          adapter=adapter,
          validated_input=validated_input,
          is_foreground=True,
      )
      # RecoveryResult.tool_result already contains success/failure with data or error
      if not recovery_result.tool_result.success:
          return recovery_result.tool_result
      # On success, fall through to step 6 with the result data
      result_dict = recovery_result.tool_result.data
  else:
      # Original path (unchanged)
      try:
          result_dict = await adapter(validated_input)
      except Exception as exc:
          ...
  ```

**Note on `RecoveryExecutor` returning `ToolResult` directly**: When `RecoveryExecutor` succeeds, it constructs a `ToolResult(success=True, data=result_dict, tool_id=tool.id)`. This means step 6 (output schema validation) is bypassed for recovery-wrapped calls. This is correct because the adapter already returns a dict that was validated by the adapter itself. However, for defense-in-depth, the `RecoveryExecutor` success path should return the raw `result_dict` so that `ToolExecutor` can still run output validation. The integration will pass `recovery_result.tool_result.data` to step 6.

**Completion gate**: `uv run pytest tests/recovery/test_executor.py tests/recovery/test_integration.py` passes. All success criteria SC-001 through SC-006 pass through the full integration path. Backward compatibility test confirms `recovery_executor=None` produces identical behavior to the current codebase.

### Phase 5 -- Streaming Retry + Edge Cases

**Goal**: Add `StreamInterruptedError` retry to `query.py` and test all edge cases from the spec.

**Files**:
- `src/kosmos/engine/query.py` -- additive change: `except StreamInterruptedError` clause, `_stream_retry_count` variable
- `tests/recovery/test_streaming_retry.py` -- US7 acceptance scenarios: single interruption retried successfully, double interruption falls to `error_unrecoverable`, partial content from failed attempt discarded on retry
- `tests/recovery/test_integration.py` (extended) -- edge case tests:
  - XML body with HTTP 200 and `Content-Type: application/json`
  - Empty response body -> `UNKNOWN`
  - `resultCode` not in known map -> `UNKNOWN`, not retried
  - Circuit breaker for never-called tool -> lazy CLOSED creation
  - Concurrent HALF_OPEN calls -> only one probe allowed
  - Cache entry TTL uses write-time TTL, not current tool definition
  - `httpx.HTTPStatusError` with no response body
  - Non-httpx exception (`ValueError`) classified as `APP_ERROR`

**Key implementation details**:

`query.py` streaming retry:
- A `_stream_retry_count: int = 0` is initialized before the `while` loop.
- Inside the `try/except` block, a new `except StreamInterruptedError` clause is added before `except Exception`:
  ```python
  except StreamInterruptedError:
      if _stream_retry_count == 0:
          _stream_retry_count += 1
          logger.warning(
              "Stream interrupted mid-delivery, retrying (attempt 2)"
          )
          continue  # re-enter while loop; snapshot will be recreated
      logger.error("Stream interrupted on retry; giving up")
      yield QueryEvent(
          type="stop",
          stop_reason=StopReason.error_unrecoverable,
          stop_message="LLM stream interrupted after retry",
      )
      return
  ```
- On successful stream completion (after the `try/except`), `_stream_retry_count` is reset to 0 so that each turn's stream gets its own retry budget.
- Partial content from the failed attempt (`content_parts`, `pending_calls`) is discarded because `continue` jumps back to the top of the while loop where `pending_calls` and `content_parts` are re-initialized. The assistant message from the interrupted attempt is NOT appended to `ctx.state.messages` because the append happens after the `try/except` block.

**Completion gate**: `uv run pytest tests/recovery/test_streaming_retry.py` passes. SC-007 passes. All edge case tests pass. Full suite: `uv run pytest tests/recovery/` is 100% green.

### Phase 6 -- Quality Gate

**Goal**: Pass all quality checks: type checking, linting, and coverage.

**Activities**:
- `uv run mypy src/kosmos/recovery/ --strict` -- fix any type errors
- `uv run ruff check src/kosmos/recovery/ tests/recovery/` -- fix any lint violations
- `uv run ruff format src/kosmos/recovery/ tests/recovery/` -- format all files
- `uv run pytest tests/recovery/ --cov=src/kosmos/recovery --cov-report=term-missing` -- verify >= 80% coverage
- `uv run pytest tests/tools/ tests/engine/` -- verify no regressions in existing test suites
- Verify all 8 success criteria (SC-001 through SC-008) pass

**Completion gate**: All quality checks pass. Coverage >= 80% on `src/kosmos/recovery/`. No regressions in `tests/tools/` or `tests/engine/`.

---

## Reference Source Mapping

Every design decision traces to a concrete source in `docs/vision.md Section Reference materials` per constitution Section I.

| Decision | Source | Evidence |
|---|---|---|
| Exponential backoff with full jitter | stamina (`hynek/stamina`) | `delay = random.uniform(0, min(max_delay, base_delay * multiplier^attempt))`. Same formula used in existing `llm/retry.py _compute_delay()`. |
| Circuit breaker three-state machine (CLOSED/OPEN/HALF_OPEN) | aiobreaker (`arlyon/aiobreaker`) | Standard pattern: failure_threshold triggers OPEN, recovery_timeout triggers HALF_OPEN, probe success triggers CLOSED. Implemented internally (~200 LOC) instead of adding dependency. |
| `data.go.kr` error code map (1, 4, 12, 20, 22, 30, 31, 32) | PublicDataReader (`WooilJeong/PublicDataReader`) | Wire format ground truth for `returnReasonCode` values and XML gateway response format. |
| XML gateway error detection (`<OpenAPI_ServiceResponse>` prefix) | PublicDataReader (`WooilJeong/PublicDataReader`) | XML/JSON response normalization: check raw text for XML prefix before JSON parsing. |
| Error matrix: 429/503 retry, 401/403 auth, timeout retry, hard-failure degrade | `docs/vision.md Section Layer 6 -- Error Recovery` | Direct mapping from vision document error matrix to `ErrorClass` enum. |
| Foreground vs background retry distinction | `docs/vision.md Section Layer 6` | "aggressive retry" (foreground, full budget) vs "fails fast" (background, `min(1, max_retries)`). |
| Cached fallback using `cache_ttl_seconds` | `docs/vision.md Section Layer 2` | `GovAPITool.cache_ttl_seconds` field activated for fallback-on-failure. |
| Graceful degradation message with `name_ko` and in-person guidance | `docs/vision.md Section Layer 6` | Hard failure terminal path: Korean message + alternative contact channels. |
| `ToolRetryPolicy` as frozen Pydantic v2 model | Constitution Section III; LLM `RetryPolicy` structural precedent | `ConfigDict(frozen=True)` with validated fields. Mirrors `llm/retry.py RetryPolicy` structure. |
| Fail-closed for unknown error codes (`is_retryable=False`) | Constitution Section II | Unknown `resultCode` values are never retried. Fail-closed principle. |
| `RecoveryExecutor` never raises, returns `ToolResult` | Existing `ToolExecutor` convention | Executor pattern: all error paths produce classified results, never propagate exceptions. |
| Retry matrix pattern for `StreamInterruptedError` | OpenAI Agents SDK (retry matrix); Claude Agent SDK (error handling) | Single transparent retry on stream interruption. Matches composable retry policy pattern. |
| `src/kosmos/recovery/` as separate sub-package | `docs/vision.md` six-layer architecture; `AGENTS.md` layer separation | Layer 6 gets its own package, isolated from `tools/` and `engine/`. |
| No external dependencies for retry/circuit breaker | Constitution -- minimal dependencies; AGENTS.md -- never add dependency outside spec-driven PR | Internal implementation (~200 LOC each) avoids dependency bloat. Patterns adapted from stamina and aiobreaker, not code-copied. |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| `ToolResult.error_type` extension breaks existing consumers | Low | Medium | The extension is additive (new `Literal` union members). Existing code that matches on old values will simply not match new ones. The `model_validator` constraint (`error is not None and error_type is not None`) is unchanged. Covered by backward-compatibility test. |
| Circuit breaker state race under concurrent coroutines | Low | Medium | Python asyncio is single-threaded. No `await` between state read and state write in `allow_request()`, `record_success()`, `record_failure()`. No locking needed. Concurrent HALF_OPEN probe test validates this. |
| `ResponseCache` memory unbounded | Low | Medium | LRU eviction with `max_entries=256` default. Each entry is a small dict (typical API response). At 256 entries with ~10KB each, worst case is ~2.5MB. |
| Retry loop masks permanent failures by retrying too aggressively | Medium | Medium | Non-retryable errors (AUTH_FAILURE, SERVICE_DEPRECATED, APP_ERROR, UNKNOWN) are never retried (fail-closed). Background calls cap at 1 retry. Circuit breaker opens after 5 consecutive failures. |
| XML gateway response changes format | Low | Low | The `<OpenAPI_ServiceResponse>` prefix detection is robust to minor whitespace changes (uses `str.strip().startswith()`). If the format changes fundamentally, it falls through to `UNKNOWN` (fail-closed). |
| `RecoveryExecutor` wrapping bypasses output validation in `ToolExecutor` | Medium | Medium | Mitigated by passing `result_dict` to step 6 on the success path. Output validation still runs for recovery-wrapped calls. |
| `StreamInterruptedError` retry re-sends partial conversation | Low | Medium | The snapshot is recreated at the top of the while loop. The interrupted attempt's content and tool calls are discarded (local variables reset). The assistant message is only appended after the `try/except` block succeeds. |
| Cache key collision (SHA-256 hash) | Negligible | Low | SHA-256 collision probability is astronomically low. Canonical JSON serialization (`sort_keys=True`) ensures deterministic key computation. |

---

## Project Structure (final)

### Documentation

```
specs/010-error-recovery-v1/
    spec.md
    plan.md           # This file
    tasks.md          # /speckit-tasks output (not yet created)
```

### Source code layout

```
src/kosmos/recovery/
    __init__.py
    classifier.py
    retry.py
    circuit_breaker.py
    cache.py
    executor.py
    messages.py

src/kosmos/tools/
    models.py         # Modified: error_type literal extended with 4 new values
    executor.py       # Modified: optional recovery_executor parameter, step 5 delegation

src/kosmos/engine/
    query.py          # Modified: StreamInterruptedError retry clause

tests/recovery/
    __init__.py
    test_classifier.py
    test_retry.py
    test_circuit_breaker.py
    test_cache.py
    test_executor.py
    test_messages.py
    test_integration.py
    test_streaming_retry.py
```
