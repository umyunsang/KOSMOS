// SPDX-License-Identifier: Apache-2.0
// Guards the first-run LogoV2 surface from regressing to upstream CC branding.

import { describe, expect, it } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { CondensedLogo } from '../../src/components/LogoV2/CondensedLogo'
import { TerminalSizeContext } from '../../src/ink/components/TerminalSizeContext'
import {
  AppStoreContext,
  getDefaultAppState,
} from '../../src/state/AppState'
import { createStore } from '../../src/state/store'
import { ThemeProvider } from '../../src/theme/provider'

describe('LogoV2 UMMAYA branding', () => {
  it('renders the condensed startup brand as UMMAYA with the Umma mascot', () => {
    const { lastFrame } = render(
      <ThemeProvider>
        <AppStoreContext.Provider value={createStore(getDefaultAppState())}>
          <TerminalSizeContext.Provider value={{ columns: 100, rows: 30 }}>
            <CondensedLogo />
          </TerminalSizeContext.Provider>
        </AppStoreContext.Provider>
      </ThemeProvider>,
    )

    const frame = lastFrame() ?? ''
    expect(frame).toContain('UMMAYA')
    expect(frame).toContain('▗▖ ▗▖')
    expect(frame).toContain('███')
    expect(frame).not.toContain('Claude Code')
  })
})
