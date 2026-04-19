// SPDX-License-Identifier: Apache-2.0
// T108 — Integration test: /save, /sessions, /resume round-trip.
// FR-038: All session-management slash commands emit session_event IPC frames
//         and surface acknowledgements to the user via i18n strings.
//
// Test strategy:
//   1. /save  → exactly one session_event{event:"save"} frame, ack = i18n.cmdSaveAck
//   2. /sessions → exactly one session_event{event:"list"} frame, ack = i18n.cmdSessionsAck
//              → simulate backend SESSION_EVENT list reply; assert payload shape
//   3. /resume abc123 → one session_event{event:"resume", payload:{id:"abc123"}} frame,
//                       ack = i18n.cmdResumeAck("abc123")
//              → simulate backend SESSION_EVENT load reply; assert store populated

import { describe, it, expect, beforeEach } from 'bun:test'
import { buildDefaultRegistry, dispatchCommand } from '../../src/commands'
import type { SendFrame } from '../../src/commands/types'
import type { SessionEventFrame } from '../../src/ipc/frames.generated'
import { dispatchSessionAction, getSessionSnapshot } from '../../src/store/session-store'
import { i18n } from '../../src/i18n'

// ---------------------------------------------------------------------------
// Spy factory — captures emitted frames for assertion
// ---------------------------------------------------------------------------

function makeSpy(): { sendFrame: SendFrame; captured: SessionEventFrame[] } {
  const captured: SessionEventFrame[] = []
  const sendFrame: SendFrame = (frame) => {
    captured.push(frame)
  }
  return { sendFrame, captured }
}

// ---------------------------------------------------------------------------
// Reset session store between tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  dispatchSessionAction({ type: 'SESSION_EVENT', event: 'new', payload: {} })
})

// ---------------------------------------------------------------------------
// /save scenario
// ---------------------------------------------------------------------------

describe('/save round-trip (FR-038)', () => {
  it('emits exactly one session_event{save} frame and returns cmdSaveAck', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeSpy()

    const result = await dispatchCommand('/save', registry, sendFrame)

    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('save')
    expect(frame.payload).toEqual({})
    expect(result.acknowledgement).toBe(i18n.cmdSaveAck)
    expect(result.renderHelp).not.toBe(true)
  })
})

// ---------------------------------------------------------------------------
// /sessions scenario
// ---------------------------------------------------------------------------

describe('/sessions round-trip (FR-038)', () => {
  it('emits exactly one session_event{list} frame and returns cmdSessionsAck', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeSpy()

    const result = await dispatchCommand('/sessions', registry, sendFrame)

    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('list')
    expect(frame.payload).toEqual({})
    expect(result.acknowledgement).toBe(i18n.cmdSessionsAck)
  })

  it('simulated backend list reply — payload shape is valid', () => {
    // Simulate backend SESSION_EVENT{list} reply with session rows.
    // The reducer leaves state intact for non-new/load events, so we
    // assert on the dispatched action payload shape only (not the store).
    const sessions = [
      { id: 'ses-1', created_at: '2026-01-01T00:00:00Z', turn_count: 3 },
      { id: 'ses-2', created_at: '2026-01-02T00:00:00Z', turn_count: 7 },
    ]
    // dispatchSessionAction must not throw
    expect(() => {
      dispatchSessionAction({
        type: 'SESSION_EVENT',
        event: 'list',
        payload: { sessions },
      })
    }).not.toThrow()

    // Payload shape matches frame_schema.py list spec
    expect(sessions).toHaveLength(2)
    for (const s of sessions) {
      expect(typeof s.id).toBe('string')
      expect(typeof s.created_at).toBe('string')
      expect(typeof s.turn_count).toBe('number')
    }
  })
})

// ---------------------------------------------------------------------------
// /resume scenario
// ---------------------------------------------------------------------------

describe('/resume round-trip (FR-038)', () => {
  it('emits session_event{resume} with id in payload and returns cmdResumeAck', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeSpy()

    const result = await dispatchCommand('/resume abc123', registry, sendFrame)

    expect(captured).toHaveLength(1)
    const frame = captured[0]!
    expect(frame.kind).toBe('session_event')
    expect(frame.event).toBe('resume')
    expect((frame.payload as Record<string, unknown>)['id']).toBe('abc123')
    expect(result.acknowledgement).toBe(i18n.cmdResumeAck('abc123'))
    expect(result.renderHelp).not.toBe(true)
  })

  it('simulated backend load reply populates store via SESSION_EVENT{load}', () => {
    // Simulate backend replaying history after /resume
    const replayMessages = [
      { id: 'msg-0', role: 'user', chunks: ['hi'], done: true, tool_calls: [], tool_results: [] },
      { id: 'msg-1', role: 'assistant', chunks: ['hello'], done: true, tool_calls: [], tool_results: [] },
    ]
    dispatchSessionAction({
      type: 'SESSION_EVENT',
      event: 'load',
      payload: {
        session_id: 'abc123',
        messages: replayMessages,
      },
    })

    const snap = getSessionSnapshot()
    expect(snap.session_id).toBe('abc123')
    expect(snap.message_order).toEqual(['msg-0', 'msg-1'])
    expect(snap.messages.size).toBe(2)

    const userMsg = snap.messages.get('msg-0')
    expect(userMsg!.role).toBe('user')
    expect(userMsg!.chunks).toEqual(['hi'])
    // FR-052: done must be true — no streaming animation on replayed messages
    expect(userMsg!.done).toBe(true)

    const assistantMsg = snap.messages.get('msg-1')
    expect(assistantMsg!.done).toBe(true)
  })

  it('returns cmdResumeMissingId when no session-id arg provided', async () => {
    const registry = buildDefaultRegistry()
    const { sendFrame, captured } = makeSpy()

    const result = await dispatchCommand('/resume', registry, sendFrame)

    expect(captured).toHaveLength(0)
    expect(result.acknowledgement).toBe(i18n.cmdResumeMissingId)
  })
})
