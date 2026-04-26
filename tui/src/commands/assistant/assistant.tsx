// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — Assistant install wizard minimal port.
//
// CC's Assistant subsystem provided an interactive ink wizard for installing
// a sandboxed Claude assistant alongside the developer environment. KOSMOS
// does not ship that subsystem (the citizen REPL is the only assistant
// surface); we expose a minimum dialog that explains the deprecation and
// resolves with `null` so any caller that races for an install path receives
// a deterministic "not available" response.

import * as React from 'react'
import { Box, Text } from '../../ink.js'
import { useKeybinding } from '../../keybindings/useKeybinding.js'

export type NewInstallWizardProps = {
  defaultDir: string
  onInstalled: (dir: string) => void
  onCancel: () => void
  onError: (message: string) => void
}

export function NewInstallWizard({ onCancel }: NewInstallWizardProps): React.ReactElement {
  useKeybinding('escape', () => {
    onCancel()
  })
  useKeybinding('return', () => {
    onCancel()
  })

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1} borderStyle="round">
      <Text bold color="yellow">
        KOSMOS — Assistant install wizard removed
      </Text>
      <Box marginTop={1}>
        <Text>
          KOSMOS does not ship the standalone Assistant install path that CC
          used. Press <Text bold>Enter</Text> or <Text bold>Esc</Text> to
          dismiss this dialog and continue with the citizen REPL.
        </Text>
      </Box>
    </Box>
  )
}

/**
 * KOSMOS-1633 — Assistant install dir is deterministically empty since the
 * subsystem is removed. Callers should treat the empty string as "not
 * configured" and skip any auto-attach behavior.
 */
export async function computeDefaultInstallDir(): Promise<string> {
  return ''
}
