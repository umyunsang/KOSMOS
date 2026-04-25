// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — /agents command (FR-026, T055)
//
// Supports two invocation forms:
//   /agents          — default list: proposal-iv 5-state per active ministry
//   /agents --detail — adds SLA-remaining / health / rolling-avg response
//
// The command resolves active AgentVisibilityEntry records from the process-
// level IPC bridge (if available) and renders AgentVisibilityPanel.
//
// T056 and T059 are Lead scope (REPL.tsx wiring + OTEL emission).
// This module exposes a pure command handler callable from the REPL command
// dispatcher without touching REPL.tsx.

import * as React from 'react'
import { Box, Text } from 'ink'
import { AgentVisibilityPanel } from '../components/agents/AgentVisibilityPanel.js'
import type { AgentVisibilityEntryT } from '../schemas/ui-l2/agent.js'
import { AgentVisibilityEntry } from '../schemas/ui-l2/agent.js'
import { emitSurfaceActivation } from '../observability/surface.js'
import { getOrCreateKosmosBridge } from '../ipc/bridgeSingleton.js'

// ---------------------------------------------------------------------------
// Argument parsing
// ---------------------------------------------------------------------------

export interface AgentsCommandArgs {
  detail: boolean
}

/**
 * Parse raw /agents argument string.
 * Accepts: '' | '--detail'
 */
export function parseAgentsArgs(raw: string): AgentsCommandArgs {
  const trimmed = raw.trim()
  return { detail: trimmed === '--detail' || trimmed === '-d' }
}

// ---------------------------------------------------------------------------
// Snapshot resolver
// ---------------------------------------------------------------------------

/**
 * Attempt to build an initial AgentVisibilityEntry snapshot from any cached
 * data the process holds.  In production this will be hydrated from the store
 * or bridge state; in the current phase (P4 UI L2) we return an empty list
 * and rely on the live-subscription inside AgentVisibilityPanel (T057) to
 * populate entries as WorkerStatusFrames arrive.
 *
 * Never throws — returns empty array on any failure.
 */
function resolveInitialEntries(): AgentVisibilityEntryT[] {
  // Future: pull from AppState.workers or store snapshot.
  // For now the panel's subscription will populate on first WorkerStatusFrame.
  return []
}

// ---------------------------------------------------------------------------
// React component rendered by the command dispatcher
// ---------------------------------------------------------------------------

interface AgentsCommandViewProps {
  showDetail: boolean
  onExit?: () => void
}

/**
 * The JSX node rendered when /agents is invoked.
 * Wraps AgentVisibilityPanel with an exit hint footer.
 */
function AgentsCommandView({
  showDetail,
  onExit: _onExit,
}: AgentsCommandViewProps): React.ReactNode {
  // Emit surface activation (FR-037)
  React.useEffect(() => {
    emitSurfaceActivation('agents', { 'kosmos.agents.detail': showDetail })
  }, [showDetail])

  let bridge: ReturnType<typeof getOrCreateKosmosBridge> | undefined
  try {
    bridge = getOrCreateKosmosBridge()
  } catch {
    // Bridge not available (e.g., test environment) — panel shows static snapshot
    bridge = undefined
  }

  const initialEntries = resolveInitialEntries()

  return (
    <Box flexDirection="column">
      <AgentVisibilityPanel
        initialEntries={initialEntries}
        showDetail={showDetail}
        bridge={bridge}
      />
      <Box marginTop={1}>
        <Text color="#5c5c5c" dimColor>
          {showDetail
            ? '  /agents 로 간단 목록 전환 · ESC 종료'
            : '  /agents --detail 로 SLA · 건강 · 응답속도 · ESC 종료'}
        </Text>
      </Box>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Command handler — compatible with the existing command registry pattern
// ---------------------------------------------------------------------------

/**
 * Main entry point for the /agents [--detail] command.
 *
 * Returns a React node (compatible with LocalJSXCommandOnDone pattern used
 * throughout the codebase).  The `raw` parameter is the string after `/agents`.
 */
export function renderAgentsCommand(
  raw: string = '',
  onExit?: () => void,
): React.ReactNode {
  const args = parseAgentsArgs(raw)
  return React.createElement(AgentsCommandView, {
    showDetail: args.detail,
    onExit,
  })
}

/**
 * Validate arguments for the agents command.
 * Returns null on success, an error string on failure.
 */
export function validateAgentsArgs(raw: string): string | null {
  const trimmed = raw.trim()
  if (trimmed === '' || trimmed === '--detail' || trimmed === '-d') return null
  return `Unknown argument: "${trimmed}". Usage: /agents [--detail]`
}
