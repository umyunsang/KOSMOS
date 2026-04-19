// SPDX-License-Identifier: Apache-2.0
// T112 regression tests — SESSION_EVENT load handler in session-store reducer.
// FR-052: replayed messages must be written with done:true (no streaming animation).
// FR-010: invalid entries are silently skipped via console.warn, no throw.

import { describe, it, expect, beforeEach } from 'bun:test'
import {
  dispatchSessionAction,
  getSessionSnapshot,
  sessionStore,
} from '../../src/store/session-store'
import type { SessionState } from '../../src/store/session-store'

// ---------------------------------------------------------------------------
// Helper: reset store between tests
// ---------------------------------------------------------------------------

function resetStore(): void {
  dispatchSessionAction({ type: 'SESSION_EVENT', event: 'new', payload: {} })
}

describe('SESSION_EVENT load — reducer (T112)', () => {
  beforeEach(() => {
    resetStore()
  })

  it('populates Map and message_order for a valid single message', () => {
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        messages: [
          {
            id: 'm1',
            role: 'user',
            chunks: ['hi'],
            done: true,
            tool_calls: [],
            tool_results: [],
          },
        ],
      },
    })
    const snap: SessionState = getSessionSnapshot()
    expect(snap.message_order).toEqual(['m1'])
    const msg = snap.messages.get('m1')
    expect(msg).toBeDefined()
    expect(msg!.role).toBe('user')
    expect(msg!.chunks).toEqual(['hi'])
    expect(msg!.done).toBe(true) // FR-052: must be true
  })

  it('sets session_id from payload when provided', () => {
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        session_id: 'ses-abc',
        messages: [],
      },
    })
    expect(getSessionSnapshot().session_id).toBe('ses-abc')
  })

  it('preserves existing session_id when payload.session_id absent', () => {
    // Set a known session_id first
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'new',
      payload: {},
    })
    const priorId = getSessionSnapshot().session_id
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        messages: [],
      },
    })
    // After load with no session_id, id should remain whatever it was
    expect(getSessionSnapshot().session_id).toBe(priorId)
  })

  it('replays multiple messages preserving order', () => {
    const msgs = [
      { id: 'a', role: 'user', chunks: ['hello'], done: true, tool_calls: [], tool_results: [] },
      { id: 'b', role: 'assistant', chunks: ['world'], done: true, tool_calls: [], tool_results: [] },
      { id: 'c', role: 'user', chunks: ['again'], done: true, tool_calls: [], tool_results: [] },
    ]
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: { messages: msgs },
    })
    const snap = getSessionSnapshot()
    expect(snap.message_order).toEqual(['a', 'b', 'c'])
    expect(snap.messages.size).toBe(3)
  })

  it('FR-052: forces done:true even if payload says false', () => {
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        messages: [
          {
            id: 'streaming',
            role: 'assistant',
            chunks: ['partial'],
            done: false, // should be overridden
            tool_calls: [],
            tool_results: [],
          },
        ],
      },
    })
    const msg = getSessionSnapshot().messages.get('streaming')
    expect(msg!.done).toBe(true)
  })

  it('FR-010: skips entries missing required id field — does not throw', () => {
    // Should not throw; valid entries are preserved, bad ones skipped
    expect(() => {
      dispatchSessionAction({
        type: 'SESSION_EVENT',
        event: 'load',
        payload: {
          messages: [
            { role: 'user', chunks: ['no-id'], done: true, tool_calls: [], tool_results: [] }, // missing id
            { id: 'ok', role: 'user', chunks: ['has-id'], done: true, tool_calls: [], tool_results: [] },
          ],
        },
      })
    }).not.toThrow()
    const snap = getSessionSnapshot()
    expect(snap.message_order).toEqual(['ok'])
  })

  it('FR-010: returns current state when messages is not an array', () => {
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        messages: null as unknown as [],
      },
    })
    // Store should be unchanged (no throw, state intact)
    const snap = getSessionSnapshot()
    expect(snap).toBeDefined()
  })

  it('leaves state intact for save event', () => {
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        messages: [{ id: 'x', role: 'user', chunks: ['x'], done: true, tool_calls: [], tool_results: [] }],
      },
    })
    const before = getSessionSnapshot()
    dispatchSessionAction({ type: 'SESSION_EVENT', event: 'save', payload: {} })
    const after = getSessionSnapshot()
    // State reference is same (store's Object.is optimization)
    expect(after.message_order).toEqual(before.message_order)
  })
})
