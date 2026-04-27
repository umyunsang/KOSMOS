# Phase 0 Research: K-EXAONE Tool Wiring (CC Reference Migration)

> Epic [#2077](https://github.com/umyunsang/KOSMOS/issues/2077) · 2026-04-27
> Companion to [plan.md](./plan.md). Resolves every NEEDS-CLARIFICATION, validates deferred items, and maps every design decision to a concrete reference per Constitution Principle I.

## R-1 · Zod → JSON Schema conversion path (AGENTS.md no-new-runtime-dep)

### Decision

Use **`zod/v4`'s built-in `z.toJSONSchema()`** for every Zod schema → JSON Schema conversion required by `tui/src/query/toolSerialization.ts`. No new runtime dependency.

### Rationale

`tui/package.json` declares `"zod": "^3.23.0"` which currently resolves to `3.25.76`. Zod 3.25+ ships a forward-compat namespace at `zod/v4` that exposes the upcoming Zod 4 API surface — specifically `z.toJSONSchema(schema)` — while remaining backward-compatible at the `zod` import. The TUI codebase already imports from `zod/v4` in every primitive (`tui/src/tools/LookupPrimitive/LookupPrimitive.ts:14` etc.), so the conversion path piggybacks on an import the project already depends on.

Plan-time verification (`bun -e`):

- `import { z } from 'zod/v4'; typeof z.toJSONSchema === 'function'` → `true`
- `z.toJSONSchema(z.object({a: z.string(), b: z.number().optional()}))` → emits valid `https://json-schema.org/draft/2020-12/schema` with proper `type`, `properties`, `required`, `additionalProperties: false`.
- `z.toJSONSchema(z.discriminatedUnion('mode', [searchSchema, fetchSchema]))` → emits `anyOf` with each variant materialized correctly, preserving `.describe()` strings as JSON Schema `description`, preserving `.min(1)` as `minLength`, preserving `.int().min(1).max(50)` as `type: integer + minimum/maximum`.

Discriminated unions are the only non-trivial Zod construct used by the five primitives (`LookupPrimitive` and `SubscribePrimitive` use them). Verification confirms they survive the conversion intact, so all five primitives can be serialized through this single API call.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| `zod-to-json-schema` (npm package) | Adds a runtime dependency. Violates AGENTS.md "no new runtime dep" hard rule. Constitution Principle VI documentation cost not justified by feature gain. |
| Hand-written JSON Schema constants per primitive | Stops the type system from catching primitive schema drift. Forces every Zod refinement to be hand-mirrored — violates the spec's FR-003 "single authoritative registry" principle (the TUI's Zod schema is the registry). |
| Stdlib AST walker against Zod's `_def` field | Brittle (Zod treats `_def` as private), reinvents what `zod/v4` already provides. |
| Bypass the JSON Schema layer (send raw Zod tokens) | FriendliAI's OpenAI-compatible API requires JSON Schema in the `parameters` field of each tool definition. |

### References mapped

- Migration pattern: `_cc_reference/api.ts:toolToAPISchema()` (line 119-266) — CC's hand-curated `BetaTool` schema generation. KOSMOS's `toolToFunctionSchema()` adapts this to Zod-driven generation rather than hand-curation.

## R-2 · Tool inventory composition (CC `tools.ts:assembleToolPool()` mapping)

### Decision

Mirror CC's `assembleToolPool()` shape in two places:

- **TUI side** (`toolSerialization.ts`): `getToolDefinitionsForFrame()` walks `getAllBaseTools()` from `tui/src/tools.ts`, filters to the five primitives + the MVP-7 auxiliary tools per Migration Tree § L1-C.C6, and emits a `ToolDefinition[]`.
- **Backend side** (`stdio.py`): when `frame.tools` is empty, call `ToolRegistry().export_core_tools_openai()` and use the result as the LLM's tool inventory. Both paths produce identical OpenAI function-call shapes; the TUI is authoritative when it provides one, the registry is the fallback.

