// SPDX-License-Identifier: Apache-2.0
// Spec 288 · T037 — `<HistorySearchOverlay>` (User Story 6).
//
// Closes #1584. FR-020 (≤ 300 ms open), FR-021 (consent-scope gating),
// FR-022 (escape byte-for-byte draft restore), FR-029..FR-032 (a11y).
//
// Modal-shell shape borrowed from the Spec 035 onboarding pattern
// (`tui/src/components/onboarding/Onboarding.tsx`) — same flexDirection +
// padding + theme-token wiring, same IME-gated `useInput` for the
// keystroke loop. The overlay deliberately does NOT subscribe to the
// keybinding registry: it is a `HistorySearch` context (see
// data-model.md § 1) so its local handlers win the resolver precedence
// while it is mounted (D7).

import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Box, Text, useInput } from 'ink'
import { useTheme } from '../../theme/provider'
import { useKoreanIME } from '../../hooks/useKoreanIME'
import { filterHistoryEntries } from '../../keybindings/hangulSearch'
import {
  cancelHistorySearch,
  selectHistoryEntry,
  type HistoryEntry,
  type OverlayOpenRequest,
} from '../../keybindings/actions/historySearch'
import { type AccessibilityAnnouncer } from '../../keybindings/types'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export type HistorySearchOverlayProps = {
  /** Open request envelope from `openHistorySearchOverlay()`. */
  request: OverlayOpenRequest
  /** Announcer shim — passed through for selection/cancel announcements. */
  announcer: AccessibilityAnnouncer
  /** Selection handler — receives the entry's query_text. */
  onSelect: (next_draft: string) => void
  /** Cancel handler — receives the byte-for-byte saved draft. */
  onCancel: (next_draft: string) => void
  /** Maximum number of visible filter rows; defaults to 8. */
  max_rows?: number
}

