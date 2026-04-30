# Contract — TUI Primitive Dispatcher (FR-001 / 002 / 003 / 004 / 005 / 006 / 007)

**Date**: 2026-04-30
**Owner**: TUI (`tui/src/tools/_shared/dispatchPrimitive.ts` + `tui/src/tools/_shared/pendingCallRegistry.ts` + 4 primitive `call()` bodies)

## I-D1 — Stub replacement

**Given** the LLM emits a tool_use for a primitive (`lookup` / `verify` / `submit` / `subscribe`) and the CC SDK invokes the local `tool.call(input, context)`.

**Then** `LookupPrimitive.call` / `VerifyPrimitive.call` / `SubmitPrimitive.call` / `SubscribePrimitive.call` MUST NOT return `{status: 'stub'}`. Each MUST delegate to `dispatchPrimitive(...)` and return its resolved `ToolResult<O>`.

## I-D2 — Shared helper signature

**Given** the helper `dispatchPrimitive` exported from `tui/src/tools/_shared/dispatchPrimitive.ts`.

**Then** the signature MUST be:

```typescript
async function dispatchPrimitive<O>(opts: {
  primitive: 'lookup' | 'verify' | 'submit' | 'subscribe'
  args: Record<string, unknown>
  context: ToolUseContext
  registry: PendingCallRegistry
  bridge: IPCBridge
  timeoutMs?: number
}): Promise<ToolResult<O>>
```

The 4 primitives differ only in (a) the literal `primitive` value and (b) the result-typing parameter `O`.

## I-D3 — IPC tool_call frame emission

**Given** `dispatchPrimitive(opts)` is invoked.

**Then** the function MUST:
1. Mint a fresh `callId = makeUUIDv7()` (from `tui/src/ipc/envelope.ts`).
2. Construct a `ToolCallFrame` (per `tui/src/ipc/frames.generated.ts:1234`) with `kind: 'tool_call'`, `call_id: callId`, `name: opts.primitive`, `arguments: opts.args`, `session_id` and `correlation_id` derived from `opts.context` and ambient session state.
3. Register the pending call: `opts.registry.register({callId, primitive, resolve, reject, timeoutHandle})`.
4. Send the frame: `opts.bridge.send(frame)`.
5. Return a `Promise<ToolResult<O>>` whose resolution / rejection is driven by the registry.

## I-D4 — Pending call registry contract

**Given** the registry instance (singleton per session, lifetime = REPL session).

**Then**:
- `register(call)` MUST throw if `call.callId` already exists in the registry (assert-once semantics).
- `resolve(callId, frame)` MUST clear the pending call's timeout handle and invoke its `resolve(frame)`. Returns `true` if found, `false` if no matching pending call (idempotent).
- `reject(callId, err)` MUST clear timeout and invoke `reject(err)`. Returns `true` if found.
- `clear()` MUST clear all pending calls — used at session teardown.
- Concurrent calls with distinct `callId` are non-interfering (Map is single-threaded JS — no locking needed).

## I-D5 — Frame stream `tool_result` route

**Given** the existing `tui/src/ipc/llmClient.ts` frame consumer loop at line 405 (the `tool_call` arm).

**Then** an additional `tool_result` arm MUST be added that:
1. Casts `frame as ToolResultFrame`.
2. Calls `pendingCallRegistry.resolve(frame.call_id, frame)`.
3. Logs at WARN if `resolve` returns `false` (no matching pending call); the frame is otherwise consumed silently.
4. Does NOT yield an SDK content_block event — the SDK loop is unaffected.

The registry instance is provided via the existing per-session injection point (or a new module-level singleton if no injection exists; preferred: pass through `LLMClientOptions` for testability).

## I-D6 — Timeout (FR-006)

**Given** `dispatchPrimitive(opts)` with `timeoutMs = 30_000` (default) or `KOSMOS_TUI_PRIMITIVE_TIMEOUT_MS` env override.

**Then**:
- A `setTimeout(reject, timeoutMs)` is registered alongside the pending call.
- On timeout, the registry's `reject` is invoked with `Error('응답 시간이 초과되었습니다')`.
- `dispatchPrimitive` catches the rejection and returns `{ data: { ok: false, error: '응답 시간이 초과되었습니다' } }`.
- An OTEL span attribute `kosmos.tui.primitive.timeout = true` is set on the active span.

## I-D7 — Error envelope passthrough (FR-007)

**Given** the backend emits a `tool_result` frame with `envelope.error` set.

**Then** `dispatchPrimitive` MUST surface the error to the citizen via the standard `renderToolResultMessage` path — return `{ data: { ok: false, error: <envelope.error> } }`. The TUI's existing error renderer prepends "오류 / Error:" prefix.

## I-D8 — VerifyPrimitive forwards args verbatim (FR-009 cross-ref)

**Given** the LLM-emitted args `{tool_id: "mock_verify_module_modid", params: {...}}`.

**Then** `VerifyPrimitive.call(input, context)` MUST invoke `dispatchPrimitive({primitive: 'verify', args: input, ...})` — the args object passed to `dispatchPrimitive` is the input object unmodified. No `tool_id` → `family_hint` translation occurs at the TUI layer. The IPC `tool_call` frame's `arguments` field carries `{tool_id, params}` verbatim.

## I-D9 — SubscribePrimitive lifetime (FR-004)

**Given** subscribe returns a session-lifetime `SubscriptionHandle` (per Spec 031).

**Then** `SubscribePrimitive.call(input, context)` returns the first `tool_result` frame's envelope as a "subscription opened" acknowledgment. The dispatcher does NOT keep the IPC frame stream open beyond the first result — subsequent stream events are out-of-scope for Phase 0 (deferred per spec.md Deferred Items "Subscribe primitive E2E demonstration"). For Phase 0, returning the opened-acknowledgment is the contract.

## I-D10 — Bun test coverage

**Given** `tui/src/tools/_shared/dispatchPrimitive.test.ts`.

**Then** the test MUST cover:
- ✅ Successful round-trip (mock bridge: send → fake tool_result → resolve).
- ✅ Timeout rejection.
- ✅ Error envelope passthrough.
- ✅ Concurrent calls don't cross-resolve.
- ✅ `verify` args preserve `tool_id` field name (FR-009 / I-D8 + I-V6).

`bun test` MUST pass on `2297-zeta-e2e-smoke` HEAD with no regressions vs `main`.
