# Data Model — IPC stdio hardening (Spec 032)

**Feature branch**: `032-ipc-stdio-hardening`
**Plan**: [plan.md](./plan.md)
**Research**: [research.md](./research.md)
**Spec**: [spec.md](./spec.md)

> **Design posture** — This spec EXTENDS `src/kosmos/ipc/frame_schema.py`. Every entity below is either (a) a new `_BaseFrame` field shared by all 19 arms, (b) a brand-new Pydantic v2 arm joining the `IPCFrame` discriminated union, or (c) a session-lifetime in-memory structure (no ORM, no persistence).

---

## 1. FrameEnvelope (extension of `_BaseFrame`)

`FrameEnvelope` is not a standalone model — it is the **shared field set** that `_BaseFrame` will carry after this spec lands. Every frame arm (existing 10 + new 9) inherits these fields.

### 1.1 Fields (post-extension `_BaseFrame`)

| Field                 | Type                                                                                              | Cardinality | Description                                                                                                                             | Source |
| --------------------- | ------------------------------------------------------------------------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| `session_id`          | `str`                                                                                             | required    | Existing. Opaque session identifier. Unchanged.                                                                                         | existing |
| `correlation_id`      | `str`                                                                                             | required    | **CHANGE**: now non-optional. UUIDv7 string (new emissions); ULID accepted for back-compat. Reader treats as opaque 128-bit sortable ID. | FR-003 |
| `ts`                  | `str`                                                                                             | required    | Existing. ISO-8601 UTC with sub-ms. Unchanged.                                                                                          | existing |
| `version`             | `Literal["1.0"]`                                                                                   | required    | Envelope version. Hard-fail on mismatch.                                                                                                 | FR-001 |
| `role`                | `Literal["tui", "backend", "tool", "llm", "notification"]`                                         | required    | Origin role. Validated against `kind` ↔ `role` allow-list.                                                                              | FR-004 |
| `frame_seq`           | `int`                                                                                             | required    | Per-session monotonic sequence. `ge=0`. Gap detection uses this.                                                                         | FR-005, FR-018 |
| `transaction_id`      | `str \| None`                                                                                     | optional    | UUIDv7. Populated for idempotent state-change frames only. `None` for streaming chunks.                                                  | FR-026, FR-027 |
| `trailer`             | `FrameTrailer \| None`                                                                            | optional    | Completion/validation metadata. Populated on terminal frames (e.g., `payload_end`, `tool_result`).                                      | FR-006 |

### 1.2 `FrameTrailer` sub-model

| Field              | Type          | Description                                                                          |
| ------------------ | ------------- | ------------------------------------------------------------------------------------ |
| `final`            | `bool`        | True when this frame terminates a logical payload/stream.                            |
| `transaction_id`   | `str \| None` | Mirror of envelope `transaction_id` for trailer-only consumers (optional convenience). |
| `checksum_sha256`  | `str \| None` | Hex SHA-256 of the concatenated `payload` bytes for streamed payloads. Optional.     |

### 1.3 Pydantic ConfigDict

```
ConfigDict(frozen=True, extra="forbid", populate_by_name=True)
```

`extra="forbid"` applies to the envelope AND every arm — unknown fields fail-closed.

### 1.4 Validation invariants (cross-field)

| ID  | Invariant                                                                                                  | Enforced by                                                  |
| --- | ---------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------ |
| E1  | `version == "1.0"` else reject.                                                                            | `Literal` type                                               |
| E2  | `frame_seq` monotonic per `session_id`; gaps trigger resume handshake.                                     | `RingBuffer.append()` runtime check + downstream gap detector |
| E3  | `role` ↔ `kind` allow-list (e.g., `kind="tool_call"` → `role ∈ {"backend","tool"}`).                       | `@model_validator(mode="after")` on `_BaseFrame`             |
| E4  | `transaction_id` required for `kind ∈ {"tool_call", "permission_response", "payload_end"}` when `role="tool"` AND caller declared `is_irreversible=true`. | `@model_validator(mode="after")` on `_BaseFrame`             |
| E5  | `correlation_id` MUST be non-empty string; emitter SHOULD use UUIDv7.                                       | `Field(min_length=1)`                                        |
| E6  | `trailer.final=true` only on terminal-capable kinds (`payload_end`, `tool_result`, `resume_response`, `resume_rejected`, `error`). | `@model_validator(mode="after")` on `_BaseFrame`             |

---

## 2. New frame arms (9 additions to `IPCFrame` union)

Each arm inherits envelope fields from `_BaseFrame`. Only arm-specific fields are shown.

