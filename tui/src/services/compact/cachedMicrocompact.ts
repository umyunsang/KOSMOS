// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — cached microcompact minimal module.
//
// Original CC module cached intermediate microcompact results in process
// memory keyed by message-tail hash. KOSMOS Spec 026 (prompt registry +
// session_compact) handles compaction on the Python backend side; the
// frontend-side cached state is therefore a no-op shell that preserves the
// `microCompact.ts` consumer's expected shape.

export interface CachedMCState {
  // Opaque to consumers; carries no behavior in KOSMOS.
  readonly _kind: 'kosmos-noop-cached-mc-state'
}

const SHARED_STATE: CachedMCState = Object.freeze({ _kind: 'kosmos-noop-cached-mc-state' })

export function createCachedMCState(): CachedMCState {
  return SHARED_STATE
}

// Some legacy consumers expect a "tryGet"/"set" surface — keep a minimal one.
export function tryGet(_state: CachedMCState, _key: string): null {
  return null
}

export function set(_state: CachedMCState, _key: string, _value: unknown): void {
  // no-op
}
