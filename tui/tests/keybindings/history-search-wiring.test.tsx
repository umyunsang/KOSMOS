// SPDX-License-Identifier: Apache-2.0
// Spec 288 Codex P1 (line 295) — `history-search` overlay mount wiring.
//
// Context: the pre-fix `history-search` handler called
// `openHistorySearchOverlay(...)` and dropped the returned
// `OverlayOpenRequest`, so ctrl+r only emitted an FR-030 announcement while
// the overlay stayed unmounted.  App-level wiring now threads the envelope
// into a React state slot (`overlayRequest`) and conditionally mounts
// `<HistorySearchOverlay>`.  This suite pins that contract end-to-end
// without rendering the full <App> (which requires a live IPC bridge):
//
//   (1) Baseline — `overlayRequest === null` + no overlay in the frame.
//   (2) Dispatching the `history-search` action flips `overlayRequest`
//       to a non-null envelope and the overlay appears in the frame.
//   (3) Pressing `escape` inside the overlay restores the saved draft
//       byte-for-byte (FR-022) and closes the overlay.
//
// The harness replicates the `App`-level wiring of `tier1Handlers.ts` ×
// `<HistorySearchOverlay>` minus the IPC bridge.  This matches the pattern
// used by `tests/keybindings/tier1-wiring.test.ts` — the integration
// point is the handler registry + conditional mount, not bridge plumbing.

import React, { useMemo, useState } from 'react'
import { afterEach, describe, expect, it } from 'bun:test'
import { render } from 'ink-testing-library'
import { ThemeProvider } from '../../src/theme/provider'
import {
  buildTier1Handlers,
  type Tier1HandlerDeps,
} from '../../src/keybindings/tier1Handlers'
import { KeybindingProviderSetup } from '../../src/keybindings/KeybindingProviderSetup'
import { dispatchAction } from '../../src/keybindings/useKeybinding'
import { HistorySearchOverlay } from '../../src/components/history/HistorySearchOverlay'
import {
  type HistoryEntry,
  type OverlayOpenRequest,
} from '../../src/keybindings/actions/historySearch'
import {
  type AccessibilityAnnouncer,
  type AnnouncementPriority,
} from '../../src/keybindings/types'

// ---------------------------------------------------------------------------
// Async tick — same as HistorySearchOverlay.test.tsx.  Lets Ink drain stdin
// and React 19 flush renders between keystrokes.
// ---------------------------------------------------------------------------

function tick(ms = 20): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// ---------------------------------------------------------------------------
// Recording announcer — captures every announcement so the test can assert
// the overlay-open message fires even when the overlay mount path is
// otherwise invisible to the harness.
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
// Deterministic fixture — two current-session entries, one cross-session
// entry.  Consent starts denied so `scope_notice` is true on the envelope;
// this is incidental to the mount contract but keeps the announcer
// priority assertion informative.
// ---------------------------------------------------------------------------

const SESSION_ID = '01956b00-d4c9-7a1e-9c8b-0b2c3d4e5f60'
const PRIOR_SESSION = '01956a00-aaaa-7a1e-9c8b-0b2c3d4e5f60'

const HISTORY: ReadonlyArray<HistoryEntry> = [
  {
    query_text: '날씨 알려줘',
    timestamp: '2026-04-20T08:00:00Z',
    session_id: SESSION_ID,
    consent_scope: 'current-session',
  },
  {
    query_text: 'entry-current-two',
    timestamp: '2026-04-20T08:01:00Z',
    session_id: SESSION_ID,
    consent_scope: 'current-session',
  },
  {
    query_text: '부산 응급실',
    timestamp: '2026-04-19T23:30:00Z',
    session_id: PRIOR_SESSION,
    consent_scope: 'cross-session',
  },
]

// ---------------------------------------------------------------------------
// Harness — mirrors the App-level wiring from `tui/src/entrypoints/tui.tsx`:
//   * owns the `overlayRequest` state slot,
//   * builds the Tier-1 handlers with `getCurrentDraft` + `setOverlayRequest`,
//   * mounts the provider and registers the handlers,
//   * conditionally renders `<HistorySearchOverlay>` when the envelope is
//     non-null.
//
// The provider is mounted with `activeContexts=['Global']` initially and
// flipped to `['HistorySearch','Global']` while the overlay is open so the
// resolver precedence mirrors production (even though the overlay owns its
// own `useInput` for escape / enter / arrow keys).
// ---------------------------------------------------------------------------

