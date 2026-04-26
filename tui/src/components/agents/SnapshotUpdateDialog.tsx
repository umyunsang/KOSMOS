// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T009 — stub-noop component.
//
// Original CC module: `tui/src/components/agents/SnapshotUpdateDialog.tsx`
// CC version: 2.1.88
// KOSMOS deviation: Anthropic's snapshot-update dialog ships agent-definition
// versions over the `claude agents` Console API. KOSMOS swarm uses Spec 027
// mailbox semantics — there is no Anthropic-Console snapshot lifecycle.
// Component returns null so any incidental render is silent.

import React from 'react'

export interface SnapshotUpdateDialogProps {
  // shape preserved as `unknown`-keyed Record so callers compile without
  // forcing us to mirror CC's full props surface.
  [key: string]: unknown
}

export function SnapshotUpdateDialog(_props: SnapshotUpdateDialogProps): React.ReactElement | null {
  return null
}

export default SnapshotUpdateDialog
