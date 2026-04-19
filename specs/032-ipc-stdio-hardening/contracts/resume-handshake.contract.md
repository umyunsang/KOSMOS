# Contract — Reconnect Handshake & At-least-once Replay

**Spec**: 032-ipc-stdio-hardening
**Scope**: FR-018..025 · US1 (P1, 세션 드롭 복구)
**Related entities**: `ResumeRequestFrame`, `ResumeResponseFrame`, `ResumeRejectedFrame`, `SessionRingBuffer`, `HeartbeatState`
**References**: MCP 2025-03-26 Streamable HTTP `Last-Event-ID` · LSP 3.17 JSON-RPC id correlation · Spec 027 `.consumed` marker

---

## 1. Happy path — successful resume

```
TUI                                              Backend
 │                                                 │
 │ ── stdio drop (EOF / pipe broken) ─────────────▶│
 │                                                 │ ring buffer: frames[..N] retained
 │ ── reconnect stdio ────────────────────────────▶│
 │                                                 │
 │ ResumeRequestFrame {                            │
 │   kind: "resume_request",                       │
 │   role: "tui",                                  │
 │   session_id: "s-abc",                          │
 │   correlation_id: "<uuidv7>",                   │
 │   frame_seq: 0,           // fresh counter      │
 │   last_seen_correlation_id: "<prev>",           │
 │   last_seen_frame_seq: 42,                      │
 │   tui_session_token: "<opaque>"                 │
 │ } ─────────────────────────────────────────────▶│
 │                                                 │ validate: session exists, token matches,
 │                                                 │           last_seen_frame_seq >= oldest_in_ring
 │                                                 │
 │ ◀──── ResumeResponseFrame {                     │
 │        kind: "resume_response",                 │
 │        role: "backend",                         │
 │        session_id: "s-abc",                     │
 │        correlation_id: "<uuidv7>",              │
 │        frame_seq: 43,                           │
 │        resumed_from_frame_seq: 43,              │
 │        replay_count: N - 42,                    │
 │        server_session_id: "s-abc",              │
 │        heartbeat_interval_ms: 30000,            │
 │        trailer: { final: true }                 │
 │      }                                          │
 │                                                 │
 │ ◀──── replayed frames [frame_seq 43..N]         │
 │        (at-least-once; duplicates possible)     │
 │                                                 │
 │ ── normal operation resumes ───────────────────▶│
```

**Key properties**:

1. TUI's `ResumeRequestFrame` resets its own outbound `frame_seq` to 0 (fresh post-reconnect counter).
2. Backend replay frames keep their ORIGINAL `frame_seq` values (≥ 43 in the diagram).
3. Backend's new post-replay frames continue from `N + 1`.
4. TUI de-dup on replay: skip any frame whose `(session_id, frame_seq)` pair it has already applied (tracked via local `applied_frame_seqs` set).

---

## 2. Rejection path — ring evicted

```
TUI                                              Backend
 │                                                 │
 │ ResumeRequestFrame { last_seen_frame_seq: 10 } ▶│
 │                                                 │ ring contains frames[200..455]
 │                                                 │ 10 < 200 → evicted
 │                                                 │
 │ ◀──── ResumeRejectedFrame {                     │
 │        kind: "resume_rejected",                 │
 │        role: "backend",                         │
 │        reason: "ring_evicted",                  │
 │        detail: "세션이 너무 오래 끊겨 이력이 소실되었습니다. 새 세션을 시작해 주세요.",
 │        trailer: { final: true }                 │
 │      }                                          │
 │                                                 │ backend tears down session state
 │ TUI starts new session                          │
```

**TUI behavior on rejection**: Render the `detail` string as a civic-friendly HUD, offer a "새 세션 시작" button, do NOT retry the same `last_seen_frame_seq` — that is fail-closed per Principle II.

---

## 3. Rejection reasons (normative)

| Reason                  | Trigger                                                                        | TUI recovery             |
| ----------------------- | ------------------------------------------------------------------------------ | ------------------------ |
| `ring_evicted`          | `last_seen_frame_seq < oldest frame in ring buffer`                             | Start new session.       |
| `session_unknown`       | `session_id` not found in backend session manager (process restart)            | Start new session.       |
| `token_mismatch`        | `tui_session_token` does not match backend-recorded token                       | Start new session; security event logged. |
| `protocol_incompatible` | TUI announces `version` not supported by backend                               | TUI must upgrade.        |
| `session_expired`       | Session idle beyond TTL (governed upstream; not set here)                      | Start new session.       |

