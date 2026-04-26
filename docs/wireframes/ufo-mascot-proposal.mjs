// SPDX-License-Identifier: Apache-2.0
// KOSMOS UFO 마스코트 · CC Clawd 기법 그대로
//
// CC Clawd.tsx L34-63 POSES 구조를 그대로 따옴:
//   · r1 (row 1): 좁은 돔 — bg-filled cockpit with eye-window cutouts
//   · r2 (row 2): 넓은 접시(saucer) — bg-filled + 양쪽 커브 (Clawd 몸통 확장)
//   · r3 (row 3): 착륙 라이트 (Clawd feet 대응, fg only)
//
// 4-pose (CC 동일 구조):
//   default · scan-left · scan-right · beam-on
//   (look-left/right → scan-*, arms-up → beam-on로 리네이밍)
//
// Run:  cd tui && bun ../docs/wireframes/alien-mascot-proposal.mjs

import { render } from 'ink'
import { h, Box, Text, C, Divider } from './_shared.mjs'

// ══ 팔레트 ═══════════════════════════════════════════════════════════════

const PALETTES = {
  teal:   { body: '#4fd1c5', background: '#134e4a', name: '청록 (kosmosCore)' },
  violet: { body: '#a78bfa', background: '#4c1d95', name: '보라 (우주)' },
  star:   { body: '#fbbf24', background: '#78350f', name: '별빛 (금)' },
  sky:    { body: '#7dd3fc', background: '#0c4a6e', name: '하늘 (UFO)' },
}

// ══ UFO POSES ═══════════════════════════════════════════════════════════
// 전체 width 13. 돔(5 col bg) + 좌우 padding(4 col × 2) = 13
// 접시(9 col bg) + 좌우 커브(2 col × 2) = 13
// 라이트(fg 13 col)

const UFO_POSES = {
  default: {
    // Row 1 dome: 좁은 돔, 두 눈·창문
    domeL:    '    ',       // 4-space left pad (fg)
    domeMid:  '▛███▜',      // 5-char bg-filled · 기본 창문 (Clawd r1E default)
    domeR:    '    ',       // 4-space right pad (fg)
    // Row 2 saucer: 넓은 접시
    saucerL:  '▗▟',         // 좌측 커브 (fg)
    saucerMid: '█████████', // 9-char bg-filled 접시 몸
    saucerR:  '▙▖',         // 우측 커브 (fg)
    // Row 3 landing lights
    lights:   '   ▘ ▘ ▘ ▘   ',  // 4 dots spread
  },
  'scan-left': {
    domeL:    '    ',
    domeMid:  '▟███▟',      // 동공 좌상향 (Clawd look-left)
    domeR:    '    ',
    saucerL:  '▗▟',
    saucerMid: '█████████',
    saucerR:  '▙▖',
    lights:   '   ▘ ▘ ▘ ▘   ',
  },
  'scan-right': {
    domeL:    '    ',
    domeMid:  '▙███▙',      // 동공 우상향 (Clawd look-right)
    domeR:    '    ',
    saucerL:  '▗▟',
    saucerMid: '█████████',
    saucerR:  '▙▖',
    lights:   '   ▘ ▘ ▘ ▘   ',
  },
  'beam-on': {
    domeL:    '    ',
    domeMid:  '▛███▜',
    domeR:    '    ',
    saucerL:  '▗▟',
    saucerMid: '█████████',
    saucerR:  '▙▖',
    // 빔 모드: 라이트가 아래로 연속 점선 (빔 궤적)
    lights:   '  ▼ ▼ ▼ ▼ ▼  ',
  },
}

// ══ UFO 렌더 (Clawd 기법 100% 이식) ══════════════════════════════════════

function UFO({ pose = 'default', palette }) {
  const p = UFO_POSES[pose]
  const { body, background } = palette
  return h(Box, { flexDirection: 'column' },
    // Row 1 · dome
    h(Text, null,
      h(Text, { color: body }, p.domeL),
      h(Text, { color: body, backgroundColor: background }, p.domeMid),
      h(Text, { color: body }, p.domeR),
    ),
    // Row 2 · saucer
    h(Text, null,
      h(Text, { color: body }, p.saucerL),
      h(Text, { color: body, backgroundColor: background }, p.saucerMid),
      h(Text, { color: body }, p.saucerR),
    ),
    // Row 3 · landing lights
    h(Text, { color: body }, p.lights),
  )
}

