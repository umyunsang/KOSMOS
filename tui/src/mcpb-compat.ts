// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #2293 FR-010 · mcpb compatibility shim.
//
// Purpose: every tui/src/ file that needs mcpb types or the lazy manifest
// validator imports from 'src/mcpb-compat.js' instead of directly from the
// mcpb package. This keeps the package literal isolated to a single shim
// file (FR-010 / SC-007 grep gate).
//
// Background: mcpb uses zod v3 which eagerly creates ~300 .bind(this) schema
// instances at import time (~700 KB of heap). loadMcpb() defers that cost to
// sessions that actually process .dxt files.

export type { McpbManifest } from '@anthropic-ai/mcpb'

/**
 * Lazy-load the mcpb package.
 *
 * Callers use:
 *   const { McpbManifestSchema } = await loadMcpb()
 */
export async function loadMcpb(): Promise<
  typeof import('@anthropic-ai/mcpb')
> {
  return import('@anthropic-ai/mcpb')
}
