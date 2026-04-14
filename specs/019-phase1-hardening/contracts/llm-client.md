# Contract — LLMClient public surface

**Feature**: 019-phase1-hardening
**Target file**: `src/kosmos/llm/client.py`

## Signatures (defaults established this epic; all overridable)

```python
class LLMClient:
    def __init__(
        self,
        *,
        # existing fields preserved
        max_retry_attempts: int = 5,
        retry_base_seconds: float = 1.0,
        retry_cap_seconds: float = 60.0,
        retry_jitter_ratio: float = 0.2,
        respect_retry_after: bool = True,
    ) -> None: ...

    async def complete(
        self,
        *,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 1.0,
        top_p: float = 0.95,
        presence_penalty: float = 0.0,
        max_tokens: int = 1024,
        enable_thinking: bool = False,
    ) -> LLMResponse: ...

    async def stream(
        self,
        *,
        messages: list[Message],
        tools: list[ToolDefinition] | None = None,
        temperature: float = 1.0,
        top_p: float = 0.95,
        presence_penalty: float = 0.0,
        max_tokens: int = 1024,
        enable_thinking: bool = False,
    ) -> AsyncIterator[LLMChunk]: ...
```

## Behavioral contract

1. **Serialization**: `complete()` and `stream()` acquire `self._semaphore` (initialized in `__init__` as `asyncio.Semaphore(1)`) around the provider call. Two concurrent invocations on the same instance execute sequentially at the provider boundary.
2. **Rate-limit handling (pre-stream)**: On HTTP 429 received before any chunk streams, the client sleeps per policy:
   - If response carries a parsable `Retry-After` header and `respect_retry_after=True`, sleep for that many seconds.
   - Otherwise sleep for `min(cap, base * 2**attempt) * uniform(1 - jitter, 1 + jitter)`.
   - Retry until success or `max_retry_attempts` attempts elapsed.
3. **Rate-limit handling (mid-stream)**: If a rate-limit error envelope is received after streaming has started, the iterator aborts the current stream, discards any partial text (does not surface a partial response as complete), and re-enters the retry loop with the same policy.
4. **Terminal failure**: On budget exhaustion, raise `LLMResponseError` with a category tag identifying rate-limit as the cause. No empty/partial response is returned to the caller.
5. **Parameter override**: Any caller passing an explicit value for `temperature`, `top_p`, `presence_penalty`, `max_tokens`, or `enable_thinking` takes precedence over the default.
6. **Payload assembly**: The outgoing provider payload includes `temperature`, `top_p`, `presence_penalty`, `max_tokens`, and `enable_thinking` fields — unit tests assert their presence and exact default values.

## Test checklist (contract-level)

- [ ] Retry-After mock → client sleeps ≥ header value before retry.
- [ ] Two consecutive 429s with no Retry-After → observed sleep intervals monotonic and bounded by cap.
- [ ] Jitter present → observed sleep is within `[delay*(1-jitter), delay*(1+jitter)]` across runs.
- [ ] 5 consecutive 429s → raises `LLMResponseError` with rate-limit category.
- [ ] Mid-stream 429 chunk → iterator aborts; retry loop engages; caller sees either a full response or `LLMResponseError`.
- [ ] Two `stream()` coroutines started on the same `LLMClient` instance → do not overlap at the provider boundary.
- [ ] Default payload assertion → outgoing body has `temperature=1.0`, `top_p=0.95`, `presence_penalty=0.0`, `max_tokens=1024`, `enable_thinking=false`.
- [ ] Explicit override → caller-supplied value appears in payload, defaults suppressed.
