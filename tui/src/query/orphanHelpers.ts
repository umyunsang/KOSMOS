// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #2077 K-EXAONE tool wiring · T016 (FR-009 pairing).
//
// Extracted from tui/src/query/deps.ts so the FR-009 pairing-invariant unit
// tests do not transitively pull autoCompact.ts → 'bun:bundle'. The Bun
// preload plugin shim that maps `bun:bundle` to a stub does not always
// intercept static-import resolution under `bun test` on CI, so isolating
// these pure helpers in a leaf module avoids the issue entirely.

/**
 * Checks whether a tool_result call_id is an orphan given the set of
 * tool_use ids seen so far in the same turn. Returns true when the id is
 * absent from the seen set (orphan) or false when it is paired.
 *
 * This pure function lets tests exercise the FR-009 pairing invariant
 * without spinning up a mock bridge or the full queryModelWithStreaming
 * generator.
 *
 * @param toolUseId  - The tool_use_id carried by the tool_result frame.
 * @param seenIds    - The Set of call_ids registered by tool_call frames so far.
 */
export function isOrphanToolResult(
  toolUseId: string,
  seenIds: ReadonlySet<string>,
): boolean {
  if (!toolUseId) return false
  return !seenIds.has(toolUseId)
}

/**
 * Builds the error message string that queryModelWithStreaming emits when it
 * detects an orphan tool_result. Tests assert on this exact string to verify
 * the visible-error contract (FR-009).
 */
export function orphanErrorMessage(toolUseId: string): string {
  return `tool_result_orphan: Tool result references unknown tool_use_id "${toolUseId}"`
}