// ══ Splash ═══════════════════════════════════════════════════════════

function Splash({ pose, palette }) {
  return h(Box, { flexDirection: 'row' },
    h(Box, { flexDirection: 'column', marginRight: 3 },
      h(UFO, { pose, palette }),
    ),
    h(Box, { flexDirection: 'column' },
      h(Text, null,
        h(Text, { bold: true }, 'KOSMOS '),
        h(Text, { color: C.subtle }, 'v0.1-alpha'),
      ),
      h(Text, { color: C.subtle }, 'EXAONE · FriendliAI'),
      h(Text, { color: C.dim, dimColor: true }, '~/KOSMOS/tui'),
    ),
  )
}

function PaletteBlock({ paletteKey }) {
  const palette = PALETTES[paletteKey]
  const poses = ['default', 'scan-left', 'scan-right', 'beam-on']
  return h(Box, { flexDirection: 'column', marginBottom: 2 },
    h(Text, { bold: true, color: C.brand }, palette.name),
    h(Box, { marginTop: 1, marginLeft: 2 },
      h(Splash, { pose: 'default', palette }),
    ),
    h(Box, { marginTop: 1, marginLeft: 2 },
      h(Text, { color: C.dim, dimColor: true }, ' 4 poses: '),
    ),
    h(Box, { marginLeft: 2, flexDirection: 'row' },
      ...poses.map((p, i) => h(Box, {
        key: p, marginRight: i < poses.length - 1 ? 2 : 0,
        flexDirection: 'column',
      },
        h(Text, { color: C.dim, dimColor: true }, p),
        h(UFO, { pose: p, palette }),
      ))
    ),
  )
}

// ══ App ═══════════════════════════════════════════════════════════════

function App() {
  return h(Box, { flexDirection: 'column' },
    h(Text, { bold: true, color: C.brand },
      'KOSMOS UFO 마스코트 · CC Clawd 기법 (bg-fill) 이식'),
    h(Text, { color: C.subtle },
      '3-row 구조: 돔(좁음) → 접시(넓음) → 착륙 라이트 · 4-pose'),

    h(Divider, { label: 'Sky 팔레트 (UFO 대표)' }),
    h(PaletteBlock, { paletteKey: 'sky' }),

    h(Divider, { label: 'Teal 팔레트 (KOSMOS 기본)' }),
    h(PaletteBlock, { paletteKey: 'teal' }),

    h(Divider, { label: 'Violet 팔레트 (우주)' }),
    h(PaletteBlock, { paletteKey: 'violet' }),

    h(Divider, { label: 'Star 팔레트 (금별)' }),
    h(PaletteBlock, { paletteKey: 'star' }),

    h(Divider, { label: '구조 해설' }),
    h(Box, { flexDirection: 'column', marginLeft: 2 },
      h(Text, { color: C.dim },
        'Row 1 dome    — 5-col bg-fill · 돔 창문(quadrant eyes)이 pose 따라 변화'),
      h(Text, { color: C.dim },
        'Row 2 saucer  — 9-col bg-fill + 양쪽 커브 ▗▟ / ▙▖ · 접시 형태'),
      h(Text, { color: C.dim },
        'Row 3 lights  — fg only · 4 착륙 라이트 (또는 빔 시 ▼)'),
      h(Box, { marginTop: 1 },
        h(Text, { color: C.dim },
          '4 poses: default · scan-left · scan-right · beam-on')),
    ),

    h(Divider, { label: '선택 요청' }),
    h(Box, { flexDirection: 'column', marginLeft: 2 },
      h(Text, { color: C.dim },
        '1. 팔레트 (sky · teal · violet · star)'),
      h(Text, { color: C.dim },
        '2. 돔 너비 (지금 5-col) · 접시 너비 (지금 9-col) 조정 필요?'),
      h(Text, { color: C.dim },
        '3. 라이트 개수·모양 (지금 4점 ▘ / beam 시 ▼) 변경?'),
    ),
  )
}

render(h(App))
