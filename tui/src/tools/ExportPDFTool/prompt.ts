// SPDX-License-Identifier: Apache-2.0
// KOSMOS Epic #1634 · T026 · P3 Tool System Wiring

export const EXPORT_PDF_TOOL_NAME = 'ExportPDF'

/**
 * STUB: P3 produces an HTML file at the requested path.
 * A future task should upgrade this to real PDF generation once a
 * dependency decision is made (e.g., a headless-browser IPC channel or
 * a WASM PDF encoder that fits the zero-new-dep constraint).
 *
 * The LLM description deliberately calls out the HTML format so the model
 * can inform the citizen accurately.
 */
export const EXPORT_PDF_DESCRIPTION = `Export citizen-facing conversation content (summaries, excerpts) to an HTML file saved under the KOSMOS Memdir USER tier (~/.kosmos/memdir/user/exports/).

Input markdown is rendered into a styled HTML document. The returned path ends in \`.html\` (PDF generation is planned for a future release). Use this tool when the user wants a shareable, printable record of a conversation or summary.

Constraints:
- title must be a non-empty string (used as the HTML document title and <h1>)
- markdown must be non-empty
- include_attachments is accepted but currently ignored (attachment embedding is deferred)
- the output directory is created automatically`

export const EXPORT_PDF_PROMPT = `Export citizen-facing markdown content (conversation excerpts, summaries) as an HTML file under ~/.kosmos/memdir/user/exports/.

The file is styled for readability and is suitable for printing or sharing. The \`pdf_path\` field in the output contains the absolute path to the written file.

Use this when the user explicitly asks to export, save, or download a conversation record or summary.`