### 2.1 `PayloadStartFrame` — `kind="payload_start"`

Begins a streamed payload (assistant output, tool result chunking). Sender MUST follow with ≥1 `payload_delta` and exactly one `payload_end`.

| Field            | Type                   | Description                                                       |
| ---------------- | ---------------------- | ----------------------------------------------------------------- |
| `content_type`   | `Literal["text/markdown", "application/json", "text/plain"]` | Payload MIME type.                      |
| `estimated_bytes`| `int \| None`          | Optional size hint for HUD progress bars. `ge=0`.                 |

**role allow-list**: `backend`, `tool`, `llm`

### 2.2 `PayloadDeltaFrame` — `kind="payload_delta"`

One chunk of a streamed payload.

| Field         | Type   | Description                                                                                |
| ------------- | ------ | ------------------------------------------------------------------------------------------ |
| `delta_seq`   | `int`  | Monotonic within the payload (first delta = 0). `ge=0`.                                    |
| `payload`     | `str`  | UTF-8 text. If content-type is `application/json`, this is a JSON-encoded fragment string. |

**role allow-list**: `backend`, `tool`, `llm`

### 2.3 `PayloadEndFrame` — `kind="payload_end"`

Terminates a streamed payload. MUST carry a `trailer` with `final=true`.

| Field                 | Type                        | Description                                            |
| --------------------- | --------------------------- | ------------------------------------------------------ |
| `delta_count`         | `int`                       | Total number of `payload_delta` frames emitted. `ge=0`. |
| `status`              | `Literal["ok", "aborted"]`  | Terminal disposition.                                  |

**role allow-list**: `backend`, `tool`, `llm`

### 2.4 `BackpressureSignalFrame` — `kind="backpressure"`

Emitted when the outgoing queue crosses the high-water mark (64 frames) or a 429 upstream condition is detected.

| Field                 | Type                                            | Description                                                                    |
| --------------------- | ----------------------------------------------- | ------------------------------------------------------------------------------ |
| `signal`              | `Literal["pause", "resume", "throttle"]`        | Reader action. `pause` = stop emitting; `resume` = clear; `throttle` = slow down. |
| `source`              | `Literal["tui_reader", "backend_writer", "upstream_429"]` | Origin of the signal.                                              |
| `queue_depth`         | `int`                                           | Current outbound queue size. `ge=0`.                                           |
| `hwm`                 | `int`                                           | High-water mark threshold in effect (default 64). `ge=1`.                      |
| `retry_after_ms`      | `int \| None`                                   | For `throttle` sourced from `upstream_429`; reflects `Retry-After`. `ge=0`.     |
| `hud_copy_ko`         | `str`                                           | Korean HUD copy (civic-facing). Examples: "부처 API가 혼잡합니다. 15초 후 자동 재시도". |
| `hud_copy_en`         | `str`                                           | English HUD copy (dev-facing).                                                 |

**role allow-list**: `tui` (tui_reader), `backend` (backend_writer, upstream_429)

### 2.5 `ResumeRequestFrame` — `kind="resume_request"`

Sent by the reconnecting TUI after a stdio drop.

| Field                      | Type          | Description                                                                  |
| -------------------------- | ------------- | ---------------------------------------------------------------------------- |
| `last_seen_correlation_id` | `str \| None` | Last `correlation_id` the TUI successfully applied. `None` if no prior frame. |
| `last_seen_frame_seq`      | `int \| None` | Last `frame_seq` applied. `None` if none.                                    |
| `tui_session_token`        | `str`         | TUI-local session token for authenticity binding. `min_length=1`.            |

**role allow-list**: `tui`

### 2.6 `ResumeResponseFrame` — `kind="resume_response"`

Backend accepts the resume. Must be followed by replay of frames with `frame_seq > last_seen_frame_seq` from the ring buffer.

| Field                   | Type                        | Description                                                              |
| ----------------------- | --------------------------- | ------------------------------------------------------------------------ |
| `resumed_from_frame_seq`| `int`                       | Inclusive lower bound of frames that will be replayed. `ge=0`.           |
| `replay_count`          | `int`                       | Total frames the backend will replay. `ge=0`. Bounded by ring buffer size. |
| `server_session_id`     | `str`                       | Backend-assigned session id the TUI should use going forward.            |
| `heartbeat_interval_ms` | `int`                       | Negotiated heartbeat cadence (default 30000). `ge=1000`.                 |

**role allow-list**: `backend`

**Trailer**: `trailer.final=true` MUST be set.

