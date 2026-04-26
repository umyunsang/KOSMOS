# Phase 0 Research — P3 · Tool System Wiring

**Branch**: `feat/1634-tool-system-wiring` | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md)
**Epic**: #1634 | **Phase**: P3 (per `docs/requirements/kosmos-migration-tree.md § Execution phases`)

> Per Constitution v1.1.1 § I and AGENTS.md "Reference source rule," every design decision below maps first to the **restored-src primary reference** (`.references/claude-code-sourcemap/restored-src/src/`, Claude Code 2.1.88). Escalations to secondary references from `docs/vision.md § Reference materials` are documented inline.

---

## 1. Reference map — every decision → CC source

P3 introduces five distinct concerns. Each maps to a concrete CC restored-src path or, where CC has no analog, an explicit secondary reference from the vision document.

### 1.1 Primitive wrappers (4) — `tui/src/tools/primitive/`

Spec 031 already mapped each primitive to its CC analog (see `specs/031-five-primitive-harness/research.md § 1`). P3 inherits that mapping verbatim:

| KOSMOS primitive | CC analog (primary, restored-src 2.1.88) | Shape carried over |
|---|---|---|
| `lookup` (`mode=search`) | `src/tools/GrepTool/` + `src/tools/ToolSearchTool/` | BM25 over `search_hint`, no side effects, idempotent |
| `lookup` (`mode=fetch`) | `src/tools/FileReadTool/` + `src/tools/WebFetchTool/` | Deterministic, cache-friendly, idempotent |
| `submit` | `src/tools/BashTool/` (single side-effecting tool gated by `bashPermissions.ts` + `bashSecurity.ts`) | `{tool_id, params}` envelope, permission-gated |
| `verify` | `src/services/oauth/` + `src/tools/McpAuthTool/` (CC delegates credentials, never mints) | Discriminated union over credential families |
| `subscribe` | No byte analog in CC tools; closest is `src/services/SessionMemory/` + `src/tools/shared/` async generator streaming | `AsyncIterator[Event]` with handle lifetime |

**Decision**: P3 builds the TUI-side wrappers (`tui/src/tools/primitive/{lookup,submit,verify,subscribe}.ts`) as thin dispatchers that translate CC's tool-call shape into the existing Python `kosmos.primitives.*` module calls. The Python primitives already exist (Spec 031 shipped `submit.py`, `subscribe.py`, `verify.py`); `lookup` lives in `src/kosmos/tools/lookup.py`. P3 does **not** rewrite Python primitive code — only adds TUI wrappers and the MCP transport layer between them.

**Rationale**: keeping primitive logic in Python (where adapter validation happens) preserves the AGENTS.md hard rule that all adapter I/O is Pydantic v2. The TUI wrapper just shapes the tool-call envelope; it does not validate adapter parameters.

**Alternatives considered**:
- TS-side primitive logic with a re-implemented adapter registry — rejected: violates AGENTS.md "no Go/Rust/duplicate-substrate" + duplicates Spec 022/025/031 work.
- Single primitive wrapper that switches on `primitive` enum at runtime — rejected: harder to unit-test in isolation and obscures the four-primitive contract.

### 1.2 MCP bridge — `tui/src/ipc/mcp.ts` + `src/kosmos/ipc/mcp_server.py`

