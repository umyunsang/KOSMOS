// [P0 reconstructed · Pass 3 · MonitorMcpTask state]
// Reference: claudefa.st MonitorTool docs +
//            claude-code-from-source Ch3 Task system +
//            sibling DreamTask.ts / LocalAgentTask.ts.
//
// `monitor_mcp` tasks observe one MCP (Model Context Protocol) server for
// tool-call events and surface them in the background tasks indicator.
// Upstream CC activates this only when the user registers a watch via
// `MonitorTool`. KOSMOS leaves the shape honest so the BackgroundTasksDialog
// picker doesn't crash when such tasks are present.

import type { TaskStateBase } from '../../Task.js'

/** One observed MCP tool invocation captured by the monitor. */
export interface McpObservation {
  /** Timestamp when the tool invocation began. */
  timestampIso: string
  /** MCP tool identifier (server.tool_name). */
  toolId: string
  /** Short label for the event feed. */
  summary: string
  /** Whether the invocation succeeded. */
  ok: boolean
}

/** State for a single MCP monitor task. */
export type MonitorMcpTaskState = TaskStateBase & {
  type: 'monitor_mcp'
  /** Name of the MCP server being watched. */
  serverName: string
  /** Human-readable title (usually "Monitor <serverName>"). */
  title: string
  /** Whether the user has backgrounded this task. */
  isBackgrounded: boolean
  /** Rolling window of recent tool invocations (capped to avoid unbounded growth). */
  recentObservations: McpObservation[]
  /** Total tool calls observed since task start (may exceed recentObservations.length). */
  totalObservationCount: number
  /** Optional abort controller so kill / disconnect can interrupt. */
  abortController?: AbortController
}
