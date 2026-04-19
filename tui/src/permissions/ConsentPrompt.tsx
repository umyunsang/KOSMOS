// SPDX-License-Identifier: Apache-2.0
// Spec 033 T018 — PIPA §15(2) consent prompt Ink component.
//
// Renders 5 required sections (Invariant C1):
//   1. Title — [tool_id] 개인정보 처리 동의
//   2. 목적   — single paragraph
//   3. 항목   — bullet list (one item per line)
//   4. 보유기간 — single line
//   5. 거부권 및 불이익 — refusal right + consequences
//
// Keyboard: Y (동의), N (거부), ESC (취소 = 거부).
// Default focus: 거부 (N) — defensive UI per Invariant UI2.
// Color per mode (from StatusBar color map).
//
// Constraint C1: if any of the 4-tuple fields (purpose, data_items,
// retention_period, refusal_right) is missing the prompt MUST NOT render
// and throws a ValidationError instead.

import React, { useState } from 'react'
import { Box, Text, useInput } from 'ink'
import type { ConsentDecision, PermissionMode } from './types'

// ---------------------------------------------------------------------------
// Validation error
// ---------------------------------------------------------------------------

/** Thrown by validateConsentDecision when PIPA §15(2) 4-tuple is incomplete. */
export class ConsentValidationError extends Error {
  constructor(field: string) {
    super(`PIPA §15(2) violation: required field "${field}" is missing or empty.`)
    this.name = 'ConsentValidationError'
  }
}

/**
 * Enforce PIPA §15(2) 4-tuple completeness (Invariant C1).
 * Throws ConsentValidationError if any required field is absent or empty.
 */
export function validateConsentDecision(decision: ConsentDecision): void {
  if (!decision.purpose || decision.purpose.trim() === '') {
    throw new ConsentValidationError('purpose')
  }
  if (!decision.data_items || decision.data_items.length === 0) {
    throw new ConsentValidationError('data_items')
  }
  if (!decision.retention_period || decision.retention_period.trim() === '') {
    throw new ConsentValidationError('retention_period')
  }
  if (!decision.refusal_right || decision.refusal_right.trim() === '') {
    throw new ConsentValidationError('refusal_right')
  }
}

// ---------------------------------------------------------------------------
// Mode → accent color
// ---------------------------------------------------------------------------

function modeAccentColor(mode: PermissionMode): string {
  switch (mode) {
    case 'plan':              return 'cyan'
    case 'acceptEdits':       return 'green'
    case 'bypassPermissions': return 'red'
    case 'dontAsk':           return 'blueBright'
    case 'default':
    default:                  return 'white'
  }
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface ConsentPromptProps {
  /** The consent decision context to display */
  decision: ConsentDecision
  /** Current permission mode — drives accent color */
  mode: PermissionMode
  /** Called when the citizen accepts (Y) */
  onGranted: () => void
  /** Called when the citizen refuses (N / ESC) */
  onRefused: () => void
  /** Whether this prompt is active / captures input */
  isActive?: boolean
}

// ---------------------------------------------------------------------------
// ConsentPrompt component
// ---------------------------------------------------------------------------

/**
 * PIPA §15(2) full consent prompt.
 *
 * Pre-condition: caller MUST call validateConsentDecision before rendering.
 * This component trusts that the decision passed to it is valid.
 *
 * Invariant UI2 — default focus is "거부 (N)".
 * Invariant C1  — all 5 sections are rendered.
 */
export function ConsentPrompt({
  decision,
  mode,
  onGranted,
  onRefused,
  isActive = true,
}: ConsentPromptProps): React.ReactElement {
  // Focus state: false = focus on 거부 (N) [default], true = focus on 동의 (Y)
  // UI2: default focus is N (refuse)
  const [focusYes, setFocusYes] = useState<boolean>(false)

  const accent = modeAccentColor(mode)

  useInput(
    (input, key) => {
      const ch = input.toLowerCase()
      if (ch === 'y') {
        onGranted()
      } else if (ch === 'n' || key.escape || key.return) {
        // Enter with default focus (N) also refuses (UI2)
        if (ch === 'n' || key.escape) {
          onRefused()
        } else if (key.return) {
          // Enter: execute whichever button is focused
          if (focusYes) {
            onGranted()
          } else {
            onRefused()
          }
        }
      } else if (key.leftArrow || key.rightArrow || key.tab) {
        setFocusYes((prev) => !prev)
      }
    },
    { isActive },
  )

  // Format AAL warning line if applicable
  const showAalWarning =
    decision.auth_level === 'AAL2' || decision.auth_level === 'AAL3'

  return (
    <Box flexDirection="column" borderStyle="round" borderColor={accent} paddingX={1} paddingY={0}>
      {/* Title — section 1 */}
      <Box marginBottom={1}>
        <Text bold color={accent}>
          [{decision.tool_id}] 개인정보 처리 동의
        </Text>
      </Box>

      {/* 목적 — section 2 */}
      <Box marginBottom={1}>
        <Text bold>{'목적: '}</Text>
        <Text>{decision.purpose}</Text>
      </Box>

      {/* 항목 — section 3 */}
      <Box flexDirection="column" marginBottom={1}>
        <Text bold>항목:</Text>
        {decision.data_items.map((item, i) => (
          <Box key={i} paddingLeft={2}>
            <Text>{'• '}{item}</Text>
          </Box>
        ))}
      </Box>

      {/* 보유기간 — section 4 */}
      <Box marginBottom={1}>
        <Text bold>{'보유기간: '}</Text>
        <Text>{decision.retention_period}</Text>
      </Box>

      {/* 거부권 및 불이익 — section 5 */}
      <Box marginBottom={1}>
        <Text bold>{'거부권 및 불이익: '}</Text>
        <Text>{decision.refusal_right}</Text>
      </Box>

      {/* AAL warning (consent-prompt.contract.md §3) */}
      {showAalWarning && (
        <Box marginBottom={1}>
          <Text color="yellow" bold>
            인증 수준: {decision.auth_level} — 추가 본인확인이 필요할 수 있습니다.
          </Text>
        </Box>
      )}

      {/* Action buttons — UI2: default focus = 거부 (N) */}
      <Box>
        <Text
          bold={!focusYes}
          color={!focusYes ? accent : 'gray'}
          underline={!focusYes}
        >
          {'[N] 거부'}
        </Text>
        <Text>{'  '}</Text>
        <Text
          bold={focusYes}
          color={focusYes ? 'green' : 'gray'}
          underline={focusYes}
        >
          {'[Y] 동의'}
        </Text>
        <Text color="gray">{'  (←/→ Tab: 포커스 이동)'}</Text>
      </Box>
    </Box>
  )
}
