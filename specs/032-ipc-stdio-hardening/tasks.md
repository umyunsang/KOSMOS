---
description: "Task list for Spec 032 — IPC stdio hardening"
---

# Tasks: IPC stdio hardening (frame envelope · backpressure · reconnect · at-least-once replay)

**Input**: Design documents from `/specs/032-ipc-stdio-hardening/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓, contracts/ ✓, quickstart.md ✓
**Parent Epic**: #1298 · 4-workstream parallel factoring (WS1 foundational · WS2/3/4 concurrent).
**Budget**: 61 tasks emitted (≤ 90 Sub-Issue API cap per `feedback_subissue_100_cap` memory). 29-task headroom for mid-cycle additions.

**Tests**: Required per Constitution Principle III (Pydantic v2 strict) + FR-040 (Python↔TS schema parity) + quickstart scenarios A–E.

## Format: `- [ ] [TaskID] [P?] [Story?] Description with file path`

- **[P]**: Parallel-safe across workstreams (different files, no incomplete-task deps).
- **[Story]**: US1/US2/US3/US4 from spec.md.
- All paths absolute from repo root.

## Path Conventions

- **Backend**: `src/kosmos/ipc/*.py`, `tests/ipc/*.py`
- **TUI**: `tui/src/ipc/*.ts[x]`, `tui/tests/ipc/*.test.ts`
- **Schema**: `tui/src/ipc/schema/frame.schema.json` (normative JSON Schema 2020-12)
- **Demo harnesses**: `src/kosmos/ipc/demo/`, `tui/src/ipc/demo/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish lint guards, OTEL attribute constants, and test scaffolding shared by all four workstreams.

- [X] T001 [P] Create `tests/ipc/conftest.py` with shared fixtures (fake clock, UUIDv7 factory, NDJSON capture buffer) — **no production code changes**. Load env overrides for `KOSMOS_IPC_RING_SIZE`, `KOSMOS_IPC_TX_CACHE_CAPACITY`, `KOSMOS_IPC_HEARTBEAT_INTERVAL_MS`, `KOSMOS_IPC_HEARTBEAT_DEAD_MS`.
- [X] T002 [P] Add OTEL attribute-key constants to `src/kosmos/ipc/otel_constants.py`: `KOSMOS_IPC_CORRELATION_ID`, `KOSMOS_IPC_TRANSACTION_ID`, `KOSMOS_IPC_TX_CACHE_STATE`, `KOSMOS_IPC_BACKPRESSURE_KIND`, `KOSMOS_IPC_BACKPRESSURE_SEVERITY`, `KOSMOS_IPC_BACKPRESSURE_SOURCE`, `KOSMOS_IPC_SCHEMA_HASH`, `KOSMOS_IPC_REPLAYED`.
- [X] T003 [P] Create `tui/tests/ipc/fixtures/` and seed it with frozen sample NDJSON fixtures (`envelope.v1.happy.ndjson`, `backpressure.throttle.ndjson`, `resume.response.ndjson`) for TUI unit tests.

**Checkpoint**: Setup complete — all four workstreams can now author code against shared fixtures and constants.

---

## Phase 2: Foundational — WS1 Envelope + Schema + Entity Substrates (Blocking Prerequisites)

**Purpose**: Extend `_BaseFrame`, add 9 new Pydantic arms, emit normative JSON Schema, publish TypeScript mirror, implement `SessionRingBuffer` / `TransactionLRU` / `HeartbeatState` entity substrates. **Blocks US1/US2/US3/US4**.

**⚠️ CRITICAL**: No user-story phase may start until T020 green.

- [X] T004 Extend `_BaseFrame` in `src/kosmos/ipc/frame_schema.py` with 5 new fields (`version: Literal["1.0"]`, `role: Literal["tui","backend","tool","llm","notification"]`, `frame_seq: NonNegativeInt`, `transaction_id: str | None`, `trailer: FrameTrailer | None`) + `FrameTrailer` model (`final: bool`, `transaction_id?`, `checksum_sha256?`). Preserve `ConfigDict(frozen=True, extra="forbid", populate_by_name=True)`.
- [X] T005 [P] Add `PayloadStartFrame`, `PayloadDeltaFrame`, `PayloadEndFrame` arms in `src/kosmos/ipc/frame_schema.py` (content_type, delta_seq, delta_count, status fields per data-model.md § 4).
- [X] T006 [P] Add `BackpressureSignalFrame` arm in `src/kosmos/ipc/frame_schema.py` (signal/source enums, queue_depth, hwm, retry_after_ms, hud_copy_ko/en with `min_length=1`).
- [X] T007 [P] Add `ResumeRequestFrame` + `ResumeResponseFrame` + `ResumeRejectedFrame` arms in `src/kosmos/ipc/frame_schema.py` (last_seen_correlation_id, last_seen_frame_seq, tui_session_token, resumed_from_frame_seq, replay_count, heartbeat_interval_ms, 5-value `reason` enum).
- [X] T008 [P] Add `HeartbeatFrame` arm in `src/kosmos/ipc/frame_schema.py` (direction=ping|pong, peer_frame_seq).
- [X] T009 [P] Add `NotificationPushFrame` arm in `src/kosmos/ipc/frame_schema.py` (subscription_id, adapter_id, event_guid, payload_content_type, payload).
- [X] T010 Update `IPCFrame = Annotated[Union[...], Field(discriminator="kind")]` in `src/kosmos/ipc/frame_schema.py` to include all 19 kinds; enforce role↔kind allow-list invariant (E3) in a shared `@model_validator(mode="after")` on `_BaseFrame`.
- [X] T011 Enforce cross-field invariants E1–E6 in `src/kosmos/ipc/frame_schema.py`: version hard-fail (E1), frame_seq non-negative (E2), role↔kind allow-list (E3), `transaction_id` presence ⇔ `{tool_call, permission_response, payload_end}` AND irreversible (E4), correlation_id min_length=1 (E5), `trailer.final=true` only on terminal kinds (E6).
- [X] T012 Implement `src/kosmos/ipc/envelope.py` emit/parse helpers: `emit_ndjson(frame) -> str`, `parse_ndjson_line(line) -> IPCFrame`, `escape_newlines_in_payload(obj) -> obj`; fail-closed on malformed lines (FR-035).
- [X] T013 [P] Implement `SessionRingBuffer` in `src/kosmos/ipc/ring_buffer.py` using `collections.deque(maxlen=256)` + `.consumed` marker set per data-model.md § 5.1 (`append`, `replay_since`, `mark_consumed`, `ring_evicted` ops). **WS4 consumes; staged in Foundational to unblock downstream workstreams.**
- [X] T014 [P] Implement `TransactionLRU` in `src/kosmos/ipc/tx_cache.py` using `collections.OrderedDict` (capacity 512) + `pinned_keys: set` for `is_irreversible=true`; `get`, `record`, `is_duplicate`, `pin`, `unpin`, `evict_oldest_non_pinned` ops (T1–T5 invariants).
- [X] T015 [P] Implement `HeartbeatState` in `src/kosmos/ipc/heartbeat.py` with `record_ping`, `record_pong`, `tick(now) -> DeadlineState`; 30s interval / 45s dead / 120s resume-grace-window defaults via `pydantic-settings`.
- [X] T016 Emit JSON Schema Draft 2020-12 from Python: add `ipc_frame_json_schema()` function in `src/kosmos/ipc/frame_schema.py` that dumps the 19-kind discriminated-union schema + `allOf` role↔kind constraints; commit output to `tui/src/ipc/schema/frame.schema.json`.
- [X] T017 Regenerate TypeScript types at `tui/src/ipc/frames.generated.ts` from `tui/src/ipc/schema/frame.schema.json` (use existing `bun run codegen` pipeline from Spec 287; extend enum export for 9 new kinds).
- [X] T018 Extend `tui/src/ipc/envelope.ts` and `tui/src/ipc/codec.ts` with NDJSON encode/decode that parses all 19 kinds, kind-narrowed type guards, and newline-escape invariant.
- [X] T019 [P] Author `tests/ipc/test_envelope_roundtrip.py` covering all 19 kinds — serialize via Pydantic, parse via envelope helpers, assert byte-equal round-trip + invariants E1–E6.
- [X] T020 [P] Author `tests/ipc/test_schema_python_ts_diff.py` — regenerate JSON Schema from Python, diff against `tui/src/ipc/schema/frame.schema.json`; fail CI on drift (FR-040 / SC-006).

**Checkpoint**: WS1 foundation green. US1/US2/US3/US4 phases may now proceed in parallel Agent Teams α/β/γ/δ.

---

## Phase 3: User Story 1 — 세션 드롭 복구 (Priority: P1, WS4) 🎯 MVP

**Goal**: TUI crash or backend restart recovers session continuity via `resume_request` handshake + ring-buffer replay; in-flight irreversible tool results never lost.

**Independent Test**: `kill -9 <backend-pid>` mid-stream → TUI reconnects → `ResumeResponseFrame(replay_count=N)` + N replayed frames with original `frame_seq` preserved → user continues without re-issuing query. Validated by `resume.integration.test.ts` (bun) + `test_resume_handshake.py` (pytest) 9-scenario matrix from `contracts/resume-handshake.contract.md` § 7.

- [ ] T021 [US1] Implement `ResumeManager.handle_resume_request()` in `src/kosmos/ipc/resume_manager.py` — validates session existence, token match, `last_seen_frame_seq >= oldest_in_ring`; emits `ResumeResponseFrame` with `resumed_from_frame_seq = last_seen + 1`.
- [ ] T022 [US1] Implement 5-value rejection enum + `ResumeRejectedFrame` emission in `src/kosmos/ipc/resume_manager.py`: `ring_evicted`, `session_unknown`, `token_mismatch`, `protocol_incompatible`, `session_expired` (FR-021/022/023 + contract § 3).
- [ ] T023 [US1] Implement 3-strike blacklist in `src/kosmos/ipc/resume_manager.py` (FR-025) — same `session_id` failing resume 3× consecutively enters blacklist; subsequent resume_request returns `session_unknown` without touching ring buffer.
- [ ] T024 [US1] Wire heartbeat ↔ resume coupling in `src/kosmos/ipc/heartbeat.py`: 45s silence → `ErrorFrame(code="peer_dead")` + keep ring buffer for 120s grace window; grace-window expiry → GC ring buffer (contract § 5).
- [ ] T025 [US1] Implement TUI reconnect loop in `tui/src/ipc/bridge.ts` — EOF detection → exponential backoff reconnect → emit `ResumeRequestFrame` as first frame (fresh outbound `frame_seq=0`) → track `applied_frame_seqs: Set<number>` for replay dedup.
- [ ] T026 [US1] Implement `tui/src/ipc/crash-detector.ts` — listen for stdin EOF / `EPIPE` errors → signal bridge.ts to enter reconnect state without prompting user.
- [ ] T027 [US1] Author `tests/ipc/test_resume_handshake.py` — all 9 scenarios from `contracts/resume-handshake.contract.md` § 7 (happy path, fresh-TUI, ring_evicted, token_mismatch, session_unknown, double resume, during backpressure, heartbeat grace recover, heartbeat grace expire).
- [ ] T028 [US1] Author `tests/ipc/test_resume_blacklist.py` — 3-strike blacklist behavior + reset semantics on successful handshake.
- [ ] T029 [US1] Author `tests/ipc/test_heartbeat_timeout.py` — 45s dead threshold, 120s grace window, `HeartbeatFrame` ping/pong symmetry.
- [ ] T030 [US1] Author `tests/ipc/test_ring_buffer.py` — `deque(maxlen=256)` overflow eviction, `.consumed` marker replay gating, `ring_evicted(last_seen_seq)` boolean correctness.
- [ ] T031 [US1] Author `tui/tests/ipc/resume.integration.test.ts` — bun end-to-end against synthetic backend: kill stdin after N frames → reconnect → assert replay_count correct + applied_frame_seqs dedup prevents double-application.

**Checkpoint**: US1 deliverable complete — MVP scope satisfied. Team may stop here and demo resume semantics.

---

## Phase 4: User Story 2 — 부처 429 / FriendliAI 쿼터 가시화 (Priority: P1, WS2)

**Goal**: Backend surfaces rate-limit/queue-saturation state to TUI HUD within 1 animation frame via `BackpressureSignalFrame`; dual-locale Korean copy.

**Independent Test**: Synthetic `BackpressureSignalFrame(signal="throttle", source="upstream_429", retry_after_ms=15000)` → TUI HUD renders "부처 API가 혼잡합니다. 15초 후 자동 재시도합니다." within 16 ms p95 (SC-003). Validated by `test_backpressure_signal.py` + `backpressure.hud.test.ts`.

- [X] T032 [US2] Implement `BackpressureController.tick()` in `src/kosmos/ipc/backpressure.py` — hysteresis logic (HWM=64 pause, HWM/2=32 resume, no-op in hysteresis band per `contracts/tx-dedup.contract.md` § 1.1).
- [X] T033 [US2] Implement 3-source emission paths in `src/kosmos/ipc/backpressure.py` — `tui_reader` (TUI congested), `backend_writer` (ring overflow risk), `upstream_429` (external adapter rate-limit pass-through).
- [X] T034 [US2] Wire `upstream_429` adapter path in `src/kosmos/ipc/backpressure.py` — parse `Retry-After` header (seconds or HTTP-date), clamp `retry_after_ms` to `[1000, 900000]`, emit `throttle` with Korean + English HUD copy templates (contract § 1.3).
- [X] T035 [US2] Enforce pause/resume pairing invariant in `src/kosmos/ipc/backpressure.py` — every `pause` must have a later `resume`; on session teardown with outstanding `pause`, emit synthetic `resume` before terminal error (contract § 1.4).
- [X] T036 [US2] Implement `tui/src/ipc/backpressure-hud.tsx` — renders Korean HUD banner with live countdown from `retry_after_ms`; non-blocking (does not pause input queue); consumes `hud_copy_ko` directly from frame.
- [X] T037 [US2] Author `tests/ipc/test_backpressure_signal.py` — hysteresis matrix (60↔64 oscillation → at most 1 pause), upstream_429 clamp, dual-locale min_length enforcement, teardown synthetic resume (contract § 5.1 test matrix).
- [X] T038 [US2] Author `tui/tests/ipc/backpressure.hud.test.ts` — ingest fixture frame → assert HUD text exact match "부처 API가 혼잡합니다. 15초 후 자동 재시도합니다." + countdown ticks.
- [X] T039 [US2] Author `tests/ipc/test_backpressure_dual_locale.py` — reject emission where `hud_copy_ko` or `hud_copy_en` is empty / missing (FR-015 discipline).

**Checkpoint**: US2 HUD visibility complete — citizen sees congestion state without log-diving.

---

## Phase 5: User Story 3 — 민원 중복 제출 차단 (Priority: P1, WS3)

**Goal**: Duplicate `transaction_id` on `is_irreversible=true` tools returns cached response without re-executing upstream; Spec 024 audit log records both hit and miss.

**Independent Test**: Same `transaction_id` submitted twice → first call executes + writes `ToolCallAuditRecord(status="ok")`, second call cache-hits + writes `ToolCallAuditRecord(status="dedup_hit")`, response byte-equal. Validated by `test_tx_dedup.py::test_double_submit_hits_cache`.

- [ ] T040 [US3] Integrate `TransactionLRU` into `ToolExecutor` dispatch in `src/kosmos/ipc/tx_cache.py` + executor call-site — Stripe 3-step (lookup → execute on miss → record with pin for irreversible) per `contracts/tx-dedup.contract.md` § 2.2.
- [ ] T041 [US3] Enforce LRU pin on `AdapterRegistration.is_irreversible=true` in `src/kosmos/ipc/tx_cache.py` — pinned entries never evicted; non-pinned overflow evicts FIFO oldest.
- [ ] T042 [US3] Implement cached-response round-trip in `src/kosmos/ipc/tx_cache.py` — `entry.cached_response = response.model_dump(mode="json")` on record, `ToolCallResponse.model_validate(...)` on replay (contract § 2.5).
- [ ] T043 [US3] Wire Spec 024 audit coupling in `src/kosmos/ipc/tx_cache.py` — write `ToolCallAuditRecord(status="ok"|"error")` on miss, `status="dedup_hit"` with reference to original `correlation_id` on hit (contract § 2.7).
- [ ] T044 [US3] Implement `tui/src/ipc/tx-registry.ts` — client-side UUIDv7 minting on user submit, persistence for retry idempotency until response received (no re-mint on duplicate click).
- [ ] T045 [US3] Author `tests/ipc/test_tx_cache_lru.py` — capacity 512, FIFO eviction of non-pinned, pinned never evicted, 513-pinned operational-limit scenario documented.
- [ ] T046 [US3] Author `tests/ipc/test_tx_irreversible_pin.py` — `is_irreversible=true` auto-pins on record, pin survives resume replay (cache survives session-drop).
- [ ] T047 [US3] Author `tests/ipc/test_tx_dedup.py` — `test_double_submit_hits_cache`, `test_cache_state_span_attribute` (asserts `kosmos.ipc.tx.cache_state="hit"`), `test_distinct_tx_id_no_dedup`, `test_reversible_tool_bypasses_cache`.

**Checkpoint**: US3 complete — PIPA §26 duplicate-submission safeguard operational.

---

## Phase 6: User Story 4 — End-to-end correlation_id trace (Priority: P2, Cross-cutting)

**Goal**: Single `correlation_id` threads `user_input → tool_call → tool_result → assistant_chunk → payload_end` spans; OTEL span attributes promote `transaction_id` + `tx.cache_state` for audit triage.

**Independent Test**: Full-turn probe emits 5+ frames → `jq -s '[.[] | .correlation_id] | unique | length' == 1`; every span in the turn has `kosmos.ipc.correlation_id` attribute set to same UUIDv7 value. Validated by `test_otel_correlation.py`.

- [ ] T048 [US4] Promote envelope `correlation_id` / `transaction_id` / `tx.cache_state` to OTEL span attributes in `src/kosmos/ipc/envelope.py` emit path — use constants from T002; attach to current span via `opentelemetry.trace.get_current_span()`.
- [ ] T049 [US4] Thread `correlation_id` through `RunContext` in existing tool-loop bootstrap (minimal touch — add `correlation_id` field if absent; propagate through `emit()` calls).
- [ ] T050 [US4] Emit `kosmos.ipc.schema.hash` as OTEL resource attribute on backend startup in `src/kosmos/ipc/envelope.py` (FR-037) — SHA-256 of `frame.schema.json` committed bytes.
- [ ] T051 [US4] Author `tests/ipc/test_otel_correlation.py` — drive synthetic full turn → assert all spans in turn share one `correlation_id` + irreversible tool-call span has `tx.cache_state="miss"` then `"hit"` on replay.
- [ ] T052 [US4] Author `src/kosmos/ipc/demo/full_turn_probe.py` + `tests/ipc/test_correlation_stability.py` — run probe → NDJSON to stdout → `jq -s '... | unique | length' == 1` (quickstart § 5.2).

**Checkpoint**: US4 audit trail complete — investigators can join OTEL / Langfuse / `ToolCallAuditRecord` by single correlation_id.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Quickstart validation, no-new-deps lint guard, documentation touch-ups, deferred-item tracking.

- [ ] T053 [P] Implement `src/kosmos/ipc/demo/session_backend.py` + `tui/src/ipc/demo/resume_probe.ts` (quickstart scenario B harness per `quickstart.md` § 2).
- [ ] T054 [P] Implement `src/kosmos/ipc/demo/upstream_429_probe.py` + `tui/src/ipc/demo/hud_probe.ts` (quickstart scenario C harness per `quickstart.md` § 3).
- [ ] T055 [P] Implement `src/kosmos/ipc/demo/register_irreversible_fixture.py` (quickstart scenario D seed — `AdapterRegistration(is_irreversible=true)` fixture for `test_tx_dedup.py`).
- [ ] T056 [P] Extend lint trio with `tests/ipc/test_no_new_runtime_deps.py` — diff `pyproject.toml` + `tui/package.json` against Spec 031 baseline; fail on any new runtime dep (SC-008 enforcement, reuses Spec 031 pattern).
- [ ] T057 [P] Author `tests/ipc/test_ndjson_integrity.py` — 1000-frame stream with 5% malformed JSON injection → 0 session aborts, only malformed frames dropped with OTEL error span (SC-007).
- [ ] T058 [P] Refresh `.specify/memory/agent-context/*.md` via `.specify/scripts/bash/update-agent-context.sh claude` — adds Spec 032 entries to Active Technologies + Recent Changes.
- [ ] T059 Touch up `docs/vision.md` § L1 Transport reference pointers + § L5 TUI IPC section to cite Spec 032 deliverables + schema path.
- [ ] T060 Track 5 `[Deferred]` items from spec.md § "Deferred to Future Work" in `docs/deferred/032-ipc-stdio-hardening.md` — remote TUI, frame signing, multi-backend shard, WebMCP capability advertisement, Windows named pipes (5 × `NEEDS TRACKING` → resolved to GitHub issues by `/speckit-taskstoissues`).
- [ ] T061 [US2] Implement critical-lane bypass in `src/kosmos/ipc/backpressure.py` — `severity=critical` frames (e.g., CBS 재난문자 `notification_push`) skip pause gate regardless of ring/queue state (FR-017). Verify via `tests/ipc/test_critical_lane_priority.py`: inject `pause`-signaled state + 10 × `severity=critical` frames; assert p95 emit latency < 16 ms per SC-009; assert ordering preserved ahead of queued non-critical frames.

**Checkpoint**: Quickstart scenarios A–E (§ 6 full regression) exit zero on `uv run pytest tests/ipc/ -q` + `cd tui && bun test ipc && cd ..`. Spec 032 landable.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: no deps — start immediately.
- **Phase 2 Foundational (WS1)**: depends on Phase 1 → **BLOCKS all user stories**.
- **Phase 3 US1 (WS4)** · **Phase 4 US2 (WS2)** · **Phase 5 US3 (WS3)**: independently runnable once Phase 2 green. **Parallel across Agent Teams α/β/γ**.
- **Phase 6 US4**: depends on Phase 3 + Phase 4 + Phase 5 for correlation-thread integration test; cross-cutting spans can partially start after Phase 2.
- **Phase 7 Polish**: depends on all user stories.

### User Story Dependencies

- **US1 (P1, WS4)**: consumes `SessionRingBuffer` (T013) + `HeartbeatState` (T015) + envelope helpers (T012). No cross-story deps.
- **US2 (P1, WS2)**: consumes `BackpressureSignalFrame` arm (T006) + envelope helpers (T012). No cross-story deps.
- **US3 (P1, WS3)**: consumes `TransactionLRU` (T014) + Spec 024 `AdapterRegistration` (pre-existing). No cross-story deps.
- **US4 (P2)**: consumes `correlation_id` field (T004) + OTEL constants (T002); full-turn probe (T052) depends on US1+US2+US3 integration.

### Within Each User Story

- Entity impl → service/controller → TUI integration → tests.
- Tests listed after implementation may be written first (TDD optional per Constitution).

### Parallel Opportunities

**Across Agent Teams at `/speckit-implement`**:

- **Team α (Backend/Python)**: T013 + T014 + T015 → T021–T024, T032–T035, T040–T043, T048–T052
- **Team β (Frontend/TS)**: T017 + T018 → T025–T026, T036, T044
- **Team γ (API Tester)**: T019 + T020 → T027–T031, T037–T039, T045–T047, T051–T052, T057
- **Team δ (Security Engineer)**: T043 spot-check (irreversible audit coupling) + T056 (no-new-deps gate)

**Within phases**:

- Phase 2: T005–T009 all [P] (separate arms in same file but pydantic classes are append-only; rebase-safe).
- Phase 2: T013–T015 all [P] (three separate files).
- Phase 7: T053–T058 all [P] (disjoint demo scripts + lint + docs).

---

## Parallel Example: Launching Agent Teams at `/speckit-implement`

```text
# Once Phase 2 (T004–T020) is green, spawn four teammates in parallel:

Team α (Backend Architect, Sonnet):
  Phase 3 tasks T021–T024 + Phase 4 T032–T035 + Phase 5 T040–T043 + Phase 6 T048–T050

Team β (Frontend Developer, Sonnet):
  Phase 3 tasks T025–T026 + Phase 4 T036 + Phase 5 T044

Team γ (API Tester, Sonnet):
  Phase 3 tests T027–T031 + Phase 4 T037–T039 + Phase 5 T045–T047 + Phase 6 T051–T052

Team δ (Security Engineer, Sonnet):
  Phase 7 T056 (no-new-deps gate) + T043 review
```

---

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 Setup (T001–T003).
2. Complete Phase 2 Foundational (T004–T020) — blocks all stories.
3. Complete Phase 3 US1 (T021–T031) — resume handshake MVP.
4. **STOP and VALIDATE**: `uv run pytest tests/ipc/test_resume_handshake.py tests/ipc/test_heartbeat_timeout.py tests/ipc/test_ring_buffer.py -q` → green. Demo `kill -9` resume scenario.
5. Deploy/demo if ready.

### Incremental Delivery

1. Setup + Foundational → substrate ready.
2. Add US1 (resume) → demo session-drop recovery (MVP).
3. Add US2 (backpressure HUD) → demo 429 visibility.
4. Add US3 (tx dedup) → demo duplicate-submit block.
5. Add US4 (correlation trace) → demo end-to-end audit.
6. Polish → CI green + docs + deferred tracking.

### Parallel Team Strategy

- Single Lead (Opus) completes Phase 1 + Phase 2 solo (sequential, envelope is load-bearing).
- Once T020 green, spawn 4 Sonnet teammates per "Parallel Example" above.
- Lead reviews PRs from each workstream, merges in dependency order (WS1 → {WS2, WS3, WS4} → US4 → Polish).

---

## Notes

- **No new runtime deps**: T014 (`OrderedDict`), T013 (`deque`), T015 (stdlib timers), T016 (Python stdlib `hashlib` + `json`) — all stdlib. SC-008 gate enforced by T056.
- **5 deferred items** tracked in T060 → `/speckit-taskstoissues` converts `NEEDS TRACKING` → GitHub issue numbers.
- **Constitution re-check**: T058 agent-context refresh + Lead Opus code review is the post-design Constitution gate.
- **Sub-Issue API compliance**: 61 tasks emitted ≤ 90 cap; 29-task headroom safely under GitHub Sub-Issues API v2 limit.
- **Task-to-issue workflow**: Tasks ONLY materialize as GitHub issues via `/speckit-taskstoissues` — do NOT create issues manually.
- **Commit cadence**: one logical PR per workstream phase (α/β/γ/δ-numbered); Copilot + Codex review on each push; final squash-merge closes Epic #1298.
