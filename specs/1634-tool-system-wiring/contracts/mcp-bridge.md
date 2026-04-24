# Contract: stdio MCP Bridge (TUI ↔ KOSMOS Python backend)

**Spec**: [../spec.md](../spec.md) | **Plan**: [../plan.md](../plan.md) | **Data Model**: [../data-model.md](../data-model.md)

## 1. Boundaries

The MCP bridge is **additive** on top of the existing Spec 287/032 stdio JSONL transport. It does NOT replace `bridge.ts` ↔ `stdio.py`; it adds protocol concerns above them.

```
LLM (FriendliAI K-EXAONE)
       │
       │ tool_use(tool="lookup", input=…)
       ▼
TUI tool dispatcher (REPL session)
       │
       │ TS call: primitive.lookup({mode, query, …})
       ▼
tui/src/tools/primitive/lookup.ts
       │
       │ MCP request frame (JSON-RPC 2.0 with method="tools/call")
       ▼
tui/src/ipc/mcp.ts ── MCP client ──┐
                                    │
                                    │ JSONL frame over stdio
                                    ▼
       tui/src/ipc/bridge.ts (Spec 287/032 transport — UNCHANGED)
                                    │
                                    │ (subprocess stdio)
                                    ▼
       src/kosmos/ipc/stdio.py (Spec 032 transport — UNCHANGED)
                                    │
                                    │ JSONL frame
                                    ▼
src/kosmos/ipc/mcp_server.py ── MCP server ──┐
                                              │
                                              │ Python call: lookup(mode=…, query=…)
                                              ▼
                       src/kosmos/tools/lookup.py + registry.py + routing_index.py
```

## 2. Handshake (MCP `initialize` exchange)

### 2.1 Frame sequence

| Step | Direction | Method | Body |
|---|---|---|---|
| 1 | client → server | `initialize` | `{protocolVersion: "2025-06-18", capabilities: {tools: {}}, clientInfo: {name: "kosmos-tui", version: "<package.json>"}}` |
| 2 | server → client | `initialize` response | `{protocolVersion: "2025-06-18", capabilities: {tools: {listChanged: false}}, serverInfo: {name: "kosmos-backend", version: "<__version__>"}}` |
| 3 | client → server | `notifications/initialized` | `{}` |
| 4 | client → server | `tools/list` | `{}` |
| 5 | server → client | `tools/list` response | `{tools: [<13 entries from contracts/primitive-envelope.md § 1>]}` |

### 2.2 Performance budget (SC-004)

| Path | Budget |
|---|---|
| Cold (process start + handshake + tool list) | < 500 ms |
| Warm (handshake + tool list, process already running) | < 100 ms |

Budget allocations:
- Process spawn + Python interpreter cold start: ≤ 250 ms
- `kosmos.tools.register_all` import + registry build: ≤ 150 ms
- 5 frame round-trips at ≤ 20 ms each (Spec 032 stdio baseline): ≤ 100 ms

### 2.3 Failure modes

| Failure | MCP response | TUI behavior |
|---|---|---|
| Backend process exit during handshake | (transport-level EOF detected by `bridge.ts`) | TUI shows "tool subsystem unavailable — restart KOSMOS" — never an empty tool list (FR-023) |
| Backend returns `error` to `initialize` | JSON-RPC error response with code | TUI shows the error text; never proceeds with empty tool list |
| `tools/list` returns 0 tools | (treated as failure, not success) | TUI shows "tool subsystem returned no tools — diagnostic snapshot at <path>"; never proceeds |
| Handshake exceeds cold budget by 2× | (no protocol error; perf alert) | TUI logs WARN to stderr but proceeds (citizen experience prioritized over budget); OTEL span carries `kosmos.mcp.handshake_ms` attribute for monitoring |

## 3. Tool call (`tools/call`) frames

### 3.1 Request

```jsonc
{
  "jsonrpc": "2.0",
  "id": "<correlation_id from Spec 032>",
  "method": "tools/call",
  "params": {
    "name": "lookup",
    "arguments": {
      "mode": "search",
      "query": "응급실"
    }
  }
}
```

### 3.2 Response (success)

```jsonc
{
  "jsonrpc": "2.0",
  "id": "<correlation_id>",
  "result": {
    "content": [
      {
        "type": "text",
        "text": "<JSON-stringified primitive output per contracts/primitive-envelope.md>"
      }
    ],
    "isError": false
  }
}
```

### 3.3 Response (adapter error)

```jsonc
{
  "jsonrpc": "2.0",
  "id": "<correlation_id>",
  "result": {
    "content": [{
      "type": "text",
      "text": "<JSON: {error_kind, message, retry_advice}>"
    }],
    "isError": true
  }
}
```

### 3.4 Response (transport / protocol error)

Standard JSON-RPC 2.0 error envelope:

```jsonc
{
  "jsonrpc": "2.0",
  "id": "<correlation_id>",
  "error": {
    "code": -32602,  // Invalid params, etc.
    "message": "<human-readable>",
    "data": { /* optional structured detail */ }
  }
}
```

## 4. Reuse contract — what mcp_server.py / mcp.ts MAY and MAY NOT do

### 4.1 MUST reuse (from Spec 032)

- Frame envelope with `correlation_id` for request/response matching
- Ring buffer for pending responses
- Heartbeat (KOSMOS_IPC_HEARTBEAT_MS)
- LRU transaction cache for resume after stdio disconnect
- Fsync-on-write semantics for the mailbox-style replay log (Spec 027)

### 4.2 MUST NOT re-implement

- JSONL framing (Spec 032 owns the byte-level frame)
- stdio buffering (Spec 032 owns OS-level pipe handling)
- Backpressure (Spec 032 owns per-session window)
- Crash detection (Spec 032 owns process lifecycle)

### 4.3 NEW responsibilities

- MCP protocol version negotiation (`initialize` exchange § 2)
- Tool list serialization from `RoutingIndex.by_tool_id` + auxiliary tool registry
- `tools/call` → primitive dispatch routing
- Conversion of Pydantic `ValidationError` to MCP `error` envelope (§ 3.4)
- OTEL span attributes: `kosmos.mcp.handshake_ms`, `kosmos.mcp.tool_call_id`, `kosmos.mcp.protocol_version`

## 5. Schema versioning

The `protocolVersion` exchanged in § 2.1 follows the upstream MCP version (`2025-06-18` at time of writing). KOSMOS does NOT introduce a custom MCP dialect. If MCP releases a new version, KOSMOS bumps both `mcp.ts` and `mcp_server.py` in lockstep behind a single ADR (`docs/adr/`).

## 6. Out-of-scope for this contract

- The `tui/src/tools/MCPTool/` external-MCP passthrough (a separate concern — that one connects the LLM to *external* MCP servers; this contract is for the TUI ↔ KOSMOS internal bridge).
- The `mcp/resources` and `mcp/prompts` MCP capabilities — KOSMOS exposes only `tools/*`. Resource/prompt capabilities are listed as `{}` in the `initialize` capabilities. Extending the server to advertise these capabilities is not planned; no commitment.