---

## 4. At-least-once semantics

### 4.1 Why at-least-once (not exactly-once)

Exactly-once over stdio would require acknowledgements and two-phase delivery, which bloats the envelope and contradicts the NDJSON human-debuggable principle. Instead:

- **Backend**: Keeps the last 256 frames. On resume, replays everything after `last_seen_frame_seq`.
- **TUI**: De-duplicates by `(session_id, frame_seq)` applied-set.
- **Net effect**: At-least-once delivery + client-side idempotency = effectively exactly-once from the user's perspective, with an O(256) worst-case duplicate cost during a single drop.

### 4.2 Irreversible tool interaction

If a `tool_call` frame with `transaction_id` (irreversible tool) is in the replay range:

1. Backend replays the original `tool_call` frame.
2. Downstream `ToolExecutor` checks `TransactionLRU.get((session_id, transaction_id))`.
3. If present → returns cached response (Stripe-style 3-step idempotency).
4. If absent → executes normally.

This means duplicate civic submissions (FR-026..033) CANNOT happen even under adversarial network conditions, because the `TransactionLRU` lives across the reconnect.

---

## 5. Heartbeat ↔ resume coupling

- Heartbeat declares the peer dead after 45 s of silence.
- On dead-declare, the backend emits `ErrorFrame(code="peer_dead")` but KEEPS the `SessionRingBuffer` alive for `resume_grace_window_ms` (default 120000 = 2 min).
- Within the grace window, a successful `ResumeRequestFrame` cancels the teardown and resumes normally.
- After the grace window, the ring buffer is garbage-collected; any subsequent `ResumeRequestFrame` returns `session_unknown`.

---

## 6. Validation checklist

| Check                                                                                   | Enforced in                |
| --------------------------------------------------------------------------------------- | -------------------------- |
| `ResumeRequestFrame.role == "tui"`                                                      | schema `allOf`             |
| `ResumeResponseFrame.trailer.final == true`                                             | schema `allOf` + pydantic  |
| `ResumeRejectedFrame.trailer.final == true`                                             | schema `allOf` + pydantic  |
| `resumed_from_frame_seq` is strictly greater than client's `last_seen_frame_seq`        | backend handler            |
| `replay_count == count(frames where frame_seq > last_seen_frame_seq)`                    | backend handler            |
| `token_mismatch` audit event emitted as `ErrorFrame` with non-PII detail                 | backend handler            |
| TUI applied-set prevents double-application after duplicate delivery                    | TUI `envelope.ts` dispatch |

---

## 7. Test matrix (normative for WS4)

| Scenario                                             | Expected                                           |
| ---------------------------------------------------- | -------------------------------------------------- |
| Happy path, gap of 5 frames                          | `ResumeResponseFrame` + 5 replayed frames          |
| Resume with `last_seen_frame_seq = 0` (fresh TUI)    | Full buffer replay                                 |
| Resume beyond ring capacity                          | `ResumeRejectedFrame(reason="ring_evicted")`       |
| Resume with wrong token                              | `ResumeRejectedFrame(reason="token_mismatch")`    |
| Resume of unknown session                            | `ResumeRejectedFrame(reason="session_unknown")`    |
| Double resume (same `last_seen_frame_seq`)           | Idempotent — second response replays same window  |
| Resume during backpressure                           | Response completes before any pre-reconnect pause resumes |
| Heartbeat timeout → dead → resume within grace       | Session recovered                                  |
| Heartbeat timeout → dead → resume after grace        | `session_unknown`                                  |

---

## 8. Out of scope

- Cross-process session migration.
- Session persistence across backend restart.
- Recovery of in-flight tool executions (those replay as `tool_call` → `ToolExecutor` dedup).
- Partial payload recovery (if a streamed payload is mid-flight when drop occurs, the stream is restarted — TUI ignores orphan `payload_delta` frames without a preceding `payload_start` in the replay window).

All of the above are tracked in spec.md § Deferred to Future Work.
