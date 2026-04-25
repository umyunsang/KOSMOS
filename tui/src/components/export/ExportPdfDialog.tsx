// SPDX-License-Identifier: Apache-2.0
// Source: .references/claude-code-sourcemap/restored-src/src/components/ExportDialog.tsx (CC 2.1.88, research-use)
// Spec 1635 P4 UI L2 — T067 ExportPdfDialog (FR-032, US5).
//
// Assembles a PDF export containing:
//   - Conversation transcript (citizen messages + LLM responses)
//   - Tool invocations and results
//   - Consent receipts (rcpt-<id> entries)
//
// EXCLUDES (SC-012 / FR-032 hard constraint):
//   - OTEL span IDs (traceId=, spanId=)
//   - Plugin-internal state markers (pluginInternal:)
//
// Uses pdf-lib (MIT) for PDF assembly.  Progress indicator follows
// CC ExportDialog pattern (Box + Text stream + done message).

import React, { useCallback, useEffect, useState } from 'react';
import { Box, Text } from 'ink';
import { PDFDocument, StandardFonts, rgb } from 'pdf-lib';
import { useTheme } from '../../theme/provider.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';
import type { PermissionReceiptT } from '../../schemas/ui-l2/permission.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConversationTurn = {
  role: 'citizen' | 'assistant';
  content: string;
  timestamp: string;
};

export type ToolInvocationRecord = {
  tool_name: string;
  input_summary: string;
  output_summary: string;
  timestamp: string;
};

export type ExportPdfDialogProps = {
  /** Conversation turns to include */
  turns: ConversationTurn[];
  /** Tool invocations to include */
  toolInvocations: ToolInvocationRecord[];
  /** Consent receipts to include */
  receipts: PermissionReceiptT[];
  /** Full path where the PDF will be written */
  outputPath: string;
  /** Called when writing is complete */
  onDone: (result: { success: boolean; message: string }) => void;
  /** Called when the citizen cancels before writing starts */
  onCancel: () => void;
};

// ---------------------------------------------------------------------------
// SC-012 leakage filter
// ---------------------------------------------------------------------------

// These patterns MUST NOT appear in the final PDF text (SC-012 / FR-032).
const FORBIDDEN_PATTERNS: RegExp[] = [
  /traceId=[A-Za-z0-9]+/g,
  /spanId=[A-Za-z0-9]+/g,
  /pluginInternal:[^\s]*/g,
];

/**
 * Sanitize a text segment, removing any OTEL or plugin-internal markers.
 * SC-012: "/export PDF contains zero OTEL span identifiers and zero
 * plugin-internal state markers in automated content scans."
 */
export function sanitizeForExport(text: string): string {
  let out = text;
  for (const pattern of FORBIDDEN_PATTERNS) {
    out = out.replace(pattern, '[redacted]');
  }
  return out;
}

// ---------------------------------------------------------------------------
// PDF assembly
// ---------------------------------------------------------------------------

const LINE_HEIGHT = 14;
const FONT_SIZE = 11;
const MARGIN = 50;
const PAGE_WIDTH = 595.28;  // A4
const PAGE_HEIGHT = 841.89; // A4
const TEXT_WIDTH = PAGE_WIDTH - MARGIN * 2;