type HarnessProps = Readonly<{
  initialDraft: string
  history: ReadonlyArray<HistoryEntry>
  announcer: AccessibilityAnnouncer
  /** Probe — receives every `setOverlayRequest` value transition. */
  onOverlayRequestChange: (request: OverlayOpenRequest | null) => void
  /** Probe — records the `next_draft` the overlay passes to onCancel. */
  onCancelCapture: (next_draft: string) => void
  /** Probe — records the `next_draft` the overlay passes to onSelect. */
  onSelectCapture: (next_draft: string) => void
}>

function Harness(props: HarnessProps): React.ReactElement {
  const [overlayRequest, setOverlayRequest] =
    useState<OverlayOpenRequest | null>(null)
  // Mirror `tui.tsx` — draft is a local state slot representing the IME buffer.
  // The harness does not exercise IME composition; holding the value in a
  // useState slot keeps it observable via rendered text + readable by
  // `getCurrentDraft`.
  const [draft, setDraft] = useState<string>(props.initialDraft)

  const deps: Tier1HandlerDeps = useMemo(
    () => ({
      sessionId: SESSION_ID,
      announcer: props.announcer,
      isAgentLoopActive: () => false,
      currentToolCallId: () => null,
      isBufferEmpty: () => draft.length === 0,
      getPermissionMode: () => 'default',
      setPermissionMode: () => {},
      hasPendingIrreversibleAction: () => false,
      readDraft: () => draft,
      setDraft: (v) => setDraft(v),
      getHistory: () => props.history,
      memdirUserGranted: false,
      memdirUserAvailable: false,
      // Spec 288 Codex P1 mount contract under test.
      getCurrentDraft: () => draft,
      setOverlayRequest: (req) => {
        setOverlayRequest(req)
        props.onOverlayRequestChange(req)
      },
    }),
    [draft, props],
  )
  const handlers = useMemo(() => buildTier1Handlers(deps), [deps])

  const isOverlayOpen = overlayRequest !== null
  const activeContexts = useMemo(
    () =>
      isOverlayOpen
        ? (['HistorySearch', 'Global'] as const)
        : (['Chat', 'Global'] as const),
    [isOverlayOpen],
  )

  return (
    <KeybindingProviderSetup
      handlerOverrides={handlers}
      announcer={props.announcer}
      activeContexts={activeContexts}
    >
      {overlayRequest !== null && (
        <HistorySearchOverlay
          request={overlayRequest}
          announcer={props.announcer}
          onSelect={(next) => {
            props.onSelectCapture(next)
            setOverlayRequest(null)
            props.onOverlayRequestChange(null)
          }}
          onCancel={(next) => {
            // FR-022 — overlay passes `request.saved_draft` verbatim.
            // Restoring to the UI state slot keeps the harness parallel
            // with the production `ime.setBuffer` wiring that Team κ is
            // landing separately.
            setDraft(next)
            props.onCancelCapture(next)
            setOverlayRequest(null)
            props.onOverlayRequestChange(null)
          }}
        />
      )}
    </KeybindingProviderSetup>
  )
}

// ---------------------------------------------------------------------------
// Cleanup — ink-testing-library retains the provider between tests unless
// the harness is torn down.  Each `mount()` tracks its unmount and
// `afterEach` flushes them.
// ---------------------------------------------------------------------------

let mounted: Array<{ unmount: () => void }> = []
afterEach(() => {
  for (const m of mounted) m.unmount()
  mounted = []
})

type MountResult = Readonly<{
  render: ReturnType<typeof render>
  announcements: AnnouncementRecord[]
  overlayRequestHistory: Array<OverlayOpenRequest | null>
  cancelCaptures: string[]
  selectCaptures: string[]
}>

