# Implementation Plan: Agent Swarm Core — Layer 4

**Branch**: `feat/13-agent-swarm-core` | **Date**: 2026-04-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification at `specs/027-agent-swarm-core/spec.md`

## Summary

Build the Layer 4 substrate that turns the Phase 1 single-agent `QueryEngine` into a coordinator-and-workers swarm: a `Coordinator` that owns the `Research → Synthesis → Implementation → Verification` phase machine, `Worker` instances that each wrap one `QueryEngine` restricted to the 2-tool facade (`lookup` + `resolve_location`) from Epic #507, an abstract `Mailbox` with a `FileMailbox` implementation backed by fsync'd JSON files under `~/.kosmos/mailbox/<session_id>/<sender_id>/`, a strictly vertical permission delegation chain via a `ConsentGateway` stub (real TUI prompt deferred to #287), cooperative cancellation propagating `asyncio.CancelledError` to all workers within 500 ms, and three new `kosmos.agent.*` OTel spans whose attribute names are declared in `src/kosmos/observability/semconv.py` for future consumption by Epic #501.

Technical approach: reuse `src/kosmos/engine/query.py::_query_inner` verbatim inside `Worker` (no tool-loop reimplementation — per FR-009 and Constitution Principle I's "Claude Code is the first reference" rule); model every mailbox message as a closed Pydantic v2 discriminated union on `msg_type` (no `Any`, per Constitution III); route messages strictly by declared `recipient` so that Constitution Principle II ("permissions never flow laterally") is enforced by the mailbox, not by worker discipline; keep the `Mailbox` class abstract so the future Redis Streams backend (Phase 3) drops in without coordinator/worker changes. All four `KOSMOS_AGENT_*` environment variables join the pydantic-settings catalog owned by Epic #468. **Zero new runtime dependencies** — everything is stdlib (`asyncio`, `uuid`, `pathlib`, `json`, `hashlib`, `datetime`) on top of `pydantic`, `httpx`, `opentelemetry-*` already in `pyproject.toml`.

## Technical Context

**Language/Version**: Python 3.12+ (existing project baseline; no version bump).
**Primary Dependencies**: `pydantic >= 2.13` (frozen models + discriminated unions, existing), `pydantic-settings >= 2.0` (env-var catalog, existing), `opentelemetry-sdk` / `opentelemetry-semantic-conventions` (span emission, existing from Spec 021), stdlib `asyncio` / `uuid` / `pathlib` / `json` / `hashlib` / `datetime`. **No new runtime dependencies** — AGENTS.md hard rule. All imports already in `pyproject.toml` courtesy of Specs 004 / 005 / 021 / 022.
**Storage**: POSIX filesystem only — `KOSMOS_AGENT_MAILBOX_ROOT` (default `~/.kosmos/mailbox`) holds one directory per `session_id`, one sub-directory per `sender_id`, one JSON file per message (`<message_id>.json`). fsync on write guarantees at-least-once delivery. No database, no external queue. `replay_unread` state is tracked via a sibling `<message_id>.json.consumed` marker file written after the coordinator or worker has processed a message; crash-replay reads only messages without a `.consumed` marker.
**Testing**: `pytest` + `pytest-asyncio` (existing). New test packages: `tests/agents/test_coordinator_phases.py`, `tests/agents/test_worker_lifecycle.py`, `tests/agents/test_mailbox_file.py`, `tests/agents/test_mailbox_crash_replay.py`, `tests/agents/test_permission_delegation.py`, `tests/agents/test_cooperative_cancellation.py`, `tests/agents/test_synthesis_tool_gate.py`, `tests/agents/test_observability_spans.py`. All integration tests use recorded fixtures from the #507 seed adapters — no live `data.go.kr` traffic (FR-037, Constitution IV).
**Target Platform**: Linux + macOS CI (POSIX fsync required). Windows not a Phase 1 target.
**Project Type**: Python backend library (single project; no frontend in this Epic — TUI is #287).
**Performance Goals**: Cooperative cancellation end-to-end wall-clock ≤ 500 ms on loopback (FR-006, SC-003); mailbox `send` with fsync ≤ 10 ms on local SSD (informational, not contractual); coordinator synthesis phase ≤ 3 s for 3 parallel workers with ≤ 10 result messages each (informational).
**Constraints**: No live `data.go.kr` (Constitution IV, hard); no new runtime deps (AGENTS.md hard); no lateral permission flow (Constitution II, non-negotiable); no `typing.Any` in message schemas (Constitution III); no nested tool calls — coordinator never calls tools, workers never spawn sub-workers (spec Out-of-Scope, references NESTful arXiv:2409.03797); source text English-only.
**Scale/Scope**: Up to `KOSMOS_AGENT_MAX_WORKERS=4` concurrent workers per coordinator session (clamped to `[1, 16]`), up to `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES=1000` messages per session (clamped to `[100, 10000]`); ~1200 LOC across `src/kosmos/agents/` + ~800 LOC of tests. Per `docs/vision.md § Appendix A` Layer 4 budget is ~8000 lines — this Epic ships the infra skeleton, ministry specialist prompts (#14) fill the remaining budget.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Plan alignment |
|---|---|---|
| **I. Reference-Driven Development** | Every design decision traces to `docs/vision.md § Reference materials`. | `research.md` Phase 0 maps each decision to one of: Claude Code reconstructed (tool loop reuse, phase machine), AutoGen (mailbox IPC + cooperative cancellation), Anthropic Cookbook orchestrator-workers (coordinator-owns-synthesis pattern), OpenAI Agents SDK (handoff semantics, retry matrix), NESTful arXiv:2409.03797 (no nested tool calls), Spec 019 (per-session semaphore reuse), Spec 021 (OTel GenAI v1.40 span conventions), Spec 507 (2-tool facade closure), Spec 468 (env-var catalog), Spec 501 (attribute boundary table). **PASS**. |
| **II. Fail-Closed Security (non-negotiable)** | Conservative defaults; bypass-immune checks. | Worker tool registry is hard-restricted to `{"lookup", "resolve_location"}` at `AgentContext` construction time (frozen Pydantic v2 model, `extra="forbid"`) — no runtime expansion path exists. Mailbox routes by declared `recipient` field so a worker literally cannot read another worker's `permission_request`. `ConsentGateway` default stub returns `True` ONLY because it is scoped to test-only use; production integration (#287) is required before any Phase 2 deploy. `MailboxOverflowError` / `MailboxWriteError` raise immediately — no silent drops. **PASS**. |
| **III. Pydantic v2 Strict Typing (non-negotiable)** | All I/O uses Pydantic v2; no `Any`. | `AgentMessage`, `AgentContext`, `CoordinatorPlan`, `PlanStep` and the six `*Payload` union members are all Pydantic v2 with `extra="forbid"`. `AgentMessagePayload` is a `Field(discriminator="kind")` closed union — `Any` is forbidden by explicit assertion in the module docstring and in FR-016. `AgentContext` uses `arbitrary_types_allowed=True` only for `LLMClient` / `ToolRegistry` (non-Pydantic infra objects, same precedent as `QueryContext`). **PASS**. |
| **IV. Government API Compliance** | No live `data.go.kr` calls in CI; fixtures only. | FR-037 mandates the #507 recorded-fixture tape for every agent integration test. SC-010 asserts zero live calls across the CI run. Workers see only `lookup` + `resolve_location` which already operate against fixture tapes in test mode. **PASS**. |
| **V. Policy Alignment** | Korea AI Action Plan Principles 5/8/9. | Coordinator-owns-synthesis preserves the "single conversational window" (Principle 8): the citizen sees exactly one session, not three. Worker isolation + vertical permission delegation preserves the consent-based data-access model (Principle 5). No new entrypoint, no new PII flow — Layer 3 Permission Pipeline remains the sole PII gate. **PASS (no regression)**. |
| **VI. Deferred Work Accountability** | Every deferral tracked in Deferred Items table with issue reference. | spec.md § "Scope Boundaries & Deferred Items" contains an 8-row table. Four rows reference live issues (#14, #287, #21, #21/Layer6). Four rows are marked `NEEDS TRACKING` (Redis backend, cross-session memory, account-wide rate-limit, scenario graph, agent handoff, formal OTel upstream registration) and will be resolved by `/speckit-taskstoissues`. No free-text "future epic" / "v2" outside the table. **PASS**. |

**Gate result**: PASS — no violations, no Complexity Tracking entries required.

**Re-check after Phase 1**: data-model.md and contracts/*.schema.json must preserve the discriminated-union closure on `msg_type` and the `extra="forbid"` invariant. See "Post-Design Constitution Re-Check" at the end of this document.

## Project Structure

### Documentation (this feature)

```text
specs/027-agent-swarm-core/
├── plan.md                              # This file (/speckit.plan output)
├── research.md                          # Phase 0 — reference mappings + resolved assumptions
├── data-model.md                        # Phase 1 — Pydantic v2 model inventory
├── quickstart.md                        # Phase 1 — contributor walkthrough
├── contracts/
│   ├── agent-message.schema.json        # JSON Schema for the AgentMessage discriminated union
│   ├── coordinator-plan.schema.json     # JSON Schema for the CoordinatorPlan output
│   └── mailbox-abi.md                   # Non-JSON contract: on-disk file layout + fsync ordering
├── checklists/
│   └── requirements.md                  # (existing /speckit-checklist output)
├── spec.md                              # (existing /speckit-specify output)
└── tasks.md                             # /speckit-tasks output (NOT created here)
```

### Source code (repository root, files this Epic adds or modifies)

```text
# New package — Layer 4 home
src/kosmos/agents/
├── __init__.py                          # Public re-exports: Coordinator, Worker, AgentContext,
│                                        #                    AgentMessage, CoordinatorPlan,
│                                        #                    FileMailbox, ConsentGateway
├── coordinator.py                       # Coordinator class + 4-phase workflow (FR-001..FR-007)
├── worker.py                            # Worker class; delegates to engine.query._query_inner (FR-008..FR-013)
├── context.py                           # AgentContext frozen Pydantic v2 model (FR-010)
├── consent.py                           # ConsentGateway ABC + always-grant stub (FR-027)
├── errors.py                            # AgentConfigurationError, AgentIsolationViolation,
│                                        # MailboxOverflowError, MailboxWriteError
├── plan.py                              # CoordinatorPlan + PlanStep Pydantic v2 models (FR-005)
└── mailbox/
    ├── __init__.py                      # Mailbox ABC re-export
    ├── base.py                          # Mailbox abstract base class (FR-014, FR-022)
    ├── messages.py                      # AgentMessage + 6 Payload union members (FR-016)
    └── file_mailbox.py                  # FileMailbox impl — fsync + FIFO + replay (FR-014..FR-021)

# Modified files (additive)
src/kosmos/observability/semconv.py      # Add kosmos.agent.* attribute-name constants (FR-031)
src/kosmos/settings.py                   # Add 4 KOSMOS_AGENT_* env fields (FR-032..FR-035)
docs/configuration.md                    # Document 4 new env vars (FR-036)

# New tests
tests/agents/
├── __init__.py
├── conftest.py                          # Shared fixtures — fixture-tape LLM + stub workers
├── test_coordinator_phases.py           # FR-001..FR-004, FR-007, SC-001, SC-002
├── test_worker_lifecycle.py             # FR-008..FR-013, SC-001
├── test_mailbox_file.py                 # FR-014..FR-022, FR-021 overflow path
├── test_mailbox_crash_replay.py         # FR-019..FR-020, SC-005
├── test_permission_delegation.py        # FR-023..FR-027, SC-004
├── test_cooperative_cancellation.py     # FR-006, SC-003
├── test_synthesis_tool_gate.py          # FR-038 — no lookup/resolve_location during synthesis
├── test_observability_spans.py          # FR-028..FR-031, SC-006
└── fixtures/
    ├── mailbox_crash_replay/
    │   └── pre_written_result.json      # Simulates a completed worker's result on disk
    └── multi_ministry_query.json        # Scripted LLM response for 3-worker dispatch
```

**Structure Decision**: Single Python package layout (Option 1 from the template). All agent code lives under `src/kosmos/agents/`, colocated with `src/kosmos/engine/`, `src/kosmos/tools/`, `src/kosmos/permissions/`, `src/kosmos/observability/` (the Layer 1/2/3/5/6 siblings). The `mailbox/` sub-package exists because the ABC + concrete impl + message union form a coherent IPC module that will grow a Redis backend in Phase 3 (#21) — splitting it now avoids a future breaking refactor. No frontend layer is introduced (TUI = #287).

## Complexity Tracking

*No Constitution Check violations — Complexity Tracking intentionally empty.*

---

## Post-Design Constitution Re-Check

*To be filled after Phase 1 artifacts (data-model.md, contracts/*.schema.json) are written. Verifies that the concrete models preserve the gates that PASSED in the pre-design check.*

| Gate | Re-check verdict |
|---|---|
| I. Reference-Driven Development | PASS — every model in data-model.md cites a reference row in research.md § 1. |
| II. Fail-Closed Security | PASS — `AgentContext.tool_registry` is typed `ToolRegistry` with a post-init invariant restricting the tool set to `{"lookup", "resolve_location"}`; `FileMailbox.send` routes only by declared `recipient`. |
| III. Pydantic v2 Strict Typing | PASS — `agent-message.schema.json` shows the closed discriminated union on `msg_type` with 6 explicit branch schemas; `Any` / `additionalProperties: true` appears nowhere. |
| IV. Government API Compliance | PASS — no adapter is modified; fixture tapes from #507 are consumed as-is. |
| V. Policy Alignment | PASS — no new PII surface; Layer 3 Permission Pipeline remains the sole PII gate. |
| VI. Deferred Work Accountability | PASS — `/speckit-taskstoissues` will resolve the 4 `NEEDS TRACKING` markers during the next phase. |

**Final gate result**: PASS. Ready for `/speckit-tasks`.
