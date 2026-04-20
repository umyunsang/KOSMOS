// SPDX-License-Identifier: Apache-2.0
// Spec 288 Codex P1 regression — `computeIsAgentLoopActive` +
// `computeCurrentToolCallId` derive liveness from the full `messages` map
// rather than the last entry of `message_order`.
//
// The bug these tests lock down: the reducer's `TOOL_CALL` branch adds a new
// assistant message to the `messages` Map but does NOT append its id to
// `message_order` (see session-store.ts around the `TOOL_CALL` case).  A probe
// that only reads `message_order` therefore returns `false` for a tool call
// that arrives BEFORE any `ASSISTANT_CHUNK` — causing `session-exit` to skip
// its FR-015 active-loop confirmation and `agent-interrupt` (ctrl+c) to arm
// exit instead of cancelling the active loop.
//
// Test cases (per Codex review follow-up on PR #1591):
//   1. TOOL_CALL with no matching TOOL_RESULT yet — probe returns true.
//   2. ASSISTANT_CHUNK with done:false — probe returns true.
//   3. ASSISTANT_CHUNK done:true + matching TOOL_RESULT — probe returns false.
//   4. TOOL_CALL arrives before any ASSISTANT_CHUNK — probe returns true
//      (the canonical Codex bug case — message is in `messages` but missing
//      from `message_order`).

import { beforeEach, describe, expect, it } from 'bun:test'
import {
  computeCurrentToolCallId,
  computeIsAgentLoopActive,
  dispatchSessionAction,
  getSessionSnapshot,
} from '../../src/store/session-store'
import type { Message } from '../../src/store/session-store'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetStore(): void {
  dispatchSessionAction({ type: 'SESSION_EVENT', event: 'new', payload: {} })
}

function snapshotMessages(): ReadonlyMap<string, Message> {
  return getSessionSnapshot().messages
}

