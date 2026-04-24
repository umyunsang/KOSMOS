// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P4 · TranslateTool UI renderers.

import React from 'react'
import { Box, Text } from '../../ink.js'
import type { ProgressMessage } from '../../types/message.js'
import type { Output } from './TranslateTool.js'

/** Rendered while the tool call is in flight (spinner phase). */
export function renderToolUseMessage(): React.ReactNode {
  return <Text dimColor>Translating…</Text>
}

/** Rendered once the tool returns its result. */
export function renderToolResultMessage(
  output: Output,
  _progressMessages: ProgressMessage[],
  _options?: { isTranscriptMode?: boolean },
): React.ReactNode {
  if (!output.text) return null
  return (
    <Box flexDirection="column" marginTop={1}>
      <Text>{output.text}</Text>
    </Box>
  )
}
