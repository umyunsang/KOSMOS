// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T071 /help command tests (FR-029, US5).

import { describe, it, expect } from 'bun:test';
import { executeHelp } from '../../src/commands/help.js';
import { GROUP_ORDER } from '../../src/schemas/ui-l2/slash-command.js';

describe('executeHelp — 4-group output (FR-029)', () => {
  it('returns a text string and groups object', () => {
    const result = executeHelp('ko');
    expect(typeof result.text).toBe('string');
    expect(typeof result.groups).toBe('object');
  });

  it('groups object has all four canonical groups', () => {
    const result = executeHelp('ko');
    for (const g of GROUP_ORDER) {
      expect(Object.keys(result.groups)).toContain(g);
    }
  });

  it('text output contains all four group labels in Korean', () => {
    const result = executeHelp('ko');
    expect(result.text).toContain('세션');
    expect(result.text).toContain('권한');
    expect(result.text).toContain('도구');
    expect(result.text).toContain('저장');
  });

  it('text output contains all four group labels in English', () => {
    const result = executeHelp('en');
    expect(result.text).toContain('Session');
    expect(result.text).toContain('Permission');
    expect(result.text).toContain('Tool');
    expect(result.text).toContain('Storage');
  });

  it('text output contains known command names', () => {
    const result = executeHelp('ko');
    expect(result.text).toContain('/help');
    expect(result.text).toContain('/consent list');
    expect(result.text).toContain('/plugins');
    expect(result.text).toContain('/export');
    expect(result.text).toContain('/history');
  });

  it('groups.session is non-empty', () => {
    const result = executeHelp('ko');
    expect(result.groups.session.length).toBeGreaterThan(0);
  });

  it('groups.permission is non-empty', () => {
    const result = executeHelp('ko');
    expect(result.groups.permission.length).toBeGreaterThan(0);
  });

  it('groups.tool is non-empty', () => {
    const result = executeHelp('ko');
    expect(result.groups.tool.length).toBeGreaterThan(0);
  });

  it('groups.storage is non-empty', () => {
    const result = executeHelp('ko');
    expect(result.groups.storage.length).toBeGreaterThan(0);
  });
});
