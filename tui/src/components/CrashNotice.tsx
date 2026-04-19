// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original (no upstream analog — Claude Code is not a child process).
//
// CrashNotice component: displays a localized crash message from the i18n
// bundle with the redacted stderr tail and a restart hint (US1 scenario 4,
// FR-004).
//
// All KOSMOS_*_KEY/SECRET/TOKEN/PASSWORD values are already redacted by
// crash-detector.ts before they reach this component; this component renders
// the already-redacted tail verbatim.

import React from 'react'
import { Box, Text } from 'ink'
import { useTheme } from '../theme/provider'
import { useI18n } from '../i18n'
import { useSessionStore } from '../store/session-store'

// ---------------------------------------------------------------------------
// CrashNotice component
// ---------------------------------------------------------------------------

/**
 * Rendered when `session-store.crash` is non-null.
 *
 * Layout:
 *  ┌──────────────────────────────────────────────┐
 *  │ [!] KOSMOS backend crashed                   │
 *  │ Code: backend_crash                          │
 *  │ backend_crash message text                   │
 *  │ ────────────────────────────────────────────  │
 *  │ (stderr tail — redacted)                     │
 *  │ ────────────────────────────────────────────  │
 *  │ Press Ctrl-C to exit or restart with:        │
 *  │   uv run kosmos                              │
 *  └──────────────────────────────────────────────┘
 */
export function CrashNotice(): React.ReactElement | null {
  const theme = useTheme()
  const i18n = useI18n()
  const crash = useSessionStore((s) => s.crash)

  if (!crash) return null

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor={theme.error}
      paddingX={1}
      paddingY={0}
      marginY={1}
    >
      {/* Header */}
      <Box>
        <Text bold color={theme.error}>{'[!] '}</Text>
        <Text bold color={theme.error}>
          {i18n.workerCrashed(crash.code)}
        </Text>
      </Box>

      {/* Error message */}
      <Box paddingLeft={4}>
        <Text color={theme.text} wrap="wrap">
          {crash.message}
        </Text>
      </Box>

      {/* Redacted stderr tail (if any) */}
      {Object.keys(crash.details).length > 0 && (
        <>
          <Box marginTop={1}>
            <Text color={theme.inactive}>{'─'.repeat(40)}</Text>
          </Box>
          <Box paddingLeft={2}>
            <Text color={theme.subtle} wrap="wrap">
              {JSON.stringify(crash.details, null, 2)}
            </Text>
          </Box>
          <Box>
            <Text color={theme.inactive}>{'─'.repeat(40)}</Text>
          </Box>
        </>
      )}

      {/* Restart hint */}
      <Box marginTop={1}>
        <Text color={theme.inactive}>
          {i18n.pressCtrlCToExit}
        </Text>
      </Box>
    </Box>
  )
}
