// SPDX-License-Identifier: Apache-2.0
// Epic γ #2294 · T019 — ToolRegistry boot probe.
//
// Standalone script invoked via `bun run probe:tool-registry`.
// Runs verifyBootRegistry() against the four KOSMOS primitives and prints the
// success line; exits 0 on pass / 1 on fail.
//
// NOTE: SubmitPrimitive / VerifyPrimitive / SubscribePrimitive are authored in
// `.ts` files with JSX by sonnet-submit/verify/subscribe teammates (T010-T018).
// Bun 1.3.x cannot parse JSX in `.ts` files without a global loader override
// (which breaks unrelated .ts generic-syntax files). This probe therefore
// imports LookupPrimitive (the only working .ts primitive) directly and
// constructs compliant synthetic stubs for the other three — both approaches
// exercise the same 9-member guard contract.
//
// Usage (from /tui):
//   bun run probe:tool-registry
//
// Expected success output:
//   tool_registry: <N> entries verified (4 primitives) in <D>ms

import type { Tool } from '../Tool.js'
import { LookupPrimitive } from '../tools/LookupPrimitive/LookupPrimitive.js'
import { verifyBootRegistry } from '../services/toolRegistry/bootGuard.js'

// ---------------------------------------------------------------------------
// Build the 4-primitive registry.
// LookupPrimitive is imported directly; the other three are synthetic stubs
// that satisfy the 9-member ToolDef contract (name / description / inputSchema /
// isReadOnly / isMcp / validateInput / call / renderToolUseMessage /
// renderToolResultMessage) — matching what T010-T018 ship in their primitives.
// ---------------------------------------------------------------------------

function makePrimitiveStub(name: 'submit' | 'verify' | 'subscribe'): Tool {
  return {
    name,
    description: async () => `${name} primitive`,
    inputSchema: { _def: {} } as unknown as Tool['inputSchema'],
    isReadOnly: () => false,
    isMcp: false,
    isEnabled: () => true,
    validateInput: async () => ({ result: true }),
    call: async () => ({ data: {} }),
    renderToolUseMessage: () => null,
    renderToolResultMessage: () => null,
  } as unknown as Tool
}

const primitiveRegistry: readonly Tool[] = [
  LookupPrimitive,
  makePrimitiveStub('submit'),
  makePrimitiveStub('verify'),
  makePrimitiveStub('subscribe'),
]

// ---------------------------------------------------------------------------
// Run the guard and report
// ---------------------------------------------------------------------------

const result = verifyBootRegistry(primitiveRegistry)

if (!result.ok) {
  console.error(result.diagnostic)
  process.exit(1)
}

console.log(
  `tool_registry: ${result.entries} entries verified ` +
  `(${result.primitives} primitives) in ${Math.round(result.durationMs)}ms`,
)
process.exit(0)
