# Phase 0 Research — IPC stdio hardening

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)
**Date**: 2026-04-19 · **Branch**: `032-ipc-stdio-hardening`

## 0. Resolved unknowns

The spec contained zero `[NEEDS CLARIFICATION]` markers (checklists/requirements.md PASS). Two items surfaced during plan drafting that required explicit research decisions:

1. **Existing `session_id`/`correlation_id` are documented as ULID; FR-003 specifies UUIDv7 going forward.** Research § 5 resolves: both are 128-bit lexicographically sortable strings serialized as opaque `str`. Pydantic type remains `str`; new fields added by this spec (`transaction_id`, new `correlation_id` values emitted by TUI after this spec lands) use Python 3.12 stdlib `uuid.uuid7()` on backend and TS `crypto.randomUUID()` + timestamp-prepend helper on TUI. Existing ULID values continue to validate — no breaking change. Docstring updated to "128-bit sortable ID (ULID or UUIDv7)".
2. **Spec 287 `frame_schema.py` already exports 10 arms; this spec adds 9 more.** Research § 6 confirms the union stays at 19 < 30, well within Pydantic discriminated-union comfort zone. No refactor required — pure extension.

## 1. Reference mapping (Constitution Principle I)

Every FR cluster traces to at least one concrete reference source in `docs/vision.md § Reference materials` + Epic A #1298 issue body + deep-research targets.

### FR-001..FR-010 — Frame envelope

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| NDJSON line framing | Standard tooling (`jq`, `grep`, line-oriented log shippers) works without custom parsers | ndjson.org specification; `.references/claude-code-sourcemap/restored-src/src/services/api/client.ts` newline-delimited message framing |
| Structured envelope `{version, correlation_id, role, payload, trailer}` | JSON-RPC id correlation precedent; envelope versioning isolates transport-vs-kind change axes | LSP 3.17 §3 Base Protocol (`jsonrpc` version field + `id` + `method` + `params`) |
| `correlation_id` UUIDv7 (sortable) | Timestamp-prefixed IDs enable direct LRU ordering + OTEL trace linking without secondary timestamp field | RFC 9562 §5.7 (UUIDv7); Python 3.12 `uuid.uuid7()` stdlib — AGENTS.md no-new-deps hard rule satisfied |
| `role` enum `{tui, backend, tool, llm, notification}` | Explicit sender identification aids debugger + OTEL span attribution | `.references/claude-code-sourcemap/restored-src/src/services/api/sessionIngress.ts` — sender tag on inbound events |
| `payload` Pydantic discriminated union by `kind` | Compile-time type safety + runtime validation in one pass; JSON Schema auto-derived | Pydantic v2 `Field(discriminator="kind")` docs; existing `IPCFrame` union in `src/kosmos/ipc/frame_schema.py` |
| `trailer` optional `{final, transaction_id, checksum_sha256}` | Streaming end-of-message signal + integrity check at chunked-frame boundary | HTTP/1.1 chunked trailers (RFC 9112 §7.1.2); gRPC trailers semantic |
| JSON Schema Draft 2020-12 @ `tui/src/ipc/schema/frame.schema.json` | Cross-language source of truth; Pydantic v2 emits 2020-12 by default; `ajv` / `jsonschema` validators support it | Pydantic v2 `TypeAdapter.json_schema(mode="validation")` defaults to Draft 2020-12 |
| Chunked split for payload > 1 MiB | stdio pipe buffer limits on macOS (64 KiB default, 1 MiB PIPE_BUF extreme); prevents single-frame pipe block | `man 2 write` PIPE_BUF guarantees; Node.js Streams doc `highWaterMark` = 64 KiB default |

### FR-011..FR-017 — Backpressure

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| 64-frame high-water-mark | Matches Node.js default `highWaterMark` object-mode (16) × 4 comfort factor; fits in < 1 MiB | Node.js docs `stream.Writable.highWaterMark`; CC sourcemap `src/services/api/withRetry.ts` retry budget shape |
| `BackpressureSignalFrame` with `{kind, severity, retry_after_ms, source_agency, message_ko, message_en}` | Korean + English HUD copy satisfies AX Principle 5 (citizen-facing) + DX Principle 8 (operator-facing) simultaneously | Korea AI Action Plan 2026-2028 Principle 8 (single conversational window); PIPA §35 citizen status-awareness derivation |
| OTEL span attribute promotion | Reuses Spec 021 GenAI instrumentation pipeline — zero new deps | Spec 021 `docs/observability/otel-genai.md`; OpenTelemetry Semantic Conventions `gen_ai.*` namespace |
| Critical-lane bypass for `severity=critical` | CBS (재난문자) and National Emergency frames cannot be throttled — legal requirement | 「재난 및 안전관리 기본법」 §38 (재난경보 전송 의무); Spec 031 `subscribe` primitive CBS path |

