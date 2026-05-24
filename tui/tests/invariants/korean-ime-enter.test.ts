// SPDX-License-Identifier: Apache-2.0
// Regression guard for the Korean IME Enter path documented in specs/2519.

import { describe, expect, it } from 'bun:test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

const REPO_ROOT = join(import.meta.dir, '../../..')
const BASE_TEXT_INPUT = join(REPO_ROOT, 'tui/src/components/BaseTextInput.tsx')

describe('Korean IME Enter invariant', () => {
  it('does not swallow return while paste state is active', () => {
    const source = readFileSync(BASE_TEXT_INPUT, 'utf8')

    expect(source).not.toContain('isPasting && key.return')
    expect(source).not.toContain('key.return) {\n        return')
  })
})
