# Implementation Plan: P3 · Tool System Wiring (4 Primitives + Python stdio MCP)

**Branch**: `feat/1634-tool-system-wiring` (`SPECIFY_FEATURE=1634-tool-system-wiring`) | **Date**: 2026-04-24 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/1634-tool-system-wiring/spec.md`
**Epic**: #1634 | **Phase**: P3 (per `docs/requirements/kosmos-migration-tree.md § Execution phases`)

## Summary

Wire `src/kosmos/tools/` Python adapters as the LLM-visible tool surface via a stdio-MCP bridge that reuses the existing `tui/src/ipc/bridge.ts` ↔ `src/kosmos/ipc/stdio.py` transport. Expose exactly four reserved primitives (`lookup`, `submit`, `verify`, `subscribe`) plus a closed auxiliary set (WebFetch, WebSearch, Translate, Calculator, DateParser, ExportPDF, Task via AgentTool, Brief, MCP). Delete the Claude Code developer tool tree (Bash, FileEdit, Glob, Grep, NotebookEdit, PowerShell, LSP, REPL, Config, Plan/Worktree mode tools) from the runtime registration path. Populate the `primitive` field on all 15 currently-registered Python adapters; rename `provider` → typed `ministry`; add `adapter_mode: Literal["live","mock"]`; introduce a `compute_permission_tier()` helper. Add a `build_routing_index()` boot-time validator + CI consistency test that fails closed if any adapter is misconfigured.

**Approach**: this is a *wiring* epic — the substrate (FriendliAI provider, OTEL, audit ledger, permission v2, IPC stdio, BM25+dense retrieval) already exists from prior specs. Implementation work is mechanical (mass adapter migration, dead-code deletion, CI guard) plus three small new modules (4 primitive wrappers, MCP server stub, MCP client). No new runtime dependencies (AGENTS.md hard rule).

## Technical Context

**Language/Version**: Python 3.12+ (backend, existing); TypeScript 5.6+ with Bun v1.2.x (TUI, existing Spec 287 stack).
**Primary Dependencies**: `pydantic >= 2.13` (frozen models + Literal enums, existing); `pydantic-settings >= 2.0` (env catalog `KOSMOS_*`, existing); `httpx >= 0.27` (async HTTP for live adapters, existing); `opentelemetry-sdk` + `opentelemetry-semantic-conventions` (Spec 021 spans, existing); `pytest` + `pytest-asyncio` (existing test stack); `mcp` Python package (already shipped) for the stdio-MCP server stub; `@modelcontextprotocol/sdk` TS (already in `tui/package.json` from Spec 287) for the stdio-MCP client. **Zero new runtime dependencies** (AGENTS.md hard rule; SC of every prior tool-system spec).
**Storage**: N/A. All registry state is in-memory, rebuilt at boot. BM25 index is in-memory (Spec 022). Audit ledger is Spec 024 territory and unchanged. Memdir USER tier (Spec 027) for sessions is unchanged.
**Testing**: `uv run pytest` for backend; `bun test` for TUI. New CI test `tests/tools/test_routing_consistency.py` runs against the live registry and fails the build if `build_routing_index()` rejects any adapter. Live API calls remain forbidden in CI per Constitution § IV; the integrated PR's `bun run tui` step provides manual E2E verification (per `feedback_integrated_pr_only`).
**Target Platform**: macOS / Linux developer terminals (Kitty / iTerm2 / xterm). Backend runs as a child process spawned by the TUI over stdio.
**Project Type**: Multi-package monorepo with backend (Python `src/kosmos/`) + TUI (TypeScript `tui/src/`) connected via stdio JSONL IPC. P3 introduces an MCP protocol layer *on top of* that existing transport — it does not replace `bridge.ts` / `stdio.py`.
**Performance Goals**: MCP handshake < 500 ms cold / < 100 ms warm (SC-004). `build_routing_index()` < 50 ms for the current 15-adapter set; must scale linearly to 100+ adapters without code changes (P5 plugin DX is the next epic). `lookup(mode="search")` BM25 query latency unchanged from Spec 022 baseline.
**Constraints**: Constitution § II fail-closed (all new fields default to safer value; `adapter_mode="live"` is the deliberate exception, fail-explicit per Q1 clarification). Constitution § III no `Any` in I/O schemas. Constitution § IV no live API calls in CI. AGENTS.md zero-new-runtime-deps. AGENTS.md English-only source text (Korean only in domain data — search hints, ministry display labels).
**Scale/Scope**: 15 registered live adapters today (`hira_hospital_search`, `kma_*` x 6, `koroad_*` x 2, `nfa_emergency_info_service`, `mohw_welfare_eligibility_search` (under `ssis/`), `nmc_emergency_search`, `road_risk_score` (composite — deleted in this epic per FR-027), `resolve_location`, `lookup`); after FR-027 composite removal the post-P3 live count is **14**. Plus **11 mock adapters** across `src/kosmos/tools/mock/{verify_*,data_go_kr/{fines_pay,rest_pull_tick,rss_notices},mydata/welfare_application,cbs/disaster_feed}.py`. Net: **26 adapters touched** (15 live + 11 mock) — one of the 15 live (road_risk_score) is deleted. TUI tool tree: 15 directories deleted (14 CC dev tools + `tui/src/tools/AgentTool/built-in` partial strip), 4 new auxiliary directories added, 1 primitive directory added with 4 files, 1 MCP client file added. Backend: 1 new MCP server file, 1 deleted composite directory, edits to `register_all.py` + `models.py` + `registry.py`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I — Reference-Driven Development

| Layer touched | Primary reference (restored-src) | Secondary reference | Mapped decision |
|---|---|---|---|
| Tool registration | `src/services/tools/toolOrchestration.ts`, `src/services/tools/toolExecution.ts` | Spec 031 § 2 (envelope), Pydantic AI registry pattern | `register_all.py` migration + `build_routing_index()` |
| Primitive wrappers (4) | `src/tools/MCPTool/MCPTool.ts` (envelope dispatch shape), `src/tools/AgentTool/AgentTool.tsx` (Task primitive backing) | Spec 031 research § 1 primitive ↔ CC analog table | `tui/src/tools/primitive/{lookup,submit,verify,subscribe}.ts` |
| MCP bridge (Python server) | `src/services/tools/StreamingToolExecutor.ts` (back-pressure), Spec 032 stdio hardening | Anthropic `mcp` Python package docs | `src/kosmos/ipc/mcp_server.py` wraps `stdio.py` |
| MCP bridge (TS client) | `src/tools/MCPTool/MCPTool.ts`, `src/tools/MCPTool/prompt.ts` | `@modelcontextprotocol/sdk` TS docs | `tui/src/ipc/mcp.ts` reuses `bridge.ts` |
| CC dev tool removal | All under `src/tools/{Bash,FileEdit,FileRead,FileWrite,Glob,Grep,NotebookEdit,PowerShell,LSP,REPL,Config,EnterWorktree,ExitWorktree,EnterPlanMode,ExitPlanMode}Tool/` | — (deletions) | `tui/src/tools/*` deletion list per spec FR-012 |
| Auxiliary tool retention | `src/tools/{WebFetch,WebSearch,Brief,MCP,Agent}Tool/` | — | Keep + rewire AgentTool→Task (strip 4 built-in agents) |
| Auxiliary tool additions | No CC analog — KOSMOS-original | Pydantic AI tool definitions | New `tui/src/tools/{Translate,Calculator,DateParser,ExportPDF}Tool/` |

**PASS** — every major decision maps to a concrete restored-src path or a documented secondary reference per Constitution § I and AGENTS.md "Reference source rule." Detailed mapping in `research.md § 1`.

### Principle II — Fail-Closed Security

- New `adapter_mode` defaults to `"live"` (fail-explicit, not fail-closed). Documented exception in `research.md § 5`: mock mode is a developer/test choice that *must* be declared, not inferred. Setting default to `"mock"` would mask production-vs-test mismatch and violate the spirit of the principle (developers would forget to declare and ship mock to prod). **Justified deviation, recorded in Complexity Tracking.**
- New `ministry` field has no default — registration fails if missing.
- `compute_permission_tier()` helper applies `is_irreversible=True` → tier 3 unconditionally (override of AAL mapping). This *increases* restrictiveness, aligned with the principle.
- All deleted CC dev tools removed structural ability for the LLM to read/write the developer's filesystem — net security gain.

**PASS with one documented deviation** (adapter_mode default).

### Principle III — Pydantic v2 Strict Typing

- `ministry` migrates from `str` to `Literal[<closed enum>]` — strictly more typed.
- `adapter_mode` new field is `Literal["live","mock"]` — typed.
- `compute_permission_tier()` return type is `Literal[1,2,3]` — typed.
- Spec 031 per-primitive envelope types (`SubmitEnvelope`, `SubscriptionEvent`, `VerifyInput`/`VerifyOutput`) and Spec 022 lookup envelope already exist; no new shared envelope, no `Any` in I/O.
- 4 new auxiliary tools (Translate, Calculator, DateParser, ExportPDF) ship with `input_schema` + `output_schema` + bilingual `search_hint` per principle.

**PASS** — all new fields and helpers preserve or strengthen typing.

### Principle IV — Government API Compliance

- No new live API integration in this epic. CI consistency test reads only adapter metadata.
- The 4 new auxiliary tools (Translate, Calculator, DateParser, ExportPDF) are local computations or stdlib-backed; no `data.go.kr` calls. Translate may use a public LLM call delegated via the existing tool-call path — `research.md § 7` confirms this avoids new `data.go.kr` quota.
- Existing rate-limit + per-key tracking unchanged.

**PASS**.

### Principle V — Policy Alignment

- Reducing the LLM's tool surface to four primitives + closed auxiliary set directly serves AI Action Plan **Principle 8** (single conversational window for cross-ministry citizen services) — the citizen sees one conversation; the LLM sees one envelope shape.
- Typed `ministry` enum makes ministry-scoped consent (per Spec 035 onboarding ministry-scope step) machine-checkable, supporting **Principle 9** Open API integration.
- Permission tier helper feeds UI-C C1 layer color rendering, which is part of the PIPA permission gauntlet display.

**PASS**.

### Principle VI — Deferred Work Accountability

- Spec § Scope Boundaries & Deferred Items already populated with 5 entries.
- 3 entries map to existing open Epics (#1635 P4, #1636 P5, #1637 P6) — verified open via GraphQL during /speckit-clarify.
- 2 entries are `NEEDS TRACKING` (Phase-2 auxiliary tools, cross-session subscribe handles, undecided-tools reclassification) — `/speckit-taskstoissues` will create placeholder issues.
- No free-text "future" / "v2" / "separate epic" pattern outside the table (verified: `grep -E "future epic|separate epic|Phase [2-9]|deferred to|out of scope for v1" specs/1634-tool-system-wiring/spec.md` returns only matches inside the Deferred table or the Out-of-Scope-Permanent list).

**PASS**.

### Constitution Check Verdict

**PASS** with one documented Complexity-Tracking entry (adapter_mode default to `"live"`, justified as fail-explicit). No blockers. Phase 0 may proceed.

## Project Structure

### Documentation (this feature)

```text
specs/1634-tool-system-wiring/
├── spec.md                       # Feature specification (complete)
├── plan.md                       # This file (Phase 2 planning)
├── research.md                   # Phase 0: reference mapping + decisions
├── data-model.md                 # Phase 1: GovAPITool/AdapterRegistration deltas, helper signatures
├── contracts/
│   ├── primitive-envelope.md     # Per-primitive JSON shapes (citing Spec 022 + Spec 031)
│   ├── mcp-bridge.md             # stdio-MCP handshake + tool-list-discovery contract
│   └── routing-consistency.md    # build_routing_index() failure-mode contract
├── quickstart.md                 # Phase 1: dev workflow for adding a new adapter post-P3
├── checklists/
│   └── requirements.md           # /speckit-specify quality checklist (complete)
└── tasks.md                      # Phase 2 output (created by /speckit-tasks, NOT this command)
```

### Source Code (repository root)

```text
src/kosmos/
├── tools/
│   ├── models.py                 # EDIT: provider→ministry rename + Literal enum; add adapter_mode field
│   ├── registry.py               # EDIT: nothing — AdapterRegistration source_mode stays
│   ├── register_all.py           # EDIT: populate primitive on 11 adapters; switch provider→ministry
│   ├── routing_index.py          # NEW: build_routing_index() with fail-closed validation
│   ├── primitives.py             # EXISTING: keep
│   └── permissions.py            # NEW: compute_permission_tier(auth_level, is_irreversible)
├── primitives/                   # EXISTING (Spec 031): submit.py, subscribe.py, verify.py, _errors.py
└── ipc/
    ├── stdio.py                  # EXISTING (Spec 032): unchanged transport
    └── mcp_server.py             # NEW: stdio-MCP server stub wrapping stdio.py

tui/src/
├── ipc/
│   ├── bridge.ts                 # EXISTING (Spec 287/032): unchanged transport
│   └── mcp.ts                    # NEW: stdio-MCP client reusing bridge.ts
└── tools/
    ├── primitive/                # NEW directory
    │   ├── lookup.ts
    │   ├── submit.ts
    │   ├── verify.ts
    │   └── subscribe.ts
    ├── WebFetchTool/             # KEEP
    ├── WebSearchTool/            # KEEP
    ├── BriefTool/                # KEEP
    ├── MCPTool/                  # KEEP (external MCP passthrough — distinct from new mcp.ts client)
    ├── AgentTool/                # KEEP + rewire as Task primitive backing; delete claudeCodeGuideAgent.ts/exploreAgent.ts/planAgent.ts/verificationAgent.ts
    ├── TranslateTool/            # NEW
    ├── CalculatorTool/           # NEW
    ├── DateParserTool/           # NEW
    ├── ExportPDFTool/            # NEW
    │
    ├── BashTool/                 # DELETE (FR-012)
    ├── FileEditTool/             # DELETE
    ├── FileReadTool/             # DELETE
    ├── FileWriteTool/            # DELETE
    ├── GlobTool/                 # DELETE
    ├── GrepTool/                 # DELETE
    ├── NotebookEditTool/         # DELETE
    ├── PowerShellTool/           # DELETE
    ├── LSPTool/                  # DELETE
    ├── REPLTool/                 # DELETE
    ├── ConfigTool/               # DELETE
    ├── EnterWorktreeTool/        # DELETE
    ├── ExitWorktreeTool/         # DELETE
    ├── EnterPlanModeTool/        # DELETE
    ├── ExitPlanModeTool/         # DELETE
    │
    └── (FR-019 undecided — TodoWriteTool, ToolSearchTool, AskUserQuestionTool, SleepTool,
         MonitorTool, WorkflowTool, ScheduleCronTool, Task{Create,Get,List,Stop,Update}Tool,
         Team{Create,Delete}Tool — per-tool decision in /speckit-tasks)

tests/
└── tools/
    └── test_routing_consistency.py   # NEW: CI gate — boot-time validation
```

**Structure Decision**: Multi-package monorepo with strict boundary between Python backend (registry, adapters, primitives, MCP server) and TS TUI (primitive wrappers, MCP client, auxiliary tool UI). The MCP layer is *additive* on top of the existing stdio JSONL IPC, not a replacement. All registration plumbing changes happen in Python (`models.py`, `register_all.py`, `routing_index.py`, `permissions.py`); all primitive surface and tool list changes happen in TUI (`primitive/`, deletions, new auxiliary tool dirs). One file change crosses the boundary: `bridge.ts` ↔ `mcp.ts` ↔ `mcp_server.py` ↔ `stdio.py`.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| `adapter_mode` defaults to `"live"` (fail-explicit, not fail-closed per Constitution § II) | Mock mode is a developer/test choice that must be declared, not inferred. A `"mock"` default would silently ship mocks to production if developers forget to override. | Defaulting to `"mock"` was rejected because it inverts the principle's intent: fail-closed exists to prevent *accidentally exposing* personal-data APIs as public, but here the inverse risk dominates — accidentally serving fixture data to a real citizen. Documented in `research.md § 5`. |

(No other deviations.)
