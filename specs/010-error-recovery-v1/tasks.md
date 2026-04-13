# Tasks: Error Recovery v1 (Layer 6)

**Input**: `specs/010-error-recovery-v1/` (spec.md, plan.md)
**Epic**: #10 — Error Recovery v1 (Layer 6)
**Branch**: `feat/010-error-recovery-v1`

---

## Phase 1: Setup (Package Structure)

**Purpose**: Create the `src/kosmos/recovery/` sub-package and `tests/recovery/` directory.
No source code yet — just the file system skeleton that all later tasks populate.

- [ ] T001 Create `src/kosmos/recovery/__init__.py` with empty public export list
- [ ] T002 Create `tests/recovery/__init__.py` to make test directory a package
- [ ] T003 Create `tests/recovery/conftest.py` with shared fixtures: mock adapter factory (`make_adapter` yielding success/failure/timeout), mock `GovAPITool` with `cache_ttl_seconds` and `name_ko`, sample XML gateway response string, sample JSON error response bodies for each `DataGoKrErrorCode`

**Checkpoint**: `src/kosmos/recovery/` and `tests/recovery/` exist as importable packages. `conftest.py` fixtures are available.

---

## Phase 2: Error Classifier (Blocking)

**Purpose**: Lay down the error classification foundation. Every other module (retry, circuit
breaker, executor) depends on `ClassifiedError` and `ErrorClass`. The `ToolResult.error_type`
literal is extended here because downstream modules reference the new values. No user story
work begins until this phase is complete.

- [ ] T004 Implement `DataGoKrErrorCode` (IntEnum) and `ErrorClass` (StrEnum) enums with all values from the spec in `src/kosmos/recovery/classifier.py`
- [ ] T005 Implement `ClassifiedError` frozen Pydantic v2 model (`error_class`, `is_retryable`, `raw_code`, `raw_message`, `source`) in `src/kosmos/recovery/classifier.py`
- [ ] T006 Implement `DataGoKrErrorClassifier` with `classify_response(status_code, body, content_type)` method: XML gateway detection via `str.startswith('<OpenAPI_ServiceResponse>')` + `str.find()` extraction of `returnReasonCode` (no XML parser per NFR-006), JSON `resultCode` parsing, HTTP status code classification (429 -> RATE_LIMIT, 401/403 -> AUTH_FAILURE, 502/503/504 -> TRANSIENT) in `src/kosmos/recovery/classifier.py`
- [ ] T007 Implement `DataGoKrErrorClassifier.classify_exception(exc)` method: `httpx.ConnectTimeout`/`ReadTimeout` -> TIMEOUT, `httpx.HTTPStatusError` -> classify by status code, all other exceptions -> APP_ERROR, in `src/kosmos/recovery/classifier.py`
- [ ] T008 Extend `ToolResult.error_type` literal in `src/kosmos/tools/models.py` with four new values: `"timeout"`, `"circuit_open"`, `"api_error"`, `"auth_expired"` (FR-012)
- [ ] T009 [P] Write unit tests for all 9 `data.go.kr` error codes, XML gateway detection, HTTP-level classification (429, 401/403, 502/503/504), transport exceptions, empty response body -> UNKNOWN, unknown `resultCode` -> UNKNOWN with `is_retryable=False`, non-httpx exceptions -> APP_ERROR in `tests/recovery/test_classifier.py`

**Completion gate**: `uv run pytest tests/recovery/test_classifier.py` passes. All 9 `data.go.kr` error codes correctly classified. XML gateway detection works with `<OpenAPI_ServiceResponse>` prefix. SC-003 passes.

---

## Phase 3: User Story 1 — Retry Matrix (Priority: P1)

**Goal**: `retry_tool_call()` wraps adapter calls with exponential backoff + full jitter,
respecting the foreground/background distinction. Retries only retryable errors and stops
immediately on non-retryable classifications.

**Independent Test**: Configure `ToolRetryPolicy` with `max_retries=3`, mock an adapter that
fails twice with HTTP 429 then succeeds on the third call, assert the successful result is
returned with `attempt_count == 3`.

