// SPDX-License-Identifier: Apache-2.0
// Spec 033 T019 — Consent round-trip over Spec 032 IPC envelope.
//
// Flow:
//   Backend sends a `notification_push` frame carrying a consent request payload.
//   The payload is keyed by `adapter_id` = CONSENT_REQUEST_KIND and contains
//   the PIPA 4-tuple for the ConsentPrompt to render.
//   TUI sends a `notification_push` frame back with `adapter_id` = CONSENT_DECISION_KIND.
//
// The Spec 032 IPC envelope is consumed here via the IPCBridge.send() API.
// This module does NOT modify IPC core (hard constraint).
//
// The consent sub-protocol rides the existing NotificationPushFrame.
// `adapter_id` is repurposed as a sub-message discriminator (convention only —
// not a change to the wire schema). See blocker note at bottom of file.
//
// `correlation_id` from ToolPermissionContext is threaded through so the
// backend can join the decision to the tool call audit record.
//
// IMPORTANT — single-consumer contract:
//   There is exactly one `bridge.frames()` consumer in the TUI (`tui.tsx`'s
//   master dispatch loop).  This module MUST NOT iterate `bridge.frames()`
//   directly — doing so steals frames from the dispatcher and breaks IPC
//   ordering.  Instead it exposes `handleNotificationFrame()` so the master
//   loop can forward consent-related frames here.

import type { IPCBridge } from '../ipc/bridge'
import type { ConsentDecision } from './types'
import type { IPCFrame, NotificationPushFrame } from '../ipc/frames.generated'
import { makeBaseEnvelope } from '../ipc/envelope'

// ---------------------------------------------------------------------------
// IPC message kinds (consent sub-protocol — riding adapter_id field)
// ---------------------------------------------------------------------------

/**
 * adapter_id value the backend sets to flag a consent prompt request.
 * Convention: sub-protocol message kind embedded in the adapter_id slot.
 */
export const CONSENT_REQUEST_KIND = 'consent.prompt.request' as const

/**
 * adapter_id value the TUI sets to flag a consent decision response.
 */
export const CONSENT_DECISION_KIND = 'consent.prompt.decision' as const

// ---------------------------------------------------------------------------
// Incoming consent request payload shape
// ---------------------------------------------------------------------------

/**
 * Payload inside a `notification_push` frame where adapter_id = CONSENT_REQUEST_KIND.
 * Backend populates this from PIPAConsentPrompt.build() output.
 */
export interface ConsentRequestPayload {
  tool_id: string
  purpose: string
  data_items: string[]
  retention_period: string
  refusal_right: string
  pipa_class: ConsentDecision['pipa_class']
  auth_level: ConsentDecision['auth_level']
  /** Scope the citizen is asked to grant. */
  requested_scope: ConsentDecision['scope']
  /** Unique receipt ID for this consent exchange (Kantara CR §5.1). */
  consent_receipt_id: string
  /** ISO 8601 UTC — when this request expires if unanswered. */
  expires_at: string | null
}

// ---------------------------------------------------------------------------
// Outgoing consent decision payload shape
// ---------------------------------------------------------------------------

export interface ConsentDecisionPayload {
  tool_id: string
  consent_receipt_id: string
  granted: boolean
  scope: ConsentDecision['scope']
  decided_at: string
  /** Echo of the correlation_id from the matching request frame. */
  correlation_id: string
}

// ---------------------------------------------------------------------------
// ConsentBridge: awaits a single consent request and submits the decision
// ---------------------------------------------------------------------------

export interface ConsentBridgeOptions {
  bridge: IPCBridge
  sessionId: string
  /** Correlation ID from ToolPermissionContext — threads through the audit trail. */
  correlationId: string
  /**
   * Timeout in ms before the consent decision is auto-refused (default: 120000).
   * Prevents the TUI from hanging indefinitely if the user leaves.
   */
  timeoutMs?: number
}

export interface ConsentBridgeResult {
  payload: ConsentRequestPayload
  /** Respond with the citizen's decision */
  resolve: (granted: boolean, scope: ConsentDecision['scope']) => void
}

// Internal resolver state: one entry per outstanding awaitConsentRequest call.
interface PendingWaiter {
  bridge: IPCBridge
  sessionId: string
  timeoutId: ReturnType<typeof setTimeout>
  resolve: (result: ConsentBridgeResult) => void
  reject: (err: Error) => void
}

const _pending = new Map<string, PendingWaiter>()

