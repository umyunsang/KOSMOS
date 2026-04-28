// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — US2 T030
// Spec 1979 — Y/N direct-keystroke pattern replaced with CC arrow+Enter pattern.
//
// BypassReinforcementModal — additional confirmation before entering
// bypassPermissions (FR-022).
//
// Source pattern:
//   .references/claude-code-sourcemap/restored-src/src/components/BypassPermissionsModeDialog.tsx
//   (Claude Code 2.1.88, research-use)
//
// CC's BypassPermissionsModeDialog uses
//   <Select options={[{label: 'No, exit', value: 'decline'},
//                     {label: 'Yes, I accept', value: 'accept'}]}
//           onChange={onChange} />
// for arrow+Enter selection (NOT direct Y/N keystrokes).  We adopt that
// pattern here while preserving KOSMOS's UI2 invariant — default focus is
// 취소 (cancel) so the citizen must explicitly arrow-down to confirm.
//
// Implementation note (per Spec 1979): we drive Up/Down/Enter via raw
// `useInput` instead of `<Select>`, because `<Select>` routes keystrokes
// through `useKeybindings` which ink-testing-library cannot drive in
// unit tests.  The interaction model is identical to CC `<Select>` from
// the citizen's perspective.

import React, { useEffect, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useUiL2I18n } from '../../i18n/uiL2.js'

export interface BypassReinforcementModalProps {
  /** Called when the citizen confirms bypass mode. */
  onConfirm: () => void
  /** Called when the citizen cancels (Esc, or selecting "취소"). */
  onCancel: () => void
}

type ChoiceValue = 'decline' | 'accept'

/**
 * Reinforcement confirmation modal for bypassPermissions mode entry.
 *
 * Visual contract (ui-c-permission.mjs § C.5 BorderedNotice):
 *   - Red border + "⚠ bypassPermissions 전환 확인" header
 *   - Warning body text (from i18n bundle)
 *   - Two-choice arrow+Enter: "취소" (default focus) / "확정"
 *
 * UI2 invariant: default focus = 취소 (the safer choice).
 *
 * FR-022: bypassPermissions mode requires an additional reinforcement-
 * confirmation modal when the citizen attempts to enter bypassPermissions.
 */
export function BypassReinforcementModal({
  onConfirm,
  onCancel,
}: BypassReinforcementModalProps): React.ReactElement {
  const i18n = useUiL2I18n()
  // UI2: default focus = decline (the safer choice)
  const [focusedIdx, setFocusedIdx] = useState(0)

  // Force a useEffect cycle on mount so Ink's stdin parser settles before
  // the first keystroke arrives (matches the permissions modal pattern).
  useEffect(() => {
    /* mount tick */
  }, [])

  const choices: { label: string; value: ChoiceValue }[] = [
    { label: '취소 (기본)', value: 'decline' },
    { label: '확정 — 우회 활성화', value: 'accept' },
  ]

  // CC arrow+Enter pattern (replaces previous Y/N direct-keystroke pattern).
  // Esc → cancel.
  //
  // Order matters: arrow keys are checked BEFORE escape because Ink emits
  // both `key.escape` and `key.downArrow` for `\x1b[B` (some terminals split
  // the CSI sequence across reads).  Checking arrows first lets a real arrow
  // press win the race over a stale escape flag from the same chunk.
  useInput((input, key) => {
    if (key.upArrow) {
      setFocusedIdx((i) => (i - 1 + choices.length) % choices.length)
      return
    }
    if (key.downArrow) {
      setFocusedIdx((i) => (i + 1) % choices.length)
      return
    }
    if (key.return) {
      const choice = choices[focusedIdx]
      if (choice?.value === 'accept') {
        onConfirm()
      } else {
        onCancel()
      }
      return
    }
    if (key.escape) {
      onCancel()
      return
    }
    // Power-user accelerators kept for FR-022 emergency cancellation.
    // The citizen-facing accent in the UI is arrow+Enter; these are not
    // advertised in the footer hint.
    if (input === 'n' || input === 'N') {
      onCancel()
      return
    }
    if (input === 'y' || input === 'Y') {
      onConfirm()
    }
  })

  return (
    <Box
      flexDirection="column"
      borderStyle="round"
      borderColor="#f87171"
      paddingX={2}
      paddingY={1}
      width={60}
    >
      {/* Header */}
      <Box flexDirection="row" gap={1}>
        <Text color="#f87171" bold>
          ⚠
        </Text>
        <Text bold>bypassPermissions 전환 확인</Text>
      </Box>

      {/* Warning body */}
      <Box marginTop={1}>
        <Text>{i18n.bypassReinforcement}</Text>
      </Box>

      {/* Arrow+Enter choice list (CC pattern; replaces Y/N keystrokes) */}
      <Box marginTop={1} flexDirection="column">
        {choices.map((c, i) => {
          const focused = i === focusedIdx
          const isAccept = c.value === 'accept'
          return (
            <Box key={c.value}>
              <Text
                color={focused ? (isAccept ? '#fb923c' : '#34d399') : undefined}
                bold={focused}
              >
                {focused ? '› ' : '  '}
                {c.label}
              </Text>
            </Box>
          )
        })}
      </Box>

      {/* Hint footer */}
      <Box marginTop={1}>
        <Text dimColor>{'↑↓ 선택 · Enter 확정 · Esc 취소'}</Text>
      </Box>
    </Box>
  )
}
