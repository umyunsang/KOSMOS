// Source: .references/claude-code-sourcemap/restored-src/src/components/CoordinatorAgentStatus.tsx (Claude Code 2.1.88, research-use)
// Source: .references/claude-code-sourcemap/restored-src/src/components/AgentProgressLine.tsx (Claude Code 2.1.88, research-use)
// KOSMOS adaptation: renders a single WorkerStatus row from session-store.
//
// FR-044 (per-worker status row), FR-050 (selector-isolated subscription).
// US4 scenario 2.

import React from 'react'
import { Box, Text } from 'ink'
import { useSessionStore } from '../../store/session-store'
import type { WorkerStatus } from '../../store/session-store'
import { useTheme } from '../../theme/provider'

// ---------------------------------------------------------------------------
// Spinner frames for running state (lifted from AgentProgressLine pattern)
// ---------------------------------------------------------------------------

const SPINNER_FRAMES = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏'] as const

/** Returns a spinner glyph deterministically from a counter; safe for tests. */
function spinnerFrame(tick: number): string {
  return SPINNER_FRAMES[tick % SPINNER_FRAMES.length] ?? '⠋'
}

// ---------------------------------------------------------------------------
// Status badge helpers
// ---------------------------------------------------------------------------

type WorkerStatusKind = WorkerStatus['status']

const STATUS_LABEL: Record<WorkerStatusKind, string> = {
  idle: 'idle',
  running: 'running',
  waiting_permission: 'waiting',
  error: 'error',
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface WorkerStatusRowProps {
  workerId: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * Renders a single worker status row.
 *
 * Layout:
 *   <glyph> <role_id>  <current_primitive>  [status]
 *
 * Subscribes exclusively to its own worker slot via selector isolation
 * (FR-050) — does NOT re-render on phase or other worker state changes.
 *
 * Returns null when the worker is not found in the store.
 */
export function WorkerStatusRow({ workerId }: WorkerStatusRowProps): React.ReactElement | null {
  const theme = useTheme()

  // Selector-isolated: only re-renders when this specific worker changes.
  const worker: WorkerStatus | undefined = useSessionStore(
    (s) => s.workers.get(workerId),
  )

  // Stable spinner tick sourced from a local state counter.
  const [tick, setTick] = React.useState(0)

  React.useEffect(() => {
    if (worker?.status !== 'running') return
    const id = setInterval(() => setTick((t) => t + 1), 100)
    return () => clearInterval(id)
  }, [worker?.status])

  if (!worker) return null

  const isRunning = worker.status === 'running'
  const isDone = worker.status === 'idle'
  const isError = worker.status === 'error'
  const isWaiting = worker.status === 'waiting_permission'

  const glyph = isRunning
    ? spinnerFrame(tick)
    : isDone
      ? '✓'
      : isError
        ? '✗'
        : isWaiting
          ? '?'
          : '○'

  const glyphColor = isRunning
    ? theme.orbitalRing
    : isDone
      ? theme.success
      : isError
        ? theme.error
        : isWaiting
          ? theme.warning
          : theme.inactive

  const statusLabel = STATUS_LABEL[worker.status]

  const statusColor = isRunning
    ? theme.orbitalRing
    : isDone
      ? theme.success
      : isError
        ? theme.error
        : isWaiting
          ? theme.warning
          : theme.inactive

  return (
    <Box flexDirection="row" marginBottom={0}>
      {/* Spinner / completion glyph */}
      <Text color={glyphColor}>{`${glyph} `}</Text>

      {/* Role label */}
      <Text bold color={theme.text}>{worker.role_id}</Text>

      {/* Primitive currently executing */}
      <Text color={theme.subtle}>{`  ${worker.current_primitive}`}</Text>

      {/* Status badge */}
      <Text color={statusColor}>{`  [${statusLabel}]`}</Text>
    </Box>
  )
}
