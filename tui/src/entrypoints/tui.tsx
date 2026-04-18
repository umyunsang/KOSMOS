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

import React, { useEffect, useMemo, useState } from 'react'
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
  const workerIds = useSessionStore((s) =>
    Array.from(s.workers.keys()).sort(),
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
  const [inputBuffer, setInputBuffer] = useState('')
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
      ts: new Date().toISOString(),
      text,
    }
    bridge.send(frame)
  }

  // DI callback for PermissionGauntletModal — keeps the modal bridge-free.
  const sendPermissionResponse = (frame: PermissionResponseFrame): void => {
    bridge.send(frame)
  }

  const submitInput = (): void => {
    const raw = inputBuffer
    setInputBuffer('')
    if (raw.trim().length === 0) return

    if (isSlashCommand(raw)) {
      // Fire-and-forget — the dispatcher resolves, never throws
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

    // Non-slash path: emit user_input IPC frame and clear any pending help
    setHelpState(null)
    setAck('')
    sendUserInput(raw)
  }

  // Keyboard handling — Ctrl-C closes bridge; otherwise build the input buffer.
  // When the permission modal is open it owns all keystrokes (FR-046): we
  // short-circuit here so y/n/Escape reach PermissionGauntletModal exclusively.
  useInput((input, key) => {
    if (pendingPermission !== null) {
      // Still allow Ctrl-C to tear down the bridge even while the modal is open.
      if (key.ctrl && input === 'c') {
        bridge.close().then(() => exit())
      }
      return
    }

    if (key.ctrl && input === 'c') {
      bridge.close().then(() => exit())
      return
    }

    if (key.return) {
      submitInput()
      return
    }

    if (key.backspace || key.delete) {
      setInputBuffer((prev) => prev.slice(0, -1))
      return
    }

    if (key.escape) {
      setInputBuffer('')
      setHelpState(null)
      return
    }

    // Ignore other control keys (arrows, tab, etc.). Proper Korean IME arrives
    // in Phase 7 US5 via the @jrichman/ink-text-input fork.
    if (input !== undefined && input.length > 0 && !key.ctrl && !key.meta) {
      setInputBuffer((prev) => prev + input)
    }
  })

  // Show ready hint if nothing has happened yet
  const isEmpty = messageOrder.length === 0 && !crash && helpState === null && ack === ''

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

      {/* Input line — minimal placeholder until Phase 7 US5 Korean IME. */}
      <Box>
        <Text bold color={theme.briefLabelYou}>{'> '}</Text>
        <Text color={theme.text}>{inputBuffer}</Text>
        <Text color={theme.inactive}>▋</Text>
      </Box>
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

  return <AppInner bridge={bridge} />
}
