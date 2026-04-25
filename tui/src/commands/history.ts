// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T070 /history command (FR-033, US5).
//
// 3-filter session history search with AND composition.
// Emits kosmos.ui.surface=history (FR-037).
//
// Session data is loaded from ~/.kosmos/memdir/user/sessions/ (Spec 027).
// Each JSONL file is a session; the command enumerates them and builds
// SessionHistoryEntry objects for HistorySearchDialog.

import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { homedir } from 'node:os';
import { emitSurfaceActivation } from '../observability/surface.js';
import {
  applyHistoryFilters,
  type HistorySearchFilters,
  type SessionHistoryEntry,
} from '../components/history/HistorySearchDialog.js';

// ---------------------------------------------------------------------------
// Session reader
// ---------------------------------------------------------------------------

const SESSIONS_DIR = join(homedir(), '.kosmos', 'memdir', 'user', 'sessions');

/**
 * Enumerate sessions from the Spec 027 memdir path.
 *
 * Each session is a JSONL file `<session_id>.jsonl`.  The first line is the
 * session header (JSON object with `session_id`, `started_at`, and optionally
 * `preview`).  We read only the first line to keep this fast.
 */
function loadSessionEntries(): SessionHistoryEntry[] {
  const entries: SessionHistoryEntry[] = [];

  let files: string[];
  try {
    files = readdirSync(SESSIONS_DIR);
  } catch {
    // Sessions directory doesn't exist yet — return empty
    return [];
  }

  for (const file of files) {
    if (!file.endsWith('.jsonl')) continue;
    const sessionId = file.replace(/\.jsonl$/, '');
    const filePath = join(SESSIONS_DIR, file);

    try {
      const content = readFileSync(filePath, { encoding: 'utf-8' });
      const firstLine = content.split('\n')[0] ?? '';
      if (!firstLine.trim()) continue;

      // Parse first JSONL entry as session header
      const header = JSON.parse(firstLine) as Record<string, unknown>;

      // Extract layers_touched from all lines (scan for layer annotations)
      const layersTouched = new Set<number>();
      for (const line of content.split('\n')) {
        if (!line.trim()) continue;
        try {
          const entry = JSON.parse(line) as Record<string, unknown>;
          const layer = entry['permission_layer'];
          if (typeof layer === 'number' && [1, 2, 3].includes(layer)) {
            layersTouched.add(layer);
          }
        } catch {
          // skip malformed lines
        }
      }

      entries.push({
        session_id: typeof header['session_id'] === 'string' ? header['session_id'] : sessionId,
        started_at: typeof header['started_at'] === 'string' ? header['started_at'] : new Date(0).toISOString(),
        last_active_at: typeof header['last_active_at'] === 'string' ? header['last_active_at'] : new Date(0).toISOString(),
        preview: typeof header['preview'] === 'string' ? header['preview'] : '',
        layers_touched: [...layersTouched],
      });
    } catch {
      // Skip unreadable or malformed session files
    }
  }

  // Sort descending by started_at (most recent first)
  entries.sort((a, b) => b.started_at.localeCompare(a.started_at));

  return entries;
}

// ---------------------------------------------------------------------------
// Result type
// ---------------------------------------------------------------------------

export type HistoryCommandResult = {
  /** All sessions loaded from memdir */
  sessions: SessionHistoryEntry[];
  /** Pre-applied filters (from CLI args) */
  appliedFilters: HistorySearchFilters;
  /** Pre-filtered results */
  filteredSessions: SessionHistoryEntry[];
};

// ---------------------------------------------------------------------------
// Command handler (T070)
// ---------------------------------------------------------------------------

/**
 * Execute the /history command with optional pre-applied filters.
 *
 * Emits `kosmos.ui.surface=history` (FR-037).
 *
 * @param args  Raw arguments string (e.g. "--date 2026-04-01..2026-04-25 --layer 2")
 */
export function executeHistory(args: string = ''): HistoryCommandResult {
  // FR-037: emit surface activation at command start
  emitSurfaceActivation('history');

  const sessions = loadSessionEntries();

  // Parse filters from CLI args
  const appliedFilters: HistorySearchFilters = {
    dateRange: null,
    sessionId: null,
    layer: null,
  };

  const dateMatch = args.match(/--date\s+(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})/);
  if (dateMatch) {
    appliedFilters.dateRange = { from: dateMatch[1]!, to: dateMatch[2]! };
  }

  const sessionMatch = args.match(/--session\s+([A-Za-z0-9_-]+)/);
  if (sessionMatch) {
    appliedFilters.sessionId = sessionMatch[1]!;
  }

  const layerMatch = args.match(/--layer\s+([123])/);
  if (layerMatch) {
    appliedFilters.layer = parseInt(layerMatch[1]!, 10);
  }

  const filteredSessions = applyHistoryFilters(sessions, appliedFilters);

  return { sessions, appliedFilters, filteredSessions };
}