### 2.7 `ResumeRejectedFrame` — `kind="resume_rejected"`

Backend cannot honor the resume request.

| Field     | Type                                                                                                     | Description                                    |
| --------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| `reason`  | `Literal["ring_evicted", "session_unknown", "token_mismatch", "protocol_incompatible", "session_expired"]` | Machine-readable reason code.                 |
| `detail`  | `str`                                                                                                    | Human-readable Korean/English detail for HUD. |

**role allow-list**: `backend`

**Trailer**: `trailer.final=true` MUST be set. Session is unrecoverable — TUI must start a new session.

### 2.8 `HeartbeatFrame` — `kind="heartbeat"`

Emitted every 30 s (default) by both sides to prove liveness.

| Field            | Type                           | Description                                                     |
| ---------------- | ------------------------------ | --------------------------------------------------------------- |
| `direction`      | `Literal["ping", "pong"]`      | `ping` from sender, `pong` from receiver.                       |
| `peer_frame_seq` | `int`                          | Sender's current outbound `frame_seq` high-water. `ge=0`.        |

**role allow-list**: `tui`, `backend`

**Note**: Heartbeat frames DO NOT increment `frame_seq` — they use a dedicated counter. This keeps ring-buffer economy tight (256 frames ≈ user-visible history, not liveness chatter).

### 2.9 `NotificationPushFrame` — `kind="notification_push"`

Push from subscription surfaces (Spec 031 SubscriptionHandle) — e.g., 재난문자, RSS. Carried over the same stdio channel to keep a single correlation plane.

| Field               | Type                                                                     | Description                                                   |
| ------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------- |
| `subscription_id`   | `str`                                                                    | Handle from Spec 031 `subscribe` registration.                |
| `adapter_id`        | `str`                                                                    | e.g., `disaster_alert_cbs_push`, `rss_newsroom_subscribe`.    |
| `event_guid`        | `str`                                                                    | RSS `guid` or CBS event hash for duplicate suppression.       |
| `payload_content_type` | `Literal["text/plain", "application/json"]`                           | Inline payload MIME.                                          |
| `payload`           | `str`                                                                    | Inline notification content (Korean for civic users).        |

**role allow-list**: `notification`

---

## 3. SessionRingBuffer (in-memory, session-scoped)

### 3.1 Purpose

Holds the last 256 outbound frames per `session_id` so the backend can replay on resume (FR-019, FR-020). Not persistent — dies with the session.

### 3.2 Shape

| Attribute          | Type                                          | Description                                                                   |
| ------------------ | --------------------------------------------- | ----------------------------------------------------------------------------- |
| `session_id`       | `str`                                         | Key.                                                                          |
| `frames`           | `collections.deque[IPCFrame]` `maxlen=256`    | FIFO eviction. Older frames silently dropped beyond 256.                      |
| `frame_seq_counter`| `int`                                         | Monotonic source of envelope `frame_seq`. Incremented on `append()`.          |
| `consumed_markers` | `set[int]`                                    | Set of `frame_seq` values the peer has acknowledged (via resume handshake).   |
| `last_append_ts`   | `datetime`                                    | For idle-session cleanup.                                                     |

### 3.3 Operations

| Op                                                  | Return                    | Notes                                                                             |
| --------------------------------------------------- | ------------------------- | --------------------------------------------------------------------------------- |
| `append(frame) -> IPCFrame`                         | `IPCFrame` with `frame_seq` set | Stamps `frame_seq` from counter, pushes to deque.                               |
| `replay_since(last_seen_frame_seq) -> list[IPCFrame]` | `list[IPCFrame]`        | Returns frames with `frame_seq > last_seen_frame_seq` still in the buffer.        |
| `ring_evicted(last_seen_frame_seq) -> bool`          | `bool`                    | True when `last_seen_frame_seq < oldest_in_buffer` → resume must reject.          |
| `mark_consumed(frame_seq) -> None`                   | `None`                    | Adds to `consumed_markers` (Spec 027 `.consumed` marker idiom, in-memory).        |

### 3.4 Backpressure coupling

When `len(frames) / maxlen >= 0.25` (64-frame threshold), the writer emits a `BackpressureSignalFrame(signal="pause")`. When depth drops below 32 (50% of HWM), writer emits `signal="resume"`.

### 3.5 Out-of-scope

- Persistence to disk (explicitly deferred per spec).
- Cross-session replay (each session owns exactly one ring).
- Compaction or summarization (Spec 030 Session Compaction governs that plane, not this one).

---

## 4. TransactionLRU (in-memory, process-scoped)

