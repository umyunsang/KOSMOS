// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original React context provider for KOSMOS_TUI_THEME resolution.
// No upstream analog in Claude Code — CC uses a plain object import, not React context.
import { createContext, useContext, type ReactNode } from 'react'
import defaultTheme from './default'
import darkTheme from './dark'
import lightTheme from './light'
import type { ThemeToken } from './tokens'

/**
 * KOSMOS-original ThemeProvider.
 *
 * Reads KOSMOS_TUI_THEME at startup and exposes the resolved ThemeToken
 * to all child components via React context.  Supported values:
 *   "default" (alias for dark)  →  defaultTheme
 *   "dark"                      →  darkTheme
 *   "light"                     →  lightTheme
 *
 * Falls back to defaultTheme on unset or unrecognised values, and writes a
 * warning to process.stderr for unrecognised values (never for unset).
 *
 * FR-039 (theme token context), FR-040 (ThemeToken named set),
 * FR-041 (KOSMOS_TUI_THEME env var).
 */

const THEMES: Record<string, ThemeToken> = {
  default: defaultTheme,
  dark: darkTheme,
  light: lightTheme,
}

const ThemeContext = createContext<ThemeToken>(defaultTheme)

export function ThemeProvider({ children }: { children: ReactNode }) {
  const name = process.env['KOSMOS_TUI_THEME'] ?? 'default'
  const theme = THEMES[name] ?? defaultTheme
  if (THEMES[name] === undefined && name !== 'default') {
    process.stderr.write(
      `[KOSMOS-TUI] Unknown theme "${name}", falling back to default\n`,
    )
  }
  return <ThemeContext.Provider value={theme}>{children}</ThemeContext.Provider>
}

export function useTheme(): ThemeToken {
  return useContext(ThemeContext)
}

/**
 * Resolve a theme by name outside of React context — used by CC-ported
 * utilities (`src/utils/theme.ts`) that expect an imperative `getTheme`
 * accessor. Falls back to defaultTheme on unknown names.
 */
export function getThemeByName(name: string): ThemeToken {
  return THEMES[name] ?? defaultTheme
}
