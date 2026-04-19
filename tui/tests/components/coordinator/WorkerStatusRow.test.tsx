// T090 — WorkerStatusRow component tests
// Asserts role_id label + current_primitive + status badge render correctly.
// Tests spinner (running) and check mark (idle) completion indicators.
// FR-044 (per-worker status row), US4 scenario 2.

import { describe, expect, it, beforeEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { WorkerStatusRow } from '../../../src/components/coordinator/WorkerStatusRow'
import { ThemeProvider } from '../../../src/theme/provider'
import { dispatchSessionAction, sessionStore } from '../../../src/store/session-store'
import type { WorkerStatus } from '../../../src/store/session-store'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const WORKER_RUNNING: WorkerStatus = {
  worker_id: 'worker-001',
  role_id: 'transport-specialist',
  current_primitive: 'lookup',
  status: 'running',
}

const WORKER_IDLE: WorkerStatus = {
  worker_id: 'worker-002',
  role_id: 'health-specialist',
  current_primitive: 'resolve_location',
  status: 'idle',
}

const WORKER_ERROR: WorkerStatus = {
  worker_id: 'worker-003',
  role_id: 'emergency-specialist',
  current_primitive: 'verify',
  status: 'error',
}

const WORKER_WAITING: WorkerStatus = {
  worker_id: 'worker-004',
  role_id: 'transport-specialist',
  current_primitive: 'submit',
  status: 'waiting_permission',
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resetStore() {
  sessionStore.dispatch({ type: 'SESSION_EVENT', event: 'new', payload: {} })
}

function Harness({ workerId }: { workerId: string }) {
  return (
    <ThemeProvider>
      <WorkerStatusRow workerId={workerId} />
    </ThemeProvider>
  )
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  resetStore()
})

describe('WorkerStatusRow — missing worker', () => {
  it('renders nothing when worker is not in the store', () => {
    const { lastFrame } = render(<Harness workerId="nonexistent" />)
    expect((lastFrame() ?? '').trim()).toBe('')
  })
})

describe('WorkerStatusRow — running worker', () => {
  it('renders role_id label', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_RUNNING })
    const { lastFrame } = render(<Harness workerId="worker-001" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('transport-specialist')
  })

  it('renders current_primitive', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_RUNNING })
    const { lastFrame } = render(<Harness workerId="worker-001" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('lookup')
  })

  it('renders running status badge', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_RUNNING })
    const { lastFrame } = render(<Harness workerId="worker-001" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('[running]')
  })
})

describe('WorkerStatusRow — idle (completed) worker', () => {
  it('renders role_id and current_primitive', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_IDLE })
    const { lastFrame } = render(<Harness workerId="worker-002" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('health-specialist')
    expect(frame).toContain('resolve_location')
  })

  it('renders check mark glyph when idle (complete indicator)', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_IDLE })
    const { lastFrame } = render(<Harness workerId="worker-002" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('✓')
  })

  it('renders idle status badge', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_IDLE })
    const { lastFrame } = render(<Harness workerId="worker-002" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('[idle]')
  })
})

describe('WorkerStatusRow — error worker', () => {
  it('renders error glyph and status badge', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_ERROR })
    const { lastFrame } = render(<Harness workerId="worker-003" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('emergency-specialist')
    expect(frame).toContain('[error]')
    expect(frame).toContain('✗')
  })
})

describe('WorkerStatusRow — waiting_permission worker', () => {
  it('renders waiting status badge and question mark glyph', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_WAITING })
    const { lastFrame } = render(<Harness workerId="worker-004" />)
    const frame = lastFrame() ?? ''
    expect(frame).toContain('[waiting]')
    expect(frame).toContain('?')
    expect(frame).toContain('submit')
  })
})

describe('WorkerStatusRow — independent updates', () => {
  it('two workers update independently without interfering', () => {
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_RUNNING })
    dispatchSessionAction({ type: 'WORKER_STATUS', status: WORKER_IDLE })
    const { lastFrame: frameA } = render(<Harness workerId="worker-001" />)
    const { lastFrame: frameB } = render(<Harness workerId="worker-002" />)
    expect(frameA() ?? '').toContain('transport-specialist')
    expect(frameB() ?? '').toContain('health-specialist')
    // Each only shows its own worker
    expect(frameA() ?? '').not.toContain('health-specialist')
    expect(frameB() ?? '').not.toContain('transport-specialist')
  })
})