### 4.1 Purpose

Prevents double-submission of irreversible actions (FR-026..033). Key = `(session_id, transaction_id)`; value = the last-known outcome so repeat submissions short-circuit to the cached response.

### 4.2 Shape

| Attribute           | Type                                              | Description                                                        |
| ------------------- | ------------------------------------------------- | ------------------------------------------------------------------ |
| `cache`             | `collections.OrderedDict[tuple[str, str], TxEntry]` | Capacity 512; insertion order = eviction order.                  |
| `pinned_keys`       | `set[tuple[str, str]]`                            | Keys for `is_irreversible=true` tools. NEVER evicted regardless of LRU. |
| `capacity`          | `int`                                             | Default 512 (from `KOSMOS_IPC_TX_CACHE_CAPACITY`). `ge=1`.         |

### 4.3 `TxEntry` sub-shape

| Field               | Type            | Description                                                       |
| ------------------- | --------------- | ----------------------------------------------------------------- |
| `session_id`        | `str`           | Session scope.                                                    |
| `transaction_id`    | `str`           | UUIDv7.                                                           |
| `tool_id`           | `str`           | Adapter identifier (Spec 024 AdapterRegistration).                |
| `is_irreversible`   | `bool`          | If True, entry is pinned (never evicted).                         |
| `first_seen_ts`     | `datetime`      | Write time.                                                       |
| `cached_response`   | `dict`          | Serialized tool response for replay.                              |
| `correlation_id`    | `str`           | Originating correlation for audit.                                |

### 4.4 Operations

| Op                                                       | Return                          | Notes                                                                              |
| -------------------------------------------------------- | ------------------------------- | ---------------------------------------------------------------------------------- |
| `get(session_id, transaction_id) -> TxEntry \| None`     | `TxEntry \| None`               | Read-through; does NOT touch LRU order (pure lookup).                              |
| `record(entry: TxEntry) -> None`                         | `None`                          | Insert; evicts oldest non-pinned if over capacity.                                 |
| `is_duplicate(session_id, tx_id) -> bool`                | `bool`                          | Sugar over `get(..) is not None`.                                                  |
| `pin(key) / unpin(key)`                                  | `None`                          | Explicit pin management (irreversible tools auto-pin on record).                   |

### 4.5 Validation invariants

| ID  | Invariant                                                                                           |
| --- | --------------------------------------------------------------------------------------------------- |
| T1  | Key tuple elements are non-empty strings.                                                           |
| T2  | `is_irreversible=true` entries MUST be in `pinned_keys`.                                            |
| T3  | `cache` size ≤ `capacity + len(pinned_keys)` at all times.                                          |
| T4  | Eviction order: `OrderedDict` FIFO, skipping `pinned_keys`.                                         |
| T5  | `cached_response` must be JSON-serializable (pydantic `.model_dump()` result).                      |

### 4.6 Coupling with Spec 024 audit

When `record()` fires, the caller (`ToolExecutor`) also writes a `ToolCallAuditRecord` with the same `correlation_id` + `transaction_id`. The LRU does not own the audit — it only stores the cached response for dedup short-circuit.

---

## 5. HeartbeatState (in-memory, per-channel)

### 5.1 Purpose

Detects dead peers (FR-039..040).

### 5.2 Shape

| Attribute               | Type        | Description                                                 |
| ----------------------- | ----------- | ----------------------------------------------------------- |
| `session_id`            | `str`       | Key.                                                        |
| `last_peer_ping_ts`     | `datetime`  | Last time we received a `heartbeat(direction="ping")` from the peer. |
| `last_peer_pong_ts`     | `datetime`  | Last time the peer answered our ping.                       |
| `ping_interval_ms`      | `int`       | Local ping cadence (default 30000).                         |
| `dead_threshold_ms`     | `int`       | Declare dead after this idle (default 45000).               |
| `dead_declared`         | `bool`      | Latched flag; once True, emits a final `error` frame.       |

### 5.3 Operations

| Op                             | Return   | Notes                                                                |
| ------------------------------ | -------- | -------------------------------------------------------------------- |
| `record_ping(ts)`              | `None`   | Update `last_peer_ping_ts` and schedule pong.                        |
| `record_pong(ts)`              | `None`   | Update `last_peer_pong_ts`.                                          |
| `tick(now) -> bool`            | `bool`   | Called every second; returns True if peer crossed dead threshold.    |

---

## 6. Relationships

