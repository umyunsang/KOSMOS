# Phase 1 Data Model: Full TUI (Ink + React + Bun)

**Branch**: `287-tui-ink-react-bun` | **Date**: 2026-04-19
**Feeds**: `contracts/*.schema.json`, `quickstart.md`, `tasks.md`

The TUI is a thin presentation layer; its data model is the **IPC frame union** it ingests, the **render-state store** it derives, and the **upstream component map** it lifts. No persistent entities.

---

## 1. IPC Frame Union

The single data plane between the TypeScript TUI and the Python backend. Encoded as newline-delimited JSON (JSONL) over stdin/stdout.

### 1.1 Envelope

```python
# Python source of truth — src/kosmos/ipc/frame_schema.py (new)
from typing import Annotated, Literal, Union
from pydantic import BaseModel, ConfigDict, Field

class _IPCFrameBase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    session_id: str                       # ULID; shared across all frames in a session
    correlation_id: str | None = None     # ULID of the triggering frame; None for unsolicited
    ts: str                               # RFC 3339 UTC timestamp, e.g. "2026-04-19T12:34:56.789Z"
```

### 1.2 Discriminated union (10 arms)

| `kind` | Direction | Payload shape | Source FR |
|---|---|---|---|
| `user_input` | TUI → backend | `{text: str}` | FR-002 |
| `assistant_chunk` | backend → TUI | `{message_id: str, delta: str, done: bool}` | FR-002, FR-006 |
| `tool_call` | backend → TUI (display) | `{call_id: str, name: str, arguments: dict}` | FR-002 |
| `tool_result` | backend → TUI (render) | `{call_id: str, envelope: PrimitiveEnvelope}` | FR-002, FR-008, FR-017–033 |
| `coordinator_phase` | backend → TUI | `{phase: Literal["Research","Synthesis","Implementation","Verification"]}` | FR-002, FR-043 |
| `worker_status` | backend → TUI | `{worker_id: str, role_id: str, current_primitive: str, status: Literal["idle","running","waiting_permission","error"]}` | FR-002, FR-044 |
| `permission_request` | backend → TUI | `{request_id: str, worker_id: str, primitive_kind: str, description_ko: str, description_en: str, risk_level: Literal["low","medium","high"]}` | FR-002, FR-045 |
| `permission_response` | TUI → backend | `{request_id: str, decision: Literal["granted","denied"]}` | FR-002, FR-046 |
| `session_event` | bidirectional | `{event: Literal["save","load","list","resume","new","exit"], payload: dict}` | FR-002, FR-038 |
| `error` | backend → TUI | `{code: str, message: str, details: dict}` | FR-002, FR-033 |

The Pydantic union:

```python
IPCFrame = Annotated[
    Union[
        UserInputFrame, AssistantChunkFrame, ToolCallFrame, ToolResultFrame,
        CoordinatorPhaseFrame, WorkerStatusFrame, PermissionRequestFrame,
        PermissionResponseFrame, SessionEventFrame, ErrorFrame,
    ],
    Field(discriminator="kind"),
]
```

### 1.3 FIFO & ordering invariants

- Frames within a `session_id` are delivered to the TUI renderer in the order they are written to stdout (FR-005). The TUI MUST NOT reorder. Enforced by a single-consumer async queue in `tui/src/ipc/bridge.ts`.
- `assistant_chunk` with `done: true` is terminal for its `message_id`; subsequent chunks for the same id are discarded with a `WARN` log.
- `permission_response` is always emitted by the TUI in response to a `permission_request` within the same `session_id`; `request_id` round-trips.

### 1.4 Crash / error invariants

- If JSONL parse fails on a single frame, the TUI logs at `ERROR` level, renders `<UnrecognizedPayload />`, and continues — other frames are not discarded (FR-033, Edge Case: malformed JSONL).
- If the backend process exits non-zero, the TUI surfaces `<CrashNotice />` within 5 s. All `KOSMOS_*` env var values in the trace are redacted (FR-004).

---

## 2. PrimitiveEnvelope (nested inside `tool_result`)

Mirrors Spec 031's 5-arm primitive discriminated union. The `kind` field at this nesting level is the primitive name (not the outer frame kind).

