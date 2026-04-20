// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/KeybindingContext.tsx (CC 2.1.88, research-use)
// Spec 288 · T016 — React context exposing the registry + resolver surface.
//
// The context value is constructed once at TUI boot by
// `KeybindingProviderSetup` (T017) and is immutable for the session — no
// React state mutation occurs here.

import React from 'react'
import {
  type AccessibilityAnnouncer,
  type AuditWriter,
  type KeybindingContext as KeybindingContextEnum,
  type KeybindingRegistry,
} from './types'
import { type ImeStateLike, type SpanEmitter } from './resolver'

export type KeybindingSurfaces = Readonly<{
  registry: KeybindingRegistry
  announcer: AccessibilityAnnouncer
  /** Injected by the provider at boot; tests can stub with a ring buffer. */
  spans: SpanEmitter
  /** Optional — present when the Spec 024 IPC audit writer is wired. */
  audit: AuditWriter | null
  /** Current session id — used when emitting reserved-action audit records. */
  sessionId: string | null
  /** Current IME composition state (derived from `useKoreanIME`). */
  ime: ImeStateLike
  /** Contexts currently active (outermost to innermost). */
  activeContexts: ReadonlyArray<KeybindingContextEnum>
}>

export const KeybindingContext = React.createContext<KeybindingSurfaces | null>(
  null,
)

export function useKeybindingSurfaces(): KeybindingSurfaces {
  const ctx = React.useContext(KeybindingContext)
  if (ctx === null) {
    throw new Error(
      'KeybindingContext missing — wrap the tree in <KeybindingProviderSetup>.',
    )
  }
  return ctx
}
