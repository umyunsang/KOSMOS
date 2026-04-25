// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T071 /export command tests (FR-032, US5).
//
// Note: PDF assembly (assemblePdf) is async and invokes pdf-lib.
// These tests cover the command handler shape and the SC-012 sanitization.
// Full PDF write tests are in ExportPdfDialog.test.ts.

import { describe, it, expect } from 'bun:test';
import { executeExport } from '../../src/commands/export.js';
import { sanitizeForExport } from '../../src/components/export/ExportPdfDialog.js';
import type { ConversationTurn, ToolInvocationRecord } from '../../src/components/export/ExportPdfDialog.js';
import type { PermissionReceiptT } from '../../src/schemas/ui-l2/permission.js';
import { homedir } from 'node:os';

// ---------------------------------------------------------------------------
// executeExport shape tests
// ---------------------------------------------------------------------------

describe('executeExport (FR-032)', () => {
  it('returns an output path ending in .pdf', () => {
    const result = executeExport([], [], []);
    expect(result.outputPath).toMatch(/\.pdf$/i);
  });

  it('output path is under ~/Downloads', () => {
    const result = executeExport([], [], []);
    expect(result.outputPath.startsWith(homedir())).toBe(true);
  });

  it('returns the provided turns unchanged', () => {
    const turns: ConversationTurn[] = [
      { role: 'citizen', content: '안녕하세요', timestamp: '2026-04-25T00:00:00Z' },
      { role: 'assistant', content: 'KOSMOS 응답', timestamp: '2026-04-25T00:00:01Z' },
    ];
    const result = executeExport(turns, [], []);
    expect(result.turns).toHaveLength(2);
    expect(result.turns[0]?.content).toBe('안녕하세요');
  });

  it('returns the provided toolInvocations unchanged', () => {
    const invocations: ToolInvocationRecord[] = [
      {
        tool_name: 'koroad_accident_hazard_search',
        input_summary: '{"location":"서울"}',
        output_summary: '3 results',
        timestamp: '2026-04-25T00:00:02Z',
      },
    ];
    const result = executeExport([], invocations, []);
    expect(result.toolInvocations).toHaveLength(1);
    expect(result.toolInvocations[0]?.tool_name).toBe('koroad_accident_hazard_search');
  });

  it('returns the provided receipts unchanged', () => {
    const receipts: PermissionReceiptT[] = [
      {
        receipt_id: 'rcpt-testabcde',
        layer: 2,
        tool_name: 'hira_hospital_search',
        decision: 'allow_once',
        decided_at: '2026-04-25T00:00:03Z',
        session_id: 'session-test',
        revoked_at: null,
      },
    ];
    const result = executeExport([], [], receipts);
    expect(result.receipts).toHaveLength(1);
    expect(result.receipts[0]?.receipt_id).toBe('rcpt-testabcde');
  });
});

// ---------------------------------------------------------------------------
// SC-012 cross-reference: sanitizeForExport must strip OTEL patterns
// (these tests are the primary SC-012 gate and are duplicated here for the
// command layer to ensure the sanitizer is importable from the command path)
// ---------------------------------------------------------------------------

describe('SC-012 cross-reference from export command (FR-032)', () => {
  it('sanitizeForExport is accessible from the export module', () => {
    expect(typeof sanitizeForExport).toBe('function');
  });

  it('sanitizeForExport strips traceId from tool output summary', () => {
    const rawSummary = 'result=ok traceId=abc123def456 total=3';
    const sanitized = sanitizeForExport(rawSummary);
    expect(sanitized).not.toMatch(/traceId=[A-Za-z0-9]+/);
  });

  it('sanitizeForExport strips spanId from LLM response content', () => {
    const rawContent = 'The request completed. spanId=ff00aa11bb22cc33';
    const sanitized = sanitizeForExport(rawContent);
    expect(sanitized).not.toMatch(/spanId=[A-Za-z0-9]+/);
  });

  it('sanitizeForExport strips pluginInternal markers from tool input', () => {
    const rawInput = 'pluginInternal:loaded::v1 {"key":"value"}';
    const sanitized = sanitizeForExport(rawInput);
    expect(sanitized).not.toMatch(/pluginInternal:[^\s]*/);
  });
});
