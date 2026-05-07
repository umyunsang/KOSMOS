// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — MarkdownRenderer component (FR-011 partial, T017).
//
// Port of cc:components/Markdown.tsx — block-level inline preview with
// MarkdownTable delegation for table tokens and ANSI text rendering for
// everything else.  Uses the same LRU token cache pattern from CC to avoid
// re-parsing immutable history messages.
//
// KOSMOS adaptation: strips CC's React compiler runtime artifact (_c); uses
// KOSMOS ink.js imports; MarkdownTable is the 1:1 port from MarkdownTable.tsx.

import React, { Suspense, useMemo } from 'react';
import { marked, type Token, type Tokens } from 'marked';
import { Ansi, Box, useTheme } from '../../ink.js';
import { MarkdownTable } from './MarkdownTable.js';
import { formatToken, configureMarked } from '../../utils/markdown.js';
import { hashContent } from '../../utils/hash.js';
import { getCliHighlightPromise } from '../../utils/cliHighlight.js';

// ---------------------------------------------------------------------------
// LRU token cache (matches cc:components/Markdown.tsx strategy)
// ---------------------------------------------------------------------------
const TOKEN_CACHE_MAX = 500;
const tokenCache = new Map<string, Token[]>();

const MD_SYNTAX_RE = /[#*`|[>\-_~]|\n\n|^\d+\. |\n\d+\. /;

function hasMarkdownSyntax(s: string): boolean {
  return MD_SYNTAX_RE.test(s.length > 500 ? s.slice(0, 500) : s);
}

function cachedLexer(content: string): Token[] {
  if (!hasMarkdownSyntax(content)) {
    return [
      {
        type: 'paragraph',
        raw: content,
        text: content,
        tokens: [{ type: 'text', raw: content, text: content }],
      } as Token,
    ];
  }
  const key = hashContent(content);
  const hit = tokenCache.get(key);
  if (hit) {
    tokenCache.delete(key);
    tokenCache.set(key, hit); // promote to MRU
    return hit;
  }
  const tokens = marked.lexer(content);
  if (tokenCache.size >= TOKEN_CACHE_MAX) {
    const first = tokenCache.keys().next().value;
    if (first !== undefined) tokenCache.delete(first);
  }
  tokenCache.set(key, tokens);
  return tokens;
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------
export type MarkdownRendererProps = {
  children: string;
  /** Render all text dimmed */
  dimColor?: boolean;
};

/**
 * MarkdownRenderer renders markdown with:
 * - Tables → MarkdownTable component (CC-parity layout)
 * - All other tokens → ANSI string via formatToken
 *
 * Contract (FR-011): table layout must match CC MarkdownTable.tsx exactly.
 */
export function MarkdownRenderer({
  children,
  dimColor = false,
}: MarkdownRendererProps): React.ReactNode {
  configureMarked();

  const [theme] = useTheme();

  // Lazy highlight promise (same pattern as CC Markdown.tsx)
  const highlight = useMemo(() => {
    try {
      return getCliHighlightPromise();
    } catch {
      return null;
    }
  }, []);

  const tokens = cachedLexer(children);

  const nodes: React.ReactNode[] = tokens.map((token, idx) => {
    // Table tokens → dedicated MarkdownTable component
    if (token.type === 'table') {
      return (
        <MarkdownTable
          key={idx}
          token={token as Tokens.Table}
          highlight={null}
        />
      );
    }

    // All other tokens → ANSI string
    const ansiText = formatToken(token, theme, 0, null, null, null);
    if (!ansiText) return null;

    return (
      <Ansi key={idx}>{dimColor ? ansiText : ansiText}</Ansi>
    );
  });

  return (
    <Box flexDirection="column">
      {nodes}
    </Box>
  );
}
