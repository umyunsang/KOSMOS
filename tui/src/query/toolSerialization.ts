// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #2077 K-EXAONE tool wiring · T005.
//
// Mirrors _cc_reference/api.ts:toolToAPISchema (line 119-266)
// Converts the TUI's Zod-defined tool catalog into ToolDefinition[] for
// ChatRequestFrame.tools. Uses zod/v4 built-in z.toJSONSchema() (Draft 2020-12).

import { z } from 'zod/v4'
import { getEmptyToolPermissionContext, type Tool } from '../Tool.js'
import type { ToolDefinition } from '../ipc/codec.js'

// ---------------------------------------------------------------------------
// Serialization helpers
// ---------------------------------------------------------------------------

/**
 * Converts a single {@link Tool} to an OpenAI-compatible {@link ToolDefinition}.
 *
 * - `function.name`        = tool.name
   * - `function.description` = await tool.prompt(...)
   * - `function.parameters`  = z.toJSONSchema(tool.inputSchema) — Draft 2020-12
   */
export async function toolToFunctionSchema(tool: Tool): Promise<ToolDefinition> {
  const description = await tool.prompt({
    getToolPermissionContext: async () => getEmptyToolPermissionContext(),
    tools: [tool],
    agents: [],
  })

  const parameters = (
    tool.inputJSONSchema ?? z.toJSONSchema(tool.inputSchema)
  ) as Record<string, unknown>

  return {
    type: 'function' as const,
    function: {
      name: tool.name,
      description,
      parameters,
    },
  }
}

/**
 * Returns the TUI-provided model-facing inventory.
 *
 * UMMAYA's backend registry is now the single source for concrete adapter
 * schemas. Returning an empty list here keeps CC's TUI Tool.call execution
 * surface available without leaking root primitives as model-facing tools.
 */
export async function getToolDefinitionsForFrame(): Promise<ToolDefinition[]> {
  return []
}
