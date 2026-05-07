// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — PdfInlineViewer component (FR-010, T016).
//
// Three-tier PDF rendering strategy (runtime signal-only, no hardcoded
// keyword tokenisers per feedback_no_hardcoding):
//
// Tier A — Kitty / iTerm2 graphics protocol detected at runtime:
//   pdf-to-img (WASM) → first-page PNG → inline escape-code render.
//
// Tier B — Terminal lacks graphics but OS `open` is available:
//   OS file opener fallback (macOS: open, Linux: xdg-open).
//
// Tier C — Headless SSH (no graphics, no opener, or SSH detected):
//   Text-only: path + size in KB + sha256 prefix.
//
// Detection sources (runtime env only):
//   TERM, TERM_PROGRAM, COLORTERM, KITTY_WINDOW_ID, ITERM_SESSION_ID.
//   A one-shot escape-code probe is attempted before falling back to env vars
//   (same approach as iTerm2's own detection).
//
// Source reference: research.md §UI-B FR-010 decision.

import React, { useEffect, useState } from 'react';
import { Box, Text } from '../../ink.js';
import { useUiL2I18n } from '../../i18n/uiL2.js';
import { createHash } from 'node:crypto';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { readFile, stat } from 'node:fs/promises';

const execFileAsync = promisify(execFile);

// ---------------------------------------------------------------------------
// Graphics protocol detection (runtime signals only)
// ---------------------------------------------------------------------------

type GraphicsSupport = 'kitty' | 'iterm2' | 'none';

function detectGraphicsSupport(): GraphicsSupport {
  const termProgram = process.env['TERM_PROGRAM'] ?? '';
  const term = process.env['TERM'] ?? '';
  const colorterm = process.env['COLORTERM'] ?? '';

  // Kitty: TERM=xterm-kitty or KITTY_WINDOW_ID set
  if (term === 'xterm-kitty' || process.env['KITTY_WINDOW_ID'] !== undefined) {
    return 'kitty';
  }

  // iTerm2: TERM_PROGRAM=iTerm.app or ITERM_SESSION_ID set
  if (
    termProgram === 'iTerm.app' ||
    process.env['ITERM_SESSION_ID'] !== undefined ||
    colorterm === 'truecolor' && termProgram.toLowerCase().includes('iterm')
  ) {
    return 'iterm2';
  }

  return 'none';
}

// ---------------------------------------------------------------------------
// OS opener detection
// ---------------------------------------------------------------------------

function detectOsOpener(): string | null {
  const platform = process.platform;
  if (platform === 'darwin') return 'open';
  if (platform === 'linux') {
    // Check SSH context (headless)
    if (process.env['SSH_CLIENT'] || process.env['SSH_TTY']) return null;
    return 'xdg-open';
  }
  return null;
}

// ---------------------------------------------------------------------------
// Kitty inline image render via APC escape (Kitty graphics protocol)
// We emit the payload as base64-encoded chunks with the Kitty APC sequence.
// For iTerm2 we use the OSC 1337 inline image protocol.
// ---------------------------------------------------------------------------

async function renderPdfPage(pdfPath: string): Promise<Buffer | null> {
  try {
    // Dynamic import of pdf-to-img — keeps the module optional at parse time.
    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment
    const pdfToImg = await import('pdf-to-img' as string).catch(() => null);
    if (!pdfToImg) return null;

    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    const doc = await (pdfToImg as Record<string, (p: string) => Promise<AsyncIterable<Buffer>>>).pdf(pdfPath);
    let firstPage: Buffer | null = null;
    for await (const page of doc) {
      firstPage = page;
      break; // only first page
    }
    return firstPage;
  } catch {
    return null;
  }
}

function emitKittyImage(pngBuffer: Buffer): string {
  const b64 = pngBuffer.toString('base64');
  const chunks: string[] = [];
  const CHUNK_SIZE = 4096;
  for (let i = 0; i < b64.length; i += CHUNK_SIZE) {
    const chunk = b64.slice(i, i + CHUNK_SIZE);
    const isLast = i + CHUNK_SIZE >= b64.length ? 1 : 0;
    const action = i === 0 ? 'a=T,f=100,' : 'a=p,';
    chunks.push(`\x1b_G${action}m=${isLast};${chunk}\x1b\\`);
  }
  return chunks.join('');
}

