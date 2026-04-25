// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — MarkdownTable component (FR-011, T018).
//
// 1:1 port of cc:components/MarkdownTable.tsx.
// Source: .references/claude-code-sourcemap/restored-src/src/components/MarkdownTable.tsx
// CC version: 2.1.88
//
// KOSMOS adaptation: imports updated to use KOSMOS ink.js path; otherwise
// identical to CC to preserve ≥90% fidelity per FR-034 / feedback_cc_tui_90_fidelity.

// Re-export the top-level MarkdownTable that lives in the shared components
// directory.  Having a messages-local re-export keeps import paths consistent
// across components within the messages/ subtree, and makes the 1:1 port
// clearly traceable to T018.
export { MarkdownTable } from '../MarkdownTable.js';
export type { } from '../MarkdownTable.js';