function mount(
  initialDraft: string,
  history: ReadonlyArray<HistoryEntry> = HISTORY,
): MountResult {
  const { announcer, records } = makeRecordingAnnouncer()
  const overlayRequestHistory: Array<OverlayOpenRequest | null> = []
  const cancelCaptures: string[] = []
  const selectCaptures: string[] = []
  const tree = render(
    <ThemeProvider>
      <Harness
        initialDraft={initialDraft}
        history={history}
        announcer={announcer}
        onOverlayRequestChange={(r) => overlayRequestHistory.push(r)}
        onCancelCapture={(s) => cancelCaptures.push(s)}
        onSelectCapture={(s) => selectCaptures.push(s)}
      />
    </ThemeProvider>,
  )
  mounted.push({ unmount: tree.unmount })
  return {
    render: tree,
    announcements: records,
    overlayRequestHistory,
    cancelCaptures,
    selectCaptures,
  }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('Spec 288 Codex P1 — history-search overlay mount wiring', () => {
  it('starts with overlayRequest === null and no overlay in the frame', async () => {
    const harness = mount('초안 텍스트')
    // Let the provider's `useEffect` flush and register handlers.
    await tick()

    expect(harness.overlayRequestHistory.length).toBe(0)
    const frame = harness.render.lastFrame() ?? ''
    // The overlay's header (`이력 검색 / History search`) is the signature
    // string a mounted overlay emits.  Its absence in the baseline frame
    // proves nothing is rendered before dispatch.
    expect(frame).not.toContain('이력 검색 / History search')
  })

  it('dispatching history-search flips overlayRequest non-null and mounts the overlay', async () => {
    const harness = mount('초안 텍스트')
    await tick()

    const fired = dispatchAction('Global', 'history-search')
    expect(fired).toBe(true)

    // React 19 batches the setState — flush the reconciler.
    await tick()

    // The handler fed the envelope to setOverlayRequest exactly once;
    // `overlayRequestHistory` captures every transition.
    expect(harness.overlayRequestHistory.length).toBe(1)
    const request = harness.overlayRequestHistory[0]
    if (request === null || request === undefined) {
      throw new Error('setOverlayRequest never received a non-null envelope')
    }
    // FR-022 seed — saved_draft is the current draft at dispatch time,
    // byte-for-byte.
    expect(request.saved_draft).toBe('초안 텍스트')
    // FR-021 — consent was denied in the fixture, so cross-session entries
    // are filtered out of visible_entries.
    expect(request.visible_entries.length).toBe(2)
    expect(request.scope_notice).toBe(true)

    // The overlay is now in the rendered tree.
    const frame = harness.render.lastFrame() ?? ''
    expect(frame).toContain('이력 검색 / History search')
  })

  it('escape inside the overlay restores the saved draft byte-for-byte (FR-022) and closes the overlay', async () => {
    // Mix Korean + emoji + combining mark to catch any naive truncation in
    // the saved-draft round-trip.
    const DRAFT = '오늘 날씨 어때?  ☀️ 🌧️  Café'
    const harness = mount(DRAFT)
    await tick()

    // Open the overlay.
    dispatchAction('Global', 'history-search')
    await tick()
    expect(harness.overlayRequestHistory.length).toBe(1)
    expect(harness.render.lastFrame() ?? '').toContain(
      '이력 검색 / History search',
    )

    // Press escape — the overlay's own `useInput` handles it via
    // `cancelHistorySearch(request, announcer)` and invokes `onCancel(
    // next_draft)` where `next_draft === request.saved_draft`.
    harness.render.stdin.write('\u001B')
    await tick()

    // Overlay closed: the harness recorded a null transition after the
    // initial non-null, and the overlay header is gone from the frame.
    expect(harness.overlayRequestHistory.length).toBe(2)
    expect(harness.overlayRequestHistory[1]).toBe(null)
    const finalFrame = harness.render.lastFrame() ?? ''
    expect(finalFrame).not.toContain('이력 검색 / History search')

    // FR-022 — byte-for-byte saved-draft restoration.  The overlay handed
    // `next_draft === DRAFT` to onCancel.
    expect(harness.cancelCaptures.length).toBe(1)
    expect(harness.cancelCaptures[0]).toBe(DRAFT)
    // UTF-8 byte-level equality — stronger than `===` because it catches
    // any accidental NFC/NFD normalisation introduced on the path.
    const enc = new TextEncoder()
    expect(Array.from(enc.encode(harness.cancelCaptures[0] ?? ''))).toEqual(
      Array.from(enc.encode(DRAFT)),
    )
  })

  it('the empty-draft case round-trips as an empty string (no spurious mutation)', async () => {
    const harness = mount('')
    await tick()

    dispatchAction('Global', 'history-search')
    await tick()
    expect(harness.overlayRequestHistory.length).toBe(1)
    expect(harness.overlayRequestHistory[0]?.saved_draft).toBe('')

    harness.render.stdin.write('\u001B')
    await tick()
    expect(harness.cancelCaptures[0]).toBe('')
    expect(harness.overlayRequestHistory[1]).toBe(null)
  })
})
