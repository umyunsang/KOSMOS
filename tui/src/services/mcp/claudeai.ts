// SPDX-License-Identifier: Apache-2.0
// KOSAX-original — Epic #1633 / Epic #2077 KOSAX no-op stub.
//
// CC's claudeai.ts fetched MCP server configurations from the claude.ai
// subscription service. KOSAX does not use the Anthropic claude.ai service —
// MCP servers are configured locally via KOSAX_* env vars and
// ~/.kosax/settings.json. This stub satisfies the import from
// services/mcp/useManageMCPConnections.ts without reaching the network.

export function clearClaudeAIMcpConfigsCache(): void {
  // KOSAX-original: no-op — no claude.ai MCP config cache to clear.
}

export async function fetchClaudeAIMcpConfigsIfEligible(): Promise<Record<string, unknown>> {
  // KOSAX-original: returns empty config — KOSAX does not use claude.ai MCP.
  return {}
}
