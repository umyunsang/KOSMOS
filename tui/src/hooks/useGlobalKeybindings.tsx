// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/hooks/useGlobalKeybindings.tsx (CC 2.1.88, research-use)
// Spec 288 · T020 — global Ink.useInput handler feeding events into the resolver.
//
// This is the single entry point for ChordEvents. Raw mode is owned by Ink's
// `useInput`; we translate every event into a `ChordEvent` via `buildChordEvent`
// then dispatch through the resolver. When the resolver returns a
// `dispatched` result, we invoke every registered handler for that action.
//
// FR-016 — ctrl+c / ctrl+d raw bytes are detected inside `buildChordEvent`,
// so terminals that strip Ink's modifier flags still reach the reserved
// action path.

import React from 'react'
import { useInput } from 'ink'
import type { Key } from 'ink'
import { buildChordEvent, type InkKeyLike } from '../keybindings/match'
import { resolve } from '../keybindings/resolver'
import { useKeybindingSurfaces } from '../keybindings/KeybindingContext'
import { dispatchAction } from '../keybindings/useKeybinding'

export type UseGlobalKeybindingsOptions = Readonly<{
  enabled?: boolean
}>

export function useGlobalKeybindings(
  options: UseGlobalKeybindingsOptions = {},
): void {
  const surfaces = useKeybindingSurfaces()
  const enabled = options.enabled ?? true

  useInput(
    (input: string, key: Key) => {
      const event = buildChordEvent(input, key as InkKeyLike)
      if (event === null) return
      const result = resolve(event, {
        active: surfaces.activeContexts,
        registry: surfaces.registry,
        ime: surfaces.ime,
        ...(surfaces.spans !== null ? { spans: surfaces.spans } : {}),
        sessionId: surfaces.sessionId ?? undefined,
        audit: surfaces.audit ?? undefined,
        announcer: surfaces.announcer,
      })
      if (result.kind !== 'dispatched') return
      dispatchAction(result.context, result.action)
    },
    { isActive: enabled },
  )
  // eslint-disable-next-line react-hooks/exhaustive-deps -- surfaces is stable
  React.useEffect(() => undefined, [])
}
