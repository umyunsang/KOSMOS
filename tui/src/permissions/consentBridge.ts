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

import type { IPCBridge } from '../ipc/bridge'
import type { ConsentDecision } from './types'
import type { NotificationPushFrame } from '../ipc/frames.generated'
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
// Raw payload record from NotificationPushFrame (untyped in generated schema)
// ---------------------------------------------------------------------------

/** Record representation of the notification_push payload field. */
type RawPayload = Record<string, unknown>

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

/**
 * Wait for the next consent prompt request frame from the backend
 * that matches `correlationId`, then return the payload and a resolve callback.
 *
 * The frame is a `notification_push` with `adapter_id = CONSENT_REQUEST_KIND`.
 *
 * The caller renders ConsentPrompt with the payload and calls
 * `result.resolve(granted, scope)` when the citizen decides.
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
export async function awaitConsentRequest(
  opts: ConsentBridgeOptions,
): Promise<ConsentBridgeResult> {
  const { bridge, sessionId, correlationId, timeoutMs = 120_000 } = opts

  return new Promise<ConsentBridgeResult>((resolve, reject) => {
    let settled = false
    const timeoutId = setTimeout(() => {
      if (!settled) {
        settled = true
        reject(new Error(`Consent request timed out after ${timeoutMs}ms (correlation_id=${correlationId})`))
      }
    }, timeoutMs)

    // Start listening for frames
    ;(async () => {
      try {
        for await (const frame of bridge.frames()) {
          if (settled) break

          // Only handle notification_push frames
          if (frame.kind !== 'notification_push') continue

          const notifFrame = frame as NotificationPushFrame
          // Match on sub-protocol kind (adapter_id) + correlation_id
          if (
            notifFrame.adapter_id !== CONSENT_REQUEST_KIND ||
            notifFrame.correlation_id !== correlationId
          ) {
            continue
          }

          // Cast payload to our expected shape — backend must conform
          const rawPayload = notifFrame.payload as unknown as RawPayload
          const payload = rawPayload as unknown as ConsentRequestPayload

          settled = true
          clearTimeout(timeoutId)

          resolve({
            payload,
            resolve: (granted: boolean, scope: ConsentDecision['scope']) => {
              _sendDecision(bridge, sessionId, correlationId, payload, granted, scope)
            },
          })
          break
        }
      } catch (err) {
        if (!settled) {
          settled = true
          clearTimeout(timeoutId)
          reject(err)
        }
      }
    })()
  })
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
  const frame: NotificationPushFrame = {
    ...base,
    role: 'tui',
    kind: 'notification_push',
    adapter_id: CONSENT_DECISION_KIND,
    subscription_id: '',
    event_guid: '',
    payload_content_type: 'application/json',
    payload: decisionPayload as unknown as NotificationPushFrame['payload'],
  }

  bridge.send(frame)
}
