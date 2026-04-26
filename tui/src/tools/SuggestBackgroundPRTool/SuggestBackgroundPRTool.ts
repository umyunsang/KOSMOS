// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T009 — stub-noop tool.
//
// Original CC: SuggestBackgroundPRTool — Anthropic's `claude pr` background
// PR suggestion tool. KOSMOS scope is Korean public-API queries, not GitHub
// PR workflow. Stub returns disabled tool descriptor.

export const SuggestBackgroundPRTool = {
  name: 'SuggestBackgroundPRTool_disabled',
  description: 'KOSMOS-1978: SuggestBackgroundPRTool not active in citizen TUI.',
  inputSchema: { type: 'object', properties: {} } as const,
  isEnabled: () => false,
}

export default SuggestBackgroundPRTool
