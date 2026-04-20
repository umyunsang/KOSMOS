// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original skeleton — wires createBridge() + useSessionStore +
// <StreamingMessage> + <CrashNotice> + commands dispatcher (T050) +
// PrimitiveDispatcher (T087 is hooked one level deeper in MessageList).
//
// Design:
//   - createBridge() spawns the Python backend (or KOSMOS_BACKEND_CMD override).
//   - The frame consumer loop dispatches every inbound IPCFrame to the session
//     store via dispatchSessionAction().
//   - SIGTERM / Ctrl-C triggers bridge.close() with ≤3 s SIGTERM → SIGKILL
//     (FR-009).
//   - This component is the root App; it is rendered by tui/src/main.tsx under
//     <ThemeProvider> (T052).
//
// Input handling:
//   - A minimal ASCII input buffer lives here; proper Korean IME is Phase 7 US5.
//   - On Enter: slash-prefixed input is intercepted by dispatchCommand(); all
//     other input is emitted as a user_input IPC frame (T050, FR-038, FR-042).

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Box, Text, useApp, useInput } from 'ink'
import { useTheme } from '../theme/provider'
import { useSessionStore, dispatchSessionAction } from '../store/session-store'
import { MessageList } from '../components/conversation/MessageList'
import { CrashNotice } from '../components/CrashNotice'
import { createBridge } from '../ipc/bridge'
import type { IPCBridge } from '../ipc/bridge'
import type {
  IPCFrame,
  UserInputFrame,
  SessionEventFrame,
  PermissionResponseFrame,
} from '../ipc/frames.generated'
import { useI18n } from '../i18n'
import {
  buildDefaultRegistry,
  dispatchCommand,
  isSlashCommand,
  listCommands,
} from '../commands'
import type { DispatchResult } from '../commands'
import type { CommandDefinition } from '../commands/types'
import { HelpView } from '../commands/help'
import { PhaseIndicator } from '../components/coordinator/PhaseIndicator'
import { WorkerStatusRow } from '../components/coordinator/WorkerStatusRow'
import { PermissionGauntletModal } from '../components/coordinator/PermissionGauntletModal'
import { InputBar } from '../components/input/InputBar'
import { handleNotificationFrame } from '../permissions/consentBridge'
import {
  Onboarding,
  resolveStartStep,
  CURRENT_CONSENT_VERSION,
  CURRENT_SCOPE_VERSION,
} from '../components/onboarding/Onboarding'
import { latestConsentRecord, latestScopeRecord } from '../memdir/io'

// ---------------------------------------------------------------------------
// Frame dispatcher — maps IPCFrame arms to SessionAction
// ---------------------------------------------------------------------------

function dispatchFrame(frame: IPCFrame): void {
  switch (frame.kind) {
    case 'user_input':
      // Inbound user_input from backend echo — store as message
      dispatchSessionAction({
        type: 'USER_INPUT',
        message_id: `user-${frame.ts}`,
        text: frame.text,
      })
      break

    case 'assistant_chunk':
      dispatchSessionAction({
        type: 'ASSISTANT_CHUNK',
        message_id: frame.message_id,
        delta: frame.delta,
        done: frame.done,
      })
      break

    case 'tool_call':
      dispatchSessionAction({
        type: 'TOOL_CALL',
        message_id: `msg-${frame.call_id}`,
        tool_call: {
          call_id: frame.call_id,
          name: frame.name,
          arguments: frame.arguments as Record<string, unknown>,
        },
      })
      break

    case 'tool_result':
      dispatchSessionAction({
        type: 'TOOL_RESULT',
        call_id: frame.call_id,
        envelope: frame.envelope as Record<string, unknown>,
      })
      break

    case 'coordinator_phase':
      dispatchSessionAction({
        type: 'COORDINATOR_PHASE',
        phase: frame.phase,
      })
      break

    case 'worker_status':
      dispatchSessionAction({
        type: 'WORKER_STATUS',
        status: {
          worker_id: frame.worker_id,
          role_id: frame.role_id,
          current_primitive: frame.current_primitive,
          status: frame.status,
        },
      })
      break

    case 'permission_request':
      dispatchSessionAction({
        type: 'PERMISSION_REQUEST',
        request: {
          request_id: frame.request_id,
          correlation_id: frame.correlation_id,
          worker_id: frame.worker_id,
          primitive_kind: frame.primitive_kind,
          description_ko: frame.description_ko,
          description_en: frame.description_en,
          risk_level: frame.risk_level,
        },
      })
      break

    case 'permission_response':
      dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
      break

    case 'session_event':
      dispatchSessionAction({
        type: 'SESSION_EVENT',
        event: frame.event,
        payload: frame.payload as Record<string, unknown>,
      })
      break

    case 'error':
      dispatchSessionAction({
        type: 'ERROR',
        code: frame.code,
        message: frame.message,
        details: frame.details as Record<string, unknown>,
      })
      break
  }
}

