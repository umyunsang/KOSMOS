# Feature Specification: P3 · Tool System Wiring (4 Primitives + Python stdio MCP)

**Feature Branch**: `feat/1634-tool-system-wiring`
**Created**: 2026-04-24
**Status**: Draft
**Epic**: #1634
**Phase**: P3 (per `docs/requirements/kosmos-migration-tree.md § Execution phases`)
**Canonical references**: `docs/requirements/kosmos-migration-tree.md § L1-B` (도구 시스템) · `§ L1-C` (메인 동사 추상화) · `docs/vision.md` (six-layer harness, Claude Code reference thesis)
**Input**: User description: "Wire Python adapters in src/kosmos/tools/ as the LLM tool surface via stdio MCP. Expose 4 reserved primitives (lookup/submit/verify/subscribe) plus auxiliary tools. Remove all Claude Code developer-oriented tools from the runtime path."

---

## Background and Mission Anchor

KOSMOS migrates the Claude Code harness from the developer domain to the Korean public-service domain. P0 (#1632) restored the CC 2.1.88 baseline; P1+P2 (#1633) eliminated dead code and migrated the LLM provider to FriendliAI + EXAONE. **P3 is where the LLM stops seeing developer tools and starts seeing the four citizen-facing primitives wired to real Korean public-service adapters.**

This is the load-bearing transition: after P3, the LLM's entire tool surface is `lookup` · `submit` · `verify` · `subscribe` (plus a small set of auxiliary utilities), with all 15 currently-registered Python adapters reachable by name through the `lookup(mode="fetch", tool_id=…)` envelope. CC's developer tools (Bash, FileEdit, Glob, Grep, etc.) must no longer appear in the runtime registry.

---

## Clarifications

### Session 2026-04-24

- Q: Should the runtime live-vs-mock distinction be a new field on `GovAPITool`, or derived from the existing `AdapterRegistration.source_mode` axis? → A: Add a new `adapter_mode: Literal["live","mock"]` field on `GovAPITool` with default `"live"`. The existing `AdapterRegistration.source_mode` (OPENAPI / OOS / HARNESS_ONLY) classifies *mirror fidelity* and is a different axis; conflating them is incorrect (e.g., a HARNESS_ONLY mock and an OPENAPI mock both run as `mock` at runtime, while an OPENAPI live adapter and an OPENAPI mock share source_mode but differ at runtime).
- Q: Should the ministry/agency owner be a free-form `provider` string (status quo), a renamed-and-typed `ministry: Literal[…]`, or both? → A: Rename `provider` → `ministry` and type it as `Literal[<closed enum>]` covering the recognized institutions (KOROAD, KMA, NMC, HIRA, NFA, MOHW, MOLIT, MOIS, KEC, MFDS, GOV24, OTHER as escape hatch). Single source of truth; same pattern Spec 025 v6 uses for `auth_type`. Cost: mechanical edit across the 15 registered adapters. Plugin DX gains a typed enum to filter against.
- Q: Should `permission_tier: Literal[1,2,3]` be a new field on `GovAPITool`, or derived from existing fields? → A: Derive via a helper `compute_permission_tier(auth_level, is_irreversible) -> Literal[1,2,3]` — no new field. Mapping: `public`/`AAL1` → 1; `AAL2` → 2; `AAL3` → 3; `is_irreversible=True` → 3 unconditionally (overrides the AAL mapping). Preserves the Spec 025 v6 `(auth_type, auth_level)` invariant without introducing a second auth axis. UI-C C1 layer color (green/orange/red) reads this helper directly.

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — A citizen looks up an emergency hospital through the LLM (Priority: P1)

A Seoul citizen tells the assistant "근처 응급실 알려줘" (find me a nearby emergency room). The LLM resolves the location, calls the `lookup` primitive in `search` mode to discover the right adapter, then calls `lookup` in `fetch` mode against `hira_hospital_search` (or `nmc_emergency_search`), and returns hospital options with addresses and phone numbers.

**Why this priority**: This is the single most representative end-to-end flow for the entire L1-B+L1-C pillar. If this works, the citizen sees the harness; if it fails, P3 has not delivered. Every other story extends this loop.

**Independent Test**: With KOSMOS booted and FriendliAI provider active, send a one-turn citizen prompt asking for an emergency-room lookup near a Korean address. The LLM must (a) only see `lookup` in its tool surface (not see `hira_hospital_search` directly), (b) issue a `lookup(mode="search", query=…)` call that returns candidate `tool_id`s, (c) issue a `lookup(mode="fetch", tool_id=…, params=…)` call that hits the real adapter, (d) return a citizen-readable answer. No CC dev tool may appear in the trace.

**Acceptance Scenarios**:

1. **Given** a fresh KOSMOS session with the citizen-facing system prompt loaded, **When** the citizen asks for an emergency room near a Korean address, **Then** the LLM completes the request using only `lookup` (with internal `search` then `fetch` calls) and returns at least one hospital result with name + address.
2. **Given** the LLM's exposed tool list during the same session, **When** an operator inspects what the LLM actually sees, **Then** the list contains the four primitives plus the agreed auxiliary set, and contains zero entries from the CC dev-tool list (BashTool, FileEditTool, FileReadTool, FileWriteTool, GlobTool, GrepTool, NotebookEditTool, PowerShellTool, LSPTool, EnterWorktreeTool, ExitWorktreeTool, EnterPlanModeTool, ExitPlanModeTool, REPLTool, ConfigTool).
3. **Given** the BM25 retrieval index is rebuilt at adapter-registration time, **When** `lookup(mode="search")` is called for "응급실", **Then** the top results include both `hira_hospital_search` and `nmc_emergency_search`, scored by Korean morpheme tokenization.

---

### User Story 2 — A citizen submits a civic action through the `submit` primitive (Priority: P2)

A citizen asks the assistant to file a road-hazard report. The LLM calls the `submit` primitive against the relevant adapter (mock-tier in this epic, since live submission portals like 정부24 / KEC e-signature are OPAQUE per `feedback_mock_evidence_based`). The user is shown a permission gauntlet (Layer 2 or Layer 3, per Spec 033) before the submit call executes; on consent the adapter returns a receipt.

**Why this priority**: `submit` is the second of the four primitives and the first one that crosses the irreversible-action boundary. It validates that primitive-level routing also flows through the existing permission system without primitive-default leakage (per `§ L1-C C5`: permissions live at the adapter layer only).

**Independent Test**: With KOSMOS in non-bypass permission mode, run a citizen prompt that triggers a `submit`-mode adapter (mock). The permission modal must appear, the receipt ID must be displayed on consent, the adapter must return a structured response, and no permission rule may be inferred from the primitive name alone.

**Acceptance Scenarios**:

1. **Given** the citizen consents to a `submit`-mode adapter call, **When** the call completes, **Then** the receipt ID appears in the conversation transcript and an audit ledger entry is written.
2. **Given** the citizen denies the same call, **When** the LLM receives the denial, **Then** it surfaces a citizen-readable refusal explaining the action was not performed, and no adapter call is issued.
3. **Given** an adapter declares `primitive="submit"` and a permission tier independently of that primitive, **When** the routing index is built at boot, **Then** the index records both fields without merging or inferring one from the other.

---

### User Story 3 — An operator boots KOSMOS and the routing index fails closed if any adapter is misconfigured (Priority: P3)

An operator (or CI) starts KOSMOS. During boot, `build_routing_index()` walks the registered adapters and verifies that each one declares a non-null `primitive` and that the adapter's `tool_id` is unique. If any adapter is missing the primitive field, the boot fails with a clear error naming the offending adapter and the field gap. CI runs the same check via `tests/tools/test_routing_consistency.py`.

**Why this priority**: This is the governance gate that prevents P3 from silently regressing in P4/P5. Without it, future plugin or adapter additions can ship with `primitive=None` and the LLM's discovery surface becomes inconsistent.

**Independent Test**: Run the routing-consistency test with the current 15 registered adapters — must pass. Inject a temporary adapter with `primitive=None`, re-run the test — must fail with a message naming the adapter. Remove the temporary adapter, re-run — passes again.

**Acceptance Scenarios**:

1. **Given** all 15 currently-registered adapters have their `primitive` field populated, **When** `build_routing_index()` runs at boot, **Then** the index lists every adapter under its declared primitive bucket and the boot proceeds.
2. **Given** any adapter has `primitive=None`, **When** boot or CI runs the consistency check, **Then** it raises a fail-closed error naming the adapter; the harness does not start.
3. **Given** two adapters declare the same `tool_id`, **When** the index is built, **Then** the second registration is rejected with a duplicate-id error.

---

### User Story 4 — The LLM uses the `subscribe` primitive for a continuing weather alert (Priority: P3)

A citizen asks for ongoing severe-weather alerts for their region. The LLM calls `subscribe` against a KMA adapter; the harness returns a `SubscriptionHandle` and the LLM is informed it can rely on push-style updates within the session lifetime (handle scope per Spec 031). The handle is recorded in the audit trail; the citizen can revoke via `/consent revoke`.

**Why this priority**: `subscribe` is the only primitive whose lifecycle exceeds a single tool call. Wiring it now (against a mock or low-risk live adapter) ensures the four-primitive surface is complete and the system prompt examples cover the full set.

**Independent Test**: Send a citizen prompt requesting weather alerts for a region. The LLM must issue a `subscribe` call, the harness must return a handle with a session-bound TTL, and the conversation transcript must show the handle ID. Revocation via `/consent revoke rcpt-<id>` must invalidate the handle.

**Acceptance Scenarios**:

1. **Given** a `subscribe`-mode adapter is registered, **When** the LLM issues a subscribe call, **Then** the handle is returned, recorded in the audit ledger, and surfaced in the transcript.
2. **Given** a session ends, **When** the next session starts, **Then** prior subscribe handles do not auto-resume (handles are session-bound per Spec 031 unless an adapter explicitly supports cross-session resumption).

---

### Edge Cases

- **CC dev tool re-imported by accident**: A future PR (or merge from a vendor branch) re-introduces a `BashTool` import into the runtime registration path. The CI guard must catch this and fail.
- **Adapter declares an unknown primitive**: A new adapter sets `primitive="execute"` (not in the reserved four). Boot must reject it.
- **Plugin namespace collision with reserved primitives**: A plugin tries to register a top-level tool named `lookup` (instead of `plugin.<id>.lookup`). The registry must reject it per `§ L1-C C7`.
- **MCP transport handshake failure**: The TUI's `mcp.ts` client cannot complete the handshake with `mcp_server.py`. The harness must surface a clear "tool subsystem unavailable" error rather than letting the LLM see an empty tool list.
- **Auxiliary tool exposure inconsistency between TS and Python sides**: A tool is registered on the TS side but not on the Python side (or vice versa). The boot-time consistency check must flag the mismatch.

---

## Requirements *(mandatory)*

### Functional Requirements — Primitive surface

- **FR-001**: The LLM MUST see exactly four primitives — `lookup`, `submit`, `verify`, `subscribe` — at the top level of its tool surface, in addition to the auxiliary tool set defined in FR-020.
- **FR-002**: The system MUST implement primitive wrappers in the TUI tool layer such that each primitive has its own dispatcher entry that forwards to the Python adapter chosen by `tool_id`.
- **FR-003**: The system MUST NOT expose adapter-level tool_ids (e.g., `hira_hospital_search`) directly in the LLM-visible tool list; adapters are reachable only through the primitive envelope.
- **FR-004**: Each primitive call MUST carry its Spec 031 per-primitive envelope type — `SubmitEnvelope` (`submit`), `SubscriptionEvent` discriminated union (`subscribe`), `VerifyInput`/`VerifyOutput` (`verify`), and the existing Spec 022 lookup envelope (`lookup`) — with primitive-specific payload fields validated against the chosen adapter's schema. The envelope shapes are canonical from `specs/031-five-primitive-harness/data-model.md § 1-3` (and Spec 022 data-model for `lookup`); P3 does not introduce a new shared envelope.
- **FR-005**: The `lookup` primitive MUST support both modes: `search` (BM25 + dense hybrid retrieval over registered adapters) and `fetch` (direct adapter invocation by `tool_id`).

### Functional Requirements — Adapter metadata and registry

- **FR-006**: All 15 currently-registered Python adapters MUST declare a non-null `primitive` field. The system MUST NOT boot if any registered adapter has `primitive=None`.
- **FR-007**: The system MUST provide a central `build_routing_index()` function that, at boot and at every adapter (re-)registration, validates `primitive != None`, validates `tool_id` uniqueness, and constructs a primitive→adapter map for the BM25 retrieval index.
- **FR-008**: A CI test (`tests/tools/test_routing_consistency.py`) MUST execute `build_routing_index()` against the live registry and fail the build if validation fails.
- **FR-009**: The system MUST distinguish, per adapter, between live (real public API) and mock (recorded fixture or shape-compatible synthetic) sources via a new `adapter_mode: Literal["live","mock"]` field on `GovAPITool`, defaulting to `"live"`. Mock adapters MUST set `adapter_mode="mock"` explicitly. The existing `AdapterRegistration.source_mode` axis (OPENAPI / OOS / HARNESS_ONLY) MUST remain as mirror-fidelity classification and MUST NOT be conflated with runtime mode.
- **FR-010**: Adapter records MUST identify the operating ministry / institution via a typed `ministry: Literal[<closed enum>]` field on `GovAPITool` covering the recognized institutions (initial enum: `KOROAD`, `KMA`, `NMC`, `HIRA`, `NFA`, `MOHW`, `MOLIT`, `MOIS`, `KEC`, `MFDS`, `GOV24`, `OTHER`). The current free-form `provider: str` field MUST be renamed to `ministry` (single source of truth, same pattern Spec 025 v6 uses for `auth_type`). All 15 currently-registered adapters MUST be migrated to the typed field at the same commit boundary as the rename.
- **FR-011**: The system MUST expose a derived helper `compute_permission_tier(auth_level, is_irreversible) -> Literal[1,2,3]` that maps `public`/`AAL1` → 1, `AAL2` → 2, `AAL3` → 3, with `is_irreversible=True` overriding the AAL mapping to 3 unconditionally. No new `permission_tier` field MUST be added to `GovAPITool` — the helper is the single read-path used by UI-C C1 layer color rendering, the permission gauntlet, and the audit ledger. The Spec 025 v6 `(auth_type, auth_level)` invariant MUST remain unchanged.

### Functional Requirements — CC dev tool removal

- **FR-012**: The runtime tool-registration path MUST contain zero references to the CC dev tools enumerated as: `BashTool`, `FileEditTool`, `FileReadTool`, `FileWriteTool`, `GlobTool`, `GrepTool`, `NotebookEditTool`, `PowerShellTool`, `LSPTool`, `EnterWorktreeTool`, `ExitWorktreeTool`, `EnterPlanModeTool`, `ExitPlanModeTool`, `REPLTool`, `ConfigTool`.
- **FR-013** (revised during `/speckit-implement` Phase 3 — recorded as scope correction): The corresponding tool directories under the TUI tools tree MUST be **removed from `getAllBaseTools()` active registration** in `tui/src/tools.ts`. Full filesystem deletion of the directories was deferred during implementation because the `toolName`/`constants`/`prompt` modules inside each CC dev tool directory are imported by KOSMOS-shared infrastructure (permissions gauntlet, sandbox adapter, attachments handler, session-restore hooks — 30+ importers) that P3 does not own. Full directory removal is tracked under a new deferred item (post-P3 harness cleanup epic); see Scope Boundaries § Deferred Items. The spirit of FR-013 — "the LLM never sees these tools" — is preserved by FR-012 + FR-020 (closed 13-tool surface via `getAllBaseTools()` rewrite).
- **FR-014**: A CI grep guard MUST scan the runtime registration entry points and fail the build if any of the FR-012 names reappear there.

### Functional Requirements — Auxiliary tools

- **FR-015**: The system MUST retain `WebFetchTool` and `WebSearchTool` as-is (they appear in the migration tree's MVP-7 auxiliary set).
- **FR-016**: The system MUST retain `BriefTool` (citizen document upload) and `MCPTool` (external MCP passthrough), keeping their existing interfaces.
- **FR-017**: The `AgentTool` MUST be retained but rewired to back the `Task` primitive (per `§ L1-C C6`); the four built-in CC agents (`claudeCodeGuideAgent.ts`, `exploreAgent.ts`, `planAgent.ts`, `verificationAgent.ts`) MUST be removed.
- **FR-018**: The system MUST add four new auxiliary tools — `Translate`, `Calculator`, `DateParser`, `ExportPDF` — completing the MVP-7 auxiliary set defined in `§ L1-C C6`.
- **FR-019**: Tools whose retention status is undecided in this epic (`TodoWriteTool`, `ToolSearchTool`, `AskUserQuestionTool`, `SleepTool`, `MonitorTool`, `WorkflowTool`, `ScheduleCronTool`, the Task-* family, the Team-* family) MUST be evaluated and either kept-and-rewired, deferred to P4/P5, or deleted; the spec MUST NOT leave their status implicit.
- **FR-020**: After this epic ships, the LLM-visible tool surface MUST be the closed set: four primitives + WebFetch + WebSearch + Translate + Calculator + DateParser + ExportPDF + Task (via AgentTool) + Brief + MCP. Any other surface entry is a regression.

### Functional Requirements — MCP bridge

- **FR-021**: The Python side MUST expose a stdio-MCP server stub (`src/kosmos/ipc/mcp_server.py`) that wraps the existing `src/kosmos/ipc/stdio.py` transport without re-implementing framing, ring-buffer, or backpressure.
- **FR-022**: The TUI side MUST provide a stdio-MCP client (`tui/src/ipc/mcp.ts`) that reuses the existing `tui/src/ipc/bridge.ts` for transport and adds only MCP protocol concerns (handshake, tool list discovery, tool call routing).
- **FR-023**: The MCP client MUST surface a clear error to the user when handshake or tool-list discovery fails; it MUST NOT present an empty tool list as a successful boot.

### Functional Requirements — Permissions and audit

- **FR-024**: Permission decisions MUST remain at the adapter layer (`§ L1-C C5`). Primitives themselves MUST NOT carry default permission tiers; routing MUST never infer a permission rule from the primitive name.
- **FR-025**: Every primitive call MUST emit the existing OTEL spans (per Spec 021) with adapter-level attributes, and `subscribe` calls MUST additionally emit handle creation/revocation events.
- **FR-026**: Audit ledger entries (per Spec 024) MUST record the primitive name AND the resolved adapter `tool_id` separately, so post-hoc queries can group by either axis.

### Functional Requirements — Composite tool removal

- **FR-027**: The existing composite adapter `road_risk_score` (`src/kosmos/tools/composite/road_risk_score.py`), which fans out to three inner adapters and computes a derived score internally, MUST be deleted from the runtime registration path per migration tree `§ L1-B B6` ("Composite 제거 · LLM primitive chain"). The `src/kosmos/tools/composite/` directory MUST be removed. Risk-assessment-style requests are expected to be served by the LLM chaining `lookup(mode="fetch")` calls against the three underlying adapters (`koroad_accident_search`, `kma_weather_alert_status`, `kma_current_observation`) and reasoning over the combined output.
- **FR-028**: After P3 ships, no registered `GovAPITool` MAY perform adapter-level fan-out to multiple inner adapters. The CI consistency test MUST include a guard that rejects any adapter whose module imports another adapter's `_call`/`register` function (composite pattern detector).

### Functional Requirements — Undecided tool classification (explicit resolution of FR-019)

- **FR-029**: Within this epic, every tool listed in FR-019 (`TodoWriteTool`, `ToolSearchTool`, `AskUserQuestionTool`, `SleepTool`, `MonitorTool`, `WorkflowTool`, `ScheduleCronTool`, `Task{Create,Get,List,Stop,Update}Tool`, `Team{Create,Delete}Tool`) MUST receive a concrete per-tool decision — kept-and-rewired, deferred to a specific Epic, or deleted — recorded in the spec before registry closure (T028). The decision record MUST cite the reason and the target disposition path. No tool may remain "undecided" after this epic ships.

- **Primitive**: One of the four reserved verbs (`lookup`, `submit`, `verify`, `subscribe`). Owns no permission, no ministry binding; only the dispatch rules and its Spec 031 per-primitive envelope type (Spec 022 lookup envelope for `lookup`).
- **Adapter (`GovAPITool`)**: A registered Python tool wrapping one Korean public-service capability. Carries `tool_id`, `primitive`, `ministry` (typed Literal enum, replaces former free-form `provider`), `auth_level` + `is_irreversible` (permission classification consumed by `compute_permission_tier()`), `adapter_mode` (`live` or `mock`), schema, and search hints.
- **Routing Index**: An in-memory structure built at boot from registered adapters, partitioned by primitive, fed into the BM25 + dense retrieval surface used by `lookup(mode="search")`.
- **MCP Bridge**: The Python stdio-MCP server + TUI stdio-MCP client pair that exposes the harness's tool surface to the LLM via the MCP protocol while reusing the existing IPC transport underneath.
- **Auxiliary Tool**: A non-primitive tool retained or added to support primitive workflows (translation, calculation, date parsing, PDF export, web fetch/search, agent task fan-out, document brief, external MCP passthrough).

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new citizen session can complete the User Story 1 hospital-lookup flow end-to-end on the first attempt, with the LLM seeing only the closed tool surface defined in FR-020.
- **SC-002**: 100% of registered Python adapters (15 of 15 today; any number on subsequent boots) declare a non-null `primitive` field, validated by `build_routing_index()` and the CI consistency test.
- **SC-003**: 0 references to any of the FR-012 CC dev tool names exist in the runtime registration path; the CI grep guard passes.
- **SC-004**: The MCP bridge handshake completes within 500 ms on a developer machine (cold start) and 100 ms (warm), and never silently degrades to an empty tool list.
- **SC-005**: A citizen-facing operator can identify, for any tool call recorded in the audit ledger, both the primitive and the resolved adapter `tool_id` from the same record without joining external sources.
- **SC-006**: After P3 ships, a fresh contributor can add a new adapter, declare its primitive, and have it appear under `lookup(mode="search")` with no code changes outside the adapter file (no central registry edits, no TUI changes) — measured by a documented contributor walkthrough.
- **SC-007**: The integrated PR for this epic includes a `bun run tui` visual verification screenshot or transcript demonstrating User Story 1 end-to-end (per `feedback_integrated_pr_only`).
- **SC-008**: After P3 ships, `src/kosmos/tools/composite/` does not exist, `road_risk_score` does not appear in the routing index, and the CI composite-pattern detector (FR-028) passes.
- **SC-009**: All 13 tools listed in FR-019 have a recorded per-tool decision (kept / deferred / deleted) committed to the spec before registry closure; zero tools remain in "undecided" state after P3 ships.

---

## Assumptions

- The FriendliAI + EXAONE provider (P2) is operational and supports the function-calling format already in use.
- The existing OTEL pipeline (Spec 021/028), permission system (Spec 033), audit ledger (Spec 024 schema), and IPC stdio transport (Spec 032) are stable and reused without modification.
- The 15 currently-registered Python adapters represent the live + mock surface for this epic; new adapters added during P3 are out of scope unless required by the four-primitive coverage.
- BM25 + dense hybrid retrieval (Spec 022 + `feat/585-retrieval-dense`) is already wired and only needs the routing-index integration.
- The MCP protocol version targeted matches the version already shipped by Anthropic's `mcp` Python package and TS SDK; this epic does not introduce a custom MCP dialect.
- "Live" adapter calls during CI remain forbidden per AGENTS.md; live verification happens in the integrated PR's manual `bun run tui` step on the developer's machine.
- The permission tier helper introduced in FR-011 reads `auth_level` and `is_irreversible` only; it does not touch `auth_type` and therefore preserves the existing Spec 025 v6 (`auth_type` ↔ `auth_level`) invariant unchanged.
- The ministry enum in FR-010 is initial; new institutions are added by enum extension (not by free-form fallback to `OTHER` for permanent use). `OTHER` is a transitional escape hatch for adapters whose institutional mapping is not yet decided and is treated as a CI warning, not a hard fail.
- The `adapter_mode` field in FR-009 defaults to `"live"` deliberately (fail-explicit, not fail-closed) because mock mode is a developer/test choice that must be declared, never inferred.

---

## Scope Boundaries & Deferred Items *(mandatory)*

### Out of Scope (Permanent)

- **Re-introducing CC dev tools** (BashTool, FileEditTool, etc.) for citizen use — KOSMOS targets citizens, not developers; the dev tools' threat surface is incompatible with the citizen permission model.
- **Composite tools** (a single tool that performs multi-step adapter chains internally) — explicitly removed per `§ L1-B B6`; LLM primitive chain replaces them.
- **Live API calls in CI** — per AGENTS.md hard rule; recorded fixtures only.

### Deferred to Future Work

| Item | Reason for Deferral | Target Epic/Phase | Tracking Issue |
|------|---------------------|-------------------|----------------|
| Plugin adapter SDK + 5-tier DX (Template / Guide / Examples / Submission / Registry) | Plugin DX is a standalone phase with its own UX surfaces and submission workflow | P5 — Plugin DX (Epic #1636) | #1636 |
| `docs/api/` per-adapter Markdown + JSON Schema/OpenAPI publication | Doc surface depends on the final adapter metadata schema and ships with smoke verification | P6 — Docs + Smoke (Epic #1637) | #1637 |
| TUI rendering of `tool_use` / `tool_result` blocks (citation styling, expand/collapse) | Tool-call rendering is a UI-L2 concern (`§ UI-B`); P3 only ensures the underlying tool calls execute | P4 — UI L2 Implementation (Epic #1635) | #1635 |
| Phase-2 auxiliary tools (`TextToSpeech`, `SpeechToText`, `LargeFontRender`, `OCR`, `Reminder`) | Migration tree explicitly classifies these as Phase 2 (`§ L1-C C6`) | Phase 2 (epic TBD) | #1754 |
| Cross-session subscribe-handle resumption | Spec 031 currently scopes handles to the session lifetime; cross-session resume requires a separate persistence + revocation design | TBD (Spec 031 follow-up) | #1755 |
| Reclassification of undecided tools (`TodoWriteTool`, `ToolSearchTool`, `AskUserQuestionTool`, `SleepTool`, `MonitorTool`, `WorkflowTool`, `ScheduleCronTool`, Task-* family, Team-* family) for any tools whose decision is "defer to P4/P5" rather than "delete now" — residual after T027a | Some of these are operator/agent-internal and may belong to P4 (UI surfaces) or P5 (plugin DX) | P4 / P5 (per per-tool decision in T027a) | #1756 |
| Full filesystem deletion of the 15 CC dev tool directories under `tui/src/tools/{Bash,FileEdit,FileRead,FileWrite,Glob,Grep,NotebookEdit,PowerShell,LSP,REPL,Config,EnterWorktree,ExitWorktree,EnterPlanMode,ExitPlanMode}Tool/` (FR-013 original) | The `toolName`/`constants`/`prompt` modules in each directory are imported by KOSMOS-shared infrastructure (permissions gauntlet, sandbox adapter, attachments handler, session-restore hooks — 30+ importers) that P3 does not own. Full deletion requires coordinated rewiring of that infrastructure to inline name constants or to a shared tool-name module, which is a harness-cleanup concern beyond P3's tool-wiring scope. | Post-P3 harness cleanup epic (TBD) | #1757 |

---

## Dependencies

- **Epic P0 — Baseline Runnable** (#1632) — merged. Provides the CC 2.1.88 source baseline.
- **Epic P1+P2 — Dead code + FriendliAI migration** (#1633) — merged. Removes Anthropic-specific code paths; primitive wrappers will not have to defend against legacy provider assumptions.
- **Spec 021 (OTEL)**, **Spec 022 (MVP main tool)**, **Spec 024 (Audit schema)**, **Spec 025 v6 (auth_type ↔ auth_level)**, **Spec 027 (Memdir)**, **Spec 028 (OTLP collector)**, **Spec 031 (Five-primitive harness)**, **Spec 032 (IPC stdio hardening)**, **Spec 033 (Permission v2)** — already shipped infrastructure that this epic composes without modification.
