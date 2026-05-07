// Source: .references/claude-code-sourcemap/restored-src/src/components/VirtualMessageList.tsx (Claude Code 2.1.88, research-use)
// Gemini CLI inspiration (Apache-2.0): overflowToBackbuffer pattern
// Source hook: .references/claude-code-sourcemap/restored-src/src/hooks/useVirtualScroll.ts (Claude Code 2.1.88, research-use)
// SPDX-License-Identifier: Apache-2.0

/**
 * VirtualizedList<T> — generic virtualized list for KOSMOS TUI.
 *
 * Renders only the items within the visible viewport (computed from
 * useVirtualScroll's scroll position + terminal height) plus OVERSCAN_ROWS on
 * each side. Spacer <Box> elements hold the total scroll height constant for
 * unmounted items so Ink layout does not reflow the whole list.
 *
 * FR-048: only visible-viewport rows are mounted as React fibers.
 * FR-052: overflowToBackbuffer prop pushes scrolled-off rows into Ink's static
 *         backbuffer region so they are never re-rendered once committed.
 *
 * Props:
 *   items              — readonly array of data items (generic T)
 *   renderItem         — (item: T, index: number) => React.ReactElement
 *   keyExtractor       — (item: T, index: number) => string  (stable identity)
 *   scrollTop          — current scroll offset in rows (0 = top; caller-managed)
 *   overflowToBackbuffer — when true, rows that have scrolled off the top are
 *                          rendered via Ink's <Static> (backbuffer) region
 *                          instead of being unmounted (FR-052). Default: false.
 */

import React, { memo, useCallback, useMemo } from 'react'
import { Box, Static } from 'ink'

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface VirtualizedListProps<T> {
  readonly items: readonly T[]
  readonly renderItem: (item: T, index: number) => React.ReactElement
  readonly keyExtractor: (item: T, index: number) => string
  /**
   * Current scroll position in rows. Defaults to `Number.MAX_SAFE_INTEGER`
   * which triggers sticky-tail behavior (conversation TUI default — new
   * messages append and the view follows the tail). Pass 0 to pin to the top.
   */
  readonly scrollTop?: number
  /**
   * When true, rows that scroll off the top are pushed into Ink's static
   * backbuffer region (via <Static>) rather than being unmounted. This
   * guarantees historical rows are never re-rendered (FR-052).
   */
  readonly overflowToBackbuffer?: boolean
}

// ---------------------------------------------------------------------------
// VirtualizedListItem — memo-wrapped item wrapper
// ---------------------------------------------------------------------------

interface VirtualizedListItemProps {
  readonly itemKey: string
  readonly content: React.ReactElement
}

const VirtualizedListItem = memo(function VirtualizedListItem({
  content,
}: VirtualizedListItemProps): React.ReactElement {
  return (
    <Box flexDirection="column" flexShrink={0}>
      {content}
    </Box>
  )
})

VirtualizedListItem.displayName = 'VirtualizedListItem'

// ---------------------------------------------------------------------------
// VirtualizedList
// ---------------------------------------------------------------------------

