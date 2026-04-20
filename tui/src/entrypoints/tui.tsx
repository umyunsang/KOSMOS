// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original skeleton — wires createBridge() + useSessionStore +
// <StreamingMessage> + <CrashNotice> + commands dispatcher (T050) +
// PrimitiveDispatcher (T087 is hooked one level deeper in MessageList).
//
// Design:
//   - createBridge() spawns the Python backend (or KOSMOS_BACKEND_CMD override).
//   - The frame consumer loop dispatches every inbound IPCFrame to the session
//     store via dispatchSessionAction().
//   - SIGTERM / Ctrl-C triggers bridge.close() with ≤3 s SIGTERM → SIGKILL
//     (FR-009).
//   - This component is the root App; it is rendered by tui/src/main.tsx under
//     <ThemeProvider> (T052).
//
// Input handling:
//   - A minimal ASCII input buffer lives here; proper Korean IME is Phase 7 US5.
//   - On Enter: slash-prefixed input is intercepted by dispatchCommand(); all
//     other input is emitted as a user_input IPC frame (T050, FR-038, FR-042).

import React, { useEffect, useMemo, useRef, useState } from 'react'
import { Box, Text, useApp, useInput } from 'ink'
import { useTheme } from '../theme/provider'
import { useSessionStore, dispatchSessionAction } from '../store/session-store'
import { MessageList } from '../components/conversation/MessageList'
import { CrashNotice } from '../components/CrashNotice'
import { createBridge } from '../ipc/bridge'
import type { IPCBridge } from '../ipc/bridge'
import type {
  IPCFrame,
  UserInputFrame,
  SessionEventFrame,
  PermissionResponseFrame,
} from '../ipc/frames.generated'
import { useI18n } from '../i18n'
import {
  buildDefaultRegistry,
  dispatchCommand,
  isSlashCommand,
  listCommands,
} from '../commands'
import type { DispatchResult } from '../commands'
import type { CommandDefinition } from '../commands/types'
import { HelpView } from '../commands/help'
import { PhaseIndicator } from '../components/coordinator/PhaseIndicator'
import { WorkerStatusRow } from '../components/coordinator/WorkerStatusRow'
import { PermissionGauntletModal } from '../components/coordinator/PermissionGauntletModal'
import { InputBar } from '../components/input/InputBar'
import { handleNotificationFrame } from '../permissions/consentBridge'
import {
  Onboarding,
  resolveStartStep,
  CURRENT_CONSENT_VERSION,
  CURRENT_SCOPE_VERSION,
} from '../components/onboarding/Onboarding'
import { latestConsentRecord, latestScopeRecord } from '../memdir/io'
import { useKoreanIME, type KoreanIMEState } from '../hooks/useKoreanIME'
import { KeybindingProviderSetup } from '../keybindings/KeybindingProviderSetup'
import type { KeybindingContext as KeybindingContextEnum } from '../keybindings/types'
import { buildTier1Handlers } from '../keybindings/tier1Handlers'
import type { HistoryNavigationEntry } from '../keybindings/actions/historyNavigate'
import type { PermissionMode } from '../permissions/types'
import { createAccessibilityAnnouncer } from '../keybindings/accessibilityAnnouncer'

// ---------------------------------------------------------------------------
// Frame dispatcher — maps IPCFrame arms to SessionAction
// ---------------------------------------------------------------------------