const DEFAULT_MAX_ROWS = 8

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function HistorySearchOverlay({
  request,
  announcer,
  onSelect,
  onCancel,
  max_rows = DEFAULT_MAX_ROWS,
}: HistorySearchOverlayProps): React.ReactElement {
  const theme = useTheme()
  const { isComposing } = useKoreanIME()
  const [needle, setNeedle] = useState<string>('')
  const [cursor, setCursor] = useState<number>(0)
  // Scroll offset into `filtered`: the first row drawn is
  // `filtered[scrollOffset]`.  Maintaining this alongside `cursor` is what
  // makes every result reachable by keyboard (Codex P2 against line 124 of
  // the pre-fix code): without an offset, down-arrow could advance `cursor`
  // past the visible window (`filtered.slice(0, max_rows)`) and `enter`
  // would silently select a hidden entry.  Invariant preserved by every
  // handler below: `scrollOffset <= cursor < scrollOffset + max_rows`.
  const [scrollOffset, setScrollOffset] = useState<number>(0)

  // Derived view: filtered entries, recomputed on every keystroke. Memoise
  // because the filter walks the haystack and decomposes each Hangul
  // syllable — for a typical session (≤ 200 entries) the cost is sub-ms,
  // but memoising keeps overlay latency well inside FR-020's 300 ms when
  // the citizen pastes a long needle.
  const filtered = useMemo(
    () => filterHistoryEntries(request.visible_entries, needle),
    [request.visible_entries, needle],
  )

  // Reset cursor + scrollOffset whenever the filter query changes.  Keeping
  // a stale offset would leave the citizen staring at empty rows when a
  // tighter needle shrinks the result list below the previous offset.
  useEffect(() => {
    setCursor(0)
    setScrollOffset(0)
  }, [needle])

  // Secondary bounds guard — the visible-entries array itself can change
  // (e.g. new entries streamed into the session) independently of the
  // needle.  Clamp cursor + offset to the post-filter length so the
  // invariant `scrollOffset <= cursor < min(filtered.length, scrollOffset +
  // max_rows)` survives those shifts.
  useEffect(() => {
    if (filtered.length === 0) {
      setCursor(0)
      setScrollOffset(0)
      return
    }
    if (cursor >= filtered.length) {
      const nextCursor = filtered.length - 1
      setCursor(nextCursor)
      if (nextCursor < scrollOffset) {
        setScrollOffset(nextCursor)
      }
    }
    // Keep the window anchored to a valid range.  If the list shrank below
    // the current offset, pull the offset back so the cursor stays visible.
    if (scrollOffset > Math.max(0, filtered.length - 1)) {
      setScrollOffset(Math.max(0, filtered.length - 1))
    }
  }, [filtered.length, cursor, scrollOffset])

  // ---- Keystroke handler -------------------------------------------------
  //
  // IME gate (FR-005, D4): when the citizen is composing a Hangul
  // syllable, every buffer-mutating key is consumed by the IME and our
  // local handler returns immediately. Pressing escape mid-composition
  // does NOT close the overlay (it would commit/drop partial jamo).
  //
  // Precedence: this hook is mounted only when the overlay is visible,
  // which means the resolver's `HistorySearch` context (data-model.md §
  // 1) is active and global Tier 1 bindings are suppressed by the
  // resolver layer. We additionally local-handle escape + enter +
  // backspace + arrow keys here for a tight round-trip.

  const handleSelect = useCallback((): void => {
    const entry = filtered[cursor]
    if (entry === undefined) return
    const result = selectHistoryEntry(entry, announcer)
    onSelect(result.next_draft)
  }, [filtered, cursor, announcer, onSelect])

  const handleCancel = useCallback((): void => {
    const result = cancelHistorySearch(request, announcer)
    onCancel(result.next_draft)
  }, [request, announcer, onCancel])

  useInput((input, key) => {
    if (isComposing) return // FR-005 / FR-007 inheritance
    if (key.escape) {
      handleCancel()
      return
    }
    if (key.return) {
      handleSelect()
      return
    }
    if (key.upArrow) {
      // Move cursor up; if it steps above the visible window, scroll the
      // window up in lockstep so the highlighted row stays on screen.
      setCursor((c) => {
        const next = Math.max(0, c - 1)
        setScrollOffset((off) => (next < off ? next : off))
        return next
      })
      return
    }
    if (key.downArrow) {
      // Move cursor down; if it steps past the last visible row and more
      // results exist, scroll the window down so the highlighted row stays
      // on screen.  The `filtered.length - 1` clamp still applies — we
      // never advance past the last entry.
      setCursor((c) => {
        const upperBound = Math.max(0, filtered.length - 1)
        const next = Math.min(upperBound, c + 1)
        setScrollOffset((off) => {
          const lastVisible = off + max_rows - 1
          if (next > lastVisible) {
            // Keep the cursor at the bottom visible row: slide the window.
            return next - max_rows + 1
          }
          return off
        })
        return next
      })
      return
    }
    if (key.backspace || key.delete) {
      setNeedle((s) => s.slice(0, -1))
      return
    }
    // Plain printable input (including IME-committed Hangul syllables) —
    // append to the needle. We accept any non-empty input that isn't a
    // control sequence handled above; Ink delivers IME-committed syllables
    // through the same `input` argument once `useKoreanIME` releases them.
    if (input.length > 0 && !key.ctrl && !key.meta) {
      setNeedle((s) => s + input)
    }
  })

  // ---- Render ------------------------------------------------------------

  // Window slide: the visible rows are the `max_rows` entries starting at
  // `scrollOffset`.  `cursor - scrollOffset` is the offset into `visible`
  // of the highlighted row and is guaranteed to be in `[0, max_rows)` by
  // the handler invariants above.
  const visible = filtered.slice(scrollOffset, scrollOffset + max_rows)
  const overflow = Math.max(0, filtered.length - (scrollOffset + visible.length))
  const cursorInWindow = cursor - scrollOffset

  return (
    <Box flexDirection="column" paddingX={1}>
      <Text bold color={theme.wordmark}>
        이력 검색 / History search
      </Text>
      {request.scope_notice && (
        <Text color={theme.subtitle}>
          ※ 이전 세션 이력은 메모리 동의가 필요합니다 — 현재 세션 결과만
          표시됩니다.
        </Text>
      )}
      <Box marginTop={1}>
        <Text color={theme.kosmosCore}>{`> ${needle}`}</Text>
      </Box>
      <Box marginTop={1} flexDirection="column">
        {visible.length === 0 ? (
          <Text color={theme.subtitle}>일치하는 이력이 없습니다.</Text>
        ) : (
          visible.map((entry, idx) => (
            <Text
              key={`${entry.session_id}:${entry.timestamp}`}
              color={idx === cursorInWindow ? theme.kosmosCore : theme.text}
            >
              {idx === cursorInWindow ? '› ' : '  '}
              {entry.query_text}
            </Text>
          ))
        )}
      </Box>
      {overflow > 0 && (
        <Box marginTop={1}>
          <Text color={theme.subtitle}>
            (+{overflow} more — 화살표로 좁혀보세요)
          </Text>
        </Box>
      )}
      <Box marginTop={1}>
        <Text color={theme.subtitle}>
          Enter 선택 · Esc 취소 · ↑↓ 이동 · Backspace 한 글자 지우기
        </Text>
      </Box>
    </Box>
  )
}
