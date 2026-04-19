// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original: input bar component consuming useKoreanIME hook.

import React from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import { useKoreanIME } from '../../hooks/useKoreanIME'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface InputBarProps {
  /**
   * Called when the user presses Enter (and is not mid-composition).
   * Receives the full committed text. The bar clears itself after calling.
   */
  onSubmit: (text: string) => void
  /**
   * When true, all input is suppressed. Intended for use while the permission
   * modal is open (caller decides). Defaults to false.
   */
  disabled?: boolean
}

// ---------------------------------------------------------------------------
// InputBar
// ---------------------------------------------------------------------------

/**
 * Single-row input bar for the KOSMOS TUI conversation view.
 *
 * Renders: `> <committed buffer><in-flight composition>▋`
 *
 * - Delegates all key handling to `useKoreanIME` (FR-015).
 * - Calls `onSubmit` on Enter when no composition is in flight.
 * - `disabled` prop suppresses input (FR-046 — caller-managed modal gate).
 * - Does NOT import the IPC bridge. Emitting `user_input` frames is the
 *   caller's responsibility.
 *
 * FR-015: Hangul composition is handled by the hook; the component only
 * renders what the hook surfaces.
 */
export function InputBar({ onSubmit, disabled = false }: InputBarProps): React.ReactElement {
  const theme = useTheme()
  const ime = useKoreanIME(!disabled)

  // Intercept Enter separately — useKoreanIME's isActive gate already blocks
  // all other input when disabled, but Enter is handled here so we can call
  // onSubmit at the right moment.
  useInput(
    (input, key) => {
      if (key.return && !ime.isComposing) {
        const text = ime.submit()
        if (text.trim().length > 0) {
          onSubmit(text)
        }
      }
    },
    { isActive: !disabled },
  )

  // Render the committed text, the in-flight composition glyph (if any), and
  // a block cursor. The composition glyph uses `theme.suggestion` to
  // visually distinguish it from committed text.
  const compositionGlyph = ime.composition ?? ''

  return (
    <Box>
      <Text bold color={theme.briefLabelYou}>{'> '}</Text>
      <Text color={theme.text}>{ime.buffer}</Text>
      {compositionGlyph.length > 0 && (
        <Text color={theme.suggestion}>{compositionGlyph}</Text>
      )}
      <Text color={theme.inactive}>{'▋'}</Text>
    </Box>
  )
}
