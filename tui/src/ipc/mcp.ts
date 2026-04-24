// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — no upstream analog.
//
// Thin stdio-MCP client that speaks JSON-RPC 2.0 + MCP to the Python
// `kosmos.ipc.mcp_server` subprocess. This is a SEPARATE client from
// `bridge.ts`, which owns the main REPL session transport (Spec 032).
// `mcp.ts` spawns its own `mcp_server.py` subprocess on demand for
// on-demand tool discovery and invocation; it does NOT share the REPL
// session pipe.
//
// Protocol version: 2025-06-18 (must match mcp_server.py MCP_PROTOCOL_VERSION;
// bump in lockstep behind a single ADR per contracts/mcp-bridge.md § 5).
//
// Handshake sequence (contracts/mcp-bridge.md § 2):
//   1. client → server: initialize
//   2. server → client: initialize response
//   3. client → server: notifications/initialized
//   4. client → server: tools/list
//   5. server → client: tools/list response
//
// Zero new runtime dependencies — Bun stdlib only; JSON-RPC 2.0 spoke directly.

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MCP_PROTOCOL_VERSION = "2025-06-18";
const CLIENT_NAME = "kosmos-tui";
const CLIENT_VERSION = "0.1.0";

/** Handshake cold-path budget: 500 ms (SC-004, contracts/mcp-bridge.md § 2.2). */
const COLD_BUDGET_MS = 500;

// ---------------------------------------------------------------------------
// JSON-RPC 2.0 error codes (contracts/mcp-bridge.md § intro + spec § 3.4)
// ---------------------------------------------------------------------------

const JSONRPC_PARSE_ERROR = -32700;
const JSONRPC_INVALID_REQUEST = -32600;
// kept for reference only — not used in requests from the client side
const _JSONRPC_METHOD_NOT_FOUND = -32601;
const _JSONRPC_INVALID_PARAMS = -32602;
const JSONRPC_INTERNAL_ERROR = -32603;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** A named MCP tool from the tools/list response. */
export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

/** Result returned by tools/call. */
export interface ToolCallResult {
  content: Array<{ type: string; text: string }>;
  isError: boolean;
}

/** Internal: pending in-flight request keyed by request id. */
interface PendingRequest {
  resolve: (msg: JsonRpcResponse) => void;
  reject: (err: Error) => void;
}

// ---------------------------------------------------------------------------
// JSON-RPC 2.0 envelope types (no `any` — narrow unions)
// ---------------------------------------------------------------------------

type JsonRpcId = number | string | null;

