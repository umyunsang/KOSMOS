// SPDX-License-Identifier: Apache-2.0
//
// KOSMOS-1633 P1+P2 / KOSMOS-1978 T011 — privacy-settings command stub.
//
// Original CC module: `tui/src/commands/privacy-settings/privacy-settings.tsx`
// (CC 2.1.88) drives the Anthropic Claude.ai privacy dialog ("Grove") which
// surfaces the consumer-tier opt-in/opt-out for training-data use.
//
// KOSMOS scope: privacy is governed by the L1 Permission Gauntlet (Spec 033)
// + the onboarding PIPA consent flow (Spec 035 §4 ministry-scope-ack). The
// Grove dialog has no KOSMOS-equivalent surface — running `/privacy-settings`
// emits a redirect message pointing the citizen to the PIPA flow.

import * as React from 'react'
import type { LocalJSXCommandOnDone } from '../../types/command.js'

const KOSMOS_PRIVACY_REDIRECT =
  'KOSMOS privacy controls live in `/onboarding pipa-consent` and `/permissions`. ' +
  'The Anthropic Grove dialog is not part of the citizen TUI (Spec 1633 P1+P2).'

export async function call(
  onDone: LocalJSXCommandOnDone,
): Promise<React.ReactNode | null> {
  onDone(KOSMOS_PRIVACY_REDIRECT, { display: 'system' })
  return null
}
