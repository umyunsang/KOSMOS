# Implementation Plan: IPC stdio hardening (frame envelope · backpressure · reconnect · at-least-once replay)

**Branch**: `032-ipc-stdio-hardening` | **Date**: 2026-04-19 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/032-ipc-stdio-hardening/spec.md`
**Parent Epic**: #1298 · ADR-006 Part D-2 Epic A

## Summary

Harden the TUI ↔ Python backend stdio protocol so that citizen sessions survive TUI/backend crashes, surface LLM-429 and ministry-API backpressure in Korean/English HUD copy, and block duplicate civil-affairs submissions via transaction-scoped idempotency. This spec EXTENDS — never replaces — the 10 existing frame arms in `src/kosmos/ipc/frame_schema.py` (Spec 287 foundation): every current field is preserved, and new envelope fields (`version`, `role`, `frame_seq`, `transaction_id`, `trailer`) are added via a single `_BaseFrame` change plus 9 new frame arms (`payload_start`/`payload_delta`/`payload_end`, `backpressure_signal`, `resume_request`/`resume_response`/`resume_rejected`, `heartbeat`, `notification_push`). Delivery is factored into four parallel-safe workstreams (WS1 envelope+schema, WS2 backpressure+ring buffer, WS3 tx dedup+audit coupling, WS4 resume handshake+heartbeat) for Agent Teams dispatch at `/speckit-implement`. No new runtime dependencies (AGENTS.md hard rule, SC-008) — stdlib `collections.OrderedDict` / `collections.deque` / `uuid.uuid7()` / `asyncio` only.

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing project baseline — required for stdlib `uuid.uuid7()`); TypeScript 5.6+ with Bun v1.2.x (TUI layer, existing Spec 287 runtime).
**Primary Dependencies**: `pydantic >= 2.13` (envelope + discriminated union, existing), `pydantic-settings >= 2.0` (ring-buffer / LRU / heartbeat knobs via `KOSMOS_IPC_*` env vars, existing), `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (span attribute emission from Spec 021, existing), `pytest` + `pytest-asyncio` (existing test stack). **Zero new runtime dependencies** (AGENTS.md hard rule; SC-008). TUI side adds no JS deps — relies on existing Bun stdlib + `crypto.randomUUID()` + timestamp-prepended UUIDv7 helper.
**Storage**: N/A at this layer. `SessionRingBuffer` (256-frame in-memory `collections.deque`) and `TransactionLRU` (512-entry `collections.OrderedDict` per session) are session-lifetime state — never persisted to disk (FR-023). `.consumed` marker pattern is reused from Spec 027 mailbox but here is ring-buffer-internal bookkeeping (not filesystem). `ToolCallAuditRecord` persistence remains Spec 024 territory — this spec only populates the `correlation_id` + `transaction_id` fields on that schema.
**Testing**: `uv run pytest` — unit (envelope round-trip, LRU eviction, ring-buffer wrap-around), contract (JSON Schema 2020-12 validation via Pydantic `TypeAdapter.json_schema()` + TS-generated type diff), integration (TUI kill → resume → frame order/count/dedup invariants via `pytest-asyncio` fixtures), stress (1000-frame × 10-session tx dedup), lint (SC-008 `pyproject.toml` / `tui/package.json` diff guard). No live `data.go.kr` calls (AGENTS.md Hard Rule).
**Target Platform**: macOS / Linux (AGENTS.md stack). Windows named-pipe support explicitly deferred (spec.md Deferred item #5).
**Project Type**: Library extension — modifies existing `src/kosmos/ipc/` + `tui/src/ipc/` packages. No new top-level package.
**Performance Goals**: Resume p95 < 500 ms (SC-001), backend-crash-recover p95 < 3 s (SC-002), backpressure signal render p95 < 16 ms = 1 animation frame @60 Hz (SC-003), tx cache hit p95 < 5 ms (SC-004), critical-severity frame bypass backpressure p95 < 16 ms (SC-009).
**Constraints**: Single-host stdio only (OS delivery guarantee, no network IPC). Session state in-memory only — backend restart invalidates ring buffer (FR-023). Heartbeat 30 s interval, 45 s dead threshold (FR-039). Single frame serialized size > 1 MiB triggers chunked-frame split (FR-010). All NDJSON — payload `\n` must be JSON-escaped (FR-009).
**Scale/Scope**: Per-session in-flight surface — ring buffer 256 frames × ~4 KiB typical payload = 1 MiB upper-bound per session; tx LRU 512 entries × ~2 KiB summary = 1 MiB. Expected concurrency: 1 citizen session per TUI process (Phase 2 horizontal scaling deferred, spec.md Deferred item #3). Frame-kind cardinality: 10 existing + 9 new = 19 arms, < 30 is within Pydantic discriminated-union comfort zone.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| # | Principle | Check | Status |
|---|-----------|-------|--------|
| I | Reference-Driven | Every FR maps to `.references/claude-code-sourcemap/restored-src/` + MCP/LSP/Stripe external refs (see research.md § Reference mapping). Envelope design derives from LSP 3.17 JSON-RPC + MCP Last-Event-ID; resume from MCP transports; idempotency from Stripe 3-step approach; backpressure from Node.js streams doc + CC `withRetry`. | PASS |
| II | Fail-Closed Security | `resume_rejected` defaults are explicit (not silent). Unknown `version` → hard-fail not upgrade-retry (FR-038, MCP precedent). Unknown frame kind → drop-and-log, never session-kill (FR-035). Tx cache miss treated conservatively — irreversible tool retries are blocked upstream (FR-031). | PASS |
| III | Pydantic v2 Strict Typing | All envelope extensions (`version`, `role`, `frame_seq`, `transaction_id`, `trailer`) are typed; new frame arms extend `_BaseFrame` via Pydantic v2 discriminated union — no `Any` escape hatches. JSON Schema auto-derived via `TypeAdapter.json_schema()`. | PASS |
| IV | Gov API Compliance | No live `data.go.kr` calls in tests (integration tests use recorded fixtures + mock tool adapters). `BackpressureSignal` payload includes `source_agency` for per-ministry quota visibility. `ToolCallAuditRecord` schema coupling with Spec 024 ensures every tx gets logged. | PASS |
| V | Policy Alignment | FR-043 (new — added in Phase 1 research) commits to PIPA §35 열람권 linkage: citizen sees backpressure / resume status in their own session HUD. Korea AI Action Plan Principle 8 (single conversational window) is preserved — resume restores the single-window context rather than forcing citizen to re-navigate. | PASS |
| VI | Deferred Work Accountability | 5 items in `Deferred to Future Work` table, all with `NEEDS TRACKING` pending `/speckit-taskstoissues`. 5 items in `Out of Scope (Permanent)`. Spec scans clean for "separate epic" / "future phase" free-text without table entry. | PASS |

**Gate outcome**: PASS — proceed to Phase 0 research. No complexity tracking entries required.

## Project Structure

### Documentation (this feature)

```text
specs/032-ipc-stdio-hardening/
├── plan.md              # This file (/speckit-plan output)
├── spec.md              # Feature specification (committed 3156d79)
├── research.md          # Phase 0 — reference mapping + decision log
├── data-model.md        # Phase 1 — envelope extension + new frame arms
├── quickstart.md        # Phase 1 — citizen-scenario walkthrough (resume)
├── contracts/           # Phase 1 — JSON Schema + Pydantic contract tests
│   ├── frame-envelope.schema.json      # JSON Schema 2020-12 full envelope
│   ├── resume-handshake.contract.md    # ResumeRequest/Response invariants
│   └── tx-dedup.contract.md            # TransactionRecord LRU invariants
└── checklists/
    └── requirements.md  # PASS — 15/15 (committed 3156d79)
```

### Source Code (repository root)

This spec modifies two existing packages and adds no new top-level directories.

```text
src/kosmos/ipc/                                     # EXTEND existing package
├── __init__.py                                     # re-exports unchanged
├── frame_schema.py                                 # EXTEND _BaseFrame + 9 new arms (WS1)
├── stdio.py                                        # EXTEND stdout-only writer (FR-036, WS1)
├── envelope.py                                     # NEW — versioning + trailer helpers (WS1)
├── ring_buffer.py                                  # NEW — 256-frame deque + .consumed (WS2)
├── backpressure.py                                 # NEW — high-water-mark + signal emitter (WS2)
├── tx_cache.py                                     # NEW — 512-entry LRU + irreversible pin (WS3)
├── resume_manager.py                               # NEW — handshake + blacklist (WS4)
└── heartbeat.py                                    # NEW — 30 s ping + 45 s dead timeout (WS4)

tui/src/ipc/                                        # EXTEND existing package
├── bridge.ts                                       # EXTEND resume handshake wire (WS4)
├── codec.ts                                        # EXTEND NDJSON line framing (WS1)
├── crash-detector.ts                               # EXTEND heartbeat timeout (WS4)
├── frames.generated.ts                             # REGENERATE from Pydantic schema (WS1)
├── envelope.ts                                     # NEW — UUIDv7 + trailer helpers (WS1)
├── backpressure-hud.tsx                            # NEW — HUD 1-animation-frame render (WS2)
├── tx-registry.ts                                  # NEW — TUI-side tx re-use guard (WS3)
└── schema/                                         # NEW directory
    └── frame.schema.json                           # NEW — JSON Schema 2020-12 (WS1)

tests/ipc/                                          # EXTEND existing test root
├── test_envelope_roundtrip.py                      # NEW (WS1)
├── test_ring_buffer.py                             # NEW (WS2)
├── test_backpressure_signal.py                     # NEW (WS2)
├── test_tx_cache_lru.py                            # NEW (WS3)
├── test_tx_irreversible_pin.py                     # NEW (WS3)
├── test_resume_handshake.py                        # NEW (WS4)
├── test_resume_blacklist.py                        # NEW (WS4)
├── test_heartbeat_timeout.py                       # NEW (WS4)
├── test_schema_python_ts_diff.py                   # NEW (WS1, CI gate for SC-006)
└── test_no_new_runtime_deps.py                     # NEW (SC-008 lint trio companion)

tui/src/ipc/__tests__/                              # EXTEND existing
├── envelope.roundtrip.test.ts                      # NEW (WS1)
├── resume.integration.test.ts                      # NEW (WS4)
└── backpressure.hud.test.ts                        # NEW (WS2)
```

**Structure Decision**: Existing `src/kosmos/ipc/` (backend) + `tui/src/ipc/` (TUI) are extended in-place. One new subdirectory `tui/src/ipc/schema/` holds the JSON Schema Draft 2020-12 source of truth. Four parallel-safe workstream boundaries map cleanly onto these directories (WS1 cuts across `frame_schema.py` + `schema/*.json` + `envelope.*`; WS2/3/4 own disjoint helper modules). Cross-workstream contracts are expressed via Pydantic class imports from `frame_schema.py` — WS1 lands the base model surface first, WS2/3/4 extend behaviorally.

## Parallel-Safe Workstream Factoring (for Agent Teams at `/speckit-implement`)

Four independent streams; WS1 up-front sync (≈1 hour), then WS2/WS3/WS4 concurrent.

| Stream | Scope | Files owned | Dependencies |
|--------|-------|-------------|--------------|
| **WS1** — Envelope + Schema | Extend `_BaseFrame` w/ `version`/`role`/`frame_seq`/`transaction_id`/`trailer`; add 9 new Pydantic frame arms; emit `tui/src/ipc/schema/frame.schema.json`; regenerate `tui/src/ipc/frames.generated.ts`; schema-diff CI gate | `frame_schema.py`, `envelope.py`, `envelope.ts`, `codec.ts`, `schema/frame.schema.json`, `frames.generated.ts`, `test_envelope_roundtrip.py`, `test_schema_python_ts_diff.py` | none (foundational) |
| **WS2** — Backpressure + Ring Buffer | 64-frame HWM; `BackpressureSignalFrame` emitter; 256-frame `SessionRingBuffer` w/ `.consumed` marker; critical-lane bypass; HUD render | `ring_buffer.py`, `backpressure.py`, `backpressure-hud.tsx`, `test_ring_buffer.py`, `test_backpressure_signal.py`, `backpressure.hud.test.ts` | WS1 model surface |
| **WS3** — Tx Dedup + Audit Coupling | 512-entry LRU `TransactionLRU`; `is_irreversible` pin exempt from eviction; cache-state OTEL attribute; Spec 024 `ToolCallAuditRecord` field population | `tx_cache.py`, `tx-registry.ts`, `test_tx_cache_lru.py`, `test_tx_irreversible_pin.py` | WS1 model surface, Spec 024 schema |
| **WS4** — Resume Handshake + Heartbeat | `resume_request/response/rejected`; 30 s heartbeat; 45 s dead-threshold; 3-fail blacklist; session-expired reason codes | `resume_manager.py`, `heartbeat.py`, `bridge.ts`, `crash-detector.ts`, `test_resume_handshake.py`, `test_resume_blacklist.py`, `test_heartbeat_timeout.py`, `resume.integration.test.ts` | WS1 model surface, WS2 ring buffer |

**Lead/Teammate assignment** (per AGENTS.md § Agent Teams):
- WS1 → Backend Architect (Sonnet) + Frontend Developer (Sonnet, parallel TS regen subtask)
- WS2 → Backend Architect (Sonnet) + Frontend Developer (Sonnet, HUD subtask)
- WS3 → Backend Architect (Sonnet) — single-file scope, solo
- WS4 → Backend Architect (Sonnet) + Frontend Developer (Sonnet, bridge.ts subtask)
- Cross-cutting review → Code Reviewer (Opus) after each WS merge
- Security spot-check → Security Engineer (Sonnet) on tx-cache-LRU irreversible pin (Spec 024 coupling)

## Complexity Tracking

No constitution violations detected. No complexity entries required.

## Post-Design Constitution Re-check (Phase 1 exit gate)

*Re-evaluated after generating `research.md`, `data-model.md`, `contracts/*`, `quickstart.md`.*

| # | Principle | Post-design check | Status |
|---|-----------|-------------------|--------|
| I | Reference-Driven | `research.md § 1` maps every FR cluster to a concrete reference; `data-model.md § 2` cites LSP/MCP/Stripe; `contracts/resume-handshake.contract.md` cites MCP 2025-03-26 + LSP 3.17; `contracts/tx-dedup.contract.md` cites Node.js highWaterMark + Stripe. No orphan decisions. | PASS |
| II | Fail-Closed Security | `data-model.md § 1.3` pins `extra="forbid"`; `§ 1.4` invariants E1–E6 all fail-closed; `contracts/resume-handshake.contract.md § 3` enumerates 5 normative rejection reasons with explicit `Start new session` recovery (no silent retry). | PASS |
| III | Pydantic v2 Strict Typing | `data-model.md § 1.1` gives concrete types (all `Literal[...]`/`int ge=0`/`str min_length=1`); no `Any`. JSON Schema in `contracts/frame-envelope.schema.json` mirrors Pydantic via `TypeAdapter.json_schema()` — round-trip validated in `quickstart.md § 1.1`. | PASS |
| IV | Gov API Compliance | `contracts/tx-dedup.contract.md § 2.7` nails the Spec 024 coupling — every irreversible call writes a `ToolCallAuditRecord` regardless of cache state; `data-model.md § 2.9` wires notification push from Spec 031 subscribe surface. `quickstart.md § 0` forbids live API calls in test harness. | PASS |
| V | Policy Alignment | `data-model.md § 2.4` HUD copy mandate (Korean + English, `min_length=1`) implements PIPA §35 investability and Korea AI Action Plan Principle 8 (civic-facing, dual-locale). `contracts/tx-dedup.contract.md § 2.6` prevents double-submission of irreversible civic actions — direct PIPA §26 수탁자 safeguard. | PASS |
| VI | Deferred Work Accountability | `research.md § 2` deferred-item validation clean (5 items, all NEEDS TRACKING); `contracts/tx-dedup.contract.md § 6` and `contracts/resume-handshake.contract.md § 8` each list "Out of scope" pointing back to spec.md Deferred table. No new scope creep introduced during Phase 1. | PASS |

**Post-design gate**: PASS — no new violations, no new complexity entries. Ready for `/speckit-tasks`.

## Phase 1 Artifacts

| Artifact | Path | Purpose |
|----------|------|---------|
| Research | [`research.md`](./research.md) | Reference mapping · deferred-item validation · tech-choice decision log · existing-code extension analysis · risk matrix |
| Data model | [`data-model.md`](./data-model.md) | FrameEnvelope extension · 9 new arms · SessionRingBuffer · TransactionLRU · HeartbeatState · invariants + state transitions |
| Envelope schema | [`contracts/frame-envelope.schema.json`](./contracts/frame-envelope.schema.json) | JSON Schema Draft 2020-12 — 19-kind enum · envelope fields · `allOf` role↔kind constraints |
| Resume contract | [`contracts/resume-handshake.contract.md`](./contracts/resume-handshake.contract.md) | Happy-path + rejection flows · normative reason codes · at-least-once semantics · test matrix |
| Tx dedup contract | [`contracts/tx-dedup.contract.md`](./contracts/tx-dedup.contract.md) | Backpressure triangle · Stripe 3-step dedup · Spec 024 audit coupling · test matrix |
| Quickstart | [`quickstart.md`](./quickstart.md) | 5 scenarios (schema · resume · 429 HUD · tx dedup · correlation trace) · rollback · troubleshooting |
| Agent context | [`/CLAUDE.md`](../../CLAUDE.md) | Updated by `update-agent-context.sh claude` — added Python 3.12 / Pydantic / OTel / no-new-deps entry |