interface JsonRpcRequest {
  jsonrpc: "2.0";
  id: JsonRpcId;
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcNotification {
  jsonrpc: "2.0";
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcSuccessResponse {
  jsonrpc: "2.0";
  id: JsonRpcId;
  result: Record<string, unknown>;
}

interface JsonRpcErrorResponse {
  jsonrpc: "2.0";
  id: JsonRpcId;
  error: {
    code: number;
    message: string;
    data?: unknown;
  };
}

type JsonRpcResponse = JsonRpcSuccessResponse | JsonRpcErrorResponse;

function isJsonRpcError(r: JsonRpcResponse): r is JsonRpcErrorResponse {
  return "error" in r;
}

// ---------------------------------------------------------------------------
// Custom error types
// ---------------------------------------------------------------------------

export class MCPSubsystemUnavailableError extends Error {
  constructor(detail: string) {
    super(`tool subsystem unavailable — MCP server exited: ${detail}`);
    this.name = "MCPSubsystemUnavailableError";
  }
}

export class MCPEmptyToolListError extends Error {
  constructor(stderrSnippet: string) {
    super(
      `tool subsystem returned no tools — diagnostic snapshot at <${stderrSnippet || "no stderr"}>`,
    );
    this.name = "MCPEmptyToolListError";
  }
}

export class MCPProtocolError extends Error {
  readonly code: number;
  constructor(code: number, message: string) {
    super(`JSON-RPC error ${code}: ${message}`);
    this.name = "MCPProtocolError";
    this.code = code;
  }
}

// ---------------------------------------------------------------------------
// Log helper (mirrors bridge.ts: KOSMOS_TUI_LOG_LEVEL, stderr only)
// ---------------------------------------------------------------------------

type LogLevel = "DEBUG" | "INFO" | "WARN" | "ERROR";

const _levelOrder: Record<LogLevel, number> = {
  DEBUG: 0,
  INFO: 1,
  WARN: 2,
  ERROR: 3,
};

function _getLogLevel(): LogLevel {
  const raw = (process.env["KOSMOS_TUI_LOG_LEVEL"] ?? "WARN").toUpperCase();
  if (raw in _levelOrder) return raw as LogLevel;
  return "WARN";
}

function _log(level: LogLevel, ...args: unknown[]): void {
  if (_levelOrder[level] >= _levelOrder[_getLogLevel()]) {
    process.stderr.write(
      `[KOSMOS MCP ${level}] ${args.map(String).join(" ")}\n`,
    );
  }
}

// ---------------------------------------------------------------------------
// KosmosMCPClient
// ---------------------------------------------------------------------------

/**
 * Thin stdio-MCP client for the KOSMOS tool subsystem.
 *
 * Spawns `uv run python -m kosmos.ipc.mcp_server` as a subprocess and speaks
 * MCP JSON-RPC 2.0 directly over its stdin/stdout. One request at a time is
 * correlated via incrementing integer ids; responses are matched by id and
 * resolved via per-request Promises.
 *
 * NOTE: this is NOT the same as `bridge.ts`. `bridge.ts` owns the main REPL
 * session IPC channel (Spec 032). `KosmosMCPClient` is an auxiliary client
 * that talks to a separate `mcp_server.py` subprocess purely for tool
 * discovery and invocation. The two share no state.
 */
export class KosmosMCPClient {
  private readonly _proc: ReturnType<typeof Bun.spawn>;
  private _nextId = 1;
  private readonly _pending = new Map<number, PendingRequest>();
  private _closed = false;
  private _remainder = "";
  private _stderrBuffer = "";

  constructor() {
    const cmd = ["uv", "run", "python", "-m", "kosmos.ipc.mcp_server"];
    _log("INFO", `Spawning MCP server: ${cmd.join(" ")}`);

    this._proc = Bun.spawn(cmd, {
      stdin: "pipe",
      stdout: "pipe",
      stderr: "pipe",
    });

    // Start background stdout reader
    this._startStdoutReader();
    // Capture stderr for error diagnostics
    this._startStderrReader();
  }

  // -------------------------------------------------------------------------
  // Public API
  // -------------------------------------------------------------------------

  /**
   * MCP handshake: initialize → notifications/initialized → tools/list.
   * Returns the list of available tools.
   * Throws {@link MCPSubsystemUnavailableError} if the subprocess exits early.
   * Throws {@link MCPEmptyToolListError} if tools/list returns zero tools.
   * Logs a WARN (but continues) if the cold budget (500 ms) is exceeded by 2x.
   */
  async initialize(): Promise<MCPTool[]> {
    const t0 = Date.now();

    // Step 1 + 2: initialize request / response
    const initResponse = await this._sendRequest("initialize", {
      protocolVersion: MCP_PROTOCOL_VERSION,
      capabilities: { tools: {} },
      clientInfo: { name: CLIENT_NAME, version: CLIENT_VERSION },
    });

    if (isJsonRpcError(initResponse)) {
      throw new MCPProtocolError(
        initResponse.error.code,
        initResponse.error.message,
      );
    }

    const serverProto = (initResponse.result["protocolVersion"] as string | undefined) ?? "(missing)";
    if (serverProto !== MCP_PROTOCOL_VERSION) {
      _log(
        "WARN",
        `MCP protocol version mismatch: client=${MCP_PROTOCOL_VERSION} server=${serverProto}`,
      );
    }

    // Step 3: notifications/initialized (no id — notification, no response expected)
    this._sendNotification("notifications/initialized", {});

    // Step 4 + 5: tools/list
    const tools = await this.listTools();

    const elapsedMs = Date.now() - t0;
    _log("INFO", `MCP handshake complete in ${elapsedMs}ms, tools=${tools.length}`);

    if (elapsedMs > COLD_BUDGET_MS * 2) {
      _log(
        "WARN",
        `MCP cold-path handshake exceeded 2x budget (${COLD_BUDGET_MS * 2}ms): actual=${elapsedMs}ms; kosmos.mcp.handshake_ms=${elapsedMs}`,
      );
    }

    return tools;
  }

  /**
   * Fetch the list of available tools from the MCP server.
   * Throws {@link MCPEmptyToolListError} on empty response.
   */
  async listTools(): Promise<MCPTool[]> {
    const response = await this._sendRequest("tools/list", {});

    if (isJsonRpcError(response)) {
      throw new MCPProtocolError(response.error.code, response.error.message);
    }

    const rawTools = response.result["tools"];
    if (!Array.isArray(rawTools)) {
      throw new MCPProtocolError(
        JSONRPC_INTERNAL_ERROR,
        `tools/list response missing 'tools' array: ${JSON.stringify(response.result)}`,
      );
    }

    if (rawTools.length === 0) {
      throw new MCPEmptyToolListError(this._stderrBuffer.slice(-500));
    }

    return rawTools.map((t: unknown) => {
      const tool = t as Record<string, unknown>;
      return {
        name: String(tool["name"] ?? ""),
        description: String(tool["description"] ?? ""),
        inputSchema: (tool["inputSchema"] as Record<string, unknown>) ?? {},
      };
    });
  }

  /**
   * Invoke a tool by name with the given arguments.
   * Returns the result envelope as defined in contracts/mcp-bridge.md § 3.2.
   */
  async callTool(name: string, args: unknown): Promise<ToolCallResult> {
    const response = await this._sendRequest("tools/call", {
      name,
      arguments: args as Record<string, unknown>,
    });

    if (isJsonRpcError(response)) {
      throw new MCPProtocolError(response.error.code, response.error.message);
    }

    const content = response.result["content"];
    const isError = Boolean(response.result["isError"]);

    if (!Array.isArray(content)) {
      throw new MCPProtocolError(
        JSONRPC_INTERNAL_ERROR,
        `tools/call response missing 'content' array: ${JSON.stringify(response.result)}`,
      );
    }

    return {
      content: content.map((c: unknown) => {
        const item = c as Record<string, unknown>;
        return { type: String(item["type"] ?? "text"), text: String(item["text"] ?? "") };
      }),
      isError,
    };
  }

  /**
   * Terminate the MCP server subprocess (SIGTERM → 3s → SIGKILL).
   */
  async close(): Promise<void> {
    if (this._closed) return;
    this._closed = true;
    _log("INFO", "Closing MCP client — sending SIGTERM");
    try {
      this._proc.stdin.end();
      this._proc.kill("SIGTERM");
      const exitPromise = this._proc.exited;
      const timeoutPromise = new Promise<void>((_, reject) =>
        setTimeout(() => reject(new Error("timeout")), 3000),
      );
      await Promise.race([exitPromise, timeoutPromise]).catch(() => {
        _log("WARN", "MCP server did not exit within 3s — sending SIGKILL");
        this._proc.kill("SIGKILL");
      });
    } catch (e: unknown) {
      _log("WARN", `close error: ${e}`);
    }
    // Reject all pending requests
    for (const [id, pending] of this._pending) {
      pending.reject(
        new MCPSubsystemUnavailableError(`client closed with pending request id=${id}`),
      );
    }
    this._pending.clear();
  }

  // -------------------------------------------------------------------------
  // Private helpers
  // -------------------------------------------------------------------------

  /**
   * Send a JSON-RPC 2.0 request and return a Promise that resolves with the
   * matching response (matched by `id`).
   * Throws {@link MCPSubsystemUnavailableError} if the subprocess exits before responding.
   */
  private _sendRequest(
    method: string,
    params: Record<string, unknown>,
  ): Promise<JsonRpcResponse> {
    if (this._closed) {
      return Promise.reject(
        new MCPSubsystemUnavailableError("client is already closed"),
      );
    }

    const id = this._nextId++;
    const request: JsonRpcRequest = {
      jsonrpc: "2.0",
      id,
      method,
      params,
    };

    return new Promise<JsonRpcResponse>((resolve, reject) => {
      // Check subprocess health before registering
      if (this._proc.killed) {
        reject(new MCPSubsystemUnavailableError("MCP server process already exited"));
        return;
      }

      this._pending.set(id, { resolve, reject });

      const line = JSON.stringify(request) + "\n";
      _log("DEBUG", `→ MCP request id=${id} method=${method}`);

      try {
        this._proc.stdin.write(line);
      } catch (e: unknown) {
        this._pending.delete(id);
        reject(new MCPSubsystemUnavailableError(`stdin write failed: ${e}`));
        return;
      }

      // Wire subprocess exit to reject pending request
      this._proc.exited.then((exitCode: number) => {
        const p = this._pending.get(id);
        if (p) {
          this._pending.delete(id);
          p.reject(
            new MCPSubsystemUnavailableError(
              `MCP server exited with code ${exitCode} while awaiting response to id=${id}`,
            ),
          );
        }
      });
    });
  }

  /**
   * Send a JSON-RPC 2.0 notification (no `id`, no response expected).
   */
  private _sendNotification(
    method: string,
    params: Record<string, unknown>,
  ): void {
    if (this._closed || this._proc.killed) {
      _log("WARN", `Cannot send notification ${method} — client closed or process exited`);
      return;
    }
    const notification: JsonRpcNotification = { jsonrpc: "2.0", method, params };
    const line = JSON.stringify(notification) + "\n";
    _log("DEBUG", `→ MCP notification method=${method}`);
    try {
      this._proc.stdin.write(line);
    } catch (e: unknown) {
      _log("WARN", `Notification write failed for ${method}: ${e}`);
    }
  }

  /**
   * Background loop: reads stdout line-by-line, parses JSON-RPC responses,
   * and resolves pending requests.
   */
  private _startStdoutReader(): void {
    ;(async () => {
      const reader = this._proc.stdout.getReader();
      const decoder = new TextDecoder("utf-8");
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          const buffered = this._remainder + chunk;
          const lines = buffered.split("\n");
          // Last element may be an incomplete line
          this._remainder = lines.pop() ?? "";

          for (const line of lines) {
            const trimmed = line.trim();
            if (!trimmed) continue;
            _log("DEBUG", `← MCP raw: ${trimmed.slice(0, 200)}`);
            this._handleLine(trimmed);
          }
        }
        // EOF: reject all pending requests
        this._rejectAllPending("MCP server stdout EOF — process exited");
      } catch (e: unknown) {
        _log("WARN", `MCP stdout reader error: ${e}`);
        this._rejectAllPending(`MCP server stdout error: ${e}`);
      }
    })();
  }

