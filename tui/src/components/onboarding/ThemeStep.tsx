// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — Onboarding step 2: Theme (FR-001 step 2, FR-035, T041).
//
// Renders the UFO mascot in idle pose with the approved KOSMOS purple palette
// (body #a78bfa / background #4c1d95). Theme options: dark (default) / light /
// system. ↑↓ to select, Enter to confirm and advance.
//
// Reference: docs/wireframes/ui-a-onboarding.mjs § Step2_Theme
//            docs/wireframes/ufo-mascot-proposal.mjs (violet palette, 3-row struct)
// FR-035: UFO mascot four-pose, purple palette body #a78bfa background #4c1d95
// IME gate: useKoreanIME per vision.md § Keyboard-shortcut migration

import React, { useEffect, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider.js'
import { useKoreanIME } from '../../hooks/useKoreanIME.js'
import { UFO_PALETTE, type UfoMascotPoseT } from '../../schemas/ui-l2/ufo.js'
import { getUiL2I18n } from '../../i18n/uiL2.js'
import { emitSurfaceActivation } from '../../observability/surface.js'

// ---------------------------------------------------------------------------
// UFO mascot (3-row Clawd-technique port, violet palette)
// ---------------------------------------------------------------------------

// Pose-to-shape mapping from docs/wireframes/ufo-mascot-proposal.mjs
const UFO_SHAPES: Record<
  UfoMascotPoseT,
  {
    domeL: string
    domeMid: string
    domeR: string
    saucerL: string
    saucerMid: string
    saucerR: string
    lights: string
  }
> = {
  idle: {
    domeL: '    ',
    domeMid: '▛███▜',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '   ▘ ▘ ▘ ▘   ',
  },
  thinking: {
    domeL: '    ',
    domeMid: '▟███▟',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '   ▘ ▘ ▘ ▘   ',
  },
  success: {
    domeL: '    ',
    domeMid: '▙███▙',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '   ▘ ▘ ▘ ▘   ',
  },
  error: {
    domeL: '    ',
    domeMid: '▛███▜',
    domeR: '    ',
    saucerL: '▗▟',
    saucerMid: '█████████',
    saucerR: '▙▖',
    lights: '  ▼ ▼ ▼ ▼ ▼  ',
  },
}

type UfoMascotProps = {
  pose: UfoMascotPoseT
  ariaLabel: string
}

function UfoMascot({ pose, ariaLabel }: UfoMascotProps): React.ReactElement {
  const shape = UFO_SHAPES[pose]
  const { body, background } = UFO_PALETTE
  return (
    <Box
      flexDirection="column"
      // aria-label is not directly supported by Ink; the ariaLabel prop is used
      // to render accessible text below when screen_reader mode is detected.
    >
      {/* Row 1 · dome */}
      <Text>
        <Text color={body}>{shape.domeL}</Text>
        <Text color={body} backgroundColor={background}>{shape.domeMid}</Text>
        <Text color={body}>{shape.domeR}</Text>
      </Text>
      {/* Row 2 · saucer */}
      <Text>
        <Text color={body}>{shape.saucerL}</Text>
        <Text color={body} backgroundColor={background}>{shape.saucerMid}</Text>
        <Text color={body}>{shape.saucerR}</Text>
      </Text>
      {/* Row 3 · landing lights */}
      <Text color={body}>{shape.lights}</Text>
      {/* Accessible description (rendered for screen readers; dimmed visually) */}
      <Text color={body} dimColor>
        {ariaLabel}
      </Text>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Theme options
// ---------------------------------------------------------------------------

type ThemeOption = {
  value: 'dark' | 'light' | 'system'
  labelKo: string
  labelEn: string
  descKo: string
  descEn: string
}

const THEME_OPTIONS: readonly ThemeOption[] = [
  { value: 'dark', labelKo: 'dark', labelEn: 'dark', descKo: '어두운 배경 (기본)', descEn: 'dark background (default)' },
  { value: 'light', labelKo: 'light', labelEn: 'light', descKo: '밝은 배경', descEn: 'light background' },
  { value: 'system', labelKo: 'system', labelEn: 'system', descKo: '시스템 따름', descEn: 'follow system setting' },
]

// ---------------------------------------------------------------------------
// Step header
// ---------------------------------------------------------------------------

function StepProgressDots({ current, total }: { current: number; total: number }) {
  const theme = useTheme()
  const dots = Array.from({ length: total }, (_, i) =>
    i < current ? '●' : i === current ? '◉' : '○',
  ).join(' ')
  return (
    <Text color={theme.subtle}>
      {dots}{'     '}{current + 1} / {total}
    </Text>
  )
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type ThemeStepProps = {
  onAdvance: (selectedTheme: 'dark' | 'light' | 'system') => void
  onExit: () => void
  locale?: 'ko' | 'en'
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ThemeStep({
  onAdvance,
  onExit,
  locale,
}: ThemeStepProps): React.ReactElement {
  const theme = useTheme()
  const { isComposing } = useKoreanIME()
  const i18n = getUiL2I18n(
    locale ?? ((process.env['KOSMOS_TUI_LOCALE'] as 'ko' | 'en') || 'ko'),
  )
  const isEn = (locale ?? process.env['KOSMOS_TUI_LOCALE']) === 'en'

  const [selectedIdx, setSelectedIdx] = useState(0)

  useEffect(() => {
    emitSurfaceActivation('onboarding', { 'onboarding.step': 'theme' })
  }, [])

  useInput((input, key) => {
    if (isComposing) return
    if (key.ctrl && (input === 'c' || input === 'd')) {
      onExit()
      return
    }
    if (key.escape) {
      onExit()
      return
    }
    if (key.upArrow) {
      setSelectedIdx((i) => (i - 1 + THEME_OPTIONS.length) % THEME_OPTIONS.length)
      return
    }
    if (key.downArrow) {
      setSelectedIdx((i) => (i + 1) % THEME_OPTIONS.length)
      return
    }
    if (key.return) {
      const opt = THEME_OPTIONS[selectedIdx]
      if (opt !== undefined) {
        onAdvance(opt.value)
      }
    }
  })

  return (
    <Box flexDirection="column" paddingX={1}>
      <Box flexDirection="column">
        <Text bold color={theme.wordmark}>
          {i18n.themeStepTitle}
        </Text>
        <StepProgressDots current={1} total={5} />
      </Box>

      {/* UFO mascot preview */}
      <Box marginTop={1} flexDirection="row" alignItems="flex-start">
        <Box marginRight={3}>
          <UfoMascot
            pose="idle"
            ariaLabel={i18n.ufoMascot('idle')}
          />
        </Box>
        <Box flexDirection="column" justifyContent="center">
          <Text bold>KOSMOS</Text>
          <Text color={theme.subtle}>EXAONE · FriendliAI</Text>
          <Box marginTop={1}>
            <Text color={UFO_PALETTE.body}>✻</Text>
            <Text color={theme.subtle}> 보라 팔레트 · purple palette</Text>
          </Box>
          <Box>
            <Text color={theme.subtle} dimColor>
              body </Text>
            <Text color={UFO_PALETTE.body}>{UFO_PALETTE.body}</Text>
            <Text color={theme.subtle} dimColor> · bg </Text>
            <Text color={UFO_PALETTE.body} backgroundColor={UFO_PALETTE.background}>
              {UFO_PALETTE.background}
            </Text>
          </Box>
        </Box>
      </Box>

      {/* Theme selector */}
      <Box marginTop={1} flexDirection="column" marginLeft={2}>
        {THEME_OPTIONS.map((opt, idx) => {
          const selected = idx === selectedIdx
          const label = isEn ? opt.labelEn : opt.labelKo
          const desc = isEn ? opt.descEn : opt.descKo
          return (
            <Box key={opt.value} flexDirection="row">
              <Text color={selected ? theme.kosmosCore : theme.subtle}>
                {selected ? '[선택] ▸ ' : '        '}
              </Text>
              <Text bold={selected}>{label.padEnd(8)}</Text>
              <Text color={theme.subtle} dimColor>{desc}</Text>
            </Box>
          )
        })}
      </Box>

      <Box marginTop={1}>
        <Text color={theme.kosmosCore}>
          ↑↓ {isEn ? 'select' : '선택'}{'  ·  '}
        </Text>
        <Text color={theme.kosmosCore}>{i18n.onboardingNext}</Text>
        <Text color={theme.subtle}>{'  ·  /theme '}{isEn ? 'to change later' : '로 나중 변경'}</Text>
      </Box>
    </Box>
  )
}