### Rationale

CC's `assembleToolPool()` is the reference implementation of "build the tool list once, exclude per-mode disabled tools, return the canonical pool." KOSMOS's two-sided architecture (TUI is the user-facing process, backend is the LLM execution process) requires the inventory to be computed where it's authoritative — the TUI knows about the user's ministry-scope opt-ins (Spec 035), the backend knows about adapter readiness. Today the backend is the only side that knows the canonical list (`ToolRegistry`), so the TUI must either call out to the backend (race condition risk) or keep its own catalog mirror (stale risk).

The migration sidesteps this by:

1. Letting the TUI publish what *it* believes is the tool inventory (`frame.tools`).
2. Letting the backend fall back to its registry when the TUI omits the field.
3. Letting the backend reject any `tool_call` whose name is not in *its* registry (FR-005), independent of what the TUI sent.

Step 3 keeps the backend authoritative for execution (no TUI-side fabrication can run a tool that doesn't exist) while step 1+2 keep the TUI authoritative for user-visible composition (e.g., the citizen's ministry-scope opt-in filters which adapters they can see).

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| Backend always computes inventory; TUI never sends `frame.tools` | Loses the ability to filter by user ministry-scope at the TUI layer (Spec 035). Forces the backend to know about user-state that lives only in TUI memdir. |
| TUI always computes; backend never falls back | Empty `frame.tools` from a misconfigured TUI would silently disable tool use. Step 4 fallback prevents this. |
| Send only an opaque inventory hash; let the backend resolve | Adds protocol complexity for no observable gain — both sides already share the registry shape (Pydantic v2 / OpenAI function call). |

### References mapped

- `_cc_reference/tools.ts:assembleToolPool()` (line 345-367) — CC's pool composition.
- `_cc_reference/api.ts:toolToAPISchema()` (line 119-266) — CC's per-tool serialization.

## R-3 · System prompt dynamic composition (CC `appendSystemContext` mapping)

### Decision

Backend appends a `## Available tools` section to the system prompt whenever the LLM call is invoked with non-empty tools. The section lists each tool's `name`, `description`, and a JSON-formatted `parameters` block (formatted with `indent=2` for readability inside the prompt). The base prompt remains `prompts/system_v1.md` (8 lines, unchanged for citizen-facing copy).

### Rationale

CC's `appendSystemContext` (in `_cc_reference/api.ts`) bridges the two-channel reality of native function calling: the model receives `tools` as a structured field *and* the system prompt restates the same surface in prose. Models hallucinate less when both channels agree. K-EXAONE specifically — per `feedback_main_verb_primitive` and `project_429_attribution` — has been observed to fall back to training-data tool names when only one channel is populated.

The implementation is a single Python helper (`system_prompt_builder.build_system_prompt_with_tools(base, tools)`) that:

1. Returns `base` unchanged if `tools` is empty.
2. Otherwise appends `\n\n## Available tools\n` plus a per-tool block: `### {name}\n{description}\n\n**Parameters**: \`\`\`json\n{json.dumps(parameters, indent=2, ensure_ascii=False)}\n\`\`\`\n`.
3. Always serializes JSON deterministically (`sort_keys=True` for the JSON dump) so prompt-cache hash stability is preserved (Spec 026 prompt-hash invariant).

### Rationale for placement

`stdio.py:_handle_chat_request` is the only place where `frame.tools` and `frame.system` meet. The helper is called inline at this single location. Keeping it module-scoped (no class) matches Constitution Principle III's "no Any, no needless abstraction" stance.

### Alternatives considered

| Alternative | Why rejected |
|---|---|
| Build the inventory text on the TUI side and stuff it into `frame.system` | Splits authority — backend would have to trust the TUI's prompt formatting, contradicting the FR-003 single-source rule. |
| Use Langfuse Prompt Management (Spec 026 optional) | Optional dep, not always available, and the inventory must update on every turn whereas Langfuse caching favors stable prompts. |
| Skip the prompt-side restatement; rely only on `tools` field | Empirically insufficient for K-EXAONE. The two-channel agreement is the documented Anthropic pattern (`_cc_reference/api.ts:appendSystemContext`). |

