// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/keybindings/useKeybinding.ts (CC 2.1.88, research-use)
// Spec 288 · T018 — per-context hook that subscribes a component to action dispatches.
//
// Usage (Team A / B / C action-handler consumers):
//
//   useKeybinding('Chat', {
//     'draft-cancel': () => clearDraft(),
//     'history-prev': () => loadPrev(),
//   })
//
// The hook does NOT own the global input listener — that lives in
// `useGlobalKeybindings` (T020). It merely registers a handler bag that the
// global listener consults after the resolver dispatches.

import React from 'react'
import { useKeybindingSurfaces } from './KeybindingContext'
import {
  type KeybindingContext as KeybindingContextEnum,
  type TierOneAction,
} from './types'

export type ActionHandlers = Partial<Record<TierOneAction, () => void>>

type HandlerRegistry = Map<
  KeybindingContextEnum,
  Set<ActionHandlers>
>

const HANDLERS: HandlerRegistry = new Map()

export function registerHandlers(
  context: KeybindingContextEnum,
  handlers: ActionHandlers,
): () => void {
  let bucket = HANDLERS.get(context)
  if (bucket === undefined) {
    bucket = new Set()
    HANDLERS.set(context, bucket)
  }
  bucket.add(handlers)
  return () => {
    bucket?.delete(handlers)
  }
}

export function dispatchAction(
  context: KeybindingContextEnum,
  action: TierOneAction,
): boolean {
  const bucket = HANDLERS.get(context)
  if (bucket === undefined) return false
  let fired = false
  for (const handlers of bucket) {
    const handler = handlers[action]
    if (handler !== undefined) {
      handler()
      fired = true
    }
  }
  return fired
}

export function useKeybinding(
  context: KeybindingContextEnum,
  handlers: ActionHandlers,
): void {
  // Re-evaluate surfaces so the component crashes loudly when the provider
  // is missing — matches CC behaviour.
  useKeybindingSurfaces()
  React.useEffect(() => registerHandlers(context, handlers), [context, handlers])
}