async function assemblePdf(
  turns: ConversationTurn[],
  toolInvocations: ToolInvocationRecord[],
  receipts: PermissionReceiptT[],
): Promise<Uint8Array> {
  const pdfDoc = await PDFDocument.create();
  const font = await pdfDoc.embedFont(StandardFonts.Helvetica);
  const boldFont = await pdfDoc.embedFont(StandardFonts.HelveticaBold);

  let page = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
  let y = PAGE_HEIGHT - MARGIN;

  const addLine = (text: string, bold = false, color = rgb(0, 0, 0)): void => {
    if (y < MARGIN + LINE_HEIGHT) {
      page = pdfDoc.addPage([PAGE_WIDTH, PAGE_HEIGHT]);
      y = PAGE_HEIGHT - MARGIN;
    }
    const sanitized = sanitizeForExport(text);
    const f = bold ? boldFont : font;
    // Truncate long lines at TEXT_WIDTH
    let displayText = sanitized;
    while (displayText.length > 0) {
      const textWidth = f.widthOfTextAtSize(displayText, FONT_SIZE);
      if (textWidth <= TEXT_WIDTH) break;
      displayText = displayText.slice(0, -1);
    }
    page.drawText(displayText, {
      x: MARGIN,
      y,
      size: FONT_SIZE,
      font: f,
      color,
    });
    y -= LINE_HEIGHT;
  };

  const addSection = (title: string): void => {
    addLine('');
    addLine(title, true, rgb(0.4, 0.1, 0.7));
    addLine('─'.repeat(70));
  };

  // Header
  addLine('KOSMOS — 대화 내보내기 / Conversation Export', true, rgb(0.4, 0.1, 0.7));
  addLine(`생성 시각 / Generated: ${new Date().toISOString()}`);
  addLine('');

  // Section 1: Conversation transcript
  addSection('대화 내역 / Conversation Transcript');
  if (turns.length === 0) {
    addLine('  (내역 없음 / no turns)');
  } else {
    for (const turn of turns) {
      const prefix = turn.role === 'citizen' ? '시민' : 'KOSMOS';
      addLine(`[${turn.timestamp}] ${prefix}:`);
      // Word-wrap content (simple: split at 80 chars)
      const content = sanitizeForExport(turn.content);
      for (let i = 0; i < content.length; i += 80) {
        addLine(`  ${content.slice(i, i + 80)}`);
      }
      addLine('');
    }
  }

  // Section 2: Tool invocations
  addSection('도구 호출 / Tool Invocations');
  if (toolInvocations.length === 0) {
    addLine('  (호출 없음 / no invocations)');
  } else {
    for (const inv of toolInvocations) {
      addLine(`[${inv.timestamp}] ${inv.tool_name}`, true);
      addLine(`  입력 / Input: ${sanitizeForExport(inv.input_summary)}`);
      addLine(`  결과 / Output: ${sanitizeForExport(inv.output_summary)}`);
      addLine('');
    }
  }

  // Section 3: Consent receipts
  addSection('권한 영수증 / Consent Receipts');
  if (receipts.length === 0) {
    addLine('  (영수증 없음 / no receipts)');
  } else {
    for (const receipt of receipts) {
      addLine(`${receipt.receipt_id}`, true);
      addLine(`  Layer: ${receipt.layer}  Tool: ${receipt.tool_name}`);
      addLine(`  Decision: ${receipt.decision}  At: ${receipt.decided_at}`);
      if (receipt.revoked_at) {
        addLine(`  Revoked: ${receipt.revoked_at}`);
      }
      addLine('');
    }
  }

  return pdfDoc.save();
}

// ---------------------------------------------------------------------------
// ExportPdfDialog (T067)
// ---------------------------------------------------------------------------

type ExportState = 'idle' | 'writing' | 'done' | 'error';

/**
 * PDF export dialog component.  Immediately triggers assembly when mounted
 * (no user interaction required to start writing — mirrors CC ExportDialog).
 *
 * SC-012 guarantee: sanitizeForExport() strips traceId=, spanId=, and
 * pluginInternal: markers from ALL text content before writing to PDF.
 */
export function ExportPdfDialog({
  turns,
  toolInvocations,
  receipts,
  outputPath,
  onDone,
}: ExportPdfDialogProps): React.ReactElement {
  const theme = useTheme();
  const i18n = useUiL2I18n();
  const [state, setState] = useState<ExportState>('idle');
  const [errorMessage, setErrorMessage] = useState<string>('');

  const runExport = useCallback(async () => {
    setState('writing');
    try {
      const bytes = await assemblePdf(turns, toolInvocations, receipts);
      // Write using Node.js fs (no new deps — stdlib)
      const { writeFileSync, mkdirSync, dirname: pathDirname } = await import('node:fs');
      const { dirname } = await import('node:path');
      mkdirSync(dirname(outputPath), { recursive: true });
      writeFileSync(outputPath, bytes);
      setState('done');
      onDone({ success: true, message: i18n.exportPdfDone(outputPath) });
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
      setState('error');
      onDone({ success: false, message: `Export failed: ${msg}` });
    }
  }, [turns, toolInvocations, receipts, outputPath, onDone, i18n]);

  useEffect(() => {
    void runExport();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      {state === 'idle' && (
        <Text color={theme.subtle}>{i18n.exportPdfWriting}</Text>
      )}
      {state === 'writing' && (
        <Box>
          <Text color={theme.kosmosCore}>{'⏳ '}</Text>
          <Text color={theme.text}>{i18n.exportPdfWriting}</Text>
        </Box>
      )}
      {state === 'done' && (
        <Box>
          <Text color={theme.success}>{'✓ '}</Text>
          <Text color={theme.text}>{i18n.exportPdfDone(outputPath)}</Text>
        </Box>
      )}
      {state === 'error' && (
        <Box flexDirection="column">
          <Box>
            <Text color={theme.error}>{'✗ Export failed: '}</Text>
            <Text color={theme.text}>{errorMessage}</Text>
          </Box>
        </Box>
      )}
    </Box>
  );
}
