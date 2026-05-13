// SPDX-License-Identifier: Apache-2.0
// UMMAYA open-mouth cat mascot.
//
// This keeps a compact block mark and emphasizes small cat ears, a rounded
// face, and an open mouth.

import * as React from 'react'
import { Box, Text } from '../../ink.js'

export type UmmaPose =
  | 'default'
  | 'arms-up'
  | 'look-left'
  | 'look-right'

type Props = {
  pose?: UmmaPose
}

type MascotSegment = {
  text: string
  color?: string
  backgroundColor?: string
}

type MascotLine = readonly MascotSegment[]
type MascotFrame = readonly [MascotLine, MascotLine, MascotLine, MascotLine, MascotLine]

const body = (text: string): MascotSegment => ({ text, color: 'umma_body' })
const mouth = (text: string): MascotSegment => ({
  text,
  color: 'error',
  backgroundColor: 'umma_background',
})

const POSES: Record<UmmaPose, MascotFrame> = {
  default: [
    [body('     ▗▖ ▗▖')],
    [body('    ▟▛▛▀▜▜▙')],
    [body('    ██▘ ▝██')],
    [body('   ▐█▘ '), mouth('▄'), body(' ▝█▌')],
    [body('   ▝▜▙'), mouth('███'), body('▟▛▘')],
  ],
  'look-left': [
    [body('     ▗▖ ▗▖')],
    [body('    ▟▛▛▀▜▜▙')],
    [body('    ██▘▘ ██')],
    [body('   ▐█▘ '), mouth('▄'), body(' ▝█▌')],
    [body('   ▝▜▙'), mouth('███'), body('▟▛▘')],
  ],
  'look-right': [
    [body('     ▗▖ ▗▖')],
    [body('    ▟▛▛▀▜▜▙')],
    [body('    ██ ▝▝██')],
    [body('   ▐█▘ '), mouth('▄'), body(' ▝█▌')],
    [body('   ▝▜▙'), mouth('███'), body('▟▛▘')],
  ],
  'arms-up': [
    [body('    ▗▖   ▗▖')],
    [body('    ▟▛▛▀▜▜▙')],
    [body('    ██▘ ▝██')],
    [body('   ▐█▘ '), mouth('▄'), body(' ▝█▌')],
    [body('   ▝▜▙'), mouth('███'), body('▟▛▘')],
  ],
}

export function Umma({ pose = 'default' }: Props = {}): React.ReactNode {
  const lines = POSES[pose]
  return (
    <Box flexDirection="column">
      {lines.map((line, lineIndex) => (
        <Text key={lineIndex}>
          {line.map((segment, segmentIndex) => (
            <Text
              key={segmentIndex}
              color={segment.color}
              backgroundColor={segment.backgroundColor}
            >
              {segment.text}
            </Text>
          ))}
        </Text>
      ))}
    </Box>
  )
}
