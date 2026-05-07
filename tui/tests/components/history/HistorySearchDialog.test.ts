// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T071 history component tests (FR-033, US5).

import { describe, it, expect } from 'bun:test';
import {
  applyHistoryFilters,
  type SessionHistoryEntry,
  type HistorySearchFilters,
} from '../../../src/components/history/HistorySearchDialog.js';

// ---------------------------------------------------------------------------
// Test fixture
// ---------------------------------------------------------------------------

const SESSIONS: SessionHistoryEntry[] = [
  {
    session_id: 'session-aaa-111',
    started_at: '2026-04-01T10:00:00Z',
    last_active_at: '2026-04-01T10:30:00Z',
    preview: '의료급여 신청 방법 안내',
    layers_touched: [1, 2],
  },
  {
    session_id: 'session-bbb-222',
    started_at: '2026-04-15T14:00:00Z',
    last_active_at: '2026-04-15T14:45:00Z',
    preview: '운전면허 갱신 절차',
    layers_touched: [1],
  },
  {
    session_id: 'session-ccc-333',
    started_at: '2026-04-20T09:00:00Z',
    last_active_at: '2026-04-20T09:15:00Z',
    preview: '주민등록증 발급 (Layer 3 도구)',
    layers_touched: [1, 3],
  },
  {
    session_id: 'session-ddd-444',
    started_at: '2026-04-25T08:00:00Z',
    last_active_at: '2026-04-25T08:30:00Z',
    preview: '날씨 정보 조회',
    layers_touched: [],
  },
];

function emptyFilters(): HistorySearchFilters {
  return { dateRange: null, sessionId: null, layer: null };
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('applyHistoryFilters — AND composition (FR-033)', () => {
  it('no filters returns all sessions', () => {
    const result = applyHistoryFilters(SESSIONS, emptyFilters());
    expect(result).toHaveLength(SESSIONS.length);
  });

  it('--date filter: returns sessions in range', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      dateRange: { from: '2026-04-14', to: '2026-04-16' },
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-bbb-222');
  });

  it('--date filter: excludes sessions outside range', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      dateRange: { from: '2026-04-24', to: '2026-04-25' },
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-ddd-444');
  });

  it('--session filter: returns sessions containing the partial ID', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      sessionId: 'ccc',
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-ccc-333');
  });

  it('--layer filter: returns sessions that touched that layer', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      layer: 3,
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-ccc-333');
  });

  it('--layer 2: returns sessions with layer 2', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      layer: 2,
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-aaa-111');
  });

  it('--layer 1: returns all sessions that touched layer 1', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      layer: 1,
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    // session-aaa, session-bbb, session-ccc all have layer 1
    expect(result).toHaveLength(3);
  });

  it('AND composition: --date + --layer narrows results', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      dateRange: { from: '2026-04-01', to: '2026-04-10' },
      layer: 2,
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-aaa-111');
  });

  it('AND composition: --date + --session zero result when no match', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      dateRange: { from: '2026-04-01', to: '2026-04-05' },
      sessionId: 'bbb', // session-bbb is on 04-15, outside range
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(0);
  });

  it('AND composition: all three filters together', () => {
    const filters: HistorySearchFilters = {
      dateRange: { from: '2026-04-01', to: '2026-04-10' },
      sessionId: 'aaa',
      layer: 2,
    };
    const result = applyHistoryFilters(SESSIONS, filters);
    expect(result).toHaveLength(1);
    expect(result[0]?.session_id).toBe('session-aaa-111');
  });

  it('empty sessions returns empty result regardless of filters', () => {
    const filters: HistorySearchFilters = {
      ...emptyFilters(),
      layer: 1,
    };
    const result = applyHistoryFilters([], filters);
    expect(result).toHaveLength(0);
  });
});