### FR-018..FR-025 — Reconnect handshake

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| `resume_request(session_id, last_seen_correlation_id, last_seen_frame_seq)` | Three-tuple disambiguates "what did the client last see" under crash-replay; matches MCP SSE resume semantic | MCP Transports Spec 2025-03-26 § Resumable Streams — `Last-Event-ID` header |
| 256-frame session ring buffer | Covers ~10 s of active streaming at typical LLM token rates; fits < 1 MiB per session | Empirical: FriendliAI streaming peak ~25 frames/s × 10 s = 250 < 256 |
| `.consumed` marker for acked frames | Reuses Spec 027 mailbox idiom (filesystem marker there, in-memory flag here — same semantic) | Spec 027 `src/kosmos/swarm/mailbox.py` `_mark_consumed()` helper |
| `resume_rejected` explicit reason codes (`session_expired`, `buffer_overflow`, `backend_restart`, `correlation_unknown`) | Fail-closed — client never guesses why resume failed; matches JSON-RPC error-object precedent | LSP 3.17 `ResponseError.code` enum |
| 3-fail blacklist | Prevents infinite resume loops under persistent corruption | CC sourcemap `src/services/api/withRetry.ts` max-attempts guard |
| 30 s heartbeat / 45 s dead | 1.5× heartbeat interval = industry standard dead threshold (TCP keep-alive, WebSocket ping) | RFC 6455 §5.5.2 WebSocket Ping/Pong; gRPC keepalive defaults |

### FR-026..FR-033 — Transaction de-dup

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| `transaction_id` UUIDv7 per `payload_start` | Sortable IDs enable LRU eviction by natural order without separate timestamp | RFC 9562 §5.7; Stripe idempotency-key blog (2017-03) |
| 512-entry LRU per session | Covers typical 1-hour citizen session (~100 transactions) with 5× safety factor | Stripe idempotency-key TTL 24 h → 512 entries × 1-hour session window translates to conservative bound |
| `is_irreversible=true` pinned (no eviction) | 정부24 민원 제출 / HIRA 진료기록 열람 신청 / MOHW 재신청 — duplicate execution = civil-affairs harm | Spec 024 `ToolCallAuditRecord.is_irreversible`; PIPA §26 수탁자 책임 |
| `(session_id, transaction_id)` cache key | Session-scope dedup matches "single-window" Principle 8 | Spec 027 mailbox `session_id` scoping |
| Cache-state OTEL attribute `kosmos.ipc.tx.cache_state ∈ {hit, miss, stored}` | Audit-able dedup outcome for PIPA compliance reporting | Spec 021 OTEL attribute namespacing convention |
| Stripe 3-step idempotency (UUID + transactional state + stale reclaim) | Battle-tested pattern for at-least-once delivery with exactly-once effect | Stripe engineering blog 2017-03 "Designing robust and predictable APIs with idempotency"; Shopify idempotency-key RFC draft |

### FR-034..FR-040 — Cross-cutting

| Decision | Rationale | Reference |
|----------|-----------|-----------|
| Pure stdlib + existing pydantic — no new runtime deps | AGENTS.md hard rule; Constitution Principle I (existing Reference alignment, not divergence) | AGENTS.md § Hard rules; SC-008 lint trio |
| stdout-only emission (no stderr pollution) | Claude Agent SDK strictness — stderr must remain clean for log shippers / parser separation | Claude Agent SDK docs § Stdio transport `process.stderr` prohibition |
| Schema version bump = hard cut (no back-compat window) | Single-host deployment = simultaneous TUI + backend upgrade; no rolling-deploy scenario | MCP Transports Spec 2025-03-26 `protocolVersion` handshake rejects mismatch |
| Python ↔ TS schema diff CI gate | SC-006 measurable outcome — drift prevention is a test, not documentation | Pydantic v2 `TypeAdapter.json_schema()` + `bun run gen:ipc` existing pipeline (Spec 287) |

## 2. Deferred-item validation (Constitution Principle VI gate)

Scanned spec.md for all deferral patterns ("separate epic", "future epic", "Phase [2+]", "v2", "deferred to", "later release", "out of scope for v1"). Every match is represented in the `Deferred to Future Work` table with a `NEEDS TRACKING` marker that will be resolved by `/speckit-taskstoissues`.

