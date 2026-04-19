// SPDX-License-Identifier: Apache-2.0
// T116 — Store-selector subscription test (US7 scenario 3).
// FR-050: subscribing components only re-render when their selected slice changes.
//
// Strategy: exercise the Zustand-compatible vanilla store's `subscribe` API
// (which `useSessionStore` / `useSyncExternalStore` wraps) by attaching two
// listener spies with different selectors before dispatching ASSISTANT_CHUNK.
//   - Selector A: s.message_order  — array reference is unchanged when the
//     chunk is for an already-tracked message id. Must NOT fire.
//   - Selector B: s.messages.get(<that-message-id>)?.text (computed from chunks)
//     — the Message Map entry is replaced by the reducer. MUST fire exactly once.
//
// Note: the vanilla store fires all listeners unconditionally on every
// state change; selector-based memoisation is the responsibility of the
// subscriber (useSyncExternalStore bails out when snapshot hasn't changed).
// We replicate that pattern here: listeners snapshot their slice, compare
// with Object.is, and increment a counter only when the slice actually changed.

import { describe, it, expect, beforeEach } from 'bun:test'
import {
  sessionStore,
  dispatchSessionAction,
  getSessionSnapshot,
} from '../../src/store/session-store'
import type { SessionState } from '../../src/store/session-store'

// ---------------------------------------------------------------------------
// Reset helpers
// ---------------------------------------------------------------------------

function resetStore(): void {
  dispatchSessionAction({ type: 'SESSION_EVENT', event: 'new', payload: {} })
}

// ---------------------------------------------------------------------------
// Selector-aware subscribe helper — mirrors useSyncExternalStore semantics.
// Returns { count, unsubscribe }.
// ---------------------------------------------------------------------------

function subscribeSelector<T>(
  selector: (s: SessionState) => T,
): { getCount: () => number; unsubscribe: () => void } {
  let prev = selector(sessionStore.getState())
  let count = 0

  const unsubscribe = sessionStore.subscribe(() => {
    const next = selector(sessionStore.getState())
    if (!Object.is(next, prev)) {
      prev = next
      count++
    }
  })

  return { getCount: () => count, unsubscribe }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Store selector subscription — ASSISTANT_CHUNK (T116, FR-050)', () => {
  beforeEach(() => {
    resetStore()
  })

  it('message_order selector does NOT fire when ASSISTANT_CHUNK is for an already-tracked id', () => {
    const MESSAGE_ID = 'msg-existing'

    // Prime the store: first chunk creates the message and appends to message_order
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'Hello',
      done: false,
    })

    // Verify the message is now tracked
    const snap0 = getSessionSnapshot()
    expect(snap0.message_order).toContain(MESSAGE_ID)

    // Start counting from this stable baseline
    const orderSub = subscribeSelector((s: SessionState) => s.message_order)

    // Fire a second chunk for the same message_id.
    // Reducer returns existing message_order reference unchanged (identity preserved).
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: ' world',
      done: false,
    })

    orderSub.unsubscribe()

    // message_order array reference must not have changed → selector fires = 0
    expect(orderSub.getCount()).toBe(0)
  })

  it('message text selector DOES fire exactly once when ASSISTANT_CHUNK appends a delta', () => {
    const MESSAGE_ID = 'msg-text-watch'

    // Helper: derive message text from chunks
    const textSelector = (s: SessionState): string =>
      s.messages.get(MESSAGE_ID)?.chunks.join('') ?? ''

    // Subscribe before the first chunk — baseline snapshot is empty string
    const textSub = subscribeSelector(textSelector)

    // Dispatch the first chunk (creates the message)
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'Hello',
      done: false,
    })

    textSub.unsubscribe()

    // The text changed from '' to 'Hello' → exactly one fire
    expect(textSub.getCount()).toBe(1)
    expect(textSelector(getSessionSnapshot())).toBe('Hello')
  })

  it('message text selector fires for each new delta on the same message', () => {
    const MESSAGE_ID = 'msg-multi-chunk'

    const textSelector = (s: SessionState): string =>
      s.messages.get(MESSAGE_ID)?.chunks.join('') ?? ''

    // Seed the first chunk so message exists
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'A',
      done: false,
    })

    // Now subscribe from the current stable state
    const textSub = subscribeSelector(textSelector)

    // Two more distinct deltas — each should trigger the selector
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'B',
      done: false,
    })
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'C',
      done: true,
    })

    textSub.unsubscribe()

    expect(textSub.getCount()).toBe(2)
    expect(textSelector(getSessionSnapshot())).toBe('ABC')
  })

  it('message_order selector IS fired for a new (unseen) message id in ASSISTANT_CHUNK', () => {
    const NEW_ID = 'msg-brand-new'

    const orderSub = subscribeSelector((s: SessionState) => s.message_order)

    // First chunk for a brand-new id → reducer appends to message_order
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: NEW_ID,
      delta: 'Hi',
      done: false,
    })

    orderSub.unsubscribe()

    // message_order changed (new id appended) → selector should fire once
    expect(orderSub.getCount()).toBe(1)
    expect(getSessionSnapshot().message_order).toContain(NEW_ID)
  })

  it('unrelated slice selector does NOT fire on unrelated action (COORDINATOR_PHASE)', () => {
    const MESSAGE_ID = 'msg-phase-irrelevant'

    // Seed a known message
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: MESSAGE_ID,
      delta: 'seed',
      done: false,
    })

    const textSub = subscribeSelector(
      (s: SessionState) => s.messages.get(MESSAGE_ID)?.chunks.join('') ?? '',
    )
    const orderSub = subscribeSelector((s: SessionState) => s.message_order)

    // Dispatch a phase change — completely unrelated to messages
    dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: 'Synthesis' })

    textSub.unsubscribe()
    orderSub.unsubscribe()

    // Neither message text nor message_order should have changed
    expect(textSub.getCount()).toBe(0)
    expect(orderSub.getCount()).toBe(0)
  })
})