function VirtualizedListInner<T>(
  props: VirtualizedListProps<T>,
): React.ReactElement {
  const {
    items,
    renderItem,
    keyExtractor,
    scrollTop = Number.MAX_SAFE_INTEGER,
    overflowToBackbuffer = false,
  } = props

  // Build stable key array (identity change triggers GC in the hook).
  const itemKeys: readonly string[] = useMemo(
    () => items.map((item, i) => keyExtractor(item, i)),
    // keyExtractor is expected to be stable (useCallback / module-level fn).
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [items, keyExtractor],
  )

  // ---------------------------------------------------------------------------
  // Inline windowing — simple slice-based viewport calculation.
  //
  // VirtualizedList is a standalone component that does NOT use <ScrollBox>.
  // It computes the visible window from `scrollTop` + estimated row height
  // without the full hook machinery (no Yoga measurements, no ScrollBox ref).
  //
  // WINDOW_SIZE: max items mounted at once. Matches useVirtualScroll's
  // COLD_START_COUNT + OVERSCAN_ROWS as a conservative bound that keeps
  // renderItem calls << 200 for any list size.
  // ---------------------------------------------------------------------------
  const WINDOW_SIZE = 99
  const OVERSCAN = 10

  const totalCount = items.length
  const stickyTail = scrollTop >= Number.MAX_SAFE_INTEGER / 2

  // Compute [start, end) half-open range for the viewport.
  const [start, end] = useMemo((): readonly [number, number] => {
    if (totalCount === 0) return [0, 0]
    if (stickyTail) {
      // Sticky tail: always show the last WINDOW_SIZE items.
      const s = Math.max(0, totalCount - WINDOW_SIZE)
      return [s, totalCount]
    }
    // Scroll-position based: treat scrollTop as a row index into the list.
    const estimatedStart = Math.max(0, scrollTop - OVERSCAN)
    const estimatedEnd = Math.min(totalCount, estimatedStart + WINDOW_SIZE)
    return [estimatedStart, estimatedEnd]
  }, [totalCount, stickyTail, scrollTop])

  // Spacers hold the scroll height constant for unmounted rows (no-ops in
  // Ink since there's no real scroll coordinate, but harmless).
  const topSpacer = start
  const bottomSpacer = totalCount - end

  // ---------------------------------------------------------------------------
  // overflowToBackbuffer: slice of items that have scrolled off (index < start)
  //
  // We pass the raw item slice to <Static> and provide the render function
  // directly so that Ink's <Static> controls when renderItem is called — it
  // only calls it for NEW items (those appended since last committed index).
  // This avoids eagerly calling renderItem for all backbuffer items on every
  // render, which would defeat the purpose of overflowToBackbuffer (FR-052).
  // ---------------------------------------------------------------------------
  type BackbufferEntry = { item: T; index: number; key: string }
  const backbufferEntries = useMemo((): BackbufferEntry[] => {
    if (!overflowToBackbuffer || start === 0) return []
    const result: BackbufferEntry[] = []
    for (let i = 0; i < start; i++) {
      const item = items[i]
      if (item !== undefined) {
        result.push({ item, index: i, key: itemKeys[i] ?? String(i) })
      }
    }
    return result
  }, [overflowToBackbuffer, start, items, itemKeys])

  const renderBackbufferEntry = useCallback(
    (entry: BackbufferEntry): React.ReactElement => (
      <Box key={entry.key} flexDirection="column" flexShrink={0}>
        {renderItem(entry.item, entry.index)}
      </Box>
    ),
    [renderItem],
  )

  // ---------------------------------------------------------------------------
  // Viewport items (start..end)
  // ---------------------------------------------------------------------------
  const viewportItems = useCallback((): React.ReactElement[] => {
    const result: React.ReactElement[] = []
    for (let i = start; i < end; i++) {
      const item = items[i]
      if (item !== undefined) {
        const key = itemKeys[i] ?? String(i)
        result.push(
          <VirtualizedListItem
            key={key}
            itemKey={key}
            content={renderItem(item, i)}
          />,
        )
      }
    }
    return result
  }, [start, end, items, itemKeys, renderItem])

  return (
    <Box flexDirection="column">
      {/* Static backbuffer: scrolled-off rows committed once, never re-rendered.
          <Static> tracks its own index state and only renders entries appended
          since the last committed index — historical rows are never re-invoked. */}
      {overflowToBackbuffer && backbufferEntries.length > 0 && (
        <Static items={backbufferEntries}>
          {renderBackbufferEntry}
        </Static>
      )}
      {/* Top spacer: holds scroll height for unmounted rows above viewport */}
      {!overflowToBackbuffer && topSpacer > 0 && (
        <Box height={topSpacer} flexShrink={0} />
      )}
      {/* Viewport items */}
      {viewportItems()}
      {/* Bottom spacer: holds scroll height for unmounted rows below viewport */}
      {bottomSpacer > 0 && (
        <Box height={bottomSpacer} flexShrink={0} />
      )}
    </Box>
  )
}

VirtualizedListInner.displayName = 'VirtualizedList'

// Generic forwardRef wrapper — TypeScript requires the cast for generic components.
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const VirtualizedList = VirtualizedListInner as <T>(
  props: VirtualizedListProps<T>,
) => React.ReactElement