describe('computeIsAgentLoopActive — derived probe (Spec 288 Codex P1)', () => {
  beforeEach(() => {
    resetStore()
  })

  // -------------------------------------------------------------------------
  // Case 1 — a TOOL_CALL with no matching TOOL_RESULT means the loop is alive
  // even when the assistant chunk has already marked itself done.
  // -------------------------------------------------------------------------
  it('returns true when a TOOL_CALL has no matching TOOL_RESULT yet', () => {
    // Stream an assistant chunk first so the message is in both `messages`
    // and `message_order` with `done:true`, then attach a tool call.  Without
    // the derived probe a legacy last-entry check would see `done:true` and
    // report idle; this test proves the derived probe still sees the pending
    // tool call.
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: 'assist-1',
      delta: 'calling a tool',
      done: true,
    })
    dispatchSessionAction({
      type: 'TOOL_CALL',
      message_id: 'assist-1',
      tool_call: {
        call_id: 'call-a',
        name: 'koroad_accident_hazard_search',
        arguments: { region: 'seoul' },
      },
    })

    const messages = snapshotMessages()
    expect(computeIsAgentLoopActive(messages)).toBe(true)
    expect(computeCurrentToolCallId(messages)).toBe('call-a')
  })

  // -------------------------------------------------------------------------
  // Case 2 — an in-flight assistant chunk (done:false) is loop-active.
  // -------------------------------------------------------------------------
  it('returns true when an ASSISTANT_CHUNK is streaming (done:false)', () => {
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: 'assist-2',
      delta: 'streaming...',
      done: false,
    })

    const messages = snapshotMessages()
    expect(computeIsAgentLoopActive(messages)).toBe(true)
    // No tool call was registered; the in-flight-tool-call probe stays null.
    expect(computeCurrentToolCallId(messages)).toBeNull()
  })

  // -------------------------------------------------------------------------
  // Case 3 — assistant done AND tool result returned means the loop is idle.
  // -------------------------------------------------------------------------
  it('returns false once ASSISTANT_CHUNK done:true and TOOL_RESULT has arrived', () => {
    dispatchSessionAction({
      type: 'USER_INPUT',
      message_id: 'user-1',
      text: 'hello',
    })
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: 'assist-3',
      delta: 'response',
      done: true,
    })
    dispatchSessionAction({
      type: 'TOOL_CALL',
      message_id: 'assist-3',
      tool_call: {
        call_id: 'call-b',
        name: 'kma_forecast_fetch',
        arguments: {},
      },
    })
    dispatchSessionAction({
      type: 'TOOL_RESULT',
      call_id: 'call-b',
      envelope: { ok: true },
    })

    const messages = snapshotMessages()
    expect(computeIsAgentLoopActive(messages)).toBe(false)
    expect(computeCurrentToolCallId(messages)).toBeNull()
  })

  // -------------------------------------------------------------------------
  // Case 4 — CANONICAL CODEX BUG CASE.
  //
  // Tool call arrives BEFORE any assistant chunk — the reducer creates a
  // synthetic assistant message in `messages` but the TOOL_CALL branch does
  // not touch `message_order`.  The legacy last-entry probe reads user-1 (the
  // last entry of `message_order`), sees `role:'user', done:true`, and wrongly
  // reports the loop idle.  The derived probe scans the full `messages` map
  // so the TOOL_CALL-only synthetic message participates.
  // -------------------------------------------------------------------------
  it('returns true when a TOOL_CALL arrives before any ASSISTANT_CHUNK (Codex bug case)', () => {
    dispatchSessionAction({
      type: 'USER_INPUT',
      message_id: 'user-2',
      text: 'run a tool please',
    })
    // Backend emits a TOOL_CALL with `msg-${call_id}` message_id per the
    // dispatchFrame mapping in tui.tsx.  No ASSISTANT_CHUNK has arrived yet.
    dispatchSessionAction({
      type: 'TOOL_CALL',
      message_id: 'msg-call-c',
      tool_call: {
        call_id: 'call-c',
        name: 'hira_hospital_search',
        arguments: { specialty: '내과' },
      },
    })

    const snap = getSessionSnapshot()
    // Sanity check on the bug shape itself — the synthetic tool-call message
    // is in `messages` but MISSING from `message_order`.  This is the exact
    // state the legacy probe failed to see.
    expect(snap.messages.has('msg-call-c')).toBe(true)
    expect(snap.message_order).not.toContain('msg-call-c')

    // Derived probe sees the in-flight tool call via the map scan.
    expect(computeIsAgentLoopActive(snap.messages)).toBe(true)
    expect(computeCurrentToolCallId(snap.messages)).toBe('call-c')
  })

  // -------------------------------------------------------------------------
  // Empty-store sanity — brand-new session reports idle.
  // -------------------------------------------------------------------------
  it('returns false on a freshly reset store', () => {
    const messages = snapshotMessages()
    expect(computeIsAgentLoopActive(messages)).toBe(false)
    expect(computeCurrentToolCallId(messages)).toBeNull()
  })

  // -------------------------------------------------------------------------
  // User-only history (no assistant work yet) reports idle.
  // -------------------------------------------------------------------------
  it('returns false when only user messages exist', () => {
    dispatchSessionAction({
      type: 'USER_INPUT',
      message_id: 'user-3',
      text: 'hi',
    })

    const messages = snapshotMessages()
    expect(computeIsAgentLoopActive(messages)).toBe(false)
    expect(computeCurrentToolCallId(messages)).toBeNull()
  })

  // -------------------------------------------------------------------------
  // Multiple tool calls — the most recent pending one wins.
  // -------------------------------------------------------------------------
  it('returns the newest pending call_id when multiple tool calls are in flight', () => {
    dispatchSessionAction({
      type: 'ASSISTANT_CHUNK',
      message_id: 'assist-4',
      delta: 'chaining tools',
      done: true,
    })
    dispatchSessionAction({
      type: 'TOOL_CALL',
      message_id: 'assist-4',
      tool_call: {
        call_id: 'call-x',
        name: 'koroad_accident_hazard_search',
        arguments: {},
      },
    })
    dispatchSessionAction({
      type: 'TOOL_CALL',
      message_id: 'assist-4',
      tool_call: {
        call_id: 'call-y',
        name: 'kma_forecast_fetch',
        arguments: {},
      },
    })

    const messages = snapshotMessages()
    expect(computeIsAgentLoopActive(messages)).toBe(true)
    // call-y was registered last → it is the in-flight id surfaced to
    // `agent-interrupt` for the cancellation envelope.
    expect(computeCurrentToolCallId(messages)).toBe('call-y')

    // Resolving call-y should expose call-x (still pending) as the next
    // in-flight id.
    dispatchSessionAction({
      type: 'TOOL_RESULT',
      call_id: 'call-y',
      envelope: { ok: true },
    })
    const afterY = snapshotMessages()
    expect(computeIsAgentLoopActive(afterY)).toBe(true)
    expect(computeCurrentToolCallId(afterY)).toBe('call-x')

    // Resolving call-x too drops the loop to idle.
    dispatchSessionAction({
      type: 'TOOL_RESULT',
      call_id: 'call-x',
      envelope: { ok: true },
    })
    const afterX = snapshotMessages()
    expect(computeIsAgentLoopActive(afterX)).toBe(false)
    expect(computeCurrentToolCallId(afterX)).toBeNull()
  })
})