### Implementation for User Story 1

- [ ] T010 [US1] Implement `ToolRetryPolicy` frozen Pydantic v2 model (`max_retries`, `base_delay`, `multiplier`, `max_delay`, `retryable_classes`) with field validators in `src/kosmos/recovery/retry.py`
- [ ] T011 [US1] Implement `retry_tool_call()` async function with exponential backoff + full jitter (`delay = random.uniform(0, min(max_delay, base_delay * multiplier^attempt))`), foreground/background distinction (`min(1, policy.max_retries)` for background), WARNING log per retry attempt, returning `(result_dict | None, ClassifiedError | None, attempt_count)` tuple in `src/kosmos/recovery/retry.py`
- [ ] T012 [P] [US1] Write unit tests for US1 acceptance scenarios: retry on 429, retry on timeout, no retry on 400, `max_retries=0`, foreground full budget (3 retries = 4 attempts), background `min(1, max_retries)` cap (1 retry = 2 attempts) in `tests/recovery/test_retry.py`

**Completion gate**: `uv run pytest tests/recovery/test_retry.py` passes. SC-001 (retry with `attempt_count == 3`) and SC-004 (background max 2 attempts) pass.

---

## Phase 4: User Story 2 — Circuit Breaker (Priority: P1)

**Goal**: `CircuitBreaker` implements the three-state machine (CLOSED, OPEN, HALF_OPEN) with
per-tool isolation via `CircuitBreakerRegistry`. Circuit breaker state checks are O(1) and
transitions are atomic within the event loop.

**Independent Test**: Create `CircuitBreaker` with `failure_threshold=5` and
`recovery_timeout=30.0`, trigger 5 consecutive failures, assert OPEN state, advance time by
30 seconds, assert HALF_OPEN state.

### Implementation for User Story 2

- [ ] T013 [US2] Implement `CircuitState` (StrEnum) and `CircuitBreakerConfig` frozen Pydantic v2 model (`failure_threshold`, `recovery_timeout`, `half_open_max_calls`) in `src/kosmos/recovery/circuit_breaker.py`
- [ ] T014 [US2] Implement `CircuitBreaker` class with `allow_request()`, `record_success()`, `record_failure()` methods and the three-state machine (CLOSED -> OPEN at threshold, OPEN -> HALF_OPEN after recovery_timeout, HALF_OPEN -> CLOSED on probe success, HALF_OPEN -> OPEN on probe failure) using `time.monotonic()` in `src/kosmos/recovery/circuit_breaker.py`
- [ ] T015 [US2] Implement `CircuitBreakerRegistry` class with lazy per-tool `CircuitBreaker` creation via `get(tool_id)` in `src/kosmos/recovery/circuit_breaker.py`
- [ ] T016 [P] [US2] Write unit tests for US2 acceptance scenarios: CLOSED -> OPEN at threshold, OPEN -> HALF_OPEN after recovery timeout, HALF_OPEN -> CLOSED on success, HALF_OPEN -> OPEN on failure, failure counter reset on success, lazy CLOSED creation for new tool, concurrent HALF_OPEN probe limiting in `tests/recovery/test_circuit_breaker.py`

**Completion gate**: `uv run pytest tests/recovery/test_circuit_breaker.py` passes. SC-002 (circuit breaker sub-1ms rejection) passes.

---

## Phase 5: User Story 5 + User Story 6 — Cache and Degradation Messages (Priority: P2)

**Goal**: `ResponseCache` provides LRU + TTL in-memory cache for fallback on failure.
`build_degradation_message()` produces Korean-language citizen-facing error messages with
the tool's `name_ko` and actionable guidance.

**Independent Test (cache)**: Populate `ResponseCache` with a result for `cache_ttl_seconds=3600`,
call `get()` after 30 minutes, assert hit. Call `get()` after 2 hours, assert miss.

**Independent Test (messages)**: Call `build_degradation_message()` for a circuit-open failure,
assert the message contains the tool's `name_ko` and mentions maintenance.

### Implementation for User Story 5 + 6

