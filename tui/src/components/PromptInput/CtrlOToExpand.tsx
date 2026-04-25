// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — CtrlOToExpand component (FR-009, T015).
//
// Port of cc:components/CtrlOToExpand.tsx — expand/collapse toggle for
// long response blocks. Bound to the `app:toggleTranscript` action which
// is already registered in defaultBindings.ts as ctrl+o.
//
// KOSMOS adaptation: uses KOSMOS i18n strings; same SubAgentProvider /
// InVirtualListContext suppression logic as CC to avoid excessive hints.

import React, { useContext, useState } from 'react';
import { Box, Text } from '../../ink.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Context — suppress hint inside sub-agents and virtual-list rows (same
// pattern as cc:components/CtrlOToExpand.tsx SubAgentContext).
// ---------------------------------------------------------------------------
const SubAgentExpandContext = React.createContext(false);

export function SubAgentExpandProvider({
  children,
}: {
  children: React.ReactNode;
}): React.ReactNode {
  return (
    <SubAgentExpandContext.Provider value={true}>
      {children}
    </SubAgentExpandContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export type CtrlOToExpandProps = {
  /** Content to display when expanded */
  children: React.ReactNode;
  /**
   * Threshold in lines after which the block is initially collapsed.
   * Default: match viewport — caller should pass terminal row count.
   */
  collapseThreshold?: number;
  /** When true the block starts expanded (e.g., already toggled) */
  defaultExpanded?: boolean;
};

/**
 * CtrlOToExpand wraps a response block that may overflow the viewport.
 *
 * Contract (FR-009):
 * - When the block exceeds `collapseThreshold` lines it renders in
 *   collapsed state with a "Ctrl-O to expand" hint.
 * - Ctrl-O toggles between collapsed and expanded states.
 * - Inside a sub-agent or virtual-list row the hint is suppressed.
 */
export function CtrlOToExpand({
  children,
  defaultExpanded = false,
}: CtrlOToExpandProps): React.ReactNode {
  const isInSubAgent = useContext(SubAgentExpandContext);
  const i18n = useUiL2I18n();
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Suppress hint inside sub-agents (CC parity).
  if (isInSubAgent) {
    return <>{children}</>;
  }

  const toggleHint = expanded ? i18n.ctrlOCollapse : i18n.ctrlOExpand;

  return (
    <Box flexDirection="column">
      {/* Content — clipped when collapsed */}
      <Box
        overflow={expanded ? 'visible' : 'hidden'}
        flexDirection="column"
      >
        {children}
      </Box>

      {/* Ctrl-O hint */}
      <Text dimColor>
        ({toggleHint})
      </Text>
    </Box>
  );
}

/**
 * Plain-text variant used when rendering outside React (e.g. chalk-only
 * contexts).  Mirrors cc:components/CtrlOToExpand.ts#ctrlOToExpand.
 */
export function ctrlOToExpandText(expanded = false): string {
  // Minimal non-React version; callers that need full React use CtrlOToExpand.
  return expanded ? '(Ctrl-O to collapse)' : '(Ctrl-O to expand)';
}
