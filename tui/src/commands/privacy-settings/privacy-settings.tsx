// SPDX-License-Identifier: Apache-2.0
//
// UMMAYA-1633 P1+P2 / UMMAYA-1978 T011 — privacy-settings command stub.
//
// Original CC module: `tui/src/commands/privacy-settings/privacy-settings.tsx`
// (CC 2.1.88) drives the Anthropic Claude.ai privacy dialog ("Grove") which
// surfaces the consumer-tier opt-in/opt-out for training-data use.
//
// UMMAYA scope: privacy is governed by the L1 Permission Gauntlet (Spec 033).
// The Grove dialog has no UMMAYA-equivalent surface — running
// `/privacy-settings` emits a redirect message to the active permission UI.

import * as React from 'react'
import type { LocalJSXCommandOnDone } from '../../types/command.js'

const UMMAYA_PRIVACY_REDIRECT =
  'UMMAYA privacy controls live in `/permissions`. ' +
  'The Anthropic Grove dialog is not part of the citizen TUI (Spec 1633 P1+P2).'

export async function call(
  onDone: LocalJSXCommandOnDone,
): Promise<React.ReactNode | null> {
  onDone(UMMAYA_PRIVACY_REDIRECT, { display: 'system' })
  return null
}