- [ ] T017 [US5] Implement `CacheEntry` frozen Pydantic v2 model (`tool_id`, `arguments_hash`, `data`, `cached_at`, `ttl_seconds`) in `src/kosmos/recovery/cache.py`
- [ ] T018 [US5] Implement `ResponseCache` class with `get(tool_id, arguments_hash, ttl_seconds)`, `put(entry)`, and `compute_hash(arguments)` methods using `collections.OrderedDict` for LRU eviction with configurable `max_entries=256` in `src/kosmos/recovery/cache.py`
- [ ] T019 [US6] Implement `build_degradation_message(tool, error)` function with Korean-language templates for general failure, circuit open, service deprecated, and auth expired cases in `src/kosmos/recovery/messages.py`
- [ ] T020 [P] [US5] Write unit tests for US5 acceptance scenarios: cache hit within TTL, cache miss after TTL expiry, no cache for `cache_ttl_seconds=0`, LRU eviction at `max_entries`, cache store on success, cache key is `(tool_id, SHA-256(args))` in `tests/recovery/test_cache.py`
- [ ] T021 [P] [US6] Write unit tests for US6 acceptance scenarios: message contains `name_ko`, circuit open message mentions maintenance, deprecated API message mentions retirement, message is in Korean in `tests/recovery/test_messages.py`

**Completion gate**: `uv run pytest tests/recovery/test_cache.py tests/recovery/test_messages.py` passes. SC-005 (cached fallback with 30-min-old result) and SC-006 (Korean message with `name_ko`) pass.

---

## Phase 6: RecoveryExecutor (Priority: P1)

**Goal**: `RecoveryExecutor` orchestrates the full recovery pipeline — circuit breaker check,
retry loop, error classification, cache fallback, and graceful degradation message. Returns
`RecoveryResult` (never raises). `ErrorContext` carries structured metadata for logging.

**Independent Test**: Call `RecoveryExecutor.execute()` with a mock adapter that always fails,
no cached fallback, circuit breaker open, assert the returned `ToolResult.error` contains
a Korean degradation message.

### Implementation for User Story 3 + 4 (Orchestration)

- [ ] T022 [US3/4] Implement `ErrorContext` frozen Pydantic v2 model (`attempt_count`, `elapsed_seconds`, `error_class`, `is_cached_fallback`, `circuit_state`, `tool_id`) and `RecoveryResult` frozen model (`tool_result`, `error_context`) in `src/kosmos/recovery/executor.py`
- [ ] T023 [US3/4] Implement `RecoveryExecutor` class with `execute(tool, adapter, validated_input, *, is_foreground=True) -> RecoveryResult` orchestrating: circuit breaker check -> retry loop -> cache fallback -> degradation message. Never raises. Logs WARNING per retry, ERROR when all paths exhausted. in `src/kosmos/recovery/executor.py`
- [ ] T024 [US3/4] Update `src/kosmos/recovery/__init__.py` to export all public symbols: `RecoveryExecutor`, `RecoveryResult`, `ErrorContext`, `ToolRetryPolicy`, `CircuitBreaker`, `CircuitBreakerConfig`, `CircuitBreakerRegistry`, `DataGoKrErrorClassifier`, `ErrorClass`, `ClassifiedError`, `DataGoKrErrorCode`, `CircuitState`, `ResponseCache`, `CacheEntry`
- [ ] T025 [P] [US3/4] Write unit tests for RecoveryExecutor: retry -> success, retry -> exhaustion -> cache hit (is_cached_fallback=True), retry -> exhaustion -> cache miss -> degradation message, circuit breaker OPEN -> cache hit, circuit breaker OPEN -> no cache -> reject with error_type="circuit_open", foreground vs background attempt counts, first-attempt success (ErrorContext is None) in `tests/recovery/test_executor.py`

**Completion gate**: `uv run pytest tests/recovery/test_executor.py` passes. RecoveryExecutor never raises on any error path. All orchestration scenarios produce correct `RecoveryResult`.

---

## Phase 7: Integration (Priority: P1)

**Goal**: Wire `RecoveryExecutor` into `ToolExecutor` (optional parameter, step 5 delegation)
and add `StreamInterruptedError` retry to `query.py`. End-to-end tests verify the full
pipeline from `ToolExecutor.dispatch()` through recovery.

