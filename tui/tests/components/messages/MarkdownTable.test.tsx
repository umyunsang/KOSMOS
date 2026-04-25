// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — MarkdownTable unit tests (T024, FR-011).
//
// Verifies the messages/MarkdownTable.tsx re-export matches the
// top-level MarkdownTable.tsx (1:1 port contract, FR-034).

import { describe, test, expect } from 'bun:test';
import { MarkdownTable as msgMarkdownTable } from '@/components/messages/MarkdownTable.js';
import { MarkdownTable as rootMarkdownTable } from '@/components/MarkdownTable.js';

describe('MarkdownTable re-export (FR-011, FR-034)', () => {
  test('messages/MarkdownTable re-exports the root MarkdownTable', () => {
    // Both exports should point to the same function (identity equality).
    expect(msgMarkdownTable).toBe(rootMarkdownTable);
  });

  test('MarkdownTable is a function (component)', () => {
    expect(typeof rootMarkdownTable).toBe('function');
  });
});