  /**
   * Background loop: buffers stderr for diagnostics (last 500 chars).
   */
  private _startStderrReader(): void {
    ;(async () => {
      const reader = this._proc.stderr.getReader();
      const decoder = new TextDecoder("utf-8");
      try {
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, { stream: true });
          this._stderrBuffer += chunk;
          // Keep only the last 2000 chars to avoid unbounded growth
          if (this._stderrBuffer.length > 2000) {
            this._stderrBuffer = this._stderrBuffer.slice(-2000);
          }
          _log("DEBUG", `MCP stderr: ${chunk.trim()}`);
        }
      } catch {
        // stderr reader failure is not fatal — diagnostics only
      }
    })();
  }

  /**
   * Parse and dispatch a single stdout line as a JSON-RPC 2.0 response.
   */
  private _handleLine(line: string): void {
    let parsed: unknown;
    try {
      parsed = JSON.parse(line);
    } catch {
      _log("ERROR", `MCP parse error on line: ${line.slice(0, 200)}`);
      // Emit parse error to all pending (could be any id)
      for (const [id, p] of this._pending) {
        this._pending.delete(id);
        p.reject(
          new MCPProtocolError(JSONRPC_PARSE_ERROR, `parse error on: ${line.slice(0, 100)}`),
        );
      }
      return;
    }

    const msg = parsed as Record<string, unknown>;

    // Ignore notifications from server (no id field, has method)
    if (!("id" in msg) && "method" in msg) {
      _log("DEBUG", `MCP server notification: ${String(msg["method"])}`);
      return;
    }

    const id = msg["id"];
    if (typeof id !== "number") {
      _log("WARN", `MCP response with non-numeric id: ${JSON.stringify(id)}`);
      return;
    }

    const pending = this._pending.get(id);
    if (!pending) {
      _log("WARN", `MCP response for unknown id=${id} — ignored`);
      return;
    }

    this._pending.delete(id);

    if ("error" in msg && msg["error"] !== null && msg["error"] !== undefined) {
      const err = msg["error"] as Record<string, unknown>;
      const response: JsonRpcErrorResponse = {
        jsonrpc: "2.0",
        id,
        error: {
          code: typeof err["code"] === "number" ? err["code"] : JSONRPC_INTERNAL_ERROR,
          message: String(err["message"] ?? "unknown error"),
          data: err["data"],
        },
      };
      _log("DEBUG", `← MCP error id=${id} code=${response.error.code}`);
      pending.resolve(response);
    } else if ("result" in msg) {
      const response: JsonRpcSuccessResponse = {
        jsonrpc: "2.0",
        id,
        result: (msg["result"] as Record<string, unknown>) ?? {},
      };
      _log("DEBUG", `← MCP result id=${id}`);
      pending.resolve(response);
    } else {
      _log("ERROR", `MCP response missing both 'result' and 'error' for id=${id}`);
      pending.reject(
        new MCPProtocolError(
          JSONRPC_INVALID_REQUEST,
          `response missing result/error for id=${id}`,
        ),
      );
    }
  }

  /**
   * Reject all pending requests with the given reason (process exit / EOF).
   */
  private _rejectAllPending(reason: string): void {
    for (const [id, p] of this._pending) {
      this._pending.delete(id);
      p.reject(new MCPSubsystemUnavailableError(`${reason} (pending id=${id})`));
    }
  }
}