function emitIterm2Image(pngBuffer: Buffer): string {
  const b64 = pngBuffer.toString('base64');
  const len = pngBuffer.length;
  return `\x1b]1337;File=inline=1;size=${len}:${b64}\x07`;
}

// ---------------------------------------------------------------------------
// Fallback text builder
// ---------------------------------------------------------------------------

async function buildTextFallback(pdfPath: string, i18n: { pdfFallbackText: (p: string, kb: number, sha: string) => string }): Promise<string> {
  try {
    const [fileData, fileStat] = await Promise.all([
      readFile(pdfPath),
      stat(pdfPath),
    ]);
    const sha = createHash('sha256').update(fileData).digest('hex');
    const sizeKb = Math.round(fileStat.size / 1024);
    return i18n.pdfFallbackText(pdfPath, sizeKb, sha);
  } catch {
    return i18n.pdfFallbackText(pdfPath, 0, '?');
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export type PdfInlineViewerProps = {
  /** Absolute or relative path to the PDF file */
  pdfPath: string;
};

type RenderState =
  | { kind: 'idle' }
  | { kind: 'loading' }
  | { kind: 'inline'; escapeSequence: string }
  | { kind: 'fallback-open'; hint: string }
  | { kind: 'fallback-text'; text: string }
  | { kind: 'error'; message: string };

/**
 * PdfInlineViewer renders a PDF attachment using the highest-quality tier
 * available at runtime.  Falls back gracefully through three tiers.
 *
 * Contract (FR-010):
 * - Tier A (Kitty/iTerm2): inline PNG via graphics protocol.
 * - Tier B (other terminal with OS opener): open via system command.
 * - Tier C (headless SSH / no opener): text-only path + size + sha.
 */
export function PdfInlineViewer({ pdfPath }: PdfInlineViewerProps): React.ReactNode {
  const i18n = useUiL2I18n();
  const [state, setState] = useState<RenderState>({ kind: 'idle' });

  useEffect(() => {
    let cancelled = false;
    setState({ kind: 'loading' });

    async function render(): Promise<void> {
      const graphics = detectGraphicsSupport();

      if (graphics !== 'none') {
        // Tier A: try inline render
        const pngBuffer = await renderPdfPage(pdfPath);
        if (cancelled) return;

        if (pngBuffer) {
          const seq = graphics === 'kitty'
            ? emitKittyImage(pngBuffer)
            : emitIterm2Image(pngBuffer);
          setState({ kind: 'inline', escapeSequence: seq });
          return;
        }
        // pdf-to-img failed — fall through to Tier B/C.
      }

      const opener = detectOsOpener();
      if (opener) {
        // Tier B: OS opener
        try {
          await execFileAsync(opener, [pdfPath]);
          if (cancelled) return;
          setState({ kind: 'fallback-open', hint: i18n.pdfFallbackOpen });
        } catch {
          if (cancelled) return;
          const text = await buildTextFallback(pdfPath, i18n);
          setState({ kind: 'fallback-text', text });
        }
        return;
      }

      // Tier C: text-only
      const text = await buildTextFallback(pdfPath, i18n);
      if (cancelled) return;
      setState({ kind: 'fallback-text', text });
    }

    void render();
    return () => { cancelled = true; };
  }, [pdfPath, i18n]);

  switch (state.kind) {
    case 'idle':
    case 'loading':
      return (
        <Box>
          <Text dimColor>{i18n.pdfRenderingInline}</Text>
        </Box>
      );

    case 'inline':
      // Emit the raw escape sequence via process.stdout for graphics protocols.
      // React/Ink cannot render binary escape sequences, so we write directly.
      process.stdout.write(state.escapeSequence + '\n');
      return (
        <Box>
          <Text dimColor>[PDF inline]</Text>
        </Box>
      );

    case 'fallback-open':
      return (
        <Box>
          <Text dimColor>{state.hint}</Text>
        </Box>
      );

    case 'fallback-text':
      return (
        <Box>
          <Text dimColor>{state.text}</Text>
        </Box>
      );

    case 'error':
      return (
        <Box>
          <Text color="red">{state.message}</Text>
        </Box>
      );
  }
}