// ---------------------------------------------------------------------------
// Help / acknowledgement state — populated by the dispatcher
// ---------------------------------------------------------------------------

interface HelpState {
  commands: CommandDefinition[]
  errorBanner?: string
}

// ---------------------------------------------------------------------------
// WorkerStatusList — selector-isolated on workers Map keys (FR-050/FR-051).
// Only re-renders when the set of worker IDs changes, not on per-row updates.
// ---------------------------------------------------------------------------

function WorkerStatusList(): React.ReactElement | null {
  // Subscribe to the workers Map by identity — the reducer replaces the Map
  // reference whenever its contents change, so this is ref-stable between
  // dispatches. Deriving the sorted ID list inside the selector would rebuild
  // a new array on every getSnapshot call and trip React 19's Object.is cache
  // check ("getSnapshot should be cached to avoid an infinite loop").
  const workers = useSessionStore((s) => s.workers)
  const workerIds = useMemo(
    () => Array.from(workers.keys()).sort(),
    [workers],
  )
  if (workerIds.length === 0) return null
  return (
    <Box flexDirection="column" marginBottom={1}>
      {workerIds.map((id) => (
        <WorkerStatusRow key={id} workerId={id} />
      ))}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// App inner — consumes theme/i18n hooks (must be inside ThemeProvider)
// ---------------------------------------------------------------------------

interface AppInnerProps {
  bridge: IPCBridge
}

function AppInner({ bridge }: AppInnerProps): React.ReactElement {
  const theme = useTheme()
  const i18n = useI18n()
  const { exit } = useApp()
  const crash = useSessionStore((s) => s.crash)
  const messageOrder = useSessionStore((s) => s.message_order)
  const pendingPermission = useSessionStore((s) => s.pending_permission)

  const registry = useMemo(() => buildDefaultRegistry(), [])
  const [ack, setAck] = useState<string>('')
  const [helpState, setHelpState] = useState<HelpState | null>(null)

  // IPC senders closed over the bridge — safe for the dispatcher's SendFrame
  // callback (typed to SessionEventFrame) and for free-text user_input frames.
  const sessionId = useSessionStore((s) => s.session_id)

  const sendSessionEvent = (frame: SessionEventFrame): void => {
    // Bridge-level fill-in: populate session_id when the command builder left
    // it as "". The dispatcher never has access to the store directly.
    const stamped: SessionEventFrame = frame.session_id === ''
      ? { ...frame, session_id: sessionId }
      : frame
    bridge.send(stamped)
  }

  const sendUserInput = (text: string): void => {
    const frame: UserInputFrame = {
      kind: 'user_input',
      session_id: sessionId,
      correlation_id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      role: 'tui',
      text,
    }
    bridge.send(frame)
  }

  // DI callback for PermissionGauntletModal — keeps the modal bridge-free.
  const sendPermissionResponse = (frame: PermissionResponseFrame): void => {
    bridge.send(frame)
  }

  // InputBar delegates key handling to useKoreanIME (Phase 7 US5). We keep a
  // thin outer useInput here only for Ctrl-C (tear down) and Escape (clear
  // help overlay) — text composition lives entirely inside InputBar.
  const handleSubmit = (raw: string): void => {
    if (raw.trim().length === 0) return

    if (isSlashCommand(raw)) {
      void dispatchCommand(raw, registry, sendSessionEvent).then((result: DispatchResult) => {
        setAck(result.acknowledgement)
        if (result.renderHelp === true) {
          setHelpState({
            commands: listCommands(registry),
            errorBanner: result.acknowledgement === '' ? undefined : result.acknowledgement,
          })
        } else {
          setHelpState(null)
        }
      })
      return
    }

    setHelpState(null)
    setAck('')
    sendUserInput(raw)
  }

  // Outer key handler — Ctrl-C always closes the bridge. Escape clears the
  // help overlay when no modal is active. Everything else passes through to
  // InputBar's useKoreanIME (or to PermissionGauntletModal when it is open).
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      bridge.close().then(() => exit())
      return
    }
    if (pendingPermission !== null) return
    if (key.escape) {
      setHelpState(null)
    }
  })

  // Show ready hint if nothing has happened yet
  const isEmpty = messageOrder.length === 0 && !crash && helpState === null && ack === ''
  const inputDisabled = pendingPermission !== null

  return (
    <Box flexDirection="column" paddingX={1}>
      {/* Coordinator phase indicator (US4 scenario 1, FR-043) */}
      <PhaseIndicator />

      {/* Per-worker status rows (US4 scenario 2, FR-044) */}
      <WorkerStatusList />

      {/* Conversation history */}
      <MessageList />

      {/* Crash notice (renders when store.crash is set) */}
      <CrashNotice />

      {/* Permission gauntlet modal (US4 scenario 3, FR-045/FR-046).
          Renders only when pending_permission is set; swallows y/n input. */}
      <PermissionGauntletModal
        sendFrame={sendPermissionResponse}
        sessionId={sessionId}
      />

      {/* Ready hint — shown before any interaction */}
      {isEmpty && (
        <Box>
          <Text color={theme.inactive} dimColor>
            {i18n.sessionReady}
          </Text>
        </Box>
      )}

      {/* Help view — slash-command listing or unknown-command error */}
      {helpState !== null && (
        <HelpView commands={helpState.commands} errorBanner={helpState.errorBanner} />
      )}

      {/* Transient acknowledgement notice from a command handler */}
      {helpState === null && ack !== '' && (
        <Box marginY={1}>
          <Text color={theme.subtle}>{ack}</Text>
        </Box>
      )}

      {/* Korean IME input bar (US5, FR-015/FR-016) — delegates to
          useKoreanIME hook; suppressed while the permission modal is open. */}
      <InputBar onSubmit={handleSubmit} disabled={inputDisabled} />
    </Box>
  )
}