```
SessionRingBuffer (1) ──owns──▶ (N) IPCFrame (extended envelope)
TransactionLRU    (1) ──keys by── (session_id, transaction_id) on irreversible IPCFrame
HeartbeatState    (1) ──per── session_id ──coexists with── SessionRingBuffer
```

All three structures are **session-scoped in-memory**; a `SessionManager` holds `dict[session_id, SessionRuntime]` where `SessionRuntime = (SessionRingBuffer, HeartbeatState)`. `TransactionLRU` is process-global (one instance, keyed by composite).

---

## 7. Lifecycle

### 7.1 Session boot

1. Backend allocates `SessionRingBuffer(session_id, frame_seq_counter=0)`.
2. Backend allocates `HeartbeatState(session_id, ping_interval_ms=30000)`.
3. Process-global `TransactionLRU` already exists (module-level singleton).

### 7.2 Normal frame emission

1. Writer builds the Pydantic arm (`UserInputFrame(...)`, etc.).
2. Writer calls `ring.append(frame)` — stamps `frame_seq`.
3. Writer serializes via `frame.model_dump_json()` with NDJSON line terminator.
4. If `ring` depth ≥ HWM → emit `BackpressureSignalFrame(signal="pause")` before the actual frame.
5. Post-emit: if the frame carries `transaction_id` AND originating tool has `is_irreversible=true` → `TransactionLRU.record(TxEntry(...))` + pin.

### 7.3 Resume

1. TUI reconnects → emits `ResumeRequestFrame(last_seen_frame_seq=N, ...)`.
2. Backend: if `ring.ring_evicted(N)` → emit `ResumeRejectedFrame(reason="ring_evicted", ...)`.
3. Otherwise: emit `ResumeResponseFrame(resumed_from_frame_seq=N+1, replay_count=len(replay), ...)` + replay frames.

### 7.4 Heartbeat

- Every `ping_interval_ms`: emit `HeartbeatFrame(direction="ping", peer_frame_seq=ring.frame_seq_counter)`.
- On receive `ping`: reply with `HeartbeatFrame(direction="pong", ...)`.
- If `heartbeat.tick(now)` returns True → emit `ErrorFrame(code="peer_dead", ...)` and tear down the session (ring buffer persists for a grace window for TUI reconnect).

### 7.5 Session termination

1. `ErrorFrame` or `ResumeRejectedFrame(reason="session_expired")` is the last frame.
2. Backend drops the `SessionRingBuffer` + `HeartbeatState` entries.
3. `TransactionLRU` entries for `is_irreversible=true` tools REMAIN pinned (cross-session protection against civic double-submit).

---

## 8. State transitions

### 8.1 FrameEnvelope — not stateful (value type).

### 8.2 SessionRingBuffer

```
[empty]
   │ append()
   ▼
[active, depth < 32]
   │ append() while depth reaches 64
   ▼
[backpressured, depth ≥ 64] ──emits pause──▶ peer halts writes
   │ peer pauses, reader drains, depth < 32
   ▼
[active, depth < 32] ──emits resume──▶ peer writes again
```

### 8.3 HeartbeatState

```
[healthy] ──no ping/pong for dead_threshold_ms──▶ [dead_declared]
```

Once `dead_declared=true` it is latched; session must reboot.

### 8.4 TransactionLRU entry

```
[absent] ──record()──▶ [present, unpinned]        [if is_irreversible=False]
[absent] ──record()──▶ [present, pinned]          [if is_irreversible=True]
[present, unpinned] ──evicted by new record──▶ [absent]
[present, pinned]   ──never evicted──▶ [present, pinned]   (until session mgr explicit purge)
```

---

## 9. JSON Schema surface

The JSON Schema generated from `ipc_frame_json_schema()` after this spec lands MUST:

1. Enumerate all 19 frame `kind` values.
2. Include `trailer` as an optional `object` with `final: boolean`.
3. Include `version: const "1.0"`.
4. Include `role: enum [...]`.
5. Include `frame_seq: integer, minimum: 0`.

File: `tui/src/ipc/schema/frame.schema.json` (JSON Schema Draft 2020-12). Generation is deterministic → byte-equal rebuilds verified in test.

---

## 10. Appendix — Fields NOT in this spec

The following fields are deliberately absent to keep the envelope minimal:

- `auth_token` / `signature` — transport is local stdio; AGENTS.md hard rule on `KOSMOS_*` secrets config applies upstream.
- `priority` / `qos` — stdio is FIFO; priority lanes are out of scope.
- `encryption` — stdio is process-local; OS handles isolation.
- `compression` — NDJSON stays human-debuggable; compression is out of scope.

These are listed in spec.md § Out of Scope.
