// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 P2 / KOSMOS-1978 T009 — stub-noop tool.
//
// Original CC: VerifyPlanExecutionTool — internal Anthropic verification of
// plan-mode execution. KOSMOS plan mode lives in its own permission gauntlet
// (Spec 033 + Shift+Tab cycle). Stub returns disabled descriptor.

export const VerifyPlanExecutionTool = {
  name: 'VerifyPlanExecutionTool_disabled',
  description: 'KOSMOS-1978: VerifyPlanExecutionTool not active in citizen TUI.',
  inputSchema: { type: 'object', properties: {} } as const,
  isEnabled: () => false,
}

export default VerifyPlanExecutionTool
