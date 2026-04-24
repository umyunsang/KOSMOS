// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 FR-007/FR-017 bootstrap helper.
//
// Holds the lazily-spawned, process-wide IPCBridge instance. This is the
// single place `query/deps.ts::callModel` reads from to construct an
// `LLMClient` — it guarantees one Python backend per TUI process, started on
// first use, shared across every turn.
//
// The bridge is spawned lazily because cold-starting `uv run kosmos --ipc
// stdio` adds ~1–2 s to TUI boot; we don't pay that cost unless the first
// prompt is actually typed. Subsequent turns reuse the running child.

import { createBridge, type IPCBridge } from './bridge.js'

let _bridge: IPCBridge | null = null
let _sessionId: string | null = null

export function getOrCreateKosmosBridge(): IPCBridge {
  if (_bridge !== null) return _bridge
  _bridge = createBridge({})
  return _bridge
}

export function getKosmosBridgeSessionId(): string {
  if (_sessionId === null) {
    _sessionId = crypto.randomUUID()
  }
  return _sessionId
}

export async function closeKosmosBridge(): Promise<void> {
  if (_bridge !== null) {
    const b = _bridge
    _bridge = null
    await b.close()
  }
}
