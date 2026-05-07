// SPDX-License-Identifier: Apache-2.0
// KOSAX-1633 P2 / KOSAX-1978 T009 — stub-noop compaction strategy.
//
// Original CC: snipCompact — context-window pruning that snips low-priority
// tool results. KOSAX uses Spec 026 PromptManifest + the compact/microCompact
// pair for context budget management. snipCompact is referenced by
// services/contextCollapse — KOSAX-1633 stub-noop the latter so this stub is
// only consulted by callers that re-export the symbol. Returns the messages
// array unchanged (no snipping).

import type { Message } from '../../types/message.js'

export interface SnipCompactResult {
  messages: Message[]
  snippedCount: number
}

export async function snipCompact(messages: Message[]): Promise<SnipCompactResult> {
  return { messages, snippedCount: 0 }
}

export default snipCompact
