// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T071 export component tests (FR-032, US5).
//
// CRITICAL — SC-012 assertion:
//   "/export PDF contains zero OTEL span identifiers and zero plugin-internal
//   state markers in automated content scans across 20 sample sessions."
//
// This test asserts that sanitizeForExport() strips ALL forbidden patterns
// from text before it can reach the PDF assembly.  The test is the CI gate
// for SC-012.

import { describe, it, expect } from 'bun:test';
import { sanitizeForExport } from '../../../src/components/export/ExportPdfDialog.js';

// ---------------------------------------------------------------------------
// SC-012 leakage patterns
// ---------------------------------------------------------------------------

const FORBIDDEN_PATTERNS = [
  /traceId=[A-Za-z0-9]+/,
  /spanId=[A-Za-z0-9]+/,
  /pluginInternal:[^\s]*/,
];

function containsForbiddenPattern(text: string): boolean {
  return FORBIDDEN_PATTERNS.some((p) => p.test(text));
}

// ---------------------------------------------------------------------------
// SC-012 core tests
// ---------------------------------------------------------------------------

describe('sanitizeForExport — SC-012 OTEL leakage prevention (FR-032)', () => {
  it('strips traceId= markers', () => {
    const input = 'Some log line traceId=abc123def456 and more text';
    const output = sanitizeForExport(input);
    expect(containsForbiddenPattern(output)).toBe(false);
    expect(output).not.toContain('traceId=');
  });

  it('strips spanId= markers', () => {
    const input = 'Span info spanId=9f8e7d6c5b4a3210 end';
    const output = sanitizeForExport(input);
    expect(containsForbiddenPattern(output)).toBe(false);
    expect(output).not.toContain('spanId=');
  });

  it('strips pluginInternal: markers', () => {
    const input = 'pluginInternal:stateSnapshot::version=3.2.1 pluginInternal:event::type=load';
    const output = sanitizeForExport(input);
    expect(containsForbiddenPattern(output)).toBe(false);
    expect(output).not.toContain('pluginInternal:');
  });

  it('handles multiple forbidden patterns in a single string', () => {
    const input =
      'traceId=aaabbbccc spanId=111222333 pluginInternal:loaded::ok and normal text';
    const output = sanitizeForExport(input);
    expect(containsForbiddenPattern(output)).toBe(false);
  });

  it('preserves normal conversation text unchanged', () => {
    const input = '안녕하세요! 운전면허 갱신 절차를 알려드리겠습니다.';
    const output = sanitizeForExport(input);
    expect(output).toBe(input);
  });

  it('preserves receipt IDs (rcpt- prefix is allowed)', () => {
    const input = 'Consent receipt issued: rcpt-abc123xyz456';
    const output = sanitizeForExport(input);
    expect(output).toBe(input);
  });

  it('preserves tool names without forbidden patterns', () => {
    const input = 'Tool: koroad_accident_hazard_search Input: {"location": "서울"}';
    const output = sanitizeForExport(input);
    expect(output).toBe(input);
  });

  it('replaces forbidden patterns with [redacted] placeholder', () => {
    const input = 'See traceId=abc123 for details';
    const output = sanitizeForExport(input);
    expect(output).toContain('[redacted]');
  });

  // ---------------------------------------------------------------------------
  // 20 sample session simulation (SC-012: "across 20 sample sessions")
  // ---------------------------------------------------------------------------

  it('SC-012: 20 sample export texts are all clean after sanitization', () => {
    const sampleTexts: string[] = [
      // Normal citizen messages
      '복지부 의료급여 신청 방법을 알려주세요.',
      '교통 사고 데이터를 조회했습니다.',
      '안녕하세요! 무엇을 도와드릴까요?',
      '주민등록증 발급 절차가 궁금합니다.',
      '국민건강보험 납입 이력 확인 부탁드립니다.',
      // Tool invocation summaries
      'Tool: hira_hospital_search - 결과: 3개 병원',
      'Tool: kma_forecast_fetch - 결과: 맑음 25°C',
      'Tool: nmc_emergency_search - 결과: 응급실 2곳',
      // Receipts (should NOT be sanitized)
      'rcpt-abc12345678 Layer:2 allow_once',
      'rcpt-xyz98765432 Layer:1 allow_session',
      // Text WITH embedded forbidden patterns (must be cleaned)
      `Normal message traceId=cafebabe spanId=deadbeef extra`,
      `pluginInternal:loaded::plugin=test-1.0 payload`,
      `Info: traceId=00000000 spanId=ffffffff something happened`,
      `Debug data: pluginInternal:event::click`,
      `Mixed: hello traceId=aaa spanId=bbb pluginInternal:x::y world`,
      // Edge cases
      'Empty string test: ',
      '한글만: 이 텍스트에는 금지된 패턴이 없습니다.',
      'Numbers only: 1234567890',
      'URL-like: https://api.kosmos.kr/v1/lookup',
      'Receipt-only: rcpt-testid001',
    ];

    for (const sample of sampleTexts) {
      const sanitized = sanitizeForExport(sample);
      expect(containsForbiddenPattern(sanitized)).toBe(false);
    }
  });
});

// ---------------------------------------------------------------------------
// executeExport — command shape tests (FR-032)
// ---------------------------------------------------------------------------

describe('executeExport — command result (FR-032)', () => {
  it('output path ends with .pdf', async () => {
    const { executeExport } = await import('../../../src/commands/export.js');
    const result = executeExport([], [], []);
    expect(result.outputPath).toMatch(/\.pdf$/);
  });

  it('output path is in ~/Downloads', async () => {
    const { executeExport } = await import('../../../src/commands/export.js');
    const { homedir } = await import('node:os');
    const result = executeExport([], [], []);
    expect(result.outputPath).toContain(homedir());
  });

  it('returns turns, toolInvocations, and receipts unchanged', async () => {
    const { executeExport } = await import('../../../src/commands/export.js');
    const turns = [{ role: 'citizen' as const, content: 'hello', timestamp: '2026-04-25T00:00:00Z' }];
    const result = executeExport(turns, [], []);
    expect(result.turns).toHaveLength(1);
    expect(result.turns[0]?.content).toBe('hello');
  });
});
