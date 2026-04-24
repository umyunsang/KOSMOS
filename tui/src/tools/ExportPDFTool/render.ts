// SPDX-License-Identifier: Apache-2.0
// KOSMOS Epic #1634 · T026 · P3 Tool System Wiring
//
// Renders citizen-facing markdown to a self-contained HTML document.
// Uses the `marked` package already present in tui/package.json (no new deps).
//
// STUB NOTE: This module produces HTML, not PDF. A future task should replace
// or wrap this with a real PDF generator once a zero-dep-compliant solution
// is identified (e.g., an IPC channel to a Bun-native renderer or a WASM
// PDF encoder). The caller (`ExportPDFTool.ts`) intentionally names the
// output `<slug>.html` so the format mismatch is transparent to the LLM.

import { marked } from 'marked'

/**
 * Render markdown to a complete, self-contained HTML document string.
 * The document includes inline CSS for print-friendly citizen output.
 */
export function renderMarkdownToHtml(title: string, markdown: string): string {
  // marked.parse is synchronous when the input has no async extensions.
  // The cast is safe: default marked configuration returns string, not Promise.
  const bodyHtml = marked.parse(markdown) as string

  return `<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${escapeHtml(title)}</title>
  <style>
    /* KOSMOS citizen export — print-optimised, palette-purple brand */
    :root {
      --brand-bg: #4c1d95;
      --brand-accent: #a78bfa;
      --text: #1f2937;
      --muted: #6b7280;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Noto Sans KR', 'Apple SD Gothic Neo', sans-serif;
      font-size: 15px;
      line-height: 1.7;
      color: var(--text);
      background: #fff;
      max-width: 800px;
      margin: 2rem auto;
      padding: 2rem 2.5rem;
    }
    header {
      border-top: 4px solid var(--brand-bg);
      padding-top: 1rem;
      margin-bottom: 2rem;
    }
    header .glyph {
      color: var(--brand-accent);
      font-size: 1.4rem;
      font-weight: 700;
      letter-spacing: 0.05em;
    }
    header h1 { font-size: 1.6rem; color: var(--brand-bg); margin-top: 0.25rem; }
    header .meta { color: var(--muted); font-size: 0.85rem; margin-top: 0.25rem; }
    main h1 { font-size: 1.5rem; margin: 1.25rem 0 0.5rem; color: var(--brand-bg); }
    main h2 { font-size: 1.25rem; margin: 1rem 0 0.4rem; color: var(--brand-bg); }
    main h3 { font-size: 1.05rem; margin: 0.75rem 0 0.3rem; }
    main p  { margin: 0.6rem 0; }
    main ul, main ol { margin: 0.6rem 0 0.6rem 1.5rem; }
    main li { margin: 0.2rem 0; }
    main code {
      font-family: 'Fira Mono', 'Courier New', monospace;
      background: #f3f4f6;
      padding: 0.1em 0.35em;
      border-radius: 3px;
      font-size: 0.88em;
    }
    main pre {
      background: #f3f4f6;
      padding: 1rem;
      border-radius: 6px;
      overflow-x: auto;
      margin: 0.75rem 0;
    }
    main pre code { background: none; padding: 0; }
    main blockquote {
      border-left: 3px solid var(--brand-accent);
      margin: 0.75rem 0;
      padding: 0.5rem 1rem;
      color: var(--muted);
    }
    main table {
      border-collapse: collapse;
      width: 100%;
      margin: 0.75rem 0;
    }
    main th, main td {
      border: 1px solid #e5e7eb;
      padding: 0.5rem 0.75rem;
      text-align: left;
    }
    main th { background: #f9fafb; font-weight: 600; }
    footer {
      margin-top: 3rem;
      padding-top: 1rem;
      border-top: 1px solid #e5e7eb;
      color: var(--muted);
      font-size: 0.8rem;
    }
    @media print {
      body { margin: 0; padding: 1.5cm; }
      header { border-top-width: 3px; }
    }
  </style>
</head>
<body>
  <header>
    <div class="glyph">✻ KOSMOS</div>
    <h1>${escapeHtml(title)}</h1>
    <div class="meta">생성일: ${new Date().toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' })}</div>
  </header>
  <main>
${bodyHtml}
  </main>
  <footer>
    KOSMOS 시민 서비스 하네스 — 이 문서는 자동 생성되었습니다.
    <!-- P3 stub: HTML format. Upgrade to PDF in a future phase once a zero-dep PDF encoder is decided. -->
  </footer>
</body>
</html>`
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}
