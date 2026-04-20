// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/KeybindingProviderSetup.tsx (CC 2.1.88, research-use)
// Spec 288 · T017 — app-root provider that builds the registry + announcer once,
// mounts the global keybinding listener, and registers default handler stubs.
//
// Places one immutable registry on the context. Consumers drive the resolver
// through `useGlobalKeybindings` (T020) and reach display chords via
// `useShortcutDisplay` (T019).

import React from 'react'
import { createAccessibilityAnnouncer } from './accessibilityAnnouncer'
import {
  KeybindingContext,
  type KeybindingSurfaces,
} from './KeybindingContext'
import { buildRegistry } from './registry'
import type { SpanEmitter } from './resolver'
import {
  registerHandlers,
  type ActionHandlers,
} from './useKeybinding'
import { useGlobalKeybindings } from '../hooks/useGlobalKeybindings'
import {
  type AuditWriter,
  type KeybindingContext as KeybindingContextEnum,
  type TierOneAction,
} from './types'

export type KeybindingProviderSetupProps = Readonly<{
  children: React.ReactNode
  /** Optional — production builds inject the IPC-backed audit writer. */
  audit?: AuditWriter | null
  /**
   * Optional — production builds inject the IPC-backed span emitter. When
   * omitted, `resolve()` falls back to its module-level ring, which
   * `drainBindingSpans()` exposes to tests.
   */
  spans?: SpanEmitter
  /** Current session id (from the bridge). */
  sessionId?: string | null
  /** Active contexts — declarative; the provider does not track modal state. */
  activeContexts?: ReadonlyArray<KeybindingContextEnum>
  /** IME composition state — typically lifted from `useKoreanIME`. */
  isImeComposing?: boolean
  /**
   * Citizen-facing handler overrides. When omitted the provider registers
   * announce-only stubs for every non-`draft-cancel` Tier 1 action so
   * `dispatchAction` is never a silent no-op (Codex P1 fix). Production
   * builds inject real handlers threading Spec 027 cancellation + Spec 024
   * audit + Spec 033 ModeCycle; see docs/spec/288 § Deferred for the wiring
   * checklist.
   */
  handlerOverrides?: {
    Global?: ActionHandlers
    Chat?: ActionHandlers
    HistorySearch?: ActionHandlers
    Confirmation?: ActionHandlers
  }
}>

// ---------------------------------------------------------------------------
// Global listener — mounted once so every keystroke flows through the
// resolver. Without this component the Tier 1 shortcuts would be inert at
// runtime (Codex P1).
// ---------------------------------------------------------------------------

function GlobalKeybindingListener(): React.ReactElement | null {
  useGlobalKeybindings()
  return null
}

// ---------------------------------------------------------------------------
// Default announce-only stubs for actions that require production deps
// (CancellationSignal, AuditWriter, history getter, ModeCycle probe). These
// guarantee `dispatchAction` always has a receiver so no chord is silently
// dropped at runtime. Real implementations replace them via `handlerOverrides`.
// ---------------------------------------------------------------------------

function buildDefaultGlobalStubs(
  announce: (message: string) => void,
): ActionHandlers {
  const stub = (
    action: TierOneAction,
    message: string,
  ): (() => void) => {
    return () => {
      announce(message)
      process.stderr.write(
        `[keybindings] ${action} dispatched — production handler not yet wired\n`,
      )
    }
  }
  return {
    'agent-interrupt': stub(
      'agent-interrupt',
      '에이전트 중단 요청 수신 — 백엔드 연결 후 완전 지원',
    ),
    'session-exit': stub(
      'session-exit',
      '세션 종료 요청 수신 — 감사 로그 플러시 후 종료',
    ),
    'history-search': stub(
      'history-search',
      '이력 검색 오버레이 요청 수신',
    ),
    'permission-mode-cycle': stub(
      'permission-mode-cycle',
      '권한 모드 순환 요청 수신',
    ),
  }
}

function buildDefaultChatStubs(
  announce: (message: string) => void,
): ActionHandlers {
  const stub =
    (action: TierOneAction, message: string): (() => void) =>
    () => {
      announce(message)
      process.stderr.write(
        `[keybindings] ${action} dispatched — production handler not yet wired\n`,
      )
    }
  return {
    'history-prev': stub('history-prev', '이전 질문 불러오기'),
    'history-next': stub('history-next', '다음 질문 불러오기'),
  }
}

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function KeybindingProviderSetup(
  props: KeybindingProviderSetupProps,
): React.ReactElement {
  const registry = React.useMemo(() => buildRegistry(), [])
  const announcer = React.useMemo(() => createAccessibilityAnnouncer(), [])

  const value = React.useMemo<KeybindingSurfaces>(
    () =>
      Object.freeze({
        registry,
        announcer,
        spans: props.spans ?? null,
        audit: props.audit ?? null,
        sessionId: props.sessionId ?? null,
        ime: { isComposing: props.isImeComposing ?? false },
        activeContexts: props.activeContexts ?? (['Global'] as const),
      }),
    [
      registry,
      announcer,
      props.spans,
      props.audit,
      props.sessionId,
      props.isImeComposing,
      props.activeContexts,
    ],
  )

  // Register default announce-only stubs once; overrides replace them.
  React.useEffect(() => {
    const cleanups: Array<() => void> = []
    const announce = (msg: string): void =>
      announcer.announce(msg, { priority: 'polite' })
    const globalHandlers =
      props.handlerOverrides?.Global ?? buildDefaultGlobalStubs(announce)
    const chatHandlers =
      props.handlerOverrides?.Chat ?? buildDefaultChatStubs(announce)
    cleanups.push(registerHandlers('Global', globalHandlers))
    cleanups.push(registerHandlers('Chat', chatHandlers))
    if (props.handlerOverrides?.HistorySearch !== undefined) {
      cleanups.push(
        registerHandlers('HistorySearch', props.handlerOverrides.HistorySearch),
      )
    }
    if (props.handlerOverrides?.Confirmation !== undefined) {
      cleanups.push(
        registerHandlers('Confirmation', props.handlerOverrides.Confirmation),
      )
    }
    return () => {
      for (const c of cleanups) c()
    }
  }, [announcer, props.handlerOverrides])

  return (
    <KeybindingContext.Provider value={value}>
      <GlobalKeybindingListener />
      {props.children}
    </KeybindingContext.Provider>
  )
}

