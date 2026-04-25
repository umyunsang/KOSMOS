// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T071 /history command tests (FR-033, US5).

import { describe, it, expect } from 'bun:test';
import { executeHistory } from '../../src/commands/history.js';

describe('executeHistory (FR-033)', () => {
  it('returns sessions, appliedFilters, and filteredSessions', () => {
    const result = executeHistory();
    expect(Array.isArray(result.sessions)).toBe(true);
    expect(typeof result.appliedFilters).toBe('object');
    expect(Array.isArray(result.filteredSessions)).toBe(true);
  });

  it('no args → all filters are null', () => {
    const result = executeHistory('');
    expect(result.appliedFilters.dateRange).toBeNull();
    expect(result.appliedFilters.sessionId).toBeNull();
    expect(result.appliedFilters.layer).toBeNull();
  });

  it('parses --date filter from args string', () => {
    const result = executeHistory('--date 2026-04-01..2026-04-25');
    expect(result.appliedFilters.dateRange).not.toBeNull();
    expect(result.appliedFilters.dateRange?.from).toBe('2026-04-01');
    expect(result.appliedFilters.dateRange?.to).toBe('2026-04-25');
  });

  it('parses --session filter from args string', () => {
    const result = executeHistory('--session abc-123');
    expect(result.appliedFilters.sessionId).toBe('abc-123');
  });

  it('parses --layer filter from args string', () => {
    const result = executeHistory('--layer 2');
    expect(result.appliedFilters.layer).toBe(2);
  });

  it('parses combined --date + --session + --layer', () => {
    const result = executeHistory('--date 2026-04-01..2026-04-30 --session xyz --layer 3');
    expect(result.appliedFilters.dateRange?.from).toBe('2026-04-01');
    expect(result.appliedFilters.sessionId).toBe('xyz');
    expect(result.appliedFilters.layer).toBe(3);
  });

  it('filteredSessions is a subset of sessions', () => {
    const result = executeHistory();
    for (const fs of result.filteredSessions) {
      const found = result.sessions.some((s) => s.session_id === fs.session_id);
      expect(found).toBe(true);
    }
  });

  it('layer values accepted: 1, 2, 3', () => {
    for (const layer of [1, 2, 3]) {
      const result = executeHistory(`--layer ${layer}`);
      expect(result.appliedFilters.layer).toBe(layer);
    }
  });

  it('invalid layer value is not parsed (returns null)', () => {
    const result = executeHistory('--layer 5');
    expect(result.appliedFilters.layer).toBeNull();
  });
});