**Primary reference**: `src/tools/MCPTool/MCPTool.ts` (CC's external-MCP passthrough — already in restored-src). It demonstrates the MCP message envelope shape the LLM expects from a registered MCP tool.

**Secondary reference**: Anthropic's `mcp` Python SDK + `@modelcontextprotocol/sdk` TS SDK (both already shipped, no new deps).

**Decision**: The MCP bridge is **additive** on top of the existing Spec 287/032 IPC stack:
- `tui/src/ipc/mcp.ts` is a thin client that constructs MCP-protocol frames and hands them to `bridge.ts` for stdio transport.
- `src/kosmos/ipc/mcp_server.py` is a thin server stub that consumes MCP-protocol frames from `stdio.py` and dispatches to the existing tool registry.
- Neither side re-implements framing, ring-buffer, back-pressure, or heartbeat — those are Spec 032 responsibilities and stay untouched.

**Rationale**: this preserves all of Spec 032's hardening work (correlation IDs, transaction LRU, ring buffer, heartbeat) without duplicating it at the MCP layer. The MCP layer carries protocol concerns (handshake, tool list, tool call routing) only.

**Alternatives considered**:
- Replace `bridge.ts` ↔ `stdio.py` with raw MCP transport — rejected: would re-implement Spec 032 hardening from scratch + invalidate prior IPC test coverage.
- Run MCP-over-HTTP instead of stdio — rejected: violates Constitution § Citizen privacy (no external egress) + AGENTS.md zero-egress observability rule (Spec 028).

### 1.3 Adapter registry deltas — `src/kosmos/tools/{models.py, register_all.py, routing_index.py, permissions.py}`

**Primary reference**: `src/services/tools/toolOrchestration.ts` + `src/services/tools/toolExecution.ts` (CC's tool registration + execution loop — already in restored-src).

**Secondary references**: Pydantic AI tool registry pattern (schema-driven typed registration); Spec 025 v6 invariant module (`src/kosmos/security/v12_dual_axis.py`) for the `(auth_type, auth_level)` invariant we must preserve.

**Decision (clarification Q1 — `adapter_mode`)**: Add a new field `adapter_mode: Literal["live", "mock"] = "live"` on `GovAPITool`. Mock adapters in `src/kosmos/tools/mock/*` set `adapter_mode="mock"` explicitly. The existing `AdapterRegistration.source_mode` (`OPENAPI` / `OOS` / `HARNESS_ONLY`) stays as mirror-fidelity classification; the two axes are orthogonal.

**Rationale**: confirmed by reading `src/kosmos/tools/registry.py:48-58` — `AdapterSourceMode` documents itself as "how faithfully the adapter mirrors its external source," not "does this adapter call the network at runtime." Conflating them breaks the OPENAPI-mock case (a mock built from a published OpenAPI spec — high fidelity, runs as mock).

**Decision (clarification Q2 — `ministry`)**: Rename `provider: str` → `ministry: Literal[<closed enum>]` with the initial enum: `KOROAD, KMA, NMC, HIRA, NFA, MOHW, MOLIT, MOIS, KEC, MFDS, GOV24, OTHER`. All 15 currently-registered adapters migrate at the same commit.

**Rationale**: Spec 025 v6 already uses the same Literal-typed pattern for `auth_type` (`Literal["public", "api_key", "oauth"]`) — pattern parity. Free-form `provider` strings would diverge in spelling across plugin authors and break ministry-scoped consent (Spec 035 onboarding) which needs machine-checkable ministry identity. `OTHER` is a transitional escape hatch for adapters whose institutional mapping is not yet decided; CI emits a warning when used (per Assumption added to spec.md).

**Decision (clarification Q3 — `permission_tier`)**: Introduce a derived helper `compute_permission_tier(auth_level: AALLevel, is_irreversible: bool) -> Literal[1, 2, 3]` in `src/kosmos/tools/permissions.py`. No new field. Mapping:

```
public/AAL1                            → 1
AAL2                                   → 2
AAL3                                   → 3
is_irreversible=True (overrides AAL)   → 3
```

**Rationale**: Spec 025 v6 (`src/kosmos/tools/models.py:313-327`) enforces a strict `(auth_type, auth_level)` allow-list. Adding a third permission axis would introduce drift risk (the helper might disagree with the validator). A pure derived function reads from existing fields, has zero state, and is unit-testable in isolation. UI-C C1 (layer color rendering) and the permission gauntlet both call this single function.

**Alternatives considered**:
- Store `permission_tier` as a third field with a validator that asserts consistency with `(auth_level, is_irreversible)` — rejected: more code, more failure modes, no benefit.
- Skip the helper and compute inline at every call site — rejected: scattered logic, drift risk between TUI display and audit ledger interpretation.

### 1.4 CC dev tool removal — deletions only

**Primary reference**: the full directory list under `src/tools/` in restored-src — KOSMOS deletes the developer-oriented subset because the citizen domain has no use for filesystem mutation, shell execution, or Jupyter notebook editing.

**Decision**: delete the 14 directories listed in spec.md FR-012 (Bash, FileEdit, FileRead, FileWrite, Glob, Grep, NotebookEdit, PowerShell, LSP, REPL, Config, Plan/Worktree mode tools). Add a CI grep guard at the runtime registration entry points.

**Rationale**: `feedback_harness_not_reimplementation` — KOSMOS is a harness that *uses* CC's substrate, not a re-implementation of CC. Tools that don't serve citizens are deleted, not stubbed. Stubs would create resurrection risk (a future PR adds them back without thinking).

**Alternatives considered**:
- Keep the directories but `delete export` from the registration index — rejected: dead code accumulates and tools can be re-imported by accident.
- Move them under a `dev-only/` subtree — rejected: KOSMOS is not a developer tool. There is no "dev mode."

### 1.5 New auxiliary tools — Translate, Calculator, DateParser, ExportPDF

**Primary reference**: no direct CC analog (CC has no Translate or PDF export — its domain is code).

**Secondary references**:
- Translate: delegates to FriendliAI EXAONE itself (no external translation API). Existing Spec 022 LLM call path is reused. No new dep.
- Calculator: stdlib `decimal` + `math`. No new dep.
- DateParser: stdlib `datetime` + `zoneinfo` (Asia/Seoul TZ defaults). No new dep.
- ExportPDF: existing `pdf-to-img` WASM (already shipped in TUI per UI-B B.3 decision); on the Python side, fixture export via stdlib `reportlab`-free path — defer the actual PDF rendering choice to a single-decision point in `data-model.md § ExportPDF`.

**Decision**: each auxiliary tool ships with `input_schema` + `output_schema` + bilingual `search_hint` per Constitution § III, and is registered alongside the existing aux tools.

**Rationale**: the migration tree (`§ L1-C C6`) lists exactly these four as the MVP-7 additions on top of the existing 3 (WebFetch, WebSearch, Task). Building all four in P3 closes the auxiliary surface for the citizen-facing release; Phase-2 adds TextToSpeech, SpeechToText, LargeFontRender, OCR, Reminder.

---

## 2. Resolved unknowns from spec.md

All three NEEDS CLARIFICATION markers in spec.md were resolved during `/speckit-clarify` Session 2026-04-24 (recorded in spec.md § Clarifications). Phase 0 ratifies those decisions:

- **Q1 (FR-009 adapter_mode)** — RESOLVED: new `adapter_mode: Literal["live","mock"] = "live"` field on `GovAPITool`. See § 1.3 for full rationale.
- **Q2 (FR-010 ministry)** — RESOLVED: rename `provider` → `ministry` with `Literal[<closed enum>]` typing. See § 1.3.
- **Q3 (FR-011 permission_tier)** — RESOLVED: derived helper `compute_permission_tier()`, no new field. See § 1.3.

**No unresolved clarifications remain.** Phase 1 may proceed.

---

## 3. Best practices research

### 3.1 BM25 + dense hybrid retrieval routing

**Question**: how does `lookup(mode="search")` partition results across adapters whose `primitive` differs?

**Decision**: BM25 + dense scoring is computed *across all adapters* (regardless of primitive). The result list is **filtered post-scoring** by primitive only when the LLM call provides an optional `primitive` filter argument; otherwise all primitives are returned with their `primitive` field surfaced in the response so the LLM can reason about the next call.

**Rationale**: citizen prompts are typically primitive-agnostic ("how do I report this?", "where do I check this?"). Pre-filtering by primitive would force the LLM to issue multiple search calls. Spec 022 already established this pattern; P3 adds the `primitive` field to results without changing the scoring or top-K logic.

**Reference**: `src/kosmos/tools/search.py` (Spec 022 BM25), `feat/585-retrieval-dense` (dense layer).

### 3.2 MCP handshake performance budget

**Question**: SC-004 sets handshake budget at < 500 ms cold, < 100 ms warm. Is this achievable over stdio with `bridge.ts` Spec 032 hardening?

**Decision**: Yes. `bridge.ts` Spec 287/032 already achieves stdio frame round-trip under 10 ms warm on developer machines. MCP handshake is 2 frame exchanges (initialize + initialized notification) + tool list discovery (1 frame). Budget headroom is ~10x the measured baseline.

**Rationale**: stdio JSONL framing is local IPC; dominant cost is process startup (Python interpreter + module imports), not transport. Cold-start budget gives Python's `kosmos.tools.register_all` ~400 ms, which matches the current observed Spec 022 cold-start.

**Reference**: `tui/src/ipc/bridge.ts` (transport), `tests/ipc/test_stdio_roundtrip.py` (Spec 032 baseline).

### 3.3 Routing-consistency CI gate failure modes

**Question**: what failure modes must `tests/tools/test_routing_consistency.py` cover beyond "primitive=None"?

**Decision**: the test enforces six invariants — full list in `contracts/routing-consistency.md`. Headlines:
1. Every registered adapter declares `primitive` in `{lookup, submit, verify, subscribe, resolve_location}`.
2. Every adapter declares `ministry` in the closed enum (no free-form fallback past the `OTHER` warning).
3. Every adapter declares `adapter_mode` in `{live, mock}`.
4. `tool_id` is unique across the entire registry.
5. `compute_permission_tier(auth_level, is_irreversible)` returns a value in `{1, 2, 3}` for every adapter (function totality check).
6. Spec 025 v6 invariant still holds for every adapter (delegated to existing `v12_dual_axis.enforce()`).

**Rationale**: a single CI gate centralizes governance. Failures must name the offending adapter + the specific invariant violated, so contributors can fix without spelunking.

---

## 4. Deferred Items validation (Constitution § VI gate)

Read from spec.md § Scope Boundaries & Deferred Items. Verification:

| Item | Tracking | GraphQL verification |
|---|---|---|
| Plugin adapter SDK + 5-tier DX | #1636 P5 | OPEN, verified during /speckit-clarify |
| `docs/api/` per-adapter Markdown + JSON Schema/OpenAPI | #1637 P6 | OPEN, verified during /speckit-clarify |
| TUI rendering of tool_use/tool_result blocks | #1635 P4 | OPEN, verified during /speckit-clarify |
| Phase-2 auxiliary tools (TextToSpeech, SpeechToText, LargeFontRender, OCR, Reminder) | NEEDS TRACKING | Will be created by /speckit-taskstoissues as Phase-2 placeholder |
| Cross-session subscribe-handle resumption | NEEDS TRACKING | Will be created by /speckit-taskstoissues as Spec 031 follow-up |
| Reclassification of undecided tools | NEEDS TRACKING | Will be resolved per-tool in /speckit-tasks; remaining undecideds become a P4/P5 placeholder |

**Free-text deferral pattern scan** (`grep -E "future epic|separate epic|Phase [2-9]|deferred to|out of scope for v1" specs/1634-tool-system-wiring/spec.md`):
- Matches inside Out-of-Scope-Permanent list — OK.
- Matches inside Deferred Items table — OK.
- No matches outside these structures — **PASS**.

Constitution § VI gate: **PASS**.

---

## 5. Documented constitution deviation

### 5.1 `adapter_mode` defaults to `"live"` (not fail-closed)

Constitution § II requires fail-closed defaults for new boolean/enum fields on `GovAPITool`. `adapter_mode = "live"` violates the *literal* reading of that principle.

**Justification**: the principle's intent is to prevent a contributor from accidentally exposing a personal-data API as public. With `adapter_mode`, the failure mode is inverted: a `"mock"` default would silently ship fixture data to a real citizen. **Fail-explicit > fail-safe** here because:

1. Mock adapters live in a clearly-segregated subtree (`src/kosmos/tools/mock/*`); the maintainer of every mock adapter has direct line-of-sight to set `adapter_mode="mock"`.
2. Live adapters are the production case; an undeclared adapter should *be* live, not silently degraded to a fixture.
3. The CI consistency test (§ 3.3 invariant 3) verifies `adapter_mode ∈ {live, mock}` is declared on every registration, so "default" never silently propagates — the field is effectively required, with `"live"` only used when omitted by an obviously-live adapter under `src/kosmos/tools/{koroad,kma,hira,nmc,nfa,mohw}/`.

This deviation is recorded in plan.md § Complexity Tracking. No other field gets a non-fail-closed default in this epic.

---

## 6. Phase 1 readiness check

| Phase 1 deliverable | Inputs ready? |
|---|---|
| `data-model.md` | Yes — all field deltas resolved in § 1.3 above |
| `contracts/primitive-envelope.md` | Yes — Spec 031 envelope is canonical, P3 inherits |
| `contracts/mcp-bridge.md` | Yes — § 1.2 above + MCP SDK docs |
| `contracts/routing-consistency.md` | Yes — § 3.3 above |
| `quickstart.md` | Yes — quickstart targets the post-P3 contributor adding a new adapter; § 1.3 + § 1.5 cover the field surface they need to know |

**Phase 0 status**: COMPLETE. All NEEDS CLARIFICATION markers resolved, all constitution gates passed (with one documented deviation), all Deferred Items validated. Phase 1 may proceed.
