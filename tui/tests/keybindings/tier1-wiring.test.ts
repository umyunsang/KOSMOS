// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Spec 288 Codex P1 integration regression.
//
// Asserts the bridge between `buildTier1Handlers` and
// `<KeybindingProviderSetup handlerOverrides={...}>`: once the bags are
// passed into the provider, `dispatchAction('Global', <name>)` must exercise
// the real controller (recorded via the injected announcer / probe deps)
// rather than the provider's announce-only default stub.
//
// The test mounts the provider inside `ink-testing-library`'s harness so the
// same `useEffect`-based `registerHandlers` path the runtime uses fires.  It
// does not render a DOM — the integration point is the handler registry
// itself, which `dispatchAction` reads.
//
// In-scope actions:
//   - agent-interrupt      → createAgentInterruptController
//   - session-exit         → buildSessionExitHandler
//   - permission-mode-cycle → buildPermissionModeCycleHandler
//   - history-prev / -next → createHistoryNavigator
//
// Out of scope here (covered by the factory-level suites T027 / T029 / T035):
//   * Exact announcement text, double-press arm window, audit-error recovery.
//   * IME gate / buffer guard for session-exit (see session-exit.test.ts).
//   * Tier-1 cycle ordering proof (see permission-mode-cycle.test.ts).
//
// Scope is deliberately thin — this suite only guards the wiring against a
// regression where the provider's default stubs shadow `handlerOverrides`.

import { afterEach, describe, expect, it } from 'bun:test'
import React from 'react'
import { render } from 'ink-testing-library'
import {
  buildTier1Handlers,
  type Tier1HandlerDeps,
} from '../../src/keybindings/tier1Handlers'
import { KeybindingProviderSetup } from '../../src/keybindings/KeybindingProviderSetup'
import { dispatchAction } from '../../src/keybindings/useKeybinding'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Deterministic announcer — captures every message so a successful
// controller invocation is observable by the test without touching stderr.
// ---------------------------------------------------------------------------

type AnnouncementRecord = Readonly<{
  message: string
  priority: AnnouncementPriority
}>

function makeRecordingAnnouncer(): {
  announcer: AccessibilityAnnouncer
  records: AnnouncementRecord[]
} {
  const records: AnnouncementRecord[] = []
  const announcer: AccessibilityAnnouncer = {
    announce(message, options) {
      records.push({
        message,
        priority: options?.priority ?? 'polite',
      })
    },
  }
  return { announcer, records }
}

// ---------------------------------------------------------------------------
// Dep factory — every probe returns a fresh counter so the test can assert
// the controller actually fired.  No live backend is contacted.
// ---------------------------------------------------------------------------

type Probes = {
  deps: Tier1HandlerDeps
  announcements: AnnouncementRecord[]
  interruptCancellationCalls: number
  interruptAuditCalls: number
  auditFlushCalls: number
  processExitCalls: number[]
  modeSets: string[]
  draftLog: string[]
  confirmExitCalls: number
}

function makeProbes(overrides: Partial<Tier1HandlerDeps> = {}): Probes {
  const { announcer, records } = makeRecordingAnnouncer()
  let interruptCancellationCalls = 0
  let interruptAuditCalls = 0
  let auditFlushCalls = 0
  const processExitCalls: number[] = []
  const modeSets: string[] = []
  const draftLog: string[] = []
  let confirmExitCalls = 0

  const historyEntries = [
    {
      query_text: 'historical-query-1',
      timestamp: new Date(0).toISOString(),
      session_id: 'test-session',
      consent_scope: 'current-session' as const,
    },
    {
      query_text: 'historical-query-2',
      timestamp: new Date(1).toISOString(),
      session_id: 'test-session',
      consent_scope: 'current-session' as const,
    },
  ]

  const deps: Tier1HandlerDeps = {
    sessionId: 'test-session',
    announcer,
    isAgentLoopActive: () => true, // interrupt path — loop-active wins
    currentToolCallId: () => 'tool-call-1',
    isBufferEmpty: () => true,
    getPermissionMode: () => 'default',
    setPermissionMode: (m) => modeSets.push(m),
    hasPendingIrreversibleAction: () => false,
    readDraft: () => '',
    setDraft: (v) => draftLog.push(v),
    getHistory: () => historyEntries,
    memdirUserGranted: false,
    memdirUserAvailable: false,
    // Spec 288 Codex P1 mount fix — `history-search` now threads the open
    // envelope through `setOverlayRequest`.  This test suite is scoped to
    // `agent-interrupt` / `session-exit` / `permission-mode-cycle` /
    // history-prev / history-next so the overlay setter is a no-op; the
    // dedicated `history-search-wiring.test.ts` asserts the mount contract.
    getCurrentDraft: () => '',
    setOverlayRequest: () => {},
    cancellation: {
      async cancelActiveAgentLoop(): Promise<void> {
        interruptCancellationCalls++
      },
    },
    audit: {
      async writeReservedAction(): Promise<void> {
        interruptAuditCalls++
      },
    },
    flushAudit: async () => {
      auditFlushCalls++
    },
    confirmExit: async () => {
      confirmExitCalls++
      return true
    },
    processExit: ((code?: number): never => {
      processExitCalls.push(code ?? 0)
      // Return a never-typed value without actually terminating the runner.
      return undefined as never
    }) as (code?: number) => never,
    ...overrides,
  }

  return {
    deps,
    announcements: records,
    get interruptCancellationCalls() {
      return interruptCancellationCalls
    },
    get interruptAuditCalls() {
      return interruptAuditCalls
    },
    get auditFlushCalls() {
      return auditFlushCalls
    },
    processExitCalls,
    modeSets,
    draftLog,
    get confirmExitCalls() {
      return confirmExitCalls
    },
  } as unknown as Probes
}

