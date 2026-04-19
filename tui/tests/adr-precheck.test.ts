// SPDX-License-Identifier: Apache-2.0
// T102 — CI precondition test (FR-014, FR-057)
//
// Asserts that the Korean IME strategy ADR file exists in the repository
// before any IME implementation code is allowed to run.  This test is the
// SC-1 gate described in specs/287-tui-ink-react-bun/tasks.md § Phase 7 US5.
//
// Expected file (relative to repo root):
//   docs/adr/ADR-005-korean-ime-strategy.md
//
// If this test fails, it means:
//   - the ADR has been accidentally deleted, renamed, or moved, OR
//   - you are running the test suite from a worktree that does not include the
//     ADR commit.
// Restore or create the ADR before proceeding — see FR-014 and FR-057.

import { test, expect } from 'bun:test'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

// Derive repo root by walking two levels up from tui/tests/
const __dirname = dirname(fileURLToPath(import.meta.url))
const REPO_ROOT = resolve(__dirname, '..', '..')

const ADR_REL_PATH = 'docs/adr/ADR-005-korean-ime-strategy.md'
const ADR_ABS_PATH = resolve(REPO_ROOT, ADR_REL_PATH)

test(
  'FR-014 + FR-057: docs/adr/ADR-005-korean-ime-strategy.md must exist (SC-1 ADR gate)',
  () => {
    expect(
      existsSync(ADR_ABS_PATH),
      `ADR gate failed — expected file not found at:\n  ${ADR_ABS_PATH}\n` +
        `Restore ${ADR_REL_PATH} before merging any IME implementation (FR-014, FR-057).`,
    ).toBe(true)
  },
)

test(
  'FR-014 + FR-057: ADR-005 must record Option (a) as the accepted decision',
  () => {
    const content = readFileSync(ADR_ABS_PATH, 'utf8')
    expect(
      content.includes('Option (a)'),
      `ADR gate failed — ADR-005 does not contain the string "Option (a)".\n` +
        `File: ${ADR_ABS_PATH}\n` +
        `The document may be truncated or the decision may have been reverted.\n` +
        `Verify the ADR reflects the accepted fork strategy before proceeding (FR-014, FR-057).`,
    ).toBe(true)
  },
)
