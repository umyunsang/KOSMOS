// SPDX-License-Identifier: Apache-2.0
// KOSMOS UFO mascot — CC Clawd 교체 (2026-04-24 확정 · 보라 팔레트)
//
// 기법은 CC Clawd.tsx L34-182 그대로:
//   · row 1 center + row 2 body를 backgroundColor로 채워 덩어리 실루엣 형성
//   · quadrant 블록들이 bg 위에 '구멍' 형태로 돔 창문 · 접시 커브 · 라이트 표현
//
// 외형:
//   row 1: 돔(dome) — 5-col bg-fill, 양쪽 4-space pad
//   row 2: 접시(saucer) — 9-col bg-fill + 양쪽 커브 ▗▟ / ▙▖
//   row 3: 착륙 라이트 ▘ ▘ ▘ ▘  (pose='arms-up' 시 빔 모드 ▼)
//
// ClawdPose 인터페이스는 호환성 유지 — look-left/right 는 돔 창문 이동,
// arms-up 은 빔 모드(beam-on)로 의미 매핑.
//
// 팔레트: 보라 (violet) · theme token 없이 하드코딩 — 추후 token 추가 고려.
//
// Source of visual truth:
//   .references/claude-code-sourcemap/restored-src/src/components/LogoV2/Clawd.tsx
//   + docs/wireframes/ufo-mascot-proposal.mjs

import * as React from 'react'
import { Box, Text } from '../../ink.js'

export type ClawdPose =
  | 'default'
  | 'arms-up'   // UFO: beam-on 모드로 의미 매핑
  | 'look-left' // UFO: scan-left (돔 창문 좌상향)
  | 'look-right' // UFO: scan-right (돔 창문 우상향)

type Props = {
  pose?: ClawdPose
}

// ── 보라 팔레트 (사용자 확정) ───────────────────────────────────────────
const UFO_BODY = '#a78bfa'       // 보라 본체 (quadrant fg)
const UFO_BACKGROUND = '#4c1d95' // 보라 배경 (bg-fill 채움)

// ── POSES ────────────────────────────────────────────────────────────
// 각 pose는 3 row:
//   dome  (r1): [pad L (fg) + dome mid (bg-fill) + pad R (fg)]
//   saucer(r2): [left curve (fg) + saucer mid (bg-fill) + right curve (fg)]
//   lights(r3): [fg-only 착륙 라이트 또는 빔]

type Segments = {
  /** row 1: dome left padding (fg) */
  domeL: string
  /** row 1: dome middle with eye-windows (bg-filled) */
  domeMid: string
  /** row 1: dome right padding (fg) */
  domeR: string
  /** row 2: saucer left curve (fg) */
  saucerL: string
  /** row 2: saucer body (bg-filled) */
  saucerMid: string
  /** row 2: saucer right curve (fg) */
  saucerR: string
  /** row 3: landing lights or beam (fg only) */
  lights: string
}

const POSES: Record<ClawdPose, Segments> = {
  default: {
    domeL: '    ',
    domeMid: '▛███▜',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '   ▘ ▘ ▘ ▘   ',
  },
  'look-left': {
    domeL: '    ',
    domeMid: '▟███▟',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '   ▘ ▘ ▘ ▘   ',
  },
  'look-right': {
    domeL: '    ',
    domeMid: '▙███▙',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '   ▘ ▘ ▘ ▘   ',
  },
  'arms-up': {
    // UFO beam-on 모드: 라이트가 아래로 쏘는 빔으로 전환
    domeL: '    ',
    domeMid: '▛███▜',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '  ▼ ▼ ▼ ▼ ▼  ',
  },
}

// Apple Terminal fallback: bg-fill trick 필요 (CC Clawd.tsx 패턴).
// 돔 창문 pose 별 fg 컷아웃 패턴만 유지.
const APPLE_DOME: Record<ClawdPose, string> = {
  default: ' ▗     ▖ ',
  'look-left': ' ▘     ▘ ',
  'look-right': ' ▝     ▝ ',
  'arms-up': ' ▗     ▖ ',
}

export function Clawd({ pose = 'default' }: Props = {}): React.ReactNode {
  const p = POSES[pose]
  return (
    <Box flexDirection="column">
      <Text>
        <Text color={UFO_BODY}>{p.domeL}</Text>
        <Text color={UFO_BODY} backgroundColor={UFO_BACKGROUND}>{p.domeMid}</Text>
        <Text color={UFO_BODY}>{p.domeR}</Text>
      </Text>
      <Text>
        <Text color={UFO_BODY}>{p.saucerL}</Text>
        <Text color={UFO_BODY} backgroundColor={UFO_BACKGROUND}>{p.saucerMid}</Text>
        <Text color={UFO_BODY}>{p.saucerR}</Text>
      </Text>
      <Text color={UFO_BODY}>{p.lights}</Text>
    </Box>
  )
}

// Apple Terminal 변형은 별도 컴포넌트에서 다룰 수 있으나, CC Clawd.tsx L87-97
// 기동 시점에 `env.terminal === 'Apple_Terminal'` 를 체크해 분기했던 부분은
// 현재 KOSMOS의 `utils/env.ts` 가 최종 wire-in되기 전까지 주석으로만 남김.
// Apple Terminal dome cutout 패턴:
//   default: ' ▗     ▖ '
//   look-left: ' ▘     ▘ '
//   look-right: ' ▝     ▝ '
//   arms-up: ' ▗     ▖ '
export { APPLE_DOME }
