// SPDX-License-Identifier: Apache-2.0
// UMMAYA home-call mascot.
//
// Keeps the CC Clawd pose contract: the eyes move left/right and the arms
// lift on the jump frame. The silhouette is a small house character because
// UMMAYA means "call the familiar place first" for public administration.

import * as React from 'react'
import { Box, Text } from '../../ink.js'

export type ClawdPose =
  | 'default'
  | 'arms-up'
  | 'look-left'
  | 'look-right'

type Props = {
  pose?: ClawdPose
}

type MascotFrame = readonly [string, string, string, string, string]

const POSES: Record<ClawdPose, MascotFrame> = {
  default: [
    '   ▗▟▀▙▖   ',
    '  ▟▛▗ ▖▜▙  ',
    ' ▟▛ ▘ ▝ ▜▙ ',
    '▝▜▙ ▟█▙ ▟▛▘',
    '   ▘▘ ▝▝   ',
  ],
  'look-left': [
    '   ▗▟▀▙▖   ',
    '  ▟▛▗  ▜▙  ',
    ' ▟▛▘  ▝ ▜▙ ',
    '▝▜▙ ▟█▙ ▟▛▘',
    '   ▘▘ ▝▝   ',
  ],
  'look-right': [
    '   ▗▟▀▙▖   ',
    '  ▟▛  ▖▜▙  ',
    ' ▟▛ ▘  ▝▜▙ ',
    '▝▜▙ ▟█▙ ▟▛▘',
    '   ▘▘ ▝▝   ',
  ],
  'arms-up': [
    '   ▗▟▀▙▖   ',
    ' ▗▟▛▗ ▖▜▙▖ ',
    ' ▜▛ ▘ ▝ ▜▛ ',
    '  ▜▙▟█▙▟▛  ',
    '   ▘▘ ▝▝   ',
  ],
}

const APPLE_DOME: Record<ClawdPose, string> = {
  default: '  U  ',
  'look-left': 'U    ',
  'look-right': '    U',
  'arms-up': '  U  ',
}

export function Clawd({ pose = 'default' }: Props = {}): React.ReactNode {
  const lines = POSES[pose]
  return (
    <Box flexDirection="column">
      {lines.map((line, index) => (
        <Text key={index} color="clawd_body">
          {line}
        </Text>
      ))}
    </Box>
  )
}

export { APPLE_DOME }
