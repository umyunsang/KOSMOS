// SPDX-License-Identifier: Apache-2.0
// UMMAYA terminal mascot animation.
//
// Keeps the CC AnimatedClawd frame contract while animating the UMMAYA
// house-shaped mascot.

import * as React from 'react'
import { useEffect, useRef, useState } from 'react'
import { Box } from '../../ink.js'
import { Clawd, type ClawdPose } from './Clawd.js'

type Frame = {
  pose: ClawdPose
  /** marginTop offset in fixed-height container (0 = normal, 1 = low) */
  offset: number
}

function hold(pose: ClawdPose, offset: number, frames: number): Frame[] {
  return Array.from({ length: frames }, () => ({ pose, offset }))
}

// 6-frame cycle at 150ms per frame.
const HOVER_BOB: readonly Frame[] = [
  ...hold('default', 0, 2),
  ...hold('default', 1, 2),
  ...hold('default', 0, 2),
]

const SCAN_SWEEP: readonly Frame[] = [
  ...hold('look-left', 0, 5),
  ...hold('look-right', 0, 5),
  ...hold('default', 0, 1),
]

const JUMP_WAVE: readonly Frame[] = [
  ...hold('default', 0, 2),
  ...hold('arms-up', 0, 3),
  ...hold('default', 0, 1),
  ...hold('default', 0, 2),
  ...hold('arms-up', 0, 3),
  ...hold('default', 0, 1),
]

const CLICK_ANIMATIONS: readonly (readonly Frame[])[] = [SCAN_SWEEP, JUMP_WAVE]

const IDLE_DEFAULT: Frame = { pose: 'default', offset: 0 }
const CLICK_FRAME_MS = 60
const HOVER_FRAME_MS = 150
const HOVER_CYCLE_LENGTH = HOVER_BOB.length
const incrementFrame = (i: number) => i + 1
const MASCOT_HEIGHT = 5

/**
 * UMMAYA mascot with a fixed-height house footprint. Click animations either
 * shift the CC-style eyes left/right or raise the roof arms.
 */
export function AnimatedClawd(): React.ReactNode {
  const { pose, bounceOffset, onClick } = useClawdAnimation()
  return (
    <Box height={MASCOT_HEIGHT} flexDirection="column" onClick={onClick}>
      <Box marginTop={bounceOffset} flexShrink={0}>
        <Clawd pose={pose} />
      </Box>
    </Box>
  )
}

function useClawdAnimation(): {
  pose: ClawdPose
  bounceOffset: number
  onClick: () => void
} {
  // Read UMMAYA_REDUCED_MOTION env once at mount. Real settings wiring can
  // replace this after the main settings loader lands.
  const [reducedMotion] = useState(
    () => process.env.UMMAYA_REDUCED_MOTION === '1',
  )

  // Click animation state (-1 = not active, else frame index)
  const [clickFrame, setClickFrame] = useState(-1)
  const clickSeqRef = useRef<readonly Frame[]>(SCAN_SWEEP)

  // Hover bob state (always running unless reducedMotion)
  const [hoverFrame, setHoverFrame] = useState(0)

  const onClick = (): void => {
    if (reducedMotion || clickFrame !== -1) return
    clickSeqRef.current =
      CLICK_ANIMATIONS[Math.floor(Math.random() * CLICK_ANIMATIONS.length)]!
    setClickFrame(0)
  }

  // Click animation timer
  useEffect(() => {
    if (clickFrame === -1) return
    if (clickFrame >= clickSeqRef.current.length) {
      setClickFrame(-1)
      return
    }
    const timer = setTimeout(setClickFrame, CLICK_FRAME_MS, incrementFrame)
    return () => clearTimeout(timer)
  }, [clickFrame])

  // Hover timer runs continuously when no click animation is active.
  useEffect(() => {
    if (reducedMotion) return
    if (clickFrame !== -1) return
    const timer = setTimeout(
      () => setHoverFrame((f) => (f + 1) % HOVER_CYCLE_LENGTH),
      HOVER_FRAME_MS,
    )
    return () => clearTimeout(timer)
  }, [hoverFrame, clickFrame, reducedMotion])

  // Click animation takes precedence over hover.
  let current: Frame
  if (clickFrame >= 0 && clickFrame < clickSeqRef.current.length) {
    current = clickSeqRef.current[clickFrame]!
  } else if (!reducedMotion) {
    current = HOVER_BOB[hoverFrame]!
  } else {
    current = IDLE_DEFAULT
  }

  return {
    pose: current.pose,
    bounceOffset: current.offset,
    onClick,
  }
}
