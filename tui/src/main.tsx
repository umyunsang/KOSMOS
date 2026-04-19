// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original entrypoint bootstrap.
//
// Renders <App> via Ink's render(), creating the bridge first so it can be
// passed as a prop (avoids module-level side-effects that would break tests).
//
// SIGTERM / Ctrl-C handling:
//   - Ink's useInput (Ctrl-C) in App triggers bridge.close() → exit().
//   - A top-level SIGTERM handler also calls bridge.close().
//   - Both paths respect the ≤3 s SIGTERM → SIGKILL timeout (FR-009).
//
// T052: <ThemeProvider> mounted at the render root so every Box/Text component
// across the tree consumes the resolved token set via useTheme() (FR-040).

import React from 'react'
import { render } from 'ink'
import { createBridge } from './ipc/bridge'
import { App } from './entrypoints/tui'
import { ThemeProvider } from './theme/provider'

async function main(): Promise<void> {
  const bridge = createBridge()

  // Top-level SIGTERM handler (e.g. docker stop / systemd stop)
  process.on('SIGTERM', () => {
    bridge.close().then(() => process.exit(0))
  })

  const { waitUntilExit } = render(
    <ThemeProvider>
      <App bridge={bridge} />
    </ThemeProvider>,
  )
  await waitUntilExit()
}

main().catch((err: unknown) => {
  process.stderr.write(`[KOSMOS TUI] Fatal error: ${err}\n`)
  process.exit(1)
})
