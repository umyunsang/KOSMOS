// SPDX-License-Identifier: Apache-2.0
// Epic #2077 K-EXAONE tool wiring — Task T016.
//
// Tests for FR-009 pairing invariant: every tool_result must pair to a prior
// tool_use block; orphan tool_results MUST surface as visible errors.
//
// Strategy: unit-test the pure helpers exported by deps.ts rather than
// driving the full queryModelWithStreaming generator through a mock bridge.
// This keeps the tests fast, deterministic, and free of process-spawn overhead
// while still verifying the exact logic that enforces the invariant.

import { describe, test, expect, mock } from 'bun:test'

// Bun's preload plugin onResolve does not always intercept `bun:bundle` for
// modules pulled in by a static import that crosses package boundaries; mock
// it explicitly so deps.ts' transitive load of autoCompact.ts resolves.
mock.module('bun:bundle', () => ({ feature: () => false }))

import { isOrphanToolResult, orphanErrorMessage } from '../../src/query/deps.js'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a Set of seen tool_use ids, simulating prior tool_call frames. */
function seenSet(...ids: string[]): Set<string> {
  return new Set(ids)
}

// ---------------------------------------------------------------------------
// Test 1 — happy path: tool_use with id 'A' then tool_result with id 'A'
// ---------------------------------------------------------------------------

describe('isOrphanToolResult — happy path', () => {
  test('paired tool_use/tool_result is not an orphan', () => {
    // Simulate: tool_call frame arrives with call_id 'A'
    const seen = seenSet('A')

    // tool_result frame arrives with tool_use_id 'A'
    const result = isOrphanToolResult('A', seen)

    // FR-009: paired result is NOT an orphan — no error envelope emitted
    expect(result).toBe(false)
  })

  test('empty tool_use_id is not treated as orphan', () => {
    // An empty string call_id is a degenerate case (malformed frame); the
    // implementation guards with `if (!toolUseId) return false` to avoid
    // false-positive orphan errors on frames where the backend omitted the id.
    const seen = seenSet('A')
    expect(isOrphanToolResult('', seen)).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// Test 2 — orphan path: tool_result with id 'X' without prior tool_use 'X'
// ---------------------------------------------------------------------------

describe('isOrphanToolResult — orphan path', () => {
  test('tool_result without prior tool_use is an orphan', () => {
    // No tool_call frames at all in this turn
    const seen = seenSet()

    // tool_result arrives with tool_use_id 'X' — no matching tool_use
    const result = isOrphanToolResult('X', seen)

    // FR-009: unpaired result IS an orphan — visible error MUST be surfaced
    expect(result).toBe(true)
  })

  test('orphanErrorMessage contains the tool_use_id and kind tag', () => {
    const msg = orphanErrorMessage('X')

    // The message must identify the orphan by id and carry the 'tool_result_orphan'
    // kind tag so log consumers can filter on it.
    expect(msg).toContain('tool_result_orphan')
    expect(msg).toContain('"X"')
  })

  test('tool_result with id not in seen set is orphan even when seen has other ids', () => {
    // Seen set has 'A' and 'B' but not 'X'
    const seen = seenSet('A', 'B')

    expect(isOrphanToolResult('X', seen)).toBe(true)
  })
})

// ---------------------------------------------------------------------------
// Test 3 — mixed path: 2 tool_uses (A, B) then 3 tool_results (A, B, C)
// ---------------------------------------------------------------------------

describe('isOrphanToolResult — mixed path', () => {
  test('C is the only orphan when A and B are paired', () => {
    // Two tool_call frames registered ids A and B
    const seen = seenSet('A', 'B')

    // Three tool_result frames arrive: A and B are paired, C is orphan
    expect(isOrphanToolResult('A', seen)).toBe(false)
    expect(isOrphanToolResult('B', seen)).toBe(false)
    expect(isOrphanToolResult('C', seen)).toBe(true)
  })

  test('orphanErrorMessage for C references the correct id', () => {
    const msg = orphanErrorMessage('C')

    expect(msg).toContain('tool_result_orphan')
    expect(msg).toContain('"C"')
    // Ensure A and B are not mentioned — error is specific to the orphan id
    expect(msg).not.toContain('"A"')
    expect(msg).not.toContain('"B"')
  })

  test('registering A and B then querying them returns false for both', () => {
    const seen = seenSet()
    // Simulate sequential tool_call registrations
    seen.add('A')
    seen.add('B')

    expect(isOrphanToolResult('A', seen)).toBe(false)
    expect(isOrphanToolResult('B', seen)).toBe(false)
  })
})
