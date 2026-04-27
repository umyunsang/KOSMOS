// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration · Epic #2077 TDZ fix.
//
// CC declares ``const proactiveModule = feature('PROACTIVE') ? require(...) : null;``
// at module scope in four files. Bun's loader evaluates these at import time,
// triggering a TDZ "cannot access proactiveModule before initialization"
// error when the four files form a circular import graph. Routing through
// a lazy getter defers the require() to first call, breaking the cycle.
//
// KOSMOS does not ship the proactive feature (`tui/src/proactive/` does not
// exist; `feature('PROACTIVE')` and `feature('KAIROS')` always return false).
// The getter therefore always returns null in production, but the indirection
// preserves the upstream API for any future Epic that reintroduces it.

import { feature } from 'bun:bundle'

type ProactiveModule = typeof import('../proactive/index.js')

let _cached: ProactiveModule | null | undefined = undefined

export function getProactiveModule(): ProactiveModule | null {
  if (_cached !== undefined) return _cached
  if (feature('PROACTIVE') || feature('KAIROS')) {
    try {
      // eslint-disable-next-line @typescript-eslint/no-require-imports
      _cached = require('../proactive/index.js') as ProactiveModule
    } catch {
      _cached = null
    }
  } else {
    _cached = null
  }
  return _cached
}

export function isProactiveActive(): boolean {
  return getProactiveModule()?.isProactiveActive() ?? false
}

export function isProactivePaused(): boolean {
  return getProactiveModule()?.isProactivePaused() ?? false
}

export function activateProactive(source: string): void {
  getProactiveModule()?.activateProactive(source)
}

export function deactivateProactive(): void {
  getProactiveModule()?.deactivateProactive()
}

export function pauseProactive(): void {
  getProactiveModule()?.pauseProactive()
}

export function resumeProactive(): void {
  getProactiveModule()?.resumeProactive()
}

export function setContextBlocked(blocked: boolean): void {
  getProactiveModule()?.setContextBlocked(blocked)
}