**Independent Test (ToolExecutor)**: Construct `ToolExecutor` with `RecoveryExecutor`, mock
adapter fails twice then succeeds, assert `ToolResult.success=True` returned.

**Independent Test (streaming)**: Mock `LLMClient.stream()` to raise `StreamInterruptedError`
on first call, succeed on second, assert `query()` completes with `stop` event.

### Implementation for Integration

- [ ] T026 [US1-6] Add optional `recovery_executor: RecoveryExecutor | None = None` parameter to `ToolExecutor.__init__()`, delegate step 5 of dispatch pipeline to `RecoveryExecutor.execute()` when present, preserve original path when absent (backward-compatible) in `src/kosmos/tools/executor.py`
- [ ] T027 [US7] Add `except StreamInterruptedError` clause to `query.py` try/except block around `ctx.llm_client.stream()`, with `_stream_retry_count` variable, single retry on first interruption, `error_unrecoverable` on second in `src/kosmos/engine/query.py`
- [ ] T028 [P] Write integration tests through `ToolExecutor.dispatch()` with `RecoveryExecutor` wired in: mock adapter fails twice then succeeds -> `ToolResult.success=True`; always-failing adapter with circuit breaker -> `error_type="circuit_open"`; backward compatibility test with `recovery_executor=None` in `tests/recovery/test_integration.py`
- [ ] T029 [P] [US7] Write streaming retry tests: single interruption retried successfully, double interruption -> `error_unrecoverable`, partial content discarded on retry, `_stream_retry_count` resets between turns in `tests/recovery/test_streaming_retry.py`

**Completion gate**: `uv run pytest tests/recovery/test_integration.py tests/recovery/test_streaming_retry.py` passes. SC-007 (StreamInterruptedError retry) passes. `ToolExecutor` backward compatibility confirmed. `uv run pytest tests/tools/` remains 100% green.

---

## Phase 8: Edge Cases + Regression

**Purpose**: Validate all edge cases from the spec and ensure no regressions in existing
test suites.

- [ ] T030 [P] Write edge-case tests: XML body with HTTP 200 + `Content-Type: application/json`, empty response body -> UNKNOWN, unknown `resultCode` -> UNKNOWN + not retried, circuit breaker for never-called tool -> lazy CLOSED, concurrent HALF_OPEN probe limiting, cache entry TTL uses write-time TTL, `httpx.HTTPStatusError` with no response body, non-httpx exception -> APP_ERROR in `tests/recovery/test_integration.py`
- [ ] T031 [P] Run full regression suite to verify no existing tests break: `uv run pytest tests/tools/` and `uv run pytest tests/engine/` must be 100% green

**Completion gate**: All edge case tests pass. Existing test suites (`tests/tools/`, `tests/engine/`) remain 100% green.

---

## Phase 9: Quality Gate

**Purpose**: Pass all quality checks: type checking, linting, formatting, and coverage.

- [ ] T032 [P] Run `uv run mypy src/kosmos/recovery/ --strict` — fix any type errors
- [ ] T033 [P] Run `uv run ruff check src/kosmos/recovery/ tests/recovery/` and `uv run ruff format src/kosmos/recovery/ tests/recovery/` — fix lint and format violations
- [ ] T034 Run `uv run pytest tests/recovery/ --cov=src/kosmos/recovery --cov-report=term-missing` — verify >= 80% coverage on `src/kosmos/recovery/`
- [ ] T035 Verify all 8 success criteria (SC-001 through SC-008) pass end-to-end

**Completion gate**: All quality checks pass. Coverage >= 80% on `src/kosmos/recovery/`. SC-001 through SC-008 all pass. `uv run pytest tests/recovery/` is 100% green. No regressions in `tests/tools/` or `tests/engine/`.

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
    └── Phase 2 (Error Classifier) ← blocks everything below
            ├── Phase 3 (US1: Retry Matrix)
            │       └── Phase 6 (RecoveryExecutor) ← depends on retry + circuit breaker + cache + messages
            ├── Phase 4 (US2: Circuit Breaker)
            │       └── Phase 6 (RecoveryExecutor)
            └── Phase 5 (US5+6: Cache + Messages)
                    └── Phase 6 (RecoveryExecutor)
                            └── Phase 7 (Integration) ← depends on executor complete
                                    └── Phase 8 (Edge Cases + Regression)
                                            └── Phase 9 (Quality Gate)