function dispatchFrame(frame: IPCFrame): void {
  switch (frame.kind) {
    case 'user_input':
      // Inbound user_input from backend echo — store as message
      dispatchSessionAction({
        type: 'USER_INPUT',
        message_id: `user-${frame.ts}`,
        text: frame.text,
      })
      break

    case 'assistant_chunk':
      dispatchSessionAction({
        type: 'ASSISTANT_CHUNK',
        message_id: frame.message_id,
        delta: frame.delta,
        done: frame.done,
      })
      break

    case 'tool_call':
      dispatchSessionAction({
        type: 'TOOL_CALL',
        message_id: `msg-${frame.call_id}`,
        tool_call: {
          call_id: frame.call_id,
          name: frame.name,
          arguments: frame.arguments as Record<string, unknown>,
        },
      })
      break

    case 'tool_result':
      dispatchSessionAction({
        type: 'TOOL_RESULT',
        call_id: frame.call_id,
        envelope: frame.envelope as Record<string, unknown>,
      })
      break

    case 'coordinator_phase':
      dispatchSessionAction({
        type: 'COORDINATOR_PHASE',
        phase: frame.phase,
      })
      break

    case 'worker_status':
      dispatchSessionAction({
        type: 'WORKER_STATUS',
        status: {
          worker_id: frame.worker_id,
          role_id: frame.role_id,
          current_primitive: frame.current_primitive,
          status: frame.status,
        },
      })
      break

    case 'permission_request':
      dispatchSessionAction({
        type: 'PERMISSION_REQUEST',
        request: {
          request_id: frame.request_id,
          correlation_id: frame.correlation_id,
          worker_id: frame.worker_id,
          primitive_kind: frame.primitive_kind,
          description_ko: frame.description_ko,
          description_en: frame.description_en,
          risk_level: frame.risk_level,
        },
      })
      break

    case 'permission_response':
      dispatchSessionAction({ type: 'PERMISSION_RESPONSE' })
      break

    case 'session_event':
      dispatchSessionAction({
        type: 'SESSION_EVENT',
        event: frame.event,
        payload: frame.payload as Record<string, unknown>,
      })
      break

    case 'error':
      dispatchSessionAction({
        type: 'ERROR',
        code: frame.code,
        message: frame.message,
        details: frame.details as Record<string, unknown>,
      })
      break
  }
}

// ---------------------------------------------------------------------------
// Help / acknowledgement state — populated by the dispatcher
// ---------------------------------------------------------------------------

interface HelpState {
  commands: CommandDefinition[]
  errorBanner?: string
}

// ---------------------------------------------------------------------------
// WorkerStatusList — selector-isolated on workers Map keys (FR-050/FR-051).
// Only re-renders when the set of worker IDs changes, not on per-row updates.
// ---------------------------------------------------------------------------

