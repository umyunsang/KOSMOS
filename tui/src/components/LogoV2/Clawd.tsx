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

type Segments = {
  roof: string
  faceL: string
  eyes: string
  faceR: string
  wallL: string
  wall: string
  wallR: string
  baseL: string
  door: string
  baseR: string
  feet: string
}

const POSES: Record<ClawdPose, Segments> = {
  default: {
    roof: '   ▟▀▀▀▙   ',
    faceL: '  ▟',
    eyes: '▛███▜',
    faceR: '▙  ',
    wallL: ' ▟',
    wall: '███████',
    wallR: '▙ ',
    baseL: '▝▜',
    door: '██▟█▙██',
    baseR: '▛▘',
    feet: '   ▘▘ ▝▝   ',
  },
  'look-left': {
    roof: '   ▟▀▀▀▙   ',
    faceL: '  ▟',
    eyes: '▟███▟',
    faceR: '▙  ',
    wallL: ' ▟',
    wall: '███████',
    wallR: '▙ ',
    baseL: '▝▜',
    door: '██▟█▙██',
    baseR: '▛▘',
    feet: '   ▘▘ ▝▝   ',
  },
  'look-right': {
    roof: '   ▟▀▀▀▙   ',
    faceL: '  ▟',
    eyes: '▙███▙',
    faceR: '▙  ',
    wallL: ' ▟',
    wall: '███████',
    wallR: '▙ ',
    baseL: '▝▜',
    door: '██▟█▙██',
    baseR: '▛▘',
    feet: '   ▘▘ ▝▝   ',
  },
  'arms-up': {
    roof: '  ▗▟▀▀▀▙▖  ',
    faceL: '  ▟',
    eyes: '▛███▜',
    faceR: '▙  ',
    wallL: ' ▜',
    wall: '███████',
    wallR: '▛ ',
    baseL: ' ▜',
    door: '██▟█▙██',
    baseR: '▛ ',
    feet: '   ▘▘ ▝▝   ',
  },
}

const APPLE_DOME: Record<ClawdPose, string> = {
  default: '  U  ',
  'look-left': 'U    ',
  'look-right': '    U',
  'arms-up': '  U  ',
}

export function Clawd({ pose = 'default' }: Props = {}): React.ReactNode {
  const p = POSES[pose]
  return (
    <Box flexDirection="column">
      <Text color="clawd_body">{p.roof}</Text>
      <Text>
        <Text color="clawd_body">{p.faceL}</Text>
        <Text color="clawd_body" backgroundColor="clawd_background">{p.eyes}</Text>
        <Text color="clawd_body">{p.faceR}</Text>
      </Text>
      <Text>
        <Text color="clawd_body">{p.wallL}</Text>
        <Text color="clawd_body" backgroundColor="clawd_background">{p.wall}</Text>
        <Text color="clawd_body">{p.wallR}</Text>
      </Text>
      <Text>
        <Text color="clawd_body">{p.baseL}</Text>
        <Text color="clawd_body" backgroundColor="clawd_background">{p.door}</Text>
        <Text color="clawd_body">{p.baseR}</Text>
      </Text>
      <Text color="clawd_body">{p.feet}</Text>
    </Box>
  )
}

export { APPLE_DOME }
