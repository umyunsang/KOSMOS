// SPDX-License-Identifier: Apache-2.0
// Spec 033 T039 — `/permissions list` rule list view.
//
// Renders current permission rules in an Ink table-style layout.
// Shows: tool_id | scope | decision | created_at.

import React from 'react'
import { Box, Text } from 'ink'
import type { PermissionRule, RuleDecision } from './types'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Map rule decision to a colored label */
function decisionLabel(decision: RuleDecision): { text: string; color: string } {
  switch (decision) {
    case 'allow': return { text: 'allow', color: 'green' }
    case 'deny':  return { text: 'deny',  color: 'red' }
    case 'ask':   return { text: 'ask',   color: 'yellow' }
  }
}

/** Truncate a string to maxLen, appending '…' if needed */
function truncate(s: string, maxLen: number): string {
  if (s.length <= maxLen) return s
  return s.slice(0, maxLen - 1) + '…'
}

/** Format ISO 8601 datetime to a readable short form */
function formatDate(iso: string): string {
  try {
    const d = new Date(iso)
    // Format: YYYY-MM-DD HH:MM
    const pad = (n: number): string => n.toString().padStart(2, '0')
    return (
      `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ` +
      `${pad(d.getHours())}:${pad(d.getMinutes())}`
    )
  } catch {
    return iso
  }
}

// ---------------------------------------------------------------------------
// Column widths (fixed for alignment)
// ---------------------------------------------------------------------------

const COL_TOOL_ID = 30
const COL_SCOPE = 9
const COL_DECISION = 8
const COL_CREATED = 17

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface RuleListViewProps {
  /** Rules to display (from session state or CLI fetch) */
  rules: PermissionRule[]
}

// ---------------------------------------------------------------------------
// RuleListView component
// ---------------------------------------------------------------------------

/**
 * Ink table-style renderer for permission rules.
 * Used by the `/permissions list` command output.
 */
export function RuleListView({ rules }: RuleListViewProps): React.ReactElement {
  if (rules.length === 0) {
    return (
      <Box>
        <Text color="gray">규칙이 없습니다. 어댑터 호출 시 동의 프롬프트가 표시됩니다.</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column">
      {/* Header row */}
      <Box>
        <Box width={COL_TOOL_ID + 2}>
          <Text bold color="white">{'tool_id'}</Text>
        </Box>
        <Box width={COL_SCOPE + 2}>
          <Text bold color="white">{'scope'}</Text>
        </Box>
        <Box width={COL_DECISION + 2}>
          <Text bold color="white">{'decision'}</Text>
        </Box>
        <Box width={COL_CREATED + 2}>
          <Text bold color="white">{'created_at'}</Text>
        </Box>
      </Box>

      {/* Separator */}
      <Box>
        <Text color="gray">
          {'─'.repeat(COL_TOOL_ID + COL_SCOPE + COL_DECISION + COL_CREATED + 8)}
        </Text>
      </Box>

      {/* Data rows */}
      {rules.map((rule, i) => {
        const { text: decText, color: decColor } = decisionLabel(rule.decision)
        return (
          <Box key={`${rule.tool_id}-${rule.scope}-${i}`}>
            <Box width={COL_TOOL_ID + 2}>
              <Text>{truncate(rule.tool_id, COL_TOOL_ID)}</Text>
            </Box>
            <Box width={COL_SCOPE + 2}>
              <Text color="cyan">{rule.scope}</Text>
            </Box>
            <Box width={COL_DECISION + 2}>
              <Text color={decColor} bold>{decText}</Text>
            </Box>
            <Box width={COL_CREATED + 2}>
              <Text color="gray">{formatDate(rule.created_at)}</Text>
            </Box>
          </Box>
        )
      })}

      {/* Footer */}
      <Box marginTop={1}>
        <Text color="gray">
          총 {rules.length}개 규칙. `/permissions edit [tool_id]`로 수정 가능.
        </Text>
      </Box>
    </Box>
  )
}
