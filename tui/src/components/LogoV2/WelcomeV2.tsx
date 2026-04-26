// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — P6 smoke: KOSMOS welcome banner.
// Ported from CC 2.1.88 WelcomeV2 (orbital-satellite motif).
// Replaced "Welcome to Claude Code" → "Welcome to KOSMOS" per migration-tree UI-A.
// Added `version` prop (with MACRO.VERSION fallback) for testability (FR-011).

import React from 'react'
import { Box, Text, useTheme } from 'src/ink.js'
import { env } from '../../utils/env.js'

const WELCOME_V2_WIDTH = 58

// ---------------------------------------------------------------------------
// Safe MACRO accessor — MACRO is a Bun build-time constant injected by
// bunfig.toml preload. In tests it is provided by src/stubs/macro-preload.ts.
// Guard for environments that may not have the preload active.
// ---------------------------------------------------------------------------
function safeVersion(): string {
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const g = globalThis as any
    if (typeof g.MACRO !== 'undefined' && g.MACRO.VERSION) return g.MACRO.VERSION
  } catch {
    /* ignore */
  }
  return 'unknown'
}

export interface WelcomeV2Props {
  /** Explicit version string. When omitted, falls back to MACRO.VERSION. */
  readonly version?: string
}

// ---------------------------------------------------------------------------
// WelcomeV2 — KOSMOS welcome banner with orbital-satellite ASCII motif.
// Renders in two flavours: Apple Terminal (compact) and standard (full art).
// ---------------------------------------------------------------------------
export function WelcomeV2({ version }: WelcomeV2Props = {}): React.ReactElement {
  const [theme] = useTheme()
  const ver = version ?? safeVersion()

  if (env.terminal === 'Apple_Terminal') {
    return <AppleTerminalWelcomeV2 theme={theme} version={ver} />
  }

  const isLight = ['light', 'light-daltonized', 'light-ansi'].includes(theme)

  if (isLight) {
    return (
      <Box width={WELCOME_V2_WIDTH}>
        <Text>
          <Text>
            <Text color="claude">{'Welcome to KOSMOS'} </Text>
            <Text dimColor>v{ver} </Text>
          </Text>
          {'…………………………………………………………………………………………………………………………………………………………'}
          {'                                                          '}
          {'                                                          '}
          {'                                                          '}
          {'            ░░░░░░                                        '}
          {'    ░░░   ░░░░░░░░░░                                      '}
          {'   ░░░░░░░░░░░░░░░░░░░                                    '}
          {'                                                          '}
          <Text>
            <Text dimColor>{'                           ░░░░'}</Text>
            <Text>{'                     ██    '}</Text>
          </Text>
          <Text>
            <Text dimColor>{'                         ░░░░░░░░░░'}</Text>
            <Text>{'               ██▒▒██  '}</Text>
          </Text>
          {'                                            ▒▒      ██   ▒'}
          <Text>
            {'      '}
            <Text color="clawd_body">{' █████████ '}</Text>
            {'                         ▒▒░░▒▒      ▒ ▒▒'}
          </Text>
          <Text>
            {'      '}
            <Text color="clawd_body" backgroundColor="clawd_background">
              {'██▄█████▄██'}
            </Text>
            {'                           ▒▒         ▒▒ '}
          </Text>
          <Text>
            {'      '}
            <Text color="clawd_body">{' █████████ '}</Text>
            {'                          ░          ▒   '}
          </Text>
          <Text>
            {'…………………'}
            <Text color="clawd_body">{'█ █   █ █'}</Text>
            {'……………………………………………………………………░…………………………▒…………'}
          </Text>
        </Text>
      </Box>
    )
  }

  // Dark / default theme — full orbital art
  return (
    <Box width={WELCOME_V2_WIDTH}>
      <Text>
        <Text>
          <Text color="claude">{'Welcome to KOSMOS'} </Text>
          <Text dimColor>v{ver} </Text>
        </Text>
        {'…………………………………………………………………………………………………………………………………………………………'}
        {'                                                          '}
        {'     *                                       █████▓▓░     '}
        {'                                 *         ███▓░     ░░   '}
        {'            ░░░░░░                        ███▓░           '}
        {'    ░░░   ░░░░░░░░░░                      ███▓░           '}
        <Text>
          {'   ░░░░░░░░░░░░░░░░░░░    '}
          <Text bold>*</Text>
          {'                ██▓░░      ▓   '}
        </Text>
        {'                                             ░▓▓███▓▓░    '}
        <Text dimColor>{' *                                 ░░░░                   '}</Text>
        <Text dimColor>{'                                 ░░░░░░░░                 '}</Text>
        <Text dimColor>{'                               ░░░░░░░░░░░░░░░░           '}</Text>
        <Text>
          {'      '}
          <Text color="clawd_body">{' █████████ '}</Text>
          {'                                       '}
          <Text dimColor>*</Text>
          <Text> </Text>
        </Text>
        <Text>
          {'      '}
          <Text color="clawd_body">{'██▄█████▄██'}</Text>
          {'                        '}
          <Text bold>*</Text>
          {'                '}
        </Text>
        <Text>
          {'      '}
          <Text color="clawd_body">{' █████████ '}</Text>
          {'     *                                   '}
        </Text>
        <Text>
          {'…………………'}
          <Text color="clawd_body">{'█ █   █ █'}</Text>
          {'………………………………………………………………………………………………………………'}
        </Text>
      </Text>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// AppleTerminalWelcomeV2 — compact variant for Apple Terminal
// ---------------------------------------------------------------------------
interface AppleTerminalWelcomeV2Props {
  theme: string
  version: string
}

function AppleTerminalWelcomeV2({
  theme,
  version,
}: AppleTerminalWelcomeV2Props): React.ReactElement {
  const isLight = ['light', 'light-daltonized', 'light-ansi'].includes(theme)

  if (isLight) {
    return (
      <Box width={WELCOME_V2_WIDTH}>
        <Text>
          <Text>
            <Text color="claude">{'Welcome to KOSMOS'} </Text>
            <Text dimColor>v{version} </Text>
          </Text>
          {'…………………………………………………………………………………………………………………………………………………………'}
          {'                                                          '}
          {'            ░░░░░░                                        '}
          {'    ░░░   ░░░░░░░░░░                                      '}
          {'   ░░░░░░░░░░░░░░░░░░░                                    '}
          <Text>
            {'        '}
            <Text color="clawd_body">{'▗'}</Text>
            <Text color="clawd_background" backgroundColor="clawd_body">
              {' '}▗{'     '}▖{' '}
            </Text>
            <Text color="clawd_body">{'▖'}</Text>
            {'                       '}
            <Text bold>*</Text>
            {'                '}
          </Text>
          <Text>
            {'        '}
            <Text backgroundColor="clawd_body">{' '.repeat(9)}</Text>
            {'      *                                   '}
          </Text>
          <Text>
            {'…………………'}
            <Text backgroundColor="clawd_body">{' '}</Text>
            <Text>{' '}</Text>
            <Text backgroundColor="clawd_body">{' '}</Text>
            {'   '}
            <Text backgroundColor="clawd_body">{' '}</Text>
            <Text>{' '}</Text>
            <Text backgroundColor="clawd_body">{' '}</Text>
            {'………………………………………………………………………………………………………………'}
          </Text>
        </Text>
      </Box>
    )
  }

  // Dark theme Apple Terminal
  return (
    <Box width={WELCOME_V2_WIDTH}>
      <Text>
        <Text>
          <Text color="claude">{'Welcome to KOSMOS'} </Text>
          <Text dimColor>v{version} </Text>
        </Text>
        {'…………………………………………………………………………………………………………………………………………………………'}
        {'     *                                       █████▓▓░     '}
        {'                                 *         ███▓░     ░░   '}
        {'            ░░░░░░                        ███▓░           '}
        {'    ░░░   ░░░░░░░░░░                      ███▓░           '}
        <Text dimColor>{' *                                 ░░░░                   '}</Text>
        <Text dimColor>{'                                 ░░░░░░░░                 '}</Text>
        <Text dimColor>{'                               ░░░░░░░░░░░░░░░░           '}</Text>
        <Text>
          {'                                                      '}
          <Text dimColor>*</Text>
          <Text> </Text>
        </Text>
        <Text>
          {'        '}
          <Text color="clawd_body">{'▗'}</Text>
          <Text color="clawd_background" backgroundColor="clawd_body">
            {' '}▗{'     '}▖{' '}
          </Text>
          <Text color="clawd_body">{'▖'}</Text>
          {'                       '}
          <Text bold>*</Text>
          {'                '}
        </Text>
        <Text>
          {'        '}
          <Text backgroundColor="clawd_body">{' '.repeat(9)}</Text>
          {'      *                                   '}
        </Text>
        <Text>
          {'…………………'}
          <Text backgroundColor="clawd_body">{' '}</Text>
          <Text>{' '}</Text>
          <Text backgroundColor="clawd_body">{' '}</Text>
          {'   '}
          <Text backgroundColor="clawd_body">{' '}</Text>
          <Text>{' '}</Text>
          <Text backgroundColor="clawd_body">{' '}</Text>
          {'………………………………………………………………………………………………………………'}
        </Text>
      </Text>
    </Box>
  )
}
