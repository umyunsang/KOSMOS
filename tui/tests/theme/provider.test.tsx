// T042 — ThemeProvider tests
// Asserts that KOSMOS_TUI_THEME env var controls which token set is exposed.
// Uses ink-testing-library to render <ThemeProvider /> + a consumer component
// that calls useTheme() and renders theme.success and theme.error as Text.

import { describe, expect, it, beforeEach, afterEach } from 'bun:test'
import React from 'react'
import { Text, Box } from 'ink'
import { render } from 'ink-testing-library'
import { ThemeProvider, useTheme } from '../../src/theme/provider'
import defaultTheme from '../../src/theme/default'
import darkTheme from '../../src/theme/dark'
import lightTheme from '../../src/theme/light'

// ---------------------------------------------------------------------------
// Helper consumer component
// ---------------------------------------------------------------------------

/**
 * A minimal component that renders the current theme's "success" token
 * so we can assert which theme is active without inspecting colors directly
 * (Ink's stdout capture strips ANSI, but Text with explicit color still
 * renders the text content reliably).
 */
function ThemeInspector() {
  const theme = useTheme()
  return (
    <Box flexDirection="column">
      <Text>{`success:${theme.success}`}</Text>
      <Text>{`error:${theme.error}`}</Text>
      <Text>{`text:${theme.text}`}</Text>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Helpers to manage env var across tests
// ---------------------------------------------------------------------------

let savedThemeEnv: string | undefined

function setThemeEnv(value: string | undefined) {
  if (value === undefined) {
    delete process.env['KOSMOS_TUI_THEME']
  } else {
    process.env['KOSMOS_TUI_THEME'] = value
  }
}

beforeEach(() => {
  savedThemeEnv = process.env['KOSMOS_TUI_THEME']
})

afterEach(() => {
  setThemeEnv(savedThemeEnv)
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('ThemeProvider — KOSMOS_TUI_THEME=default', () => {
  it('exposes defaultTheme tokens when KOSMOS_TUI_THEME=default', () => {
    setThemeEnv('default')
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeInspector />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain(`success:${defaultTheme.success}`)
    expect(frame).toContain(`error:${defaultTheme.error}`)
  })
})

describe('ThemeProvider — KOSMOS_TUI_THEME=dark', () => {
  it('exposes darkTheme tokens when KOSMOS_TUI_THEME=dark', () => {
    setThemeEnv('dark')
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeInspector />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain(`success:${darkTheme.success}`)
    expect(frame).toContain(`error:${darkTheme.error}`)
  })
})

describe('ThemeProvider — KOSMOS_TUI_THEME=light', () => {
  it('exposes lightTheme tokens when KOSMOS_TUI_THEME=light', () => {
    setThemeEnv('light')
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeInspector />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain(`success:${lightTheme.success}`)
    expect(frame).toContain(`error:${lightTheme.error}`)
  })
})

describe('ThemeProvider — unset KOSMOS_TUI_THEME', () => {
  it('falls back to defaultTheme when env var is unset', () => {
    setThemeEnv(undefined)
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeInspector />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain(`success:${defaultTheme.success}`)
  })
})

describe('ThemeProvider — unknown KOSMOS_TUI_THEME value', () => {
  it('falls back to defaultTheme on unknown value', () => {
    setThemeEnv('neon-cyberpunk')
    const { lastFrame } = render(
      <ThemeProvider>
        <ThemeInspector />
      </ThemeProvider>,
    )
    const frame = lastFrame() ?? ''
    expect(frame).toContain(`success:${defaultTheme.success}`)
  })
})
