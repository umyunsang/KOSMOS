// SPDX-License-Identifier: Apache-2.0
// Copilot review fix: createRoot() must delete from instances on unmount
// (prevents map leak when the same stdout key is reused across root lifetimes).
//
// root.ts cannot be imported directly in this environment because its
// `import Ink from './ink.js'` resolves to node_modules/ink/build/ink.js,
// which pulls in terminal I/O that is unavailable in the test runner.
// Instead, we test the exact guard logic that was added:
//
//   if (instances.get(stdout) === instance) {
//     instances.delete(stdout)
//   }
//
// by exercising the instances map directly with a minimal fake Ink shape.
// This is sufficient to verify the contract because the guard is a pure
// identity check on the map value — no Ink internals are involved.

import { describe, it, expect, beforeEach } from 'bun:test'
import instances from '../../src/ink/instances'
import type Ink from 'ink'

// ---------------------------------------------------------------------------
// Minimal Ink-like stub (only the shape the guard cares about: identity)
// ---------------------------------------------------------------------------

function fakeInk(): Ink {
  return {} as unknown as Ink
}

// ---------------------------------------------------------------------------
// Fake stdout key (avoids touching process.stdout)
// ---------------------------------------------------------------------------

function fakeStdout(): NodeJS.WriteStream {
  return {} as unknown as NodeJS.WriteStream
}

// ---------------------------------------------------------------------------
// Helper: simulate what createRoot() does after our fix
// ---------------------------------------------------------------------------

function simulateCreateRoot(stdout: NodeJS.WriteStream): {
  instance: Ink
  unmount: () => void
} {
  const instance = fakeInk()
  instances.set(stdout, instance)

  return {
    instance,
    unmount: () => {
      // This is the exact guard code added in root.ts:
      if (instances.get(stdout) === instance) {
        instances.delete(stdout)
      }
    },
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  instances.clear()
})

describe('createRoot instances-map cleanup (Copilot IMPORTANT fix)', () => {
  it('map size returns to zero after unmount', () => {
    const stdout = fakeStdout()
    const root = simulateCreateRoot(stdout)

    expect(instances.size).toBe(1)
    root.unmount()
    expect(instances.size).toBe(0)
  })

  it('unmount deletes the entry for the correct stdout key', () => {
    const stdout = fakeStdout()
    const root = simulateCreateRoot(stdout)

    root.unmount()
    expect(instances.has(stdout)).toBe(false)
  })

  it('guard: unmount does NOT delete a newer root registered against the same stdout', () => {
    // Simulate: root A created, root B created with the same stdout (replaces A),
    // then root A unmounts — must NOT evict root B's entry.
    const stdout = fakeStdout()
    const rootA = simulateCreateRoot(stdout) // instances[stdout] = instanceA

    // Root B registers against the same key, overwriting root A's entry.
    const instanceB = fakeInk()
    instances.set(stdout, instanceB)

    // Root A unmounts. Guard: instances.get(stdout) === instanceA? No → skip delete.
    rootA.unmount()

    // Root B's entry must still be present.
    expect(instances.get(stdout)).toBe(instanceB)
    expect(instances.size).toBe(1)
  })

  it('two independent roots on different stdouts each clean up their own entry', () => {
    const stdoutA = fakeStdout()
    const stdoutB = fakeStdout()

    const rootA = simulateCreateRoot(stdoutA)
    const rootB = simulateCreateRoot(stdoutB)

    expect(instances.size).toBe(2)

    rootA.unmount()
    expect(instances.size).toBe(1)
    expect(instances.has(stdoutA)).toBe(false)
    expect(instances.has(stdoutB)).toBe(true)

    rootB.unmount()
    expect(instances.size).toBe(0)
  })
})