### References mapped

- `_cc_reference/api.ts:appendSystemContext()` — CC's exact pattern.
- `_cc_reference/prompts.ts` (914 lines) — CC's dynamic prompt composition primitives.
- Spec 026 § Prompt Registry — preserves prompt-hash stability invariant.

## R-4 · Stream-event projection for `tool_call` frame (CC `claude.ts:1995-2052` mapping)

### Decision

When `deps.ts` receives a `tool_call` frame (`fa.kind === 'tool_call'`), it yields **two** stream events (in CC order):

```typescript
yield { type: 'stream_event', event: { type: 'content_block_start', index: ++blockIndex, content_block: { type: 'tool_use', id: fa.call_id, name: fa.name, input: fa.arguments } } }
yield { type: 'stream_event', event: { type: 'content_block_stop', index: blockIndex } }
```

`handleMessageFromStream` (already in `tui/src/utils/messages.ts:3024-3037`) routes `content_block_start` events whose `content_block.type === 'tool_use'` into the `streamingToolUses` array, which `AssistantToolUseMessage.tsx` (367 LOC, real, mounted in REPL.tsx) renders as a transcript-native record.

The legacy `createSystemMessage("🔧 ${name}${args}")` line is **removed** — it leaks display state into the conversation transcript and never paired with a result.

### Rationale

The TUI's existing UI components (`AssistantToolUseMessage`, `GroupedToolUseContent`) are CC ports. They consume the CC stream-event shape natively. Today's `deps.ts` collapses tool calls into transient SystemMessage progress lines because the projection layer was missed in the original Spec 1978 implementation (handoff §3.2 line-cited). Restoring the projection makes the existing components light up without modifying them.

### Pairing semantics

- `index` increments per content block, including the leading text block from `message_start` (which is already index 0 after fdfd3e9 `messageStartEmitted` initialization).
- `id` (UUID) is taken from `fa.call_id` and must match the eventual `tool_result.tool_use_id` (FR-009 invocation↔result pairing invariant).
- `input` is the raw arguments object — `handleMessageFromStream` validates against the tool's Zod schema downstream when needed.
- Multiple `tool_call` frames arriving in the same turn each consume their own `index` and produce their own `tool_use` block. CC's pattern is "any number of tool_use blocks per turn," and this matches FR-006 (every invocation has its own record).

### References mapped

- `_cc_reference/claude.ts:1995-2052` — CC's `content_block_start` tool_use case.
- `_cc_reference/messages.ts:normalizeContentFromAPI()` — CC's content-block routing logic.
- `tui/src/components/messages/AssistantToolUseMessage.tsx` — KOSMOS port (already in repo).

## R-5 · Tool result content block as user-role message (CC `messages.ts:ensureToolResultPairing` mapping)

### Decision

When `deps.ts` receives a `tool_result` frame, it creates a **user-role message** carrying a single `tool_result` content block:

```typescript
yield createUserMessage([{ type: 'tool_result', tool_use_id: fa.call_id, content: serializeEnvelope(fa.envelope) }])
```

The user-role placement is intentional and follows CC's invariant — the next turn's LLM context must include the result in the position where the LLM expects "user input" to live. This is how Claude/K-EXAONE both consume tool results.

The legacy `createSystemMessage("✓ ${status}${summary}")` is **removed**.

### Rationale

`ensureToolResultPairing()` in `_cc_reference/messages.ts:1150-1250` enforces:

1. Every `tool_use` content block MUST have a matching `tool_result` content block in a *subsequent* user-role message.
2. The `tool_use_id` field is the pairing key.
3. Orphans (tool_use without tool_result, or tool_result without prior tool_use) are surfaced as visible errors in the transcript (FR-009).

