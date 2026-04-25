# US4 Integration Notes — Ministry Agent Visibility

**Teammate**: Sonnet Teammate #4
**Date**: 2026-04-25
**Branch**: `feat/1635-ui-l2-citizen-port`

## Tasks Completed

| Task | Status | File |
|------|--------|------|
| T053 AgentVisibilityPanel | DONE | `tui/src/components/agents/AgentVisibilityPanel.tsx` |
| T054 AgentDetailRow | DONE | `tui/src/components/agents/AgentDetailRow.tsx` |
| T055 /agents command | DONE | `tui/src/commands/agents.ts` |
| T057 Live subscription (inside AgentVisibilityPanel) | DONE | `tui/src/components/agents/AgentVisibilityPanel.tsx` |
| T058 bun:test units | DONE | `tui/tests/components/agents/AgentVisibilityPanel.test.ts` + `tui/tests/commands/agents.test.ts` |

**Deferred to Lead**: T056 (REPL.tsx plan handler wiring), T059 (OTEL surface emit) — per task assignment.

## Files Produced

- `tui/src/components/agents/AgentVisibilityPanel.tsx` — Proposal-IV 5-state panel
- `tui/src/components/agents/AgentDetailRow.tsx` — SLA / health / avg-response row
- `tui/src/commands/agents.ts` — `/agents [--detail]` command
- `tui/tests/components/agents/AgentVisibilityPanel.test.ts` — schema + swarm tests
- `tui/tests/commands/agents.test.ts` — command arg parse + swarm regression

## Design Decisions

### Live Subscription (T057, FR-028)

The `AgentVisibilityPanel` subscribes to `WorkerStatusFrame` events directly inside a `useEffect` by iterating `bridge.frames()` (the existing async-iterable on the IPC bridge from `tui/src/ipc/bridge.ts`). No polling. The effect tears down cleanly (`cancelled = true` + loop break) on unmount, satisfying SC-007 ≤500 ms p95.

**Why bridge.frames() and not a custom event emitter?** The IPC bridge's `frames()` method is the canonical push channel for all backend events (Spec 032). Adding a second event bus would violate the single-path principle. The existing `onFrame` hook is fire-and-forget for telemetry; it cannot block on UI updates. The async iterable is the correct consumer.

**IPC status → AgentState mapping**:
```
IPC status          AgentState (FR-025)
────────────────────────────────────────
idle                → idle
running             → running
waiting_permission  → waiting-permission
error               → done   (terminal; displayed as done)
dispatched          → dispatched (not in IPC; set on new worker entry)
done                → done   (set externally via initialEntries)
```

The IPC `WorkerStatusFrame.worker_id` maps to `AgentVisibilityEntry.agent_id`. `WorkerStatusFrame.role_id` maps to `ministry` (the specialist label, e.g., `transport-specialist` or the ministry code). If a new `worker_id` arrives that is not in the current entries list, a new entry is appended.

### Dot Color Regulation (proposal-iv.mjs)

`dotColorForPrimitive()` from `tui/src/schemas/ui-l2/agent.ts` maps primitive verb → color token name. The panel resolves token names to hex using a local `PRIMITIVE_HEX` map matching the `_shared.mjs` `C` palette:

```
primitiveLookup    → #60a5fa (blue)
primitiveSubmit    → #fb923c (orange)
primitiveVerify    → #f87171 (red)
primitiveSubscribe → #34d399 (green)
primitivePlugin    → #a78bfa (purple)
```

The `currentPrimitive` per worker is passed in via `primitiveByWorker` prop. The Lead's T056 wiring should populate this from the LLM plan output.

## REPL.tsx Integration Handoff (T056 — Lead)

### Where to call shouldActivateSwarm

In `tui/src/screens/REPL.tsx`, find the section that processes an incoming LLM plan response. When the assistant reply includes a plan with `mentioned_ministries` and `complexity_tag` fields (structured output from the backend), call:

```typescript
import { shouldActivateSwarm } from '../schemas/ui-l2/agent.js'

// Inside the plan handler callback:
const swarmActive = shouldActivateSwarm({
  mentioned_ministries: plan.mentioned_ministries,  // string[]
  complexity_tag: plan.complexity_tag,              // 'simple' | 'complex'
})

if (swarmActive) {
  // Set swarm mode in app state
  setAppState(prev => ({ ...prev, swarmMode: true }))
}
```

### How to feed AgentVisibilityPanel from the LLM plan output

When swarm mode is active, render `AgentVisibilityPanel` in the REPL output area:

```typescript
import { AgentVisibilityPanel } from '../components/agents/AgentVisibilityPanel.js'
import { getOrCreateKosmosBridge } from '../ipc/bridgeSingleton.js'

// In REPL render (when swarmMode is true):
{swarmMode && (
  <AgentVisibilityPanel
    initialEntries={[]}          // Panel will self-populate from WorkerStatusFrames
    showDetail={false}            // Default; /agents --detail sets this to true
    bridge={getOrCreateKosmosBridge()}
    primitiveByWorker={primitiveByWorkerMap}  // Map<worker_id, primitive_verb>
  />
)}
```

The `primitiveByWorkerMap` should be populated from `WorkerStatusFrame.current_primitive` fields as they arrive. The Lead can maintain this as a `useState<Record<string, string>>` updated in the same frame-processing loop that drives the swarm indicator.

### T059 OTEL Surface Emit

Add `emitSurfaceActivation('agents')` when the `/agents` panel is first rendered. The `AgentsCommandView` component in `tui/src/commands/agents.ts` already calls this in a `useEffect`. For the inline REPL panel (activated by swarm), call:

```typescript
import { emitSurfaceActivation } from '../observability/surface.js'

// When AgentVisibilityPanel mounts in REPL context:
useEffect(() => {
  if (swarmMode) emitSurfaceActivation('agents', { 'kosmos.swarm.auto': true })
}, [swarmMode])
```

## Typecheck / Test Status

Run from `tui/`:
```bash
bun test tests/components/agents/AgentVisibilityPanel.test.ts
bun test tests/commands/agents.test.ts
```

Both test files are pure-logic tests (no Ink render required). They import only from `tui/src/schemas/ui-l2/agent.ts` and `tui/src/commands/agents.ts`, both of which have no DOM or IPC dependencies at import time.

TypeScript compilation: the components import from `.js` extension paths (Bun/ESM convention), use only `ink`, `react`, and existing schemas. No new runtime dependencies.
