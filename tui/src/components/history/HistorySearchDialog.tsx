// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/components/HistorySearchDialog.tsx (CC 2.1.88, research-use)
// Spec 1635 P4 UI L2 — T069 HistorySearchDialog (FR-033, US5).
//
// 3-filter session history search:
//   --date FROM..TO      date range (ISO date prefix: YYYY-MM-DD)
//   --session <id>       exact session UUID match
//   --layer <n>          Layer integer (1, 2, or 3) — sessions that touched
//                        at least one tool of that layer
//
// Filters are AND-composed (FR-033): a session must pass ALL active filters.
//
// Structural shape mirrors CC HistorySearchDialog with KOSMOS-specific
// 3-filter form replacing the single needle input.

import React, { useCallback, useMemo, useState } from 'react';
import { Box, Text, useInput } from 'ink';
import { useTheme } from '../../theme/provider.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';
import { useKoreanIME } from '../../hooks/useKoreanIME.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type SessionHistoryEntry = {
  session_id: string;
  /** ISO datetime of first turn */
  started_at: string;
  /** ISO datetime of last activity */
  last_active_at: string;
  /** Short preview of the first citizen message */
  preview: string;
  /** Layers touched (set of 1, 2, 3) — for --layer filter */
  layers_touched: number[];
};

export type HistorySearchFilters = {
  /** date range — ISO date prefix (YYYY-MM-DD..YYYY-MM-DD) */
  dateRange: { from: string; to: string } | null;
  /** Exact session UUID */
  sessionId: string | null;
  /** Layer integer (1|2|3) */
  layer: number | null;
};

export type HistorySearchDialogProps = {
  /** Available sessions from memdir */
  sessions: SessionHistoryEntry[];
  /** Called with the selected session ID when the citizen presses Enter */
  onSelect: (sessionId: string) => void;
  /** Called when the citizen cancels (Escape) */
  onCancel: () => void;
  /** Maximum visible result rows */
  maxRows?: number;
};

// ---------------------------------------------------------------------------
// Filtering logic (AND composition — FR-033)
// ---------------------------------------------------------------------------

/**
 * Apply all active filters with AND semantics.
 * A session must pass every non-null filter to appear in results.
 */
export function applyHistoryFilters(
  sessions: SessionHistoryEntry[],
  filters: HistorySearchFilters,
): SessionHistoryEntry[] {
  return sessions.filter((session) => {
    // --date filter
    if (filters.dateRange !== null) {
      const { from, to } = filters.dateRange;
      const startedDate = session.started_at.slice(0, 10); // YYYY-MM-DD
      if (startedDate < from || startedDate > to) return false;
    }

    // --session filter
    if (filters.sessionId !== null) {
      if (!session.session_id.includes(filters.sessionId)) return false;
    }

    // --layer filter
    if (filters.layer !== null) {
      if (!session.layers_touched.includes(filters.layer)) return false;
    }

    return true;
  });
}

// ---------------------------------------------------------------------------
// Filter input parsing
// ---------------------------------------------------------------------------

function parseFilters(raw: string): HistorySearchFilters {
  const filters: HistorySearchFilters = {
    dateRange: null,
    sessionId: null,
    layer: null,
  };

  // --date FROM..TO
  const dateMatch = raw.match(/--date\s+(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})/);
  if (dateMatch) {
    filters.dateRange = { from: dateMatch[1]!, to: dateMatch[2]! };
  }

  // --session <id>
  const sessionMatch = raw.match(/--session\s+([A-Za-z0-9_-]+)/);
  if (sessionMatch) {
    filters.sessionId = sessionMatch[1]!;
  }

  // --layer <n>
  const layerMatch = raw.match(/--layer\s+([123])/);
  if (layerMatch) {
    filters.layer = parseInt(layerMatch[1]!, 10);
  }

  return filters;
}

// ---------------------------------------------------------------------------
// HistorySearchDialog (T069)
// ---------------------------------------------------------------------------

const DEFAULT_MAX_ROWS = 8;

/**
 * History search dialog with 3 AND-composed filters (FR-033).
 *
 * The citizen types filter flags directly into the needle field:
 *   --date 2026-04-01..2026-04-25
 *   --session abc123
 *   --layer 2
 *
 * Flags can be combined freely:
 *   --date 2026-04-01..2026-04-25 --layer 2
 *
 * Results update live as the citizen types.
 */
