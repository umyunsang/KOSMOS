# Phase 0 Research — Agent Swarm Core (Layer 4)

**Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md) · **Branch**: `feat/13-agent-swarm-core` · **Date**: 2026-04-18

Every design decision in `plan.md` must trace to a concrete reference per Constitution Principle I. This document enumerates those mappings, resolves the "NEEDS CLARIFICATION" markers the spec template surfaces, and validates the spec's Deferred Items table per Constitution Principle VI.

---

## 1. Reference mapping — decisions → sources

| # | Decision | Reference (Primary) | Reference (Secondary) | Why it fits KOSMOS Layer 4 |
|---|---|---|---|---|
| D1 | **Coordinator + Workers + Mailbox topology** (not a single monolithic agent) | AutoGen `AgentRuntime` mailbox IPC (`microsoft/autogen`, MIT) — `docs/vision.md § Reference materials` row 4 | Anthropic Cookbook **orchestrator-workers** pattern (`anthropic-cookbook`, MIT) — `docs/vision.md § Reference materials` row 5 | Multi-ministry queries like "이사 준비" span 3+ domains; a single-context agent cannot hold all prompts + tool registries without blowing the context window. AutoGen proves mailbox IPC scales; Anthropic Cookbook proves orchestrator-owns-synthesis keeps worker outputs composable. |
| D2 | **Coordinator owns Synthesis — never delegates** | `docs/vision.md § Layer 4 → Coordinator workflow` (KOSMOS canon) | Anthropic Cookbook orchestrator-workers example | Synthesis must integrate cross-ministry dependencies (e.g., residence transfer must precede vehicle registration). Delegating synthesis to a "meta-worker" would make the dependency graph opaque to the citizen-facing coordinator. Enforced by FR-004 + FR-038. |
| D3 | **Workers reuse `engine/query.py::_query_inner` verbatim** (no tool-loop reimplementation) | Claude Agent SDK async-generator tool loop (`anthropics/claude-agent-sdk-python`, MIT) — `docs/vision.md § Reference materials` row 1 | Claude Code reconstructed — `ChinaSiro/claude-code-sourcemap` | Constitution Principle I: "Claude Code is the first reference." The Phase 1 tool loop is already reference-anchored — reimplementing it inside `Worker` would fork the reference and drift. FR-009 makes this binding. |
| D4 | **File-based mailbox with fsync for at-least-once delivery** | `docs/vision.md § Layer 4 → Mailbox IPC` (KOSMOS canon) | AutoGen durable-message discussion | Phase 2 is single-process; Redis (Phase 3, deferred to #21) is overkill. Files give (a) cross-process correctness if we ever run coordinator + workers in separate processes, (b) trivial crash-replay, (c) zero service-discovery cost. fsync-before-return is the POSIX-sanctioned at-least-once pattern. |
| D5 | **Per-sender FIFO, no cross-sender ordering guarantee** | AutoGen mailbox semantics | POSIX `open(O_APPEND)` / directory iteration semantics | Per-sender FIFO is cheap (filename timestamp + monotonic counter inside sender directory); total-order FIFO would require a central sequencer which contradicts D1. FR-018 makes the weaker guarantee binding. |
| D6 | **Vertical-only permission delegation** (worker → coordinator → citizen → coordinator → worker) | `docs/vision.md § Layer 4 → Permission delegation across agents` + Constitution Principle II | OpenAI Agents SDK guardrail pipeline (`openai/openai-agents-python`, MIT) — `docs/vision.md § Reference materials` row 2 | Lateral flow would let a compromised worker exfiltrate another worker's credential via a crafted message. Constitution Principle II makes vertical flow non-negotiable; mailbox-routes-by-recipient enforces it mechanically (FR-025). |
| D7 | **`ConsentGateway` abstract base + always-grant stub** | OpenAI Agents SDK `HumanInTheLoop` handoff pattern | Google ADK Runner-level plugin pattern (`google/adk-python`, Apache-2.0) — `docs/vision.md § Reference materials` row 14 | The real consent UI is TUI work (#287). The ABC freezes the contract now so #287 can implement without a coordinator refactor. Stub returns `True` unconditionally to keep tests deterministic — real impl will return `bool` from citizen input. FR-027 pins the single async method signature. |
| D8 | **Cooperative cancellation via `asyncio.CancelledError` propagation, ≤ 500 ms bound** | AutoGen cooperative cancellation pattern | Claude Agent SDK async-generator cancellation (`docs/vision.md § Layer 1` carryover) | `asyncio.create_task` + `asyncio.CancelledError` are stdlib primitives; no new dep. 500 ms is derived from Phase 1 single-agent timeout expectations and Spec 019's per-session semaphore timing. SC-003 asserts the wall-clock bound. |
| D9 | **Closed discriminated union on `msg_type` for `AgentMessage.payload`** | Pydantic v2 `Field(discriminator=...)` pattern — `pydantic/pydantic-ai` tool-use schema assembly (`docs/vision.md § Reference materials` row 3) | Constitution Principle III ("no `Any` in I/O schemas") | Without a closed discriminator, `payload: dict[str, Any]` would be the default and Principle III would be violated. Six branches (`TaskPayload`, `ResultPayload`, `ErrorPayload`, `PermissionRequestPayload`, `PermissionResponsePayload`, `CancelPayload`) correspond 1:1 to the six `msg_type` values. FR-016 makes this binding. |
| D10 | **Worker tool registry hard-restricted to `{"lookup", "resolve_location"}`** | Epic #507 — "2-tool facade: lookup + resolve_location + 4 seed adapters" | `docs/design/mvp-tools.md` — MVP tool surface contract | Exposing per-API tools at the agent layer would mean 5000+ tool definitions in every worker prompt — infeasible. The 2-tool facade is the architectural constraint set by #507 and this Epic consumes it. FR-011 makes this binding. |
| D11 | **Nested tool calls forbidden (coordinator never calls tools, workers never spawn sub-workers)** | NESTful paper (arXiv:2409.03797) — nested tool calls amplify failure 17× | `docs/vision.md § Layer 4` — flat dispatch canon | Nesting would turn a 2% per-tool failure rate into a 34% end-to-end failure. Spec's "Out of Scope (Permanent)" section makes this a non-negotiable architectural rule. |
| D12 | **Reuse per-session LLM semaphore from Spec 019** (no new rate-limit infra) | Spec 019 hardening — `specs/019-phase1-hardening/` | FriendliAI Tier 1 budget (60 RPM) — project memory | Each `LLMClient` instance already holds a per-session semaphore with exponential backoff. Coordinator + N workers share this instance per `AgentContext`, so rate-limit budget is auto-managed. Spec 019 assumption noted in spec § Assumptions. |
| D13 | **`kosmos.agent.*` OTel attribute namespace**, spans `gen_ai.agent.coordinator.phase` / `gen_ai.agent.worker.iteration` / `gen_ai.agent.mailbox.message` | Spec 021 — OTel GenAI v1.40 attribute boundary | Spec 501 — OTLP collector boundary table | Extending an existing namespace keeps Epic #501's collector schema additive. All new names are declared as constants in `src/kosmos/observability/semconv.py` (FR-031) so Epic #501 can pull them into its boundary table without string duplication. |
| D14 | **Env-var additions via `KosmosSettings` catalog** (`src/kosmos/settings.py`) | Spec 468 — Secrets & Config + pydantic-settings | AGENTS.md hard rule — `KOSMOS_` prefix | Four new fields (`agent_mailbox_root`, `agent_mailbox_max_messages`, `agent_max_workers`, `agent_worker_timeout_seconds`) clamp with `Field(ge=..., le=...)` per #468's precedent. `docs/configuration.md` gets a new "Agent Swarm" section. FR-032..FR-036 binding. |
| D15 | **Pydantic v2 frozen `AgentContext` with `arbitrary_types_allowed=True`** | `src/kosmos/engine/models.py::QueryContext` precedent (Spec 005) | Pydantic v2 docs | `LLMClient` and `ToolRegistry` are non-Pydantic infra objects. The frozen constraint prevents workers from mutating shared state — Constitution II alignment. Matches the existing Layer 1 pattern exactly. |
| D16 | **`CoordinatorPlan` references `correlation_id` of every contributing worker result** (zero-orphan-id invariant) | OpenAI Agents SDK retry-matrix correlation pattern | Anthropic Cookbook orchestrator-workers output shape | Without correlation-ID traceability, synthesis failures cannot be diagnosed (which worker's result caused the wrong plan?). SC-002 makes zero-orphan-id the acceptance criterion. |

### References that this Epic does NOT use (and why)

- **Langfuse / Prompt Registry** (Spec 026): no new prompts ship in this Epic. Ministry-specialist prompts are #14. Spec 026's manifest is not extended here.
- **`rank_bm25` / retrieval** (Spec 022): no new retrieval surface. Workers see the 2-tool facade, which already embeds retrieval inside `lookup(mode="search")`.
- **Tool Security Spec v1 / v6** (Specs 024 / 025): worker tool registry inherits the already-validated v6 invariants from the #507 adapters — no new adapter means no new security surface.
- **Infisical OIDC** (Spec 468 follow-on): agent env vars live in the standard `KOSMOS_*` namespace; no secret material is introduced (the mailbox stores message bodies, which may contain citizen data, but that is a Layer 3 PII concern, not a secrets-management concern).

---

## 2. Resolved clarifications

The spec template requires that every "NEEDS CLARIFICATION" be resolved before Phase 1. Re-reading `spec.md`, no "NEEDS CLARIFICATION" tokens remain — every FR, entity, and edge case is concretely specified. The following implicit ambiguities surfaced during plan authoring are resolved here:

| # | Ambiguity | Resolution | Cite |
|---|---|---|---|
| C1 | What is the `sender_id` of the coordinator? | Fixed string `"coordinator"` (also the string used in `recipient` field when a worker addresses the coordinator). Written to mailbox as `<session_id>/coordinator/`. | Mirrors `AutoGen` `AgentId("coordinator")` pattern. |
| C2 | What is the `sender_id` of a worker? | `worker-<specialist_role>-<uuid4>` — stable for the worker's lifetime, unique across a session. Written to mailbox as `<session_id>/worker-<role>-<uuid>/`. | Pattern mirrors Claude Code agent spawn IDs (sourcemap analysis). |
| C3 | What happens if two workers spawn with the same `specialist_role` in the same session? | Permitted — each gets its own UUID suffix so mailbox paths remain unique. The coordinator treats them as independent research threads. | Anthropic Cookbook allows N workers per role. |
| C4 | How does replay distinguish "consumed" from "unconsumed" messages across crashes? | Each message file `<id>.json` has a sibling marker `<id>.json.consumed` written AFTER the reader has processed it. Replay scans for `.json` files without a matching `.consumed` marker. The marker is created atomically via `os.rename` on a temp file to guarantee crash-safety. | POSIX rename-atomicity pattern used by mail-transfer agents (mbox, maildir). |
| C5 | What is the fsync ordering contract? | The message body file is fully written + `os.fsync(fd)` + `close(fd)` + `os.fsync(dir_fd)` before `send()` returns. The `.consumed` marker is written under the same ordering. | POSIX `fsync(2)` + `sync_file_range(2)` idiom; Linux/macOS both honor. |
| C6 | What happens if `KOSMOS_AGENT_MAILBOX_ROOT` does not exist on coordinator startup? | The coordinator creates it with `mkdir(..., parents=True, exist_ok=True)` and mode `0o700` (user-only). If creation fails, coordinator startup raises `MailboxWriteError` — fail-closed. | `pathlib.Path.mkdir` semantics; matches the fail-closed posture of Constitution II. |
| C7 | Can the same `correlation_id` appear in multiple `result` messages (worker retry)? | Yes, but the coordinator MUST take the first non-error result and WARN on duplicates (spec Edge Cases row 3). No duplicate in `CoordinatorPlan.worker_correlation_ids`. | Spec edge cases row 3. |
| C8 | What is the worker's behavior if its `asyncio.Task` is cancelled MID-fsync during a mailbox write? | The message file is considered partially written — crash-replay will skip it at WARNING level (FR-020). The worker propagates `CancelledError` immediately and does NOT attempt a retry. | fsync is not atomic at the file level; partial files are expected and handled by D20 below. |
| C9 | Does `replay_unread` apply across process restarts with DIFFERENT `session_id`? | No. Replay is scoped strictly to `<session_id>`. Cross-session memory is out of scope and deferred to Phase 3 (spec Deferred Items row 5). | Spec FR-019 + Deferred Items. |
| C10 | What is the `ConsentGateway` method signature exactly? | `async def request_consent(self, tool_id: str, correlation_id: UUID) -> bool` — returns `True` for grant, `False` for deny. The stub always returns `True`. Production impl (from #287) will prompt the citizen. | FR-027. |

---

## 3. Deferred Items validation (Constitution VI gate)

Re-reading `spec.md § Scope Boundaries & Deferred Items`:

### Out of Scope (Permanent) — 4 items
- Individual adapter tool registration at the agent layer — architectural constraint per `docs/vision.md § Layer 4` + `docs/design/mvp-tools.md`. **Reference cited. OK.**
- Nested tool calls — NESTful arXiv:2409.03797. **Reference cited. OK.**
- Lateral permission flow — Constitution Principle II. **Reference cited. OK.**
- Live `data.go.kr` API calls in CI — Constitution Principle IV. **Reference cited. OK.**

### Deferred to Future Work — 8 rows

| Item | Tracking | Verification |
|---|---|---|
| Ministry specialist system prompts | #14 | **OPEN** — verified via `gh issue view 14` 2026-04-18. |
| TUI rendering | #287 | **OPEN** — verified via `gh issue view 287` 2026-04-18. |
| Production hardening (DLQ, cross-process, retry budgets) | #21 | **OPEN** — verified via `gh issue view 21` 2026-04-18. |
| Redis Streams mailbox backend | NEEDS TRACKING | Will be resolved by `/speckit-taskstoissues` — placeholder issue created in next phase. |
| Cross-session agent memory | NEEDS TRACKING | Will be resolved by `/speckit-taskstoissues`. |
| Account-wide LLM rate-limit orchestration | NEEDS TRACKING (has `Epic #21 / Layer 6` hint) | Will be resolved. |
| Scenario graph / multi-turn planning | NEEDS TRACKING | Will be resolved. |
| Agent-to-agent handoff | NEEDS TRACKING | Will be resolved. |
| Formal OTel upstream registration | NEEDS TRACKING | Will be resolved. |

### Free-text deferral scan

Grep of `spec.md` for the patterns in Constitution VI:

- "separate epic" — 1 hit inside the Deferred Items table (row "Production hardening") — **tracked (#21)**, OK.
- "future epic" — 0 hits.
- "Phase 2"/"Phase 3" — multiple hits, all either referencing the current epic's phase or inside the Deferred Items table. **OK.**
- "v2" — 0 hits.
- "deferred to" — only inside the Deferred Items table. **OK.**
- "later release" — 0 hits.
- "out of scope for v1" — 0 hits.

**Deferred Items gate result**: PASS. `/speckit-taskstoissues` will resolve the 6 `NEEDS TRACKING` markers into real placeholder issues.

---

## 4. Key non-goals (re-stated for implementers)

- No change to Layer 1 `QueryEngine` public API. `Worker` composes `_query_inner`; it does not modify it.
- No change to Layer 2 `ToolRegistry` type signatures. `AgentContext.tool_registry` wraps an existing registry with an allow-list assertion.
- No change to Layer 3 `PermissionPipeline`. The `ConsentGateway` is a new abstraction at Layer 4 that sits AHEAD of the pipeline — it decides whether to even attempt the protected tool call.
- No change to Layer 5 Context Assembly. System prompts for coordinator / worker are inlined in this Epic as stub strings; the real prompts are Epic #14.
- No change to Layer 6 Error Recovery. Worker errors surface as `error` messages to the coordinator; Layer 6 retry policy is inherited unchanged from Phase 1.
- No change to TUI. The `ConsentGateway` stub is the only integration point; the real TUI prompt is #287.

---

## 5. Risks and open questions (non-blocking)

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| fsync on macOS CI is weaker than Linux (known kernel difference) | Medium | Crash-replay test may be flaky on macOS CI | Use `os.fsync(dir_fd)` after `os.fsync(fd)` (both platforms honor this); document the contract in `contracts/mailbox-abi.md`. |
| Worker starves the coordinator LLM budget under `MAX_WORKERS=16` | Low (default is 4) | Rate-limit 429 cascades | Already mitigated by Spec 019 per-session semaphore + exponential backoff; no new infra. |
| `asyncio.CancelledError` may not propagate through a blocking `json.dump` call during mailbox write | Low | Cancellation exceeds 500 ms bound | Use `asyncio.to_thread()` for fsync-heavy writes so the event loop stays responsive; SC-003 test enforces the bound. |
| Epic #501 attribute boundary table not yet merged | Medium | `kosmos.agent.*` names might need renaming later | FR-031 requires submission to #501 before any collector deploys; rename cost is string-constant scope only. |
| Epic #14 ministry prompts may reveal missing `AgentContext` fields (e.g., ministry-specific memory pointers) | Medium | Late additive changes to `AgentContext` | Keep `AgentContext` frozen; Epic #14 adds new fields additively — no type-breaking change expected. |

---

## Phase 0 Exit Checklist

- [x] All "NEEDS CLARIFICATION" markers resolved (0 present in spec; 10 implicit ambiguities resolved here).
- [x] Every decision in plan.md traced to a reference row in `docs/vision.md § Reference materials` or to an upstream Epic.
- [x] Deferred Items table validated; 2 existing issues (#14, #287, #21) confirmed OPEN; 6 `NEEDS TRACKING` markers flagged for `/speckit-taskstoissues`.
- [x] No untracked free-text deferrals ("separate epic", "v2", "future phase") outside the Deferred Items table.
- [x] Constitution Principles I / II / III / IV / V / VI re-verified against the plan's architectural shape.

**Phase 0 gate**: PASS. Proceed to Phase 1 design artifacts.
