// SPDX-License-Identifier: Apache-2.0
/**
 * BackpressureHud — Spec 032 T036
 *
 * Renders a non-blocking Korean HUD banner when the backend emits a
 * BackpressureSignalFrame.  Displays a live countdown from retry_after_ms.
 *
 * Design rules:
 * - Consumes hud_copy_ko directly from the frame (FR-013, FR-015).
 * - Non-blocking: does NOT pause the input queue; the citizen can still type.
 * - SC-003: HUD render p95 < 16 ms (1 animation frame @ 60 Hz).
 *   Proof: purely declarative React re-render; no I/O in the hot path.
 * - Cleared when signal="resume" arrives.
 *
 * Spec refs: FR-013, FR-015, SC-003, contracts/tx-dedup.contract.md § 1.3 / 1.5
 */

import React, { useEffect, useRef, useState } from 'react'
import { Box, Text } from 'ink'
import type { BackpressureSignalFrame } from './frames.generated.js'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BackpressureHudProps {
  /** The most recent BackpressureSignalFrame received, or null when idle. */
  frame: BackpressureSignalFrame | null
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Format a remaining millisecond value as a human-readable seconds string.
 * e.g. 15000 → "15초", 1500 → "2초", 0 → "0초"
 */
function formatCountdownKo(remainingMs: number): string {
  const secs = Math.ceil(remainingMs / 1000)
  return `${secs}초`
}

// ---------------------------------------------------------------------------
// BackpressureHud component
// ---------------------------------------------------------------------------

/**
 * Renders a HUD banner from a BackpressureSignalFrame.
 *
 * When signal="pause" or signal="throttle": show Korean HUD copy with optional
 * live countdown.  When signal="resume" or frame=null: render nothing.
 *
 * The countdown ticks every second using a setInterval.  When retry_after_ms
 * is present (upstream_429 throttle), the banner shows a live countdown in
 * the format: "부처 API가 혼잡합니다. 15초 후 자동 재시도합니다." with the
 * "15초" part counting down in real-time.
 *
 * Non-blocking guarantee: this component never touches the input event queue;
 * it is purely display-only.
 */
export function BackpressureHud({ frame }: BackpressureHudProps): React.ReactElement | null {
  // Track remaining ms for countdown (initialised from frame.retry_after_ms)
  const [remainingMs, setRemainingMs] = useState<number | null>(null)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const startTimeRef = useRef<number | null>(null)
  const initialMsRef = useRef<number | null>(null)

  // When frame changes, (re-)start the countdown timer
  useEffect(() => {
    // Clear any running timer
    if (intervalRef.current !== null) {
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (!frame || frame.signal === 'resume') {
      setRemainingMs(null)
      startTimeRef.current = null
      initialMsRef.current = null
      return
    }

    const retryMs = frame.retry_after_ms ?? null

    if (retryMs !== null && retryMs > 0) {
      // Throttle with countdown
      setRemainingMs(retryMs)
      startTimeRef.current = Date.now()
      initialMsRef.current = retryMs

      intervalRef.current = setInterval(() => {
        if (startTimeRef.current === null || initialMsRef.current === null) return
        const elapsed = Date.now() - startTimeRef.current
        const rem = Math.max(0, initialMsRef.current - elapsed)
        setRemainingMs(rem)
        if (rem <= 0) {
          if (intervalRef.current !== null) {
            clearInterval(intervalRef.current)
            intervalRef.current = null
          }
        }
      }, 250) // 4 Hz refresh — well within 16 ms render budget per tick
    } else {
      // pause / throttle without countdown — static banner
      setRemainingMs(null)
    }

    return () => {
      if (intervalRef.current !== null) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
  }, [frame])

  // Nothing to show when no active backpressure
  if (!frame || frame.signal === 'resume') {
    return null
  }

  // Build display text:
  // If we have a countdown, substitute the current remaining time into the copy.
  // The hud_copy_ko from upstream_429 frames contains "{retry_after}초 후 자동 재시도합니다."
  // We re-render with live countdown instead of static copy.
  let displayText = frame.hud_copy_ko

  if (remainingMs !== null && frame.retry_after_ms !== null) {
    // Replace any existing time reference in the copy with the live countdown.
    // The canonical template is "부처 API가 혼잡합니다. Xs 후 자동 재시도합니다."
    // We replace the numeric seconds portion with the live countdown.
    displayText = displayText.replace(
      /\d+초 후 자동 재시도합니다\./,
      `${formatCountdownKo(remainingMs)} 후 자동 재시도합니다.`,
    )
  }

  const isThrottle = frame.signal === 'throttle'
  const bannerColor = isThrottle ? 'yellow' : 'red'

  return (
    <Box
      borderStyle="single"
      borderColor={bannerColor}
      paddingX={1}
      marginY={0}
    >
      <Text color={bannerColor} bold>
        {isThrottle ? '⚠ ' : '⛔ '}
        {displayText}
      </Text>
    </Box>
  )
}

export default BackpressureHud
