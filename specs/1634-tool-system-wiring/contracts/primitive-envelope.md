# Contract: Primitive Envelope (LLM-visible surface)

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data Model**: [../data-model.md](../data-model.md)

> The envelope shape is canonical from Spec 031; see `specs/031-five-primitive-harness/contracts/{submit,subscribe,verify}.{input,output}.schema.json`. P3 inherits these shapes verbatim and adds the `lookup` envelope which Spec 022 already defined. This contract documents the *LLM-visible* surface — what the model sees in its tool list and what the TUI primitive wrappers must serialize.

## 1. Surface summary

The LLM sees exactly the following tools after P3 ships. Anything else is a regression.

| Tool name (LLM-visible) | Backed by | Notes |
|---|---|---|
| `lookup` | `tui/src/tools/primitive/lookup.ts` → `kosmos.tools.lookup` (Spec 022) | Two modes: `search` (BM25+dense over registered adapters) and `fetch` (direct adapter call by `tool_id`) |
| `submit` | `tui/src/tools/primitive/submit.ts` → `kosmos.primitives.submit` (Spec 031) | Permission-gated side-effecting action |
| `verify` | `tui/src/tools/primitive/verify.ts` → `kosmos.primitives.verify` (Spec 031) | Credential delegation, never mints |
| `subscribe` | `tui/src/tools/primitive/subscribe.ts` → `kosmos.primitives.subscribe` (Spec 031) | Returns `SubscriptionHandle` with session lifetime |
| `WebFetch` | `tui/src/tools/WebFetchTool/` (CC retained) | Unchanged from CC |
| `WebSearch` | `tui/src/tools/WebSearchTool/` (CC retained) | Unchanged from CC |
| `Translate` | `tui/src/tools/TranslateTool/` (NEW) | Delegates to FriendliAI K-EXAONE; no new dep |
| `Calculator` | `tui/src/tools/CalculatorTool/` (NEW) | stdlib `decimal` + `math` |
| `DateParser` | `tui/src/tools/DateParserTool/` (NEW) | stdlib `datetime` + `zoneinfo` (Asia/Seoul default) |
| `ExportPDF` | `tui/src/tools/ExportPDFTool/` (NEW) | TUI side: existing `pdf-to-img` WASM (UI-B B.3) |
| `Task` | `tui/src/tools/AgentTool/` (rewired) | Backed by AgentTool with built-in CC agents stripped |
| `Brief` | `tui/src/tools/BriefTool/` (CC retained) | Citizen document upload |
| `MCP` | `tui/src/tools/MCPTool/` (CC retained) | External MCP passthrough — distinct from `tui/src/ipc/mcp.ts` (which is the stdio MCP client connecting TUI ↔ KOSMOS Python backend) |

**Closed set**: 13 entries. Any registration outside this set after P3 is a regression caught by the CI tool-list snapshot test.

## 2. `lookup` envelope (P3 wrapper over Spec 022)

### 2.1 Input

```jsonc
{
  "mode": "search",          // or "fetch"
  // mode=search:
  "query": "응급실",          // citizen prompt fragment in Korean or English
  "primitive_filter": null,   // optional: restrict results to a single primitive
  "top_k": 5,                 // optional, default 5
  // mode=fetch:
  "tool_id": "hira_hospital_search",
  "params": { /* adapter-defined Pydantic-validated body */ }
}
```

### 2.2 Output

```jsonc
// mode=search
{
  "mode": "search",
  "results": [
    {
      "tool_id": "hira_hospital_search",
      "primitive": "lookup",
      "ministry": "HIRA",
      "score": 0.873,
      "search_hint": "병원 hospital 진료 medical"
    }
    // ... up to top_k entries, ranked descending
  ]
}

// mode=fetch
{
  "mode": "fetch",
  "tool_id": "hira_hospital_search",
  "result": { /* adapter output_schema instance */ }
}
```

### 2.3 Validation

