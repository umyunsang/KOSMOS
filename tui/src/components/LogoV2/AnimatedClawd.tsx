// SPDX-License-Identifier: Apache-2.0
// KOSMOS UFO AnimatedClawd — hover-bob idle + click-triggered scan/beam
//
// CC AnimatedClawd.tsx의 Frame 시퀀스 재활용:
//   · JUMP_WAVE → BEAM_PULSE (클릭시 빔 깜빡이며 펄스)
//   · LOOK_AROUND → SCAN_SWEEP (클릭시 돔 창문 좌우 스캔)
//   · idle offset=0 고정 → HOVER_BOB (미세 상하 움직임, 항상 작동)
//
// 레이아웃 고정: CLAWD_HEIGHT=3 유지 (Clawd.tsx footprint 동일).
// reducedMotion 플래그 시 HOVER_BOB 및 클릭 애니메이션 전부 정지.
//
// Source of visual truth:
//   .references/claude-code-sourcemap/restored-src/src/components/LogoV2/AnimatedClawd.tsx
//   + docs/wireframes/ufo-mascot-proposal.mjs

import * as React from 'react'
import { useEffect, useRef, useState } from 'react'
import { Box } from '../../ink.js'
import { Clawd, type ClawdPose } from './Clawd.js'

type Frame = {
  pose: ClawdPose
  /** marginTop offset in fixed-height-3 container (0 = normal, 1 = low) */
  offset: number
}

function hold(pose: ClawdPose, offset: number, frames: number): Frame[] {
  return Array.from({ length: frames }, () => ({ pose, offset }))
}

// ── Idle animation: HOVER_BOB ───────────────────────────────────────────
// UFO가 공중에 떠 있을 때 미세하게 위아래로 흔들리는 느낌.
// 6-frame cycle at 150ms per frame (~0.9s per loop).
const HOVER_BOB: readonly Frame[] = [
  ...hold('default', 0, 2),  // 위
  ...hold('default', 1, 2),  // 아래 (margin-top으로 미세 하강)
  ...hold('default', 0, 2),  // 위
]

// ── Click animation: SCAN_SWEEP ──────────────────────────────────────────
// 돔 창문이 좌 → 우 → 기본으로 스캔 (CC LOOK_AROUND 재이용).
const SCAN_SWEEP: readonly Frame[] = [
  ...hold('look-left', 0, 5),
  ...hold('look-right', 0, 5),
  ...hold('default', 0, 1),
]

// ── Click animation: BEAM_PULSE ─────────────────────────────────────────
// 빔을 두 번 켰다 끔 (CC JUMP_WAVE 크라우치/스프링 구조 재이용).
// arms-up 은 Clawd.tsx에서 beam-on 모드로 매핑됨.
const BEAM_PULSE: readonly Frame[] = [
  ...hold('default', 0, 2),   // 빔 꺼짐
  ...hold('arms-up', 0, 3),   // 빔 켜짐!
  ...hold('default', 0, 1),
  ...hold('default', 0, 2),   // 다시 꺼짐
  ...hold('arms-up', 0, 3),   // 빔 켜짐!
  ...hold('default', 0, 1),
]

const CLICK_ANIMATIONS: readonly (readonly Frame[])[] = [SCAN_SWEEP, BEAM_PULSE]

const IDLE_DEFAULT: Frame = { pose: 'default', offset: 0 }
const CLICK_FRAME_MS = 60
const HOVER_FRAME_MS = 150  // 느린 hover bob
const HOVER_CYCLE_LENGTH = HOVER_BOB.length
const incrementFrame = (i: number) => i + 1
const UFO_HEIGHT = 3

/**
 * KOSMOS UFO mascot with idle hover-bob animation + click-triggered
 * scan/beam sequences. Container height is fixed at UFO_HEIGHT so the
 * surrounding layout never shifts. Respects `prefersReducedMotion` from
 * user settings — if set, all animation is disabled and a static UFO
 * renders (behavior identical to bare `<Clawd />`).
 *
 * Click triggers one of:
 *   · SCAN_SWEEP — dome window sweeps left → right → default
 *   · BEAM_PULSE — beam row turns on (▼) twice
 */
export function AnimatedClawd(): React.ReactNode {
  const { pose, bounceOffset, onClick } = useClawdAnimation()
  return (
    <Box height={UFO_HEIGHT} flexDirection="column" onClick={onClick}>
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
  // Read KOSMOS_REDUCED_MOTION env once at mount. Real settings wiring can
  // replace this after the main settings loader lands.
  const [reducedMotion] = useState(
    () => process.env.KOSMOS_REDUCED_MOTION === '1',
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

  // Hover bob timer (runs continuously when no click animation active)
  useEffect(() => {
    if (reducedMotion) return
    if (clickFrame !== -1) return  // Pause hover during click animation
    const timer = setTimeout(
      () => setHoverFrame((f) => (f + 1) % HOVER_CYCLE_LENGTH),
      HOVER_FRAME_MS,
    )
    return () => clearTimeout(timer)
  }, [hoverFrame, clickFrame, reducedMotion])

  // Decide active frame: click animation takes precedence over hover bob
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
