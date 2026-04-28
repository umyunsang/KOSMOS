// Source: .references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionPrompt.tsx (Claude Code 2.1.88, research-use)
// Spec 2077 — KOSMOS coordinator-scoped permission gauntlet wired to sessionStore.
// Spec 1979 — KOSMOS y/n direct-keystroke pattern replaced with CC arrow+Enter pattern.
//
// Renders when `pending_permission` is set in sessionStore.  Subscribes only
// to that field; emits a PermissionResponseFrame via the injected sendFrame
// prop (FR-046).  Uses CC's arrow+Enter selection pattern so the entire TUI
// shares one permission UX vocabulary.
//
// Implementation note (per Spec 1979): we drive Up/Down/Enter via raw
// `useInput` instead of the `<Select>` component, because `<Select>` routes
// keystrokes through `useKeybindings` which ink-testing-library's stdin
// emulator cannot drive in unit tests.  The interaction model is identical
// to CC's Select from the citizen's perspective.

import React, { useMemo, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import { useI18n } from '../../i18n'
import { useSessionStore, dispatchSessionAction } from '../../store/session-store'
import type { PermissionResponseFrame } from '../../ipc/frames.generated'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface PermissionGauntletModalProps {
  /** DI: never imports bridge directly. Caller provides sendFrame. */
  sendFrame: (frame: PermissionResponseFrame) => void
  /** Session ID needed to build the response frame header. */
  sessionId: string
}

// ---------------------------------------------------------------------------
// Risk level helpers (KOSMOS-original; uses theme tokens, not hex)
// ---------------------------------------------------------------------------

type RiskLevel = 'low' | 'medium' | 'high'

function riskColor(level: RiskLevel, theme: ReturnType<typeof useTheme>): string {
  switch (level) {
    case 'high':
      return theme.error
    case 'medium':
      return theme.warning
    case 'low':
    default:
      return theme.success
  }
}

// ---------------------------------------------------------------------------
// PermissionGauntletModal
// ---------------------------------------------------------------------------

type ChoiceValue = 'granted' | 'denied'

/**
 * Modal-style permission dialog (CC arrow+Enter pattern).
 *
 * Renders when pending_permission is set in the session store.
 * Two-choice [granted / denied] arrow+Enter selection.  Esc cancels → denied.
 * Emits a PermissionResponseFrame via the injected sendFrame prop (FR-046).
 *
 * Component is selector-isolated: subscribes only to pending_permission.
 */
export function PermissionGauntletModal({
  sendFrame,
  sessionId,
}: PermissionGauntletModalProps): React.ReactElement | null {
  const theme = useTheme()
  const i18n = useI18n()
  const pendingRequest = useSessionStore((s) => s.pending_permission)
  const [focusedIdx, setFocusedIdx] = useState(0)

  const choices: { label: string; value: ChoiceValue }[] = useMemo(
    () => [
      { label: i18n.permissionApproved, value: 'granted' },
      { label: i18n.permissionDenied, value: 'denied' },
    ],
    [i18n],
  )

  const decide = (decision: ChoiceValue): void => {
    if (pendingRequest == null) return
    dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
    sendFrame({
      session_id: sessionId,
      correlation_id: pendingRequest.correlation_id,
      ts: new Date().toISOString(),
      role: 'tui',
      kind: 'permission_response',
      request_id: pendingRequest.request_id,
      decision,
    })
  }

  // CC arrow+Enter pattern (replaces previous y/n direct-keystroke pattern).
  // Esc → denied (Select.onCancel-equivalent semantics).
  useInput((_input, key) => {
    if (pendingRequest == null) return
    if (key.escape) {
      decide('denied')
      return
    }
    if (key.upArrow) {
      setFocusedIdx((i) => (i - 1 + choices.length) % choices.length)
      return
    }
    if (key.downArrow) {
      setFocusedIdx((i) => (i + 1) % choices.length)
      return
    }
    if (key.return) {
      const choice = choices[focusedIdx]
      if (choice) decide(choice.value)
    }
    // All other keystrokes are swallowed (modal blocks input).
  })

  // When no pending request, render nothing (modal closed).
  if (pendingRequest == null) return null

  const riskBorderColor = riskColor(pendingRequest.risk_level, theme)

  return (
    <Box
      borderStyle="round"
      borderColor={riskBorderColor}
      flexDirection="column"
      paddingX={2}
      paddingY={1}
      marginY={1}
    >
      {/* Title row */}
      <Box marginBottom={1}>
        <Text bold color={theme.permission}>
          {i18n.permissionPromptTitle}
        </Text>
        <Text color={theme.subtle}>{' — '}</Text>
        <Text color={riskBorderColor}>{pendingRequest.risk_level.toUpperCase()}</Text>
      </Box>

      {/* Bilingual description */}
      <Box flexDirection="column" marginBottom={1}>
        <Text color={theme.text}>{pendingRequest.description_ko}</Text>
        <Text color={theme.subtle}>{pendingRequest.description_en}</Text>
      </Box>

      {/* Primitive + worker context */}
      <Box marginBottom={1}>
        <Text color={theme.inactive}>primitive: </Text>
        <Text color={theme.text}>{pendingRequest.primitive_kind}</Text>
        <Text color={theme.inactive}>{'  worker: '}</Text>
        <Text color={theme.text}>{pendingRequest.worker_id}</Text>
      </Box>

      {/* Question */}
      <Box marginBottom={1}>
        <Text color={theme.permission}>
          {i18n.permissionPromptBody(pendingRequest.primitive_kind)}
        </Text>
      </Box>

      {/* Arrow+Enter choice list (CC pattern; replaces y/n keystrokes) */}
      <Box flexDirection="column">
        {choices.map((c, i) => {
          const focused = i === focusedIdx
          return (
            <Box key={c.value}>
              <Text color={focused ? theme.permission : undefined} bold={focused}>
                {focused ? '› ' : '  '}
                {c.label}
              </Text>
            </Box>
          )
        })}
      </Box>

      {/* Hint footer */}
      <Box marginTop={1}>
        <Text color={theme.subtle}>{'↑↓ 선택 · Enter 확정 · Esc 거부'}</Text>
      </Box>
    </Box>
  )
}