| Outer `kind` | Nested `kind` | Subtype discriminator | Renderer |
|---|---|---|---|
| `tool_result` | `lookup` | `subtype: LookupPoint \| LookupRecord \| LookupTimeseries \| LookupList \| LookupCollection \| LookupDetail \| LookupError` | `<PointCard />` / `<TimeseriesTable />` / `<CollectionList />` / `<DetailView />` / `<ErrorBanner />` |
| `tool_result` | `resolve_location` | `slots: {coords?, adm_cd?, address?, poi?}` | `<CoordPill />` + `<AdmCodeBadge />` + `<AddressBlock />` + `<POIMarker />` |
| `tool_result` | `submit` | `family: Literal["pay","issue_certificate","submit_application","reserve_slot","check_eligibility"]` + optional `mock_reason: Literal["tee_bound","payment_rail","pii_gate","delegation_absent"]` | `<SubmitReceipt />` / `<SubmitErrorBanner />` |
| `tool_result` | `subscribe` | `modality: Literal["cbs","rest_pull","rss"]`, AsyncIterator of `StreamEvent` + terminal `StreamClosed` with `close_reason: Literal["exhausted","revoked","timeout"]` | `<EventStream />` / `<StreamClosed />` |
| `tool_result` | `verify` | `family: Literal["gongdong_injeungseo","geumyung_injeungseo","ganpyeon_injeung","digital_onepass","mobile_id","mydata"]`, `korea_tier` (one of 18 published values), `nist_aal_hint?` | `<AuthContextCard />` / `<AuthWarningBanner />` |

**Invariants** (enforced by renderers, tested per FR-034):

- `verify` primary label = `korea_tier` (never omitted even if `nist_aal_hint` absent) — FR-030.
- `submit` with `mock_reason` present renders a `[MOCK: <reason>]` chip — FR-026.
- Any unrecognized nested `kind` → `<UnrecognizedPayload />`; no structure-guessing — FR-033.

---

## 3. Render-State Store (TUI-side, ephemeral)

Lifted from Claude Code's `useSyncExternalStore` pattern (`.references/claude-code-sourcemap/restored-src/src/hooks/useSyncExternalStore*` + `restored-src/src/store/`).

### 3.1 Store shape

```ts
interface SessionStore {
  session_id: string;                 // From first frame
  messages: Map<string, Message>;     // Keyed by message_id; preserves insertion order via separate array
  message_order: string[];            // FIFO render order
  coordinator_phase: Phase | null;
  workers: Map<string, WorkerStatus>; // Keyed by worker_id
  pending_permission: PermissionRequest | null; // Single-slot; input blocked while set
  crash: CrashNotice | null;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  chunks: string[];    // Accumulated deltas
  done: boolean;
  tool_calls: ToolCall[];
  tool_results: ToolResult[];
}
```

### 3.2 Reducers (one per IPC frame arm)

| Frame arm | Reducer effect |
|---|---|
| `user_input` | Append user `Message` to `messages` + `message_order` |
| `assistant_chunk` | Append `delta` to matching `Message.chunks`; set `done` if `done: true` |
| `tool_call` | Attach to the active assistant message's `tool_calls` |
| `tool_result` | Attach to matching call's `tool_results` |
| `coordinator_phase` | Overwrite `coordinator_phase` (phase is single-valued) |
| `worker_status` | Upsert into `workers` map |
| `permission_request` | Set `pending_permission`; UI blocks input |
| `permission_response` | Clear `pending_permission`; emit IPC frame |
| `session_event` | Trigger side-effect (load history for `resume`, clear store for `new`, etc.) |
| `error` | Append a synthetic assistant message with `<ErrorBanner />` |

### 3.3 Subscription

React components subscribe via `useSyncExternalStore(store.subscribe, store.getSnapshot)`. Only components whose selector result changes re-render. This is the key to FR-051's 100 ev/s soak target.

---

## 4. Upstream Component Map (lifted from `restored-src/`)

Traceability table for SC-9. Every file below carries the attribution header per FR-011.

### 4.1 Ink reconciler & layout (lift-as-is)

| TUI path | Upstream path | Reason |
|---|---|---|
| `tui/src/ink/reconciler.ts` | `restored-src/src/ink/reconciler.ts` | Reconciler core |
| `tui/src/ink/renderer.ts` | `restored-src/src/ink/renderer.ts` | Screen writer |
| `tui/src/ink/layout/*` | `restored-src/src/ink/layout/*` | Yoga layout bridge |
| `tui/src/ink/hooks/*` | `restored-src/src/ink/hooks/*` | Upstream internal hooks |

### 4.2 Commands (lift + subset)

