// SPDX-License-Identifier: Apache-2.0
// KOSAX-1633 P2 / KOSAX-1978 T009 — stub-noop replacement.
//
// Original CC module: `tui/src/commands/agents-platform/index.js`
// CC version: 2.1.88
// KOSAX deviation: agents-platform is Anthropic's `claude agents` CLI surface
// (Anthropic Console agent CRUD + collaboration). The Anthropic Console-backed
// CLI is non-functional in KOSAX by design.
//
// Function shape preserved so dynamic imports in main.tsx link successfully.
// Returning the absent-handler shape (`{ register: noop }`) is the canonical
// no-op pattern used elsewhere by KOSAX-1633 P2.

import type { Command } from '../../commands.js'

export function getAgentsPlatformCommands(): Command[] {
  return []
}

export const agentsPlatformCommands: Command[] = []

export default {
  getAgentsPlatformCommands,
  agentsPlatformCommands,
}