/**
 * Wait for the next consent prompt request frame from the backend
 * that matches `correlationId`, then return the payload and a resolve callback.
 *
 * The frame is a `notification_push` with `adapter_id = CONSENT_REQUEST_KIND`.
 *
 * The caller renders ConsentPrompt with the payload and calls
 * `result.resolve(granted, scope)` when the citizen decides.
 *
 * The master IPC dispatch loop (tui.tsx) is expected to call
 * `handleNotificationFrame(frame)` for every notification_push frame so this
 * function can deliver the matching payload back to the awaiting caller.
 *
 * BLOCKER NOTE: The current NotificationPushFrame schema (auto-generated from
 * frame_schema.py Spec 031) does not carry a consent-specific field —
 * the sub-protocol rides `adapter_id`.  The Lead integration step should
 * add a dedicated `consent_request` / `consent_response` frame kind to
 * frame_schema.py once the Python backend consent prompt handler is wired.
 * At that point this module should be updated to match the new frame kind.
 *
 * @throws Error if timeout is reached before a matching request arrives.
 */
export function awaitConsentRequest(
  opts: ConsentBridgeOptions,
): Promise<ConsentBridgeResult> {
  const { bridge, sessionId, correlationId, timeoutMs = 120_000 } = opts

  return new Promise<ConsentBridgeResult>((resolve, reject) => {
    if (_pending.has(correlationId)) {
      reject(
        new Error(
          `Duplicate awaitConsentRequest for correlation_id=${correlationId}`,
        ),
      )
      return
    }

    const timeoutId = setTimeout(() => {
      const waiter = _pending.get(correlationId)
      if (waiter) {
        _pending.delete(correlationId)
        waiter.reject(
          new Error(
            `Consent request timed out after ${timeoutMs}ms (correlation_id=${correlationId})`,
          ),
        )
      }
    }, timeoutMs)

    _pending.set(correlationId, {
      bridge,
      sessionId,
      timeoutId,
      resolve,
      reject,
    })
  })
}

/**
 * Forwarded from the TUI master frame loop for every incoming frame.
 *
 * Returns `true` if the frame was claimed by the consent sub-protocol (and
 * therefore must not be dispatched to the main store), `false` otherwise.
 * Non-notification_push frames are ignored without claim.
 */
export function handleNotificationFrame(frame: IPCFrame): boolean {
  if (frame.kind !== 'notification_push') return false
  const notifFrame = frame as NotificationPushFrame
  if (notifFrame.adapter_id !== CONSENT_REQUEST_KIND) return false

  const waiter = _pending.get(notifFrame.correlation_id)
  if (!waiter) return false

  // NotificationPushFrame.payload is a JSON-encoded string per frame_schema.py.
  // Parse defensively — an unparseable payload is a backend contract violation
  // and should fail the waiter loudly instead of silently returning undefined
  // fields.
  let payload: ConsentRequestPayload
  try {
    const rawPayload = notifFrame.payload as unknown
    const jsonText =
      typeof rawPayload === 'string' ? rawPayload : JSON.stringify(rawPayload)
    payload = JSON.parse(jsonText) as ConsentRequestPayload
  } catch (err) {
    _pending.delete(notifFrame.correlation_id)
    clearTimeout(waiter.timeoutId)
    waiter.reject(
      err instanceof Error
        ? err
        : new Error('Failed to parse consent request payload'),
    )
    return true
  }

  _pending.delete(notifFrame.correlation_id)
  clearTimeout(waiter.timeoutId)

  waiter.resolve({
    payload,
    resolve: (granted: boolean, scope: ConsentDecision['scope']) => {
      _sendDecision(
        waiter.bridge,
        waiter.sessionId,
        notifFrame.correlation_id,
        payload,
        granted,
        scope,
      )
    },
  })
  return true
}

// ---------------------------------------------------------------------------
// Internal: send consent decision frame back to backend
// ---------------------------------------------------------------------------

function _sendDecision(
  bridge: IPCBridge,
  sessionId: string,
  correlationId: string,
  payload: ConsentRequestPayload,
  granted: boolean,
  scope: ConsentDecision['scope'],
): void {
  const decisionPayload: ConsentDecisionPayload = {
    tool_id: payload.tool_id,
    consent_receipt_id: payload.consent_receipt_id,
    granted,
    scope,
    decided_at: new Date().toISOString(),
    correlation_id: correlationId,
  }

  const base = makeBaseEnvelope({ sessionId, correlationId })

  // Ride NotificationPushFrame with adapter_id = CONSENT_DECISION_KIND.
  // event_guid and subscription_id are stub values — the backend filters on adapter_id.
  // payload must be a JSON-encoded string per the IPC schema (frame_schema.py).
  const frame: NotificationPushFrame = {
    ...base,
    role: 'tui',
    kind: 'notification_push',
    adapter_id: CONSENT_DECISION_KIND,
    subscription_id: '',
    event_guid: '',
    payload_content_type: 'application/json',
    payload: JSON.stringify(decisionPayload),
  }

  bridge.send(frame)
}
