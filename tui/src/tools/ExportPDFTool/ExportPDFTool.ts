// SPDX-License-Identifier: Apache-2.0
// KOSMOS Epic #1634 · T026 · P3 Tool System Wiring
//
// ExportPDFTool — exports citizen-facing markdown to the Memdir USER tier.
//
// Input/Output contract (from specs/1634-tool-system-wiring/contracts/
//   primitive-envelope.md § 6):
//   Input : { markdown: string, title: string, include_attachments?: boolean }
//   Output: { pdf_path: string }   ← absolute path under ~/.kosmos/memdir/user/exports/
//
// STUB (P3): writes an HTML file, not a binary PDF.  The `pdf_path` field
// deliberately ends in `.html` so the LLM can inform the citizen accurately.
// A future task should upgrade to real PDF generation (see render.ts note).
//
// Zero new runtime dependencies — uses:
//   • `marked`        (already in tui/package.json)
//   • `node:fs`       (Bun stdlib)
//   • `node:os`       (Bun stdlib)
//   • `node:path`     (Bun stdlib)
//   • `node:crypto`   (Bun stdlib, for collision-free filename slugging)

import { mkdirSync, writeFileSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'
import { createHash } from 'node:crypto'
import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { DEFAULT_MEMDIR_ROOT } from '../../memdir/io.js'
import {
  EXPORT_PDF_TOOL_NAME,
  EXPORT_PDF_DESCRIPTION,
  EXPORT_PDF_PROMPT,
} from './prompt.js'
import { renderMarkdownToHtml } from './render.js'

// ---------------------------------------------------------------------------
// Schemas
// ---------------------------------------------------------------------------

const inputSchema = lazySchema(() =>
  z.strictObject({
    markdown: z
      .string()
      .min(1)
      .describe(
        'Citizen-facing markdown content to export (conversation excerpt or summary).',
      ),
    title: z
      .string()
      .min(1)
      .describe('Document title displayed as the page heading.'),
    include_attachments: z
      .boolean()
      .optional()
      .describe(
        'Reserved for future use — attachment embedding is deferred. Accepted but ignored in P3.',
      ),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

const outputSchema = lazySchema(() =>
  z.object({
    pdf_path: z
      .string()
      .describe(
        'Absolute path of the exported file under ~/.kosmos/memdir/user/exports/. ' +
          'In P3 this is an HTML file; the field name is kept for API stability.',
      ),
  }),
)
type OutputSchema = ReturnType<typeof outputSchema>
export type Output = z.infer<OutputSchema>

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------

/**
 * Returns the Memdir USER exports directory.
 * Mirrors the pattern used in tui/src/memdir/io.ts for the USER tier.
 *
 * Priority:
 *   1. KOSMOS_MEMDIR_ROOT env var (testing / integration override)
 *   2. DEFAULT_MEMDIR_ROOT (~/.kosmos/memdir) from memdir/io.ts
 */
export function exportsDir(
  root: string = process.env.KOSMOS_MEMDIR_ROOT ?? DEFAULT_MEMDIR_ROOT,
): string {
  return join(root, 'user', 'exports')
}

/**
 * Derive a filesystem-safe slug from the document title.
 * Limit to 48 chars to avoid path-length issues; append a short content hash
 * for collision-resistance.
 */
function makeFilename(title: string, markdown: string): string {
  const slug = title
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')       // strip non-word chars
    .replace(/\s+/g, '-')           // spaces → dashes
    .replace(/-+/g, '-')            // collapse consecutive dashes
    .replace(/^-|-$/g, '')          // trim leading/trailing dashes
    .slice(0, 48)
    || 'export'

  const ts = new Date()
    .toISOString()
    .replace(/[:.]/g, '-')
    .replace('T', 'T')
    .slice(0, 19)                   // YYYY-MM-DDTHH-MM-SS

  // 6-char content hash for collision resistance across same-title exports
  const hash = createHash('sha256')
    .update(markdown)
    .digest('hex')
    .slice(0, 6)

  return `${ts}-${slug}-${hash}.html`
}

// ---------------------------------------------------------------------------
// Tool definition
// ---------------------------------------------------------------------------

export const ExportPDFTool = buildTool({
  name: EXPORT_PDF_TOOL_NAME,
  searchHint:
    'export conversation content or summaries to a file for citizen download',
  maxResultSizeChars: 4_096,

  get inputSchema(): InputSchema {
    return inputSchema()
  },
  get outputSchema(): OutputSchema {
    return outputSchema()
  },

  isEnabled() {
    return true
  },
  isConcurrencySafe() {
    return false
  },
  isReadOnly() {
    return false
  },

  async description() {
    return EXPORT_PDF_DESCRIPTION
  },
  async prompt() {
    return EXPORT_PDF_PROMPT
  },

  mapToolResultToToolResultBlockParam(output, toolUseID) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result',
      content: `Exported to: ${output.pdf_path}`,
    }
  },

  renderToolUseMessage() {
    return null
  },
  renderToolResultMessage() {
    return null
  },

  async call({ markdown, title }) {
    const dir = exportsDir()
    mkdirSync(dir, { recursive: true, mode: 0o700 })

    const filename = makeFilename(title, markdown)
    const outputPath = join(dir, filename)
    const htmlContent = renderMarkdownToHtml(title, markdown)

    writeFileSync(outputPath, htmlContent, { encoding: 'utf-8', mode: 0o600 })

    return { data: { pdf_path: outputPath } }
  },
} satisfies ToolDef<InputSchema, Output>)