export function HistorySearchDialog({
  sessions,
  onSelect,
  onCancel,
  maxRows = DEFAULT_MAX_ROWS,
}: HistorySearchDialogProps): React.ReactElement {
  const theme = useTheme();
  const i18n = useUiL2I18n();
  const { isComposing } = useKoreanIME();

  const [needle, setNeedle] = useState('');
  const [cursor, setCursor] = useState(0);
  const [scrollOffset, setScrollOffset] = useState(0);

  const filters = useMemo(() => parseFilters(needle), [needle]);

  const filtered = useMemo(
    () => applyHistoryFilters(sessions, filters),
    [sessions, filters],
  );

  // Reset cursor on filter change
  const prevFiltered = useMemo(() => filtered, [filtered]);
  if (filtered !== prevFiltered) {
    setCursor(0);
    setScrollOffset(0);
  }

  const clampCursor = useCallback(
    (c: number) => Math.min(Math.max(0, c), Math.max(0, filtered.length - 1)),
    [filtered.length],
  );

  useInput((input, key) => {
    if (isComposing) return;

    if (key.escape) { onCancel(); return; }
    if (key.return) {
      const entry = filtered[cursor];
      if (entry) onSelect(entry.session_id);
      return;
    }
    if (key.upArrow) {
      setCursor((c) => {
        const next = clampCursor(c - 1);
        setScrollOffset((off) => (next < off ? next : off));
        return next;
      });
      return;
    }
    if (key.downArrow) {
      setCursor((c) => {
        const next = clampCursor(c + 1);
        setScrollOffset((off) => {
          const lastVisible = off + maxRows - 1;
          return next > lastVisible ? next - maxRows + 1 : off;
        });
        return next;
      });
      return;
    }
    if (key.backspace || key.delete) {
      setNeedle((s) => s.slice(0, -1));
      setCursor(0);
      setScrollOffset(0);
      return;
    }
    if (!key.ctrl && !key.meta && input.length > 0) {
      setNeedle((s) => s + input);
      setCursor(0);
      setScrollOffset(0);
    }
  });

  const visible = filtered.slice(scrollOffset, scrollOffset + maxRows);
  const overflow = Math.max(0, filtered.length - (scrollOffset + visible.length));
  const cursorInWindow = cursor - scrollOffset;

  return (
    <Box flexDirection="column" paddingX={1}>
      {/* Title */}
      <Text bold color={theme.wordmark}>{i18n.historySearchTitle}</Text>

      {/* Filter input */}
      <Box marginTop={1}>
        <Text color={theme.kosmosCore}>{`> ${needle}`}</Text>
        <Text color={theme.subtle}>{'█'}</Text>
      </Box>

      {/* Filter hint */}
      <Box marginTop={0}>
        <Text dimColor>
          {'--date YYYY-MM-DD..YYYY-MM-DD  --session <id>  --layer <1|2|3>'}
        </Text>
      </Box>

      {/* Results */}
      <Box marginTop={1} flexDirection="column">
        {visible.length === 0 ? (
          <Text color={theme.subtle}>
            {needle.length > 0 ? '일치하는 세션이 없습니다 · No sessions match' : '세션 없음 · No sessions'}
          </Text>
        ) : (
          visible.map((entry, idx) => (
            <Box key={entry.session_id}>
              <Text
                color={idx === cursorInWindow ? theme.kosmosCore : theme.text}
                bold={idx === cursorInWindow}
              >
                {idx === cursorInWindow ? '› ' : '  '}
                {entry.started_at.slice(0, 10)}
                {'  '}
                {entry.session_id.slice(0, 12)}
                {'…  '}
                {entry.preview.slice(0, 40)}
              </Text>
            </Box>
          ))
        )}
      </Box>

      {/* Overflow indicator */}
      {overflow > 0 && (
        <Box marginTop={1}>
          <Text color={theme.subtle}>
            {`+${overflow} more · ↑↓로 탐색`}
          </Text>
        </Box>
      )}

      {/* Footer */}
      <Box marginTop={1}>
        <Text dimColor>
          {'Enter 선택 · Esc 취소 · ↑↓ 이동 · Backspace 지우기'}
        </Text>
      </Box>
    </Box>
  );
}
