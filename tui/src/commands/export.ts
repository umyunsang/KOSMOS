// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — T068 /export command (FR-032, US5).
//
// Writes a PDF to the platform-default download location.
// Emits kosmos.ui.surface=export (FR-037).
//
// SC-012: sanitizeForExport() in ExportPdfDialog ensures zero OTEL span IDs
// and zero plugin-internal markers in the output PDF.

import { homedir } from 'node:os';
import { join } from 'node:path';
import { emitSurfaceActivation } from '../observability/surface.js';
import type { ConversationTurn, ToolInvocationRecord } from '../components/export/ExportPdfDialog.js';
import type { PermissionReceiptT } from '../schemas/ui-l2/permission.js';

// ---------------------------------------------------------------------------
// Platform-default download path
// ---------------------------------------------------------------------------

function getDefaultDownloadPath(): string {
  // macOS and Linux: ~/Downloads
  // Fallback: home directory
  const downloadsDir = join(homedir(), 'Downloads');
  return downloadsDir;
}

function buildOutputPath(): string {
  const now = new Date();
  const timestamp = now.toISOString().replace(/[:.]/g, '-').replace('T', '_').replace('Z', '');
  return join(getDefaultDownloadPath(), `kosmos-export_${timestamp}.pdf`);
}

// ---------------------------------------------------------------------------
// Result type
// ---------------------------------------------------------------------------

export type ExportCommandResult = {
  /** Where the PDF will be written */
  outputPath: string;
  /** Conversation turns snapshot */
  turns: ConversationTurn[];
  /** Tool invocations snapshot */
  toolInvocations: ToolInvocationRecord[];
  /** Consent receipts snapshot */
  receipts: PermissionReceiptT[];
};

// ---------------------------------------------------------------------------
// Command handler (T068)
// ---------------------------------------------------------------------------

/**
 * Execute the /export command.
 *
 * Emits `kosmos.ui.surface=export` (FR-037) and returns the data to render
 * in ExportPdfDialog.  The actual PDF write happens inside the component
 * via pdf-lib (T067).
 *
 * @param turns            Conversation turns from the active session
 * @param toolInvocations  Tool call records from the active session
 * @param receipts         Consent receipts from the active session
 */
export function executeExport(
  turns: ConversationTurn[],
  toolInvocations: ToolInvocationRecord[],
  receipts: PermissionReceiptT[],
): ExportCommandResult {
  // FR-037: emit surface activation at command start
  emitSurfaceActivation('export');

  return {
    outputPath: buildOutputPath(),
    turns,
    toolInvocations,
    receipts,
  };
}
