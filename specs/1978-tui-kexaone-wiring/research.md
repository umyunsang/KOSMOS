# Phase 0 Research: TUI ↔ K-EXAONE wiring closure

**Feature**: Epic #1978 — close P3/1633 wiring gaps
**Plan**: [plan.md](./plan.md)
**Date**: 2026-04-27

## Reference walk (per Constitution §I — `feedback_check_references_first`)

### CC 2.1.88 source map — primary reference

| Path | Read for | Finding |
|---|---|---|
| `.references/claude-code-sourcemap/restored-src/src/services/api/claude.ts` | `queryModelWithStreaming` shape | Signature carries `messages, systemPrompt, thinkingConfig, tools, signal, options`. KOSMOS `tui/src/services/api/claude.ts` is **byte-identical 3,419 lines** to this file. KOSMOS `tui/src/query/deps.ts:queryModelWithStreaming` is the wrapper that routes the call to `LLMClient` instead of Anthropic SDK — but `tools` is forwarded through to the LLMClient correctly. The forwarding gap is on the **harness side**, not the TS side. |
| `.references/claude-code-sourcemap/restored-src/src/query.ts` | how `tools` reaches the API site | Constructed via `Tools` registry (`tui/src/Tool.ts`) and passed through `query.ts` → `deps.ts:queryModelWithStreaming` → `LLMClient.stream({tools})`. KOSMOS `tui/src/query.ts` mirrors this verbatim (16-line import diff explained by KOSMOS-1633 stub injection). |
| `.references/claude-code-sourcemap/restored-src/src/Tool.ts` | tool-definition shape | `Tools` is `ReadonlyArray<Tool>`; each Tool has `name`, `description`, `inputSchema`. `KosmosToolDefinition` in `tui/src/ipc/llmTypes.ts` is shape-compatible. |
| `.references/claude-code-sourcemap/restored-src/src/query/deps.ts` | DI boundary | Original CC ships a `productionDeps` factory binding the real `queryModelWithStreaming`. KOSMOS replaces only this binding (memory `project_tui_architecture` confirmed). |
| `.references/claude-code-sourcemap/restored-src/src/hooks/useCanUseTool.ts` | sync-vs-async permission gate | CC uses `Promise<CanUseToolResult>` — synchronous in the sense that the tool dispatch awaits the resolution. Confirms ADR-0002. |
| `.references/claude-code-sourcemap/restored-src/src/services/mcp/` | MCP client connection model | CC eagerly opens MCP connections at session start (per `mcpClients` populate site). Confirms ADR-0003. |

### Project memory walk