function WorkerStatusList(): React.ReactElement | null {
  // Subscribe to the workers Map by identity — the reducer replaces the Map
  // reference whenever its contents change, so this is ref-stable between
  // dispatches. Deriving the sorted ID list inside the selector would rebuild
  // a new array on every getSnapshot call and trip React 19's Object.is cache
  // check ("getSnapshot should be cached to avoid an infinite loop").
  const workers = useSessionStore((s) => s.workers)
  const workerIds = useMemo(
    () => Array.from(workers.keys()).sort(),
    [workers],
  )
  if (workerIds.length === 0) return null
  return (
    <Box flexDirection="column" marginBottom={1}>
      {workerIds.map((id) => (
        <WorkerStatusRow key={id} workerId={id} />
      ))}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// App inner — consumes theme/i18n hooks (must be inside ThemeProvider)
// ---------------------------------------------------------------------------

interface AppInnerProps {
  bridge: IPCBridge
  /**
   * IME state lifted to <App> so <KeybindingProviderSetup> can feed
   * `isImeComposing` into the resolver's central IME guard for
   * `mutates_buffer` actions (Spec 288 Codex P1).  InputBar consumes the same
   * instance — there is exactly one active `useKoreanIME` hook in the
   * post-onboarding branch of the tree.
   */
  ime: KoreanIMEState
  /**
   * Reports modal-surface state (permission gauntlet, help overlay) upward so
   * <App> can derive `activeContexts` for the keybinding resolver.  Called on
   * every render with the currently-active `Chat | Confirmation` surface.
   */
  onActiveSurfaceChange: (surface: 'Chat' | 'Confirmation') => void
  /**
   * Reports modal-open state upward so <App> can deactivate the IME hook while
   * a modal (permission gauntlet, help overlay) owns the keyboard.  Without
   * this gate the IME listener keeps consuming `y/n` keystrokes in the
   * background during a permission prompt and reveals them as unexpected
   * draft text once the modal closes (Codex P1 regression fix).
   */
  onModalStateChange: (isModalOpen: boolean) => void
}

function AppInner({ bridge, ime, onActiveSurfaceChange, onModalStateChange }: AppInnerProps): React.ReactElement {
  const theme = useTheme()
  const i18n = useI18n()
  const { exit } = useApp()
  const crash = useSessionStore((s) => s.crash)
  const messageOrder = useSessionStore((s) => s.message_order)
  const pendingPermission = useSessionStore((s) => s.pending_permission)

  const registry = useMemo(() => buildDefaultRegistry(), [])
  const [ack, setAck] = useState<string>('')
  const [helpState, setHelpState] = useState<HelpState | null>(null)

  // Spec 288 Codex P1 — surface Chat / Confirmation state to <App> so the
  // central keybinding resolver sees the right context stack.  A modal open
  // (permission gauntlet, help overlay) claims `Confirmation`; otherwise the
  // InputBar owns focus → `Chat`.  `HistorySearch` is not yet wired because
  // <HistorySearchOverlay> is not mounted in the tree — see the TODO in
  // <App> below (Spec 288.1 follow-up).
  const isModalOpen = pendingPermission !== null || helpState !== null
  const activeSurface: 'Chat' | 'Confirmation' =
    isModalOpen ? 'Confirmation' : 'Chat'
  useEffect(() => {
    onActiveSurfaceChange(activeSurface)
  }, [activeSurface, onActiveSurfaceChange])
  // Spec 288 Codex P1 regression — report modal state to <App> so it can
  // deactivate the lifted `useKoreanIME` hook while a modal owns keys.  Prior
  // to this gate `y/n` presses inside the permission gauntlet leaked into
  // `ime.buffer` in the background and surfaced as draft text once the modal
  // closed, producing accidental submissions.
  useEffect(() => {
    onModalStateChange(isModalOpen)
  }, [isModalOpen, onModalStateChange])

  // IPC senders closed over the bridge — safe for the dispatcher's SendFrame
  // callback (typed to SessionEventFrame) and for free-text user_input frames.
  const sessionId = useSessionStore((s) => s.session_id)

  const sendSessionEvent = (frame: SessionEventFrame): void => {
    // Bridge-level fill-in: populate session_id when the command builder left
    // it as "". The dispatcher never has access to the store directly.
    const stamped: SessionEventFrame = frame.session_id === ''
      ? { ...frame, session_id: sessionId }
      : frame
    bridge.send(stamped)
  }

  const sendUserInput = (text: string): void => {
    const frame: UserInputFrame = {
      kind: 'user_input',
      session_id: sessionId,
      correlation_id: crypto.randomUUID(),
      ts: new Date().toISOString(),
      role: 'tui',
      text,
    }
    bridge.send(frame)
  }

  // DI callback for PermissionGauntletModal — keeps the modal bridge-free.
  const sendPermissionResponse = (frame: PermissionResponseFrame): void => {
    bridge.send(frame)
  }

  // InputBar delegates key handling to useKoreanIME (Phase 7 US5). We keep a
  // thin outer useInput here only for Ctrl-C (tear down) and Escape (clear
  // help overlay) — text composition lives entirely inside InputBar.
  const handleSubmit = (raw: string): void => {
    if (raw.trim().length === 0) return

    if (isSlashCommand(raw)) {
      void dispatchCommand(raw, registry, sendSessionEvent).then((result: DispatchResult) => {
        setAck(result.acknowledgement)
        if (result.renderHelp === true) {
          setHelpState({
            commands: listCommands(registry),
            errorBanner: result.acknowledgement === '' ? undefined : result.acknowledgement,
          })
        } else {
          setHelpState(null)
        }
      })
      return
    }

    setHelpState(null)
    setAck('')
    sendUserInput(raw)
  }

  // Outer key handler — Ctrl-C always closes the bridge. Escape clears the
  // help overlay when no modal is active. Everything else passes through to
  // InputBar's useKoreanIME (or to PermissionGauntletModal when it is open).
  //
  // Spec 288 Codex P1 note: the central keybinding resolver (mounted by
  // <KeybindingProviderSetup> in <App>) now also fires for ctrl+c via the
  // `session-exit` Tier-1 action.  Both paths run in parallel during the
  // Spec 288.1 migration window — keeping this handler means Ctrl-C still
  // tears the bridge down immediately even if the resolver's handler is
  // stubbed (announce-only).  Removing the dual path is tracked by Spec 288.1
  // alongside the resolver's production session-exit wiring.
  useInput((input, key) => {
    if (key.ctrl && input === 'c') {
      bridge.close().then(() => exit())
      return
    }
    if (pendingPermission !== null) return
    if (key.escape) {
      setHelpState(null)
    }
  })

  // Show ready hint if nothing has happened yet
  const isEmpty = messageOrder.length === 0 && !crash && helpState === null && ack === ''
  const inputDisabled = pendingPermission !== null

  return (
    <Box flexDirection="column" paddingX={1}>
      {/* Coordinator phase indicator (US4 scenario 1, FR-043) */}
      <PhaseIndicator />

      {/* Per-worker status rows (US4 scenario 2, FR-044) */}
      <WorkerStatusList />

      {/* Conversation history */}
      <MessageList />

      {/* Crash notice (renders when store.crash is set) */}
      <CrashNotice />

      {/* Permission gauntlet modal (US4 scenario 3, FR-045/FR-046).
          Renders only when pending_permission is set; swallows y/n input. */}
      <PermissionGauntletModal
        sendFrame={sendPermissionResponse}
        sessionId={sessionId}
      />

      {/* Ready hint — shown before any interaction */}
      {isEmpty && (
        <Box>
          <Text color={theme.inactive} dimColor>
            {i18n.sessionReady}
          </Text>
        </Box>
      )}

      {/* Help view — slash-command listing or unknown-command error */}
      {helpState !== null && (
        <HelpView commands={helpState.commands} errorBanner={helpState.errorBanner} />
      )}

      {/* Transient acknowledgement notice from a command handler */}
      {helpState === null && ack !== '' && (
        <Box marginY={1}>
          <Text color={theme.subtle}>{ack}</Text>
        </Box>
      )}

      {/* Korean IME input bar (US5, FR-015/FR-016) — consumes the lifted
          `ime` state so both the resolver (<KeybindingProviderSetup>) and
          the InputBar observe the same composition flag.  Suppressed while
          the permission modal is open. */}
      <InputBar ime={ime} onSubmit={handleSubmit} disabled={inputDisabled} />
    </Box>
  )
}

// ---------------------------------------------------------------------------
// App — sets up bridge frame consumer, then renders AppInner
// ---------------------------------------------------------------------------

interface AppProps {
  bridge: IPCBridge
}

export function App({ bridge }: AppProps): React.ReactElement {
  const { exit } = useApp()

  useEffect(() => {
    // Consume frames from the bridge and dispatch to store
    let active = true
    ;(async () => {
      for await (const frame of bridge.frames()) {
        if (!active) break
        // Consent sub-protocol rides notification_push frames; if a waiter
        // claims one, skip store dispatch to avoid double-handling.
        if (handleNotificationFrame(frame)) continue
        dispatchFrame(frame)
        // Exit event from backend
        if (frame.kind === 'session_event' && frame.event === 'exit') {
          bridge.close().then(() => exit())
          break
        }
      }
    })()

    return () => {
      active = false
    }
  }, [bridge, exit])

  // Epic H #1302: gate the main UI behind the citizen onboarding flow.
  // On first launch (or after a consent/scope version bump) render the
  // three-step Onboarding before AppInner.  Returning citizens with fresh
  // memdir records skip the flow in ≤ 3 s via the splash fast-path
  // (SC-012).  The memdir snapshot is read synchronously at boot only —
  // subsequent state lives in `onComplete`.
  const initialMemdir = useMemo(() => {
    const consent = latestConsentRecord()
    const scope = latestScopeRecord()
    return {
      consentRecord: consent !== null ? { consent_version: consent.consent_version } : undefined,
      scopeRecord: scope !== null ? { scope_version: scope.scope_version } : undefined,
    }
  }, [])
  // Stable per-launch session id — the same value is stamped on every
  // consent + ministry-scope record written during this session so the
  // two records cross-reference (contracts/onboarding-step-registry.md § 4).
  // UUIDv4 is used until Spec 032 surfaces a UUIDv7 helper; the Zod
  // schemas accept any RFC 4122 UUID shape.
  const sessionIdRef = useRef<string | null>(null)
  if (sessionIdRef.current === null) {
    sessionIdRef.current = crypto.randomUUID()
  }
  const consentFresh =
    initialMemdir.consentRecord?.consent_version === CURRENT_CONSENT_VERSION
  const scopeFresh =
    initialMemdir.scopeRecord?.scope_version === CURRENT_SCOPE_VERSION
  const [onboardingDone, setOnboardingDone] = useState<boolean>(
    consentFresh && scopeFresh,
  )

  // ---------------------------------------------------------------------
  // Spec 288 Codex P1 — lift IME + activeContexts to <App>
  //
  // `KeybindingProviderSetup` was previously mounted in main.tsx with no
  // props, causing the resolver to fall back to `['Global']` + `false` for
  // the entire session (Chat-only shortcuts unreachable, IME guard for
  // `mutates_buffer` actions inert).  We now lift both values up:
  //
  //   1. `useKoreanIME` is instantiated here with
  //      `isActive = onboardingDone && !isModalOpen` so it does not race
  //      Onboarding's own IME hook during first-launch AND it does not
  //      consume keystrokes in the background while a modal (permission
  //      gauntlet, help overlay) owns the keyboard.  Before this guard,
  //      `y/n` presses inside the permission gauntlet leaked into
  //      `ime.buffer` and re-appeared as draft text once the modal closed
  //      (Codex P1 regression from the previous `useKoreanIME(!disabled)`
  //      call in <InputBar>).  AppInner reports the modal state via
  //      `onModalStateChange`; the provider consumes the same instance via
  //      the `ime` prop, guaranteeing exactly one `useInput` composition
  //      listener per branch.
  //
  //   2. `activeContexts` is derived dynamically.  During onboarding we
  //      treat the tree as `['Confirmation', 'Global']` (consent-style
  //      modal).  Post-onboarding, AppInner reports whether the permission
  //      gauntlet / help overlay claim the surface via
  //      `onActiveSurfaceChange`; we lift the result into state and stamp
  //      the resolver context accordingly.
  //
  //   3. `HistorySearch` is not yet wired.  <HistorySearchOverlay> from
  //      Team C is not mounted into the tree — when Spec 288.1 mounts it,
  //      this branch should observe the overlay's open state (likely via
  //      an `onOpenChange` callback or lifted store field) and push
  //      `'HistorySearch'` onto the context stack.  Leaving a TODO here
  //      rather than fabricating a read path (Codex P1 scope is wiring the
  //      two values that already have backing state).
  //
  // The `cancelHistoryRef` below tracks whether the fire-and-forget memdir
  // scope-ack write from Onboarding has completed — orthogonal to the
  // provider concerns above.
  // ---------------------------------------------------------------------
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false)
  const ime = useKoreanIME(onboardingDone && !isModalOpen)
  const [activeSurface, setActiveSurface] = useState<'Chat' | 'Confirmation'>('Chat')
  const activeContexts = useMemo<ReadonlyArray<KeybindingContextEnum>>(() => {
    if (!onboardingDone) {
      // Onboarding is a consent-style modal — the three steps (splash,
      // consent review, ministry scope) all accept y/n / Enter inputs that
      // should shadow Chat chords.  TODO (Spec 288.1): add `'HistorySearch'`
      // here when <HistorySearchOverlay> is mounted.
      return ['Confirmation', 'Global'] as const
    }
    if (activeSurface === 'Confirmation') {
      return ['Confirmation', 'Global'] as const
    }
    return ['Chat', 'Global'] as const
  }, [onboardingDone, activeSurface])

  // ---------------------------------------------------------------------
  // Spec 288 Codex P1 (follow-up) — wire real Tier-1 handlers into the
  // provider.  Without `handlerOverrides` the provider would register its
  // default announce-only stubs, so ctrl+d / history navigation / mode
  // cycling never exercise their implemented controllers at runtime.
  //
  // The announcer is created once here so both `<KeybindingProviderSetup>`
  // and `buildTier1Handlers` share a single announce stream — the default
  // stubs inside the provider (used only before `handlerOverrides` takes
  // effect) and our real handlers funnel through the same stderr channel.
  //
  // Some controller deps are still stubs — see `tier1Handlers.ts` for the
  // `FIXME: Spec 288.1` comments covering the Spec 027 cancellation
  // envelope and Spec 024 audit writer.  The goal of this block is the
  // Codex P1 fix: every dispatched Tier-1 chord reaches a real controller
  // instead of the announce-only fallback.
  // ---------------------------------------------------------------------
  const sharedAnnouncer = useMemo(() => createAccessibilityAnnouncer(), [])

  const [permissionMode, setPermissionMode] =
    useState<PermissionMode>('default')

  // Tracks the latest InputBar buffer snapshot so the `session-exit` FR-014
  // guard can read an up-to-date value without InputBar needing to
  // re-render on every keystroke of its own draft.  `useKoreanIME` already
  // owns the buffer; we mirror its length via an effect inside <App>.
  const isBufferEmptyRef = useRef<boolean>(true)
  // Keep the ref in sync with the live IME buffer.  `ime.buffer` is
  // updated by the hook on every keystroke; reading it during render is
  // safe (same microtask) and cheap.
  isBufferEmptyRef.current = ime.buffer.length === 0

  // History source — for the wiring PR we surface the current session's
  // user-input messages only.  Cross-session entries land when Epic D
  // (#1299) exposes the memdir USER read path to the TUI.
  const messagesMap = useSessionStore((s) => s.messages)
  const backendSessionId = useSessionStore((s) => s.session_id)
  const resolvedSessionId =
    backendSessionId !== '' ? backendSessionId : sessionIdRef.current

  const historyEntries = useMemo<ReadonlyArray<HistoryNavigationEntry>>(() => {
    const entries: HistoryNavigationEntry[] = []
    for (const [, msg] of messagesMap) {
      if (msg.role !== 'user') continue
      entries.push({
        query_text: msg.chunks.join(''),
        // `Message` does not carry a timestamp today — surface a stable
        // placeholder so downstream consumers see ISO-8601 shaped data.
        // FIXME: Spec 288.1 — thread the true `user_input` frame `ts`
        // through the reducer so this reflects wall-clock history order.
        timestamp: new Date(0).toISOString(),
        session_id: resolvedSessionId,
        consent_scope: 'current-session',
      })
    }
    return entries
  }, [messagesMap, resolvedSessionId])

  // memdir USER consent — the onboarding boot snapshot already drives
  // `consentFresh`; reuse it as the Tier-1 consent probe.  Epic D (#1299)
  // will replace this with a live read when the USER tier lands.
  const memdirUserGranted = consentFresh
  // Availability mirrors granted-ness today; once Epic D ships the USER
  // tier can exist without a consent record (`available && !granted`).
  const memdirUserAvailable = consentFresh

  // Agent loop probe — the session store does not track liveness directly,
  // so derive it from the latest assistant message's `done` flag.
  const messageOrderForProbe = useSessionStore((s) => s.message_order)
  const isAgentLoopActive = React.useCallback((): boolean => {
    const lastId = messageOrderForProbe[messageOrderForProbe.length - 1]
    if (lastId === undefined) return false
    const msg = messagesMap.get(lastId)
    if (msg === undefined) return false
    return msg.role === 'assistant' && !msg.done
  }, [messageOrderForProbe, messagesMap])

  const currentToolCallId = React.useCallback((): string | null => {
    // Scan the most recent assistant message for the last tool call that
    // has no matching result yet.  When none is in flight, return null.
    for (let i = messageOrderForProbe.length - 1; i >= 0; i--) {
      const id = messageOrderForProbe[i]
      if (id === undefined) continue
      const msg = messagesMap.get(id)
      if (msg === undefined || msg.role !== 'assistant') continue
      for (let j = msg.tool_calls.length - 1; j >= 0; j--) {
        const call = msg.tool_calls[j]
        if (call === undefined) continue
        const hasResult = msg.tool_results.some(
          (r) => r.call_id === call.call_id,
        )
        if (!hasResult) return call.call_id
      }
    }
    return null
  }, [messageOrderForProbe, messagesMap])

  const tier1Handlers = useMemo(
    () =>
      buildTier1Handlers({
        sessionId: resolvedSessionId,
        announcer: sharedAnnouncer,
        isAgentLoopActive,
        currentToolCallId,
        isBufferEmpty: () => isBufferEmptyRef.current,
        getPermissionMode: () => permissionMode,
        setPermissionMode,
        // FIXME: Spec 288.1 — read Spec 033 session state once the
        // permission pipeline surfaces an irreversible-action flag.
        hasPendingIrreversibleAction: () => false,
        readDraft: () => ime.buffer,
        setDraft: (value: string) => {
          // Spec 288 Codex P1 fix — `history-prev` / `history-next` write the
          // selected historical query into the input bar via `ime.setBuffer`.
          // The hook's setter overwrites the committed buffer and drops any
          // in-flight composition so the citizen sees the recalled text
          // verbatim.  Empty-string writes (the `returned-to-present`
          // branch in `createHistoryNavigator`) are honoured as a clear.
          ime.setBuffer(value)
        },
        getHistory: () => historyEntries,
        memdirUserGranted,
        memdirUserAvailable,
      }),
    [
      resolvedSessionId,
      sharedAnnouncer,
      isAgentLoopActive,
      currentToolCallId,
      permissionMode,
      ime,
      historyEntries,
      memdirUserGranted,
      memdirUserAvailable,
    ],
  )

  const body = !onboardingDone ? (
    <Onboarding
      memdir={initialMemdir}
      startStep={resolveStartStep(initialMemdir)}
      sessionId={sessionIdRef.current}
      onComplete={() => setOnboardingDone(true)}
    />
  ) : (
    <AppInner
      bridge={bridge}
      ime={ime}
      onActiveSurfaceChange={setActiveSurface}
      onModalStateChange={setIsModalOpen}
    />
  )

  // Note on `sessionId`: the provider prop is only consumed by the IPC-backed
  // audit writer (currently unmounted — announce-only stubs from T017).
  // Wiring it to a concrete id belongs with the production audit writer in
  // Spec 288.1, where the backend session_id (from the IPC store) supersedes
  // the onboarding-local `sessionIdRef`.  Leaving it unset here avoids
  // stamping the wrong id on eventual audit records.
  return (
    <KeybindingProviderSetup
      activeContexts={activeContexts}
      isImeComposing={ime.isComposing}
      announcer={sharedAnnouncer}
      handlerOverrides={tier1Handlers}
    >
      {body}
    </KeybindingProviderSetup>
  )
}