```

### Within-Phase Parallelism

Tasks marked `[P]` within the same phase touch different files and can run simultaneously:

- **Phase 2**: T009 test file is parallel with T004–T008 implementation
- **Phase 3**: T012 test file is parallel with T010–T011 implementation
- **Phase 4**: T016 test file is parallel with T013–T015 implementation
- **Phase 5**: T020 and T021 test files are parallel with T017–T019 implementation
- **Phase 6**: T025 test file is parallel with T022–T024 implementation
- **Phase 7**: T028 and T029 test files are parallel with T026–T027 implementation
- **Phase 8**: T030 and T031 are parallel (different test scopes)
- **Phase 9**: T032 and T033 are parallel (different quality tools)

### Cross-Phase Parallelism

Once Phase 2 is complete, Phases 3, 4, and 5 can all start in parallel — they touch
different files (`retry.py` vs `circuit_breaker.py` vs `cache.py` + `messages.py`):

```
Teammate A — US1 Retry (Phase 3):
  src/kosmos/recovery/retry.py           (T010, T011)
  tests/recovery/test_retry.py           (T012)

Teammate B — US2 Circuit Breaker (Phase 4):
  src/kosmos/recovery/circuit_breaker.py  (T013, T014, T015)
  tests/recovery/test_circuit_breaker.py  (T016)

Teammate C — US5+6 Cache + Messages (Phase 5):
  src/kosmos/recovery/cache.py            (T017, T018)
  src/kosmos/recovery/messages.py         (T019)
  tests/recovery/test_cache.py            (T020)
  tests/recovery/test_messages.py         (T021)
```

All three teammates finish before Phase 6 (RecoveryExecutor) begins. Phase 6 touches
`executor.py` and `__init__.py` which are not edited by Phases 3–5.

Phase 7 integration touches `src/kosmos/tools/executor.py` and `src/kosmos/engine/query.py`
(external modules), which are not edited by any prior recovery phase.

---

## Task Count Summary

| Phase | Tasks | Parallel-eligible | User Story |
|-------|-------|-------------------|------------|
| Phase 1: Setup | 3 | 0 | — |
| Phase 2: Error Classifier | 6 | 1 | US3 (classification) |
| Phase 3: US1 Retry Matrix | 3 | 1 | US1 |
| Phase 4: US2 Circuit Breaker | 4 | 1 | US2 |
| Phase 5: US5+6 Cache + Messages | 5 | 2 | US5, US6 |
| Phase 6: RecoveryExecutor | 4 | 1 | US3, US4 |
| Phase 7: Integration | 4 | 2 | US1–7 |
| Phase 8: Edge Cases + Regression | 2 | 2 | — |
| Phase 9: Quality Gate | 4 | 2 | — |
| **Total** | **35** | **12** | — |

- **Total tasks**: 35
- **Parallel-eligible**: 12 (marked `[P]`)
- **Sequential-only**: 23
- **P1 user stories**: US1, US2, US3 (Phases 2–4, 6–7)
- **P2 user stories**: US4, US5, US6 (Phases 5–6)
- **P3 user story**: US7 (Phase 7)
- **New source files**: 7 (`recovery/__init__.py`, `classifier.py`, `retry.py`, `circuit_breaker.py`, `cache.py`, `executor.py`, `messages.py`)
- **Modified source files**: 3 (`tools/models.py`, `tools/executor.py`, `engine/query.py`)
- **New test files**: 9 (`tests/recovery/__init__.py`, `conftest.py`, `test_classifier.py`, `test_retry.py`, `test_circuit_breaker.py`, `test_cache.py`, `test_messages.py`, `test_executor.py`, `test_integration.py`, `test_streaming_retry.py`)