// ---------------------------------------------------------------------------
// App — sets up bridge frame consumer, then renders AppInner
// ---------------------------------------------------------------------------

interface AppProps {
  bridge: IPCBridge
}

export function App({ bridge }: AppProps): React.ReactElement {
  const { exit } = useApp()

  useEffect(() => {
    // Consume frames from the bridge and dispatch to store
    let active = true
    ;(async () => {
      for await (const frame of bridge.frames()) {
        if (!active) break
        // Consent sub-protocol rides notification_push frames; if a waiter
        // claims one, skip store dispatch to avoid double-handling.
        if (handleNotificationFrame(frame)) continue
        dispatchFrame(frame)
        // Exit event from backend
        if (frame.kind === 'session_event' && frame.event === 'exit') {
          bridge.close().then(() => exit())
          break
        }
      }
    })()

    return () => {
      active = false
    }
  }, [bridge, exit])

  // Epic H #1302: gate the main UI behind the citizen onboarding flow.
  // On first launch (or after a consent/scope version bump) render the
  // three-step Onboarding before AppInner.  Returning citizens with fresh
  // memdir records skip the flow in ≤ 3 s via the splash fast-path
  // (SC-012).  The memdir snapshot is read synchronously at boot only —
  // subsequent state lives in `onComplete`.
  const initialMemdir = useMemo(() => {
    const consent = latestConsentRecord()
    const scope = latestScopeRecord()
    return {
      consentRecord: consent !== null ? { consent_version: consent.consent_version } : undefined,
      scopeRecord: scope !== null ? { scope_version: scope.scope_version } : undefined,
    }
  }, [])
  // Stable per-launch session id — the same value is stamped on every
  // consent + ministry-scope record written during this session so the
  // two records cross-reference (contracts/onboarding-step-registry.md § 4).
  // UUIDv4 is used until Spec 032 surfaces a UUIDv7 helper; the Zod
  // schemas accept any RFC 4122 UUID shape.
  const sessionIdRef = useRef<string | null>(null)
  if (sessionIdRef.current === null) {
    sessionIdRef.current = crypto.randomUUID()
  }
  const consentFresh =
    initialMemdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION
  const scopeFresh =
    initialMemdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION
  const [onboardingDone, setOnboardingDone] = useState<boolean>(
    consentFresh && scopeFresh,
  )

  if (!onboardingDone) {
    return (
      <Onboarding
        memdir={initialMemdir}
        startStep={resolveStartStep(initialMemdir)}
        sessionId={sessionIdRef.current}
        onComplete={() => setOnboardingDone(true)}
      />
    )
  }
  return <AppInner bridge={bridge} />
}