- `mode=search` MUST NOT carry `params` or `tool_id`.
- `mode=fetch` MUST carry `tool_id`; `params` MUST validate against the named adapter's `input_schema`.
- Unknown `tool_id` → MCP error code `tool_not_found`.
- Unknown `primitive_filter` → MCP error code `invalid_params`.

## 3. `submit` envelope (Spec 031, unchanged shape)

Reference: `specs/031-five-primitive-harness/contracts/submit.input.schema.json` + `submit.output.schema.json`. P3 wires the TUI wrapper to forward this shape verbatim.

### 3.1 LLM-visible properties

- LLM sees `submit({tool_id, params})` as the input contract.
- Permission gauntlet (Spec 033) executes *between* the LLM call and the adapter dispatch — the LLM never sees the modal; the TUI does.
- LLM sees `{transaction_id, status, adapter_receipt}` as output. The `transaction_id` is deterministically derived (Spec 031 § 2 — adapter `nonce` + canonical params) so the LLM can reason about idempotency.

## 4. `verify` envelope (Spec 031, unchanged shape)

Reference: `specs/031-five-primitive-harness/contracts/verify.input.schema.json` + `verify.output.schema.json`. P3 wires the TUI wrapper to forward this shape verbatim.

### 4.1 LLM-visible properties

- LLM sees `verify({tool_id, params})` as input.
- Output is a discriminated union over `auth_family` (`gongdong_injeungseo` | `geumyung_injeungseo` | `ganpyeon_injeung` | `digital_onepass` | `mobile_id` | `mydata`) — the LLM uses the family to decide subsequent calls (e.g., "now I have AAL2, I can call this submit adapter").

## 5. `subscribe` envelope (Spec 031, unchanged shape)

Reference: `specs/031-five-primitive-harness/contracts/subscribe.input.schema.json` + `subscribe.output.schema.json`. P3 wires the TUI wrapper to forward this shape verbatim.

### 5.1 LLM-visible properties

- LLM sees `subscribe({tool_id, params, lifetime_hint})` as input.
- Output is `{handle_id, lifetime, kind}` — NOT the stream itself. The stream is delivered out-of-band via TUI rendering (UI-B B.5 multi-turn citation prefix `⎿`); the LLM is informed of the handle and can issue follow-up `subscribe` or `lookup` calls referencing it.
- `handle_id` is recorded in the audit ledger as a Spec 024 entry with `primitive="subscribe"`.

## 6. Auxiliary tool envelopes

The 4 retained CC auxiliary tools (WebFetch, WebSearch, Brief, MCP) keep their existing CC envelopes verbatim — see restored-src `src/tools/{WebFetch,WebSearch,Brief,MCP}Tool/prompt.ts` for the LLM-facing shape.

The 4 new auxiliary tools each ship their own `input_schema` + `output_schema`:

| Tool | Input fields | Output fields |
|---|---|---|
| `Translate` | `text: str`, `source_lang: Lang`, `target_lang: Lang` | `text: str` |
| `Calculator` | `expression: str` (restricted grammar), `precision: int = 28` | `result: Decimal`, `kind: Literal["int","float","fraction"]` |
| `DateParser` | `text: str`, `tz: str = "Asia/Seoul"` | `iso8601: str`, `interpreted_text: str` |
| `ExportPDF` | `markdown: str`, `title: str`, `include_attachments: bool = False` | `pdf_path: str` (Memdir USER tier scoped) |

`Lang` is `Literal["ko","en","ja"]` (matches UI-A A.3 onboarding language tier).

## 7. CC-removed tools (FR-012)

After P3 ships, the following tool names MUST NOT appear in the LLM tool list response:

`Bash, BashOutput, FileEdit, FileRead, FileWrite, Glob, Grep, NotebookEdit, PowerShell, LSP, REPL, Config, EnterWorktree, ExitWorktree, EnterPlanMode, ExitPlanMode`

The CI tool-list snapshot test (`tests/tools/test_routing_consistency.py` complementary check) asserts the LLM-visible tool list is *exactly* the closed set in § 1 — no more, no less.
