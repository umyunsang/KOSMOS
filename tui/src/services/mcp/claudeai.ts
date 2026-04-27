// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 / Epic #2077 KOSMOS no-op stub.
//
// CC's claudeai.ts fetched MCP server configurations from the claude.ai
// subscription service. KOSMOS does not use the Anthropic claude.ai service —
// MCP servers are configured locally via KOSMOS_* env vars and
// ~/.kosmos/settings.json. This stub satisfies the import from
// services/mcp/useManageMCPConnections.ts without reaching the network.

export function clearClaudeAIMcpConfigsCache(): void {
  // KOSMOS-original: no-op — no claude.ai MCP config cache to clear.
}

export async function fetchClaudeAIMcpConfigsIfEligible(): Promise<Record<string, unknown>> {
  // KOSMOS-original: returns empty config — KOSMOS does not use claude.ai MCP.
  return {}
}
