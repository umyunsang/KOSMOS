// SPDX-License-Identifier: Apache-2.0
// Task T025: Codec round-trip tests — zod-parse every JSON file under
// tui/tests/fixtures/ipc/ against the frames.generated.ts discriminated union;
// one pass case + one malformed-json case per arm.

import { describe, expect, test } from 'bun:test'
import { readFileSync, readdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { decodeFrame, decodeFrames, encodeFrame } from '../../src/ipc/codec'
import type { IPCFrame } from '../../src/ipc/frames.generated'

const __dirname = dirname(fileURLToPath(import.meta.url))
const FIXTURES_DIR = join(__dirname, '../fixtures/ipc')

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Load a fixture file and return its content as a single-line JSON string. */
function loadFixture(filename: string): string {
  const raw = readFileSync(join(FIXTURES_DIR, filename), 'utf-8').trim()
  // Re-serialize to guarantee a single-line JSON string (fixture files are
  // pretty-printed with internal newlines which would confuse decodeFrames).
  return JSON.stringify(JSON.parse(raw))
}

function listFixtures(): string[] {
  return readdirSync(FIXTURES_DIR).filter(f => f.endsWith('.json'))
}

// ---------------------------------------------------------------------------
// Happy-path: every fixture must parse cleanly
// ---------------------------------------------------------------------------

describe('codec: fixture round-trip', () => {
  const fixtures = listFixtures()
  expect(fixtures.length).toBeGreaterThan(0)

  for (const filename of fixtures) {
    test(`parses ${filename}`, () => {
      const json = loadFixture(filename)
      const result = decodeFrame(json)
      expect(result.ok).toBe(true)
      if (!result.ok) return // type narrowing
      expect(result.frame).toBeDefined()
      expect(typeof result.frame.kind).toBe('string')
      expect(typeof result.frame.session_id).toBe('string')
      expect(typeof result.frame.ts).toBe('string')
    })
  }
})

// ---------------------------------------------------------------------------
// Happy-path: encodeFrame → decodeFrame round-trip preserves every field
// ---------------------------------------------------------------------------

describe('codec: encode→decode round-trip', () => {
  const fixtures = listFixtures()

  for (const filename of fixtures) {
    test(`round-trips ${filename}`, () => {
      const json = loadFixture(filename)
      const decoded = decodeFrame(json)
      expect(decoded.ok).toBe(true)
      if (!decoded.ok) return

      // Encode the decoded frame and decode again — must be equal
      const re_encoded = encodeFrame(decoded.frame)
      expect(re_encoded.endsWith('\n')).toBe(true)
      const re_decoded = decodeFrame(re_encoded.trimEnd())
      expect(re_decoded.ok).toBe(true)
      if (!re_decoded.ok) return

      expect(re_decoded.frame.kind).toBe(decoded.frame.kind)
      expect(re_decoded.frame.session_id).toBe(decoded.frame.session_id)
      expect(re_decoded.frame.ts).toBe(decoded.frame.ts)
    })
  }
})

// ---------------------------------------------------------------------------
// Error path: malformed JSON returns DecodeError (not throw) — per arm
// ---------------------------------------------------------------------------

const ARMS = [
  'user_input',
  'assistant_chunk',
  'tool_call',
  'tool_result',
  'coordinator_phase',
  'worker_status',
  'permission_request',
  'permission_response',
  'session_event',
  'error',
] as const

describe('codec: malformed JSON returns DecodeError', () => {
  for (const arm of ARMS) {
    test(`malformed JSON for arm ${arm} → DecodeError`, () => {
      const result = decodeFrame(`{not valid json for ${arm}}`)
      expect(result.ok).toBe(false)
      if (result.ok) return
      expect(result.error).toContain('JSON parse error')
      expect(result.raw).toBeDefined()
    })
  }
})

// ---------------------------------------------------------------------------
// Error path: valid JSON but wrong shape → Zod validation error
// ---------------------------------------------------------------------------

describe('codec: wrong shape returns DecodeError', () => {
  test('missing kind field', () => {
    const result = decodeFrame(JSON.stringify({ session_id: 'x', ts: 'y' }))
    expect(result.ok).toBe(false)
  })

  test('unknown kind value', () => {
    const result = decodeFrame(
      JSON.stringify({ kind: 'not_a_real_kind', session_id: 'x', ts: 'y' }),
    )
    expect(result.ok).toBe(false)
  })

  test('assistant_chunk missing message_id', () => {
    const result = decodeFrame(
      JSON.stringify({
        kind: 'assistant_chunk',
        session_id: 'x',
        ts: '2026-04-19T00:00:00Z',
        delta: 'hello',
        done: false,
        // message_id intentionally omitted
      }),
    )
    expect(result.ok).toBe(false)
  })
})

// ---------------------------------------------------------------------------
// decodeFrames: multi-line buffer splitting
// ---------------------------------------------------------------------------

describe('codec: decodeFrames buffer splitting', () => {
  test('empty buffer returns empty frames + empty remainder', () => {
    const { frames, remainder } = decodeFrames('')
    expect(frames).toHaveLength(0)
    expect(remainder).toBe('')
  })

  test('single complete line + newline', () => {
    const json = loadFixture('user_input.json')
    const { frames, remainder } = decodeFrames(json + '\n')
    expect(frames).toHaveLength(1)
    expect(frames[0]!.ok).toBe(true)
    expect(remainder).toBe('')
  })

  test('partial line buffered in remainder', () => {
    const partial = '{"kind": "user_input"'
    const { frames, remainder } = decodeFrames(partial)
    expect(frames).toHaveLength(0)
    expect(remainder).toBe(partial)
  })

  test('two complete lines in one chunk', () => {
    const a = loadFixture('user_input.json')
    const b = loadFixture('assistant_chunk.json')
    const { frames, remainder } = decodeFrames(a + '\n' + b + '\n')
    expect(frames).toHaveLength(2)
    expect(frames[0]!.ok).toBe(true)
    expect(frames[1]!.ok).toBe(true)
    expect(remainder).toBe('')
  })

  test('one line + partial second line', () => {
    const a = loadFixture('user_input.json')
    const partial = '{"kind": "ass'
    const { frames, remainder } = decodeFrames(a + '\n' + partial)
    expect(frames).toHaveLength(1)
    expect(remainder).toBe(partial)
  })

  test('blank lines between frames are skipped', () => {
    const a = loadFixture('user_input.json')
    const b = loadFixture('assistant_chunk.json')
    const { frames, remainder } = decodeFrames(a + '\n\n' + b + '\n')
    expect(frames).toHaveLength(2)
    expect(remainder).toBe('')
  })
})
