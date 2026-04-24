// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// The upstream Claude Code claude.ai MCP proxy integration has no counterpart
// in KOSMOS: we neither authenticate against claude.ai nor proxy its MCP
// connectors (Datadog, Slack, Gmail, BigQuery, PubMed, etc.). Epic #1633 P2
// deleted the real implementation, but multiple callers (main.tsx, mcp/config,
// useManageMCPConnections, useMcpConnectivityStatus) still import from this
// path. Restoring a no-op stub keeps the 298-file import surface intact
// without reintroducing Anthropic-specific runtime behaviour.

import type { ScopedMcpServerConfig } from './types.js'

export async function fetchClaudeAIMcpConfigsIfEligible(): Promise<
  Record<string, ScopedMcpServerConfig>
> {
  return {}
}

export function hasClaudeAiMcpEverConnected(_serverName: string): boolean {
  return false
}

export function markClaudeAiMcpConnected(_serverName: string): void {
  /* no-op */
}

export function clearClaudeAIMcpConfigsCache(): void {
  /* no-op */
}
