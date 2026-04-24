// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original: Replaces CC services/api streaming with KOSMOS stdio IPC

/**
 * useReplBridge — encapsulates all IPC I/O for the TUI.
 *
 * Extracted from tui/src/entrypoints/tui.tsx (App + AppInner senders) so that
 * the parent component tree stays bridge-free and Lead can integrate freely.
 *
 * Shape is kept compatible with the CC useReplBridge return surface
 * (sendUserInput / sendSessionEvent / sendPermissionResponse).
 */

import { useCallback, useEffect, useRef } from 'react'
import type { IPCBridge } from '../ipc/bridge'
import type {
  IPCFrame,
  UserInputFrame,
  SessionEventFrame,
  PermissionResponseFrame,
} from '../ipc/frames.generated'
import { useSessionStore, dispatchSessionAction } from '../store/session-store'
import { handleNotificationFrame } from '../permissions/consentBridge'

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface ReplBridgeOptions {
  /** Called for every frame before store dispatch (recv) or after send (send). */
  onFrame?: (frame: IPCFrame, direction: 'recv' | 'send') => void
  /** Called when the backend emits session_event(event="exit"). */
  onExit?: () => void
}

export interface ReplBridgeHandle {
  sendUserInput(text: string): void
  sendSessionEvent(frame: SessionEventFrame): void
  sendPermissionResponse(frame: PermissionResponseFrame): void
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useReplBridge(
  bridge: IPCBridge,
  options?: ReplBridgeOptions,
): ReplBridgeHandle {
  const sessionId = useSessionStore((s) => s.session_id)

  // Keep mutable refs so callbacks are always fresh without re-memoising.
  const sessionIdRef = useRef(sessionId)
  useEffect(() => { sessionIdRef.current = sessionId }, [sessionId])
  const optsRef = useRef(options)
  useEffect(() => { optsRef.current = options }, [options])

  // -------------------------------------------------------------------------
  // Outbound senders
  // -------------------------------------------------------------------------

  const sendSessionEvent = useCallback((frame: SessionEventFrame): void => {
    const stamped: SessionEventFrame =
      frame.session_id === ''
        ? { ...frame, session_id: sessionIdRef.current }
        : frame
    optsRef.current?.onFrame?.(stamped, 'send')
    bridge.send(stamped)
  }, [bridge])

  const sendUserInput = useCallback((text: string): void => {
    const frame: UserInputFrame = {
      kind: 'user_input',
      session_id: sessionIdRef.current,
      correlation_id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      role: 'tui',
      text,
      // TODO: stamp version/frame_seq/transaction_id via codec helper once
      // tui/src/ipc/codec.ts exposes a stampOutbound() utility.
      version: '1.0',
      frame_seq: 0,
      transaction_id: null,
    }
    optsRef.current?.onFrame?.(frame, 'send')
    bridge.send(frame)
  }, [bridge])

  const sendPermissionResponse = useCallback(
    (frame: PermissionResponseFrame): void => {
      optsRef.current?.onFrame?.(frame, 'send')
      bridge.send(frame)
    },
    [bridge],
  )

  // -------------------------------------------------------------------------
  // Inbound frame consumer (mirrors App useEffect — tui.tsx L419-440)
  // -------------------------------------------------------------------------

  useEffect(() => {
    let active = true
    ;(async () => {
      for await (const frame of bridge.frames()) {
        if (!active) break
        optsRef.current?.onFrame?.(frame, 'recv')
        // Consent sub-protocol: claimed notification_push frames must not reach
        // the store (double-handle guard, mirrors tui.tsx L427).
        if (handleNotificationFrame(frame)) continue
        _dispatchFrame(frame)
        if (frame.kind === 'session_event' && frame.event === 'exit') {
          optsRef.current?.onExit?.()
          break
        }
      }
    })()
    return () => { active = false }
  }, [bridge])

  return { sendUserInput, sendSessionEvent, sendPermissionResponse }
}

// ---------------------------------------------------------------------------
// Private frame dispatcher (mirrors tui.tsx L75-169, kept co-located so
// Lead can delete tui.tsx's copy when integrating this hook).
// ---------------------------------------------------------------------------

function _dispatchFrame(frame: IPCFrame): void {
  switch (frame.kind) {
    case 'user_input':
      dispatchSessionAction({ type: 'USER_INPUT', message_id: `user-${frame.ts}`, text: frame.text })
      break
    case 'assistant_chunk':
      dispatchSessionAction({ type: 'ASSISTANT_CHUNK', message_id: frame.message_id, delta: frame.delta, done: frame.done })
      break
    case 'tool_call':
      dispatchSessionAction({ type: 'TOOL_CALL', message_id: `msg-${frame.call_id}`, tool_call: { call_id: frame.call_id, name: frame.name, arguments: frame.arguments as Record<string, unknown> } })
      break
    case 'tool_result':
      dispatchSessionAction({ type: 'TOOL_RESULT', call_id: frame.call_id, envelope: frame.envelope as Record<string, unknown> })
      break
    case 'coordinator_phase':
      dispatchSessionAction({ type: 'COORDINATOR_PHASE', phase: frame.phase })
      break
    case 'worker_status':
      dispatchSessionAction({ type: 'WORKER_STATUS', status: { worker_id: frame.worker_id, role_id: frame.role_id, current_primitive: frame.current_primitive, status: frame.status } })
      break
    case 'permission_request':
      dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: { request_id: frame.request_id, correlation_id: frame.correlation_id, worker_id: frame.worker_id, primitive_kind: frame.primitive_kind, description_ko: frame.description_ko, description_en: frame.description_en, risk_level: frame.risk_level } })
      break
    case 'permission_response':
      dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
      break
    case 'session_event':
      dispatchSessionAction({ type: 'SESSION_EVENT', event: frame.event, payload: frame.payload as Record<string, unknown> })
      break
    case 'error':
      dispatchSessionAction({ type: 'ERROR', code: frame.code, message: frame.message, details: frame.details as Record<string, unknown> })
      break
    case 'notification_push':
      // Unclaimed notification_push frames (not consumed by handleNotificationFrame) are a no-op.
      break
  }
}