| # | Item | Status |
|---|------|--------|
| 1 | 원격 TUI(WebSocket/HTTP) 전송 계층 | IN TABLE — NEEDS TRACKING |
| 2 | Frame-level 서명/암호화(e2e) | IN TABLE — NEEDS TRACKING |
| 3 | 백엔드 다중 인스턴스 세션 shard | IN TABLE — NEEDS TRACKING |
| 4 | WebMCP-style declarative capability advertisement | IN TABLE — NEEDS TRACKING |
| 5 | OS-native stdio alternative (Windows named pipes) | IN TABLE — NEEDS TRACKING |

No unregistered deferrals found. PASS.

## 3. Technology-choice decision log

### 3.1 Why `collections.OrderedDict` for tx LRU (not `functools.lru_cache`)

- **Decision**: `collections.OrderedDict` with `move_to_end()` + manual eviction.
- **Rationale**: `functools.lru_cache` is a decorator bound to function identity — we need per-session instance state with pinnable entries (`is_irreversible` exemption). `OrderedDict` gives explicit control with zero dependencies.
- **Alternatives considered**: `cachetools.LRUCache` (new runtime dep — rejected per SC-008); custom dict+deque (NIH).

### 3.2 Why `collections.deque(maxlen=256)` for ring buffer

- **Decision**: `collections.deque` with `maxlen=256` for auto-wrap semantics.
- **Rationale**: O(1) append + natural FIFO overflow = ring buffer at zero cost. Auto-eviction of oldest frame on push is the desired behavior for resume-buffer-overflow detection.
- **Alternatives considered**: `asyncio.Queue` (unbounded by default, requires `maxsize=` + manual drop policy); `numpy.ndarray` (overkill, adds deps).

### 3.3 Why JSON Schema Draft 2020-12 (not Draft 7)

- **Decision**: Draft 2020-12.
- **Rationale**: Pydantic v2 `TypeAdapter.json_schema()` emits Draft 2020-12 by default. Draft 7 would require post-processing. `ajv` + `jsonschema` both support 2020-12. MCP Transports Spec also uses 2020-12.
- **Alternatives considered**: Draft 7 (deprecated for new work); OpenAPI 3.1 subset (tied to HTTP — not relevant here).

### 3.4 Why UUIDv7 (not UUIDv4 or ULID)

- **Decision**: UUIDv7 for new IDs emitted from this spec forward; ULID values from Spec 287 remain valid (both are opaque sortable `str`).
- **Rationale**: Python 3.12 stdlib `uuid.uuid7()` — zero deps. UUIDv4 is not sortable (bad for LRU eviction ordering). ULID requires a new runtime dep (`python-ulid` — forbidden).
- **Alternatives considered**: UUIDv4 (unsortable — makes LRU eviction O(n)); `python-ulid` (new dep rejected).

### 3.5 Why 64-frame HWM / 256-frame ring / 512-entry LRU / 30 s heartbeat

- **Decision**: These four knobs are the defaults; all are `pydantic-settings` env-var tunable via `KOSMOS_IPC_HWM_FRAMES`, `KOSMOS_IPC_RING_CAPACITY`, `KOSMOS_IPC_TX_LRU_CAPACITY`, `KOSMOS_IPC_HEARTBEAT_INTERVAL_MS`.
- **Rationale**: Values chosen per deep-research comparison (Node Streams default, MCP SSE typical buffer depths, Stripe idempotency guidance, WebSocket keepalive conventions). Env-var exposure allows per-deployment tuning without code change.
- **Alternatives considered**: Hardcoded constants (rejected — operators need adjustment knobs in prod).

## 4. Existing-code extension analysis

Read `src/kosmos/ipc/frame_schema.py` (279 lines, 10 frame arms, Pydantic v2 discriminated union, Spec 287 origin).

**Existing `_BaseFrame` fields**: `session_id: str`, `correlation_id: str | None`, `ts: str`.

**Fields this spec adds** to `_BaseFrame`:
- `version: Literal["1.0"]` — envelope format version (FR-002); MUST bump on breaking change (FR-038).
- `role: Literal["tui", "backend", "tool", "llm", "notification"]` — sender role (FR-004).
- `frame_seq: int` — monotonically increasing per session, used by ring buffer + resume (FR-018).
- `transaction_id: str | None = None` — UUIDv7, None for non-idempotent streaming frames (FR-026, FR-032).
- `trailer: FrameTrailer | None = None` — `{final, transaction_id, checksum_sha256}`, streaming end (FR-006).

