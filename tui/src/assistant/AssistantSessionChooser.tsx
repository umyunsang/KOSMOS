// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T009 — stub-noop component.
//
// Original CC module: `tui/src/assistant/AssistantSessionChooser.tsx`
// CC version: 2.1.88
// KOSMOS deviation: AssistantSessionChooser is the Anthropic Console
// session-selection UI. KOSMOS sessions live in `~/.kosmos/memdir/user/sessions/`
// (Spec 027) and the chooser is a different KOSMOS-original component
// (`tui/src/screens/SessionPicker.tsx` — separate stack). This stub returns
// null so any unintended dynamic import via main.tsx links cleanly.

import React from 'react'

export interface AssistantSessionChooserProps {
  [key: string]: unknown
}

export function AssistantSessionChooser(
  _props: AssistantSessionChooserProps,
): React.ReactElement | null {
  return null
}

export default AssistantSessionChooser
