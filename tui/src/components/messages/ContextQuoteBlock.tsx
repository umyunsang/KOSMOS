// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — ContextQuoteBlock component (FR-013, T020).
//
// Multi-turn context citation with ⎿ prefix + single-border box.
// Brand glyph ⎿ is canonical (migration tree § brand · thread glyph,
// FR-036) — must not be substituted.
//
// Source reference: cc:components/Message.tsx (CC quote glyph usage)
//   + migration tree §UI-B.5.

import React from 'react';
import { Box, Text } from '../../ink.js';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Thread-prefix glyph — brand-frozen per FR-036 / migration tree brand. */
export const QUOTE_GLYPH = '⎿' as const;

/** Single-border color for the quote box (dimmed to match CC style). */
const QUOTE_BORDER_COLOR = 'gray';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export type ContextQuoteBlockProps = {
  /** The quoted turn content (markdown or plain text). */
  children: React.ReactNode;
  /** Optional label shown after the ⎿ glyph (e.g., turn number or summary). */
  label?: string;
};

/**
 * ContextQuoteBlock renders a multi-turn context citation.
 *
 * Contract (FR-013):
 * - Renders with ⎿ prefix on the first line.
 * - Surrounds content with a single-border box.
 * - Glyph must be ⎿ (brand-frozen per FR-036).
 */
export function ContextQuoteBlock({
  children,
  label,
}: ContextQuoteBlockProps): React.ReactNode {
  return (
    <Box flexDirection="row" alignItems="flex-start">
      {/* ⎿ prefix glyph */}
      <Box marginRight={1} flexShrink={0}>
        <Text dimColor>{QUOTE_GLYPH}</Text>
      </Box>

      {/* Content with single-border box */}
      <Box
        flexDirection="column"
        borderStyle="single"
        borderColor={QUOTE_BORDER_COLOR}
        paddingX={1}
        paddingY={0}
        flexGrow={1}
      >
        {label && (
          <Text dimColor bold>
            {label}
          </Text>
        )}
        {children}
      </Box>
    </Box>
  );
}
