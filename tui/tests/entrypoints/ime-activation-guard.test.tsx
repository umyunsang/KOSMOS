// SPDX-License-Identifier: Apache-2.0
// Spec 288 Codex P1 regression test — IME activation guard while a modal is open.
//
// Context: when Team α lifted `useKoreanIME` from <InputBar> up to <App>, the
// initial wiring set `isActive = onboardingDone` only.  This regressed the
// prior <InputBar> behaviour where `isActive = !disabled` (disabled = modal
// open).  Without the modal guard, `y/n` keystrokes fired inside the
// permission gauntlet still fed the IME listener in the background and
// re-appeared as draft text once the modal closed, producing accidental
// submissions.
//
// This test renders a tiny harness that mounts `useKoreanIME` with a
// controllable `isActive` flag and asserts that keystrokes delivered while
// `isActive === false` do NOT mutate the hook's buffer.  The test mirrors the
// real wiring in `tui/src/entrypoints/tui.tsx` — `<App>` now computes
// `useKoreanIME(onboardingDone && !isModalOpen)` so the hook is inert while
// the permission gauntlet or help overlay owns the keyboard.
//
// Companion semantic note lives in `tui/tests/hooks/useKoreanIME.test.ts`.

import React, { useState } from 'react'
import { describe, expect, it } from 'bun:test'
import { Box, Text } from 'ink'
import { render } from 'ink-testing-library'
import { useKoreanIME } from '../../src/hooks/useKoreanIME'

// ---------------------------------------------------------------------------
// Minimal harness — renders the IME buffer so tests can observe mutations.
// ---------------------------------------------------------------------------

interface HarnessProps {
  /**
   * Initial value of the `isActive` flag.  Flipping it mid-run is not needed
   * for these tests because Ink's test renderer cannot re-target stdin to a
   * remounted hook; we render two separate instances instead.
   */
  initialActive: boolean
}

function ImeHarness({ initialActive }: HarnessProps): React.ReactElement {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- retained for
  // future toggling tests; harness currently fixes the flag at mount time.
  const [active, _setActive] = useState<boolean>(initialActive)
  const ime = useKoreanIME(active)
  return (
    <Box>
      <Text>buffer=[{ime.buffer}]</Text>
    </Box>
  )
}

/**
 * Ink schedules renders via `void this.onRender()` (async) and reads stdin on
 * `'readable'` events.  Two timer-zero flushes cover the React reconciler
 * commit, Ink's `handleReadable` pump, and the async frame write.  Mirrors
 * the helper in `tui/tests/ink/renderer-double-buffer.test.tsx`.
 */
async function flush(): Promise<void> {
  await new Promise<void>((r) => setTimeout(r, 0))
  await new Promise<void>((r) => setTimeout(r, 0))
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useKoreanIME — activation guard (Spec 288 Codex P1 regression)', () => {
  it('while isActive=false, y/n keystrokes do NOT mutate the IME buffer', async () => {
    // Mirrors the permission-gauntlet-open state: <App> computes
    // `useKoreanIME(onboardingDone && !isModalOpen)` → `isActive=false`.
    const { stdin, lastFrame, unmount } = render(
      <ImeHarness initialActive={false} />,
    )
    await flush()

    // Baseline: buffer empty.
    expect(lastFrame()).toContain('buffer=[]')

    // Simulate the exact keystrokes the gauntlet accepts.  Under the previous
    // (regressed) wiring these would land in `ime.buffer`; under the fix the
    // IME's `useInput` is inactive and Ink routes them nowhere.  Sent one
    // char at a time because Ink's `parseKeypress` treats each stdin chunk
    // as a single keypress (see companion note in the active-case test).
    stdin.write('y')
    await flush()
    stdin.write('n')
    await flush()
    stdin.write('h')
    await flush()
    stdin.write('e')
    await flush()
    stdin.write('l')
    await flush()
    stdin.write('l')
    await flush()
    stdin.write('o')
    await flush()

    // Critical assertion: the buffer is still empty because the hook's
    // `useInput({ isActive: false })` call suppresses all input.
    expect(lastFrame()).toContain('buffer=[]')

    unmount()
  })

  it('while isActive=true, the IME buffer accepts ASCII keystrokes', async () => {
    // Control case: confirm the harness actually reaches the hook when the
    // guard is open.  Without this companion assertion, a broken harness
    // (e.g. stdin not wired) would make the inactive-case test vacuous.
    //
    // NOTE: Ink's `parseKeypress` parses each stdin `write()` chunk as a
    // single keypress — `'hi'` lands as the keypress name `'h'` (leading
    // char), not the full two-char string.  Send keystrokes one at a time
    // so the hook's jamo state machine receives them individually.
    const { stdin, lastFrame, unmount } = render(
      <ImeHarness initialActive={true} />,
    )
    await flush()

    expect(lastFrame()).toContain('buffer=[]')

    stdin.write('h')
    await flush()
    stdin.write('i')
    await flush()

    expect(lastFrame()).toContain('buffer=[hi]')

    unmount()
  })
})