// ---------------------------------------------------------------------------
// Harness — mounts the provider with `handlerOverrides` and flushes
// `useEffect` so the registrations land in the module-level registry.
// ---------------------------------------------------------------------------

type Harness = {
  probes: Probes
  unmount: () => void
}

async function mountProvider(
  overrides: Partial<Tier1HandlerDeps> = {},
): Promise<Harness> {
  const probes = makeProbes(overrides)
  const handlerOverrides = buildTier1Handlers(probes.deps)
  const { unmount } = render(
    React.createElement(
      KeybindingProviderSetup,
      {
        handlerOverrides,
        announcer: probes.deps.announcer,
        activeContexts: ['Chat', 'Global'] as const,
        children: null,
      },
      null,
    ),
  )
  // Wait a microtask so the provider's `useEffect` runs and registers the
  // handler bags with the module-level registry that `dispatchAction` reads.
  await Promise.resolve()
  return {
    probes,
    unmount,
  }
}

// ---------------------------------------------------------------------------
// Cleanup — ink-testing-library retains the provider across tests otherwise;
// each test calls `unmount` via the harness return.
// ---------------------------------------------------------------------------

let harnesses: Array<{ unmount: () => void }> = []
afterEach(() => {
  for (const h of harnesses) h.unmount()
  harnesses = []
})

async function mount(
  overrides: Partial<Tier1HandlerDeps> = {},
): Promise<Harness> {
  const h = await mountProvider(overrides)
  harnesses.push({ unmount: h.unmount })
  return h
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Tier 1 wiring — buildTier1Handlers × KeybindingProviderSetup', () => {
  it('dispatches agent-interrupt through the real controller (cancellation + audit fire)', async () => {
    const { probes } = await mount()

    const fired = dispatchAction('Global', 'agent-interrupt')
    expect(fired).toBe(true)

    // The controller is async internally; settle its microtasks so the
    // cancellation and audit promises resolve before asserting.
    await Promise.resolve()
    await Promise.resolve()

    expect(probes.interruptCancellationCalls).toBeGreaterThanOrEqual(1)
    expect(probes.interruptAuditCalls).toBeGreaterThanOrEqual(1)
    // The real controller emits an assertive interrupt notice; the default
    // stub would emit a polite announce-only message.  Presence of any
    // `assertive` record confirms the real path executed.
    const assertive = probes.announcements.find((r) => r.priority === 'assertive')
    expect(assertive).toBeDefined()
  })

  it('dispatches session-exit through the real handler (flush + exit fire)', async () => {
    // Start with an inactive loop so the handler short-circuits the
    // confirm path and goes straight to flush+exit.
    const { probes } = await mount({
      isAgentLoopActive: () => false,
    })

    const fired = dispatchAction('Global', 'session-exit')
    expect(fired).toBe(true)

    // Async handler — let its internal awaits settle.
    await Promise.resolve()
    await Promise.resolve()

    expect(probes.auditFlushCalls).toBeGreaterThanOrEqual(1)
    expect(probes.processExitCalls.length).toBeGreaterThanOrEqual(1)
    expect(probes.processExitCalls[0]).toBe(0)
  })

  it('dispatches permission-mode-cycle through the real handler (setMode fires)', async () => {
    const { probes } = await mount()

    const fired = dispatchAction('Global', 'permission-mode-cycle')
    expect(fired).toBe(true)

    await Promise.resolve()
    await Promise.resolve()

    // Real controller calls setMode with the Tier-1 next mode; the default
    // stub only announces.  Any setMode entry proves the real path ran.
    expect(probes.modeSets.length).toBeGreaterThanOrEqual(1)
    // plan → default → acceptEdits → bypassPermissions → plan;
    // starting from `default` the next mode is `acceptEdits`.
    expect(probes.modeSets[0]).toBe('acceptEdits')
  })

  it('dispatches history-prev through the real navigator (setDraft fires)', async () => {
    const { probes } = await mount()

    const fired = dispatchAction('Chat', 'history-prev')
    expect(fired).toBe(true)

    // Navigator is synchronous — no await required.
    expect(probes.draftLog.length).toBeGreaterThanOrEqual(1)
    // Newest entry loaded first.
    expect(probes.draftLog[0]).toBe('historical-query-2')
  })

  it('dispatches history-next through the real navigator after a prev step', async () => {
    const { probes } = await mount()

    // Prime the cursor with a prev so next has somewhere to return from.
    dispatchAction('Chat', 'history-prev')
    const draftCountBefore = probes.draftLog.length

    const fired = dispatchAction('Chat', 'history-next')
    expect(fired).toBe(true)

    // Navigator writes an empty string back on returned-to-present.
    expect(probes.draftLog.length).toBeGreaterThan(draftCountBefore)
  })
})
