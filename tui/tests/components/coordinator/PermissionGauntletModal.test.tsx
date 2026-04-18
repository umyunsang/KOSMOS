/**
 * Component tests for PermissionGauntletModal.
 *
 * Covers:
 *   - Renders when pending_permission is set in the store (FR-045)
 *   - Does NOT render when pending_permission is null
 *   - Blocks all input while modal is open (keystrokes do not emit user_input)
 *   - y key → emits permission_response with decision: 'granted' + correct request_id (FR-046)
 *   - n key → emits permission_response with decision: 'denied' + correct request_id (FR-046)
 *
 * DI pattern: sendFrame is provided as a spy prop; bridge is never imported.
 */
import { describe, test, expect, mock, beforeEach } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import { ThemeProvider } from '@/theme/provider'
import { PermissionGauntletModal } from '@/components/coordinator/PermissionGauntletModal'
import { dispatchSessionAction, sessionStore } from '@/store/session-store'
import type { PermissionRequest } from '@/store/session-store'
import type { PermissionResponseFrame } from '@/ipc/frames.generated'

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const SESSION_ID = 'test-session-01'

const MOCK_REQUEST: PermissionRequest = {
  request_id: 'req-001',
  worker_id: 'transport-worker-1',
  primitive_kind: 'lookup',
  description_ko: '교통 정보를 조회하려 합니다',
  description_en: 'Looking up transport information',
  risk_level: 'medium',
}

function wrap(sendFrame: (f: PermissionResponseFrame) => void): React.ReactElement {
  return (
    <ThemeProvider>
      <PermissionGauntletModal sendFrame={sendFrame} sessionId={SESSION_ID} />
    </ThemeProvider>
  )
}

// Reset store before each test
beforeEach(() => {
  dispatchSessionAction({ type: 'PERMISSION_RESPONSE' }) // clear any leftover
})

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('PermissionGauntletModal', () => {
  test('renders nothing when pending_permission is null', () => {
    // Store starts with pending_permission: null (reset above)
    const spy = mock(() => {})
    const { lastFrame } = render(wrap(spy))
    const frame = lastFrame() ?? ''
    // No permission title should appear
    expect(frame).not.toContain('필요합니다')
    expect(spy).not.toHaveBeenCalled()
  })

  test('renders modal when pending_permission is set in store', () => {
    dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: MOCK_REQUEST })
    const spy = mock(() => {})
    const { lastFrame } = render(wrap(spy))
    const frame = lastFrame() ?? ''
    // Korean description must be visible
    expect(frame).toContain(MOCK_REQUEST.description_ko)
    // English description must be visible
    expect(frame).toContain(MOCK_REQUEST.description_en)
    // Risk level badge must be visible
    expect(frame).toContain('MEDIUM')
    // Worker ID must be visible
    expect(frame).toContain(MOCK_REQUEST.worker_id)
  })

  test('y key emits permission_response: granted with correct request_id', () => {
    dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: MOCK_REQUEST })
    const spy = mock((_f: PermissionResponseFrame) => {})
    const { stdin } = render(wrap(spy))
    stdin.write('y')
    expect(spy).toHaveBeenCalledTimes(1)
    const emitted = (spy.mock.calls[0] as [PermissionResponseFrame])[0]
    expect(emitted.kind).toBe('permission_response')
    expect(emitted.request_id).toBe(MOCK_REQUEST.request_id)
    expect(emitted.decision).toBe('granted')
    expect(emitted.session_id).toBe(SESSION_ID)
  })

  test('n key emits permission_response: denied with correct request_id', () => {
    dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: MOCK_REQUEST })
    const spy = mock((_f: PermissionResponseFrame) => {})
    const { stdin } = render(wrap(spy))
    stdin.write('n')
    expect(spy).toHaveBeenCalledTimes(1)
    const emitted = (spy.mock.calls[0] as [PermissionResponseFrame])[0]
    expect(emitted.kind).toBe('permission_response')
    expect(emitted.request_id).toBe(MOCK_REQUEST.request_id)
    expect(emitted.decision).toBe('denied')
    expect(emitted.session_id).toBe(SESSION_ID)
  })

  test('blocks arbitrary keystrokes while modal is open (no user_input frame emitted)', () => {
    // Seed a pending permission so modal is mounted
    dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: MOCK_REQUEST })
    const spy = mock(() => {})
    // Simulate non-y/n keystrokes; spy should never be called
    const { stdin } = render(wrap(spy))
    stdin.write('a')
    stdin.write('b')
    stdin.write('z')
    // The modal swallows all input — sendFrame spy should NOT be invoked
    expect(spy).not.toHaveBeenCalled()
    // Store should still have the pending request (not cleared)
    const snapshot = sessionStore.getState()
    expect(snapshot.pending_permission).not.toBeNull()
    expect(snapshot.pending_permission?.request_id).toBe(MOCK_REQUEST.request_id)
  })

  test('store pending_permission is cleared after grant', () => {
    dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: MOCK_REQUEST })
    const spy = mock((_f: PermissionResponseFrame) => {})
    const { stdin } = render(wrap(spy))
    stdin.write('y')
    const snapshot = sessionStore.getState()
    expect(snapshot.pending_permission).toBeNull()
  })

  test('store pending_permission is cleared after deny', () => {
    dispatchSessionAction({ type: 'PERMISSION_REQUEST', request: MOCK_REQUEST })
    const spy = mock((_f: PermissionResponseFrame) => {})
    const { stdin } = render(wrap(spy))
    stdin.write('n')
    const snapshot = sessionStore.getState()
    expect(snapshot.pending_permission).toBeNull()
  })
})
