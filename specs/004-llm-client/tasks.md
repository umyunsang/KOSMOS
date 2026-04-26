# Tasks: LLM Client Integration (FriendliAI EXAONE)

**Input**: Design documents from `specs/004-llm-client/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3, US4)
- Exact file paths included in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create module structure and add dependencies

- [ ] T001 Create `src/kosmos/llm/` package directory with `__init__.py` and create `tests/llm/` package directory with `__init__.py`
- [ ] T002 Add `pydantic-settings>=2.0` to `dependencies` in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, configuration, and error types that ALL user stories depend on

**CRITICAL**: No user story work can begin until this phase is complete

- [ ] T003 [P] Implement error hierarchy (`KosmosLLMError`, `ConfigurationError`, `BudgetExceededError`, `AuthenticationError`, `LLMConnectionError`, `LLMResponseError`, `StreamInterruptedError`) in `src/kosmos/llm/errors.py`
- [ ] T004 [P] Implement Pydantic v2 message models (`ChatMessage`, `ToolCall`, `FunctionCall`, `TokenUsage`, `ChatCompletionResponse`, `StreamEvent`) in `src/kosmos/llm/models.py` — include role-based validation (tool role requires tool_call_id, system/user require content)
- [ ] T005 [P] Implement `LLMClientConfig` using pydantic-settings with `KOSMOS_FRIENDLI_TOKEN` (required SecretStr), `KOSMOS_FRIENDLI_BASE_URL` (default), `KOSMOS_FRIENDLI_MODEL` (default), `KOSMOS_LLM_SESSION_BUDGET` (default 100000), `timeout`, `max_retries` in `src/kosmos/llm/config.py`
- [ ] T006 [P] Create test infrastructure with shared fixtures (respx mock routes for chat/completions, mock SSE response generator, sample ChatMessage lists) in `tests/llm/conftest.py`

**Checkpoint**: Foundation ready — models, config, and errors are importable and tested

---

## Phase 3: User Story 1 — Single-turn Query Resolution (Priority: P1) MVP

**Goal**: Send a prompt to EXAONE via FriendliAI and receive a streamed response with token usage metadata

**Independent Test**: Send a prompt string, verify a streamed response is received chunk-by-chunk with correct content and token usage counts

### Implementation for User Story 1

- [ ] T007 [US1] Implement `LLMClient.__init__`, `close()`, `__aenter__`/`__aexit__` context manager, and non-streaming `complete()` method using httpx async POST to `/chat/completions` in `src/kosmos/llm/client.py`
- [ ] T008 [US1] Implement `LLMClient.stream()` async generator method with SSE line parsing (`data:` prefix, `[DONE]` sentinel, JSON chunk → `StreamEvent`) in `src/kosmos/llm/client.py`
- [ ] T009 [P] [US1] Write unit tests for Pydantic model validation (ChatMessage role constraints, TokenUsage computed total, StreamEvent types) in `tests/llm/test_models.py`
- [ ] T010 [P] [US1] Write unit tests for LLMClientConfig loading from env vars (missing token raises ConfigurationError, defaults applied, override via env) in `tests/llm/test_config.py`
- [ ] T011 [P] [US1] Write unit tests for `LLMClient.complete()` using respx (mock successful response, verify ChatCompletionResponse fields, verify token usage extracted) in `tests/llm/test_client.py`
- [ ] T012 [P] [US1] Write unit tests for `LLMClient.stream()` SSE parsing (mock SSE lines, verify StreamEvent sequence, verify final usage event, verify content_delta assembly) in `tests/llm/test_streaming.py`

**Checkpoint**: Single-turn query works end-to-end with streaming. `uv run pytest tests/llm/` passes.

---

## Phase 4: User Story 2 — Session Budget Enforcement (Priority: P2)

**Goal**: Track cumulative token usage per session and reject calls when budget is exhausted

**Independent Test**: Configure a low token budget, make calls until budget exhausted, verify the system refuses further calls with BudgetExceededError

### Implementation for User Story 2

- [ ] T013 [US2] Implement `UsageTracker` with `can_afford()`, `debit()`, `remaining` property, `is_exhausted` property, and `call_count` in `src/kosmos/llm/usage.py`
- [ ] T014 [US2] Integrate `UsageTracker` into `LLMClient`: initialize from config budget, pre-flight check in `complete()`/`stream()`, post-call debit from response usage in `src/kosmos/llm/client.py`
- [ ] T015 [US2] Write unit tests for UsageTracker (budget creation, debit, exhaustion, can_afford pre-flight, call_count increment) in `tests/llm/test_usage.py`

**Checkpoint**: Budget enforcement works. Calls exceeding budget are rejected before sending.

---

## Phase 5: User Story 3 — Transient Failure Recovery (Priority: P2)

**Goal**: Automatically retry 429/503 errors with exponential backoff; immediately fail on 401/400

**Independent Test**: Simulate 429/503 responses → verify automatic retry with backoff; simulate 401/400 → verify immediate failure with AuthenticationError/LLMResponseError

### Implementation for User Story 3

- [ ] T016 [US3] Implement `RetryPolicy` model and `retry_with_backoff()` async function (exponential backoff, full jitter, base 1s, multiplier 2x, cap 60s, max 3 retries, retryable codes {429, 503}) in `src/kosmos/llm/retry.py`
- [ ] T017 [US3] Integrate retry logic into `LLMClient.complete()` and `LLMClient.stream()` — wrap HTTP calls with retry, map non-retryable status codes to specific error types (401→AuthenticationError, 400→LLMResponseError) in `src/kosmos/llm/client.py`
- [ ] T018 [US3] Write unit tests for retry logic (429 retries with backoff, 503 retries then succeeds, 401 immediate failure, retry exhaustion raises LLMConnectionError) in `tests/llm/test_retry.py`

**Checkpoint**: Transient failures are recovered automatically. Permanent errors fail immediately.

---

## Phase 6: User Story 4 — Tool Use Message Assembly (Priority: P3)

**Goal**: Support sending tool definitions and receiving tool_calls in OpenAI function-calling format

**Independent Test**: Send messages with tool definitions, verify model response includes tool_calls with function name and JSON arguments; send tool result continuation, verify model incorporates it

### Implementation for User Story 4

- [ ] T019 [US4] Add `ToolDefinition` and `FunctionSchema` Pydantic v2 models to `src/kosmos/llm/models.py`
- [ ] T020 [US4] Implement tool_calls support in `LLMClient.complete()` and `LLMClient.stream()` — serialize `tools` parameter, parse `tool_calls` in response/stream events, handle `tool_call_delta` StreamEvent assembly in `src/kosmos/llm/client.py`
- [ ] T021 [US4] Write unit tests for tool use flow (request with tools parameter, response with tool_calls, streaming tool_call_delta assembly, tool result continuation message) in `tests/llm/test_client.py`

**Checkpoint**: Tool loop messages assemble correctly. Ready for Query Engine (Epic #5) integration.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finalize public API, add logging, validate documentation

- [ ] T022 Finalize public exports in `src/kosmos/llm/__init__.py` — export `LLMClient`, all models, all errors, `UsageTracker`, `RetryPolicy`, `LLMClientConfig`
- [ ] T023 Add stdlib `logging` calls for all LLM operations (request metadata, token counts, latency, retry attempts, errors) per FR-012 in `src/kosmos/llm/client.py`
- [ ] T024 Run `quickstart.md` code examples as validation (verify imports, API surface matches contract)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — start immediately
- **Foundational (Phase 2)**: Depends on Phase 1 — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Phase 2 — MVP delivery target
- **US2 (Phase 4)**: Depends on Phase 3 (needs working LLMClient to integrate UsageTracker)
- **US3 (Phase 5)**: Depends on Phase 3 (needs working LLMClient to integrate retry)
- **US4 (Phase 6)**: Depends on Phase 3 (extends models and client with tool support)
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational (Phase 2) — no story dependencies
- **US2 (P2)**: Depends on US1 (needs LLMClient to integrate budget tracking)
- **US3 (P2)**: Depends on US1 (needs LLMClient to integrate retry) — parallel-safe with US2
- **US4 (P3)**: Depends on US1 (extends models and client) — parallel-safe with US2/US3

### Within Each User Story

- Models/infrastructure before client integration
- Client integration before tests (tests verify integrated behavior)
- All [P] tasks within a phase can run in parallel

### Parallel Opportunities

- **Phase 2**: T003, T004, T005, T006 — all parallel-safe (different files)
- **Phase 3**: T009, T010, T011, T012 — test files are parallel-safe (after T007, T008)
- **Phase 4+5+6**: US2, US3, US4 are parallel-safe across stories (different files: usage.py, retry.py, models.py additions) — but each integrates into client.py, so client.py edits must be serialized

---

## Parallel Example: Foundational Phase

```text
# Launch all foundational tasks in parallel (different files):
Agent 1: T003 — errors.py
Agent 2: T004 — models.py
Agent 3: T005 — config.py
Agent 4: T006 — conftest.py
```

## Parallel Example: Cross-Story (after US1 complete)

```text
# US2, US3, US4 infrastructure tasks in parallel:
Agent 1: T013 [US2] — usage.py (new file)
Agent 2: T016 [US3] — retry.py (new file)
Agent 3: T019 [US4] — models.py (additions)
# Then serialize client.py integrations: T014, T017, T020
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T002)
2. Complete Phase 2: Foundational (T003-T006) — parallel
3. Complete Phase 3: US1 (T007-T012)
4. **STOP and VALIDATE**: `uv run pytest tests/llm/` passes
5. LLM client is usable for basic queries

### Incremental Delivery

1. Setup + Foundational → Foundation ready
2. Add US1 → Streaming LLM calls work (MVP!)
3. Add US2 → Budget enforcement active
4. Add US3 → Transient errors auto-recovered
5. Add US4 → Tool loop ready for Query Engine
6. Polish → Production-grade logging and exports

---

## Notes

- Total tasks: 24 (T001-T024)
- Parallel-safe tasks: 10 (marked [P])
- New dependency: `pydantic-settings>=2.0` (T002)
- All tests use respx for httpx mocking — no live API calls
- US2 and US3 are both P2 priority but parallel-safe
- client.py is the integration point — edits from different stories must be serialized