| TUI path | Upstream path |
|---|---|
| `tui/src/commands/dispatcher.ts` | `restored-src/src/commands.ts` + `restored-src/src/commands/` registry shape |
| `tui/src/commands/save.ts` | `restored-src/src/commands/compact/` (pattern) |
| `tui/src/commands/sessions.ts` | `restored-src/src/commands/context/` (pattern) |
| `tui/src/commands/resume.ts` | (new, KOSMOS-original following registry shape) |
| `tui/src/commands/new.ts` | `restored-src/src/commands/clear` (pattern) |

### 4.3 Theme (lift-as-is)

| TUI path | Upstream path |
|---|---|
| `tui/src/theme/tokens.ts` | `restored-src/src/components/design-system/` tokens |
| `tui/src/theme/default.ts` / `dark.ts` / `light.ts` | `restored-src/src/components/design-system/themes/` |

### 4.4 Permission gauntlet (lift-as-is)

| TUI path | Upstream path |
|---|---|
| `tui/src/components/coordinator/PermissionGauntletModal.tsx` | `restored-src/src/components/ToolPermission*.tsx` |
| `tui/src/hooks/useCanUseTool.ts` | `restored-src/src/hooks/useCanUseTool.tsx` |
| `tui/src/components/coordinator/CoordinatorAgentStatus.tsx` | `restored-src/src/components/CoordinatorAgentStatus.tsx` |

### 4.5 Virtualization & rendering (lift-as-is)

| TUI path | Upstream path |
|---|---|
| `tui/src/components/conversation/VirtualizedList.tsx` | `restored-src/src/components/` (search term `Virtualized`) |
| `tui/src/store/session-store.ts` | `restored-src/src/store/` `useSyncExternalStore` pattern (≈35-line store) |
| `tui/src/components/conversation/StreamingMessage.tsx` | `restored-src/src/components/` streaming message pattern |

### 4.6 KOSMOS-original (no upstream)

| TUI path | Why original |
|---|---|
| `tui/src/ipc/bridge.ts` / `codec.ts` / `crash-detector.ts` | KOSMOS stdio protocol; Claude Code uses HTTP SSE |
| `tui/src/components/primitive/*` | KOSMOS 5-primitive renderers; no Claude Code analog |
| `tui/scripts/gen-ipc-types.ts` | Pydantic → TS code-gen; Claude Code uses hand-written TS types |
| `tui/scripts/diff-upstream.sh` | KOSMOS traceability tool |
| `src/kosmos/ipc/stdio.py` | Python multiplexer; Anthropic backend doesn't need this |

---

## 5. Environment Variables (registered in #468 registry)

| Name | Type | Default | Purpose |
|---|---|---|---|
| `KOSMOS_TUI_THEME` | `default \| dark \| light` | `default` | Theme selection (FR-039, FR-041) |
| `KOSMOS_TUI_LOG_LEVEL` | `DEBUG \| INFO \| WARN \| ERROR` | `WARN` | IPC frame logging verbosity (FR-010) |
| `KOSMOS_TUI_SUBSCRIBE_TIMEOUT_S` | int (seconds) | `120` | `subscribe` stream timeout (Edge Case) |
| `KOSMOS_TUI_IME_STRATEGY` | `fork \| readline` | (set by ADR) | Korean IME strategy selector (FR-014) |
| `KOSMOS_TUI_SOAK_EVENTS_PER_SEC` | int | `100` | Soak test rate (dev only; FR-007) |

All `KOSMOS_TUI_*` values MUST be redacted from crash notices per #468 guard pattern (FR-004).

---

## 6. State Transitions

### 6.1 Session lifecycle

```
          /new          /save          /resume <id>
  IDLE ---------> ACTIVE -------> ACTIVE --------> ACTIVE_RESTORED
                    |
                    | Ctrl-C / /exit
                    v
                CLOSING --(SIGTERM ≤3s)--> CLOSED --(backup SIGKILL)--> CLOSED
```

### 6.2 Permission gauntlet

```
  IDLE --(permission_request)--> BLOCKED --(citizen decision)--> IDLE
         ^                                                         |
         |                                                         | emit permission_response
         +---------------------------------------------------------+
```

### 6.3 Subscribe stream

```
  OPEN --(stream_event*)--> OPEN --(stream_closed: exhausted|revoked|timeout)--> CLOSED
         |
         | no event for KOSMOS_TUI_SUBSCRIBE_TIMEOUT_S
         v
      CLOSED (reason: "timeout")
```

---

## 7. Non-Goals (data model)

- No TUI-side session persistence (FR-131 / User Story 6). Sessions are backend-owned.
- No derived aggregates beyond the render-state store (no message search index, no vector cache, no local BM25).
- No client-side rate limiting of outbound frames — citizen input is naturally slow; backend polices.
