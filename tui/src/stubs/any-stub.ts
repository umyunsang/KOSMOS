// SPDX-License-Identifier: Apache-2.0
// Stage-1 NO-OP stub — resolves unreachable CC-only module imports so the
// runtime bundle loads. Real implementations are tracked in the CC TUI
// Fidelity Meta-Epic (Epic #1633).
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any

// Smart Proxy that cooperates with primitive coercion / iteration / JSON
const makeStub = (): any => {
  const target = function () {} as any
  return new Proxy(target, {
    get(_t, p) {
      // Well-known symbols used by JS engine during coercion
      if (p === Symbol.toPrimitive) return () => ''
      if (p === Symbol.iterator) return function* () {}
      if (p === Symbol.asyncIterator) return async function* () {}
      if (p === Symbol.toStringTag) return 'Stub'
      if (p === 'then') return undefined // not a thenable
      if (p === 'toString') return () => ''
      if (p === 'valueOf') return () => undefined
      if (p === 'toJSON') return () => null
      if (p === 'length') return 0
      if (p === 'constructor') return Object
      return __stub
    },
    apply() { return __stub },
    construct() { return __stub },
    has() { return false },
    ownKeys() { return [] },
    getOwnPropertyDescriptor() { return undefined },
  })
}

const __stub: any = makeStub()

export default __stub

// Common utility exports for lodash-es-style consumers
export const memoize = <T extends (...args: any[]) => any>(fn: T): T => fn
export const sample = <T>(arr: readonly T[]): T | undefined =>
  arr[Math.floor(Math.random() * arr.length)]
export const tokenize = (input: string): unknown[] => [input]

// CC internal symbols routed via tsconfig paths to this stub
export const BROWSER_TOOLS: readonly string[] = []
export const COMPUTER_USE_TOOLS: readonly string[] = []
export const datadogLogs = { logger: { log: __noop, error: __noop, warn: __noop, info: __noop } }
export const log = __noop
export const logger = { log: __noop, error: __noop, warn: __noop, info: __noop, debug: __noop }
