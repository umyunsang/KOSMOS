// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — AgentDetailRow
//
// Source reference: cc:components/CoordinatorAgentStatus.tsx (Claude Code 2.1.88)
// Port of the SLA-remaining / health / rolling-avg-response surface for FR-026.
//
// Displays one row of `/agents --detail` output with:
//   - SLA remaining (seconds countdown or "—" if unknown)
//   - Health indicator: green ● / amber ● / red ●
//   - Rolling-average response time (ms or "—" if no samples yet)

import * as React from 'react'
import { Box, Text } from 'ink'
import type { AgentVisibilityEntryT, AgentHealthT } from '../../schemas/ui-l2/agent.js'
import { dotColorForPrimitive } from '../../schemas/ui-l2/agent.js'

// ── Color map for health states (matches proposal-iv palette) ───────────────
const HEALTH_COLOR: Record<AgentHealthT, string> = {
  green: '#34d399',
  amber: '#fbbf24',
  red: '#f87171',
}

// ── Primitive dot hex (mirrors AgentVisibilityPanel map) ────────────────────
const PRIMITIVE_HEX: Record<string, string> = {
  primitiveLookup: '#60a5fa',
  primitiveSubmit: '#fb923c',
  primitiveVerify: '#f87171',
  primitiveSubscribe: '#34d399',
  primitivePlugin: '#a78bfa',
}

function resolveDotHex(verb: string): string {
  const token = dotColorForPrimitive(verb)
  return PRIMITIVE_HEX[token] ?? '#8a8a8a'
}

// ── Props ────────────────────────────────────────────────────────────────────

export interface AgentDetailRowProps {
  entry: AgentVisibilityEntryT
  /** The primitive verb currently in-flight — determines dot color. */
  currentPrimitive?: string
  /** Column widths for alignment (defaults match ui-d-extensions.mjs widths). */
  colWidths?: {
    ministry: number
    status: number
    sla: number
    health: number
    avg: number
  }
}

/**
 * T054: One agent row in `/agents --detail` output.
 *
 * CC reference: CoordinatorAgentStatus.tsx — task row with status + elapsed.
 * UI-D wireframe: ui-d-extensions.mjs AgentsDetailed rows.
 *
 * Layout:
 *   ⏺ MINISTRY   status      SLA     health_dot  HealthLabel  AvgResp
 */
export function AgentDetailRow({
  entry,
  currentPrimitive = 'lookup',
  colWidths = {
    ministry: 9,
    status: 10,
    sla: 8,
    health: 6,
    avg: 8,
  },
}: AgentDetailRowProps): React.ReactNode {
  const dotHex = resolveDotHex(currentPrimitive)
  const healthColor = HEALTH_COLOR[entry.health]

  // SLA remaining
  const slaDisplay =
    entry.sla_remaining_ms !== null
      ? `${Math.max(0, Math.round(entry.sla_remaining_ms / 1000))}s`
      : '—'

  // Rolling-average response
  const avgDisplay =
    entry.rolling_avg_response_ms !== null
      ? `${Math.round(entry.rolling_avg_response_ms)}ms`
      : '—'

  // Health dot ●
  const healthDot = '●'

  return (
    <Box>
      {/* Primitive-colored leading dot */}
      <Text color={dotHex} bold>{'  ⏺ '}</Text>
      {/* Ministry code */}
      <Text bold>{entry.ministry.padEnd(colWidths.ministry)}</Text>
      {/* State */}
      <Text color="#8a8a8a">{entry.state.padEnd(colWidths.status)}</Text>
      {/* SLA remaining */}
      <Text>{slaDisplay.padEnd(colWidths.sla)}</Text>
      {/* Health dot + label */}
      <Text color={healthColor}>{`${healthDot} `}</Text>
      <Text color={healthColor}>{entry.health.padEnd(colWidths.health)}</Text>
      {/* Rolling-average response */}
      <Text color="#8a8a8a">{avgDisplay}</Text>
    </Box>
  )
}

// ── AgentDetailTable ─────────────────────────────────────────────────────────
// Convenience wrapper that renders a header + multiple AgentDetailRow.

export interface AgentDetailTableProps {
  entries: AgentVisibilityEntryT[]
  primitiveByWorker?: Record<string, string>
}

/**
 * Renders the full `--detail` table: header + one AgentDetailRow per entry.
 * Used by AgentVisibilityPanel when showDetail=true.
 */
export function AgentDetailTable({
  entries,
  primitiveByWorker = {},
}: AgentDetailTableProps): React.ReactNode {
  return (
    <Box flexDirection="column">
      {/* Column header — matches ui-d-extensions.mjs AgentsDetailed header */}
      <Box marginBottom={1}>
        <Text color="#5c5c5c" dimColor bold>
          {'  부처     상태      마지막     평균응답   건강'}
        </Text>
      </Box>
      {entries.map((entry) => (
        <AgentDetailRow
          key={entry.agent_id}
          entry={entry}
          currentPrimitive={primitiveByWorker[entry.agent_id] ?? 'lookup'}
        />
      ))}
    </Box>
  )
}
