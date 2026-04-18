// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original skeleton — wires createBridge() + useSessionStore +
// <StreamingMessage> + <CrashNotice>.
//
// Design:
//   - createBridge() spawns the Python backend (or KOSMOS_BACKEND_CMD override).
//   - The frame consumer loop dispatches every inbound IPCFrame to the session
//     store via dispatchSessionAction().
//   - SIGTERM / Ctrl-C triggers bridge.close() with ≤3 s SIGTERM → SIGKILL
//     (FR-009).
//   - This component is the root App; it is rendered by tui/src/main.tsx.

// TODO(T050): wire commands dispatcher — slash-prefixed input intercepted
//             before user_input frame emission (Phase 4, Team B).
// TODO(T087): wire PrimitiveDispatcher — tool_result envelopes routed to
//             primitive renderers (Phase 5, Team C).

import React, { useEffect, useRef } from 'react'
import { Box, Text, useApp, useInput } from 'ink'
import { ThemeProvider, useTheme } from '../theme/provider'
import { useSessionStore, dispatchSessionAction, sessionStore } from '../store/session-store'
import type { SessionAction } from '../store/session-store'
import { MessageList } from '../components/conversation/MessageList'
import { CrashNotice } from '../components/CrashNotice'
import { createBridge } from '../ipc/bridge'
import type { IPCBridge } from '../ipc/bridge'
import type { IPCFrame } from '../ipc/frames.generated'
import { useI18n } from '../i18n'

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
  const inputRef = useRef('')

  // Wire Ctrl-C to bridge.close() + Ink exit
  useInput((_input, key) => {
    if (key.ctrl && _input === 'c') {
      bridge.close().then(() => exit())
    }
  })

  // Show ready hint if no messages yet
  const isEmpty = messageOrder.length === 0 && !crash

  return (
    <Box flexDirection="column" paddingX={1}>
      {/* Conversation history */}
      <MessageList />

      {/* Crash notice (renders when store.crash is set) */}
      <CrashNotice />

      {/* Ready hint — shown before first message */}
      {isEmpty && (
        <Box>
          <Text color={theme.inactive} dimColor>
            {i18n.sessionReady}
          </Text>
        </Box>
      )}

      {/* TODO(T050): wire commands dispatcher — input box goes here */}
      {/* TODO(T087): wire PrimitiveDispatcher — permission gauntlet goes here */}
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

  return (
    <ThemeProvider>
      <AppInner bridge={bridge} />
    </ThemeProvider>
  )
}