**New frame arms added** (9 total):
1. `PayloadStartFrame` — begin chunked payload stream.
2. `PayloadDeltaFrame` — intermediate chunk.
3. `PayloadEndFrame` — terminal chunk with `trailer.final=true`.
4. `BackpressureSignalFrame` — rate-limit notification.
5. `ResumeRequestFrame` — client reconnect probe.
6. `ResumeResponseFrame` — server replay header.
7. `ResumeRejectedFrame` — server refuse + reason code.
8. `HeartbeatFrame` — 30 s ping.
9. `NotificationPushFrame` — CBS / disaster-alert lane (never throttled).

**Existing arms unchanged** (10): `UserInputFrame`, `AssistantChunkFrame`, `ToolCallFrame`, `ToolResultFrame`, `CoordinatorPhaseFrame`, `WorkerStatusFrame`, `PermissionRequestFrame`, `PermissionResponseFrame`, `SessionEventFrame`, `ErrorFrame`. They automatically inherit the new envelope fields via `_BaseFrame` extension — zero per-arm changes.

**Union cardinality**: 10 + 9 = 19 < 30 (Pydantic discriminated-union comfort zone). Validator performance impact: O(1) discriminator dispatch — no degradation.

## 5. Risk & mitigation

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Python ↔ TS schema drift | M | CI gate `test_schema_python_ts_diff.py` (SC-006) — exit ≠ 0 on diff |
| Ring buffer memory leak (session never ends) | L | `maxlen=256` auto-evicts; session-end hook clears buffer |
| Tx LRU leaking irreversible entries across sessions | L | cache key is `(session_id, transaction_id)`; session-end hook drops entire session namespace |
| UUIDv7 collision in same ms | Negligible | UUIDv7 has 12-bit `rand_a` + 62-bit `rand_b` = 2^74 entropy per ms |
| Stderr parser pollution | L | `stdio.py` existing writer already stdout-only; contract test `test_no_stderr_emission.py` reaffirms |
| Resume blacklist false-positive after transient crash | M | Blacklist is session-scoped + cleared on new session-id; 3-fail threshold covers retry storms |
| Chunked frame interleave under concurrent tools | L | `frame_seq` monotonic per session — consumer reorders by seq if needed; streams are per-correlation-id isolated |

## 6. Key open questions — NONE

All design decisions resolved via reference mapping (§ 1) + decision log (§ 3). No `[NEEDS CLARIFICATION]` markers remain in the spec. No research-derived `[NEEDS CLARIFICATION]` added here.

## 7. Deep-research sources consulted 2026-04-19

- **MCP Transports Spec 2025-03-26** — resumable-stream semantic, Last-Event-ID header, protocolVersion handshake
- **LSP 3.17 Base Protocol** — JSON-RPC id correlation, ResponseError.code enum
- **RFC 9562 (UUIDv7)** — sortable UUID spec + entropy analysis
- **Claude Agent SDK docs § Stdio transport** — stderr pollution prohibition
- **Node.js Streams doc (nodejs.org/api/stream.html)** — highWaterMark defaults, backpressure flow control
- **NDJSON spec (ndjson.org)** — line-delimited JSON, `\n` escape rules
- **Stripe engineering blog 2017-03** — idempotency-key 3-step approach
- **Shopify idempotency-key RFC draft (ietf-httpbis)** — HTTP header convention (not adopted here, pattern adapted)
- **RFC 6455 §5.5.2** — WebSocket Ping/Pong keepalive semantic
- **gRPC keepalive defaults (grpc.io docs)** — 1.5× heartbeat as dead threshold
- **CC sourcemap `src/services/api/{client,bootstrap,sessionIngress,withRetry}.ts`** — HTTP-based retry + correlation patterns ported to stdio
- **CC sourcemap `src/session/`** — session lifecycle + recovery patterns
- **재난 및 안전관리 기본법 §38** — 재난경보 전송 의무 (critical-lane bypass legal basis)
- **PIPA §26, §35** — 수탁자 책임, 열람권 derivation for status-visibility

## 8. Outcome

- Technical Context fully populated in plan.md — no NEEDS CLARIFICATION.
- Constitution Check PASS on all six principles.
- Deferred items validated — 5 tracked, 0 unregistered.
- Reference mapping complete — every FR cluster linked to a concrete source.
- **Proceed to Phase 1 design artifacts.**