| Memory | Decision impact |
|---|---|
| `project_tui_architecture` | Confirms `services/api/만 stdio JSONL로 교체` rewrite boundary. Locks in ADR-0005 (TUI-canonical history). |
| `feedback_cc_tui_90_fidelity` | Constrains all changes to backend + `services/api/`; CC `query.ts` / `Tool.ts` untouched. |
| `feedback_check_references_first` | Forces this research.md to cite restored-src first, vision.md last. |
| `project_tui_anthropic_residue` | Lists the four live Anthropic call sites this Epic must eliminate (Phase B). |
| `project_frame_schema_dead_arms` | Lists the 15 dead arms; this Epic activates 4 (`tool_call`, `tool_result`, `permission_request`, `permission_response`) plus introduces 1 new (`chat_request`). |
| `feedback_runtime_verification` | This research **had** to include a PTY rehearsal trace, not just code grep. (Done in Epic #1978 issue body.) |
| `feedback_integrated_pr_only` | Single PR — no per-Phase split. |
| `feedback_subissue_100_cap` | 74-task estimate honoured (plan.md table). |
| `feedback_speckit_autonomous` | No user gating between speckit phases. |
| `feedback_no_hardcoding` | Tool routing stays LLM-driven; no static keyword tables added. |
| `project_friendli_tier_wait` | FriendliAI Tier 1 active; live tests permitted under `@pytest.mark.live`. |
| `feedback_env_check_first` | `KOSMOS_FRIENDLI_TOKEN` precondition documented in spec.md Assumptions + quickstart.md. |

### KOSMOS canonical docs

| Source | Used for | Note |
|---|---|---|
| `AGENTS.md` | Hard rules (zero new deps, branches, PR closing) | All hard rules pass; see plan.md Constitution Check |
| `docs/requirements/kosmos-migration-tree.md § L1-A/B/C` | Pillars | Phases A-H map: A→ TUI input transport (L1-A·A6 error recovery); B→ L1-A·A1 single fixed provider; C/D→ L1-A·A3 native function calling; E→ L1-B·B4 + L1-C·C5 permission; G/H→ L1-A·A4 context |
| `docs/vision.md § Layer 1-6` | Architectural intent | **§183 Query↔TUI transport** says "Python query loop never touches the terminal". Empirically incorrect (see `tui/src/query.ts` 1,200-line agent loop). spec.md Assumptions section authorises correction; this Epic does NOT amend vision.md (out of scope, `feedback_subissue_100_cap` discipline) — a follow-up doc-only PR will. |

### Spec history walk

| Spec | Touched stdio.py? | Closure honest? |
|---|:---:|---|
| 287 | ❌ | TUI port — by design |
| 032 | ✅ (created) | Yes — schema 19-arm + envelope correct |
| 1633 | ✅ (last touch 2026-04-24) | **Premature**: closure declared while 4 Anthropic call sites still live (proven by 2026-04-27 PTY trace); residue is this Epic's Phase B |
| 1634 | ❌ (`git show 06740c0 --name-only` confirms 0 hits) | **Premature**: PR titled "tool system wiring" but stdio.py untouched. Phase D restores |
| 1635 | ❌ | UI port — orthogonal |
| 1636 | ❌ | Plugin DX — orthogonal |
| 1637 | ❌ | Docs/smoke — but smoke missed this gap (smoke = "TUI doesn't crash in 3 s"; not "scenario flows end-to-end"). Phase H broadens |

## Resolved unknowns

| ID | Unknown | Resolution |
|---|---|---|
| ADR-0001 | Frame schema design — extend vs new arm | **New `ChatRequestFrame` arm**. See plan.md ADR-0001. |
| ADR-0002 | Permission pipeline sync vs async | **Synchronous request/response with 60 s timeout, default deny on timeout.** See plan.md ADR-0002. |
| ADR-0003 | mcp.ts ↔ mcp_server.py lifecycle | **Eager spawn at TUI startup.** See plan.md ADR-0003. |
| ADR-0004 | Telemetry span hierarchy | **`kosmos.session > kosmos.turn > kosmos.frame{kind}`.** See plan.md ADR-0004. |
| ADR-0005 | Conversation history canonical location | **TUI side (`tui/src/query.ts`).** See plan.md ADR-0005. |

All five resolved with cited reference sources. No `[NEEDS CLARIFICATION]` markers remain.

## Deferred Items validation (Constitution §VI gate)

### spec.md table audit

| # | Item | Reason | Target | Tracking |
|---|---|---|---|---|
| 1 | Multi-ministry agent swarm | KSC 2026 single-citizen demo doesn't need it | Successor Epic | NEEDS TRACKING |
| 2 | Large attachment payload streaming | Current scope is text + small JSON results | Successor Epic | NEEDS TRACKING |
| 3 | Plugin operations frame | 1636 mid-flight | Continuation 1636 | NEEDS TRACKING |
| 4 | Session resume across backend restart | Strong durability needs checkpointing | Successor Epic | NEEDS TRACKING |
| 5 | Heartbeat/backpressure/push-notification frames | Stability surfaces | Successor Epic | NEEDS TRACKING |

### Free-text deferral pattern scan (spec.md)

```
$ grep -inE 'separate epic|future phase|future epic|v2|deferred to|out of scope for v1|later release' specs/1978-tui-kexaone-wiring/spec.md
```

Result (manually verified during this research):
- "separate epic" — **2 hits, both inside the Deferred Items table** (legal). Lines: 119, 125.
- "future phase" — **0 hits**.
- "future epic" — **0 hits** (table column header `Target Epic/Phase` is structural, not a forbidden phrase).
- "v2" — **0 hits**.
- "deferred to" — **0 hits outside the table**.
- "out of scope for v1" — **0 hits**.
- "later release" — **0 hits**.

**Validation result**: ✅ PASS. All deferrals captured in the table; `NEEDS TRACKING` resolved at `/speckit-taskstoissues`.

## Best-practice findings (per stream)

### Stream 1 (tool forwarding)
- **Decision**: Backend `_handle_chat_request` forwards `tools` directly into `LLMClient.stream(tools=...)`. The existing `kosmos.llm.client.LLMClient.stream` already accepts `tools: list[ToolDefinition | dict]` per its signature.
- **Rationale**: Pre-existing API surface — zero adapter overhead.
- **Alternatives considered**: Mid-bridge tool registry on backend (rejected — duplicates TUI registry, breaks single-source-of-truth).

### Stream 2 (frame schema)
- **Decision**: New `ChatRequestFrame` arm with fields `messages: list[ChatMessage]`, `tools: list[ToolDefinition]`, `system: str | None`. Role allow-list: `{"tui"}`. Terminal: `False` (not a stream terminator).
- **Rationale**: ADR-0001 (plan.md). Discoverability + audit + backward compat.
- **Alternatives considered**: Polymorphic `UserInputFrame` (rejected — `extra="forbid"` blocks).

### Stream 3 (permission bridge)
- **Decision**: Backend `_handle_chat_request` instantiates `PermissionPipeline` once per session, calls `evaluate(tool, ctx)` before each tool dispatch. On `decision == ASK`, emit `PermissionRequestFrame{transaction_id}`, await matching response (60 s timeout via `asyncio.wait_for`), record receipt to `~/.kosmos/memdir/user/consent/`. On any other decision, proceed/abort directly.
- **Rationale**: ADR-0002. Spec 033 contract. CC `useCanUseTool.ts` semantic match.
- **Alternatives considered**: Async fire-and-forget (rejected — fail-closed violation).

### Stream 4 (mcp.ts lifecycle)
- **Decision**: Spawn `kosmos.ipc.mcp_server` at TUI boot (parallel to main bridge). Cache MCP client connection on `bridgeSingleton`. mcpClients populate site is `tui/src/bootstrap/state.ts` (preliminary trace; verified during Phase 1 implementation).
- **Rationale**: ADR-0003. Latency budget SC-002.
- **Alternatives considered**: Lazy spawn (rejected — 500 ms regression).

### Stream 5 (telemetry)
- **Decision**: Span hierarchy `kosmos.session > kosmos.turn > kosmos.frame{kind}` with `correlation_id` attribute on all spans. GenAI spans (Spec 021) parented to `kosmos.turn`.
- **Rationale**: ADR-0004. FR-014 reconstructibility.
- **Alternatives considered**: Flat span list (rejected — Langfuse navigability).

## Cross-stream conflict scan

- ADR-0002 (sync permission) ↔ ADR-0005 (TUI-canonical history): no conflict — permission roundtrip happens **between** turns, not inside the message store.
- ADR-0001 (new frame arm) ↔ Spec 032 18-arm freeze: existing 18 arms unchanged; +1 new arm is additive, not amending. Spec 032 schema SHA-256 hash will change — captured as a Phase C task (re-emit `kosmos.ipc.schema.hash` OTEL attribute).
- ADR-0003 (eager MCP spawn) ↔ Spec 1634 mcp-bridge contract: contract permits both lazy and eager (§ 2.2); we choose eager. No contract amendment needed.

## Phase 0 conclusion

All five ADRs resolved with cited references. Five deferred items tracked. Zero `[NEEDS CLARIFICATION]` markers. Constitution gates pass. Proceed to Phase 1 design output.
