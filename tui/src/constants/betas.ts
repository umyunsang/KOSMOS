// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 post-merge fix · stub-noop beta constants.
//
// Wave B (commit 644661b) removed this file to strip Anthropic beta-header
// management per FR-013. Codex review on PR #1706 flagged that three active
// import sites remained (utils/context.ts, utils/sideQuery.ts,
// services/tokenEstimation.ts) — the last two gate feature-enablement on
// these constants, and the first is imported via main.tsx's boot path, so
// module resolution breaks at TUI launch.
//
// This file preserves the three exported names as KOSMOS-neutral values:
// empty string header / empty Set. All call sites naturally short-circuit
// to their disabled branch, which matches FR-013 intent (no Anthropic
// beta-feature surface). A future Epic may rewire these to KOSMOS-specific
// feature markers, in which case this file is replaced in whole.

/** Anthropic's "context-1M" beta HTTP header token. KOSMOS does not ship
 * 1M-context support in P1+P2 — returns empty string so any
 * `betas.includes(CONTEXT_1M_BETA_HEADER)` check resolves false. */
export const CONTEXT_1M_BETA_HEADER = ''

/** Anthropic's "structured-outputs" beta HTTP header token. KOSMOS does
 * not enable structured outputs in P1+P2 — empty string causes all
 * `.includes()` / `.push()` call sites to no-op in practice. */
export const STRUCTURED_OUTPUTS_BETA_HEADER = ''

/** Set of Vertex `countTokens` beta-header allow-list entries. KOSMOS does
 * not route through Vertex AI — empty Set so any filter through this
 * allow-list drops all members (no false-positive enablement). */
export const VERTEX_COUNT_TOKENS_ALLOWED_BETAS: ReadonlySet<string> = new Set<string>()
