# Contract — `sessionStore.setPendingPermission()` + `waitForPermissionDecision()`

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> Promise-based bridge between the IPC `permission_request` frame and the already-mounted `PermissionGauntletModal`.

## Module

`tui/src/store/sessionStore.ts` (modified — Step 7).

## Surface area additions

```typescript
import type { PermissionDecision } from '../ipc/codec.js'

export interface PendingPermissionRequest {
  request_id: string
  primitive_kind: 'submit' | 'subscribe'
  description_ko: string
  description_en: string
  risk_level: 'low' | 'medium' | 'high'
  receipt_id: string
  enqueued_at: number  // performance.now()
}

interface SessionStoreActions {
  // existing actions unchanged ...

  // NEW
  setPendingPermission: (
    request: PendingPermissionRequest,
  ) => Promise<PermissionDecision>

  resolvePermissionDecision: (
    request_id: string,
    decision: PermissionDecision,
  ) => void

  // NEW (selector helper for PermissionGauntletModal subscription)
  getActivePermission: () => PendingPermissionRequest | null
}
```

## `setPendingPermission(request)` semantics

```typescript
setPendingPermission(request) {
  return new Promise<PermissionDecision>((resolve) => {
    const queued: QueuedRequest = { ...request, resolver: resolve }
    set((state) => {
      if (state.activePermission == null) {
        state.activePermission = queued
        state.permissionTimeoutHandle = setTimeout(() => {
          this.resolvePermissionDecision(queued.request_id, 'timeout')
        }, getPermissionTimeoutMs())
      } else {
        state.permissionQueue.push(queued)
      }
    })
  })
}
```

- Idempotent on duplicate `request_id`: second call resolves immediately to `'denied'` with a `kosmos.permission.duplicate` warning span.
- Timeout window: `getPermissionTimeoutMs()` reads `KOSMOS_PERMISSION_TIMEOUT_SEC` (default 300, i.e. 5 minutes per Spec 033).

## `resolvePermissionDecision(request_id, decision)` semantics

```typescript
resolvePermissionDecision(request_id, decision) {
  set((state) => {
    if (state.activePermission?.request_id === request_id) {
      clearTimeout(state.permissionTimeoutHandle)
      state.activePermission.resolver(decision)
      // shift queue → next request becomes active
      const next = state.permissionQueue.shift() ?? null
      state.activePermission = next
      if (next != null) {
        state.permissionTimeoutHandle = setTimeout(() => {
          this.resolvePermissionDecision(next.request_id, 'timeout')
        }, getPermissionTimeoutMs())
      }
    } else {
      // not head — search queue
      const idx = state.permissionQueue.findIndex(q => q.request_id === request_id)
      if (idx >= 0) {
        state.permissionQueue[idx].resolver(decision)
        state.permissionQueue.splice(idx, 1)
      }
    }
  })
}
```

## `PermissionGauntletModal` integration

The modal at `tui/src/screens/REPL.tsx:5275-5277` (already mounted) subscribes via:

```typescript
const active = useSessionStore(s => s.activePermission)

if (active == null) return null

return (
  <PermissionGauntletModal
    request={active}
    onGrant={() => useSessionStore.getState().resolvePermissionDecision(active.request_id, 'granted')}
    onDeny={() => useSessionStore.getState().resolvePermissionDecision(active.request_id, 'denied')}
  />
)
```

The modal component itself is unchanged — only the props pipeline through `sessionStore`.

## Caller pattern (in `deps.ts`)

```typescript
} else if (fa.kind === 'permission_request') {
  const fp = f as PermissionRequestFrame
  const decision = await useSessionStore.getState().setPendingPermission({
    request_id: fp.request_id,
    primitive_kind: fp.primitive_kind,
    description_ko: fp.description_ko ?? '',
    description_en: fp.description_en ?? '',
    risk_level: fp.risk_level ?? 'medium',
    receipt_id: fp.receipt_id ?? '',
    enqueued_at: performance.now(),
  })

  bridge.send({
    session_id: sessionId,
    correlation_id: correlationId,
    ts: new Date().toISOString(),
    role: 'tui',
    kind: 'permission_response',
    request_id: fp.request_id,
    decision,
  } as PermissionResponseFrame as unknown as IPCFrame)
}
```

## Edge cases

| Case | Behavior |
|---|---|
| Backend sends two `permission_request` frames with same `request_id` | Second resolves immediately to `'denied'`, span `kosmos.permission.duplicate`. |
| Modal unmounts mid-decision (e.g., session save) | Cleanup function calls `resolvePermissionDecision(active.request_id, 'denied')` for fail-closed. |
| Backend never resolves (network drop) | 5-min timeout fires; backend receives `decision: 'timeout'`. |
| Citizen presses Esc while modal open | Modal calls `resolvePermissionDecision(active.request_id, 'denied')` — Esc maps to deny. |
| 100 queued requests | Queue is bounded by SessionStore's session lifetime; no max enforced (gated primitives are user-initiated; queue depth in practice is 0-3). |

## Test coverage

### `tui/tests/store/sessionStore.test.ts` (NEW or modified)

| Test | Asserts |
|---|---|
| `setPendingPermission stores active request when slot empty` | `state.activePermission` equals input request. |
| `setPendingPermission queues when slot occupied` | First request becomes active; second appears in `permissionQueue`. |
| `resolvePermissionDecision shifts queue` | After resolve, second request becomes head. |
| `Promise resolves with decision` | `await setPendingPermission(...)` returns the decision passed to resolve. |
| `timeout resolves to 'timeout' after configured ms` | `setTimeout` fakes; promise resolves. |
| `duplicate request_id resolves immediately to 'denied'` | Second `setPendingPermission` returns 'denied' synchronously (effectively). |
| `resolvePermissionDecision for unknown id is no-op` | No state change, no error. |

### `tui/tests/integration/permission-modal.test.ts` (NEW)

- Render REPL with mocked `PermissionGauntletModal`.
- Send `permission_request` IPC frame.
- Assert modal mounts with correct props.
- Click "Grant" — assert `permission_response{decision: 'granted'}` IPC frame is sent.

## OTEL attributes

- `kosmos.permission.queue_depth` (int gauge) — number of queued requests.
- `kosmos.permission.decision_latency_ms` (histogram) — `performance.now() - enqueued_at` at resolve time.
- `kosmos.permission.timeout_count` (int counter) — number of timeouts fired (alarm signal).
- `kosmos.permission.duplicate_count` (int counter) — duplicate request_ids dropped.
