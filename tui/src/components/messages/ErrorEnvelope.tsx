// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — ErrorEnvelope component (FR-012, T019).
//
// Three visually differentiated error envelope styles (migration tree §UI-B.4):
//   llm     → purple accent + brain glyph  (🧠)
//   tool    → orange accent + wrench glyph (🔧)
//   network → red accent + signal glyph    (📡)
//
// Source reference: cc:components/FallbackToolUseErrorMessage.tsx (Tool path)
//   + Spec 019 LLM 429 / Spec 032 Network HUD patterns.
// KOSMOS adaptation: unified 3-type envelope with KOSMOS i18n + color tokens.

import React from 'react';
import { Box, Text } from '../../ink.js';
import {
  type ErrorEnvelopeT,
  ERROR_VISUAL,
} from '../../schemas/ui-l2/error.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';

// ---------------------------------------------------------------------------
// Color map — maps error type to Ink color string.
// These intentionally use literal hex values (not theme tokens) so that
// the three error types remain visually distinct regardless of the active
// theme — per FR-012 "unique color" requirement.
// ---------------------------------------------------------------------------
const ERROR_COLOR: Record<ErrorEnvelopeT['type'], string> = {
  llm: '#a78bfa',      // purple (KOSMOS brand / LLM layer)
  tool: '#f97316',     // orange (tool layer, CC-style)
  network: '#ef4444',  // red (network layer)
};

const ERROR_BORDER_COLOR: Record<ErrorEnvelopeT['type'], string> = {
  llm: '#7c3aed',
  tool: '#ea580c',
  network: '#dc2626',
};

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export type ErrorEnvelopeProps = {
  error: ErrorEnvelopeT;
  /** When provided, called when the citizen presses R to retry */
  onRetry?: () => void;
  /** Locale override — falls back to KOSMOS_TUI_LOCALE env var */
  locale?: 'ko' | 'en';
};

/**
 * ErrorEnvelope displays a failed operation with three differentiated styles.
 *
 * Contract (FR-012):
 * - Each error type has a unique color, icon (glyph), and header label.
 * - A non-technical citizen can identify the error layer at a glance.
 * - `retry_suggested` shows a retry hint (R keystroke).
 */
export function ErrorEnvelope({
  error,
  onRetry,
}: ErrorEnvelopeProps): React.ReactNode {
  const i18n = useUiL2I18n();
  const visual = ERROR_VISUAL[error.type];
  const color = ERROR_COLOR[error.type];
  const borderColor = ERROR_BORDER_COLOR[error.type];

  // Locale-select title and detail.
  const locale = (process.env['KOSMOS_TUI_LOCALE'] ?? 'ko') as 'ko' | 'en';
  const title = locale === 'en' ? error.title_en : error.title_ko;
  const detail = locale === 'en' ? error.detail_en : error.detail_ko;

  return (
    <Box
      flexDirection="column"
      borderStyle="single"
      borderColor={borderColor}
      paddingX={1}
      paddingY={0}
    >
      {/* Header: glyph + type label + title */}
      <Box>
        <Text color={color} bold>
          {visual.glyph} {i18n.errorTitle(error.type)}{title !== i18n.errorTitle(error.type) ? `: ${title}` : ''}
        </Text>
      </Box>

      {/* Detail (optional) */}
      {detail && (
        <Box marginTop={0}>
          <Text color={color} dimColor>
            {detail}
          </Text>
        </Box>
      )}

      {/* Retry hint */}
      {error.retry_suggested && (
        <Box marginTop={0}>
          <Text dimColor>
            {i18n.errorRetryHint}
          </Text>
        </Box>
      )}

      {/* Timestamp */}
      <Box marginTop={0}>
        <Text dimColor>
          {new Date(error.occurred_at).toLocaleTimeString()}
        </Text>
      </Box>
    </Box>
  );
}