KOSMOS today violates this pairing because the result becomes a SystemMessage that's invisible to LLM-context serialization. Multi-turn loops break: the LLM never sees the tool's output and asks for it again on the next turn.

### Envelope serialization

The CC pattern accepts either a `string` content (when the tool produces text) or an `array` of content blocks (when the tool produces images, citations, etc.). For KOSMOS's primitive envelopes (`PrimitiveOutput` ok/error union), the serialization is `JSON.stringify(envelope)` with no structural change — the LLM sees the envelope verbatim, identical to what the existing `_dispatch_primitive` path emits today via `LLMChatMessage(role="tool", content=payload)`.

### References mapped

- `_cc_reference/messages.ts:ensureToolResultPairing()` (line 1150-1250) — CC's pairing invariant.
- `_cc_reference/toolExecution.ts:runToolUse()` — CC's result envelope construction.
- `_cc_reference/toolResultStorage.ts:processToolResultBlock()` — CC's token budgeting (out of scope for this epic, deferred).

## R-6 · Permission gauntlet wiring (CC `permissions.ts` ↔ KOSMOS Spec 033)

### Decision

The TUI side adds a single Promise-based dispatch path:

```typescript
// in deps.ts, on permission_request frame
const decision = await waitForPermissionDecision(fp.request_id) // resolves on modal Y/N or timeout
bridge.send({ ..., kind: 'permission_response', request_id: fp.request_id, decision })
```

`waitForPermissionDecision` is a new export from `sessionStore.ts`. It writes the request into `sessionStore.pendingPermission`, which the already-mounted `PermissionGauntletModal` (`tui/src/screens/REPL.tsx:5275-5277`) subscribes to. When the citizen presses Y or N, the modal calls `sessionStore.resolvePermissionDecision(request_id, 'granted' | 'denied')` which resolves the awaiting Promise. A 5-minute timeout (Spec 033 default) auto-resolves to `'denied'`.

The modal mount, the modal UI, and the underlying `PermissionRule` storage are all unchanged from Spec 033 — this epic only wires the request/response Promise.

### Rationale

The auto-deny shortcut at `deps.ts:250-266` was a Spec 1978 deferral. The modal component has been ready since Spec 033, but no code path connects the IPC-level `permission_request` frame to its `pendingPermission` slot. The Promise wrapper is the smallest possible bridge: store-level setter + store-level resolver + modal subscription (already exists).

### Bypass-immune preservation

Spec 033's bypass-immune steps (cross-citizen records, medical records without consent, write-without-identity) are enforced at the **adapter** layer — not at the modal. The modal only gates *whether the citizen sees a prompt*. Bypass-immune adapters refuse to run irrespective of modal outcome (Constitution §II). This wiring change does not alter that behavior.

### Timeout semantics

FR-017 requires a configurable timeout. `KOSMOS_PERMISSION_TIMEOUT_SEC` defaults to 300 (5 min) per Spec 033. On timeout, the Promise resolves to `decision: 'denied'` and the backend receives a structured denial result, indistinguishable from an explicit citizen denial — preserving fail-closed behavior.

### Queueing

FR-018 requires that a second `permission_request` arriving while a prior modal is open must wait. Implementation: `sessionStore.pendingPermission` is a single slot (not an array). The setter queues additional requests in an internal FIFO. The modal subscribes to the head of the queue. Each resolution shifts to the next queued request.

### References mapped

- `_cc_reference/permissions.ts` (1486 lines) — CC's permission gauntlet body.
- Spec 033 § Permission v2 Spectrum — KOSMOS's adapter-layer permission system.
- `tui/src/components/permissions/PermissionGauntletModal.tsx` — KOSMOS port (already in repo).
- `feedback_runtime_verification` — required PTY verification harness for the modal interaction.

## R-7 · Deferred-item validation (Constitution Principle VI gate)

### Spec scan results

`spec.md § Scope Boundaries & Deferred Items` declares 9 entries (2 Out of Scope, 7 Deferred):

