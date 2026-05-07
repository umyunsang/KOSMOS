// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #1633 / Epic #2077 UMMAYA no-op stub.
//
// CC's claudeai.ts fetched MCP server configurations from the claude.ai
// subscription service. UMMAYA does not use the Anthropic claude.ai service —
// MCP servers are configured locally via UMMAYA_* env vars and
// ~/.ummaya/settings.json. This stub satisfies the import from
// services/mcp/useManageMCPConnections.ts without reaching the network.

export function clearClaudeAIMcpConfigsCache(): void {
  // UMMAYA-original: no-op — no claude.ai MCP config cache to clear.
}

export async function fetchClaudeAIMcpConfigsIfEligible(): Promise<Record<string, unknown>> {
  // UMMAYA-original: returns empty config — UMMAYA does not use claude.ai MCP.
  return {}
}
