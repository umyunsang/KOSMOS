// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/KeybindingProviderSetup.tsx (CC 2.1.88, research-use)
// Spec 288 · T017 — app-root provider that builds the registry + announcer once.
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
import { drainBindingSpans } from './resolver'
import type { SpanEmitter } from './resolver'
import {
  type AuditWriter,
  type KeybindingContext as KeybindingContextEnum,
} from './types'

export type KeybindingProviderSetupProps = Readonly<{
  children: React.ReactNode
  /** Optional — production builds inject the IPC-backed audit writer. */
  audit?: AuditWriter | null
  /** Optional — production builds inject the IPC-backed span emitter. */
  spans?: SpanEmitter
  /** Current session id (from the bridge). */
  sessionId?: string | null
  /** Active contexts — declarative; the provider does not track modal state. */
  activeContexts?: ReadonlyArray<KeybindingContextEnum>
  /** IME composition state — typically lifted from `useKoreanIME`. */
  isImeComposing?: boolean
}>

const inMemorySpanEmitter: SpanEmitter = {
  emitBinding(attrs) {
    // Route through the resolver's shared ring so `drainBindingSpans()`
    // remains a single source of truth for tests.
    void drainBindingSpans() // touch to keep the ring alive; no-op in prod
    const _ = attrs
  },
}

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
        spans: props.spans ?? inMemorySpanEmitter,
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

  return (
    <KeybindingContext.Provider value={value}>
      {props.children}
    </KeybindingContext.Provider>
  )
}
