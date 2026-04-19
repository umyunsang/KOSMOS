// Source: .references/claude-code-sourcemap/restored-src/src/hooks/useVirtualScroll.ts (Claude Code 2.1.88, research-use)
// Adapted for KOSMOS: removed ScrollBox/DOMElement dependencies; uses useStdout().stdout.rows
// for terminal height; simplified to a stateless range calculator suitable for Ink Box layout.
// SPDX-License-Identifier: Apache-2.0

import { useCallback, useMemo, useRef } from 'react'
import { useStdout } from 'ink'

// ---------------------------------------------------------------------------
// Constants (byte-faithful from source)
// ---------------------------------------------------------------------------

/** Estimated height (rows) for items not yet measured. Low to avoid blank spacer. */
const DEFAULT_ESTIMATE = 3

/** Extra rows rendered above and below the viewport. */
const OVERSCAN_ROWS = 10

/** Items rendered before viewport height is known. */
const COLD_START_COUNT = 20

/** Cap on mounted items to bound fiber allocation. */
const MAX_MOUNTED_ITEMS = 100

// ---------------------------------------------------------------------------
// Public types
// ---------------------------------------------------------------------------

export interface VirtualScrollResult {
  /** [startIndex, endIndex) half-open slice of items to render. */
  readonly range: readonly [number, number]
  /** Height (rows) of spacer before the first rendered item. */
  readonly topSpacer: number
  /** Height (rows) of spacer after the last rendered item. */
  readonly bottomSpacer: number
  /**
   * Call once per render to update measured height for a key.
   * Replaces the measureRef(key) callback-ref pattern from the source;
   * callers report heights after Yoga/Ink layout resolves.
   */
  readonly reportHeight: (key: string, rows: number) => void
  /**
   * Cumulative y-offset of each item in list coords.
   * offsets[i] = rows above item i; offsets[n] = totalHeight.
   */
  readonly offsets: ReadonlyArray<number>
  /** Current terminal height used for viewport calculation. */
  readonly viewportHeight: number
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

/**
 * Lightweight viewport-range calculator for KOSMOS VirtualizedList.
 *
 * Derived from Claude Code's useVirtualScroll (research-use attribution on
 * line 1). Key simplifications for KOSMOS's Ink context:
 *   - No ScrollBox/Yoga dependency: uses useStdout().stdout.rows for height.
 *   - No pendingDelta/sticky-scroll: items are always appended at the tail;
 *     the list is presumed sticky-scrolled to the bottom by default.
 *   - scrollTop is tracked as a simple state param passed by the consumer.
 *
 * @param itemKeys   Stable, ordered key array (one entry per item).
 * @param scrollTop  Current scroll offset in rows. Pass `Number.MAX_SAFE_INTEGER`
 *                   (the default) for sticky-tail behavior — the list shows the
 *                   most-recent (bottom) items, as a conversation TUI requires.
 *                   Pass 0 to pin to the top.
 */
export function useVirtualScroll(
  itemKeys: readonly string[],
  scrollTop: number = Number.MAX_SAFE_INTEGER,
): VirtualScrollResult {
  const { stdout } = useStdout()
  const viewportHeight: number = (stdout as unknown as { rows?: number }).rows ?? 24

  const heightCache = useRef(new Map<string, number>())
  const offsetVersionRef = useRef(0)

  // GC stale entries when itemKeys identity changes (compaction / clear).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useMemo(() => {
    const live = new Set(itemKeys)
    let dirty = false
    for (const k of heightCache.current.keys()) {
      if (!live.has(k)) {
        heightCache.current.delete(k)
        dirty = true
      }
    }
    if (dirty) offsetVersionRef.current++
  }, [itemKeys])

  // Build cumulative offsets array.
  const offsets: number[] = useMemo(() => {
    const arr: number[] = [0]
    let cum = 0
    for (const key of itemKeys) {
      cum += heightCache.current.get(key) ?? DEFAULT_ESTIMATE
      arr.push(cum)
    }
    return arr
    // offsetVersionRef is a ref — cannot be a dep. We include itemKeys as
    // the primary invalidator; reportHeight increments the ref and the
    // caller is expected to trigger a re-render via external state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [itemKeys, offsetVersionRef.current])

  const n = itemKeys.length

  // ---------------------------------------------------------------------------
  // Viewport range calculation (simplified sticky-tail path from source)
  // ---------------------------------------------------------------------------

  let start: number
  let end: number

  const totalHeight = offsets[n] ?? 0
  // maxScroll: the scroll offset at which the bottom of content aligns with
  // the bottom of the viewport. If content fits entirely in the viewport,
  // maxScroll is 0 — meaning the list is always "stuck to the bottom."
  const maxScroll = Math.max(0, totalHeight - viewportHeight)
  // isSticky: true when the caller is at (or past) the bottom, OR has not yet
  // scrolled (scrollTop === 0 and content fits). For a conversation list the
  // default UX is sticky-tail — new messages append and the view follows.
  const isSticky = scrollTop >= maxScroll

  if (viewportHeight === 0 || n === 0) {
    start = Math.max(0, n - COLD_START_COUNT)
    end = n
  } else if (isSticky) {
    // Sticky-tail path (source useVirtualScroll § isSticky branch):
    // walk back from the tail until viewport + overscan is covered.
    const budget = viewportHeight + OVERSCAN_ROWS
    start = n
    while (start > 0 && totalHeight - (offsets[start - 1] ?? 0) < budget) {
      start--
    }
    end = n
  } else {
    const budget = viewportHeight + OVERSCAN_ROWS
    const effLo = Math.max(0, scrollTop - OVERSCAN_ROWS)

    // Binary search for start (O(log n) — from source).
    {
      let l = 0
      let r = n
      while (l < r) {
        const m = (l + r) >> 1
        if ((offsets[m + 1] ?? 0) <= effLo) l = m + 1
        else r = m
      }
      start = l
    }

    // Extend end until coverage >= viewport + 2×overscan.
    const needed = budget + OVERSCAN_ROWS
    const maxEnd = Math.min(n, start + MAX_MOUNTED_ITEMS)
    let coverage = 0
    end = start
    while (end < maxEnd && coverage < needed) {
      coverage += heightCache.current.get(itemKeys[end] ?? '') ?? DEFAULT_ESTIMATE
      end++
    }
  }

  const effTopSpacer = offsets[start] ?? 0
  const effBottomSpacer = totalHeight - (offsets[end] ?? totalHeight)

  const reportHeight = useCallback((key: string, rows: number) => {
    const prev = heightCache.current.get(key)
    if (prev !== rows) {
      heightCache.current.set(key, rows)
      offsetVersionRef.current++
    }
  }, [])

  return {
    range: [start, end] as const,
    topSpacer: effTopSpacer,
    bottomSpacer: effBottomSpacer,
    reportHeight,
    offsets,
    viewportHeight,
  }
}