| # | Item | Resolution status |
|---|------|-------------------|
| OOS-1 | Composite / macro tool combinations | Permanent OOS (Migration Tree § L1-B.B6). No tracking needed. |
| OOS-2 | Hardcoded tool whitelists outside the registry | Permanent OOS (FR-003 invariant). No tracking needed. |
| D-1 | Plugin-tier tool discovery in citizen sessions | → [#1979](https://github.com/umyunsang/KOSMOS/issues/1979) (state: OPEN, verified 2026-04-27) |
| D-2 | Adapter-level Spec 033 Layer 2/3 receipt issuance + ledger persistence | NEEDS TRACKING (resolved at `/speckit-taskstoissues`) |
| D-3 | `lookup` mode split (search vs fetch BM25 routing) | NEEDS TRACKING |
| D-4 | `subscribe` primitive long-lived stream | NEEDS TRACKING |
| D-5 | Agent swarm coordinator/worker spawn over IPC | → [#1980](https://github.com/umyunsang/KOSMOS/issues/1980) (state: OPEN, verified 2026-04-27) |
| D-6 | Onboarding/help/config/history-search UI rendering | NEEDS TRACKING |
| D-7 | Inline-XML `<tool_call>` legacy parser removal | NEEDS TRACKING |

### Free-text deferral pattern scan

`grep -i "separate epic\|future phase\|future epic\|v2\|deferred to\|later release\|out of scope for v1"` over `spec.md`:

- "out of scope" appears in the section header and the Scope Boundaries table only — no orphan free-text mention.
- "future" appears 3 times: section header "Deferred to **Future** Work" and entries D-4 ("**Future** subscribe-stream epic"), D-7 ("**Future** LLM-protocol cleanup epic") — all inside the table.
- "separate epic" / "v2" / "later release" patterns: 0 matches.

**Result**: PASS. Every deferral has a table row. No constitution Principle VI violation.

### Tracking issues to be created at `/speckit-taskstoissues`

D-2, D-3, D-4, D-6, D-7 will spawn placeholder issues. None are blockers for this epic.

## R-8 · Existing baseline verification (handoff diagnosis stability)

The handoff-prompt's line-cited diagnosis (Section 3) was independently re-verified at `main HEAD 523b520` during plan-time:

| Claim | Verified? | Evidence |
|---|---|---|
| `tui/src/query/deps.ts:73-81` omits `tools` field | ✓ | Lines 73-81 read by Read tool; no `tools:` key in the spread object literal. |
| `src/kosmos/ipc/stdio.py:1099-1101` unpacks `frame.tools` correctly | ✓ | Line 1099-1101 confirms `LLMToolDefinition.model_validate(t.model_dump())` loop. |
| `src/kosmos/ipc/stdio.py:1117` passes `tools=llm_tools or None` | ✓ | Line 1117 read; `or None` collapses empty list to None. |
| `prompts/system_v1.md` carries no tool list | ✓ | 8 lines of citizen-facing copy only; no `## Tools` section. |
| `src/kosmos/tools/registry.py:373` defines `export_core_tools_openai` | ✓ | grep located definition at line 373. |
| `src/kosmos/ipc/stdio.py:627-679` carries hardcoded primitive whitelist | ✓ | grep located `_PERMISSION_GATED_PRIMITIVES` and per-fname dispatch. |
| `tui/src/screens/REPL.tsx:5275-5277` mounts `PermissionGauntletModal` | ✓ | grep located the JSX mount + import. |
| `fdfd3e9` paint chain commit is orthogonal to tool wiring | ✓ | `git show fdfd3e9 --stat` confirms changes are limited to deps.ts streaming projection + stdio.py thinking_delta forwarding — neither touches `frame.tools`, `frame.system`, or registry fallback. |

The handoff diagnosis stands in full. No drift since 2026-04-27 09:00 KST.

## Open Questions

None. All technical context fields are filled. No `NEEDS CLARIFICATION` markers in plan or spec. Ready for Phase 1 (data-model + contracts + quickstart).
