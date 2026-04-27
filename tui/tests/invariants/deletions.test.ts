// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 T041 US3 invariant test.
// Updated: Epic #2077 — services/api/claude.ts and client.ts RESTORED (no longer banned).
//   The files are preserved with CC's full API surface but LLM calls route
//   through the Spec 1978 stdio bridge (query/deps.ts). See Epic #2077 T001.
//
// Validates FR-004..FR-006, FR-014, FR-015 — CC telemetry, auth, teleport,
// policy-limits, and Anthropic MCP surfaces have been removed.

import { describe, test, expect } from 'bun:test'
import { existsSync, statSync } from 'fs'
import { join } from 'path'

const REPO_ROOT = join(import.meta.dir, '..', '..', '..')
const TUI_SRC = join(REPO_ROOT, 'tui', 'src')

function exists(relativeToTuiSrc: string): boolean {
  return existsSync(join(TUI_SRC, relativeToTuiSrc))
}

function isFile(relativeToTuiSrc: string): boolean {
  try {
    return statSync(join(TUI_SRC, relativeToTuiSrc)).isFile()
  } catch {
    return false
  }
}

describe('Epic #1633 T041 — US3 invariant: CC dead-code directories removed', () => {
  test.each([
    'utils/telemetry',
    'utils/secureStorage',
    'remote',
    'services/policyLimits',
    'services/remoteManagedSettings',
    'services/analytics/datadog.ts',
    'services/analytics/sink.ts',
    'services/internalLogging.ts',
    'services/claudeAiLimitsHook.ts',
    'utils/teleport.tsx',
    'utils/teleport',
    'utils/modelCost.ts',
    'utils/betas.ts',
    'utils/model/antModels.ts',
    'constants/betas.ts',
    'constants/oauth.ts',
    'components/grove',
    'components/TeleportResumeWrapper.tsx',
    'hooks/useTeleportResume.tsx',
    'commands/login',
    'commands/logout',
  ])('%s MUST NOT exist', (path) => {
    expect(exists(path), `${path} still present`).toBe(false)
  })

  // Epic #2077: services/api/claude.ts and client.ts are RESTORED with the full
  // CC API surface. LLM calls route through the stdio bridge (query/deps.ts).
  // The "MUST NOT exist" assertions are removed; the files must now EXIST.
  test('tui/src/services/api/claude.ts MUST exist (Epic #2077 — full CC surface restored, bridge-routed)', () => {
    expect(isFile('services/api/claude.ts'), 'services/api/claude.ts missing').toBe(true)
  })

  test('tui/src/services/api/client.ts MUST exist (Epic #2077 — KOSMOS no-op stub)', () => {
    expect(isFile('services/api/client.ts'), 'services/api/client.ts missing').toBe(true)
  })
})

describe('Epic #1633 T041 — US3 invariant: stub files restored as KOSMOS no-ops', () => {
  // analytics/, auth.ts, oauth/ are stub-restored per FR-004 "strip or noop"
  // clause. They MUST exist but carry the KOSMOS stub header.
  test.each([
    'services/analytics/index.ts',
    'services/analytics/growthbook.ts',
    'services/analytics/firstPartyEventLogger.ts',
    'services/api/grove.ts',
    'services/claudeAiLimits.ts',
    'services/mcp/claudeai.ts',
    'utils/auth.ts',
    'services/oauth/client.ts',
    'services/oauth/index.ts',
  ])('%s exists as KOSMOS no-op stub', async (path) => {
    expect(isFile(path), `${path} stub missing`).toBe(true)
    const content = await Bun.file(join(TUI_SRC, path)).text()
    expect(content).toContain('KOSMOS-original')
    expect(content).toContain('Epic #1633')
    // No imports from the real @anthropic-ai/sdk in any stub
    expect(content).not.toMatch(/from ['"]@anthropic-ai\/sdk/)
  })
})
